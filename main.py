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

# Токен бота
BOT_TOKEN = "8905419939:AAH4AhrCIvA6s8TOdeY0CU48etE7lUKjTv0"

# Telegram ID основателей
ADMIN_IDS = [6941597273]

REF_LINK = "https://pocketoption.com/register?utm_source=ref"
SUPPORT_LINK = "https://t.me/your_support"

# Пресеты стратегий
PRESETS = {
    "precision": {
        "title": "🎯 Precision Strike",
        "desc": "Максимальная агрессия, короткая экспирация",
        "stop": 3, "cycles": 5, "tf": "1 мин", "delay": 1.2
    },
    "high_profit": {
        "title": "⚡️ High-Profit",
        "desc": "Расширенная лестница, ставка на серию",
        "stop": 5, "cycles": 10, "tf": "5 мин", "delay": 2.5
    },
    "balanced": {
        "title": "📊 Balanced",
        "desc": "Баланс риска и частоты входов",
        "stop": 4, "cycles": 10, "tf": "5 мин", "delay": 2.0
    },
    "conservative": {
        "title": "🛡 Conservative",
        "desc": "Минимальная просадка, для малых депозитов",
        "stop": 3, "cycles": 10, "tf": "1 мин", "delay": 1.8
    }
}

class AuthState(StatesGroup):
    waiting_for_reg_uid = State()
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_custom_amount = State()

class TradeState(StatesGroup):
    trading_active = State()

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

def get_main_menu_keyboard(is_admin: bool = False):
    kb = [
        [InlineKeyboardButton(text="🚀 Начать торговлю", callback_data="select_account_type")],
        [InlineKeyboardButton(text="📊 Стратегии торговли", callback_data="strategies")],
        [InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton(text="🎯 Настройки", callback_data="settings")],
        [
            InlineKeyboardButton(text="📞 Поддержка ↗", url=SUPPORT_LINK),
            InlineKeyboardButton(text="📕 F.A.Q", callback_data="faq")
        ]
    ]
    if is_admin:
        kb.append([InlineKeyboardButton(text="👑 Панель Основателя", callback_data="admin_panel")])
        
    kb.append([InlineKeyboardButton(text="📕 Выйти из аккаунта РО", callback_data="logout")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_strategies_keyboard(active_preset="high_profit", custom_mode=False):
    kb = []
    for key, p in PRESETS.items():
        is_active = (key == active_preset and not custom_mode)
        status = "🔴 АКТИВЕН" if is_active else "⚪️ Выбрать"
        kb.append([InlineKeyboardButton(text=f"{p['title']} [{status}]", callback_data=f"set_preset_{key}")])

    custom_status = "🟢 ВКЛ" if custom_mode else "⚪️ ВЫКЛ"
    kb.append([InlineKeyboardButton(text=f"⚙️ Ручные настройки [{custom_status}]", callback_data="custom_settings")])
    kb.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_custom_settings_keyboard(stop=5, cycles=10, tf="5 мин"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Стоп: {stop} мин", callback_data="set_custom_stop"),
                InlineKeyboardButton(text=f"Циклы: {cycles}", callback_data="set_custom_cycles"),
                InlineKeyboardButton(text=f"ТФ: {tf}", callback_data="set_custom_tf")
            ],
            [InlineKeyboardButton(text="⬅️ К стратегиям", callback_data="strategies")]
        ]
    )

def get_settings_keyboard(lang="🇷🇺 Русский", martin="Вкл (до 3 плечей)", tf="1 мин"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🌐 Язык / Language: {lang}", callback_data="toggle_lang")],
            [InlineKeyboardButton(text=f"🛡 Мартингейл: {martin}", callback_data="toggle_martin")],
            [InlineKeyboardButton(text=f"⏱ Таймфрейм: {tf}", callback_data="toggle_tf")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика пользователей", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⚡ Выдать себе $250+ (Для теста)", callback_data="admin_add_funds")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )

def get_account_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎮 Демо счёт", callback_data="acc_demo"),
                InlineKeyboardButton(text="💰 Реальный счёт", callback_data="acc_real")
            ],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")]
        ]
    )

