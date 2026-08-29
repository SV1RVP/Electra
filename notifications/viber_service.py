from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

logger = logging.getLogger("UPSStatus.Viber")


class ViberService:
    """
    Viber Notification Service for Channels and Bots.
    Supports token validation, superadmin lookup, automatic webhook initialization,
    and message delivery.
    """

    def __init__(self, token: str = "", sender_name: str = "UPS Monitor", receiver_id: str = ""):
        self.token = token.strip()
        self.sender_name = sender_name.strip() or "UPS Monitor"
        self.receiver_id = receiver_id.strip()

    def update_config(self, token: str, sender_name: str, receiver_id: str = ""):
        self.token = token.strip()
        self.sender_name = sender_name.strip() or "UPS Monitor"
        self.receiver_id = receiver_id.strip()

    def _ensure_webhook(self) -> bool:
        """
        Initializes the Viber webhook if not set yet.
        Viber API requires a set_webhook call at least once before allowing messages.
        """
        if not self.token:
            return False
        headers = {"X-Viber-Auth-Token": self.token}
        url = "https://chatapi.viber.com/pa/set_webhook"
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"url": "https://httpbin.org/post"},
                timeout=10,
            ).json()
            if resp.get("status") == 0:
                logger.info("Viber webhook initialized successfully.")
                return True
            else:
                logger.warning(f"Viber set_webhook returned: {resp.get('status_message')}")
        except Exception as e:
            logger.error(f"Viber set_webhook exception: {e}")
        return False

    def _get_superadmin_id(self) -> Optional[str]:
        if not self.token:
            return None
        headers = {"X-Viber-Auth-Token": self.token}
        url = "https://chatapi.viber.com/pa/get_account_info"
        try:
            resp = requests.post(url, headers=headers, json={}, timeout=10).json()
            if resp.get("status") == 0:
                members = resp.get("members", [])
                admin_id = next(
                    (m["id"] for m in members if m.get("role") == "superadmin"), None
                )
                if not admin_id and members:
                    admin_id = members[0]["id"]
                return admin_id
            else:
                msg = resp.get("status_message", "")
                if msg == "invalidAuthToken":
                    logger.warning("Viber get_account_info: Token is not valid. Please configure a valid Viber Auth Token in Settings.")
                else:
                    logger.warning(f"Viber get_account_info failed: {msg}")
        except Exception as e:
            logger.warning(f"Viber get_account_info exception: {e}")
        return None

    def send_message(self, text: str, retry_webhook: bool = True) -> Tuple[bool, Optional[str]]:
        if not self.token:
            return False, "Viber Channel/Bot token is not configured."

        headers = {"X-Viber-Auth-Token": self.token}

        # Case 1: If receiver_id is set, send direct bot message to user
        if self.receiver_id:
            url = "https://chatapi.viber.com/pa/send_message"
            payload = {
                "receiver": self.receiver_id,
                "type": "text",
                "text": text,
                "sender": {"name": self.sender_name},
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=12).json()
                if resp.get("status") == 0:
                    return True, None
                elif resp.get("status") == 10 and retry_webhook:
                    logger.info("Viber status 10 (webhookNotSet) detected. Auto-setting webhook...")
                    if self._ensure_webhook():
                        return self.send_message(text, retry_webhook=False)
                return False, f"Viber API Error ({resp.get('status')}): {resp.get('status_message')}"
            except Exception as e:
                return False, f"Connection error: {e}"

        # Case 2: Post to Channel using Superadmin ID
        admin_id = self._get_superadmin_id()
        if not admin_id:
            return False, "Could not find Admin ID for Viber channel or invalid token."

        url = "https://chatapi.viber.com/pa/post"
        payload = {
            "from": admin_id,
            "type": "text",
            "text": text,
            "sender": {"name": self.sender_name},
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=12).json()
            if resp.get("status") == 0:
                return True, None
            elif resp.get("status") == 10 and retry_webhook:
                logger.info("Viber status 10 (webhookNotSet) detected. Auto-setting webhook...")
                if self._ensure_webhook():
                    return self.send_message(text, retry_webhook=False)
            return False, f"Viber API Error ({resp.get('status')}): {resp.get('status_message')}"
        except Exception as e:
            return False, f"Connection error: {e}"

    def send_test_message(self, lang: str = "el") -> Tuple[bool, Optional[str]]:
        now_str = (
            time.strftime("%d/%m/%Y %H:%M:%S")
            if lang == "el"
            else time.strftime("%Y-%m-%d %H:%M:%S")
        )
        if lang == "el":
            test_msg = (
                f"⚡ *UPS MONITOR - ΔΟΚΙΜΑΣΤΙΚΗ ΕΙΔΟΠΟΙΗΣΗ*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Ημερομηνία & Ώρα: {now_str}\n"
                f"✅ Η σύνδεση με το Viber API λειτουργεί κανονικά!\n"
                f"🔋 Το σύστημα παρακολούθησης UPS είναι συνδεδεμένο και ενεργό."
            )
        else:
            test_msg = (
                f"⚡ *UPS MONITOR - TEST ALERT*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Date & Time: {now_str}\n"
                f"✅ Viber API connection verified and working!\n"
                f"🔋 UPS monitoring system is online and active."
            )
        return self.send_message(test_msg)
