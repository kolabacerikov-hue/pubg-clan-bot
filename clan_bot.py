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
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Регайся в базе и лови 100💵:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    text = (
        "🤖 **Команды Клан-Бот Экономика**\n\n"
        "💳 **Профиль:** `/balance`, `/bonus`, `/shop`, `/settitle [тег]`\n"
        "🎮 **Сборы:** `/go [код]`, `/reg [ID] [Ник]`, `/clan`, `/tournament`\n"
        "🎰 **Игры:** `/casino`, `/roulette [ставка]`, `/bj [ставка]`, `/duel`\n"
        "🎲 **Фан:** `/drop`, `/weapon`, `/kiss`, `/hug`, `/hit`, `/meme`, `/music [трек]`\n"
        "🛡️ **Админка:** `/report`, `/reports`, `/clear_reports`, `/mute`, `/ban`"
    )
    await m.reply(text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await m.reply(f"💳 Баланс: **{get_bal(m.from_user.id)}💵**")

@dp.message(Command("bonus"))
async def cmd_bonus(m: Message):
    uid = m.from_user.id
    now = datetime.datetime.now()
    if uid in bonus_cooldown and (now - bonus_cooldown[uid]).total_seconds() < 86400:
        rem = 86400 - (now - bonus_cooldown[uid]).total_seconds()
        await m.reply(f"❌ Бонус уже забран! Жди: **{int(rem//3600)}ч {int((rem%3600)//60)}м**")
        return
    val = random.randint(50, 150)
    change_bal(uid, val)
    bonus_cooldown[uid] = now
    await m.reply(f"🎉 Зачислено **{val}💵** бонуса!")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    text = (
        "🛒 **Магазин Клан-Тегов:**\n\n"
        "1️⃣ Тег `🎯 Снайпер` — **150💵** (`/buy_1`)\n"
        "2️⃣ Тег `🍳 Зажариватель` — **200💵** (`/buy_2`)\n"
        "3️⃣ Тег `🚑 Реаниматор` — **250💵** (`/buy_3`)\n\n"
        "⚙️ Свой уникальный тег: `/settitle [Тег]` (**500💵**)"
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

@dp.message(Command("casino"))
async def cmd_casino(m: Message):
    uid = m.from_user.id
    if get_bal(uid) < 20:
        await m.reply("❌ Стоимость прокрута слота — **20💵**. У тебя не хватает!")
        return
    change_bal(uid, -20)
    msg = await m.answer_dice(emoji="🎰")
    await asyncio.sleep(2)
    if msg.dice.value == 64:
        change_bal(uid, 300)
        await m.reply("🎉 ДЖЕКПОТ! Семерки! Ты выиграл **300💵**! 🏆")
    elif msg.dice.value in:
        change_bal(uid, 50)
        await m.reply("💰 Вин! Две фигурки совпали. Держи **50💵**!")
    else:
        await m.reply("💩 Лут пустой! Ты проиграл.")

@dp.message(Command("roulette"))
async def cmd_roulette(m: Message):
    uid = m.from_user.id
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await m.reply("❌ Напиши ставку! Пример: `/roulette 50`")
        return
    bet = int(args[1])
    if bet <= 0 or get_bal(uid) < bet:
        await m.reply("❌ Некорректная ставка!")
        return
    res = random.choice(["red", "black", "zero"])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔴 Красное", callback_query_data=f"r_red_{res}_{bet}"),
        InlineKeyboardButton(text="⚫ Черное", callback_query_data=f"r_black_{res}_{bet}")
    ]])
    await m.reply(f"🎰 Ставка **{bet}💵** принята! На что ставишь?", reply_markup=kb)

