import asyncio, datetime, random, urllib.parse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from aiohttp import web

TOKEN = "8853585706:AAGwxTOc91F21Ys4n2c9GLTkUyL3Zm1t6Dc"
bot = Bot(token=TOKEN)
dp = Dispatcher()

lobby =
team_code_storage = {}   
warns_db = {}            
moderation_cache = {}    
bj_games = {}
clan_members = {}
tournament_teams =
reports_db = {}
balances = {}
custom_titles = {}
bonus_cooldown = {}

async def is_admin(m: Message) -> bool:
    mem = await m.chat.get_member(m.from_user.id)
    return mem.status in ["administrator", "creator"]

def get_lobby_text(cid: int) -> str:
    c = team_code_storage.get(cid, "Не указан")
    text = f"🔥 **Сбор на катку PUBG Mobile!**\n📌 Код (клик): `{c}`\n\n"
    for i in range(4):
        text += f"{i+1}. [Игрок](tg://user?id={lobby[i]})\n" if i < len(lobby) else f"{i+1}. Свободно\n"
    return text + f"\nМест осталось: {4 - len(lobby)}"

def get_bal(uid: int) -> int:
    return balances.get(uid, 100)

def change_bal(uid: int, amount: int):
    balances[uid] = get_bal(uid) + amount

@dp.chat_member(F.chat.type.in_(["group", "supergroup"]))
async def welcome(e: ChatMemberUpdated):
    if e.new_chat_member.status == "member":
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Внеси свой ID в базу и получи 100💵:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    text = (
        "🤖 **Команды Клан-Бот Экономика**\n\n"
        "💳 **Экономика и Профиль:**\n"
        "▫️ `/balance` — Твой баланс коинов\n"
        "▫️ `/bonus` — Забрать ежедневные 💵\n"
        "▫️ `/shop` — Купить клановый статус/тег\n"
        "▫️ `/settitle [тег]` — Создать свой тег (500💵)\n\n"
        "🎮 **Сборы и Клан:**\n"
        "▫️ `/go [код]` — Сбор сквада\n"
        "▫️ `/reg [ID] [Ник]` — Регистрация\n"
        "▫️ `/clan` — Таблица участников и тегов\n\n"
        "🎰 **Казино на Коины:**\n"
        "▫️ `/casino` — Слот (Ставка 20💵)\n"
        "▫️ `/roulette [ставка]` — Рулетка (на Красное/Черное)\n"
        "▫️ `/bj [ставка]` — Блэкджек (21 очко)\n\n"
        "🎭 **Фан и Модерация:**\n"
        "▫️ `/duel`, `/meme`, `/drop`, `/weapon`\n"
        "▫️ `/report`, `/reports`, `/mute`, `/ban`"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await m.reply(f"💳 Твой баланс: **{get_bal(m.from_user.id)} Клан-Коинов (💵)**")

@dp.message(Command("bonus"))
async def cmd_bonus(m: Message):
    uid = m.from_user.id
    now = datetime.datetime.now()
    if uid in bonus_cooldown and (now - bonus_cooldown[uid]).total_seconds() < 86400:
        rem = 86400 - (now - bonus_cooldown[uid]).total_seconds()
        await m.reply(f"❌ Ты уже забирал бонус! До следующего осталось: **{int(rem//3600)}ч {int((rem%3600)//60)}м**")
        return
    val = random.randint(50, 150)
    change_bal(uid, val)
    bonus_cooldown[uid] = now
    await m.reply(f"🎉 Ты забрал ежедневный бонус! На твой счет зачислено **{val}💵**!")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    text = (
        "🛒 **Магазин Клан-Тегов PUBG Mobile:**\n\n"
        "1️⃣ Тег `🎯 Снайпер` — **150💵** (`/buy_1`)\n"
        "2️⃣ Тег `🍳 Зажариватель` — **200💵** (`/buy_2`)\n"
        "3️⃣ Тег `🚑 Реаниматор` — **250💵** (`/buy_3`)\n\n"
        "⚙️ Хочешь **свой уникальный тег**? Напиши:\n`/settitle [Твой_Тег]` (Стоимость: **500💵**)"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("buy_1", "buy_2", "buy_3"))
async def cmd_buy(m: Message):
    uid = m.from_user.id
    t_map = {"buy_1": ("🎯 Снайпер", 150), "buy_2": ("🍳 Зажариватель", 200), "buy_3": ("🚑 Реаниматор", 250)}
    cmd = m.text.split()[0].replace("/", "")
    title, price = t_map[cmd]
    if get_bal(uid) < price:
        await m.reply(f"❌ Недостаточно Клан-Коинов! Требуется {price}💵.")
        return
    change_bal(uid, -price)
    custom_titles[uid] = title
    await m.reply(f"🎉 Успешно куплено! Твой новый тег: **[{title}]**")

@dp.message(Command("settitle"))
async def cmd_settitle(m: Message):
    uid = m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Напиши тег! Пример: `/settitle Киберкотлет`")
        return
    new_t = " ".join(args[1:])
    if len(new_t) > 15:
        await m.reply("❌ Слишком длинный теag! Максимум 15 символов.")
        return
    if get_bal(uid) < 500:
        await m.reply("❌ Создание кастомного тега стоит **500💵**! У тебя не хватает.")
        return
    change_bal(uid, -500)
    custom_titles[uid] = new_t
    await m.reply(f"🔥 **Уникальный тег создан!** Теперь ты отображаешься как: **[{new_t}]**")

@dp.message(Command("go"))
async def cmd_go(m: Message):
    global lobby
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Укажи код! Пример: `/go 309494`")
        return
    team_code_storage[m.chat.id] = args
    lobby = [m.from_user.id] 
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Залететь", callback_query_data="join_lobby"),
        InlineKeyboardButton(text="❌ Выйти", callback_query_data="leave_lobby")
    ]])
    await m.answer(get_lobby_text(m.chat.id), reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "join_lobby")
