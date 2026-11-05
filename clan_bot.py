import asyncio
import datetime
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.client.telegram import TelegramAPIServer

TOKEN = "8853585706:AAGwxTOc91F21Ys4n2c9GLTkUyL3Zm1t6Dc"

local_server = TelegramAPIServer.from_base("https://telegram-proxy.org")
bot = Bot(token=TOKEN, server=local_server)
dp = Dispatcher()

lobby = []
team_code_storage = {}   
warns_db = {}            
moderation_cache = {}    
bj_games = {}

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

@dp.message(Command("help_bot"))
async def cmd_help(message: Message):
    text = (
        "🤖 **Команды бота PUBG Mobile**\n\n"
        "🎮 **Сборы:** `/go [код]`\n"
        "🎰 **Игры:** `/casino`, `/roulette`, `/bj` (21 очко)\n"
        "🛡️ **Админка (в ответ на сообщение):** `/mute`, `/unmute`, `/ban`, `/warn`, `/unwarn`"
    )
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("go"))
async def cmd_go(message: Message):
    global lobby
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Укажи код команды из PUBG!\nПример: `/go 309494`", parse_mode="Markdown")
        return
    code = args[1]
    chat_id = message.chat.id
    team_code_storage[chat_id] = code
    lobby = [message.from_user.id] 
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Залететь", callback_query_data="join_lobby"),
        InlineKeyboardButton(text="❌ Выйти", callback_query_data="leave_lobby")
    ]])
    await message.answer(get_lobby_text(chat_id), reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "join_lobby")
async def join_lobby(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    if user_id in lobby:
        await callback.answer("Ты уже в скваде!", show_alert=True)
        return
    if len(lobby) >= 4:
        await callback.answer("Сквад забит!", show_alert=True)
        return
    lobby.append(user_id)
    if len(lobby) == 4:
        text = get_lobby_text(chat_id) + "\n\n🚀 **СКВАД СОБРАН! Все в игру!**"
        tags = " ".join([f"[⚡](tg://user?id={uid})" for uid in lobby])
        await callback.message.edit_text(text, parse_mode="Markdown")
        await callback.message.answer(f"📢 Сквад готов: {tags}", parse_mode="Markdown")
    else:
        await callback.message.edit_text(get_lobby_text(chat_id), reply_markup=callback.message.reply_markup, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "leave_lobby")
async def leave_lobby(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    if user_id not in lobby:
        await callback.answer("Тебя нет в скваде.", show_alert=True)
        return
    lobby.remove(user_id)
    await callback.message.edit_text(get_lobby_text(chat_id), reply_markup=callback.message.reply_markup, parse_mode="Markdown")
    await callback.answer("Ты вышел.")

@dp.message(Command("casino"))
async def cmd_casino(message: Message):
    await message.answer_dice(emoji="🎰")

@dp.message(Command("roulette"))
async def cmd_roulette(message: Message):
    options = ["🔴 КРАСНОЕ", "⚫️ ЧЕРНОЕ", "🟢 ЗЕРО"]
    result = random.choices(options, weights=[48, 48, 4])[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Красное", callback_query_data=f"r_red_{result}"),
        InlineKeyboardButton(text="Черное", callback_query_data=f"r_black_{result}")
    ]])
    await message.reply(f"🎰 Ставки приняты! На что ставишь, {message.from_user.first_name}?", reply_markup=kb)

@dp.callback_query(F.data.startswith("r_"))
async def handle_roulette_bet(callback: CallbackQuery):
    data = callback.data.split("_")
    user_choice = data[1]
    result = data[2]
    text = f"🎰 Выпало: **{result}**!\n\n"
    if (user_choice == "red" and "КРАСНОЕ" in result) or (user_choice == "black" and "ЧЕРНОЕ" in result):
        text += "🎉 Победил!"
    else:
        text += "💩 Продул!"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("bj"))
