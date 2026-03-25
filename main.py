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

# Позиции в футбольном составе
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
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загрузка данных
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

# --- ГЛАВНЫЕ КОМАНДЫ ---

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

# --- ЛОГИКА КРУТКИ КАРТ ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_card(message):
    global cards, user_colls
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    # Проверка: есть ли вообще карты в игре
    if not cards:
        bot.send_message(message.chat.id, "⚠️ В игре пока нет доступных карт. Попроси админа добавить их!")
        return

    # Проверка КД (5 минут) для обычных игроков
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            rem = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ КД! Жди еще {rem // 60} мин. {rem % 60} сек.")
            return

    # Логика выбора редкости
    rand_val = random.randint(1, 100)
    stars, accum = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        accum += info['chance']
        if rand_val <= accum:
            stars = s
            break

    # Фильтруем карты по выпавшим звездам
    possible_cards = [c for c in cards if c.get('stars', 1) == stars]
    if not possible_cards:
        possible_cards = cards # Если такой редкости нет, берем любую

    card = random.choice(possible_cards)
    cooldowns[uid] = now # Засекаем время

    # Проверка на дубликат
    if uid not in user_colls: user_colls[uid] = []
    
    has_card = False
    for c in user_colls[uid]:
        if c['name'] == card['name']:
            has_card = True
            break
            
    if has_card:
        bot.send_message(message.chat.id, f"🃏 Выпала повторка: {card['name']}. Карта уже есть в коллекции.")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(message.chat.id, card['photo'], 
                       caption=f"✨ НОВАЯ КАРТА!\n\nИгрок: {card['name']}\nРедкость: {'⭐'*card['stars']}\nОписание: {card['desc']}")

# --- КОЛЛЕКЦИЯ (СТАРЫЙ ФОРМАТ) ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def show_collection_filter(message):
    bot.send_message(message.chat.id, "Выберите редкость карт для просмотра:", reply_markup=stars_filter_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_cards_by_stars(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    
    my_cards = []
    if uid in user_colls:
        for c in user_colls[uid]:
            if c.get('stars', 1) == stars:
                my_cards.append(c)
                
    if not my_cards:
        bot.answer_callback_query(call.id, f"У тебя нет карт на {stars} звезд!")
        return

    txt = f"🗂 Твои карты ({'⭐'*stars}):\n\n"
    for c in my_cards:
        txt += f"• {c['name']}\n"
    
    bot.send_message(call.message.chat.id, txt)
    bot.answer_callback_query(call.id)

# --- АРЕНА (ИСПРАВЛЕННАЯ) ---

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith("арена") or m.text == "Арена"))
def call_to_arena(message):
    uid = str(message.from_user.id)
    target_id = None

    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
    else:
        parts = message.text.split()
        if len(parts) > 1:
            target_name = parts[1].replace("@", "").lower()
            target_id = registered_users.get(target_name)
    
    if not target_id:
        bot.send_message(message.chat.id, "⚠️ Укажи игрока! Ответь на сообщение словом 'Арена' или напиши 'Арена @юзернейм'.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "Нельзя играть против самого себя!")
        return
    
    arena_reqs[target_id] = uid
    bot.send_message(message.chat.id, "⚔️ Вызов отправлен! Противник должен написать 'Принять'.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def accept_fight(message):
    uid = str(message.from_user.id)
    if uid not in arena_reqs:
        return
    
    enemy_id = arena_reqs.pop(uid)
    
    def calculate_power(user_id):
        squad = user_squads.get(user_id, [None]*7)
        total_hp = 0
        total_atk = 0
        for slot in squad:
            if slot:
                st = slot.get('stars', 1)
                total_hp += STATS[st]['hp']
                total_atk += STATS[st]['atk']
        # Базовые статы если состав пуст
        if total_hp == 0: total_hp, total_atk = 1000, 500
        return total_hp, total_atk

    hp1, atk1 = calculate_power(uid)
    hp2, atk2 = calculate_power(enemy_id)
    
    # Симуляция боя
    log = "🏟 **МАТЧ НАЧАЛСЯ!**\n\n"
    for r in range(1, 4):
        dmg1 = atk1 + random.randint(-200, 500)
        dmg2 = atk2 + random.randint(-200, 500)
        hp2 -= dmg1
        hp1 -= dmg2
        log += f"Раунд {r}: Твой урон: {dmg1} | Враг нанес: {dmg2}\n"
        if hp1 <= 0 or hp2 <= 0: break
    
    winner = "Победа!" if hp1 > hp2 else "Поражение!"
    bot.send_message(message.chat.id, log + f"\n🏆 **Итог: {winner}**", parse_mode="Markdown")

# --- СОСТАВ (ФУТБОЛЬНЫЙ) ---

def get_squad_inline(uid):
    uid = str(uid)
    markup = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        markup.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {name}", callback_data=f"edit_sl_{i}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_main(message):
    bot.send_message(message.chat.id, "⚔️ **Твой футбольный состав:**", reply_markup=get_squad_inline(message.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sl_"))
def choose_player_for_squad(call):
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    
    if not coll:
        bot.answer_callback_query(call.id, "Твоя коллекция пуста!")
        return

    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({'⭐'*card['stars']})", callback_data=f"set_p_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Очистить позицию", callback_data=f"set_p_{idx}_none"))
    
    bot.edit_message_text(f"Выбери игрока на позицию {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_p_"))
def save_player_to_squad(call):
    parts = call.data.split("_")
    idx, name = int(parts[2]), parts[3]
    uid = str(call.from_user.id)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        found_card = next((c for c in user_colls[uid] if c['name'] == name), None)
        user_squads[uid][idx] = found_card
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_inline(uid))

# --- АДМИН-ПАНЕЛЬ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm_panel(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "Меню администратора:", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def admin_card_action(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите название карты:")
        bot.register_next_step_handler(msg, step_stars)

def step_stars(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите звезды (1-5) для '{name}':")
    bot.register_next_step_handler(msg, step_photo, name)

def step_photo(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправьте фото для '{name}':")
        bot.register_next_step_handler(msg, step_desc, name, stars)
    except:
        bot.send_message(m.chat.id, "Ошибка! Нужно число.")

def step_desc(m, name, stars):
    if not m.photo:
        bot.send_message(m.chat.id, "Нужно фото!")
        return
    photo_id = m.photo[-1].file_id
    msg = bot.send_message(m.chat.id, "Введите описание карты:")
    bot.register_next_step_handler(msg, step_final, name, stars, photo_id)

def step_final(m, name, stars, photo_id):
    global cards
    # Удаляем старую карту если меняем её
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': stars, 'photo': photo_id, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} сохранена!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def admin_del(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите имя карты для удаления:")
        bot.register_next_step_handler(msg, step_del_final)

def step_del_final(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Удалено.", reply_markup=admin_keyboard())

bot.infinity_polling()