async def join_lobby(c: CallbackQuery):
    cid = c.message.chat.id
    if c.from_user.id in lobby:
        await c.answer("Ты уже в скваде!", show_alert=True)
        return
    if len(lobby) >= 4:
        await c.answer("Сквад забит!", show_alert=True)
        return
    lobby.append(c.from_user.id)
    if len(lobby) == 4:
        await c.message.edit_text(get_lobby_text(cid) + "\n\n🚀 **СКВАД СОБРАН!**", parse_mode="Markdown")
    else:
        await c.message.edit_text(get_lobby_text(cid), reply_markup=c.message.reply_markup, parse_mode="Markdown")
    await c.answer()

@dp.callback_query(F.data == "leave_lobby")
async def leave_lobby(c: CallbackQuery):
    if c.from_user.id not in lobby:
        await c.answer("Тебя нет в скваде.", show_alert=True)
        return
    lobby.remove(c.from_user.id)
    await c.message.edit_text(get_lobby_text(c.message.chat.id), reply_markup=c.message.reply_markup, parse_mode="Markdown")
    await c.answer()
import asyncio, datetime, random, urllib.parse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from aiohttp import web

TOKEN = "8853585706:AAGwxTOc91F21Ys4n2c9GLTkUyL3Zm1t6Dc"
bot = Bot(token=TOKEN)
dp = Dispatcher()

lobby =
team_code_storage = {}   
warns_db = {}            
moderation_cache = {}    
bj_games = {}
clan_members = {}
tournament_teams =
reports_db = {}
balances = {}
custom_titles = {}
bonus_cooldown = {}

async def is_admin(m: Message) -> bool:
    mem = await m.chat.get_member(m.from_user.id)
    return mem.status in ["administrator", "creator"]

def get_lobby_text(cid: int) -> str:
    c = team_code_storage.get(cid, "Не указан")
    text = f"🔥 **Сбор на катку PUBG Mobile!**\n📌 Код (клик): `{c}`\n\n"
    for i in range(4):
        text += f"{i+1}. [Игрок](tg://user?id={lobby[i]})\n" if i < len(lobby) else f"{i+1}. Свободно\n"
    return text + f"\nМест осталось: {4 - len(lobby)}"

def get_bal(uid: int) -> int:
    return balances.get(uid, 100)

def change_bal(uid: int, amount: int):
    balances[uid] = get_bal(uid) + amount

