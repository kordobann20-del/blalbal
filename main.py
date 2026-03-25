import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФІГУРАЦІЯ ТА НАЛАШТУВАННЯ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Шляхи до файлів бази даних
FILES = {
    'cards': 'cards.json',      # Всі існуючі картки в грі
    'colls': 'collections.json', # Колекції гравців (хто що вибив)
    'squads': 'squads.json',    # Активні склади (7 позицій)
    'users': 'users.json'       # Зв'язка username -> user_id
}

# Характеристики карток залежно від зірок
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# Позиції для футбольного складу
POSITIONS = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- РОБОТА З БАЗОЮ ДАНИХ (JSON) ---

def load_data(key):
    """Завантажує дані з файлу. Якщо файлу немає — повертає порожній об'єкт."""
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_data(data, key):
    """Записує дані у файл JSON."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Ініціалізація даних при запуску
cards = load_data('cards')
user_colls = load_data('colls')
user_squads = load_data('squads')
registered_users = load_data('users')
cooldowns = {}   # Тимчасова пам'ять для КД (не зберігається після перезапуску)
arena_reqs = {}  # Тимчасова пам'ять для викликів на бій

# --- КЛАВІАТУРИ (ІНТЕРФЕЙС) ---

def get_main_menu(username):
    """Головне реплай-меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена", "Премиум")
    # Кнопка адміна з'являється тільки у списку ADMINS
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def get_stars_inline():
    """Кнопки для фільтрації колекції за зірками."""
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⭐", callback_data="filter_1"), 
               types.InlineKeyboardButton("⭐⭐", callback_data="filter_2"))
    markup.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="filter_3"), 
               types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="filter_4"))
    markup.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="filter_5"))
    return markup

