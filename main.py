import os
import asyncio
import logging
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Вставьте ваш токен от BotFather
BOT_TOKEN = "8905419939:AAH4AhrCIvA6s8TOdeY0CU48etE7lUKjTv0"

# Ссылки
REF_LINK = "https://pocketoption.com/register?utm_source=ref"
SUPPORT_LINK = "https://t.me/your_support"

class AuthState(StatesGroup):
    waiting_for_reg_uid = State()
    waiting_for_email = State()
    waiting_for_password = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- КЛАВИАТУРЫ ---

def get_start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Создать новый аккаунт", callback_data="create_acc")],
            [InlineKeyboardButton(text="🔑 Войти в существующий аккаунт", callback_data="login_acc")],
            [InlineKeyboardButton(text="🌐 Зарегистрироваться самостоятельно ↗", url=REF_LINK)],
            [InlineKeyboardButton(text="📞 Поддержка ↗", url=SUPPORT_LINK)]
        ]
    )

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать торговлю", callback_data="start_trade")],
            [InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit")],
            [InlineKeyboardButton(text="🎯 Настройки", callback_data="settings")],
            [
                InlineKeyboardButton(text="📞 Поддержка ↗", url=SUPPORT_LINK),
                InlineKeyboardButton(text="📕 F.A.Q", callback_data="faq")
            ],
            [InlineKeyboardButton(text="📕 Выйти из аккаунта РО", callback_data="logout")]
        ]
    )