@dp.chat_member(F.chat.type.in_(["group", "supergroup"]))
async def welcome(e: ChatMemberUpdated):
    if e.new_chat_member.status == "member":
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Внеси свой ID в базу и получи 100💵:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    text = (
        "🤖 **Команды Клан-Бот Экономика**\n\n"
        "💳 **Экономика и Профиль:**\n"
        "▫️ `/balance` — Твой баланс коинов\n"
        "▫️ `/bonus` — Забрать ежедневные 💵\n"
        "▫️ `/shop` — Купить клановый статус/тег\n"
        "▫️ `/settitle [тег]` — Создать свой тег (500💵)\n\n"
        "🎮 **Сборы и Клан:**\n"
        "▫️ `/go [код]` — Сбор сквада\n"
        "▫️ `/reg [ID] [Ник]` — Регистрация\n"
        "▫️ `/clan` — Таблица участников и тегов\n\n"
        "🎰 **Казино на Коины:**\n"
        "▫️ `/casino` — Слот (Ставка 20💵)\n"
        "▫️ `/roulette [ставка]` — Рулетка (на Красное/Черное)\n"
        "▫️ `/bj [ставка]` — Блэкджек (21 очко)\n\n"
        "🎭 **Фан и Модерация:**\n"
        "▫️ `/duel`, `/meme`, `/drop`, `/weapon`\n"
        "▫️ `/report`, `/reports`, `/mute`, `/ban`"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await m.reply(f"💳 Твой баланс: **{get_bal(m.from_user.id)} Клан-Коинов (💵)**")

@dp.message(Command("bonus"))
async def cmd_bonus(m: Message):
    uid = m.from_user.id
    now = datetime.datetime.now()
    if uid in bonus_cooldown and (now - bonus_cooldown[uid]).total_seconds() < 86400:
        rem = 86400 - (now - bonus_cooldown[uid]).total_seconds()
        await m.reply(f"❌ Ты уже забирал бонус! До следующего осталось: **{int(rem//3600)}ч {int((rem%3600)//60)}м**")
        return
    val = random.randint(50, 150)
    change_bal(uid, val)
    bonus_cooldown[uid] = now
    await m.reply(f"🎉 Ты забрал ежедневный бонус! На твой счет зачислено **{val}💵**!")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    text = (
        "🛒 **Магазин Клан-Тегов PUBG Mobile:**\n\n"
        "1️⃣ Тег `🎯 Снайпер` — **150💵** (`/buy_1`)\n"
        "2️⃣ Тег `🍳 Зажариватель` — **200💵** (`/buy_2`)\n"
        "3️⃣ Тег `🚑 Реаниматор` — **250💵** (`/buy_3`)\n\n"
        "⚙️ Хочешь **свой уникальный тег**? Напиши:\n`/settitle [Твой_Тег]` (Стоимость: **500💵**)"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("buy_1", "buy_2", "buy_3"))
async def cmd_buy(m: Message):
    uid = m.from_user.id
    t_map = {"buy_1": ("🎯 Снайпер", 150), "buy_2": ("🍳 Зажариватель", 200), "buy_3": ("🚑 Реаниматор", 250)}
    cmd = m.text.split()[0].replace("/", "")
    title, price = t_map[cmd]
    if get_bal(uid) < price:
        await m.reply(f"❌ Недостаточно Клан-Коинов! Требуется {price}💵.")
        return
    change_bal(uid, -price)
    custom_titles[uid] = title
    await m.reply(f"🎉 Успешно куплено! Твой новый тег: **[{title}]**")

@dp.message(Command("settitle"))
async def cmd_settitle(m: Message):
    uid = m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Напиши тег! Пример: `/settitle Киберкотлет`")
        return
    new_t = " ".join(args[1:])
    if len(new_t) > 15:
        await m.reply("❌ Слишком длинный теag! Максимум 15 символов.")
        return
    if get_bal(uid) < 500:
        await m.reply("❌ Создание кастомного тега стоит **500💵**! У тебя не хватает.")
        return
    change_bal(uid, -500)
    custom_titles[uid] = new_t
    await m.reply(f"🔥 **Уникальный тег создан!** Теперь ты отображаешься как: **[{new_t}]**")

@dp.message(Command("go"))
async def cmd_go(m: Message):
    global lobby
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Укажи код! Пример: `/go 309494`")
        return
    team_code_storage[m.chat.id] = args
    lobby = [m.from_user.id] 
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Залететь", callback_query_data="join_lobby"),
        InlineKeyboardButton(text="❌ Выйти", callback_query_data="leave_lobby")
    ]])
    await m.answer(get_lobby_text(m.chat.id), reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "join_lobby")
async def join_lobby(c: CallbackQuery):
    cid = c.message.chat.id
    if c.from_user.id in lobby:
        await c.answer("Ты уже в скваде!", show_alert=True)
        return
    if len(lobby) >= 4:
        await c.answer("Сквад забит!", show_alert=True)
        return
    lobby.append(c.from_user.id)
    if len(lobby) == 4:
        await c.message.edit_text(get_lobby_text(cid) + "\n\n🚀 **СКВАД СОБРАН!**", parse_mode="Markdown")
    else:
        await c.message.edit_text(get_lobby_text(cid), reply_markup=c.message.reply_markup, parse_mode="Markdown")
    await c.answer()

@dp.callback_query(F.data == "leave_lobby")
async def leave_lobby(c: CallbackQuery):
    if c.from_user.id not in lobby:
        await c.answer("Тебя нет в скваде.", show_alert=True)
        return
    lobby.remove(c.from_user.id)
    await c.message.edit_text(get_lobby_text(c.message.chat.id), reply_markup=c.message.reply_markup, parse_mode="Markdown")
    await c.answer()
