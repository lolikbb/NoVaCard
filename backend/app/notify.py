import httpx
from .config import BOT_TOKEN


async def notify_user_paid(order):
    text = (
        f"✅ <b>Оплата получена!</b>\n\n"
        f"🛍 Товар: {order.product.title}\n"
        f"💰 Сумма: {order.amount} {order.asset}\n\n"
    )
    if order.delivered_content:
        text += f"🔑 Ваш товар:\n<code>{order.delivered_content}</code>"
    else:
        text += "Мы скоро свяжемся с вами по поводу выдачи товара."

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": order.user.tg_id, "text": text, "parse_mode": "HTML"},
        )