import asyncio, datetime, random, urllib.parse
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
bj_games = {}
clan_members = {}
tournament_teams = []
user_stats = {}

async def is_admin(m: Message) -> bool:
    mem = await m.chat.get_member(m.from_user.id)
    return mem.status in ["administrator", "creator"]

def get_lobby_text(cid: int) -> str:
    c = team_code_storage.get(cid, "Не указан")
    text = f"🔥 **Сбор на катку PUBG Mobile!**\n📌 Код (клик): `{c}`\n\n"
    for i in range(4):
        text += f"{i+1}. [Игрок](tg://user?id={lobby[i]})\n" if i < len(lobby) else f"{i+1}. Свободно\n"
    return text + f"\nМест осталось: {4 - len(lobby)}"

def add_stat(uid: int, name: str):
    if uid not in user_stats: user_stats[uid] = {"name": name, "games": 0}
    user_stats[uid]["games"] += 1

@dp.chat_member(F.chat.type.in_(["group", "supergroup"]))
async def welcome(e: ChatMemberUpdated):
    if e.new_chat_member.status == "member":
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Внеси свой ID в базу:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    text = (
        "🤖 **Все команды PUBG клан-бота**\n\n"
        "| **Сборы и Клан:**\n"
        "▫️ `/go [код]` — Сбор сквада\n"
        "▫️ `/reg [ID] [Ник]` — Регистрация\n"
        "▫️ `/clan` — Список ID клана\n"
        "▫️ `/tournament` — Регистрация на праки\n"
        "▫️ `/shuffleteam` — Поделить лобби на Дуо\n\n"
        "| **Казино и Фан:**\n"
        "▫️ `/casino`, `/roulette`, `/bj` (21 очко)\n"
        "▫️ `/top` — Топ игроков казика\n\n"
        "| **PUBG Фан и Рандом:**\n"
        "▫️ `/drop` — Куда летим? | `/weapon` — Челлендж пушка\n"
        "▫️ `/roll` — 1-100 | `/coin` — Монетка | `/ball [вопрос]` — Шар\n"
        "▫️ `/title` — Твое звание | `/quote` — Цитата | `/meme` — Мем\n"
        "▫️ `/kiss`, `/hug`, `/hit` — Действия | `/music [трек]` — Поиск\n\n"
        "| **Модерация и Безопасность:**\n"
        "▫️ `/rules` — Правила чата\n"
        "▫️ `/report` — Пожаловаться админам\n"
        "▫️ `/mute`, `/unmute`, `/ban`, `/warn`, `/unwarn` — Админка"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("go"))
async def cmd_go(m: Message):
    global lobby
    args = m.text.split()
    if len(args) < 2:
        await m.reply("❌ Укажи код! Пример: `/go 309494`")
        return
    team_code_storage[m.chat.id] = args[1]
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

@dp.message(Command("shuffleteam"))
async def cmd_shuffle(m: Message):
    if len(lobby) < 4:
        await m.reply("❌ В лобби должно быть 4 человека!")
        return
    players = list(lobby)
    random.shuffle(players)
    await m.reply(f"⚔️ **Лобби поделено на Дуо:**\n\n🔵 Команда 1: [Игрок 1](tg://user?id={players[0]}) & [Игрок 2](tg://user?id={players[1]})\n🔴 Команда 2: [Игрок 3](tg://user?id={players[2]}) & [Игрок 4](tg://user?id={players[3]})", parse_mode="Markdown")

@dp.message(Command("casino"))
async def cmd_casino(m: Message):
    add_stat(m.from_user.id, m.from_user.first_name)
    await m.answer_dice(emoji="🎰")

@dp.message(Command("roulette"))
async def cmd_roulette(m: Message):
    add_stat(m.from_user.id, m.from_user.first_name)
    res = random.choice(["red", "black", "zero"])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔴 Красное", callback_query_data=f"r_red_{res}"),
        InlineKeyboardButton(text="⚫ Черное", callback_query_data=f"r_black_{res}")
    ]])
    await m.reply(f"🎰 На что ставишь, {m.from_user.first_name}?", reply_markup=kb)

@dp.callback_query(F.data.startswith("r_"))
async def handle_roulette(c: CallbackQuery):
    data = c.data.split("_")
    user_bet, result = data[1], data[2]
    names = {"red": "🔴 КРАСНОЕ", "black": "⚫ ЧЕРНОЕ", "zero": "🟢 ЗЕРО"}
    text = f"🎰 Выпало: **{names.get(result, result)}**!\n\n" + ("🎉 Выиграл!" if user_bet == result else "💩 Проиграл!")
    await c.message.edit_text(text, parse_mode="Markdown")
    await c.answer()

