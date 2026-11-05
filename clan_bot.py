import asyncio
import datetime
import random
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

async def is_admin(message: Message) -> bool:
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]

def get_lobby_text(chat_id: int) -> str:
    code = team_code_storage.get(chat_id, "Не указан")
    text = f"🔥 **Сбор на катку PUBG Mobile!**\n📌 Код команды (кликни для копирования): `{code}`\n\n"
    for i in range(4):
        if i < len(lobby):
            text += f"{i+1}. [Игрок](tg://user?id={lobby[i]})\n"
        else:
            text += f"{i+1}. Свободно\n"
    text += f"\nМест осталось: {4 - len(lobby)}"
    return text

@dp.chat_member(F.chat.type.in_(["group", "supergroup"]))
async def welcome_new_member(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member" and (event.old_chat_member is None or event.old_chat_member.status in ["left", "kicked"]):
        user = event.new_chat_member.user
        text = f"👋 **Салют, боец {user.full_name}! Добро пожаловать в клан!**\n\n🆔 Напиши команду, чтобы внести свой ID в базу:\n`/reg [твой_ID] [игровой_ник]`"
        await bot.send_message(chat_id=event.chat.id, text=text, parse_mode="Markdown")

@dp.message(Command("help_bot"))
async def cmd_help(message: Message):
    text = (
        "🤖 **Команды бота PUBG Mobile**\n\n"
        "🎮 **Сборы:** `/go [код]`, `/reg [ID] [Ник]`, `/clan`\n"
        "🎰 **Игры:** `/casino`, `/roulette`, `/bj` (21 очко)\n"
        "🛡️ **Админка:** `/mute`, `/unmute`, `/ban`, `/warn`, `/unwarn`"
    )
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("go"))
async def cmd_go(message: Message):
    global lobby
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Укажи код команды! Пример: `/go 309494`")
        return
    team_code_storage[message.chat.id] = args[1]
    lobby = [message.from_user.id] 
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Залететь", callback_query_data="join_lobby"),
        InlineKeyboardButton(text="❌ Выйти", callback_query_data="leave_lobby")
    ]])
    await message.answer(get_lobby_text(message.chat.id), reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "join_lobby")
async def join_lobby(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if callback.from_user.id in lobby:
        await callback.answer("Ты уже в скваде!", show_alert=True)
        return
    if len(lobby) >= 4:
        await callback.answer("Сквад забит!", show_alert=True)
        return
    lobby.append(callback.from_user.id)
    if len(lobby) == 4:
        text = get_lobby_text(chat_id) + "\n\n🚀 **СКВАД СОБРАН! Все в игру!**"
        await callback.message.edit_text(text, parse_mode="Markdown")
    else:
        await callback.message.edit_text(get_lobby_text(chat_id), reply_markup=callback.message.reply_markup, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "leave_lobby")
async def leave_lobby(callback: CallbackQuery):
    if callback.from_user.id not in lobby:
        await callback.answer("Тебя нет в скваде.", show_alert=True)
        return
    lobby.remove(callback.from_user.id)
    await callback.message.edit_text(get_lobby_text(callback.message.chat.id), reply_markup=callback.message.reply_markup, parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("casino"))
async def cmd_casino(message: Message):
    await message.answer_dice(emoji="🎰")

@dp.message(Command("roulette"))
async def cmd_roulette(message: Message):
    res = random.choice(["КРАСНОЕ", "ЧЕРНОЕ", "ЗЕРО"])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Красное", callback_query_data=f"r_red_{res}"),
        InlineKeyboardButton(text="Черное", callback_query_data=f"r_black_{res}")
    ]])
    await message.reply(f"🎰 На что ставишь, {message.from_user.first_name}?", reply_markup=kb)