def get_trade_amount_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="$10", callback_data="set_amount_10"),
                InlineKeyboardButton(text="$20", callback_data="set_amount_20"),
                InlineKeyboardButton(text="$50", callback_data="set_amount_50"),
                InlineKeyboardButton(text="$100", callback_data="set_amount_100")
            ],
            [
                InlineKeyboardButton(text="$200", callback_data="set_amount_200"),
                InlineKeyboardButton(text="$500", callback_data="set_amount_500"),
                InlineKeyboardButton(text="$1000", callback_data="set_amount_1000")
            ],
            [
                InlineKeyboardButton(text="0.5%", callback_data="set_amount_0.5%"),
                InlineKeyboardButton(text="1%", callback_data="set_amount_1%"),
                InlineKeyboardButton(text="1.5%", callback_data="set_amount_1.5%"),
                InlineKeyboardButton(text="2%", callback_data="set_amount_2%"),
                InlineKeyboardButton(text="⚠️ 3%", callback_data="set_amount_3%")
            ],
            [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="set_custom_amount")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")]
        ]
    )

# --- ВЫВОД МЕНЮ ---

async def show_main_menu(target, user_data: dict, user_id: int):
    email = user_data.get("email", "user@pocketoption.com")
    uid = user_data.get("uid", str(random.randint(10000000, 99999999)))
    real_bal = user_data.get("real_bal", 0.0)
    demo_bal = user_data.get("demo_bal", 54920.0)
    is_admin = user_id in ADMIN_IDS

    status_badge = "👑 Founder" if is_admin else "🥉 Bronze"

    text = (
        "📱 **Главное меню**\n\n"
        f"📧 **Почта:**\n`{email}`\n\n"
        f"🆔 **UID профиля:**\n`{uid}`\n\n"
        f"💰 **СТАТИСТИКА РЕАЛЬНОГО СЧЁТА**\n"
        f"💵 Баланс: {real_bal:.2f} USD\n"
        f"📊 Открыто сделок: 0 | Прибыль: 0.00\n\n"
        f"🎮 **СТАТИСТИКА ДЕМО СЧЁТА**\n"
        f"💵 Баланс: {demo_bal:,.2f} USD\n"
        f"📊 Открыто сделок: 0 | Прибыль: 0.00\n\n"
        f"🏆 **Статус:** {status_badge}"
    )

    reply_markup = get_main_menu_keyboard(is_admin=is_admin)

    if isinstance(target, types.Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif isinstance(target, types.CallbackQuery):
        await target.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# --- ХЭНДЛЕРЫ СТАРТА И АВТОРИЗАЦИИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "email" in data:
        await show_main_menu(message, data, message.from_user.id)
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

    await message.answer(text=caption_text, parse_mode="Markdown", reply_markup=get_start_keyboard(), disable_web_page_preview=True)

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
    await state.update_data(email=email, uid=uid, real_bal=0.0, demo_bal=54920.0, lang="🇷🇺 Русский", martin="Вкл (до 3 плечей)", tf="1 мин", active_preset="high_profit", custom_mode=False, custom_stop=5, custom_cycles=10, custom_tf="5 мин")
    await message.answer("✅ Аккаунт успешно привязан!")
    data = await state.get_data()
    await show_main_menu(message, data, message.from_user.id)

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

    generated_uid = str(random.randint(10000000, 99999999))
    user_data = await state.get_data()
    email = user_data.get("email", f"user_{generated_uid}@pocket.option")

    await state.update_data(email=email, uid=generated_uid, real_bal=0.0, demo_bal=54920.0, lang="🇷🇺 Русский", martin="Вкл (до 3 плечей)", tf="1 мин", active_preset="high_profit", custom_mode=False, custom_stop=5, custom_cycles=10, custom_tf="5 мин")
    await message.answer("🎮 Демо-режим открывается после первого пополнения реального счёта.\n\n💳 Пополни реальный счёт — и демо станет доступно.", parse_mode="Markdown")
    await asyncio.sleep(2)
    updated_data = await state.get_data()
    await show_main_menu(message, updated_data, message.from_user.id)

# --- ЛОГИКА СТРАТЕГИЙ И ПРЕСЕТОВ ---

@dp.callback_query(F.data == "strategies")
async def process_strategies(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    active_preset = data.get("active_preset", "high_profit")
    custom_mode = data.get("custom_mode", False)

    if custom_mode:
        stop = data.get("custom_stop", 5)
        cycles = data.get("custom_cycles", 10)
        tf = data.get("custom_tf", "5 мин")
        status_text = f"⚙️ **Ручной режим**\nСтоп: {stop} минусов | Циклов: {cycles} | Экспирация: {tf}"
    else:
        p = PRESETS.get(active_preset, PRESETS["high_profit"])
        status_text = f"**{p['title']}**\n_{p['desc']}_\nСтоп: {p['stop']} минусов | Циклов: {p['cycles']} | Экспирация: {p['tf']}"

    text = f"📊 **Настройки и стратегии торговли**\n\nCurrent Config:\n{status_text}\n\nВыберите пресет или настройте вручную:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_strategies_keyboard(active_preset, custom_mode))

@dp.callback_query(F.data.startswith("set_preset_"))
async def process_set_preset(callback: types.CallbackQuery, state: FSMContext):
    preset_key = callback.data.replace("set_preset_", "")
    await state.update_data(active_preset=preset_key, custom_mode=False)
    p = PRESETS.get(preset_key, PRESETS["high_profit"])
    await callback.answer(f"Активирована стратегия: {p['title']}")
    await process_strategies(callback, state)

@dp.callback_query(F.data == "custom_settings")
async def process_custom_settings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(custom_mode=True)
    data = await state.get_data()
    stop = data.get("custom_stop", 5)
    cycles = data.get("custom_cycles", 10)
    tf = data.get("custom_tf", "5 мин")

    text = "⚙️ **Ручные настройки параметров**\n\nНастройте параметры индивидуально:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_custom_settings_keyboard(stop, cycles, tf))

@dp.callback_query(F.data == "set_custom_stop")
async def toggle_custom_stop(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    stops = [3, 4, 5]
    curr = data.get("custom_stop", 5)
    next_s = stops[(stops.index(curr) + 1) % len(stops)] if curr in stops else 3
    await state.update_data(custom_stop=next_s)
    await callback.answer(f"Стоп: {next_s} минусов")
    await process_custom_settings(callback, state)

@dp.callback_query(F.data == "set_custom_cycles")
async def toggle_custom_cycles(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cycles_list = [5, 10, 15]
    curr = data.get("custom_cycles", 10)
    next_c = cycles_list[(cycles_list.index(curr) + 1) % len(cycles_list)] if curr in cycles_list else 5
    await state.update_data(custom_cycles=next_c)
    await callback.answer(f"Макс. циклов: {next_c}")
    await process_custom_settings(callback, state)

@dp.callback_query(F.data == "set_custom_tf")
async def toggle_custom_tf(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tfs = ["1 мин", "5 мин", "15 мин"]
    curr = data.get("custom_tf", "5 мин")
    next_tf = tfs[(tfs.index(curr) + 1) % len(tfs)] if curr in tfs else "1 мин"
    await state.update_data(custom_tf=next_tf)
    await callback.answer(f"Экспирация: {next_tf}")
    await process_custom_settings(callback, state)

# --- ЛОГИКА ТОРГОВОЙ СЕССИИ (ВОРОНКА) ---

@dp.callback_query(F.data == "select_account_type")
async def process_select_account_type(callback: types.CallbackQuery):
    await callback.answer()
    text = "❓ **Где торговать?**\n\nВыберите тип счёта для запуска автоматической сессии:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_account_type_keyboard())

@dp.callback_query(F.data.in_({"acc_demo", "acc_real"}))
async def process_account_choice(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    acc_type = "real" if callback.data == "acc_real" else "demo"
    await state.update_data(selected_acc_type=acc_type)
    
    data = await state.get_data()
    real_bal = data.get("real_bal", 0.0)
    is_admin = callback.from_user.id in ADMIN_IDS

    if acc_type == "real" and not is_admin and real_bal < 250:
        text = (
            "⚠️ **Недостаточно средств для запуска**\n\n"
            "Для активации автоматической торговли на реальном счете минимальный баланс должен составлять **$250**.\n\n"
            "Пополните счет на платформе и повторите попытку."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить счет ↗", url=REF_LINK)],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    text = "🎯 **Сумма сделки:**\n\nВыберите фиксированную сумму или процент от баланса:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_trade_amount_keyboard())

@dp.callback_query(F.data.startswith("set_amount_"))
async def process_set_amount(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    val = callback.data.replace("set_amount_", "")
    await state.update_data(trade_amount=val)
    await start_trading_session(callback, state)

@dp.callback_query(F.data == "set_custom_amount")
async def process_set_custom_amount(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✏️ Введите сумму сделки в USD (числом):")
    await state.set_state(AuthState.waiting_for_custom_amount)

@dp.message(AuthState.waiting_for_custom_amount)
async def process_custom_amount_input(message: types.Message, state: FSMContext):
    amount_text = message.text.strip().replace("$", "")
    if not amount_text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите корректное число.")
        return

    await state.update_data(trade_amount=f"${amount_text}")
    msg = await message.answer("⚙️ Инициализация торговой сессии...")
    
    class FakeCallback:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
        async def answer(self): pass

    fake_cb = FakeCallback(msg, message.from_user)
    await start_trading_session(fake_cb, state)

async def start_trading_session(callback, state: FSMContext):
    await state.set_state(TradeState.trading_active)
    data = await state.get_data()
    amount = data.get("trade_amount", "$50")
    acc_type = data.get("selected_acc_type", "demo")
    
    # Считываем активные параметры стратегии
    custom_mode = data.get("custom_mode", False)
    if custom_mode:
        cycles_count = data.get("custom_cycles", 5)
        delay_time = 1.8
    else:
        active_preset = data.get("active_preset", "high_profit")
        preset_info = PRESETS.get(active_preset, PRESETS["high_profit"])
        cycles_count = preset_info["cycles"]
        delay_time = preset_info["delay"]

    bal_key = "real_bal" if acc_type == "real" else "demo_bal"
    current_bal = data.get(bal_key, 54920.0)

    pairs = ["EUR/USD OTC", "EUR/CHF OTC", "GBP/USD OTC", "USD/JPY OTC", "EUR/GBP OTC", "USD/EGP OTC"]
    session_profit = 0.0
    history_lines = []

    stop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏸ Остановить и посмотреть результат", callback_data="stop_session")]
    ])

    for i in range(1, cycles_count + 1):
        current_state = await state.get_state()
        if current_state != TradeState.trading_active.state:
            break

        pair = random.choice(pairs)
        is_win = random.choices([True, False], weights=[75, 25])[0]
        
        try:
            stake = float(amount.replace("$", "").replace("%", ""))
        except ValueError:
            stake = 50.0

        if is_win:
            profit = round(stake * random.uniform(0.8, 0.92), 2)
            session_profit += profit
            current_bal += profit
            history_lines.append(f"✅ {pair} +${profit:.2f} USD")
        else:
            loss = stake
            session_profit -= loss
            current_bal -= loss
            history_lines.append(f"❌ {pair} -${loss:.2f} USD")

        await state.update_data({bal_key: current_bal})

        history_text = "\n".join(history_lines)
        text = (
            "☕️ **Торговля активна**\n\n"
            f"🎯 **Сумма сделки:** {amount}\n\n"
            f"{history_text}\n\n"
            f"💰 **Баланс:** ${current_bal:,.2f} USD"
        )

        try:
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=stop_kb)
        except Exception:
            pass

        await asyncio.sleep(delay_time)

    await finish_trading_session(callback, state, session_profit, current_bal)

@dp.callback_query(F.data == "stop_session")
async def process_stop_session(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Останавливаем сессию...")
    await state.set_state(None)

async def finish_trading_session(callback, state: FSMContext, profit: float = 0.0, final_bal: float = 0.0):
    await state.set_state(None)
    
    if final_bal == 0.0:
        data = await state.get_data()
        acc_type = data.get("selected_acc_type", "demo")
        final_bal = data.get("real_bal" if acc_type == "real" else "demo_bal", 54920.0)

    sign = "+" if profit >= 0 else ""
    text = (
        "⏸ **Сессия остановлена**\n\n"
        f"🎯 **Результат:** {sign}${profit:,.2f} USD\n"
        f"💰 **Баланс:** ${final_bal:,.2f} USD\n\n"
        "👇 **Выбери следующий шаг:**"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️▶️ Запустить снова", callback_data="select_account_type")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            [InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_LINK)]
        ]
    )

    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)

# --- НАСТРОЙКИ (ЯЗЫК, МАРТИНГЕЙЛ, ТАЙМФРЕЙМ) ---

@dp.callback_query(F.data == "settings")
async def process_settings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", "🇷🇺 Русский")
    martin = data.get("martin", "Вкл (до 3 плечей)")
    tf = data.get("tf", "1 мин")
    
    text = "🎯 **Настройки торгового бота**\n\nВыберите параметр для изменения:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_settings_keyboard(lang, martin, tf))

@dp.callback_query(F.data == "toggle_lang")
async def toggle_lang(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr_lang = data.get("lang", "🇷🇺 Русский")
    next_lang = "🇬🇧 English" if curr_lang == "🇷🇺 Русский" else "🇷🇺 Русский"
    await state.update_data(lang=next_lang)
    await callback.answer(f"Язык изменен на: {next_lang}")
    updated_data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(updated_data.get("lang"), updated_data.get("martin"), updated_data.get("tf")))

@dp.callback_query(F.data == "toggle_martin")
async def toggle_martin(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr = data.get("martin", "Вкл (до 3 плечей)")
    next_m = "Выкл" if "Вкл" in curr else "Вкл (до 3 плечей)"
    await state.update_data(martin=next_m)
    await callback.answer(f"Мартингейл: {next_m}")
    updated_data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(updated_data.get("lang"), updated_data.get("martin"), updated_data.get("tf")))

@dp.callback_query(F.data == "toggle_tf")
async def toggle_tf(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tfs = ["1 мин", "3 мин", "5 мин"]
    curr = data.get("tf", "1 мин")
    next_tf = tfs[(tfs.index(curr) + 1) % len(tfs)] if curr in tfs else "1 мин"
    await state.update_data(tf=next_tf)
    await callback.answer(f"Таймфрейм: {next_tf}")
    updated_data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(updated_data.get("lang"), updated_data.get("martin"), updated_data.get("tf")))

# --- ПАНЕЛЬ ОСНОВАТЕЛЯ ---

@dp.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет доступа к этой панели.", show_alert=True)
        return
        
    await callback.answer()
    text = "👑 **Панель Управления Основателя**\n\nДобро пожаловать в админ-центр управления ботом."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.answer("Все системы работают в штатном режиме. Всего подключено пользователей: 1", show_alert=True)

@dp.callback_query(F.data == "admin_add_funds")
async def process_admin_add_funds(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    await state.update_data(real_bal=500.0)
    await callback.answer("✅ Вам успешно зачислено $500.00 на реальный баланс!", show_alert=True)
    data = await state.get_data()
    await show_main_menu(callback, data, callback.from_user.id)

# --- ДРУГИЕ ХЭНДЛЕРЫ ---

@dp.callback_query(F.data == "deposit")
async def process_deposit(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "💳 **Пополнение баланса**\n\n"
        "Пополнение происходит непосредственно в вашем личном кабинете Pocket Option.\n"
        "После депозита средства отобразятся в боте в течение 5 минут."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти к пополнению ↗", url=REF_LINK)],
        [InlineKeyboardButton(text="🔄 Проверить зачисление", callback_data="check_deposit")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "check_deposit")
async def process_check_deposit(callback: types.CallbackQuery):
    await callback.answer("⏳ Платеж не найден. Подождите 2–5 минут.", show_alert=True)

@dp.callback_query(F.data == "faq")
async def process_faq(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📕 **Часто задаваемые вопросы (F.A.Q)**\n\n"
        "❓ **Как работает бот?**\n"
        "Бот использует индикаторный анализ и алгоритмы ИИ.\n\n"
        "❓ **Почему нужен баланс от $250?**\n"
        "Это необходимо для корректной работы рисков и системы Мартингейла.\n\n"
        "❓ **Безопасно ли это для аккаунта?**\n"
        "Бот работает через защищенный шлюз и имитирует действия пользователя."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(None)
    data = await state.get_data()
    await show_main_menu(callback, data, callback.from_user.id)

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_start(callback.message, state)

@dp.callback_query(F.data == "logout")
async def process_logout(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Вы вышли из аккаунта", show_alert=True)
    await callback.message.edit_text("Вы успешно вышли из системы. Нажмите /start для входа.")

# --- ВЕБ-СЕРВЕР RENDER ---

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
