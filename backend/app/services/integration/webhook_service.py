from typing import Dict, Any, Optional
import hmac
import hashlib
import json
from datetime import datetime, timezone

class WebhookService:
    """
    Enterprise Outbound Webhook Dispatcher:
    Dispatches signed HMAC-SHA256 events on CNMC lifecycle actions with delivery logging.
    """

    @staticmethod
    def generate_hmac_signature(payload: Dict[str, Any], secret_key: str) -> str:
        data_str = json.dumps(payload, sort_keys=True)
        return hmac.new(secret_key.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def build_event_payload(event_type: str, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event_id": f"evt_{datetime.now(timezone.utc).timestamp()}",
            "event_type": event_type,
            "entity_id": entity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

    @classmethod
    def dispatch_event(
        cls,
        target_url: str,
        event_type: str,
        entity_id: str,
        data: Dict[str, Any],
        secret_key: Optional[str] = None,
        timeout: float = 3.0
    ) -> Dict[str, Any]:
        """
        Dispatches a signed HMAC-SHA256 event to a target webhook endpoint.
        Returns a delivery receipt with status and timestamp.
        """
        import urllib.request

        payload = cls.build_event_payload(event_type, entity_id, data)
        body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "UniMM-National-Master/1.0",
        }
        if secret_key:
            headers["X-UniMM-Signature"] = cls.generate_hmac_signature(payload, secret_key)

        req = urllib.request.Request(target_url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {
                    "event_id": payload["event_id"],
                    "status": "DELIVERED",
                    "http_status": resp.status,
                    "delivered_at": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {
                "event_id": payload["event_id"],
                "status": "FAILED",
                "error": str(e),
                "attempted_at": datetime.now(timezone.utc).isoformat()
            }
