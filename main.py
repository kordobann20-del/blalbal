import telebot
from telebot import types
import random
import time
import json
import os

# ==============================================================================
# [1] НАСТРОЙКИ, ТОКЕН И АДМИНИСТРАТОРЫ
# ==============================================================================

# Твой токен бота
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"

# Список администраторов (username БЕЗ @)
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 

bot = telebot.TeleBot(TOKEN)

# Названия файлов для хранения данных (JSON базы)
DB_FILES = {
    'cards': 'cards.json',         # Все существующие карточки игроков
    'colls': 'collections.json',   # Коллекции (кто какими картами владеет)
    'squads': 'squads.json',       # Текущие составы из 7 позиций
    'users': 'users_data.json',     # Данные игроков (очки, рефералы, удача)
    'bans': 'bans.json',           # Черный список (ID и ники)
    'promos': 'promos.json'        # База активных промокодов
}

# ==============================================================================
# [2] КОНФИГУРАЦИЯ ИГРОВОГО БАЛАНСА
# ==============================================================================

# Характеристики редкостей: шансы, награды в очках и сила атаки (ATK)
RARITY_STATS = {
    1: {
        "chance": 35, 
        "score": 1000, 
        "atk": 100,
        "label": "Обычная"
    },
    2: {
        "chance": 30, 
        "score": 3000, 
        "atk": 450,
        "label": "Необычная"
    },
    3: {
        "chance": 20, 
        "score": 7500, 
        "atk": 1000,
        "label": "Редкая"
    },
    4: {
        "chance": 10, 
        "score": 15000, 
        "atk": 2500,
        "label": "Эпическая"
    },
    5: {
        "chance": 5,  
        "score": 30000, 
        "atk": 5000,
        "label": "Легендарная"
    }
}

# Словарь позиций для корректного отображения в интерфейсе
POSITIONS_RU = {
    "ГК": "Вратарь", 
    "ЛЗ": "Левый Защитник", 
    "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник", 
    "ЛВ": "Левый Вингер", 
    "ПВ": "Правый Вингер", 
    "КФ": "Нападающий"
}

# Структура игрового состава (7 обязательных слотов)
SQUAD_SLOTS = {
    0: {"label": "🧤 ГК (Вратарь)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ (Защитник)", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ (Защитник)", "code": "ПЗ"},
    3: {"label": "👟 ЦП (Полузащитник)", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ (Вингер)", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ (Вингер)", "code": "ПВ"},
    6: {"label": "🎯 КФ (Нападающий)", "code": "КФ"}
}

# Временные словари для хранения кулдаунов (ограничение времени действий)
roll_cooldowns = {}
pvp_cooldowns = {}

# ==============================================================================
# [3] УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ (JSON)
# ==============================================================================

def load_data(key):
    """
    Загружает данные из файла. Если файла нет или он пустой,
    создает структуру по умолчанию.
    """
    file_path = DB_FILES[key]
    if not os.path.exists(file_path):
        # Если это списки (карты, баны), создаем [], иначе {}
        default_structure = [] if key in ['cards', 'bans'] else {}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=4)
        return default_structure
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            content = f.read()
            if not content:
                return [] if key in ['cards', 'bans'] else {}
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return [] if key in ['cards', 'bans'] else {}

def save_data(data, key):
    """
    Сохраняет объект данных в соответствующий JSON файл.
    """
    file_path = DB_FILES[key]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# [4] СИСТЕМНЫЕ ПРОВЕРКИ И УТИЛИТЫ
# ==============================================================================

def is_admin(user_object):
    """Проверка на права администратора по списку ников."""
    if not user_object.username:
        return False
    username_lower = user_object.username.lower()
    admin_list_lower = [admin.lower() for admin in ADMINS]
    return username_lower in admin_list_lower

def is_banned(user_object):
    """Проверка, находится ли пользователь в черном списке по ID или нику."""
    ban_list = load_data('bans')
    user_id = str(user_object.id)
    user_name = user_object.username.lower() if user_object.username else "нет_ника"
    
    if user_id in ban_list or user_name in ban_list:
        return True
    return False

def get_team_power(user_id):
    """Расчет суммарной силы атаки (ATK) текущего состава игрока."""
    squad_db = load_data('squads')
    # Если состава нет, создаем пустой из 7 слотов
    user_squad = squad_db.get(str(user_id), [None] * 7)
    
    total_power = 0
    for player_card in user_squad:
        if player_card:
            # Получаем количество звезд и сопоставляем с ATK из настроек
            stars = player_card.get('stars', 1)
            total_power += RARITY_STATS[stars]['atk']
            
    return total_power

