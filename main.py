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

# Футбольные позиции
POSITIONS = [
    "ГК (Вратарь)", 
    "ЛЗ (Левый защитник)", 
    "ПЗ (Правый защитник)", 
    "ЦП (Центральный полузащитник)", 
    "ЛВ (Левый вингер)", 
    "ПВ (Правый вингер)", 
    "КФ (Центральный форвард)"
]

# --- ФУНКЦИИ РАБОТЫ С ДАННЫМИ ---

def load_db(key):
    """Загрузка данных из JSON файла"""
    file_path = FILES[key]
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    """Сохранение данных в JSON файл"""
    file_path = FILES[key]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация баз данных
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

# --- КЛАВИАТУРЫ (МЕНЮ) ---

def get_main_keyboard(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена", "Премиум")
    # Проверка на админа
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Удалить карту")
    markup.row("Изменить карту", "Назад в меню")
    return markup

def get_squad_keyboard(user_id):
    user_id = str(user_id)
    markup = types.InlineKeyboardMarkup()
    # Получаем состав игрока или создаем пустой (7 слотов)
    squad = user_squads.get(user_id, [None] * 7)
    
    for i in range(7):
        # Если в слоте есть карта, пишем её имя, иначе "Пусто"
        if i < len(squad) and squad[i] is not None:
            card_name = squad[i]['name']
        else:
            card_name = "❌ Пусто"
        
        button_text = f"{POSITIONS[i]}: {card_name}"
        callback_data = f"select_slot_{i}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
    
    return markup

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    # Сохраняем юзера для поиска по @username на Арене
    if username:
        registered_users[username.lower()] = user_id
        save_db(registered_users, 'users')
        
    bot.send_message(
        message.chat.id, 
        "💎 **Добро пожаловать в футбольный симулятор!**\n\nСобирайте карточки игроков, выстраивайте тактику и побеждайте на арене.",
        reply_markup=get_main_keyboard(username),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_to_menu(message):
    bot.send_message(
        message.chat.id, 
        "Вы вернулись в главное меню.", 
        reply_markup=get_main_keyboard(message.from_user.username)
    )

@bot.message_handler(func=lambda m: m.text == "Премиум")
def show_premium(message):
    bot.send_message(
        message.chat.id, 
        "💎 **Премиум статус**\n\nДает возможность крутить карту без КД и уникальные карточки.\n\nДля покупки пишите: @verybigsun",
        parse_mode="Markdown"
    )

# --- БЛОК: СОСТАВ (ФУТБОЛЬНЫЕ ПОЗИЦИИ) ---

@bot.message_handler(func=lambda m: m.text == "Состав")
def show_squad_menu(message):
    bot.send_message(
        message.chat.id, 
        "⚔️ **Ваш боевой состав:**\nНажмите на позицию, чтобы выбрать игрока из вашей коллекции.",
        reply_markup=get_squad_keyboard(message.from_user.id),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_slot_"))
def handle_slot_selection(call):
    slot_index = int(call.data.split("_")[-1])
    user_id = str(call.from_user.id)
    
    # Получаем коллекцию игрока
    collection = user_colls.get(user_id, [])
    
    if not collection:
        bot.answer_callback_query(call.id, "Ваша коллекция пуста! Сначала выбейте карты.")
        return

    markup = types.InlineKeyboardMarkup()
    for card in collection:
        stars_str = "⭐" * card['stars']
        btn_text = f"{card['name']} ({stars_str})"
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"apply_{slot_index}_{card['name']}"))
    
    # Кнопка очистки слота
    markup.add(types.InlineKeyboardButton(text="🚫 Очистить позицию", callback_data=f"apply_{slot_index}_none"))
    
    bot.edit_message_text(
        f"Выберите игрока на позицию: {POSITIONS[slot_index]}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("apply_"))
def handle_card_application(call):
    data_parts = call.data.split("_")
    slot_index = int(data_parts[1])
    card_name = data_parts[2]
    user_id = str(call.from_user.id)
    
    if user_id not in user_squads:
        user_squads[user_id] = [None] * 7
    
    if card_name == "none":
        user_squads[user_id][slot_index] = None
        bot.answer_callback_query(call.id, "Позиция очищена")
    else:
        # Находим данные карты в коллекции пользователя
        selected_card = None
        for c in user_colls[user_id]:
            if c['name'] == card_name:
                selected_card = c
                break
        
        user_squads[user_id][slot_index] = selected_card
        bot.answer_callback_query(call.id, f"Игрок {card_name} установлен!")

    save_db(user_squads, 'squads')
    # Возвращаемся в меню состава
    bot.edit_message_text(
        "⚔️ **Ваш боевой состав обновлен:**",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_squad_keyboard(user_id),
        parse_mode="Markdown"
    )

# --- БЛОК: АДМИН-ПАНЕЛЬ (ДОБАВИТЬ, УДАЛИТЬ, ИЗМЕНИТЬ) ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def show_admin_panel(message):
    if message.from_user.username and message.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(message.chat.id, "Добро пожаловать в режим разработчика.", reply_markup=get_admin_keyboard())

# 1. Добавление карты
@bot.message_handler(func=lambda m: m.text == "Добавить карту")
def admin_add_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите название новой карты:")
        bot.register_next_step_handler(msg, admin_add_stars)

def admin_add_stars(message):
    card_name = message.text
    msg = bot.send_message(message.chat.id, f"Введите редкость (число от 1 до 5 звезд) для '{card_name}':")
    bot.register_next_step_handler(msg, admin_add_photo, card_name)

def admin_add_photo(message, card_name):
    try:
        stars = int(message.text)
        if not (1 <= stars <= 5): raise ValueError
        msg = bot.send_message(message.chat.id, f"Отправьте фотографию для карточки '{card_name}':")
        bot.register_next_step_handler(msg, admin_add_desc, card_name, stars)
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно ввести число от 1 до 5.")

def admin_add_desc(message, card_name, stars):
    if not message.photo:
        bot.send_message(message.chat.id, "Вы не отправили фото. Начните заново.")
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, f"Введите краткое описание (характеристики) игрока:")
    bot.register_next_step_handler(msg, admin_add_finish, card_name, stars, photo_id)

def admin_add_finish(message, card_name, stars, photo_id):
    description = message.text
    # Добавляем в список
    cards.append({
        'name': card_name,
        'stars': stars,
        'photo': photo_id,
        'desc': description
    })
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Карта '{card_name}' успешно создана!", reply_markup=get_admin_keyboard())

# 2. Удаление карты
@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def admin_delete_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите ТОЧНОЕ название карты, которую хотите удалить:")
        bot.register_next_step_handler(msg, admin_delete_finish)

def admin_delete_finish(message):
    target_name = message.text.lower()
    global cards
    initial_count = len(cards)
    cards = [c for c in cards if c['name'].lower() != target_name]
    
    if len(cards) < initial_count:
        save_db(cards, 'cards')
        bot.send_message(message.chat.id, f"✅ Карта '{message.text}' удалена из базы.", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Карта с таким названием не найдена.", reply_markup=get_admin_keyboard())

# 3. Изменение карты
@bot.message_handler(func=lambda m: m.text == "Изменить карту")
def admin_edit_start(message):
    if message.from_user.username in ADMINS:
        msg = bot.send_message(message.chat.id, "Введите название карты, данные которой нужно обновить:")
        bot.register_next_step_handler(msg, admin_add_stars) # Используем логику добавления (она перезапишет старую)

# --- ЗАПУСК БОТА ---

@bot.message_handler(func=lambda m: True)
def handle_other(message):
    # Заглушка для прочих сообщений или если кнопки не сработали
    if message.text == "Коллекция":
        # Простое уведомление
        bot.send_message(message.chat.id, "Используйте фильтры в меню коллекции.")

bot.infinity_polling()
