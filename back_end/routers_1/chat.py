"""用户聊天接口"""
import asyncio
from typing import Any
from crud_1.chat import (
    check_chat_permission,
    get_message,
    get_my_message_list,
    get_or_create_chat,
    read_message,
    send_message,
)
from crud_1.users import get_user_cached, get_user_info, verify_websocket_user
from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, WebSocket, HTTPException, WebSocketDisconnect, Query
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from schemas_1.chat import SendMessageRequest, WSMessage
from tools_1.limit import check_rate_limit
from tools_1.logger import get_logger
from tools_1.websocket_manager import manager

chat = APIRouter()
logger = get_logger(__name__, "python")


"""获取/创建 订单聊天接口"""
@chat.post("/api/chat/conversations")
async def create_or_get_chat(order_id:int,current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_or_create_chat(
        user_id=current_user["id"],
        order_id=order_id
    )
    return result


"""获取聊天信息接口"""
@chat.get("/api/chat/conversations/{conversation_id}/messages")
async def get_my_messages(conversation_id: int,before_id: int | None = Query(default=None, ge=1),
limit: int = Query(default=50, ge=1, le=100),current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_message(
        user_id=current_user["id"],
        conversation_id=conversation_id,
        before_id=before_id,
        limit=limit
    )
    return result


"""发送消息接口"""
@chat.post("/api/chat/conversations/{conversation_id}/messages")
async def send_msg(conversation_id:int,data:SendMessageRequest,current_user = Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str,Any]:
    # 和 WebSocket 共用同一个限流 key 换通道也绕不过去
    await check_rate_limit(
        redis,
        f"ratelimit:chat:{current_user['id']}", 30, 60, "发送消息过于频繁"
    )
    result = await send_message(
        user_id=current_user["id"],
        content=data.content,
        conversation_id=conversation_id
    )
    return result


"""获取所有聊天信息接口"""
@chat.get("/api/chat/conversations")
async def get_all_msg(current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_my_message_list(
        user_id=current_user["id"]
    )
    return result


"""标记消息已读接口"""
@chat.post("/api/chat/messages/{message_id}/read")
async def read_msg(message_id: int,current_user=Depends(get_user_info)) -> dict[str, Any]:
    user_id = current_user["id"]
    result = await read_message(
        user_id=user_id,
        message_id=message_id
    )
    if result["code"] != 200:
        return result
    data = result["data"]
    if data.get("newly_read", False):
        await manager.broadcast(
            data["conversation_id"],
            {
                "type": "read",
                "data": {
                    "message_ids": [message_id],
                    "reader_id": user_id
                }
            }
        )
    return result


"""WebSocket接口"""
@chat.websocket("/api/chat/ws/{conversation_id}")
async def chat_websocket(websocket:WebSocket,conversation_id:int) -> None:
    """
    WebSocket 聊天
    :param websocket:Websocket
    :param conversation_id:会话id
    :return:
    """
    connected = False
    redis = websocket.app.state.redis
    await websocket.accept()

    try:
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10
            )
        except ValueError:
            logger.warning("WebSocket认证失败原因=无效JSON")
            await websocket.close(
                code=1008,reason="认证信息无效"
            )
            return

        if (
            not isinstance(auth_data,dict)
            or auth_data.get("type") != "auth"
            or not isinstance(auth_data.get("token"),str)
        ):
            logger.warning("WebSocket认证失败原因=认证消息格式错误")
            await websocket.close(
                code=1008,reason="认证信息无效"
            )
            return

        try:
            current_user = await verify_websocket_user(redis, auth_data["token"])
            user_id = current_user["id"]

            await check_chat_permission(
                user_id=user_id,
                conversation_id=conversation_id
            )

            manager.connect(conversation_id, websocket)
            connected = True

            await websocket.send_json({
                "type": "auth_success",
                "user_id": user_id
            })
            logger.info(
                "WebSocket认证成功 user_id=%s conversation_id=%s",
                user_id,
                conversation_id
            )
        except (HTTPException,ValueError):
            logger.warning(
                "WebSocket认证失败或无权限 conversation_id=%s",
                conversation_id
            )
            await websocket.close(
                code=1008,reason="认证失败或无权访问"
            )
            return

        while True:
            try:
                raw_data = await websocket.receive_json()
            except ValueError:
                """收到的不是合法JSON,提示后继续等待下一条"""
                await websocket.send_json({
                    "type": "error",
                    "message": "消息格式不正确"
                })
                continue

            try:
                data = WSMessage.model_validate(raw_data)
            except ValidationError:
                await websocket.send_json({
                    "type": "error",
                    "message": "消息格式不正确"
                })
                continue

            if data.type == "ping":
                await websocket.send_json({
                    "type":"pong"
                })
                continue

            if data.type != "message":
                await websocket.send_json({
                    "type": "error",
                    "message": "不支持的消息类型"
                })
                continue

            content = (data.content or "").strip()
            if not content:
                await websocket.send_json({
                    "type": "error",
                    "message": "消息不能为空"
                })
                continue

            # 每条消息前检查账号状态 走用户缓存 基本不增加 MySQL 压力
            user = await get_user_cached(redis, user_id)
            if user is None or user["status"] == "banned":
                logger.warning(
                    "WebSocket账户不可用 user_id=%s conversation_id=%s",
                    user_id,
                    conversation_id
                )
                await websocket.close(code=1008, reason="账户不可用")
                return

            try:
                # 限流 抛出的 HTTPException 会被下面接住 以错误消息形式发给客户端
                await check_rate_limit(
                    redis,
                    f"ratelimit:chat:{user_id}", 30, 60, "发送消息过于频繁"
                )
                result = await send_message(
                    user_id=user_id,
                    content=content,
                    conversation_id=conversation_id
                )
            except HTTPException as exc:
                await websocket.send_json({
                    "type": "error",
                    "message": str(exc.detail)
                })
                continue

            await manager.broadcast(
                conversation_id,
                {
                    "type": "message",
                    "data": jsonable_encoder(result["data"])
                }
            )

    except WebSocketDisconnect:
        pass

    except TimeoutError:
        logger.warning("WebSocket认证超时 conversation_id=%s", conversation_id)
        await websocket.close(
            code=1008,
            reason="认证超时"
        )

    finally:
        if connected:
            manager.disconnect(conversation_id, websocket)
            logger.info(
                "WebSocket会话结束 user_id=%s conversation_id=%s",
                user_id,
                conversation_id
            )
