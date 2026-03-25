import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json'
}

COOLDOWN_TIME = 10800 

STATS = {
    1: {"chance": 50, "score": 1000},
    2: {"chance": 30, "score": 3000},
    3: {"chance": 12, "score": 5000},
    4: {"chance": 6, "score": 8000},
    5: {"chance": 2, "score": 10000}
}

POSITIONS_LIST = ["🧤 ГК", "🛡 ЛЗ", "🛡 ПЗ", "👟 ЦП", "⚡️ ЛВ", "⚡️ ПВ", "🎯 КФ"]

# --- [2] РАБОТА С БД ---
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

cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
cooldowns = {}

# --- [3] КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "🏆 Топ очков")
    markup.row("🏟 Арена")
    
    user_info = bot.get_chat(uid)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "🗑 Удалить карту")
    markup.row("📝 Изменить карту", "🏠 Назад в меню")
    return markup

# --- [4] РЕГИСТРАЦИЯ ---
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = str(message.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(message.chat.id, "👋 **Добро пожаловать!**\n\nВведите ваш **игровой ник**:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, register_user_nick)
    else:
        bot.send_message(message.chat.id, "⚽️ С возвращением!", reply_markup=main_kb(uid))

def register_user_nick(message):
    uid = str(message.from_user.id)
    nick = message.text
    if not nick:
        msg = bot.send_message(message.chat.id, "❌ Введи ник!")
        return bot.register_next_step_handler(msg, register_user_nick)
    users_data[uid] = {"nick": nick, "score": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Профиль создан!", reply_markup=main_kb(uid))

# --- [5] КРУТКА КАРТ (ОБНОВЛЕННЫЙ ДИЗАЙН) ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(message):
    uid = str(message.from_user.id)
    now = time.time()
    if uid not in users_data: return start_command(message)

    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_TIME and not is_admin:
        left = int(COOLDOWN_TIME - (now - cooldowns[uid]))
        return bot.send_message(message.chat.id, f"⏳ КД: `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")

    if not cards: return bot.send_message(message.chat.id, "❌ Нет карт в базе.")

    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc: stars = s; break

    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    
    base_pts = STATS[won['stars']]['score']
    if is_dub:
        final_pts = int(base_pts * 0.3)
        status = "ПОВТОРКА"
    else:
        final_pts = base_pts
        status = "НОВАЯ КАРТА"
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    users_data[uid]['score'] += final_pts
    save_db(users_data, 'users')

    # ДИЗАЙН: Очки + (Общий баланс)
    cap = (
        f"🏃‍♂️ **{won['name']} ({status})**\n\n"
        f"╔════════════════════╗\n"
        f"  📊 **ИНФО:**\n"
        f"  ├ Позиция: **{won['pos']}**\n"
        f"  ├ Рейтинг: **{'⭐' * won['stars']}**\n"
        f"  └ Очки:    **+{final_pts:,} ({users_data[uid]['score']:,})**\n"
        f"╚════════════════════╝"
    )
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] АДМИН-ПАНЕЛЬ (УДАЛЕНИЕ И ИЗМЕНЕНИЕ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(m.chat.id, "🛠 **Управление картами:**", reply_markup=admin_kb(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_add(m):
    msg = bot.send_message(m.chat.id, "Введите имя игрока:")
    bot.register_next_step_handler(msg, adm_add_pos)

def adm_add_pos(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиция для {name}:")
    bot.register_next_step_handler(msg, adm_add_stars, name)

def adm_add_stars(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Рейтинг (1-5):")
    bot.register_next_step_handler(msg, adm_add_photo, name, pos)

def adm_add_photo(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправь фото для {name}:")
        bot.register_next_step_handler(msg, adm_add_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "Нужно число!"); return

def adm_add_fin(m, name, pos, stars):
    if not m.photo: return bot.send_message(m.chat.id, "Нет фото!")
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта **{name}** добавлена!", reply_markup=admin_kb())

# --- УДАЛЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def adm_del(m):
    if not cards: return bot.send_message(m.chat.id, "База пуста.")
    kb = types.InlineKeyboardMarkup()
    for c in cards:
        kb.add(types.InlineKeyboardButton(f"❌ {c['name']}", callback_data=f"del_{c['name']}"))
    bot.send_message(m.chat.id, "Выбери карту для удаления:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def adm_del_confirm(call):
    name = call.data.split("_")[1]
    global cards
    cards = [c for c in cards if c['name'] != name]
    save_db(cards, 'cards')
    bot.edit_message_text(f"✅ Карта **{name}** удалена!", call.message.chat.id, call.message.message_id)

# --- ИЗМЕНЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def adm_edit(m):
    if not cards: return bot.send_message(m.chat.id, "База пуста.")
    kb = types.InlineKeyboardMarkup()
    for c in cards:
        kb.add(types.InlineKeyboardButton(f"📝 {c['name']}", callback_data=f"edit_{c['name']}"))
    bot.send_message(m.chat.id, "Какую карту изменить?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def adm_edit_pick(call):
    name = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введи новую позицию для **{name}**:")
    bot.register_next_step_handler(msg, adm_edit_stars, name)

def adm_edit_stars(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, f"Новый рейтинг для **{name}** (1-5):")
    bot.register_next_step_handler(msg, adm_edit_fin, name, pos)

def adm_edit_fin(m, name, pos):
    try:
        stars = int(m.text)
        for c in cards:
            if c['name'] == name:
                c['pos'] = pos
                c['stars'] = stars
                break
        save_db(cards, 'cards')
        bot.send_message(m.chat.id, f"✅ Карта **{name}** обновлена!", reply_markup=admin_kb())
    except: bot.send_message(m.chat.id, "Ошибка! Нужно число.")

# --- ОСТАЛЬНЫЕ ФУНКЦИИ (КОЛЛЕКЦИЯ, ТОП, СОСТАВ) ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"v_{i}"))
    bot.send_message(m.chat.id, "🗂 **Твоя коллекция:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def view_coll(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "Пусто!", show_alert=True)
    txt = f"🗂 **Карты {s}⭐:**\n\n" + "\n".join([f"• **{c['name']}** ({c['pos']})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    uid = str(m.from_user.id)
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(uid, [None]*7)
    for i in range(7):
        n = sq[i]['name'] if sq[i] else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {n}", callback_data=f"slot_{i}"))
    bot.send_message(m.chat.id, "📋 **Твой состав:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_pick(call):
    idx = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text("Выбери игрока:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def slot_save(call):
    parts = call.data.split("_"); idx = int(parts[1]); name = parts[2]; uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    if name != "none":
        if any(s['name'] == name for s in user_squads[uid] if s and user_squads[uid].index(s) != idx):
            return bot.answer_callback_query(call.id, "❌ Уже в составе!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else: user_squads[uid][idx] = None
    save_db(user_squads, 'squads'); bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id, "✅ Состав обновлен!")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_view(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        txt += f"{i}. **{data['nick']}** — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🏟 Арена")
def arena_info(m):
    bot.send_message(m.chat.id, "🏟 **Арена в разработке!**")

bot.infinity_polling()
