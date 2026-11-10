"""WebSocket管理器"""

from collections import defaultdict
from fastapi import WebSocket
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")


class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[
            int, set[WebSocket]
        ] = defaultdict(set)

    def connect(
        self,
        conversation_id: int,
        websocket: WebSocket
    ) -> None:
        self.active_connections[conversation_id].add(websocket)
        logger.info(
            "WebSocket连接加入 conversation_id=%s connections=%s",
            conversation_id,
            len(self.active_connections[conversation_id])
        )

    def disconnect(
        self,
        conversation_id: int,
        websocket: WebSocket
    ) -> None:
        connections = self.active_connections.get(conversation_id)

        if connections is None:
            return

        connections.discard(websocket)

        if not connections:
            self.active_connections.pop(conversation_id, None)
        logger.info(
            "WebSocket连接断开 conversation_id=%s connections=%s",
            conversation_id,
            len(connections)
        )

    async def broadcast(
        self,
        conversation_id: int,
        data: dict
    ) -> None:
        connections = list(
            self.active_connections.get(conversation_id, set())
        )

        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception:
                logger.warning(
                    "WebSocket广播失败，移除连接 conversation_id=%s",
                    conversation_id
                )
                self.disconnect(conversation_id, websocket)


manager = ConnectionManager()