@dp.message(Command("bj"))
async def cmd_blackjack(m: Message):
    add_stat(m.from_user.id, m.from_user.first_name)
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    bj_games[m.from_user.id] = {"deck": deck, "user": [deck.pop(), deck.pop()], "bot": [deck.pop(), deck.pop()]}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"),
        InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")
    ]])
    await m.reply(f"🃏 **21 очко**\n🤠 Твоя сумма: **{sum(bj_games[m.from_user.id]['user'])}**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bj_"))
async def handle_blackjack(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in bj_games: return
    game = bj_games[uid]
    if c.data == "bj_hit":
        game["user"].append(game["deck"].pop())
        score = sum(game["user"])
        if score > 21:
            await c.message.edit_text(f"💥 Перебор! Сумма: **{score}**\n💩 Ты слил!", parse_mode="Markdown")
            del bj_games[uid]
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"), InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")]])
            await c.message.edit_text(f"🃏 Твоя сумма: **{score}**", reply_markup=kb, parse_mode="Markdown")
    elif c.data == "bj_stand":
        u_score, b_score = sum(game["user"]), sum(game["bot"])
        while b_score < 17: game["bot"].append(game["deck"].pop()); b_score = sum(game["bot"])
        text = f"🛑 Вскрытие! Ты: **{u_score}**, Бот: **{b_score}**\n\n"
        text += "🏆 Победа!" if b_score > 21 or u_score > b_score else ("💩 Проиграл!" if u_score < b_score else "🤝 Ничья!")
        await c.message.edit_text(text, parse_mode="Markdown")
        del bj_games[uid]
    await c.answer()
@dp.message(Command("top"))
async def cmd_top(m: Message):
    if not user_stats:
        await m.reply("🎰 В казик еще никто не играл.")
        return
    sorted_top = sorted(user_stats.values(), key=lambda x: x["games"], reverse=True)[:5]
    text = "👑 **Топ-5 лудоманов клана:**\n\n"
    for i, u in enumerate(sorted_top, 1): text += f"{i}. {u['name']} — сыграно {u['games']} раз\n"
    await m.reply(text)

@dp.message(Command("drop"))
async def cmd_drop(m: Message):
    places = ["Починки 🏠", "Школа 🏫", "Сосновка 🎖", "Георгополь 📦", "Ясная Поляна 🏢", "Приморск ⚓️", "Милта Пауэр 🏭"]
    await m.reply(f"📍 Высаживаемся в: **{random.choice(places)}**")

@dp.message(Command("weapon"))
async def cmd_weapon(m: Message):
    guns = ["M416 🔫", "АКМ 💥", "AWM 🎯", "Гроза ⚡️", "Узи 🕒", "Дробовик S12K 🍳", "Арбалет 🏹"]
    await m.reply(f"⚔️ **Челлендж пушка:** Катай раунд используя только **{random.choice(guns)}**!")

@dp.message(Command("roll"))
async def cmd_roll(m: Message):
    await m.reply(f"🎲 Твое число: **{random.randint(1, 100)}**")

@dp.message(Command("coin"))
async def cmd_coin(m: Message):
    await m.reply(f"🪙 Выпало: **{random.choice(['Орел 🦅', 'Решка 👑'])}**")

@dp.message(Command("ball"))
async def cmd_ball(m: Message):
    ans = ["100% Да! 🏆", "Повезет в катке! 🚀", "Даже не думай 💩", "Шансы 50 на 50 🤝", "Спроси позже 🛑"]
    await m.reply(f"🔮 Шар говорит: **{random.choice(ans)}**")

@dp.message(Command("title"))
async def cmd_title(m: Message):
    titles = ["👑 Клан-Лидер", "🎯 Топ-Снайпер", "🍳 Мастер Сковородки", "📦 Лутатель", "🚑 Реаниматор", "🦧 Главный Токсик", "🤖 Робот Починок"]
    await m.reply(f"🏅 Твое звание в клане: **{random.choice(titles)}**")

@dp.message(Command("quote"))
async def cmd_quote(m: Message):
    quotes = [
        "💬 Не важно, сколько у тебя ХП, важно, сколько патронов в магазине.",
        "💬 Настоящий друг поднимает тебя в синей зоне.",
        "💬 Жизнь как PUBG: ты можешь лутаться полчаса, чтобы отлететь за секунду.",
        "💬 Сковородка за спиной защищает лучше, чем жилет 3-го уровня."
    ]
    await m.reply(random.choice(quotes))

@dp.message(Command("rules"))
async def cmd_rules(m: Message):
    await m.reply("📜 **Правила клана:**\n1. Не токсичить.\n2. Делиться лутом.\n3. Увидел АВМ — отдай снайперу.\n4. Спам = БАН.")

