import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
# Ники администраторов без символа @
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Пути к файлам базы данных
FILES = {
    'cards': 'cards.json',      # Все существующие карты
    'colls': 'collections.json', # Коллекции пользователей
    'squads': 'squads.json',    # Составы (7 игроков)
    'users': 'users.json'       # База: username -> user_id
}

# Характеристики по звездам
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# Позиции в футбольном составе
POSITIONS = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- СИСТЕМА РАБОТЫ С ФАЙЛАМИ (JSON) ---

def load_db(key):
    """Загрузка данных. Если файла нет, создает пустой список или словарь."""
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
    """Сохранение данных в файл сразу после изменений."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация данных при старте скрипта
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

def update_user_record(message):
    """Обновляет базу данных юзеров для поиска по @username."""
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        uname_lower = uname.lower()
        if registered_users.get(uname_lower) != uid:
            registered_users[uname_lower] = uid
            save_db(registered_users, 'users')

# --- КЛАВИАТУРЫ ---

def get_main_keyboard(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Изменить карту")
    markup.row("Удалить карту", "Назад в меню")
    return markup

# --- ОБРАБОТЧИКИ МЕНЮ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    update_user_record(message)
    bot.send_message(
        message.chat.id, 
        "⚽ **Football Card Bot приветствует тебя!**\n\nВыбивай карты, собирай состав и сражайся на Арене.",
        reply_markup=get_main_keyboard(message.from_user.username),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_to_main(message):
    bot.send_message(message.chat.id, "Вы в главном меню.", reply_markup=get_main_keyboard(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_info(message):
    bot.send_message(message.chat.id, "💎 **Премиум**\n\nПозволяет крутить карты без КД!\nДля покупки: @verybigsun", parse_mode="Markdown")

# --- КРУТКА КАРТ (ROLL) ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_logic(message):
    global cards, user_colls
    update_user_record(message)
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        bot.send_message(message.chat.id, "❌ Админ еще не добавил ни одной карты!")
        return

    # КД 5 минут для обычных игроков
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            left = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Подожди {left // 60} мин. {left % 60} сек.")
            return

    # Рандом редкости
    val = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if val <= acc:
            stars = s
            break

    # Выбор карты
    pool = [c for c in cards if c.get('stars', 1) == stars] or cards
    won_card = random.choice(pool)
    cooldowns[uid] = now

    if uid not in user_colls:
        user_colls[uid] = []

    # Проверка на повторку
    is_dub = any(c['name'] == won_card['name'] for c in user_colls[uid])
    
    if is_dub:
        status = "✨ **Статус: Повторка**"
    else:
        status = "✨ **Статус: Новая карта!**"
        user_colls[uid].append(won_card)
        save_db(user_colls, 'colls') # Сохранение сразу в файл

    cap = (
        f"🃏 **{won_card['name']}**\n"
        f"Редкость: {'⭐' * won_card['stars']}\n"
        f"Описание: {won_card['desc']}\n\n"
        f"{status}"
    )
    bot.send_photo(message.chat.id, won_card['photo'], caption=cap, parse_mode="Markdown")

# --- АРЕНА (ЗАПРОСЫ И БОЙ) ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def arena_main(message):
    bot.reply_to(message, "⚔️ Чтобы вызвать игрока, напиши:\n`Арена @username` (игрок должен быть в боте)\n\nИли ответь на любое сообщение игрока словом `Арена`.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_call(message):
    update_user_record(message)
    uid = str(message.from_user.id)
    target_id = None
    target_name = "Игрок"

    # По реплаю
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        target_name = message.reply_to_message.from_user.first_name
    # По упоминанию
    else:
        parts = message.text.split()
        if len(parts) > 1:
            raw = parts[1].replace("@", "").lower()
            target_id = registered_users.get(raw)
            target_name = parts[1]

    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден в базе бота.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "❌ Нельзя вызвать самого себя.")
        return

    if not any(user_squads.get(uid, [None]*7)):
        bot.send_message(message.chat.id, "❌ У тебя пустой состав! Сначала выбери игроков в меню 'Состав'.")
        return

    arena_reqs[target_id] = {"att_id": uid, "att_name": message.from_user.first_name}
    bot.send_message(message.chat.id, f"⚔️ **{message.from_user.first_name}** бросил вызов **{target_name}**!\nОппонент должен написать: **Принять**")
    
    try:
        bot.send_message(target_id, f"⚔️ Тебе брошен вызов от {message.from_user.first_name}! Зайди в чат и напиши 'Принять'.")
    except:
        pass

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept(message):
    def_id = str(message.from_user.id)
    if def_id not in arena_reqs: return

    req = arena_reqs.pop(def_id)
    att_id = req["att_id"]
    att_name = req["att_name"]
    def_name = message.from_user.first_name
    
    def calc_power(uid):
        sq = user_squads.get(str(uid), [None]*7)
        hp, atk = 0, 0
        for c in sq:
            if c:
                st = c.get('stars', 1)
                hp += STATS[st]['hp']
                atk += STATS[st]['atk']
        return hp, atk

    h1, a1 = calc_power(att_id)
    h2, a2 = calc_power(def_id)

    if h1 == 0 or h2 == 0:
        bot.send_message(message.chat.id, "❌ Бой невозможен: у кого-то пустой состав.")
        return

    log = f"🏟 **МАТЧ НАЧАЛСЯ!**\n👟 {att_name} VS {def_name}\n\n"
    for r in range(1, 4):
        d1 = a1 + random.randint(0, 300)
        d2 = a2 + random.randint(0, 300)
        h2 -= d1; h1 -= d2
        log += f"Раунд {r}: {att_name} -{d1} HP | {def_name} -{d2} HP\n"
    
    winner = att_name if h1 > h2 else def_name
    bot.send_message(message.chat.id, log + f"\n🏆 **Победитель:** {winner}")

# --- СОСТАВ (SQUAD) ---

def get_sq_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(uid, [None]*7)
    for i in range(7):
        n = sq[i]['name'] if (i < len(sq) and sq[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {n}", callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_view(message):
    bot.send_message(message.chat.id, "⚔️ **Твой состав:**", reply_markup=get_sq_kb(message.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_choose(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll:
        bot.answer_callback_query(call.id, "Коллекция пуста!")
        return
    
    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"set_{idx}_none"))
    bot.edit_message_text(f"Позиция {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def slot_save(call):
    p = call.data.split("_")
    idx, name = int(p[1]), p[2]
    uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None)
    
    save_db(user_squads, 'squads') # Мгновенное сохранение состава
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- АДМИН-ПАНЕЛЬ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_menu(message):
    if message.from_user.username in ADMINS:
        bot.send_message(message.chat.id, "⚙️ Панель управления:", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def admin_add_init(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите имя игрока:")
        bot.register_next_step_handler(msg, admin_add_stars)

def admin_add_stars(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"Введите звезды (1-5) для {name}:")
    bot.register_next_step_handler(msg, admin_add_photo, name)

def admin_add_photo(message, name):
    try:
        s = int(message.text)
        msg = bot.send_message(message.chat.id, f"Отправь фото для {name}:")
        bot.register_next_step_handler(msg, admin_add_desc, name, s)
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно число.")

def admin_add_desc(message, name, s):
    if not message.photo:
        bot.send_message(message.chat.id, "Нужно отправить именно фото!")
        return
    fid = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "Введите описание:")
    bot.register_next_step_handler(msg, admin_add_final, name, s, fid)

def admin_add_final(message, name, s, fid):
    global cards
    # Если имя совпадает — заменяем карту (логика изменения)
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': s, 'photo': fid, 'desc': message.text})
    save_db(cards, 'cards') # Сохранение в JSON
    bot.send_message(message.chat.id, f"✅ Карта {name} сохранена!", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def admin_delete(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Имя игрока для удаления:")
        bot.register_next_step_handler(msg, admin_delete_done)

def admin_delete_done(message):
    global cards
    cards = [c for c in cards if c['name'].lower() != message.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, "✅ Удалено.", reply_markup=get_admin_keyboard())

# --- КОЛЛЕКЦИЯ ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def collection_stars(message):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⭐", callback_data="v_1"), types.InlineKeyboardButton("⭐⭐", callback_data="v_2"))
    kb.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="v_3"), types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="v_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="v_5"))
    bot.send_message(message.chat.id, "Выберите редкость:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def collection_view(call):
    s = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == s]
    if not my:
        bot.answer_callback_query(call.id, "Нет таких карт!")
        return
    txt = f"🗂 **Карты {s}⭐:**\n\n" + "\n".join([f"• {c['name']}" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

bot.infinity_polling()