# ==============================================================================
# [5] ГЕНЕРАЦИЯ КНОПОК И МЕНЮ (KEYBOARDS)
# ==============================================================================

def get_main_keyboard(user_id):
    """Главное меню для обычного пользователя."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Кнопки основного функционала
    btn_roll = types.KeyboardButton("🎰 Крутить карту")
    btn_coll = types.KeyboardButton("🗂 Коллекция")
    btn_squad = types.KeyboardButton("📋 Состав")
    btn_profile = types.KeyboardButton("👤 Профиль")
    btn_top = types.KeyboardButton("🏆 Топ очков")
    btn_pvp = types.KeyboardButton("🏟 ПВП Арена")
    btn_promo = types.KeyboardButton("🎟 Промокод")
    btn_refs = types.KeyboardButton("👥 Рефералы")
    
    markup.add(btn_roll, btn_coll, btn_squad, btn_profile, btn_top, btn_pvp, btn_promo, btn_refs)
    
    # Если пользователь — админ, добавляем кнопку входа в панель управления
    try:
        user_info = bot.get_chat(user_id)
        if is_admin(user_info):
            markup.add(types.KeyboardButton("🛠 Админ-панель"))
    except:
        pass
        
    return markup

def get_admin_keyboard():
    """Специальное меню для администраторов."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Кнопки управления контентом
    add_card = types.KeyboardButton("➕ Добавить карту")
    edit_card = types.KeyboardButton("📝 Изменить карту")
    del_card = types.KeyboardButton("🗑 Удалить карту")
    
    # Управление промокодами
    add_promo = types.KeyboardButton("🎟 +Промокод")
    del_promo = types.KeyboardButton("🗑 Удалить промокод")
    
    # Управление пользователями
    ban_user = types.KeyboardButton("🚫 Забанить")
    unban_user = types.KeyboardButton("✅ Разбанить")
    
    # Опасные действия
    reset_bot = types.KeyboardButton("🧨 Обнулить бота")
    back_home = types.KeyboardButton("🏠 Назад в меню")
    
    markup.add(add_card, edit_card, del_card, add_promo, del_promo, ban_user, unban_user, reset_bot, back_home)
    return markup

