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

COOLDOWN_TIME = 10800 # 3 часа

STATS = {
    1: {"chance": 50, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 12, "score": 5000, "atk": 600},
    4: {"chance": 6, "score": 8000, "atk": 1000},
    5: {"chance": 2, "score": 10000, "atk": 1500}
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
        try:
            return json.load(f)
        except:
            return [] if key == 'cards' else {}

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
    markup.row("📋 Состав", "🏆 Топ очков") # Убрал Топ карт
    markup.row("🏟 Арена")
    
    user_info = bot.get_chat(uid)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
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
    users_data[uid] = {"nick": nick, "score": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Профиль **{nick}** создан!", reply_markup=main_kb(uid), parse_mode="Markdown")

# --- [5] КРУТКА КАРТ ---

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(message):
    uid = str(message.from_user.id)
    now = time.time()
    if uid not in users_data: return start_command(message)

    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_TIME and not is_admin:
        left = int(COOLDOWN_TIME - (now - cooldowns[uid]))
        bot.send_message(message.chat.id, f"⏳ КД: `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")
        return

    if not cards:
        bot.send_message(message.chat.id, "❌ Карт еще нет.")
        return

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
    
    if not is_dub:
        user_colls[uid].append(won)
        users_data[uid]['score'] += STATS[won['stars']]['score']
        save_db(user_colls, 'colls')
        save_db(users_data, 'users')

    status = "ПОВТОРКА" if is_dub else "НОВАЯ КАРТА"
    cap = (
        f"🏃‍♂️ **{won['name']} ({status})**\n"
        f"👤 Игрок: **{users_data[uid]['nick']}**\n\n"
        f"╔════════════════════╗\n"
        f"  📊 **ИНФО:**\n"
        f"  ├ Позиция: **{won['pos']}**\n"
        f"  ├ Рейтинг: **{'⭐' * won['stars']}**\n"
        f"  └ Очки:    **+{STATS[won['stars']]['score']:,}**\n"
        f"╚════════════════════╝"
    )
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] КОЛЛЕКЦИЯ (ПОЧИНЕНО) ---

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def collection_menu(message):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"view_stars_{i}"))
    bot.send_message(message.chat.id, "🗂 **Твоя коллекция.** Выбери редкость:", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_stars_"))
def view_collection_by_stars(call):
    stars = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    my_cards = [c for c in user_colls.get(uid, []) if c['stars'] == stars]
    
    if not my_cards:
        bot.answer_callback_query(call.id, "У тебя нет таких карт!", show_alert=True)
        return

    text = f"🗂 **Карты {stars}⭐:**\n\n"
    for c in my_cards:
        text += f"• **{c['name']}** ({c['pos']})\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [7] СОСТАВ ---

def get_sq_kb(uid):
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        name = sq[i]['name'] if sq[i] else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {name}", callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "📋 **Твой состав:**", reply_markup=get_sq_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_pick(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: 
        bot.answer_callback_query(call.id, "Коллекция пуста!"); return

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
            bot.answer_callback_query(call.id, "❌ Уже в составе!", show_alert=True); return
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else:
        user_squads[uid][idx] = None
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- [8] АРЕНА (ДОБАВЛЕНО) ---

@bot.message_handler(func=lambda m: m.text == "🏟 Арена")
def arena_start(m):
    uid = str(m.from_user.id)
    sq = user_squads.get(uid, [])
    active_players = [p for p in sq if p is not None]
    
    if len(active_players) < 1:
        bot.send_message(m.chat.id, "❌ В твоем составе нет игроков! Сначала заполни **📋 Состав**.")
        return

    # Простая симуляция матча
    power = sum(STATS[p['stars']]['atk'] for p in active_players)
    bot.send_message(m.chat.id, f"🏟 **Добро пожаловать на Арену!**\n\nТвоя текущая мощь состава: **{power:,} ⚡️**\n\n_Система ПвП матчей находится в разработке..._", parse_mode="Markdown")

# --- [9] ТОП ОЧКОВ ---

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_score(message):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        txt += f"{i}. **{data['nick']}** — `{data['score']:,}`\n"
    bot.send_message(message.chat.id, txt, parse_mode="Markdown")

# --- [10] АДМИНКА ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    if m.from_user.username in ADMINS:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "🗑 Удалить карту", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Админка:**", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_name(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Имя футболиста:")
        bot.register_next_step_handler(msg, adm_pos)

def adm_pos(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиция для {name}:")
    bot.register_next_step_handler(msg, adm_stars, name)

def adm_stars(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Рейтинг (1-5):")
    bot.register_next_step_handler(msg, adm_photo, name, pos)

def adm_photo(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправь фото:")
        bot.register_next_step_handler(msg, adm_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "Нужно число.")

def adm_fin(m, name, pos, stars):
    if not m.photo: return
    global cards
    cards = [c for c in cards if c['name'] != name]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, "✅ Добавлено!")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back(m):
    bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
