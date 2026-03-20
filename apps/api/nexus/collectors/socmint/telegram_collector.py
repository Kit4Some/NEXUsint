"""Telegram data collector using Telethon."""

from datetime import datetime
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()


class TelegramCollector(BaseCollector):
    """Collects data from public Telegram channels/groups via Telethon."""

    def __init__(self) -> None:
        super().__init__(rate_limit=0.5, max_retries=2)
        self._api_id = settings.telegram_api_id
        self._api_hash = settings.telegram_api_hash
        self._client = None

    async def _get_client(self) -> Any:
        """Lazy-initialize Telethon client."""
        if self._client is None:
            try:
                from telethon import TelegramClient

                self._client = TelegramClient(
                    "nexus_session", self._api_id, self._api_hash
                )
                await self._client.start()
            except Exception as e:
                logger.error("telegram.client_init_failed", error=str(e))
                raise
        return self._client

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        if not self._api_id or not self._api_hash:
            logger.warning("telegram.no_api_credentials")
            return []

        scan_type = query.scan_type
        try:
            if scan_type == "channel_messages":
                return await self._get_channel_messages(query.query, query.options)
            elif scan_type == "channel_info":
                return await self._get_channel_info(query.query)
            else:
                logger.warning("telegram.unknown_scan_type", scan_type=scan_type)
                return []
        except Exception as e:
            logger.error("telegram.collection_failed", error=str(e), scan_type=scan_type)
            return []

    async def _get_channel_messages(
        self, channel: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get messages from a public Telegram channel."""
        client = await self._get_client()
        limit = options.get("limit", 100)

        results: list[CollectionResult] = []
        async for message in client.iter_messages(channel, limit=limit):
            if message.text:
                media_info = None
                if message.media:
                    media_info = {"type": type(message.media).__name__}

                results.append(CollectionResult(
                    source_int="SOCMINT",
                    source_id=f"telegram:message:{channel}:{message.id}",
                    raw_data={
                        "id": message.id,
                        "text": message.text,
                        "date": message.date.isoformat() if message.date else None,
                        "sender_id": message.sender_id,
                        "reply_to": message.reply_to_msg_id,
                        "forwards": message.forwards,
                        "views": message.views,
                        "has_media": message.media is not None,
                    },
                    normalized={
                        "entity_type": "Post",
                        "platform": "telegram",
                        "channel": channel,
                        "text": message.text,
                        "created_at": message.date.isoformat() if message.date else "",
                        "sender_id": str(message.sender_id) if message.sender_id else "",
                        "views": message.views or 0,
                        "forwards": message.forwards or 0,
                        "media": media_info,
                    },
                    metadata={"collector": "telegram", "scan_type": "channel_messages"},
                    reliability_grade="C",
                ))

        logger.info("telegram.messages_collected", channel=channel, count=len(results))
        return results

    async def _get_channel_info(self, channel: str) -> list[CollectionResult]:
        """Get information about a Telegram channel."""
        client = await self._get_client()

        entity = await client.get_entity(channel)
        full = await client(
            __import__("telethon.tl.functions.channels", fromlist=["GetFullChannelRequest"])
            .GetFullChannelRequest(entity)
        )

        info = {
            "id": entity.id,
            "title": getattr(entity, "title", ""),
            "username": getattr(entity, "username", ""),
            "participants_count": getattr(full.full_chat, "participants_count", 0),
            "about": getattr(full.full_chat, "about", ""),
            "date": entity.date.isoformat() if hasattr(entity, "date") and entity.date else "",
        }

        return [CollectionResult(
            source_int="SOCMINT",
            source_id=f"telegram:channel:{entity.id}",
            raw_data=info,
            normalized={
                "entity_type": "SocialAccount",
                "platform": "telegram",
                "username": info["username"],
                "display_name": info["title"],
                "description": info["about"],
                "followers_count": info["participants_count"],
                "created_at": info["date"],
            },
            metadata={"collector": "telegram", "scan_type": "channel_info"},
            reliability_grade="C",
        )]

    async def close(self) -> None:
        """Disconnect Telethon client and close HTTP session."""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None
        await super().close()

    async def health_check(self) -> bool:
        if not self._api_id or not self._api_hash:
            return False
        try:
            await self._get_client()
            return True
        except Exception:
            return False
