import telebot
from telebot import types
import random
import time
import json
import os

# --- НАСТРОЙКИ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
# Убедись, что твои юзернеймы вписаны правильно (без @)
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',      # Все карты игры
    'colls': 'collections.json', # Кто какими картами владеет
    'squads': 'squads.json',    # Выбранные 7 игроков для боя
    'users': 'users.json'       # База: username -> user_id (для поиска по @)
}

# Характеристики по редкости
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# Список позиций
POSITIONS = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- ФУНКЦИИ РАБОТЫ С ДАННЫМИ ---

def load_db(key):
    """Загрузка данных из JSON файла."""
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {} if key != 'cards' else []
    return {} if key != 'cards' else []

def save_db(data, key):
    """Сохранение данных в JSON файл."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}   # Время перезарядки крутки
arena_reqs = {}  # Активные вызовы на бой

def update_user_db(message):
    """Автоматически записывает юзера в базу при любом действии."""
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        uname_lower = uname.lower()
        if registered_users.get(uname_lower) != uid:
            registered_users[uname_lower] = uid
            save_db(registered_users, 'users')

# --- КЛАВИАТУРЫ ---

def main_kb(username):
    """Главное меню игрока."""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Крутить карту", "Коллекция")
    kb.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        kb.add("🛠 Админ-панель")
    return kb

def admin_kb():
    """Меню администратора."""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Добавить карту", "Удалить карту")
    kb.row("Изменить карту", "Назад в меню")
    return kb

def get_stars_kb():
    """Инлайн кнопки для просмотра редкостей."""
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⭐", callback_data="show_1"), 
           types.InlineKeyboardButton("⭐⭐", callback_data="show_2"))
    kb.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="show_3"), 
           types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="show_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="show_5"))
    return kb

# --- ОСНОВНЫЕ КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start_handler(message):
    update_user_db(message)
    bot.send_message(
        message.chat.id, 
        "⚽ **Football Card Bot запущен!**\n\nСобирай команду мечты и сражайся с друзьями.\nИспользуй кнопки ниже для навигации.", 
        reply_markup=main_kb(message.from_user.username),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_handler(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_kb(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_handler(message):
    bot.send_message(
        message.chat.id, 
        "💎 **Статус Премиум**\n\n- Убирает время ожидания (КД) на крутки.\n- Дает особый статус в боях.\n\nДля покупки: @verybigsun",
        parse_mode="Markdown"
    )

# --- ЛОГИКА АРЕНЫ (ИСПРАВЛЕННАЯ) ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def arena_info_handler(message):
    update_user_db(message)
    text = (
        "⚔️ **Арена вызовов**\n\n"
        "Чтобы начать бой с игроком:\n"
        "1. Напиши: `Арена @username` (например: `Арена @Nazikrrk`)\n"
        "2. Или ответь (реплай) на любое сообщение игрока словом `Арена`.\n\n"
        "⚠️ **Важно:** Соперник должен быть зарегистрирован в боте (нажать /start)."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith("арена") or m.text.lower() == "арена"))
def arena_call_handler(message):
    update_user_db(message)
    uid = str(message.from_user.id)
    target_id = None
    target_username = "Игрок"

    # Способ 1: Через ответ на сообщение (Reply)
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        target_username = message.reply_to_message.from_user.first_name
    
    # Способ 2: Через упоминание @username
    else:
        parts = message.text.split()
        if len(parts) > 1:
            raw_name = parts[1].replace("@", "").lower()
            target_id = registered_users.get(raw_name)
            target_username = parts[1]

    if not target_id:
        bot.send_message(message.chat.id, "❌ Ошибка: Игрок не найден в базе бота. Попроси его нажать /start.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "❌ Ты не можешь вызвать на бой самого себя!")
        return

    # Проверка, есть ли у вызывающего хоть один игрок в составе
    if not any(user_squads.get(uid, [None]*7)):
        bot.send_message(message.chat.id, "❌ Твой состав пуст! Сначала выбери игроков в меню 'Состав'.")
        return

    # Сохраняем запрос
    arena_reqs[target_id] = {"attacker_id": uid, "attacker_name": message.from_user.first_name}
    
    # Отправляем сообщение в текущий чат
    bot.send_message(message.chat.id, f"⚔️ **{message.from_user.first_name}** бросил вызов игроку **{target_username}**!\n\nОппонент должен ответить словом: **Принять**")
    
    # Отправляем личное сообщение сопернику, чтобы он точно увидел
    try:
        bot.send_message(target_id, f"⚔️ Тебе брошен вызов от **{message.from_user.first_name}**!\nЗайди в чат и напиши 'Принять', чтобы начать бой.")
    except:
        pass # Если у игрока заблокирован бот

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept_handler(message):
    defender_id = str(message.from_user.id)
    if defender_id not in arena_reqs:
        return # Нет активных вызовов для этого юзера

    # Извлекаем данные вызова
    req_data = arena_reqs.pop(defender_id)
    attacker_id = req_data["attacker_id"]
    attacker_name = req_data["attacker_name"]
    defender_name = message.from_user.first_name
    
    def calculate_stats(user_id):
        squad = user_squads.get(str(user_id), [None]*7)
        total_hp, total_atk = 0, 0
        for card in squad:
            if card:
                stars = card.get('stars', 1)
                total_hp += STATS[stars]['hp']
                total_atk += STATS[stars]['atk']
        return total_hp, total_atk

    hp_1, atk_1 = calculate_stats(attacker_id)
    hp_2, atk_2 = calculate_stats(defender_id)

    if hp_1 == 0 or hp_2 == 0:
        bot.send_message(message.chat.id, "❌ Бой невозможен: у одного из игроков нет карт в составе.")
        return

    log = f"🏟 **МАТЧ НАЧАЛСЯ!**\n👟 {attacker_name} VS {defender_name}\n\n"
    
    # Бой длится максимум 5 раундов или до смерти
    for r in range(1, 6):
        dmg_1 = atk_1 + random.randint(-150, 450)
        dmg_2 = atk_2 + random.randint(-150, 450)
        
        hp_2 -= dmg_1
        hp_1 -= dmg_2
        
        log += f"Раунд {r}: {attacker_name} ударил на {dmg_1} ⚔️ {defender_name} ударил на {dmg_2}\n"
        if hp_1 <= 0 or hp_2 <= 0:
            break

    # Итоги
    if hp_1 > hp_2:
        winner, loser = attacker_name, defender_name
    else:
        winner, loser = defender_name, attacker_name

    res = (
        f"\n🏆 **ИТОГИ МАТЧА:**\n"
        f"🥇 **Победитель:** {winner}\n"
        f"💀 **Проигравший:** {loser}\n\n"
        f"Это было захватывающе!"
    )
    bot.send_message(message.chat.id, log + res, parse_mode="Markdown")

# --- ЛОГИКА СОСТАВА ---

def get_squad_buttons(uid):
    uid = str(uid)
    markup = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        markup.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {name}", callback_data=f"slot_{i}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_handler(message):
    update_user_db(message)
    bot.send_message(message.chat.id, "⚔️ **Твой футбольный состав (7 мест):**", reply_markup=get_squad_buttons(message.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
def slot_click(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    collection = user_colls.get(uid, [])
    
    if not collection:
        bot.answer_callback_query(call.id, "Твоя коллекция пуста!")
        return

    markup = types.InlineKeyboardMarkup()
    for card in collection:
        markup.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    markup.add(types.InlineKeyboardButton("🚫 Очистить позицию", callback_data=f"set_{idx}_none"))
    
    bot.edit_message_text(f"Выберите игрока на позицию {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def slot_set(call):
    parts = call.data.split("_")
    idx, c_name = int(parts[1]), parts[2]
    uid = str(call.from_user.id)
    
    if uid not in user_squads:
        user_squads[uid] = [None]*7
        
    if c_name == "none":
        user_squads[uid][idx] = None
    else:
        card_obj = next((c for c in user_colls[uid] if c['name'] == c_name), None)
        user_squads[uid][idx] = card_obj
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав успешно обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_buttons(uid))

# --- ЛОГИКА КРУТКИ КАРТ ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_handler(message):
    global cards, user_colls
    update_user_db(message)
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        bot.send_message(message.chat.id, "⚠️ В игре пока нет ни одной карты. Сообщите админу!")
        return

    # Проверка КД (5 минут)
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            left = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Нужно подождать еще {left // 60} мин. {left % 60} сек.")
            return

    # Определение редкости
    roll_val = random.randint(1, 100)
    stars_res, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if roll_val <= acc:
            stars_res = s
            break

    # Выбор карты
    pool = [c for c in cards if c.get('stars', 1) == stars_res] or cards
    won_card = random.choice(pool)
    cooldowns[uid] = now

    if uid not in user_colls: user_colls[uid] = []
    
    if any(c['name'] == won_card['name'] for c in user_colls[uid]):
        bot.send_message(message.chat.id, f"🃏 Выпала карта **{won_card['name']}**, но она у тебя уже есть.", parse_mode="Markdown")
    else:
        user_colls[uid].append(won_card)
        save_db(user_colls, 'colls')
        bot.send_photo(
            message.chat.id, 
            won_card['photo'], 
            caption=f"✨ **НОВЫЙ ИГРОК В КОЛЛЕКЦИИ!**\n\nИмя: {won_card['name']}\nРедкость: {'⭐'*won_card['stars']}\nОписание: {won_card['desc']}",
            parse_mode="Markdown"
        )

# --- АДМИН ПАНЕЛЬ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel_handler(message):
    if message.from_user.username in ADMINS:
        bot.send_message(message.chat.id, "⚙️ Добро пожаловать в меню разработчика:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def admin_add_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите имя футболиста:")
        bot.register_next_step_handler(msg, admin_add_stars)

def admin_add_stars(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"Сколько звезд у {name} (1-5)?")
    bot.register_next_step_handler(msg, admin_add_photo, name)

def admin_add_photo(message, name):
    try:
        st = int(message.text)
        msg = bot.send_message(message.chat.id, f"Отправьте фото для {name}:")
        bot.register_next_step_handler(msg, admin_add_desc, name, st)
    except:
        bot.send_message(message.chat.id, "❌ Ошибка: Введите число от 1 до 5.")

def admin_add_desc(message, name, st):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Ошибка: Вы не прислали фото.")
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "Введите краткое описание (клуб, роль):")
    bot.register_next_step_handler(msg, admin_add_finish, name, st, photo_id)

def admin_add_finish(message, name, st, photo_id):
    global cards
    # Перезаписываем если имя совпадает
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': st, 'photo': photo_id, 'desc': message.text})
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Игрок **{name}** успешно добавлен в базу!", reply_markup=admin_kb(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def admin_delete_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите имя игрока для удаления:")
        bot.register_next_step_handler(msg, admin_delete_finish)

def admin_delete_finish(message):
    global cards
    cards = [c for c in cards if c['name'].lower() != message.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, "✅ Карта удалена.", reply_markup=admin_kb())

# --- ЗАПУСК ---
print("Бот запущен и готов к работе...")
bot.infinity_polling()
