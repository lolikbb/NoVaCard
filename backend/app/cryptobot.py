import hashlib
import hmac
import httpx

from .config import CRYPTOPAY_TOKEN, CRYPTOPAY_API

HEADERS = {"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN}


async def create_invoice(amount: float, asset: str, description: str, payload: str, paid_btn_url: str = None):
    data = {
        "asset": asset,
        "amount": str(amount),
        "description": description[:1024],
        "payload": payload,
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 1800,
    }
    if paid_btn_url:
        data["paid_btn_name"] = "callback"
        data["paid_btn_url"] = paid_btn_url

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{CRYPTOPAY_API}/createInvoice", data=data, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("ok"):
            raise Exception(result)
        return result["result"]


async def get_invoice(invoice_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CRYPTOPAY_API}/getInvoices",
            params={"invoice_ids": invoice_id},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("result", {}).get("items", [])
        return items[0] if items else None


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = hashlib.sha256(CRYPTOPAY_TOKEN.encode()).digest()
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)