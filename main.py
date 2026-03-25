import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json'
}

# Очки по рейтингу
STATS = {
    1: {"chance": 50, "score": 1000},
    2: {"chance": 30, "score": 3000},
    3: {"chance": 12, "score": 5000},
    4: {"chance": 6, "score": 8000},
    5: {"chance": 2, "score": 10000}
}

POSITIONS_LIST = ["🧤 ГК", "🛡 ЛЗ", "🛡 ПЗ", "👟 ЦП", "⚡️ ЛВ", "⚡️ ПВ", "🎯 КФ"]

# --- СИСТЕМА БД ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key == 'cards' else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return [] if key == 'cards' else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загрузка данных
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
cooldowns = {}

# --- КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "🏟 Арена")
    markup.row("🏆 Топ очков", "🔝 Топ карт")
    
    chat_info = bot.get_chat(uid)
    if chat_info.username and chat_info.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

# --- РЕГИСТРАЦИЯ ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(message.chat.id, "👋 **Добро пожаловать в FootCard!**\n\nВведи свой **игровой ник** для регистрации:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, register_nick)
    else:
        bot.send_message(message.chat.id, f"⚽️ С возвращением, **{users_data[uid]['nick']}**!", reply_markup=main_kb(uid), parse_mode="Markdown")

def register_nick(message):
    uid = str(message.from_user.id)
    nick = message.text
    users_data[uid] = {"nick": nick, "score": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Ник **{nick}** успешно сохранен!", reply_markup=main_kb(uid), parse_mode="Markdown")

# --- КРУТКА ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(message):
    uid = str(message.from_user.id)
    now = time.time()
    
    if uid not in users_data: return start(message)

    # Проверка на КД (5 минут)
    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    if uid in cooldowns and now - cooldowns[uid] < 300 and not is_admin:
        left = int(300 - (now - cooldowns[uid]))
        return bot.send_message(message.chat.id, f"⏳ **Бутсы ещё сохнут!**\nПодожди еще: `{left // 60}м {left % 60}с`", parse_mode="Markdown")

    if not cards: return bot.send_message(message.chat.id, "⚠️ В игре пока нет созданных карточек.")

    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc:
            stars = s
            break

    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    status = "повторка" if is_dub else "новая карта"
    pts = STATS[won['stars']]['score']
    
    if not is_dub:
        user_colls[uid].append(won)
        users_data[uid]['score'] += pts
        save_db(user_colls, 'colls')
        save_db(users_data, 'users')

    # ОФОРМЛЕНИЕ КАРТОЧКИ
    user_nick = users_data[uid]['nick']
    
    cap = (
        f"🏃‍♂️ **{won['name']} ({status})**\n"
        f"👤 Владелец: **{user_nick}**\n\n"
        f"╔════════════════════╗\n"
        f"  📊 **ИНФО:**\n"
        f"  ├ Позиция: **{won.get('pos', 'Не указана')}**\n"
        f"  ├ Рейтинг: **{'⭐' * won['stars']}**\n"
        f"  └ Очки:    **+{pts:,}**\n"
        f"╚════════════════════╝\n\n"
        f"💰 Твой баланс: **{users_data[uid]['score']:,}**"
    )
    
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- ТОПЫ ---
@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_score(message):
    sorted_users = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ ПО ОЧКАМ:**\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        txt += f"{i}. **{data['nick']}** — `{data['score']:,}`\n"
    bot.send_message(message.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔝 Топ карт")
def top_cards_list(message):
    sorted_colls = sorted(user_colls.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    txt = "🔝 **ЛИДЕРЫ ПО КОЛЛЕКЦИИ:**\n\n"
    for i, (uid, coll) in enumerate(sorted_colls, 1):
        nick = users_data.get(uid, {}).get('nick', 'Аноним')
        txt += f"{i}. **{nick}** — `{len(coll)}` карт\n"
    bot.send_message(message.chat.id, txt, parse_mode="Markdown")

# --- СОСТАВ ---
def get_sq_kb(uid):
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        n = sq[i]['name'] if sq[i] else "⚠️ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {n}", callback_data=f"sl_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_view(m):
    bot.send_message(m.chat.id, "📋 **Твой основной состав:**", reply_markup=get_sq_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("sl_"))
def slot_choose(call):
    idx = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"st_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"st_{idx}_none"))
    bot.edit_message_text("Выбери игрока (дубликаты запрещены):", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("st_"))
def slot_update(call):
    _, idx, name = call.data.split("_"); idx = int(idx); uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        if any(s['name'] == name for s in user_squads[uid] if s and user_squads[uid].index(s) != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже на другой позиции!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else:
        user_squads[uid][idx] = None
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав успешно обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_start(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "🗑 Удалить карту", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Режим администратора:**", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_1(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Введите имя игрока:")
        bot.register_next_step_handler(msg, add_2)

def add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите позицию для **{name}**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, add_3, name)

def add_3(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Введите рейтинг (1-5 звезд):")
    bot.register_next_step_handler(msg, add_4, name, pos)

def add_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте фото игрока:")
        bot.register_next_step_handler(msg, add_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "Ошибка! Введите число от 1 до 5.")

def add_fin(m, name, pos, stars):
    if not m.photo: return bot.send_message(m.chat.id, "Это не фото! Попробуй снова.")
    global cards
    cards = [c for c in cards if c['name'] != name]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта **{name}** успешно добавлена в базу!", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def go_back(m):
    bot.send_message(m.chat.id, "Возвращаемся в главное меню...", reply_markup=main_kb(m.from_user.id))

# --- КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⭐", callback_data="v_1"), types.InlineKeyboardButton("⭐⭐", callback_data="v_2"))
    kb.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="v_3"), types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="v_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="v_5"))
    bot.send_message(m.chat.id, "🔍 Выберите редкость для просмотра:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def coll_view(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == s]
    if not my: return bot.answer_callback_query(call.id, "У тебя еще нет таких карт!")
    txt = f"🗂 **ТВОИ КАРТЫ {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c.get('pos', '???')})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

bot.infinity_polling()
