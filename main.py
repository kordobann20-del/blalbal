import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] НАСТРОЙКИ БОТА ---
TOKEN = "8728235198:AAGMHfBZw0UCnOk_0DUsB7VbDt8fiWua8Ik"
ADMINS = ["verybigsun", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Названия файлов для хранения данных
FILES = {
    'cards': 'cards.json', 
    'colls': 'colls.json', 
    'users': 'users.json'
}

# Шансы выпадения и количество очков за рейтинг (звезды)
STATS = {
    1: {"chance": 40, "score": 1000},
    2: {"chance": 30, "score": 3000},
    3: {"chance": 20, "score": 5000},
    4: {"chance": 10, "score": 8000},
    5: {"chance": 5, "score": 15000}
}

# --- [2] РАБОТА С БАЗОЙ ДАННЫХ (JSON) ---

def load_db(key):
    """Загрузка данных из файлов"""
    if not os.path.exists(FILES[key]):
        # Если файла нет, создаем пустой (список для карт/коллекций, словарь для юзеров)
        default_data = [] if key != 'users' else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key != 'users' else {}

def save_db(data, key):
    """Сохранение данных в файлы"""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация данных при запуске
cards = load_db('cards')
user_colls = load_db('colls')
users_data = load_db('users')
cooldowns = {}

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def is_admin(user):
    """Проверка, является ли пользователь админом"""
    if user.username:
        return user.username.lower() in [a.lower() for a in ADMINS]
    return False

def get_main_keyboard(user):
    """Главное меню бота"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_roll = types.KeyboardButton("🎰 Крутить карту")
    btn_coll = types.KeyboardButton("🗂 Коллекция")
    btn_top = types.KeyboardButton("🏆 Топ по очкам")
    
    markup.row(btn_roll, btn_coll)
    markup.row(btn_top)
    
    # Если зашел админ, добавляем кнопку панели
    if is_admin(user):
        btn_admin = types.KeyboardButton("🛠 Админ-панель")
        markup.add(btn_admin)
        
    return markup

# --- [4] ОСНОВНЫЕ КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def command_start(message):
    uid = str(message.from_user.id)
    # Автоматическое добавление пользователя в базу без лишних вопросов
    if uid not in users_data:
        users_data[uid] = {
            "score": 0, 
            "username": message.from_user.username or f"id{uid}"
        }
        save_db(users_data, 'users')
    
    bot.send_message(
        message.chat.id, 
        f"⚽️ Добро пожаловать, {message.from_user.first_name}!\nЖми кнопки в меню, чтобы начать игру.", 
        reply_markup=get_main_keyboard(message.from_user)
    )

# --- [5] ЛОГИКА ВЫПАДЕНИЯ КАРТ ---

@bot.message_handler(func=lambda message: message.text == "🎰 Крутить карту")
def handle_roll(message):
    uid = str(message.from_user.id)
    now = time.time()
    
    # Проверка КД (3 часа), если не админ
    if not is_admin(message.from_user):
        if uid in cooldowns:
            time_passed = now - cooldowns[uid]
            if time_passed < 10800:
                seconds_left = int(10800 - time_passed)
                hours = seconds_left // 3600
                minutes = (seconds_left % 3600) // 60
                return bot.send_message(message.chat.id, f"⏳ КД! Приходи через {hours}ч {minutes}м.")

    if not cards:
        return bot.send_message(message.chat.id, "❌ В игре пока нет ни одной карточки.")

    # Выбор рейтинга на основе шансов
    weights = [s['chance'] for s in STATS.values()]
    stars_list = list(STATS.keys())
    chosen_stars = random.choices(stars_list, weights=weights)[0]
    
    # Фильтруем карты по выпавшим звездам
    available_cards = [c for c in cards if c['stars'] == chosen_stars]
    if not available_cards:
        available_cards = cards # Если карт с таким рейтингом нет, берем любую

    won_card = random.choice(available_cards)
    cooldowns[uid] = now # Ставим КД
    
    # Проверка на повторку
    if uid not in user_colls:
        user_colls[uid] = []
    
    is_duplicate = any(c['name'] == won_card['name'] for c in user_colls[uid])
    
    # Начисление очков (за повторку только 30%)
    base_points = STATS[won_card['stars']]['score']
    earned_points = int(base_points * 0.3) if is_duplicate else base_points
    
    if not is_duplicate:
        user_colls[uid].append(won_card)
        save_db(user_colls, 'colls')
    
    # Обновляем счет и юзернейм
    users_data[uid]['score'] += earned_points
    users_data[uid]['username'] = message.from_user.username or f"id{uid}"
    save_db(users_data, 'users')
    
    status_text = "🔄 ПОВТОРКА" if is_duplicate else "✨ НОВАЯ КАРТА"
    caption = (
        f"⚽️ *{won_card['name']}* ({status_text})\n\n"
        f"🎯 Позиция: {won_card['pos']}\n"
        f"📊 Рейтинг: {'⭐' * won_card['stars']}\n\n"
        f"💠 Очки: +{earned_points:,} | Всего: {users_data[uid]['score']:,}"
    )
    
    bot.send_photo(message.chat.id, won_card['photo'], caption=caption, parse_mode="Markdown")

# --- [6] ТОП И КОЛЛЕКЦИЯ ---

@bot.message_handler(func=lambda message: message.text == "🏆 Топ по очкам")
def handle_top(message):
    # Сортировка всех юзеров по убыванию очков
    sorted_users = sorted(users_data.values(), key=lambda x: x['score'], reverse=True)[:10]
    
    text = "🏆 **ТОП-10 ЛУЧШИХ ИГРОКОВ:**\n\n"
    for index, user in enumerate(sorted_users, 1):
        # Если юзернейм начинается на id, значит у игрока нет @username
        username = user['username']
        display_name = f"@{username}" if not username.startswith("id") else username
        text += f"{index}. {display_name} — `{user['score']:,}` очков\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🗂 Коллекция")
def handle_collection(message):
    markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        btn = types.InlineKeyboardButton(text="⭐" * i, callback_data=f"view_stars_{i}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, "Выберите рейтинг карточек для просмотра:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_stars_"))
def callback_view_collection(call):
    stars = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    
    my_cards = [c for c in user_colls.get(uid, []) if c['stars'] == stars]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас пока нет карточек этого рейтинга!", show_alert=True)
    
    card_list = "\n".join([f"• {c['name']} ({c['pos']})" for c in my_cards])
    bot.send_message(call.message.chat.id, f"🗂 **Ваши карты {stars}⭐:**\n\n{card_list}", parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [7] АДМИН-ПАНЕЛЬ (УПРАВЛЕНИЕ) ---

@bot.message_handler(func=lambda message: message.text == "🛠 Админ-панель")
def handle_admin_main(message):
    if not is_admin(message.from_user): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "🗑 Удалить карту")
    markup.row("📝 Изменить карту")
    markup.add("🏠 Назад")
    
    bot.send_message(message.chat.id, "🛠 **Меню администратора:**", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🏠 Назад")
def handle_back_home(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_keyboard(message.from_user))

# --- ДОБАВЛЕНИЕ КАРТЫ ---

@bot.message_handler(func=lambda message: message.text == "➕ Добавить карту")
def admin_add_start(message):
    if not is_admin(message.from_user): return
    msg = bot.send_message(message.chat.id, "Введите ИМЯ игрока:")
    bot.register_next_step_handler(msg, admin_add_get_pos)

def admin_add_get_pos(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"Введите ПОЗИЦИЮ для {name}:")
    bot.register_next_step_handler(msg, admin_add_get_stars, name)

def admin_add_get_stars(message, name):
    pos = message.text
    msg = bot.send_message(message.chat.id, "Введите РЕЙТИНГ (число от 1 до 5):")
    bot.register_next_step_handler(msg, admin_add_get_photo, name, pos)

def admin_add_get_photo(message, name, pos):
    try:
        stars = int(message.text)
        if not (1 <= stars <= 5): raise ValueError
        msg = bot.send_message(message.chat.id, "Отправьте ФОТО для карточки:")
        bot.register_next_step_handler(msg, admin_add_finish, name, pos, stars)
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно ввести число от 1 до 5. Попробуйте снова через меню.")

def admin_add_finish(message, name, pos, stars):
    if not message.photo:
        return bot.send_message(message.chat.id, "❌ Вы не отправили фото. Операция отменена.")
    
    new_card = {
        "name": name, 
        "pos": pos, 
        "stars": stars, 
        "photo": message.photo[-1].file_id
    }
    cards.append(new_card)
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Карточка {name} успешно добавлена в игру!")

# --- УДАЛЕНИЕ КАРТЫ ---

@bot.message_handler(func=lambda message: message.text == "🗑 Удалить карту")
def admin_delete_list(message):
    if not is_admin(message.from_user): return
    if not cards: return bot.send_message(message.chat.id, "Карт нет.")
    
    markup = types.InlineKeyboardMarkup()
    for card in cards:
        btn = types.InlineKeyboardButton(text=f"❌ {card['name']}", callback_data=f"del_card_{card['name']}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, "Выберите карту для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_card_"))
def admin_delete_confirm(call):
    card_name = call.data.split("_")[2]
    global cards
    cards = [c for c in cards if c['name'] != card_name]
    save_db(cards, 'cards')
    bot.edit_message_text(f"✅ Карточка '{card_name}' была удалена из базы.", call.message.chat.id, call.message.message_id)

# --- ИЗМЕНЕНИЕ КАРТЫ ---

@bot.message_handler(func=lambda message: message.text == "📝 Изменить карту")
def admin_edit_list(message):
    if not is_admin(message.from_user): return
    if not cards: return bot.send_message(message.chat.id, "Карт нет.")
    
    markup = types.InlineKeyboardMarkup()
    for card in cards:
        btn = types.InlineKeyboardButton(text=card['name'], callback_data=f"select_edit_{card['name']}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, "Какую карту хотите изменить?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_edit_"))
def admin_edit_menu(call):
    card_name = call.data.split("_")[2]
    
    markup = types.InlineKeyboardMarkup()
    btn_name = types.InlineKeyboardButton("Название", callback_data=f"prop_name_{card_name}")
    btn_rate = types.InlineKeyboardButton("Рейтинг", callback_data=f"prop_star_{card_name}")
    btn_phot = types.InlineKeyboardButton("Фото", callback_data=f"prop_photo_{card_name}")
    
    markup.row(btn_name, btn_rate)
    markup.add(btn_phot)
    
    bot.edit_message_text(f"Карта: *{card_name}*\nЧто именно нужно изменить?", 
                          call.message.chat.id, call.message.message_id, 
                          reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("prop_"))
def admin_edit_input_step(call):
    data_parts = call.data.split("_")
    property_type = data_parts[1]
    card_name = data_parts[2]
    
    text_map = {
        "name": "новое ИМЯ",
        "star": "новый РЕЙТИНГ (1-5)",
        "photo": "новое ФОТО"
    }
    
    msg = bot.send_message(call.message.chat.id, f"Введите {text_map[property_type]} для карточки {card_name}:")
    bot.register_next_step_handler(msg, admin_edit_save, property_type, card_name)

def admin_edit_save(message, property_type, card_name):
    # Ищем карту в списке
    for card in cards:
        if card['name'] == card_name:
            if property_type == "name":
                card['name'] = message.text
            elif property_type == "star":
                try:
                    val = int(message.text)
                    if 1 <= val <= 5: card['stars'] = val
                    else: raise ValueError
                except: return bot.send_message(message.chat.id, "❌ Ошибка! Нужно число 1-5.")
            elif property_type == "photo":
                if message.photo:
                    card['photo'] = message.photo[-1].file_id
                else:
                    return bot.send_message(message.chat.id, "❌ Это не фото!")
            break
            
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Данные карточки {card_name} обновлены!")

# --- [8] ЗАПУСК ---

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()