@dp.callback_query(F.data.startswith("r_"))
async def handle_roulette_bet(callback: CallbackQuery):
    data = callback.data.split("_")
    text = f"🎰 Выпало: **{data[2]}**!\n\n" + ("🎉 Победил!" if data[1] in data[2].lower() else "💩 Продул!")
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("bj"))
async def cmd_blackjack(message: Message):
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    bj_games[message.from_user.id] = {"deck": deck, "user": [deck.pop(), deck.pop()], "bot": [deck.pop(), deck.pop()]}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"),
        InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")
    ]])
    await message.reply(f"🃏 **21 очко**\n\n🤠 Твоя сумма: **{sum(bj_games[message.from_user.id]['user'])}**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bj_"))
async def handle_blackjack(callback: CallbackQuery):
    uid = callback.from_user.id
    if uid not in bj_games:
        return
    game = bj_games[uid]
    if callback.data == "bj_hit":
        game["user"].append(game["deck"].pop())
        score = sum(game["user"])
        if score > 21:
            await callback.message.edit_text(f"💥 Перебор! Сумма: **{score}**\n💩 Ты проиграл!", parse_mode="Markdown")
            del bj_games[uid]
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"), InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")]])
            await callback.message.edit_text(f"🃏 Твоя сумма: **{score}**", reply_markup=kb, parse_mode="Markdown")
    elif callback.data == "bj_stand":
        u_score, b_score = sum(game["user"]), sum(game["bot"])
        while b_score < 17:
            b_score += game["deck"].pop()
        text = f"🛑 Вскрытие! Твоя сумма: **{u_score}**, Бот сумма: **{b_score}**\n\n"
        text += "🏆 Ты выиграл!" if b_score > 21 or u_score > b_score else ("💩 Бот выиграл!" if u_score < b_score else "🤝 Ничья!")
        await callback.message.edit_text(text, parse_mode="Markdown")
        del bj_games[uid]
    await callback.answer()
@dp.message(Command("reg"))
async def cmd_reg(message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Ошибка! Пример: `/reg 5123456789 Ник`", parse_mode="Markdown")
        return
    clan_members[message.from_user.id] = {"id": args[1], "name": " ".join(args[2:]), "tg": message.from_user.full_name}
    await message.reply(f"✅ **Успешно зарегистрирован!**", parse_mode="Markdown")

@dp.message(Command("clan"))
async def cmd_clan(message: Message):
    if not clan_members:
        await message.reply("📭 База пуста.")
        return
    text = "📋 **Список клана:**\n\n"
    for i, data in enumerate(clan_members.values(), 1):
        text += f"{i}. {data['tg']} — Ник: `{data['name']}` | ID: `{data['id']}`\n"
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not message.reply_to_message or not await is_admin(message): return
    args = message.text.split()
    duration = int(args[1]) if len(args) > 1 and args[1].isdigit() else 15
    if duration > 180: duration = 180
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration)
    await message.chat.restrict(user_id=message.reply_to_message.from_user.id, permissions={"can_send_messages": False}, until_date=until)
    await message.answer(f"🤫 Замучен на {duration} мин.")

@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not message.reply_to_message or not await is_admin(message): return
    await message.chat.restrict(user_id=message.reply_to_message.from_user.id, permissions={"can_send_messages": True, "can_send_media_messages": True})
    await message.answer("🔊 Размучен!")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not message.reply_to_message or not await is_admin(message): return
    args = message.text.split()
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
    if days > 7: days = 7
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    await message.chat.ban(user_id=message.reply_to_message.from_user.id, until_date=until)
    await message.answer(f"💥 Забанен на {days} дн.")

@dp.message(Command("warn"))
async def cmd_warn(message: Message):
    if not message.reply_to_message or not await is_admin(message): return
    uid = message.reply_to_message.from_user.id
    warns_db[uid] = warns_db.get(uid, 0) + 1
    if warns_db[uid] >= 3:
        await message.chat.ban(user_id=uid)
        warns_db[uid] = 0
        await message.answer(f"⛔️ {message.reply_to_message.from_user.full_name} получил 3/3 варнов и забанен!")
    else:
        await message.answer(f"⚠️ Варн! [ {warns_db[uid]} / 3 ]")

@dp.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    if not message.reply_to_message or not await is_admin(message): return
    warns_db[message.reply_to_message.from_user.id] = 0
    await message.answer("✅ Варны сброшены.")

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
