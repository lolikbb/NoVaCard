import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class Support(StatesGroup):
    waiting = State()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть Nova Card",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(text="💬 Написать в поддержку", callback_data="support")]
    ])


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в Nova Card</b>\n\n"
    "Выпускай виртуальные крипто-карты для оплаты в интернете "
    "и переводов в сети за секунды.\n\n"
    "🔒 Безопасно · ⚡ Мгновенно · 🌍 Без границ\n\n"
    "Нажми кнопку ниже, чтобы открыть приложение 👇"
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "support")
async def support_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "✍️ Опиши свою проблему одним сообщением — мы ответим как можно скорее.",
        reply_markup=cancel_kb()
    )
    await state.set_state(Support.waiting)
    await call.answer()


@dp.message(Support.waiting, F.text == "❌ Отмена")
async def support_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


@dp.message(Support.waiting)
async def support_forward(message: Message, state: FSMContext):
    user = message.from_user
    text = (
        f"📩 <b>Новое обращение в поддержку</b>\n"
        f"👤 {user.full_name} (@{user.username or '—'})\n"
        f"🆔 <code>{user.id}</code>\n\n"
        f"{message.text}"
    )
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено! Мы ответим в этот чат.",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


# Ответ админа пользователю: reply на пересланное сообщение вида "🆔 <id>"
@dp.message(F.reply_to_message, F.from_user.id == ADMIN_ID)
async def admin_reply(message: Message):
    original = message.reply_to_message.text or ""
    marker = "🆔 "
    if marker not in original:
        return
    try:
        user_id = int(original.split(marker)[1].split()[0].strip("</code>").replace("<code>", ""))
    except Exception:
        return
    await bot.send_message(user_id, f"💬 <b>Ответ поддержки:</b>\n\n{message.text}", parse_mode="HTML")
    await message.answer("✅ Отправлено пользователю")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())