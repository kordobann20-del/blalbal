import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] ОСНОВНЫЕ НАСТРОЙКИ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
DB_FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json',
    'bans': 'bans.json',
    'promos': 'promos.json'
}

# ШАНСЫ И СТАТИСТИКА РЕДКОСТИ
# Шансы: 1 - 30%, 2 - 30%, 3 - 25%, 4 - 10%, 5 - 5%
RARITY_STATS = {
    1: {"chance": 30, "score": 1000, "atk": 100},   # Обычные
    2: {"chance": 30, "score": 3000, "atk": 450},   # Необычные
    3: {"chance": 25, "score": 7500, "atk": 1000},  # Редкие
    4: {"chance": 10, "score": 15000, "atk": 2500}, # Эпические
    5: {"chance": 5,  "score": 30000, "atk": 5000}  # Легендарные
}

# Названия позиций для вывода пользователю
POSITIONS_RU = {
    "ГК": "Вратарь", 
    "ЛЗ": "Левый Защитник", 
    "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник", 
    "ЛВ": "Левый Вингер", 
    "ПВ": "Правый Вингер", 
    "КФ": "Нападающий"
}

# Схемы слотов для состава (7 игроков)
SQUAD_SLOTS = {
    0: {"label": "🧤 ГК (Вратарь)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ (Защитник)", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ (Защитник)", "code": "ПЗ"},
    3: {"label": "👟 ЦП (Полузащитник)", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ (Вингер)", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ (Вингер)", "code": "ПВ"},
    6: {"label": "🎯 КФ (Нападающий)", "code": "КФ"}
}

# Словари для кулдаунов (в оперативной памяти)
roll_cooldowns = {}
pvp_cooldowns = {}

# --- [2] ФУНКЦИИ РАБОТЫ С ДАННЫМИ ---

def load_data(key):
    """Загружает данные из указанного JSON файла."""
    file_path = DB_FILES[key]
    if not os.path.exists(file_path):
        # Создаем пустой файл, если его нет
        default_content = [] if key in ['cards', 'bans'] else {}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_content, f, ensure_ascii=False, indent=4)
        return default_content
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Если файл поврежден, возвращаем пустую структуру
            return [] if key in ['cards', 'bans'] else {}

def save_data(data, key):
    """Сохраняет данные в указанный JSON файл."""
    file_path = DB_FILES[key]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---

def is_admin(user):
    """Проверяет, является ли пользователь администратором."""
    if not user.username:
        return False
    return user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    """Проверяет, находится ли пользователь в черном списке."""
    ban_list = load_data('bans')
    uid = str(user.id)
    username = user.username.lower() if user.username else "no_username"
    if uid in ban_list or username in ban_list:
        return True
    return False

def get_team_power(uid):
    """Считает суммарную атаку всех игроков в составе."""
    squad_db = load_data('squads')
    user_squad = squad_db.get(str(uid), [None] * 7)
    total_power = 0
    for player in user_squad:
        if player:
            stars = player.get('stars', 1)
            total_power += RARITY_STATS[stars]['atk']
    return total_power

# --- [4] КЛАВИАТУРЫ (ИНТЕРФЕЙС) ---

def get_main_keyboard(uid):
    """Главное меню бота."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_roll = types.KeyboardButton("🎰 Крутить карту")
    btn_coll = types.KeyboardButton("🗂 Коллекция")
    btn_squad = types.KeyboardButton("📋 Состав")
    btn_profile = types.KeyboardButton("👤 Профиль")
    btn_top = types.KeyboardButton("🏆 Топ очков")
    btn_pvp = types.KeyboardButton("🏟 ПВП Арена")
    btn_promo = types.KeyboardButton("🎟 Промокод")
    btn_ref = types.KeyboardButton("👥 Рефералы")
    
    markup.add(btn_roll, btn_coll)
    markup.add(btn_squad, btn_profile)
    markup.add(btn_top, btn_pvp)
    markup.add(btn_promo, btn_ref)
    
    # Кнопка админки видна только избранным
    try:
        chat_info = bot.get_chat(uid)
        if is_admin(chat_info):
            markup.add(types.KeyboardButton("🛠 Админ-панель"))
    except:
        pass
    return markup

def get_cancel_keyboard():
    """Клавиатура для отмены действий."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    return markup