@dp.callback_query(F.data.startswith("r_"))
async def handle_roulette(c: CallbackQuery):
    data = c.data.split("_")
    user_bet, result, bet = data[1], data[2], int(data[3])
    uid = c.from_user.id
    names = {"red": "🔴 КРАСНОЕ", "black": "⚫ ЧЕРНОЕ", "zero": "🟢 ЗЕРО"}
    if user_bet == result:
        change_bal(uid, bet)
        text = f"🎰 Выпало: **{names[result]}**!\n\n🎉 Угадал! Ты выиграл **+{bet}💵**!"
    else:
        change_bal(uid, -bet)
        text = f"🎰 Выпало: **{names[result]}**!\n\n💩 Продул! Ты потерял **-{bet}💵**."
    await c.message.edit_text(text, parse_mode="Markdown")
    await c.answer()

@dp.message(Command("bj"))
async def cmd_blackjack(m: Message):
    uid = m.from_user.id
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await m.reply("❌ Пример: `/bj 40`")
        return
    bet = int(args[1])
    if bet <= 0 or get_bal(uid) < bet: 
        await m.reply("❌ Ошибка баланса или ставки!")
        return
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11] * 4
    random.shuffle(deck)
    bj_games[uid] = {"deck": deck, "user": [deck.pop(), deck.pop()], "bot": [deck.pop(), deck.pop()], "bet": bet}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"),
        InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")
    ]])
    await m.reply(f"🃏 **21 очко на {bet}💵**\n🤠 Твоя сумма: **{sum(bj_games[uid]['user'])}**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bj_"))
async def handle_blackjack(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in bj_games: return
    game = bj_games[uid]
    bet = game["bet"]
    if c.data == "bj_hit":
        game["user"].append(game["deck"].pop())
        score = sum(game["user"])
        if score > 21:
            change_bal(uid, -bet)
            await c.message.edit_text(f"💥 Перебор! Сумма: **{score}**\n💩 Проиграл **-{bet}💵**!", parse_mode="Markdown")
            del bj_games[uid]
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"),
                InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")
            ]])
            await c.message.edit_text(f"🃏 Твоя сумма: **{score}**", reply_markup=kb, parse_mode="Markdown")
    elif c.data == "bj_stand":
        u_score, b_score = sum(game["user"]), sum(game["bot"])
        while b_score < 17: game["bot"].append(game["deck"].pop()); b_score = sum(game["bot"])
        text = f"🛑 Вскрытие! Ты: **{u_score}**, Бот: **{b_score}**\n\n"
        if b_score > 21 or u_score > b_score:
            change_bal(uid, bet)
            text += f"🏆 Победа! **+{bet}💵**!"
        elif u_score < b_score:
            change_bal(uid, -bet)
            text += f"💩 Проиграл **-{bet}💵**."
        else:
            text += "🤝 Ничья!"
        await c.message.edit_text(text, parse_mode="Markdown")
        del bj_games[uid]
    await c.answer()

@dp.message(Command("duel"))
async def cmd_duel(m: Message):
    if not m.reply_to_message: return
    p1, p2 = m.from_user, m.reply_to_message.from_user
    if get_bal(p1.id) < 50 or get_bal(p2.id) < 50:
        await m.reply("❌ Нужно минимум 50💵 у каждого!")
        return
    win, los = random.choice([(p1, p2), (p2, p1)])
    change_bal(win.id, 50); change_bal(los.id, -50)
    await m.answer(f"🎯 **ДУЭЛЬ НА 50💵!**\n💥 Хедшот оформляет **{win.first_name}**! Забирает куш у **{los.first_name}**! 🏆")

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
    await m.reply("✅ Успешно зарегистрирован! Стартовый баланс 100💵 выдан!")

@dp.message(Command("clan"))
async def cmd_clan(m: Message):
    if not clan_members:
        await m.reply("📭 База пуста.")
        return
    text = "📋 **Список клана:**\n\n"
    for i, (tg_id, data) in enumerate(clan_members.items(), 1):
        t = f" [{custom_titles[tg_id]}]" if tg_id in custom_titles else ""
        text += f"{i}. {data['tg']}{t} — Ник: `{data['name']}` | ID: `{data['id']}` | Баланс: {get_bal(tg_id)}💵\n"
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
