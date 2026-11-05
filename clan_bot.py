import asyncio, datetime, random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from aiohttp import web

TOKEN = "8853585706:AAGwxTOc91F21Ys4n2c9GLTkUyL3Zm1t6Dc"
bot = Bot(token=TOKEN)
dp = Dispatcher()

lobby = []
team_code_storage = {}   
warns_db = {}            
moderation_cache = {}    
clan_members = {}
tournament_teams = []
reports_db = {}
balances = {}
custom_titles = {}
case_cooldown = {}

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
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Регайся в базе и лови 100💵:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    text = (
        "🤖 **Команды PUBG Клан-Бота с Кейсами**\n\n"
        "📦 **Ящики и Дроп:**\n"
        "▫️ `/case` — Открыть ежедневный кейс с монетами!\n"
        "▫️ `/balance` — Твой баланс коинов\n"
        "▫️ `/shop` — Купить клановый статус/тег\n"
        "▫️ `/settitle [тег]` — Создать свой тег (500💵)\n\n"
        "🎮 **Сборы и Клан:**\n"
        "▫️ `/go [код]` — Сбор сквада\n"
        "▫️ `/reg [ID] [Ник]` — Регистрация\n"
        "▫️ `/clan` — Таблица участников, балансов и тегов\n"
        "▫️ `/tournament` — Запись на праки\n\n"
        "🛡️ **Фан и Админка:**\n"
        "▫️ `/drop`, `/weapon`, `/meme`, `/report`, `/mute`, `/ban`"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await m.reply(f"💳 Баланс: **{get_bal(m.from_user.id)} Клан-Коинов (💵)**")

@dp.message(Command("case"))
async def cmd_case(m: Message):
    uid = m.from_user.id
    now = datetime.datetime.now()
    if uid in case_cooldown and (now - case_cooldown[uid]).total_seconds() < 86400:
        rem = 86400 - (now - case_cooldown[uid]).total_seconds()
        await m.reply(f"❌ Твой лимит кейсов исчерпан! Новый дроп будет доступен через: **{int(rem//3600)}ч {int((rem%3600)//60)}м**")
        return
        
    case_types = [
        ("📦 Солдатский ящик", 20, 60),
        ("💼 Классический кейс", 60, 150),
        ("🔥 Премиум ящик", 150, 300),
        ("🚀 КЛАНОВЫЙ AIRDROP", 300, 700)
    ]
    weights = [50, 30, 15, 5]
    c_name, min_cash, max_val = random.choices(case_types, weights=weights)[0]
    val = random.randint(min_cash, max_val)
    
    change_bal(uid, val)
    case_cooldown[uid] = now
    await m.reply(f"✈️ Самолёт сбросил тебе ящик...\n\n🎁 Ты открыл **{c_name}**!\n💵 Внутри оказалось: **+{val} Клан-Коинов!**")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    text = (
        "🛒 **Магазин Клан-Тегов PUBG Mobile:**\n\n"
        "1️⃣ Тег `🎯 Снайпер` — **150💵** (`/buy_1`)\n"
        "2️⃣ Тег `🍳 Зажариватель` — **200💵** (`/buy_2`)\n"
        "3️⃣ Тег `🚑 Реаниматор` — **250💵** (`/buy_3`)\n\n"
        "⚙️ Хочешь свой уникальный тег? Напиши:\n`/settitle [Твой_Тег]` (Стоимость: **500💵**)"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("buy_1", "buy_2", "buy_3"))
async def cmd_buy(m: Message):
    uid = m.from_user.id
    t_map = {"buy_1": ("🎯 Снайпер", 150), "buy_2": ("🍳 Зажариватель", 200), "buy_3": ("🚑 Реаниматор", 250)}
    cmd = m.text.replace("/", "").strip()
    if cmd not in t_map: return
    title, price = t_map[cmd]
    if get_bal(uid) < price:
        await m.reply(f"❌ Нужно {price}💵!")
        return
    change_bal(uid, -price)
    custom_titles[uid] = title
    await m.reply(f"🎉 Куплено! Новый тег: **[{title}]**")
@dp.message(Command("settitle"))
async def cmd_settitle(m: Message):
    uid = m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Пример: `/settitle Киберкотлет`")
        return
    new_t = " ".join(args[1:])
    if len(new_t) > 15: return
    if get_bal(uid) < 500:
        await m.reply("❌ Кастомный тег стоит **500💵**!")
        return
    change_bal(uid, -500)
    custom_titles[uid] = new_t
    await m.reply(f"🔥 Установлен тег: **[{new_t}]**")

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
    if c.from_user.id not in lobby: return
    lobby.remove(c.from_user.id)
    await c.message.edit_text(get_lobby_text(c.message.chat.id), reply_markup=c.message.reply_markup, parse_mode="Markdown")
    await c.answer()

@dp.message(Command("tournament"))
async def cmd_tournament(m: Message):
    args = m.text.split()
    if len(args) == 1:
        if not tournament_teams:
            await m.reply("📭 На праки еще никто не зарегился.\nЗапиши свой состав: `/tournament [Название]`")
            return
        text = "🏆 **Зарегистрированные сквады:**\n\n"
        for i, team in enumerate(tournament_teams, 1): text += f"{i}. Team `{team}`\n"
        await m.reply(text, parse_mode="Markdown")
    else:
        team_name = " ".join(args[1:])
        tournament_teams.append(team_name)
        await m.reply(f"✅ Команда `{team_name}` внесена в сетку праков!", parse_mode="Markdown")

@dp.message(Command("drop"))
async def cmd_drop(m: Message):
    await m.reply(f"📍 Высаживаемся в: **{random.choice(['Починки 🏠', 'Школа 🏫', 'Сосновка 🎖'])}**")

@dp.message(Command("weapon"))
async def cmd_weapon(m: Message):
    await m.reply(f"⚔️ Пушка на раунд: **{random.choice(['M416 🔫', 'АКМ 💥', 'AWM 🎯', 'Гроза ⚡️'])}**!")

@dp.message(Command("meme"))
async def cmd_meme(m: Message):
    await m.reply(f"😂 PUBG Мем: {random.choice(['Тиммейт кричит ОН ЛОУ, а у врага броня 3 уровня.', 'Дроп упал на крышу, а внутри маскхалат.'])}")

@dp.message(Command("reg"))
async def cmd_reg(m: Message):
    args = m.text.split()
    if len(args) < 3:
        await m.reply("❌ Пример: `/reg 5123456789 Ник`")
        return
    clan_members[m.from_user.id] = {"id": args[1], "name": " ".join(args[2:]), "tg": m.from_user.full_name}
    await m.reply("✅ Успешно зарегистрирован! Старт баланс 100💵 выдан!")

@dp.message(Command("clan"))
async def cmd_clan(m: Message):
    if not clan_members:
        await m.reply("📭 База пуста.")
        return
    text = "📋 **Список клана:**\n\n"
    for i, (tg_id, data) in enumerate(clan_members.items(), 1):
        t = f" [{custom_titles[tg_id]}]" if tg_id in custom_titles else ""
        text += f"{i}. {data['tg']}{t} — Ник: `{data['name']}` | ID: `{data['id']}` | {get_bal(tg_id)}💵\n"
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("report"))
async def cmd_report(m: Message):
    if not m.reply_to_message: return
    rep_id = random.randint(1000, 9999)
    reports_db[rep_id] = {"target_name": m.reply_to_message.from_user.full_name, "text": m.reply_to_message.text or "Медиа", "date": datetime.datetime.now().strftime("%H:%M")}
    await m.answer(f"🚨 **Жалоба #{rep_id} отправлена!**")

@dp.message(Command("reports"))
async def cmd_view_reports(m: Message):
    if not await is_admin(m) or not reports_db: return
    text = "📂 **Список жалоб:**\n\n"
    for rid, rep in list(reports_db.items()):
        text += f"🆔 Жалоба #{rid}\n👤 Нарушитель: {rep['target_name']}\n📝 Текст: *{rep['text']}*\n➖➖➖➖\n"
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("clear_reports"))
async def cmd_clear_reports(m: Message):
    if not await is_admin(m): return
    global reports_db
    reports_db = {}
    await m.reply("✅ Список жалоб очищен.")

@dp.message(Command("mute"))
async def cmd_mute(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    await m.chat.restrict(user_id=m.reply_to_message.from_user.id, permissions={"can_send_messages": False}, until_date=until)
    await m.answer("🤫 Нарушитель замучен на 15 мин.")

@dp.message(Command("ban"))
async def cmd_ban(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    await m.chat.ban(user_id=m.reply_to_message.from_user.id)
    await m.answer("💥 Бан оформлен!")

async def handle_web(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