def get_settings_keyboard(risk="2%", martin="Вкл (до 3 плечей)", tf="1 мин"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📊 Риск на сделку: {risk}", callback_data="toggle_risk")],
            [InlineKeyboardButton(text=f"🛡 Мартингейл: {martin}", callback_data="toggle_martin")],
            [InlineKeyboardButton(text=f"⏱ Таймфрейм: {tf}", callback_data="toggle_tf")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def show_main_menu(target, user_data: dict):
    email = user_data.get("email", "user@pocketoption.com")
    uid = user_data.get("uid", str(random.randint(10000000, 99999999)))
    real_bal = user_data.get("real_bal", 0.0)
    demo_bal = user_data.get("demo_bal", 54920.0)

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

    if isinstance(target, types.Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
    elif isinstance(target, types.CallbackQuery):
        await target.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

# --- ХЭНДЛЕРЫ НАЧАЛА И АВТОРИЗАЦИИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "email" in data:
        await show_main_menu(message, data)
        return

    await state.clear()
    user_name = message.from_user.first_name or "трейдер"
    
    caption_text = (
        f"👋 **Привет, {user_name} ⚜️!**\n\n"
        f"Я — торговый бот для Pocket Option.\n\n"
        f"🤖 **Что я умею:**\n"
        f"✅ Торгую автоматически на твоём счёте\n"
        f"✅ Использую мартингейл с защитой до 3 плечей\n"
        f"✅ Работаю 24/7 без участия менеджеров\n\n"
        f"Для начала нужно создать аккаунт на Pocket Option 👈\n\n"
        f"💡 Хотите зарегистрироваться сами?\n"
        f"Перейдите по ссылке 👉 [Регистрация тут]({REF_LINK})"
    )

    await message.answer(
        text=caption_text,
        parse_mode="Markdown",
        reply_markup=get_start_keyboard(),
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == "create_acc")
async def process_create_acc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "🚀 **Создание нового аккаунта**\n\n"
        "1. Зарегистрируйтесь на платформе по ссылке: [Зарегистрироваться]({REF_LINK})\n"
        "2. После регистрации отправьте сюда ваш **UID** (8-значный номер профиля)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Зарегистрироваться ↗", url=REF_LINK)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)
    await state.set_state(AuthState.waiting_for_reg_uid)

@dp.message(AuthState.waiting_for_reg_uid)
async def process_reg_uid(message: types.Message, state: FSMContext):
    uid = message.text.strip()
    email = f"user_{uid}@pocket.option"
    await state.update_data(email=email, uid=uid, real_bal=0.0, demo_bal=54920.0, risk="2%", martin="Вкл (до 3 плечей)", tf="1 мин")
    await message.answer("✅ Аккаунт успешно привязан!")
    data = await state.get_data()
    await show_main_menu(message, data)

@dp.callback_query(F.data == "login_acc")
async def process_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📧 Введите email от Pocket Option:")
    await state.set_state(AuthState.waiting_for_email)

@dp.message(AuthState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await message.answer("🔒 Введите пароль Pocket Option.\nСообщение будет удалено из чата после отправки.")
    await state.set_state(AuthState.waiting_for_password)

@dp.message(AuthState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except Exception:
        pass

    user_data = await state.get_data()
    generated_uid = str(random.randint(10000000, 99999999))
    await state.update_data(
        uid=generated_uid,
        real_bal=0.0,
        demo_bal=54920.0,
        risk="2%",
        martin="Вкл (до 3 плечей)",
        tf="1 мин"
    )

    info_text = (
        "🎮 Демо-режим открывается после первого пополнения реального счёта.\n\n"
        "💳 Пополни реальный счёт — и демо станет доступно."
    )
    await message.answer(info_text, parse_mode="Markdown")
    await asyncio.sleep(2)
    updated_data = await state.get_data()
    await show_main_menu(message, updated_data)

# --- ХЭНДЛЕРЫ ГЛАВНОГО МЕНЮ ---

@dp.callback_query(F.data == "start_trade")
async def process_start_trade(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    real_bal = data.get("real_bal", 0.0)

    if real_bal < 250:
        text = (
            "⚠️ **Недостаточно средств для запуска**\n\n"
            "Для активации автоматической торговли и доступа к демо-режиму минимальный баланс реального счета должен составлять **$250**.\n\n"
            "Пополните счет на платформе и повторите попытку."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить счет ↗", url=REF_LINK)],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await callback.message.edit_text("🚀 **Автоторговля запущена!**\n\nБот анализирует рынок и открывает сделки согласно вашим настройкам.", parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

@dp.callback_query(F.data == "deposit")
async def process_deposit(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "💳 **Пополнение баланса**\n\n"
        "Пополнение происходит непосредственно в вашем личном кабинете Pocket Option.\n"
        "После совершения депозита средства автоматически отобразятся в боте в течение 5 минут."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти к пополнению ↗", url=REF_LINK)],
        [InlineKeyboardButton(text="🔄 Проверить зачисление", callback_data="check_deposit")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "check_deposit")
async def process_check_deposit(callback: types.CallbackQuery):
    await callback.answer("⏳ Платеж не найден. Если вы уже пополнили счет, подождите 2–5 минут.", show_alert=True)

# --- НАСТРОЙКИ ---

@dp.callback_query(F.data == "settings")
async def process_settings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    risk = data.get("risk", "2%")
    martin = data.get("martin", "Вкл (до 3 плечей)")
    tf = data.get("tf", "1 мин")
    
    text = "🎯 **Настройки торгового бота**\n\nВыберите нужный параметр для изменения:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_settings_keyboard(risk, martin, tf))

@dp.callback_query(F.data == "toggle_risk")
async def toggle_risk(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    risks = ["1%", "2%", "5%"]
    curr = data.get("risk", "2%")
    next_risk = risks[(risks.index(curr) + 1) % len(risks)] if curr in risks else "1%"
    await state.update_data(risk=next_risk)
    await callback.answer(f"Риск изменен на {next_risk}")
    
    data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(data.get("risk"), data.get("martin"), data.get("tf")))

@dp.callback_query(F.data == "toggle_martin")
async def toggle_martin(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr = data.get("martin", "Вкл (до 3 плечей)")
    next_m = "Выкл" if "Вкл" in curr else "Вкл (до 3 плечей)"
    await state.update_data(martin=next_m)
    await callback.answer(f"Мартингейл: {next_m}")
    
    data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(data.get("risk"), data.get("martin"), data.get("tf")))

@dp.callback_query(F.data == "toggle_tf")
async def toggle_tf(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tfs = ["1 мин", "3 мин", "5 мин"]
    curr = data.get("tf", "1 мин")
    next_tf = tfs[(tfs.index(curr) + 1) % len(tfs)] if curr in tfs else "1 мин"
    await state.update_data(tf=next_tf)
    await callback.answer(f"Таймфрейм изменен на {next_tf}")
    
    data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(data.get("risk"), data.get("martin"), data.get("tf")))

# --- F.A.Q И ВОЗВРАТЫ ---

@dp.callback_query(F.data == "faq")
async def process_faq(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📕 **Часто задаваемые вопросы (F.A.Q)**\n\n"
        "❓ **Как работает бот?**\n"
        "Бот использует индикаторный анализ и алгоритмы ИИ для определения точек входа.\n\n"
        "❓ **Почему нужен баланс от $250?**\n"
        "Это необходимо для корректной работы рисков и системы Мартингейла (до 3 ступеней).\n\n"
        "❓ **Безопасно ли это для аккаунта?**\n"
        "Бот работает через защищенный шлюз и полностью имитирует действия пользователя."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await show_main_menu(callback, data)

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_start(callback.message, state)

@dp.callback_query(F.data == "logout")
async def process_logout(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Вы вышли из аккаунта", show_alert=True)
    await callback.message.edit_text("Вы успешно вышли из системы. Нажмите /start для входа.")

# --- СЕРВЕР ДЛЯ RENDER ---

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
