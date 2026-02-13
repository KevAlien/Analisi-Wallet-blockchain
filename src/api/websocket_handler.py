"""
WebSocket handler for real-time signal and price streaming.
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Set

from fastapi import WebSocket, WebSocketDisconnect

from src.api.auth.security import hash_api_key
from src.database import mongodb as db

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for all users."""

    def __init__(self):
        # user_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._running = False

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        logger.info(f"WebSocket connected: user={user_id}, "
                    f"total_connections={self.total_connections}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"WebSocket disconnected: user={user_id}")

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a user."""
        connections = self.active_connections.get(user_id, set())
        dead_connections = set()

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws, user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)


# Global manager instance
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> str:
    """
    Authenticate a WebSocket connection.

    Supports authentication via:
    - Query parameter: ?api_key=wt_sk_...
    - Query parameter: ?token=jwt_token_here
    """
    api_key = websocket.query_params.get("api_key")
    token = websocket.query_params.get("token")

    if api_key:
        key_hash = hash_api_key(api_key)
        user = await db.get_user_by_api_key_hash(key_hash)
        if user:
            return str(user["_id"])

    if token:
        from src.api.auth.security import decode_jwt_token
        try:
            payload = decode_jwt_token(token)
            return payload.get("sub", "")
        except Exception:
            pass

    return ""


async def websocket_signal_handler(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal streaming.

    Connection: ws://host/api/v1/ws/signals?api_key=wt_sk_...

    Messages sent:
    - {"type": "signal", "data": {...}}  - New trading signal
    - {"type": "heartbeat", "timestamp": "..."}  - Keep-alive
    """
    user_id = await authenticate_websocket(websocket)
    if not user_id:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await manager.connect(websocket, user_id)

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "message": "Signal stream connected",
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        last_check = datetime.utcnow()

        while True:
            # Check for new signals periodically
            try:
                signals, _ = await db.get_signals(
                    user_id=user_id,
                    since=last_check,
                    page=1,
                    page_size=10,
                )

                for signal in signals:
                    await websocket.send_json({
                        "type": "signal",
                        "data": {
                            "id": str(signal["_id"]),
                            "signal_type": signal.get("signal_type"),
                            "strength": signal.get("strength"),
                            "confidence": signal.get("confidence"),
                            "chain": signal.get("chain"),
                            "description": signal.get("description", ""),
                            "recommended_action": signal.get("recommended_action"),
                            "created_at": signal.get("created_at", datetime.utcnow()).isoformat(),
                        },
                    })

                last_check = datetime.utcnow()

            except Exception as e:
                logger.error(f"Signal check error: {e}")

            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": manager.total_connections,
            })

            # Wait for messages or timeout
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                # Handle client messages (e.g., filter updates)
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                continue

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


async def websocket_price_handler(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price updates.

    Connection: ws://host/api/v1/ws/prices?api_key=wt_sk_...&symbols=BTC,ETH
    """
    user_id = await authenticate_websocket(websocket)
    if not user_id:
        await websocket.close(code=4001, reason="Authentication required")
        return

    symbols_param = websocket.query_params.get("symbols", "BTC,ETH")
    symbols = [s.strip() for s in symbols_param.split(",")]

    await manager.connect(websocket, user_id)

    try:
        from src.market_data.price_oracle import PriceOracle, PriceSource
        oracle = PriceOracle(primary_source=PriceSource.BINANCE)

        while True:
            try:
                prices = await oracle.get_multiple_prices(
                    [s.lower() for s in symbols]
                )

                if prices:
                    await websocket.send_json({
                        "type": "prices",
                        "data": {
                            symbol.upper(): price
                            for symbol, price in prices.items()
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.error(f"Price fetch error: {e}")

            # Update every 10 seconds
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                msg = json.loads(data)
                if msg.get("type") == "subscribe":
                    new_symbols = msg.get("symbols", [])
                    if new_symbols:
                        symbols = new_symbols
            except asyncio.TimeoutError:
                continue

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Price WebSocket error: {e}")
        manager.disconnect(websocket, user_id)
