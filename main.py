import telebot
from telebot import types
import random
import time
import json
import os

# --- НАСТРОЙКИ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users.json'
}

# Характеристики и шансы выпадения
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# Футбольные позиции для состава
POSITIONS = [
    "ГК (Вратарь)", 
    "ЛЗ (Защитник)", 
    "ПЗ (Защитник)", 
    "ЦП (Полузащитник)", 
    "ЛВ (Вингер)", 
    "ПВ (Вингер)", 
    "КФ (Нападающий)"
]

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---

def load_db(key):
    """Загрузка данных из JSON"""
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    """Сохранение данных в JSON"""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

# --- КЛАВИАТУРЫ ---

def main_keyboard(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Удалить карту")
    markup.row("Изменить карту", "Назад в меню")
    return markup

def stars_filter_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⭐", callback_data="view_1"), 
               types.InlineKeyboardButton("⭐⭐", callback_data="view_2"))
    markup.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="view_3"), 
               types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="view_4"))
    markup.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="view_5"))
    return markup

# --- ОБРАБОТЧИКИ КНОПОК МЕНЮ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        registered_users[uname.lower()] = uid
        save_db(registered_users, 'users')
    bot.send_message(message.chat.id, "💎 Добро пожаловать! Собирай футбольные карты и побеждай на арене.", 
                     reply_markup=main_keyboard(uname))

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в меню.", reply_markup=main_keyboard(message.from_user.username))

# ИСПРАВЛЕННАЯ КНОПКА ПРЕМИУМ
@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_info(message):
    text = (
        "💎 **Премиум Статус**\n\n"
        "Преимущества:\n"
        "1. Отсутствие КД на крутку карт (5 минут ждать не нужно).\n"
        "2. Повышенный шанс на легендарных игроков.\n"
        "3. Уникальный префикс в профиле.\n\n"
        "💳 **Для покупки пишите администратору:** @verybigsun"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- ЛОГИКА КРУТКИ КАРТ ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_card(message):
    global cards, user_colls
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        bot.send_message(message.chat.id, "⚠️ Ошибка: В игре пока нет ни одной карты. Попроси админа добавить их!")
        return

    # Проверка КД
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            rem = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ КД! Жди еще {rem // 60} мин. {rem % 60} сек.")
            return

    # Выбор редкости
    rand_val = random.randint(1, 100)
    stars, accum = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        accum += info['chance']
        if rand_val <= accum:
            stars = s
            break

    possible_cards = [c for c in cards if c.get('stars', 1) == stars]
    if not possible_cards: possible_cards = cards

    card = random.choice(possible_cards)
    cooldowns[uid] = now

    if uid not in user_colls: user_colls[uid] = []
    
    # Проверка дубликата
    has_card = any(c['name'] == card['name'] for c in user_colls[uid])
            
    if has_card:
        bot.send_message(message.chat.id, f"🃏 Выпала повторка: {card['name']}. Карта уже есть в коллекции.")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(message.chat.id, card['photo'], 
                       caption=f"✨ НОВАЯ КАРТА!\n\nИгрок: {card['name']}\nРедкость: {'⭐'*card['stars']}\nОписание: {card['desc']}")

# --- КОЛЛЕКЦИЯ (ВЫБОР ПО ЗВЕЗДАМ) ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def show_collection_menu(message):
    bot.send_message(message.chat.id, "Выберите ценность карточек (редкость):", reply_markup=stars_filter_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def filter_coll_by_stars(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    
    my_cards = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars]
                
    if not my_cards:
        bot.answer_callback_query(call.id, f"У тебя нет карт на {stars} звезд!")
        return

    txt = f"🗂 Твои игроки ({'⭐'*stars}):\n\n"
    for c in my_cards:
        txt += f"• {c['name']}\n"
    
    bot.send_message(call.message.chat.id, txt)
    bot.answer_callback_query(call.id)

# --- АРЕНА И СОСТАВ (РАЗВЕРНУТО) ---

def get_squad_inline(uid):
    uid = str(uid)
    markup = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        markup.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {name}", callback_data=f"set_slot_{i}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_main(message):
    bot.send_message(message.chat.id, "⚔️ **Твой футбольный состав:**", reply_markup=get_squad_inline(message.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_slot_"))
def squad_edit_pos(call):
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll:
        bot.answer_callback_query(call.id, "Коллекция пуста!")
        return
    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({'⭐'*card['stars']})", callback_data=f"apply_p_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Очистить", callback_data=f"apply_p_{idx}_none"))
    bot.edit_message_text(f"Выбери игрока на позицию {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("apply_p_"))
def squad_apply_final(call):
    p = call.data.split("_")
    idx, name = int(p[2]), p[3]
    uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    if name == "none":
        user_squads[uid][idx] = None
    else:
        user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None)
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_inline(uid))

# --- АДМИНКА (ДОБАВИТЬ/ИЗМЕНИТЬ) ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "Панель разработчика:", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def adm_start(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите название игрока:")
        bot.register_next_step_handler(msg, adm_stars)

def adm_stars(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите звезды (1-5) для '{name}':")
    bot.register_next_step_handler(msg, adm_photo, name)

def adm_photo(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправьте фото для '{name}':")
        bot.register_next_step_handler(msg, adm_desc, name, stars)
    except: bot.send_message(m.chat.id, "Ошибка! Нужно число.")

def adm_desc(m, name, stars):
    if not m.photo: return
    fid = m.photo[-1].file_id
    msg = bot.send_message(m.chat.id, "Введите описание:")
    bot.register_next_step_handler(msg, adm_final, name, stars, fid)

def adm_final(m, name, stars, fid):
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': stars, 'photo': fid, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Игрок {name} сохранен!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def adm_del(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите имя карты для удаления:")
        bot.register_next_step_handler(msg, adm_del_confirm)

def adm_del_confirm(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Удалено.", reply_markup=admin_keyboard())

# --- ЗАПУСК ---
bot.infinity_polling()