async def cmd_blackjack(message: Message):
    user_id = message.from_user.id
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    user_hand = [deck.pop(), deck.pop()]
    bot_hand = [deck.pop(), deck.pop()]
    bj_games[user_id] = {"deck": deck, "user": user_hand, "bot": bot_hand}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"),
        InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")
    ]])
    await message.reply(f"🃏 **21 очко**\n\n🤠 Твои карты: {user_hand} (Сумма: **{sum(user_hand)}**)\n🤖 Карта бота: [{bot_hand[0]}, ?]", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bj_"))
async def handle_blackjack(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data
    if user_id not in bj_games:
        await callback.answer("Начни заново через /bj", show_alert=True)
        return
    game = bj_games[user_id]
    if action == "bj_hit":
        game["user"].append(game["deck"].pop())
        user_score = sum(game["user"])
        if user_score > 21:
            await callback.message.edit_text(f"💥 Перебор! Твои карты: {game['user']} (Сумма: **{user_score}**)\n💩 Ты проиграл!", parse_mode="Markdown")
            del bj_games[user_id]
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Карту", callback_query_data="bj_hit"), InlineKeyboardButton(text="🛑 Вскрыться", callback_query_data="bj_stand")]])
            await callback.message.edit_text(f"🃏 Твои карты: {game['user']} (Сумма: **{user_score}**)\n🤖 Бот: [{game['bot'][0]}, ?]", reply_markup=kb, parse_mode="Markdown")
    elif action == "bj_stand":
        user_score = sum(game["user"])
        bot_score = sum(game["bot"])
        while bot_score < 17:
            bot_score += game["deck"].pop()
        text = f"🛑 Вскрытие! Твоя сумма: **{user_score}**, Бот сумма: **{bot_score}**\n\n"
        if bot_score > 21 or user_score > bot_score:
            text += "🏆 Ты выиграл!"
        elif user_score < bot_score:
            text += "💩 Бот выиграл!"
        else:
            text += "🤝 Ничья!"
        await callback.message.edit_text(text, parse_mode="Markdown")
        del bj_games[user_id]
    await callback.answer()
@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение нарушителя!")
        return
    if not await is_admin(message):
        return
    target_user = message.reply_to_message.from_user
    args = message.text.split()
    if len(args) == 1:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏳ 15м", callback_query_data="m_15"), InlineKeyboardButton(text="⏳ 60м", callback_query_data="m_60"), InlineKeyboardButton(text="🛑 180м", callback_query_data="m_180")]])
        msg = await message.reply(f"🤐 Время мута для {target_user.full_name}?", reply_markup=kb)
        moderation_cache[msg.message_id] = target_user.id
        return
    if len(args) > 1 and args[1].isdigit():
        duration = int(args[1])
        if duration > 180:
            duration = 180
        until_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration)
        try:
            await message.chat.restrict(user_id=target_user.id, permissions={"can_send_messages": False, "can_send_media_messages": False}, until_date=until_date)
            await message.answer(f"🤫 {target_user.full_name} замучен на {duration} мин.")
        except Exception as e:
            await message.reply(f"⚠️ Ошибка: {e}")

@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not message.reply_to_message or not await is_admin(message):
        return
    target_user = message.reply_to_message.from_user
    try:
        await message.chat.restrict(user_id=target_user.id, permissions={"can_send_messages": True, "can_send_media_messages": True, "can_send_other_messages": True, "can_add_web_page_previews": True})
        await message.answer(f"🔊 {target_user.full_name} размучен!")
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not message.reply_to_message or not await is_admin(message):
        return
    target_user = message.reply_to_message.from_user
    args = message.text.split()
    if len(args) == 1:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔨 1 день", callback_query_data="b_1"), InlineKeyboardButton(text="🔨 7 дней", callback_query_data="b_7"), InlineKeyboardButton(text="☠️ Пермач", callback_query_data="b_0")]])
        msg = await message.reply(f"🔨 Срок бана для {target_user.full_name}?", reply_markup=kb)
        moderation_cache[msg.message_id] = target_user.id
        return
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
        if days > 7:
            days = 7
        until_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
        try:
            await message.chat.ban(user_id=target_user.id, until_date=until_date)
            await message.answer(f"💥 {target_user.full_name} забанен на {days} дн.")
        except Exception as e:
            await message.reply(f"⚠️ Ошибка: {e}")

@dp.callback_query(F.data.startswith("m_") | F.data.startswith("b_"))
async def handle_moderation_buttons(callback: CallbackQuery):
    if not await is_admin(callback.message):
        return
    msg_id = callback.message.message_id
    target_user_id = moderation_cache.get(msg_id)
    if not target_user_id:
        return
    action_type = callback.data.split("_")[0]
    value = int(callback.data.split("_")[2] if action_type == "r" else callback.data.split("_")[1])
    try:
        member_info = await callback.message.chat.get_member(target_user_id)
        user_name = member_info.user.full_name
    except Exception:
        user_name = "Игрок"
    if action_type == "m":
        until_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=value)
        try:
            await callback.message.chat.restrict(user_id=target_user_id, permissions={"can_send_messages": False, "can_send_media_messages": False}, until_date=until_date)
            await callback.message.edit_text(f"🤫 {user_name} замучен на {value} мин.")
        except Exception:
            pass
    elif action_type == "b":
        if value == 0:
            try:
                await callback.message.chat.ban(user_id=target_user_id)
                await callback.message.edit_text(f"💥 {user_name} забанен НАВСЕГДА!")
            except Exception:
                pass
        else:
            until_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=value)
            try:
                await callback.message.chat.ban(user_id=target_user_id, until_date=until_date)
                await callback.message.edit_text(f"💥 {user_name} забанен на {value} дн.")
            except Exception:
                pass
    if msg_id in moderation_cache:
        del moderation_cache[msg_id]
    await callback.answer()

@dp.message(Command("warn"))
async def cmd_warn(message: Message):
    if not message.reply_to_message or not await is_admin(message):
        return
    target_user = message.reply_to_message.from_user
    user_id = target_user.id
    warns_db[user_id] = warns_db.get(user_id, 0) + 1
    current_warns = warns_db[user_id]
    if current_warns >= 3:
        try:
            await message.chat.ban(user_id=user_id)
            warns_db[user_id] = 0
            await message.answer(f"⛔️ {target_user.full_name} получил 3/3 варнов и забанен!")
        except Exception:
            pass
    else:
        await message.answer(f"⚠️ {target_user.full_name} получил предупреждение! [ {current_warns} / 3 ]")

@dp.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    if not message.reply_to_message or not await is_admin(message):
        return
    target_user = message.reply_to_message.from_user
    warns_db[target_user.id] = 0
    await message.answer(f"✅ Варны игрока {target_user.full_name} сброшены.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
