"""用户聊天接口函数"""
import datetime
from sqlalchemy import select,or_
from sqlalchemy.orm import selectinload
from modles_1.chat import ChatConversation,ChatMessage
from modles_1.order import Order
from typing import Any
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException,status
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")

async def get_or_create_chat(user_id:int,order_id:int) -> dict[str,Any]:
    """
    获取/创建 订单聊天
    :param order_id:订单id
    :param user_id:用户id
    :return:聊天信息
    """
    async with async_session_maker() as session:
        stmt = select(Order).where(
            Order.id == order_id
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        if user_id not in (order.buyer_id,order.seller_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无法访问此订单"
            )
        stmt = select(ChatConversation).where(
            ChatConversation.order_id == order_id,
            ChatConversation.buyer_id == order.buyer_id,
            ChatConversation.seller_id == order.seller_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            conversation = ChatConversation(
                order_id=order.id,
                buyer_id=order.buyer_id,
                seller_id=order.seller_id
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            logger.info(
                "聊天会话创建成功 conversation_id=%s order_id=%s",
                conversation.id,
                order_id
            )
        return {
            "code": 200,
            "message": "获取聊天成功",
            "data": {
                "conversation_id": conversation.id,
                "order_id": conversation.order_id,
                "buyer_id": conversation.buyer_id,
                "seller_id": conversation.seller_id,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at
            }
        }

async def get_message(user_id:int,conversation_id:int) -> dict[str,Any]:
    """
    获取聊天信息
    :param user_id:用户id
    :param conversation_id:聊天id
    :return:聊天消息列表
    """
    async with async_session_maker() as session:
        stmt = select(ChatConversation).where(
            ChatConversation.id == conversation_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在"
            )
        if user_id not in (conversation.buyer_id,conversation.seller_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问"
            )
        stmt = select(ChatMessage).where(
            ChatMessage.conversation_id == conversation_id,
        ).order_by(ChatMessage.created_at.asc())
        result = await session.execute(stmt)
        messages = result.scalars().all()
        message_list = []
        for message in messages:
            message_list.append({"id":message.id,
                "conversation_id":message.conversation_id,
                "sender_id": message.sender_id,
                "content": message.content,
                "message_type":message.message_type,
                "is_read": message.is_read,
                "created_at": message.created_at})
        return {"code": 200,
                "message":"获取聊天消息成功",
                "data": message_list
                }

async def send_message(user_id:int,content:str,conversation_id:int) -> dict[str,Any]:
    """
    发送消息
    :param user_id:用户id
    :param content:内容
    :param conversation_id:对话id
    :return:内容信息
    """
    async with async_session_maker() as session:
        stmt = select(ChatConversation).where(
            ChatConversation.id == conversation_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在"
            )
        if user_id not in (conversation.seller_id,conversation.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问"
            )
        content = content.strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息内容不能为空"
            )
        if len(content) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="字数超出限制"
            )
        message = ChatMessage(
            conversation_id=conversation_id,
            sender_id=user_id,
            content=content,
            message_type="text",
            is_read=False
        )
        session.add(message)
        conversation.updated_at = datetime.datetime.now()
        await session.commit()
        await session.refresh(conversation)
        message_id = message.id
        logger.info(
            "聊天消息发送成功 message_id=%s conversation_id=%s sender_id=%s",
            message_id,
            conversation_id,
            user_id
        )
        return {"code": 200,
            "message": "发送成功",
            "data": {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_id": message.sender_id,
                "content": message.content,
                "message_type": message.message_type,
                "is_read": message.is_read,
                "created_at": message.created_at
            }
        }

async def get_my_message_list(user_id:int) -> dict[str,Any]:
    """
    获取我的所有聊天信息
    :param user_id:用户id
    :return:聊天信息列表
    """
    async with async_session_maker() as session:
        stmt = select(ChatConversation).where(
            or_(
                ChatConversation.seller_id == user_id,
                ChatConversation.buyer_id == user_id
            )
        ).order_by(ChatConversation.updated_at.desc())
        result = await session.execute(stmt)
        conversations = result.scalars().all()
        conversation_list = []
        for conversation in conversations:
            other_user_id = (
                conversation.seller_id
                if conversation.buyer_id == user_id
                else conversation.buyer_id
            )
            conversation_list.append({
                "id": conversation.id,
                "order_id": conversation.order_id,
                "buyer_id": conversation.buyer_id,
                "seller_id": conversation.seller_id,
                "other_user_id": other_user_id,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at
            })
        return {
            "code": 200,
            "message": "获取聊天列表成功",
            "data": conversation_list
        }

async def read_message(message_id:int,user_id:int) -> dict[str,Any]:
    """
    标记消息已读
    :param message_id: 消息id
    :param user_id: 当前用户id
    :return:
    """
    async with async_session_maker() as session:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.id == message_id)
            .options(
                selectinload(ChatMessage.conversation)
            )
        )
        result = await session.execute(stmt)
        message = result.scalar_one_or_none()
        if message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="信息不存在"
            )
        conversation = message.conversation
        if user_id not in (
            conversation.buyer_id,
            conversation.seller_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问"
            )
        if message.sender_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能标记自己发送的信息"
            )
        if message.is_read:
            return {
                "code": 200,
                "message": "消息已是已读状态",
                "data": {
                    "message_id": message.id,
                    "conversation_id": conversation.id,
                    "is_read": True,
                    "newly_read": False
                }
            }
        message.is_read = True
        await session.commit()
        logger.info(
            "聊天消息标记已读 message_id=%s user_id=%s",
            message.id,
            user_id
        )
        return {
            "code": 200,
            "message": "标记已读成功",
            "data": {
                "message_id": message.id,
                "conversation_id": conversation.id,
                "is_read": True,
                "newly_read": True
            }
        }

async def check_chat_permission(user_id:int,conversation_id:int) -> bool:
    """
    检查聊天权限
    :param user_id:用户id
    :param conversation_id:对话id
    :return:是否有对话权限
    """
    async with async_session_maker() as session:
        stmt = select(ChatConversation).where(
            ChatConversation.id == conversation_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在"
            )
        if user_id not in (conversation.buyer_id,conversation.seller_id):
            raise HTTPException(
                status_code=403,
                detail="无权访问该聊天"
            )
        return True


