def get_admin_keyboard():
    """Клавиатура управления для администраторов."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ Добавить карту"))
    markup.add(types.KeyboardButton("📝 Изменить карту"))
    markup.add(types.KeyboardButton("🗑 Удалить карту"))
    markup.add(types.KeyboardButton("🎟 +Промокод"))
    markup.add(types.KeyboardButton("🚫 Забанить"))
    markup.add(types.KeyboardButton("✅ Разбанить"))
    markup.add(types.KeyboardButton("🧨 Обнулить бота"))
    markup.add(types.KeyboardButton("🏠 Назад в меню"))
    return markup

# --- [5] ОБРАБОТКА КОМАНДЫ /START И РЕФЕРАЛОВ ---

@bot.message_handler(commands=['start'])
def command_start(message):
    if is_banned(message.from_user):
        bot.send_message(message.chat.id, "🚫 Доступ заблокирован администрацией.")
        return

    user_db = load_data('users')
    uid = str(message.from_user.id)
    
    # Проверка на реферальную ссылку
    referred_by = None
    command_args = message.text.split()
    if len(command_args) > 1:
        referred_by = command_args[1]

    if uid not in user_db:
        # Регистрация нового игрока
        username_display = f"@{message.from_user.username}" if message.from_user.username else f"id{uid}"
        user_db[uid] = {
            "nick": message.from_user.first_name,
            "username": username_display,
            "score": 0,
            "free_rolls": 0,
            "bonus_luck": 1.0,
            "referals_count": 0,
            "used_promos": []
        }
        
        # Награда пригласившему
        if referred_by and referred_by in user_db and referred_by != uid:
            user_db[referred_by]["score"] += 5000
            user_db[referred_by]["referals_count"] += 1
            try:
                bot.send_message(int(referred_by), "👥 По вашей ссылке зарегистрировался новый игрок! Вам начислено 5,000 очков.")
            except:
                pass

    save_data(user_db, 'users')
    welcome_text = (
        f"⚽️ Привет, {message.from_user.first_name}!\n\n"
        "Это футбольный бот, где ты можешь собирать карточки игроков, "
        "формировать состав и сражаться с другими участниками.\n\n"
        "Жми '🎰 Крутить карту', чтобы начать!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def view_referals(message):
    if is_banned(message.from_user): return
    uid = message.from_user.id
    user_db = load_data('users')
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={uid}"
    
    count = user_db.get(str(uid), {}).get("referals_count", 0)
    
    text = (
        "👥 **ПАРТНЕРСКАЯ ПРОГРАММА**\n\n"
        "Приглашайте друзей и получайте бонусы за их активность!\n"
        "За каждого приглашенного вы получаете **5,000 очков**.\n\n"
        f"Вы пригласили: **{count}** человек.\n\n"
        "Ваша уникальная ссылка:\n"
        f"`{ref_link}`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- [6] ПРОМОКОДЫ И БЕСПЛАТНЫЕ ПРОКРУТЫ ---

@bot.message_handler(func=lambda m: m.text == "🎟 Промокод")
def enter_promo_start(message):
    if is_banned(message.from_user): return
    msg = bot.send_message(message.chat.id, "🎟 Введите ваш промокод:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, process_promo_activation)

def process_promo_activation(message):
    if message.text == "❌ Отмена":
        return global_cancel_action(message)
    
    promo_code = message.text.strip().upper()
    uid = str(message.from_user.id)
    user_db = load_data('users')
    promo_db = load_data('promos')
    
    if promo_code not in promo_db:
        bot.send_message(message.chat.id, "❌ Такого промокода не существует.", reply_markup=get_main_keyboard(uid))
        return

    if promo_code in user_db[uid].get('used_promos', []):
        bot.send_message(message.chat.id, "❌ Вы уже активировали этот код ранее.", reply_markup=get_main_keyboard(uid))
        return

    data = promo_db[promo_code]
    bonus_type = data['type']
    bonus_val = data['value']
    
    if bonus_type == 'rolls':
        user_db[uid]['free_rolls'] = user_db[uid].get('free_rolls', 0) + int(bonus_val)
        response = f"✅ Активировано! Вы получили **{int(bonus_val)} бесплатных прокрутов**, которые игнорируют КД!"
    elif bonus_type == 'luck':
        user_db[uid]['bonus_luck'] = float(bonus_val)
        response = f"✅ Активировано! Ваша удача увеличена в **{bonus_val} раз** на следующую крутку!"
    else:
        user_db[uid]['score'] += int(bonus_val)
        response = f"✅ Активировано! На ваш баланс начислено **{int(bonus_val):,} очков**."

    user_db[uid].setdefault('used_promos', []).append(promo_code)
    save_data(user_db, 'users')
    bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard(uid), parse_mode="Markdown")

# --- [7] ЛОГИКА ВЫПАДЕНИЯ КАРТ (ROLL) ---

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card_handler(message):
    if is_banned(message.from_user): return
    uid = str(message.from_user.id)
    user_db = load_data('users')
    now = time.time()
    
    user_free_rolls = user_db[uid].get('free_rolls', 0)
    
    # ПРОВЕРКА КУЛДАУНА
    # Если есть бесплатные прокруты - КД не проверяем
    if not is_admin(message.from_user) and user_free_rolls <= 0:
        if uid in roll_cooldowns:
            time_passed = now - roll_cooldowns[uid]
            if time_passed < 10800: # 3 часа в секундах
                remaining = int(10800 - time_passed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                bot.send_message(message.chat.id, f"⏳ Перерыв! Ваши скауты отдыхают. Попробуйте через {hours}ч {minutes}м.\n\n🎟 Или используйте промокод на бесплатные прокруты!")
                return

    cards_pool = load_data('cards')
    if not cards_pool:
        bot.send_message(message.chat.id, "❌ К сожалению, в базе еще нет ни одной карточки.")
        return

    # РАСЧЕТ ВЫПАДЕНИЯ (Удача)
    luck_multiplier = user_db[uid].get('bonus_luck', 1.0)
    rarities = sorted(RARITY_STATS.keys())
    weights = []
    for r in rarities:
        chance = RARITY_STATS[r]['chance']
        if r >= 4: # Эпики и легенды получают бонус от удачи
            chance *= luck_multiplier
        weights.append(chance)

    selected_rarity = random.choices(rarities, weights=weights)[0]
    available_cards = [c for c in cards_pool if c['stars'] == selected_rarity]
    
    # Если карт такой редкости нет, берем любую
    if not available_cards:
        available_cards = cards_pool
        
    won_card = random.choice(available_cards)
    
    # ОБРАБОТКА ПОПЫТКИ
    if user_free_rolls > 0:
        user_db[uid]['free_rolls'] -= 1
        roll_info = f"🎫 Использован бонусный прокрут! Осталось: {user_db[uid]['free_rolls']}"
    else:
        roll_cooldowns[uid] = now
        roll_info = "⏳ Кулдаун на 3 часа запущен."

    # Сброс удачи после использования
    user_db[uid]['bonus_luck'] = 1.0

    # Проверка на повторку
    collections = load_data('colls')
    if uid not in collections:
        collections[uid] = []
    
    is_duplicate = any(c['name'] == won_card['name'] for c in collections[uid])
    
    if is_duplicate:
        points_gain = int(RARITY_STATS[won_card['stars']]['score'] * 0.3)
        status = "🔄 Повторная карта (30% стоимости начислено)"
    else:
        points_gain = RARITY_STATS[won_card['stars']]['score']
        status = "✨ Новое пополнение в коллекции!"
        collections[uid].append(won_card)
        save_data(collections, 'colls')

    user_db[uid]['score'] += points_gain
    save_data(user_db, 'users')

    # Визуальное оформление
    stars_display = "⭐️" * won_card['stars']
    pos_name = POSITIONS_RU.get(won_card['pos'].upper(), won_card['pos'])
    
    caption = (
        f"⚽️ **{won_card['name']}**\n\n"
        f"📊 Рейтинг: {stars_display}\n"
        f"🎯 Позиция: {pos_name}\n\n"
        f"💠 {status}\n"
        f"💰 Очки: +{points_gain:,}\n"
        f"📈 Баланс: {user_db[uid]['score']:,}\n\n"
        f"{roll_info}"
    )
    bot.send_photo(message.chat.id, won_card['photo'], caption=caption, parse_mode="Markdown")

# --- [8] ПВП АРЕНА (МАТЧИ) ---

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def pvp_arena_menu(message):
    if is_banned(message.from_user): return
    uid = str(message.from_user.id)
    now = time.time()
    
    if not is_admin(message.from_user):
        if uid in pvp_cooldowns and now - pvp_cooldowns[uid] < 900:
            rem = int(900 - (now - pvp_cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Ваши футболисты вымотались. Следующий матч через {rem//60} мин.")
            return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Искать случайный матч", callback_data="arena_random"))
    markup.add(types.InlineKeyboardButton("🔍 Вызвать игрока по ID", callback_data="arena_id"))
    
    bot.send_message(message.chat.id, "🏟 **ГЛАВНЫЙ СТАДИОН**\n\nЗдесь вы можете сравнить силу своих команд. Победа приносит 1,000 очков!", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "arena_random")
def handle_random_pvp(call):
    user_db = load_data('users')
    my_id = str(call.from_user.id)
    my_power = get_team_power(my_id)
    
    if my_power == 0:
        bot.answer_callback_query(call.id, "❌ Ваш состав пуст! Сначала соберите команду.", show_alert=True)
        return

    # Выбор оппонента (кто уже имеет команду)
    opponents = [uid for uid in user_db if uid != my_id and get_team_power(uid) > 0]
    
    if not opponents:
        bot.answer_callback_query(call.id, "❌ Достойных соперников пока не нашлось.", show_alert=True)
        return
        
    enemy_id = random.choice(opponents)
    execute_match_logic(call.message.chat.id, my_id, enemy_id)

def execute_match_logic(chat_id, p1_id, p2_id):
    """Рассчитывает исход матча между двумя игроками."""
    user_db = load_data('users')
    p1_power = get_team_power(p1_id)
    p2_power = get_team_power(p2_id)
    
    # Шансы зависят от силы (степень 1.2 делает разрыв более значимым)
    p1_weight = p1_power ** 1.2
    p2_weight = p2_power ** 1.2
    
    winner_id = random.choices([p1_id, p2_id], weights=[p1_weight, p2_weight])[0]
    
    # Награда
    user_db[winner_id]['score'] += 1000
    save_data(user_db, 'users')
    
    # Установка КД инициатору
    pvp_cooldowns[p1_id] = time.time()

    winner_name = user_db[winner_id]['username']
    
    match_text = (
        "🏟 **РЕЗУЛЬТАТЫ МАТЧА**\n\n"
        f"🏠 {user_db[p1_id]['nick']} (Сила: {p1_power})\n"
        "       **против**\n"
        f"🚀 {user_db[p2_id]['nick']} (Сила: {p2_power})\n\n"
        f"🏆 Победитель: **{winner_name}**\n"
        "💰 Приз: +1,000 очков"
    )
    bot.send_message(chat_id, match_text, parse_mode="Markdown")

# --- [9] ПРОФИЛЬ, ТОП И КОЛЛЕКЦИЯ ---

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def user_profile_view(message):
    if is_banned(message.from_user): return
    uid = str(message.from_user.id)
    u_db = load_data('users')
    colls = load_data('colls')
    
    user = u_db[uid]
    coll_size = len(colls.get(uid, []))
    
    profile_text = (
        f"👤 **ВАШ ПРОФИЛЬ**\n\n"
        f"📝 Имя: {user['nick']}\n"
        f"🔗 Логин: {user['username']}\n\n"
        f"💠 Баланс очков: `{user['score']:,}`\n"
        f"🗂 В коллекции: {coll_size} карт\n"
        f"🛡 Сила состава: **{get_team_power(uid)}**\n"
        f"🎫 Бесплатных круток: **{user.get('free_rolls', 0)}**"
    )
    bot.send_message(message.chat.id, profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def global_leaderboard(message):
    if is_banned(message.from_user): return
    user_db = load_data('users')
    # Сортировка по убыванию очков
    sorted_users = sorted(user_db.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    leader_text = "🏆 **ТОП-10 ЛУЧШИХ ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        leader_text += f"{i}. {data['username']} — `{data['score']:,}` очков\n"
    
    bot.send_message(message.chat.id, leader_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def user_collection_menu(message):
    if is_banned(message.from_user): return
    markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(f"{'⭐️'*i} Просмотреть", callback_data=f"view_stars_{i}"))
    
    bot.send_message(message.chat.id, "🗂 **ВАША КОЛЛЕКЦИЯ**\n\nВыберите редкость карт для просмотра:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_stars_"))
def show_collection_by_stars(call):
    star_level = int(call.data.split("_")[-1])
    uid = str(call.from_user.id)
    user_cards = [c for c in load_data('colls').get(uid, []) if c['stars'] == star_level]
    
    if not user_cards:
        bot.answer_callback_query(call.id, f"У вас еще нет карт {star_level}⭐️", show_alert=True)
        return
    
    list_text = f"🗂 **ВАШИ КАРТЫ {star_level}⭐️:**\n\n"
    for c in user_cards:
        list_text += f"• {c['name']} ({c['pos']})\n"
        
    bot.send_message(call.message.chat.id, list_text, parse_mode="Markdown")

# --- [10] УПРАВЛЕНИЕ СОСТАВОМ (SQUAD) ---

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_management_view(message):
    if is_banned(message.from_user): return
    bot.send_message(message.chat.id, "📋 **РЕДАКТИРОВАНИЕ СОСТАВА**\n\nНажмите на позицию, чтобы поставить туда игрока из вашей коллекции.", reply_markup=generate_squad_markup(message.from_user.id), parse_mode="Markdown")

def generate_squad_markup(uid):
    """Генерирует инлайн-кнопки для состава игрока."""
    squad_db = load_data('squads')
    user_squad = squad_db.get(str(uid), [None] * 7)
    markup = types.InlineKeyboardMarkup()
    
    for i in range(7):
        slot_info = SQUAD_SLOTS[i]
        player = user_squad[i]
        
        if player:
            btn_text = f"{slot_info['label']}: {player['name']} ({player['stars']}⭐)"
        else:
            btn_text = f"{slot_info['label']}: ❌ Не назначен"
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"squad_edit_{i}"))
    return markup

@bot.callback_query_handler(func=lambda c: c.data.startswith("squad_edit_"))
def select_player_for_squad(call):
    slot_index = int(call.data.split("_")[-1])
    uid = str(call.from_user.id)
    required_pos = SQUAD_SLOTS[slot_index]["code"]
    
    user_collection = load_data('colls').get(uid, [])
    # Фильтруем карты по подходящей позиции
    matching_cards = [c for c in user_collection if c['pos'].upper() == required_pos]
    
    if not matching_cards:
        bot.answer_callback_query(call.id, f"У вас нет игроков позиции {required_pos}!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup()
    for card in matching_cards:
        markup.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"squad_set_{slot_index}_{card['name']}"))
    
    markup.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"squad_set_{slot_index}_none"))
    
    bot.edit_message_text(f"Выберите игрока на позицию **{required_pos}**:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("squad_set_"))
def save_player_to_squad(call):
    parts = call.data.split("_")
    slot_idx = int(parts[2])
    player_name = parts[3]
    uid = str(call.from_user.id)
    
    squad_db = load_data('squads')
    if uid not in squad_db:
        squad_db[uid] = [None] * 7
        
    if player_name == "none":
        squad_db[uid][slot_idx] = None
    else:
        user_coll = load_data('colls').get(uid, [])
        # Ищем карту в коллекции по имени
        selected_card = next((c for c in user_coll if c['name'] == player_name), None)
        squad_db[uid][slot_idx] = selected_card
        
    save_data(squad_db, 'squads')
    bot.edit_message_text("✅ Изменения сохранены!", call.message.chat.id, call.message.message_id, reply_markup=generate_squad_markup(uid))

# --- [11] АДМИН-ПАНЕЛЬ: УПРАВЛЕНИЕ КАРТАМИ И БОТОМ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_admin_panel(message):
    if not is_admin(message.from_user): return
    bot.send_message(message.chat.id, "🛠 **РЕЖИМ АДМИНИСТРАТОРА**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# [ДОБАВЛЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_card_step1(message):
    if not is_admin(message.from_user): return
    msg = bot.send_message(message.chat.id, "Введите ФИО футболиста:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, admin_add_card_step2)

def admin_add_card_step2(message):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    name = message.text
    msg = bot.send_message(message.chat.id, "Введите позицию (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):")
    bot.register_next_step_handler(msg, admin_add_card_step3, name)

def admin_add_card_step3(message, name):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    pos = message.text.upper()
    msg = bot.send_message(message.chat.id, "Введите редкость (число от 1 до 5 звезд):")
    bot.register_next_step_handler(msg, admin_add_card_step4, name, pos)

def admin_add_card_step4(message, name, pos):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    try:
        stars = int(message.text)
        msg = bot.send_message(message.chat.id, "Пришлите ФОТО для карточки:")
        bot.register_next_step_handler(msg, admin_add_card_final, name, pos, stars)
    except:
        bot.send_message(message.chat.id, "Ошибка! Введите число.")

def admin_add_card_final(message, name, pos, stars):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото! Начните заново.")
        return
    
    cards_db = load_data('cards')
    cards_db.append({
        "name": name,
        "pos": pos,
        "stars": stars,
        "photo": message.photo[-1].file_id
    })
    save_data(cards_db, 'cards')
    bot.send_message(message.chat.id, f"✅ Карта {name} успешно создана!", reply_markup=get_admin_keyboard())

# [ИЗМЕНЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_card_list(message):
    if not is_admin(message.from_user): return
    db = load_data('cards')
    if not db:
        bot.send_message(message.chat.id, "База пуста.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for card in db:
        markup.add(types.InlineKeyboardButton(f"⚙️ {card['name']}", callback_data=f"medit_select_{card['name']}"))
    bot.send_message(message.chat.id, "Выберите карту для редактирования:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("medit_select_"))
def admin_edit_field_choice(call):
    card_name = call.data.replace("medit_select_", "")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Имя", callback_data=f"medit_field_{card_name}_name"))
    markup.add(types.InlineKeyboardButton("Позиция", callback_data=f"medit_field_{card_name}_pos"))
    markup.add(types.InlineKeyboardButton("Звезды", callback_data=f"medit_field_{card_name}_stars"))
    markup.add(types.InlineKeyboardButton("Фото", callback_data=f"medit_field_{card_name}_photo"))
    bot.edit_message_text(f"Что изменить у игрока {card_name}?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("medit_field_"))
def admin_edit_input_start(call):
    # Формат: medit_field_ИмяКарты_Поле
    parts = call.data.split("_")
    card_name = parts[2]
    field = parts[3]
    
    msg = bot.send_message(call.message.chat.id, f"Введите новое значение для поля **{field}**:", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_edit_save_process, card_name, field)

def admin_edit_save_process(message, card_name, field):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    
    db = load_data('cards')
    for c in db:
        if c['name'] == card_name:
            if field == "photo":
                if not message.photo:
                    bot.send_message(message.chat.id, "Ошибка! Нужно фото.")
                    return
                c[field] = message.photo[-1].file_id
            elif field == "stars":
                c[field] = int(message.text)
            else:
                c[field] = message.text if field != "pos" else message.text.upper()
            break
            
    save_data(db, 'cards')
    bot.send_message(message.chat.id, "✅ Данные карты обновлены!", reply_markup=get_admin_keyboard())

# [УДАЛЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_card_view(message):
    if not is_admin(message.from_user): return
    db = load_data('cards')
    markup = types.InlineKeyboardMarkup()
    for card in db:
        markup.add(types.InlineKeyboardButton(f"❌ {card['name']}", callback_data=f"mdel_confirm_{card['name']}"))
    bot.send_message(message.chat.id, "Выберите карту для УДАЛЕНИЯ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("mdel_confirm_"))
def admin_delete_card_exec(call):
    name = call.data.replace("mdel_confirm_", "")
    db = load_data('cards')
    new_db = [c for c in db if c['name'] != name]
    save_data(new_db, 'cards')
    bot.edit_message_text(f"🗑 Карта **{name}** удалена из базы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# [СОЗДАНИЕ ПРОМОКОДА]
@bot.message_handler(func=lambda m: m.text == "🎟 +Промокод")
def admin_add_promo_step1(message):
    if not is_admin(message.from_user): return
    msg = bot.send_message(message.chat.id, "Напишите слово-код (например: NEWYEAR):", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, admin_add_promo_step2)

def admin_add_promo_step2(message):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    code_name = message.text.strip().upper()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎫 Бесплатные прокруты", callback_data=f"apromo_type_{code_name}_rolls"))
    markup.add(types.InlineKeyboardButton("💠 Очки", callback_data=f"apromo_type_{code_name}_points"))
    markup.add(types.InlineKeyboardButton("🍀 Удача", callback_data=f"apromo_type_{code_name}_luck"))
    bot.send_message(message.chat.id, f"Выберите тип бонуса для `{code_name}`:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("apromo_type_"))
def admin_add_promo_step3(call):
    # apromo_type_КОД_ТИП
    parts = call.data.split("_")
    code_name = parts[2]
    code_type = parts[3]
    
    msg = bot.send_message(call.message.chat.id, f"Введите ЧИСЛО (количество {code_type}):")
    bot.register_next_step_handler(msg, admin_add_promo_final, code_name, code_type)

def admin_add_promo_final(message, code_name, code_type):
    try:
        val = float(message.text)
        db = load_data('promos')
        db[code_name] = {"type": code_type, "value": val}
        save_data(db, 'promos')
        bot.send_message(message.chat.id, f"✅ Промокод `{code_name}` на {code_type} успешно создан!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "Ошибка! Введите числовое значение.")

# --- [12] СИСТЕМА БАНОВ ---

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_start(message):
    if not is_admin(message.from_user): return
    msg = bot.send_message(message.chat.id, "Введите @username или ID для блокировки:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, process_ban_action, True)

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_start(message):
    if not is_admin(message.from_user): return
    msg = bot.send_message(message.chat.id, "Введите @username или ID для разблокировки:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, process_ban_action, False)

def process_ban_action(message, is_banning):
    if message.text == "❌ Отмена": return global_cancel_action(message)
    
    target = message.text.replace("@", "").lower().strip()
    ban_list = load_data('bans')
    
    if is_banning:
        if target not in ban_list:
            ban_list.append(target)
            msg = f"✅ Пользователь `{target}` заблокирован."
        else:
            msg = "Этот игрок уже в бане."
    else:
        if target in ban_list:
            ban_list.remove(target)
            msg = f"✅ Пользователь `{target}` разблокирован."
        else:
            msg = "Этого игрока нет в черном списке."
            
    save_data(ban_list, 'bans')
    bot.send_message(message.chat.id, msg, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- [13] СЛУЖЕБНЫЕ ФУНКЦИИ ---

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_confirm_view(message):
    if not is_admin(message.from_user): return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚨 ПОДТВЕРЖДАЮ УДАЛЕНИЕ", "❌ Отмена")
    bot.send_message(message.chat.id, "⚠️ **ВНИМАНИЕ!** Это действие удалит прогресс, коллекции и составы ВСЕХ игроков. Это нельзя отменить!", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚨 ПОДТВЕРЖДАЮ УДАЛЕНИЕ")
def admin_reset_execute(message):
    if not is_admin(message.from_user): return
    save_data({}, 'users')
    save_data({}, 'colls')
    save_data({}, 'squads')
    bot.send_message(message.chat.id, "🧨 База данных очищена. Все игроки обнулены.", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_to_main_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def global_cancel_action(message):
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=get_main_keyboard(message.from_user.id))

# Запуск бота в режиме бесконечного цикла
if __name__ == "__main__":
    print("Бот успешно запущен и готов к работе...")
    bot.infinity_polling()
