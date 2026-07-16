import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NotificationManager:

    def __init__(self):
        self._history: list[dict] = []
        self._rate_limits: dict[str, datetime] = {}
        self._min_interval = timedelta(seconds=30)
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send(self, channels: list[dict], alert_name: str, severity:str, state: str, message: str, annotations: dict[str, Any] | None = None):
        for channel in channels:
            channel_type = channel.get("type", "")
            channel_id = f"{channel_type}:{channel.get("webhook", channel.get("url", ""))}"

            if self._is_rate_limited(channel_id):
                logger.debug(f"Rate limited: {channel_id}")
                continue

            try:
                pass
            except Exception as e:
                logger.error(f"Notification failed ({channel_type}):{e}")
                self._record_history(channel_type, alert_name, state, "failed", str(e))

    async def _send_slack(self, channel:dict, alert_name:str, severity:str, state: str, message:str, annotations: dict | None):
        webhook_url = channel.get("webhook", "")
        if not webhook_url:
            return 

        colors = {
            "firing": "#FF4444" if severity == "critical" else "#FF8C00",
            "resolved": "#44BB44",
            "still_firing": "#FF8C00",
        }

        emoji = {"firing": "\U0001f6a8", "resolved": "\u2705", "still_firing": "\u26a0\ufe0f"}

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji.get(state, '')} [{severity.upper()}] {alert_name}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*State:* {state.upper()}\n*Message:* {message}",
                },
            },
        ]

        if annotations:
            fields = []
            for k, v in list(annotations.items())[:6]:
                fields.append({"type": "mrdwn", "text": f"*{k}:*{v}"})
            
            if fields:
                blocks.append({"type": "section", "fields": fields})

            payload = {
                "attachments": [{
                    "color": colors.get(state, "#888888"),
                    "blocks": blocks,
                }]
            }

            response = await self._client.post(webhook_url, json=payload)
            response.raise_for_status()

    async def _send_webhook(self, channel: dict, alert_name: str, severity: str, state: str, message: str, annotations: dict | None,):
        url = channel.get("url", "")
        if not url:
            return
        
        payload = {
            "alert_name": alert_name,
            "severity": severity,
            "state": state,
            "message": message,
            "annotations": annotations or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "sentryops",
        }

        headers = channel.get("headers", {})
        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

                        

    async def _store_in_app(self, alert_name:str, severity: str, state: str, message:str, annotations: dict | None):
        self._history.append({
            "type": "in_app",
            "alert_name": alert_name,
            "severity": severity,
            "state": state,
            "message": message,
            "annotations": annotations or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
         })
    def _is_rate_limited(self, channel_id: str)-> bool:
        last_sent = self._rate_limits.get(channel_id)
        if not last_sent:
            return False
        return datetime.now(timezone.utc) - last_sent < self._min_interval


    def _mark_sent(self, channel_id: str):
        self._rate_limits[channel_id] = datetime.now(timezone.utc)

    def _record_history(self, channel_type: str, alert_name: str, state: str, status: str, error: str | None = None):
        self._history.append({
            "channel": channel_type,
            "alert_name": alert_name,
            "state": state,
            "status": status,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if len(self._history) > 1000:
            self._history = self._history[-500:]


    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:][::-1]

    def get_unread_in_app(self) -> list[dict]:
        return [n for n in self._history if n.get("type") == "in_app" and not n.get("read")]

    async def close(self):
        await self._client.aclose()


notification_manager = NotificationManager()
    