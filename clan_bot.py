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
bj_games = {}
clan_members = {}

async def is_admin(m: Message) -> bool:
    mem = await m.chat.get_member(m.from_user.id)
    return mem.status in ["administrator", "creator"]

def get_lobby_text(cid: int) -> str:
    c = team_code_storage.get(cid, "Не указан")
    text = f"🔥 **Сбор на катку PUBG Mobile!**\n📌 Код: `{c}`\n\n"
    for i in range(4):
        text += f"{i+1}. [Игрок](tg://user?id={lobby[i]})\n" if i < len(lobby) else f"{i+1}. Свободно\n"
    return text + f"\nМест осталось: {4 - len(lobby)}"

@dp.chat_member(F.chat.type.in_(["group", "supergroup"]))
async def welcome(e: ChatMemberUpdated):
    if e.new_chat_member.status == "member":
        await bot.send_message(e.chat.id, f"👋 **Салют, {e.new_chat_member.user.full_name}!**\n🆔 Внеси свой ID в базу:\n`/reg [ID] [Ник]`", parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(m: Message):
    await m.reply("🤖 **Команды бота**\n🎮 `/go [код]`, `/reg [ID] [Ник]`, `/clan`\n🎰 `/casino`, `/roulette`, `/bj` (21)\n🛡️ `/mute`, `/unmute`, `/ban`, `/warn`, `/unwarn` ")

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

@dp.message(Command("casino"))
async def cmd_casino(m: Message):
    await m.answer_dice(emoji="🎰")

@dp.message(Command("roulette"))
async def cmd_roulette(m: Message):
    res = random.choice(["red", "black", "zero"])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔴 Красное", callback_query_data=f"r_red_{res}"),
        InlineKeyboardButton(text="⚫ Черное", callback_query_data=f"r_black_{res}")
    ]])
    await m.reply(f"🎰 На что ставишь, {m.from_user.first_name}?", reply_markup=kb)

@dp.callback_query(F.data.startswith("r_"))
async def handle_roulette(c: CallbackQuery):
    data = c.data.split("_")
    user_bet = data[1]
    result = data[2]
    text = f"🎰 Выпало: **{result.upper()}**!\n\n" + ("🎉 Выиграл!" if user_bet == result else "💩 Проиграл!")
    await c.message.edit_text(text, parse_mode="Markdown")
    await c.answer()

@dp.message(Command("bj"))
async def cmd_blackjack(m: Message):
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