def get_cancel_keyboard():
    """Кнопка для отмены действий в пошаговых сценариях."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    return markup

# ==============================================================================
# [6] РЕГИСТРАЦИЯ И ПАРТНЕРСКАЯ ПРОГРАММА
# ==============================================================================

@bot.message_handler(commands=['start'])
def handle_command_start(message):
    """Обработка команды /start и реферальных переходов."""
    if is_banned(message.from_user):
        bot.send_message(message.chat.id, "🚫 Вы заблокированы и не можете пользоваться ботом.")
        return

    users_db = load_data('users')
    user_id_str = str(message.from_user.id)
    
    # Поиск реферального родителя в ссылке (если есть)
    parent_id = None
    command_parts = message.text.split()
    if len(command_parts) > 1:
        parent_id = command_parts[1]

    # Если пользователь зашел впервые
    if user_id_str not in users_db:
        # Определяем отображаемое имя (ник или ID)
        if message.from_user.username:
            username_display = f"@{message.from_user.username}"
        else:
            username_display = f"id{user_id_str}"
            
        users_db[user_id_str] = {
            "nick": message.from_user.first_name,
            "username": username_display,
            "score": 0,
            "free_rolls": 0,    # Накопленные бесплатные прокруты
            "bonus_luck": 1.0,  # Множитель удачи (1.0 = норма)
            "refs": 0,          # Сколько человек привел
            "used_promos": []   # Список кодов, которые он уже вводил
        }
        
        # Обработка реферального бонуса
        if parent_id and parent_id in users_db and parent_id != user_id_str:
            users_db[parent_id]["score"] += 5000
            users_db[parent_id]["refs"] += 1
            try:
                bot.send_message(int(parent_id), "👥 По вашей ссылке зарегистрирован новый игрок! Вам начислено 5,000 очков.")
            except:
                pass

    save_data(users_db, 'users')
    
    welcome_text = (
        f"⚽️ Добро пожаловать, {message.from_user.first_name}!\n\n"
        "Это симулятор футбольных карточек. Собирай игроков, "
        "формируй лучший состав и сражайся с другими игроками!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def show_referals_stats(message):
    """Отображение личной реферальной ссылки и статистики."""
    if is_banned(message.from_user): return
    
    user_id = message.from_user.id
    users_db = load_data('users')
    bot_username = bot.get_me().username
    
    # Создаем уникальную ссылку на бота с ID игрока
    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    my_referals_count = users_db.get(str(user_id), {}).get("refs", 0)
    
    text = (
        "👥 **РЕФЕРАЛЬНАЯ СИСТЕМА**\n\n"
        "Приглашайте друзей и получайте бонусы!\n"
        "За каждого приглашенного вы получите **5,000 очков** на баланс.\n\n"
        f"Вами приглашено: **{my_referals_count}** чел.\n\n"
        "Ваша ссылка для приглашения:\n"
        f"`{invite_link}`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==============================================================================
# [7] СИСТЕМА ПРОМОКОДОВ
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🎟 Промокод")
def start_promo_activation(message):
    """Запуск процесса ввода промокода."""
    if is_banned(message.from_user): return
    
    sent_msg = bot.send_message(
        message.chat.id, 
        "🎟 Введите промокод для получения бонуса:", 
        reply_markup=get_cancel_keyboard()
    )
    bot.register_next_step_handler(sent_msg, process_promo_code_logic)

def process_promo_code_logic(message):
    """Логика проверки и начисления бонусов по коду."""
    if message.text == "❌ Отмена":
        return cancel_action_and_return(message)
    
    input_code = message.text.strip().upper()
    user_id_str = str(message.from_user.id)
    
    users_db = load_data('users')
    promos_db = load_data('promos')
    
    # 1. Проверяем, существует ли такой код вообще
    if input_code not in promos_db:
        bot.send_message(message.chat.id, "❌ Такого кода не существует.", reply_markup=get_main_keyboard(user_id_str))
        return

    # 2. Проверяем, не использовал ли пользователь его ранее
    if input_code in users_db[user_id_str].get('used_promos', []):
        bot.send_message(message.chat.id, "❌ Вы уже активировали этот промокод.", reply_markup=get_main_keyboard(user_id_str))
        return

    # 3. Получаем данные кода и начисляем награду
    code_data = promos_db[input_code]
    reward_type = code_data['type']
    reward_value = code_data['value']
    
    if reward_type == 'rolls':
        # Бесплатные прокруты без таймера
        users_db[user_id_str]['free_rolls'] = users_db[user_id_str].get('free_rolls', 0) + int(reward_value)
        msg_result = f"✅ Успех! Вы получили **{int(reward_value)} бесплатных прокрутов**! Они позволяют крутить карту без ожидания 3 часов."
    
    elif reward_type == 'luck':
        # Повышение удачи на следующий ролл
        users_db[user_id_str]['bonus_luck'] = float(reward_value)
        msg_result = f"✅ Успех! Ваша удача увеличена в **{reward_value} раз** на следующую попытку!"
    
    else:
        # Просто начисление очков
        users_db[user_id_str]['score'] += int(reward_value)
        msg_result = f"✅ Успех! На ваш баланс зачислено **{int(reward_value):,} очков**."

    # Отмечаем код как использованный игроком
    if 'used_promos' not in users_db[user_id_str]:
        users_db[user_id_str]['used_promos'] = []
    users_db[user_id_str]['used_promos'].append(input_code)
    
    save_data(users_db, 'users')
    bot.send_message(message.chat.id, msg_result, reply_markup=get_main_keyboard(user_id_str), parse_mode="Markdown")

# ==============================================================================
# [8] ГЛАВНАЯ МЕХАНИКА: ПОЛУЧЕНИЕ КАРТ (ROLL)
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def handle_roll_request(message):
    """Процесс вытягивания новой футбольной карточки."""
    if is_banned(message.from_user): return
    
    user_id_str = str(message.from_user.id)
    users_db = load_data('users')
    all_available_cards = load_data('cards')
    
    if not all_available_cards:
        bot.send_message(message.chat.id, "❌ В игре пока нет созданных карт. Обратитесь к админу.")
        return
        
    current_time = time.time()
    bonus_rolls = users_db[user_id_str].get('free_rolls', 0)
    
    # ПРОВЕРКА КУЛДАУНА (3 ЧАСА)
    # Если есть бонусные прокруты или игрок админ — кулдаун игнорируется
    if not is_admin(message.from_user) and bonus_rolls <= 0:
        if user_id_str in roll_cooldowns:
            time_passed = current_time - roll_cooldowns[user_id_str]
            if time_passed < 10800: # 10800 секунд = 3 часа
                remaining = int(10800 - time_passed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                bot.send_message(message.chat.id, f"⏳ Ваши скауты еще в пути. Приходите через {hours}ч {minutes}м.\n\n🎟 Используйте промокод, чтобы получить мгновенный прокрут!")
                return

    # РАСЧЕТ ШАНСОВ (УДАЧА)
    user_luck = users_db[user_id_str].get('bonus_luck', 1.0)
    
    # Генерируем веса редкостей
    rarity_list = sorted(RARITY_STATS.keys())
    weights = []
    for r in rarity_list:
        chance = RARITY_STATS[r]['chance']
        # Если это Эпик (4) или Легенда (5), применяем множитель удачи
        if r >= 4:
            chance *= user_luck
        weights.append(chance)

    # Выбор итоговой редкости
    selected_rarity = random.choices(rarity_list, weights=weights)[0]
    
    # Фильтруем все карты по этой редкости
    potential_cards = [c for c in all_available_cards if c['stars'] == selected_rarity]
    
    # Если в базе нет карт именно такой редкости (например, не добавили легенд), берем любую
    if not potential_cards:
        potential_cards = all_available_cards
        
    reward_card = random.choice(potential_cards)
    
    # ОБРАБОТКА ПОПЫТОК
    if bonus_rolls > 0:
        users_db[user_id_str]['free_rolls'] -= 1
        status_info = f"🎫 Использован бонусный прокрут. Осталось: {users_db[user_id_str]['free_rolls']}"
    else:
        roll_cooldowns[user_id_str] = current_time
        status_info = f"⏳ Попытка использована. Следующая будет доступна через 3 часа."

    # После использования ролла удача всегда сбрасывается к 1.0
    users_db[user_id_str]['bonus_luck'] = 1.0

    # ПРОВЕРКА НА ПОВТОР (ДУБЛИКАТ)
    collections_db = load_data('colls')
    if user_id_str not in collections_db:
        collections_db[user_id_str] = []
        
    # Проверяем наличие по имени (имя уникально для карты)
    is_duplicate = any(card['name'] == reward_card['name'] for card in collections_db[user_id_str])
    
    if is_duplicate:
        # За дубликат даем 30% от базовых очков редкости
        points_to_add = int(RARITY_STATS[reward_card['stars']]['score'] * 0.3)
        result_note = "🔄 У вас уже есть эта карта! Вы получили 30% компенсации очками."
    else:
        # За новую карту даем 100% очков
        points_to_add = RARITY_STATS[reward_card['stars']]['score']
        result_note = "✨ ПОЗДРАВЛЯЕМ! Это новый игрок в вашу коллекцию!"
        collections_db[user_id_str].append(reward_card)
        save_data(collections_db, 'colls')

    # Обновляем баланс пользователя
    users_db[user_id_str]['score'] += points_to_add
    save_data(users_db, 'users')

    # Оформляем карточку для отправки
    stars_display = "⭐" * reward_card['stars']
    pos_name = POSITIONS_RU.get(reward_card['pos'].upper(), reward_card['pos'])
    
    caption_text = (
        f"⚽️ **{reward_card['name']}**\n\n"
        f"📊 Редкость: {stars_display} ({RARITY_STATS[reward_card['stars']]['label']})\n"
        f"🎯 Позиция: {pos_name}\n\n"
        f"💠 {result_note}\n"
        f"💰 Начислено: +{points_to_add:,} очков\n"
        f"📈 Ваш текущий баланс: {users_db[user_id_str]['score']:,}\n\n"
        f"{status_info}"
    )
    
    bot.send_photo(message.chat.id, reward_card['photo'], caption=caption_text, parse_mode="Markdown")

# ==============================================================================
# [9] ПВП АРЕНА (БОИ С ИГРОКАМИ)
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def open_pvp_hub(message):
    """Главный экран ПВП режима."""
    if is_banned(message.from_user): return
    
    uid_str = str(message.from_user.id)
    
    # Кулдаун на ПВП — 15 минут (900 сек)
    if not is_admin(message.from_user):
        if uid_str in pvp_cooldowns:
            passed = time.time() - pvp_cooldowns[uid_str]
            if passed < 900:
                rem = int(900 - passed)
                bot.send_message(message.chat.id, f"⏳ Ваши футболисты восстанавливают силы. ПВП будет доступно через {rem // 60} мин.")
                return

    pvp_markup = types.InlineKeyboardMarkup(row_width=1)
    btn_random = types.InlineKeyboardButton("🎲 Случайный соперник", callback_data="pvp_action_random")
    btn_by_name = types.InlineKeyboardButton("👤 Бой по юзернейму", callback_data="pvp_action_by_user")
    
    pvp_markup.add(btn_random, btn_by_name)
    
    my_power = get_team_power(uid_str)
    
    hub_text = (
        "🏟 **ФУТБОЛЬНАЯ АРЕНА**\n\n"
        "Здесь вы можете сразиться с составами других игроков.\n"
        f"Ваша суммарная мощь состава: **{my_power}**\n\n"
        "Победа в матче приносит **1,000 очков**!"
    )
    bot.send_message(message.chat.id, hub_text, reply_markup=pvp_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "pvp_action_random")
def execute_random_matchmaking(call):
    """Поиск случайного противника из базы данных."""
    users_db = load_data('users')
    player1_id = str(call.from_user.id)
    
    p1_power = get_team_power(player1_id)
    if p1_power <= 0:
        bot.answer_callback_query(call.id, "❌ Ваш состав пуст! Назначьте игроков в меню '📋 Состав'.", show_alert=True)
        return

    # Находим всех, у кого сила > 0 и кто не является самим игроком
    potential_opponents = []
    for uid in users_db:
        if uid != player1_id and get_team_power(uid) > 0:
            potential_opponents.append(uid)
            
    if not potential_opponents:
        bot.answer_callback_query(call.id, "❌ Сейчас нет игроков с готовыми составами. Попробуйте позже.", show_alert=True)
        return
        
    player2_id = random.choice(potential_opponents)
    perform_match_calculation(call.message.chat.id, player1_id, player2_id)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_action_by_user")
def start_pvp_by_username_input(call):
    """Запрос ввода ника для точного поиска врага."""
    msg = bot.send_message(
        call.message.chat.id, 
        "👤 Введите @username или числовой ID игрока, которого хотите вызвать на бой:", 
        reply_markup=get_cancel_keyboard()
    )
    bot.register_next_step_handler(msg, process_search_enemy_by_input)

def process_search_enemy_by_input(message):
    """Поиск игрока по вводу и запуск боя."""
    if message.text == "❌ Отмена":
        return cancel_action_and_return(message)
        
    search_query = message.text.replace("@", "").lower().strip()
    users_db = load_data('users')
    player1_id = str(message.from_user.id)
    
    player2_id = None
    
    # Ищем совпадения по ID или нику
    for uid, data in users_db.items():
        if uid == search_query:
            player2_id = uid
            break
        if data['username'].replace("@", "").lower() == search_query:
            player2_id = uid
            break
            
    if not player2_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден в нашей базе данных.", reply_markup=get_main_keyboard(player1_id))
        return
        
    if player2_id == player1_id:
        bot.send_message(message.chat.id, "❌ Вы не можете играть против самого себя.", reply_markup=get_main_keyboard(player1_id))
        return
        
    # Проверка силы противника
    if get_team_power(player2_id) <= 0:
        bot.send_message(message.chat.id, "❌ У этого игрока пока не настроен состав.", reply_markup=get_main_keyboard(player1_id))
        return
        
    perform_match_calculation(message.chat.id, player1_id, player2_id)

def perform_match_calculation(chat_id, p1_id, p2_id):
    """Математический расчет результата футбольного матча."""
    users_db = load_data('users')
    
    p1_power = get_team_power(p1_id)
    p2_power = get_team_power(p2_id)
    
    # Расчет вероятности победы (чем выше сила, тем больше шансов)
    # Используем возведение в степень 1.3, чтобы разница была ощутимее
    weight1 = p1_power ** 1.3
    weight2 = p2_power ** 1.3
    
    # Определение победителя случайным образом на основе весов
    winner_id = random.choices([p1_id, p2_id], weights=[weight1, weight2])[0]
    
    # Начисляем награду (1000 очков)
    users_db[winner_id]['score'] += 1000
    save_data(users_db, 'users')
    
    # Ставим кулдаун на ПВП инициатору (p1)
    pvp_cooldowns[p1_id] = time.time()
    
    # Формируем отчет
    report = (
        "🏟 **РЕЗУЛЬТАТ МАТЧА**\n\n"
        f"🏠 Хозяева: **{users_db[p1_id]['nick']}**\n"
        f"🛡 Сила: {p1_power}\n\n"
        f"🚀 Гости: **{users_db[p2_id]['nick']}**\n"
        f"🛡 Сила: {p2_power}\n\n"
        "➖➖➖➖➖➖➖➖\n"
        f"🏆 Победитель: **{users_db[winner_id]['username']}**\n"
        f"💰 Награда: **+1,000 очков**"
    )
    bot.send_message(chat_id, report, parse_mode="Markdown", reply_markup=get_main_keyboard(p1_id))

# ==============================================================================
# [10] ПРОФИЛЬ, ТОП И ПРОСМОТР КОЛЛЕКЦИИ
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_my_personal_profile(message):
    """Показ баланса и статистики игрока."""
    if is_banned(message.from_user): return
    
    uid_str = str(message.from_user.id)
    u_db = load_data('users')
    c_db = load_data('colls')
    
    user_data = u_db.get(uid_str)
    my_cards_total = len(c_db.get(uid_str, []))
    my_power = get_team_power(uid_str)
    
    msg = (
        f"👤 **ВАШ ПРОФИЛЬ**\n\n"
        f"🆔 ID: `{uid_str}`\n"
        f"👤 Имя: {user_data['nick']}\n\n"
        f"💠 Баланс очков: `{user_data['score']:,}`\n"
        f"🗂 Коллекция: {my_cards_total} игроков\n"
        f"🛡 Мощь состава: **{my_power}**\n"
        f"🎫 Бонусные прокруты: **{user_data.get('free_rolls', 0)}**"
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_global_leaderboard(message):
    """Список 10 самых богатых игроков."""
    if is_banned(message.from_user): return
    
    u_db = load_data('users')
    # Сортировка по очкам
    sorted_top = sorted(u_db.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    text = "🏆 **ТОП-10 ИГРОКОВ ПО ОЧКАМ:**\n\n"
    for index, (uid, data) in enumerate(sorted_top, 1):
        text += f"{index}. {data['username']} — `{data['score']:,}`\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def open_collection_stars_menu(message):
    """Выбор редкости для просмотра своего альбома."""
    if is_banned(message.from_user): return
    
    markup = types.InlineKeyboardMarkup()
    for s in range(1, 6):
        markup.add(types.InlineKeyboardButton(f"{'⭐'*s} Показать карты", callback_data=f"view_stars_{s}"))
    
    bot.send_message(message.chat.id, "🗂 **ВАШ АЛЬБОМ**\nВыберите редкость карт для просмотра:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_stars_"))
def show_filtered_collection(call):
    """Отображение списка имен карт выбранной редкости."""
    star_level = int(call.data.split("_")[-1])
    uid_str = str(call.from_user.id)
    
    full_coll = load_data('colls').get(uid_str, [])
    filtered_list = [card for card in full_coll if card['stars'] == star_level]
    
    if not filtered_list:
        bot.answer_callback_query(call.id, f"У вас еще нет карт достоинством {star_level} звезд.", show_alert=True)
        return
        
    text = f"🗂 **ВАШИ КАРТЫ {star_level}⭐:**\n\n"
    for item in filtered_list:
        # Находим русское название позиции
        p_ru = POSITIONS_RU.get(item['pos'].upper(), item['pos'])
        text += f"• {item['name']} ({p_ru})\n"
        
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==============================================================================
# [11] УПРАВЛЕНИЕ ИГРОВЫМ СОСТАВОМ (SQUAD)
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def open_squad_editor(message):
    """Главный экран выбора позиций в составе."""
    if is_banned(message.from_user): return
    
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id, 
        "📋 **РЕДАКТИРОВАНИЕ СОСТАВА**\n\nНажмите на позицию, чтобы выбрать игрока из своей коллекции.", 
        reply_markup=generate_squad_markup(user_id), 
        parse_mode="Markdown"
    )

def generate_squad_markup(user_id):
    """Генерация Inline кнопок для 7 слотов состава."""
    squad_db = load_data('squads')
    current_slots = squad_db.get(str(user_id), [None] * 7)
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for i in range(7):
        slot_info = SQUAD_SLOTS[i]
        player = current_slots[i]
        
        if player:
            btn_text = f"{slot_info['label']}: {player['name']} ({player['stars']}⭐)"
        else:
            btn_text = f"{slot_info['label']}: ❌ Не назначен"
            
        kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"squad_slot_edit_{i}"))
        
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("squad_slot_edit_"))
def show_available_players_for_position(call):
    """Показывает только тех игроков из коллекции, которые подходят на выбранный слот."""
    slot_index = int(call.data.split("_")[-1])
    uid_str = str(call.from_user.id)
    
    # Какая позиция требуется для этого слота (например ГК или КФ)
    target_position_code = SQUAD_SLOTS[slot_index]["code"]
    
    user_collection = load_data('colls').get(uid_str, [])
    # Фильтруем коллекцию по коду позиции
    valid_players = []
    for p in user_collection:
        if p['pos'].upper() == target_position_code:
            valid_players.append(p)
    
    if not valid_players:
        bot.answer_callback_query(call.id, f"❌ У вас нет игроков позиции {target_position_code} в коллекции!", show_alert=True)
        return
        
    choice_kb = types.InlineKeyboardMarkup(row_width=1)
    for p in valid_players:
        btn_label = f"{p['name']} ({p['stars']}⭐)"
        choice_kb.add(types.InlineKeyboardButton(btn_label, callback_data=f"save_to_squad_{slot_index}_{p['name']}"))
        
    choice_kb.add(types.InlineKeyboardButton("🚫 Очистить слот", callback_data=f"save_to_squad_{slot_index}_empty"))
    
    bot.edit_message_text(
        f"Выберите игрока на позицию **{target_position_code}**:", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=choice_kb, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("save_to_squad_"))
def save_selected_player_to_slot(call):
    """Финальное сохранение выбора в базу составов."""
    parts = call.data.split("_")
    slot_id = int(parts[3])
    player_name = parts[4]
    uid_str = str(call.from_user.id)
    
    squad_db = load_data('squads')
    if uid_str not in squad_db:
        squad_db[uid_str] = [None] * 7
        
    if player_name == "empty":
        squad_db[uid_str][slot_id] = None
    else:
        # Ищем объект карты в коллекции игрока
        user_coll = load_data('colls').get(uid_str, [])
        found_card = None
        for card in user_coll:
            if card['name'] == player_name:
                found_card = card
                break
        squad_db[uid_str][slot_id] = found_card
        
    save_data(squad_db, 'squads')
    bot.edit_message_text(
        "✅ Состав успешно обновлен!", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=generate_squad_markup(uid_str)
    )

# ==============================================================================
# [12] АДМИН-ПАНЕЛЬ: УПРАВЛЕНИЕ КАРТАМИ
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_admin_main_screen(message):
    """Доступ к панели управления для админов."""
    if not is_admin(message.from_user): return
    bot.send_message(message.chat.id, "🛠 **ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- ДОБАВЛЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_card_step1(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Введите ФИО нового футболиста:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, admin_add_card_step2)

def admin_add_card_step2(message):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    name = message.text
    sent = bot.send_message(message.chat.id, "Введите позицию (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):")
    bot.register_next_step_handler(sent, admin_add_card_step3, name)

def admin_add_card_step3(message, name):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    pos = message.text.upper()
    sent = bot.send_message(message.chat.id, "Введите редкость (число от 1 до 5 звезд):")
    bot.register_next_step_handler(sent, admin_add_card_step4, name, pos)

def admin_add_card_step4(message, name, pos):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    try:
        stars = int(message.text)
        sent = bot.send_message(message.chat.id, "Теперь отправьте ФОТОГРАФИЮ для этой карточки:")
        bot.register_next_step_handler(sent, admin_add_card_step5, name, pos, stars)
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно ввести число (1-5). Процесс прерван.")

def admin_add_card_step5(message, name, pos, stars):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Вы не отправили фото. Операция отменена.")
        return
    
    cards_db = load_data('cards')
    cards_db.append({
        "name": name,
        "pos": pos,
        "stars": stars,
        "photo": message.photo[-1].file_id # Берем самое качественное фото
    })
    save_data(cards_db, 'cards')
    bot.send_message(message.chat.id, f"✅ Игрок **{name}** успешно добавлен!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- УДАЛЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_card_list(message):
    if not is_admin(message.from_user): return
    cards = load_data('cards')
    if not cards:
        bot.send_message(message.chat.id, "Список карт пуст.")
        return
        
    markup = types.InlineKeyboardMarkup()
    for c in cards:
        markup.add(types.InlineKeyboardButton(f"❌ Удалить {c['name']}", callback_data=f"admin_del_card_{c['name']}"))
    bot.send_message(message.chat.id, "Выберите карту для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_del_card_"))
def admin_delete_card_confirm(call):
    target_name = call.data.replace("admin_del_card_", "")
    all_cards = load_data('cards')
    
    new_list = []
    for c in all_cards:
        if c['name'] != target_name:
            new_list.append(c)
            
    save_data(new_list, 'cards')
    bot.edit_message_text(f"🗑 Игрок **{target_name}** был удален из базы данных.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- ИЗМЕНЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_card_list(message):
    if not is_admin(message.from_user): return
    cards = load_data('cards')
    markup = types.InlineKeyboardMarkup()
    for c in cards:
        markup.add(types.InlineKeyboardButton(f"⚙️ {c['name']}", callback_data=f"admin_edit_card_{c['name']}"))
    bot.send_message(message.chat.id, "Выберите карту для редактирования:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_edit_card_"))
def admin_edit_field_choice(call):
    name = call.data.replace("admin_edit_card_", "")
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("Имя", callback_data=f"edit_f_{name}_name"),
        types.InlineKeyboardButton("Позиция", callback_data=f"edit_f_{name}_pos"),
        types.InlineKeyboardButton("Звезды", callback_data=f"edit_f_{name}_stars"),
        types.InlineKeyboardButton("Фото", callback_data=f"edit_f_{name}_photo")
    )
    bot.edit_message_text(f"Что изменить у игрока {name}?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_f_"))
def admin_edit_start_input(call):
    parts = call.data.split("_")
    name, field = parts[2], parts[3]
    msg = bot.send_message(call.message.chat.id, f"Введите новое значение для **{field}**:", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_edit_save_to_db, name, field)

def admin_edit_save_to_db(message, name, field):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    db = load_data('cards')
    found = False
    for item in db:
        if item['name'] == name:
            if field == "photo":
                if not message.photo: return bot.send_message(message.chat.id, "Нужно фото!")
                item[field] = message.photo[-1].file_id
            elif field == "stars":
                item[field] = int(message.text)
            else:
                item[field] = message.text if field != "pos" else message.text.upper()
            found = True
            break
    if found:
        save_data(db, 'cards')
        bot.send_message(message.chat.id, "✅ Изменено!", reply_markup=get_admin_keyboard())

# ==============================================================================
# [13] АДМИН-ПАНЕЛЬ: УПРАВЛЕНИЕ ПРОМОКОДАМИ
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🎟 +Промокод")
def admin_add_promo_step1(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Напишите код (ЛАТИНИЦЕЙ):", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, admin_add_promo_step2)

def admin_add_promo_step2(message):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    code = message.text.strip().upper()
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🎫 Прокруты", callback_data=f"p_t_{code}_rolls"),
        types.InlineKeyboardButton("💠 Очки", callback_data=f"p_t_{code}_points"),
        types.InlineKeyboardButton("🍀 Удача", callback_data=f"p_t_{code}_luck")
    )
    bot.send_message(message.chat.id, f"Тип бонуса для `{code}`:", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_t_"))
def admin_add_promo_step3(call):
    parts = call.data.split("_")
    code, p_type = parts[2], parts[3]
    msg = bot.send_message(call.message.chat.id, f"Введите число (значение бонуса):")
    bot.register_next_step_handler(msg, admin_add_promo_final, code, p_type)

def admin_add_promo_final(message, code, p_type):
    try:
        val = float(message.text)
        db = load_data('promos')
        db[code] = {"type": p_type, "value": val}
        save_data(db, 'promos')
        bot.send_message(message.chat.id, f"✅ Код `{code}` создан!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "Нужно число! Попробуйте снова.")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить промокод")
def admin_delete_promo_list(message):
    if not is_admin(message.from_user): return
    db = load_data('promos')
    if not db:
        bot.send_message(message.chat.id, "Кодов нет.")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for code in db.keys():
        kb.add(types.InlineKeyboardButton(f"🗑 Удалить {code}", callback_data=f"del_p_{code}"))
    bot.send_message(message.chat.id, "Выберите код для удаления:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_p_"))
def admin_delete_promo_exec(call):
    code = call.data.replace("del_p_", "")
    db = load_data('promos')
    if code in db:
        del db[code]
        save_data(db, 'promos')
        bot.edit_message_text(f"✅ Промокод `{code}` удален.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==============================================================================
# [14] АДМИН-ПАНЕЛЬ: БАНЫ И СБРОС
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_user_start(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "ID или @username для бана:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, process_ban_action, True)

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_user_start(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "ID или @username для разбана:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, process_ban_action, False)

def process_ban_action(message, block_mode):
    if message.text == "❌ Отмена": return cancel_action_and_return(message)
    target = message.text.replace("@", "").lower().strip()
    db = load_data('bans')
    if block_mode:
        if target not in db: db.append(target)
        msg = f"✅ `{target}` забанен."
    else:
        if target in db: db.remove(target)
        msg = f"✅ `{target}` разбанен."
    save_data(db, 'bans')
    bot.send_message(message.chat.id, msg, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_confirm_screen(message):
    if not is_admin(message.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚨 УДАЛИТЬ ВСЕ ДАННЫЕ", "❌ Отмена")
    bot.send_message(message.chat.id, "🚨 ВНИМАНИЕ! Это действие удалит всех юзеров, их очки и составы. Вы уверены?", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚨 УДАЛИТЬ ВСЕ ДАННЫЕ")
def admin_reset_execution(message):
    if not is_admin(message.from_user): return
    save_data({}, 'users')
    save_data({}, 'colls')
    save_data({}, 'squads')
    bot.send_message(message.chat.id, "🧨 База данных игроков полностью очищена.", reply_markup=get_admin_keyboard())

# ==============================================================================
# [15] СЕРВИСНЫЕ КОМАНДЫ
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_to_main_screen(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def cancel_action_and_return(message):
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=get_main_keyboard(message.from_user.id))

# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
    print("---------------------------------")
    print("⚽️ Football Cards Bot запущен!")
    print("---------------------------------")
    bot.infinity_polling()
