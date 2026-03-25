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

COOLDOWN_ROLL = 10800       # 3 часа на крутку
COOLDOWN_NICK = 1209600     # 2 недели на смену ника

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
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 Арена")
    
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
        bot.send_message(message.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(uid))

def register_user_nick(message):
    uid = str(message.from_user.id)
    nick = message.text
    if not nick:
        msg = bot.send_message(message.chat.id, "❌ Ник не может быть пустым!")
        return bot.register_next_step_handler(msg, register_user_nick)
    users_data[uid] = {"nick": nick, "score": 0, "last_nick_change": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Профиль создан!", reply_markup=main_kb(uid))

# --- [5] ПРОФИЛЬ И СМЕНА НИКА ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_view(m):
    uid = str(m.from_user.id)
    data = users_data.get(uid, {"nick": "Игрок", "score": 0})
    txt = (
        f"👤 **Твой профиль:**\n\n"
        f"📝 Ник: **{data['nick']}**\n"
        f"💰 Очки: **{data['score']:,}**\n"
        f"🗂 Коллекция: **{len(user_colls.get(uid, []))} шт.**"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Изменить ник", callback_data="change_nick"))
    bot.send_message(m.chat.id, txt, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "change_nick")
def change_nick_init(call):
    uid = str(call.from_user.id)
    now = time.time()
    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]
    
    last_change = users_data[uid].get('last_nick_change', 0)
    if now - last_change < COOLDOWN_NICK and not is_admin:
        left = int(COOLDOWN_NICK - (now - last_change))
        days = left // 86400
        return bot.answer_callback_query(call.id, f"❌ Менять ник можно раз в 2 недели! Осталось: {days} дн.", show_alert=True)
    
    msg = bot.send_message(call.message.chat.id, "📝 Введите новый ник:")
    bot.register_next_step_handler(msg, change_nick_final)
    bot.answer_callback_query(call.id)

def change_nick_final(m):
    uid = str(m.from_user.id)
    new_nick = m.text
    if not new_nick: return
    users_data[uid]['nick'] = new_nick
    users_data[uid]['last_nick_change'] = time.time()
    save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"✅ Ник изменен на **{new_nick}**!", reply_markup=main_kb(uid), parse_mode="Markdown")

# --- [6] КРУТКА КАРТ ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(message):
    uid = str(message.from_user.id)
    now = time.time()
    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL and not is_admin:
        left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
        return bot.send_message(message.chat.id, f"⏳ КД: `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")

    if not cards: return bot.send_message(message.chat.id, "❌ Нет карт.")

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

# --- [7] СОСТАВ (ИСПРАВЛЕНО) ---
def get_sq_kb(uid):
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        n = sq[i]['name'] if sq[i] else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {n}", callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "📋 **Твой основной состав:**", reply_markup=get_sq_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_pick(call):
    idx = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: return bot.answer_callback_query(call.id, "У тебя нет карт!", show_alert=True)
    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text("Выбери игрока в состав:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def slot_save(call):
    parts = call.data.split("_"); idx = int(parts[1]); name = parts[2]; uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    if name != "none":
        if any(s['name'] == name for s in user_squads[uid] if s and user_squads[uid].index(s) != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже в составе!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else: user_squads[uid][idx] = None
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- [8] АРЕНА (ИСПРАВЛЕНО) ---
@bot.message_handler(func=lambda m: m.text == "🏟 Арена")
def arena_view(m):
    bot.send_message(m.chat.id, "🏟 **Арена в разработке!**\n\nЗдесь ты сможешь сражаться своими составами.", parse_mode="Markdown")

# --- [9] АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "🗑 Удалить карту")
        kb.row("📝 Изменить карту", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Управление:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_add(m):
    msg = bot.send_message(m.chat.id, "Имя:")
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
        msg = bot.send_message(m.chat.id, "Фото:")
        bot.register_next_step_handler(msg, adm_add_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "Ошибка!"); return

def adm_add_fin(m, name, pos, stars):
    if not m.photo: return
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Добавлен: {name}!", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def adm_del(m):
    kb = types.InlineKeyboardMarkup()
    for c in cards: kb.add(types.InlineKeyboardButton(f"❌ {c['name']}", callback_data=f"del_{c['name']}"))
    bot.send_message(m.chat.id, "Что удалить?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_card(call):
    name = call.data.split("_")[1]
    global cards
    cards = [c for c in cards if c['name'] != name]
    save_db(cards, 'cards')
    bot.edit_message_text(f"✅ Удалено!", call.message.chat.id, call.message.message_id)

# --- ПРОЧЕЕ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"v_{i}"))
    bot.send_message(m.chat.id, "🗂 **Твои карты:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def view_coll(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "Пусто!", show_alert=True)
    txt = f"🗂 **Карты {s}⭐:**\n\n" + "\n".join([f"• **{c['name']}**" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_view(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП ПО ОЧКАМ:**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        txt += f"{i}. **{data['nick']}** — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_h(m):
    bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