@dp.message(Command("report"))
async def cmd_report(m: Message):
    if not m.reply_to_message: return
    await m.answer("🚨 **ВЫЗОВ АДМИНИСТРАЦИИ!** Нарушитель зафиксирован. Админы, разберитесь!")

@dp.message(Command("kiss"))
async def cmd_kiss(m: Message):
    if m.reply_to_message: await m.answer(f"💋 **{m.from_user.first_name}** поцеловал(а) **{m.reply_to_message.from_user.first_name}**! 🔥")

@dp.message(Command("hug"))
async def cmd_hug(m: Message):
    if m.reply_to_message: await m.answer(f"🤗 **{m.from_user.first_name}** крепко обнял(а) **{m.reply_to_message.from_user.first_name}**! 🚀")

@dp.message(Command("hit"))
async def cmd_hit(m: Message):
    if m.reply_to_message: await m.answer(f"💥 **{m.from_user.first_name}** прописал леща сковородкой **{m.reply_to_message.from_user.first_name}**! 🍳")

@dp.message(Command("music"))
async def cmd_music(m: Message):
    args = m.text.split()
    if len(args) < 2: return
    q = urllib.parse.quote(" ".join(args[1:]))
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎵 Яндекс Музыка", url=f"https://yandex.ru{q}"),
        InlineKeyboardButton(text="📺 YouTube Music", url=f"https://youtube.com{q}")
    ]])
    await m.reply(f"🎧 Трек: `{' '.join(args[1:])}` 👇", reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("meme"))
async def cmd_meme(m: Message):
    memes = [
        "🤖 Нашел пистолет в Починках, а на тебя бежит фулл-сквад с Грозами...",
        "🍳 Тиммейт кричит 'ОН ЛОУ!', ты выбегаешь, а у врага фулл броня 3-го уровня.",
        "📦 Дроп упал на крышу. 10 минут строили пирамиду из УАЗов, а внутри маскхалат.",
        "🏎️ Тиммейт: 'Я знаю короткую дорогу!'. Через 5 секунд вы взрываетесь на Багги."
    ]
    await m.reply(f"😂 **PUBG Клан Мем:**\n\n{random.choice(memes)}")

@dp.message(Command("reg"))
async def cmd_reg(m: Message):
    args = m.text.split()
    if len(args) < 3:
        await m.reply("❌ Ошибка! Пример: `/reg 5123456789 Ник`", parse_mode="Markdown")
        return
    clan_members[m.from_user.id] = {"id": args[1], "name": " ".join(args[2:]), "tg": m.from_user.full_name}
    await m.reply(f"✅ **Успешно зарегистрирован!**", parse_mode="Markdown")

@dp.message(Command("clan"))
async def cmd_clan(m: Message):
    if not clan_members:
        await m.reply("📭 База пуста.")
        return
    text = "📋 **Список клана:**\n\n"
    for i, data in enumerate(clan_members.values(), 1):
        text += f"{i}. {data['tg']} — Ник: `{data['name']}` | ID: `{data['id']}`\n"
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("mute"))
async def cmd_mute(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    args = m.text.split()
    duration = int(args[1]) if len(args) > 1 and args[1].isdigit() else 15
    if duration > 180: duration = 180
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration)
    await m.chat.restrict(user_id=m.reply_to_message.from_user.id, permissions={"can_send_messages": False}, until_date=until)
    await m.answer(f"🤫 Замучен на {duration} мин.")

@dp.message(Command("unmute"))
async def cmd_unmute(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    await m.chat.restrict(user_id=m.reply_to_message.from_user.id, permissions={"can_send_messages": True, "can_send_media_messages": True})
    await m.answer("🔊 Размучен!")

@dp.message(Command("ban"))
async def cmd_ban(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    args = m.text.split()
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
    if days > 7: days = 7
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    await m.chat.ban(user_id=m.reply_to_message.from_user.id, until_date=until)
    await m.answer(f"💥 Забанен на {days} дн.")

@dp.message(Command("warn"))
async def cmd_warn(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    uid = m.reply_to_message.from_user.id
    warns_db[uid] = warns_db.get(uid, 0) + 1
    if warns_db[uid] >= 3:
        await m.chat.ban(user_id=uid)
        warns_db[uid] = 0
        await m.answer(f"⛔️ {m.reply_to_message.from_user.full_name} получил 3/3 варнов и забанен!")
    else:
        await m.answer(f"⚠️ Варн! [ {warns_db[uid]} / 3 ]")

@dp.message(Command("unwarn"))
async def cmd_unwarn(m: Message):
    if not m.reply_to_message or not await is_admin(m): return
    warns_db[m.reply_to_message.from_user.id] = 0
    await m.answer("✅ Варны сброшены.")

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