# --- ОБРОБНИКИ КОМАНД ТА КНОПОК ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        registered_users[uname.lower()] = uid
        save_data(registered_users, 'users')
    
    bot.send_message(
        message.chat.id, 
        "⚽ **Ласкаво просимо до Football Card Bot!**\n\nЗбирай легендарних гравців, формуй склад та змагайся на Арені.",
        reply_markup=get_main_menu(uname),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def handle_back(message):
    bot.send_message(message.chat.id, "Ви повернулися в головне меню.", reply_markup=get_main_menu(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def handle_premium(message):
    text = (
        "💎 **PREMIUM СТАТУС**\n\n"
        "Що дає преміум:\n"
        "• Нульове КД на крутку карт (можна крутити без зупинки).\n"
        "• Унікальний значок у профілі.\n"
        "• Доступ до секретних карток.\n\n"
        "💳 Для придбання звертайтесь до: @verybigsun"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- ЛОГІКА КРУТКИ КАРТ (ROLL) ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def handle_roll(message):
    global cards, user_colls
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        bot.send_message(message.chat.id, "⚠️ У базі ще немає жодної картки! Зверніться до адміна.")
        return

    # Перевірка КД (5 хвилин), адміни крутять без КД
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            wait = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Зачекайте ще {wait // 60} хв {wait % 60} сек.")
            return

    # Рандомний вибір рідкості за шансами
    r_val = random.randint(1, 100)
    stars, current_chance = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        current_chance += info['chance']
        if r_val <= current_chance:
            stars = s
            break

    # Вибір випадкової карти з пулу вибраної рідкості
    pool = [c for c in cards if c.get('stars', 1) == stars]
    if not pool: pool = cards # Якщо саме такої рідкості немає, беремо будь-яку
    
    selected_card = random.choice(pool)
    cooldowns[uid] = now # Оновлюємо час останньої крутки

    # Додавання в колекцію
    if uid not in user_colls: user_colls[uid] = []
    
    # Перевірка на дублікат
    if any(c['name'] == selected_card['name'] for c in user_colls[uid]):
        bot.send_message(message.chat.id, f"🃏 Випав гравець **{selected_card['name']}**, але він вже є у твоїй колекції.", parse_mode="Markdown")
    else:
        user_colls[uid].append(selected_card)
        save_data(user_colls, 'colls')
        bot.send_photo(
            message.chat.id, 
            selected_card['photo'], 
            caption=f"✨ **НОВИЙ ГРАВЕЦЬ!**\n\nИмя: {selected_card['name']}\nРедкость: {'⭐'*selected_card['stars']}\nОписание: {selected_card['desc']}",
            parse_mode="Markdown"
        )

# --- ЛОГІКА АРЕНИ (БОЙОВА СИСТЕМА) ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def handle_arena_main(message):
    bot.reply_to(message, "⚔️ **Ви на Арені!**\n\nЩоб викликати гравця:\n1. Напишіть `Арена @username` (гравець має бути в боті)\n2. Або **відповідайте** словом `Арена` на повідомлення іншої людини.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith("арена") or m.text.lower() == "арена"))
def handle_arena_call(message):
    uid = str(message.from_user.id)
    target_id = None
    target_name = "Опонент"

    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        target_name = message.reply_to_message.from_user.first_name
    else:
        parts = message.text.split()
        if len(parts) > 1:
            raw_name = parts[1].replace("@", "").lower()
            target_id = registered_users.get(raw_name)
            target_name = parts[1]

    if not target_id:
        bot.send_message(message.chat.id, "❌ Гравця не знайдено. Він повинен натиснути /start.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "❌ Не можна викликати самого себе!")
        return

    # Перевірка наявності гравців у складі того, хто викликає
    if not any(user_squads.get(uid, [None]*7)):
        bot.send_message(message.chat.id, "❌ Твій склад порожній! Вибери гравців у меню 'Состав'.")
        return

    arena_reqs[target_id] = {"attacker_id": uid, "attacker_name": message.from_user.first_name}
    bot.send_message(message.chat.id, f"⚔️ **{message.from_user.first_name}** викликає на бій **{target_name}**!\n\nОпонент повинен написати: **Принять**")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def handle_arena_accept(message):
    def_id = str(message.from_user.id)
    if def_id not in arena_reqs: return

    req = arena_reqs.pop(def_id)
    att_id = req["attacker_id"]
    
    att_name = req["attacker_name"]
    def_name = message.from_user.first_name
    
    # Функція розрахунку стат складу
    def get_team_stats(uid):
        squad = user_squads.get(str(uid), [None]*7)
        hp, atk = 0, 0
        for slot in squad:
            if slot:
                st = slot.get('stars', 1)
                hp += STATS[st]['hp']
                atk += STATS[st]['atk']
        return hp, atk

    h_att, a_att = get_team_stats(att_id)
    h_def, a_def = get_team_stats(def_id)

    if h_att == 0 or h_def == 0:
        bot.send_message(message.chat.id, "❌ У когось склад порожній. Бій скасовано.")
        return

    log = f"🏟 **МАТЧ НАЧАЛСЯ!**\n👟 {att_name} VS {def_name}\n\n"
    for r in range(1, 4):
        d_att = a_att + random.randint(-100, 400)
        d_def = a_def + random.randint(-100, 400)
        h_def -= d_att; h_att -= d_def
        log += f"Раунд {r}: {att_name} нанес {d_att} ⚔️ {def_name} нанес {d_def}\n"
        if h_att <= 0 or h_def <= 0: break
    
    winner, loser = (att_name, def_name) if h_att > h_def else (def_name, att_name)

    res_text = (
        f"\n🏆 **ИТОГИ МАТЧА (RU):**\n"
        f"🥇 **Победитель:** {winner}\n"
        f"💀 **Проигравший:** {loser}\n\n"
        f"Битва была легендарной!"
    )
    bot.send_message(message.chat.id, log + res_text, parse_mode="Markdown")

# --- ЛОГИКА СОСТАВА (SQUAD) ---

def get_squad_markup(uid):
    uid = str(uid)
    markup = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        markup.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {name}", callback_data=f"edit_slot_{i}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "Состав")
def handle_squad(message):
    bot.send_message(message.chat.id, "⚔️ **Твій активний склад (7 гравців):**", reply_markup=get_squad_markup(message.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_slot_"))
def handle_slot_selection(call):
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    
    if not coll:
        bot.answer_callback_query(call.id, "Твоя колекція порожня!")
        return

    markup = types.InlineKeyboardMarkup()
    for card in coll:
        markup.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    markup.add(types.InlineKeyboardButton("🚫 Очистити слот", callback_data=f"set_{idx}_none"))
    
    bot.edit_message_text(f"Виберіть гравця на позицію {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_slot_save(call):
    p = call.data.split("_")
    idx, card_name = int(p[1]), p[2]
    uid = str(call.from_user.id)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if card_name == "none":
        user_squads[uid][idx] = None
    else:
        card_obj = next((c for c in user_colls[uid] if c['name'] == card_name), None)
        user_squads[uid][idx] = card_obj
    
    save_data(user_squads, 'squads')
    bot.edit_message_text("✅ Склад оновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_markup(uid))

# --- ЛОГІКА КОЛЕКЦІЇ ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def handle_collection_menu(message):
    bot.send_message(message.chat.id, "Виберіть рідкість карток для перегляду:", reply_markup=get_stars_inline())

@bot.callback_query_handler(func=lambda call: call.data.startswith("filter_"))
def handle_collection_filter(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my_cards = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars]
    
    if not my_cards:
        bot.answer_callback_query(call.id, f"У тебе немає карт на {stars} зірок!")
        return

    text = f"🗂 **Твої гравці ({'⭐'*stars}):**\n\n"
    for c in my_cards:
        text += f"• {c['name']}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- АДМІН-ПАНЕЛЬ (ДОДАВАННЯ КАРТ) ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def handle_admin_menu(message):
    if message.from_user.username in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("Добавить карту", "Удалить карту")
        markup.add("Назад в меню")
        bot.send_message(message.chat.id, "⚙️ Панель розробника:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Добавить карту")
def admin_add_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введіть ім'я нового гравця:")
        bot.register_next_step_handler(msg, admin_add_stars)

def admin_add_stars(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"Введіть кількість зірок (1-5) для {name}:")
    bot.register_next_step_handler(msg, admin_add_photo, name)

def admin_add_photo(message, name):
    try:
        stars = int(message.text)
        msg = bot.send_message(message.chat.id, f"Надішліть фотографію для {name}:")
        bot.register_next_step_handler(msg, admin_add_desc, name, stars)
    except:
        bot.send_message(message.chat.id, "❌ Помилка: зірки мають бути числом.")

def admin_add_desc(message, name, stars):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Помилка: ви не надіслали фото.")
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "Введіть опис картки:")
    bot.register_next_step_handler(msg, admin_add_finish, name, stars, photo_id)

def admin_add_finish(message, name, stars, photo_id):
    global cards
    # Видаляємо стару карту з таким же ім'ям, якщо вона була
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    # Додаємо нову
    cards.append({
        'name': name,
        'stars': stars,
        'photo': photo_id,
        'desc': message.text
    })
    save_data(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Гравець **{name}** успішно доданий у гру!", parse_mode="Markdown")

# --- ЗАПУСК БОТА ---
print("Бот запущений...")
bot.infinity_polling()
