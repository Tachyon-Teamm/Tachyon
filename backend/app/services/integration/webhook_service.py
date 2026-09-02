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
