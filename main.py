import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] ГЛОБАЛЬНЫЕ НАСТРОЙКИ И ТОКЕН ---
# Вставь свой токен ниже
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
# Список администраторов (username без @)
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 

bot = telebot.TeleBot(TOKEN)

# Названия файлов для базы данных (JSON)
DB_FILES = {
    'cards': 'cards.json',         # База всех существующих в боте карт
    'colls': 'collections.json',   # Коллекции игроков (какие карты у кого есть)
    'squads': 'squads.json',       # Составы игроков (выбранные 7 позиций)
    'users': 'users_data.json',     # Данные юзеров (очки, баланс, рефералы)
    'bans': 'bans.json',           # Черный список (ID и ники)
    'promos': 'promos.json'        # База активных промокодов
}

# --- [2] БАЛАНС И ХАРАКТЕРИСТИКИ РЕДКОСТИ ---
# Шансы выпадения и вознаграждение за редкость
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

# Позиции игроков на русском
POSITIONS_RU = {
    "ГК": "Вратарь", 
    "ЛЗ": "Левый Защитник", 
    "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник", 
    "ЛВ": "Левый Вингер", 
    "ПВ": "Правый Вингер", 
    "КФ": "Нападающий"
}

# Описание слотов для формирования состава
SQUAD_SLOTS = {
    0: {"label": "🧤 ГК (Вратарь)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ (Защитник)", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ (Защитник)", "code": "ПЗ"},
    3: {"label": "👟 ЦП (Полузащитник)", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ (Вингер)", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ (Вингер)", "code": "ПВ"},
    6: {"label": "🎯 КФ (Нападающий)", "code": "КФ"}
}

# Словари для хранения временных данных (кулдауны)
roll_cooldowns = {}
pvp_cooldowns = {}

# --- [3] ФУНКЦИИ РАБОТЫ С JSON БАЗОЙ ---

def load_data(key):
    """
    Универсальная функция загрузки данных из файла.
    Если файла нет — создает его с пустой структурой.
    """
    file_path = DB_FILES[key]
    if not os.path.exists(file_path):
        # Если это список (карты, баны), создаем [], иначе {}
        default_data = [] if key in ['cards', 'bans'] else {}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            # Если файл битый, возвращаем базу по умолчанию
            return [] if key in ['cards', 'bans'] else {}

def save_data(data, key):
    """
    Универсальная функция сохранения данных в файл.
    """
    file_path = DB_FILES[key]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [4] ПРОВЕРКИ ПРАВ И СТАТУСОВ ---

def is_admin(user_object):
    """Проверяет, является ли пользователь админом по списку ников."""
    if not user_object.username:
        return False
    return user_object.username.lower() in [admin_name.lower() for admin_name in ADMINS]

def is_banned(user_object):
    """Проверяет наличие ID или ника в черном списке."""
    ban_list = load_data('bans')
    user_id = str(user_object.id)
    user_name = user_object.username.lower() if user_object.username else "none"
    if user_id in ban_list or user_name in ban_list:
        return True
    return False

def get_team_power(user_id):
    """Рассчитывает суммарную силу (атаку) состава игрока."""
    squad_db = load_data('squads')
    # По умолчанию у игрока 7 пустых слотов
    user_squad = squad_db.get(str(user_id), [None] * 7)
    total_power = 0
    for player_card in user_squad:
        if player_card:
            # Берем атаку по количеству звезд из RARITY_STATS
            star_count = player_card.get('stars', 1)
            total_power += RARITY_STATS[star_count]['atk']
    return total_power

# --- [5] ГЕНЕРАЦИЯ ИНТЕРФЕЙСА (КЛАВИАТУРЫ) ---

def get_main_keyboard(user_id):
    """Главное меню игрока."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎰 Крутить карту")
    btn2 = types.KeyboardButton("🗂 Коллекция")
    btn3 = types.KeyboardButton("📋 Состав")
    btn4 = types.KeyboardButton("👤 Профиль")
    btn5 = types.KeyboardButton("🏆 Топ очков")
    btn6 = types.KeyboardButton("🏟 ПВП Арена")
    btn7 = types.KeyboardButton("🎟 Промокод")
    btn8 = types.KeyboardButton("👥 Рефералы")
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    
    # Если юзер админ, добавляем кнопку панели
    try:
        user_info = bot.get_chat(user_id)
        if is_admin(user_info):
            markup.add(types.KeyboardButton("🛠 Админ-панель"))
    except:
        pass
    return markup

def get_admin_keyboard():
    """Меню управления для администраторов."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ Добавить карту"))
    markup.add(types.KeyboardButton("📝 Изменить карту"))
    markup.add(types.KeyboardButton("🗑 Удалить карту"))
    markup.add(types.KeyboardButton("🎟 +Промокод"))
    markup.add(types.KeyboardButton("🗑 Удалить промокод"))
    markup.add(types.KeyboardButton("🚫 Забанить"))
    markup.add(types.KeyboardButton("✅ Разбанить"))
    markup.add(types.KeyboardButton("🧨 Обнулить бота"))
    markup.add(types.KeyboardButton("🏠 Назад в меню"))
    return markup

def get_cancel_keyboard():
    """Кнопка для отмены текущего действия."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    return markup

# --- [6] КОМАНДА СТАРТ И РЕФЕРАЛЬНАЯ СИСТЕМА ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    if is_banned(message.from_user):
        bot.send_message(message.chat.id, "🚫 Вы заблокированы в этом боте.")
        return

    users_db = load_data('users')
    user_id_str = str(message.from_user.id)
    
    # Проверка на реферальный код в ссылке
    ref_parent_id = None
    args = message.text.split()
    if len(args) > 1:
        ref_parent_id = args[1]

    # Если игрока нет в базе — регистрируем
    if user_id_str not in users_db:
        display_name = f"@{message.from_user.username}" if message.from_user.username else f"id{user_id_str}"
        users_db[user_id_str] = {
            "nick": message.from_user.first_name,
            "username": display_name,
            "score": 0,
            "free_rolls": 0,   # Поле для бесплатных прокрутов из промокодов
            "bonus_luck": 1.0, # Множитель удачи
            "refs": 0,         # Количество приглашенных
            "used_promos": []  # Список активированных кодов
        }
        
        # Если пришел по рефералке
        if ref_parent_id and ref_parent_id in users_db and ref_parent_id != user_id_str:
            users_db[ref_parent_id]["score"] += 5000
            users_db[ref_parent_id]["refs"] += 1
            try:
                bot.send_message(int(ref_parent_id), "👥 По вашей ссылке зашел новый игрок! Вам начислено 5,000 очков.")
            except:
                pass

    save_data(users_db, 'users')
    welcome_text = (
        f"⚽️ Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в симулятор футбольных карточек.\n"
        "Собирай лучших игроков, настраивай состав и побеждай!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def show_referals_menu(message):
    if is_banned(message.from_user): return
    user_id = message.from_user.id
    users_db = load_data('users')
    bot_info = bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    my_refs = users_db.get(str(user_id), {}).get("refs", 0)
    
    text = (
        "👥 **ПАРТНЕРСКАЯ ПРОГРАММА**\n\n"
        "Приглашайте друзей и получайте бонусы!\n"
        "За каждого друга вам полагается **5,000 очков**.\n\n"
        f"Вы пригласили: **{my_refs}** чел.\n\n"
        "Ваша ссылка для приглашения:\n"
        f"`{invite_link}`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- [7] ПРОМОКОДЫ И БОНУСНЫЕ ПРОКРУТЫ ---

@bot.message_handler(func=lambda m: m.text == "🎟 Промокод")
def start_promo_entry(message):
    if is_banned(message.from_user): return
    sent_msg = bot.send_message(message.chat.id, "🎟 Введите промокод для активации:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent_msg, apply_promo_code)

def apply_promo_code(message):
    if message.text == "❌ Отмена":
        return cancel_to_main(message)
    
    code_input = message.text.strip().upper()
    user_id_str = str(message.from_user.id)
    users_db = load_data('users')
    promos_db = load_data('promos')
    
    # Проверка существования кода
    if code_input not in promos_db:
        bot.send_message(message.chat.id, "❌ Такого кода не существует.", reply_markup=get_main_keyboard(user_id_str))
        return

    # Проверка, использовал ли его игрок раньше
    if code_input in users_db[user_id_str].get('used_promos', []):
        bot.send_message(message.chat.id, "❌ Вы уже использовали этот промокод.", reply_markup=get_main_keyboard(user_id_str))
        return

    promo_data = promos_db[code_input]
    p_type = promo_data['type']
    p_val = promo_data['value']
    
    # Применение бонуса
    if p_type == 'rolls':
        users_db[user_id_str]['free_rolls'] = users_db[user_id_str].get('free_rolls', 0) + int(p_val)
        msg = f"✅ Успех! Получено **{int(p_val)} бесплатных прокрутов**! Они позволяют крутить карту без ожидания 3 часов."
    elif p_type == 'luck':
        users_db[user_id_str]['bonus_luck'] = float(p_val)
        msg = f"✅ Успех! Удача увеличена в **{p_val} раз** на следующую попытку!"
    else:
        users_db[user_id_str]['score'] += int(p_val)
        msg = f"✅ Успех! На ваш баланс зачислено **{int(p_val):,} очков**."

    # Отмечаем как использованный
    users_db[user_id_str].setdefault('used_promos', []).append(code_input)
    save_data(users_db, 'users')
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(user_id_str), parse_mode="Markdown")

# --- [8] ГЛАВНАЯ МЕХАНИКА: КРУТКА КАРТ (ROLL) ---

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_process_handler(message):
    if is_banned(message.from_user): return
    user_id_str = str(message.from_user.id)
    users_db = load_data('users')
    current_time = time.time()
    
    # Проверяем наличие бесплатных прокрутов
    bonus_rolls_count = users_db[user_id_str].get('free_rolls', 0)
    
    # ПРОВЕРКА ТАЙМЕРА (Кулдауна)
    # Если у игрока есть бонусные прокруты, КД игнорируется
    if not is_admin(message.from_user) and bonus_rolls_count <= 0:
        if user_id_str in roll_cooldowns:
            passed = current_time - roll_cooldowns[user_id_str]
            if passed < 10800: # 3 часа
                left = int(10800 - passed)
                h = left // 3600
                m = (left % 3600) // 60
                bot.send_message(message.chat.id, f"⏳ Ваши скауты еще не вернулись. Приходите через {h}ч {m}м.\n\n🎟 Или используйте промокод на бесплатные прокруты!")
                return

    all_cards = load_data('cards')
    if not all_cards:
        bot.send_message(message.chat.id, "❌ Ошибка: В базе данных еще нет футболистов.")
        return

    # ЛОГИКА ШАНСОВ (УДАЧА)
    luck_factor = users_db[user_id_str].get('bonus_luck', 1.0)
    rarity_keys = sorted(RARITY_STATS.keys())
    chance_weights = []
    
    for r_key in rarity_keys:
        base_chance = RARITY_STATS[r_key]['chance']
        # Если это эпики(4) или легенды(5), умножаем их шанс на бонус удачи
        if r_key >= 4:
            base_chance *= luck_factor
        chance_weights.append(base_chance)

    # Выбираем редкость на основе весов
    final_rarity = random.choices(rarity_keys, weights=chance_weights)[0]
    
    # Фильтруем карты по выбранной редкости
    possible_cards = [c for c in all_cards if c['stars'] == final_rarity]
    # Если такой редкости нет в базе карт, берем любую случайную
    if not possible_cards:
        possible_cards = all_cards
        
    reward_card = random.choice(possible_cards)
    
    # СПИСАНИЕ ПОПЫТКИ
    if bonus_rolls_count > 0:
        users_db[user_id_str]['free_rolls'] -= 1
        roll_status_text = f"🎫 Использован бонусный прокрут. Осталось: {users_db[user_id_str]['free_rolls']}"
    else:
        # Устанавливаем КД на 3 часа
        roll_cooldowns[user_id_str] = current_time
        roll_info_h = 3
        roll_status_text = f"⏳ Вы использовали попытку. Следующая через {roll_info_h} часа."

    # Сбрасываем множитель удачи до стандартного
    users_db[user_id_str]['bonus_luck'] = 1.0

    # ПРОВЕРКА НА ПОВТОРКУ В КОЛЛЕКЦИИ
    colls_db = load_data('colls')
    if user_id_str not in colls_db:
        colls_db[user_id_str] = []
    
    # Проверяем, есть ли уже карта с таким именем у игрока
    is_already_owned = any(owned['name'] == reward_card['name'] for owned in colls_db[user_id_str])
    
    if is_already_owned:
        # За повторку даем только 30% очков
        gain_points = int(RARITY_STATS[reward_card['stars']]['score'] * 0.3)
        duplicate_msg = "🔄 У вас уже есть такая карта! Получено 30% компенсации."
    else:
        # За новую карту даем полные очки
        gain_points = RARITY_STATS[reward_card['stars']]['score']
        duplicate_msg = "✨ Это новая карта в вашей коллекции!"
        colls_db[user_id_str].append(reward_card)
        save_data(colls_db, 'colls')

    # Обновляем баланс очков игрока
    users_db[user_id_str]['score'] += gain_points
    save_data(users_db, 'users')

    # Формируем красивое сообщение
    stars_str = "⭐" * reward_card['stars']
    pos_label = POSITIONS_RU.get(reward_card['pos'].upper(), reward_card['pos'])
    
    final_caption = (
        f"⚽️ **{reward_card['name']}**\n\n"
        f"📊 Рейтинг: {stars_str} ({RARITY_STATS[reward_card['stars']]['label']})\n"
        f"🎯 Позиция: {pos_label}\n\n"
        f"💠 {duplicate_msg}\n"
        f"💰 Очки: +{gain_points:,}\n"
        f"📈 Ваш баланс: {users_db[user_id_str]['score']:,}\n\n"
        f"{roll_status_text}"
    )
    
    bot.send_photo(message.chat.id, reward_card['photo'], caption=final_caption, parse_mode="Markdown")

# --- [9] ПВП АРЕНА И БОИ ---

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def open_arena_hub(message):
    if is_banned(message.from_user): return
    uid_str = str(message.from_user.id)
    time_now = time.time()
    
    # КД на ПВП — 15 минут
    if not is_admin(message.from_user):
        if uid_str in pvp_cooldowns and time_now - pvp_cooldowns[uid_str] < 900:
            rem_pvp = int(900 - (time_now - pvp_cooldowns[uid_str]))
            bot.send_message(message.chat.id, f"⏳ Ваши игроки восстанавливают силы. ПВП будет доступно через {rem_pvp//60} мин.")
            return

    pvp_markup = types.InlineKeyboardMarkup(row_width=1)
    pvp_markup.add(
        types.InlineKeyboardButton("🎲 Случайный соперник", callback_data="pvp_find_random"),
        types.InlineKeyboardButton("🏆 Мировой рейтинг", callback_data="pvp_leaderboard")
    )
    
    arena_text = (
        "🏟 **ФУТБОЛЬНАЯ АРЕНА**\n\n"
        "Здесь решается, чей состав сильнее.\n"
        "Сила вашей команды: " + str(get_team_power(uid_str)) + "\n\n"
        "Победа в матче дает **1,000 очков**!"
    )
    bot.send_message(message.chat.id, arena_text, reply_markup=pvp_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_find_random")
def run_match_making(call):
    users_db = load_data('users')
    p1_id = str(call.from_user.id)
    p1_power = get_team_power(p1_id)
    
    if p1_power == 0:
        bot.answer_callback_query(call.id, "❌ Ваш состав пуст! Поставьте игроков в меню '📋 Состав'.", show_alert=True)
        return

    # Ищем всех, у кого есть хоть какая-то сила в команде, кроме самого себя
    potential_enemies = [uid for uid in users_db if uid != p1_id and get_team_power(uid) > 0]
    
    if not potential_enemies:
        bot.answer_callback_query(call.id, "❌ Сейчас нет игроков онлайн с готовыми составами.", show_alert=True)
        return
        
    p2_id = random.choice(potential_enemies)
    p2_power = get_team_power(p2_id)
    
    # Расчет вероятности победы (зависит от силы)
    # Используем возведение в степень, чтобы разница в силе была более значимой
    w1 = p1_power ** 1.3
    w2 = p2_power ** 1.3
    
    winner_id = random.choices([p1_id, p2_id], weights=[w1, w2])[0]
    
    # Начисляем награду победителю
    users_db[winner_id]['score'] += 1000
    save_data(users_db, 'users')
    
    # Записываем кулдаун инициатору
    pvp_cooldowns[p1_id] = time.time()

    winner_nick = users_db[winner_id]['username']
    
    match_report = (
        "🏟 **ОТЧЕТ О МАТЧЕ**\n\n"
        f"🏠 Хозяева: {users_db[p1_id]['nick']} (Сила: {p1_power})\n"
        f"🚀 Гости: {users_db[p2_id]['nick']} (Сила: {p2_power})\n\n"
        "➖➖➖➖➖➖➖➖\n"
        f"🏆 Итог матча: победа **{winner_nick}**!\n"
        "💰 Награда: +1,000 очков."
    )
    bot.send_message(call.message.chat.id, match_report, parse_mode="Markdown")

# --- [10] ПРОФИЛЬ, ТОП И ПРОСМОТР КОЛЛЕКЦИИ ---

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_user_profile(message):
    if is_banned(message.from_user): return
    uid_str = str(message.from_user.id)
    u_db = load_data('users')
    colls = load_data('colls')
    
    user_data = u_db.get(uid_str)
    my_cards_count = len(colls.get(uid_str, []))
    
    profile_msg = (
        f"👤 **ВАШ ПРОФИЛЬ**\n\n"
        f"🆔 ID: `{uid_str}`\n"
        f"👤 Ник: {user_data['nick']}\n\n"
        f"💠 Очки баланса: `{user_data['score']:,}`\n"
        f"🗂 Всего карт: {my_cards_count} шт.\n"
        f"🛡 Сила команды: **{get_team_power(uid_str)}**\n"
        f"🎫 Бонусные прокруты: **{user_data.get('free_rolls', 0)}**"
    )
    bot.send_message(message.chat.id, profile_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_global_top(message):
    if is_banned(message.from_user): return
    u_db = load_data('users')
    # Сортируем по убыванию очков и берем топ-10
    top_list = sorted(u_db.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    text_top = "🏆 **ТОП-10 МАЖОРОВ (ПО ОЧКАМ):**\n\n"
    for i, (uid, data) in enumerate(top_list, 1):
        text_top += f"{i}. {data['username']} — `{data['score']:,}`\n"
    
    bot.send_message(message.chat.id, text_top, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def show_collection_hub(message):
    if is_banned(message.from_user): return
    markup_stars = types.InlineKeyboardMarkup()
    for s in range(1, 6):
        markup_stars.add(types.InlineKeyboardButton(f"{'⭐'*s} Показать эти карты", callback_data=f"show_coll_{s}"))
    
    bot.send_message(message.chat.id, "🗂 **ВАШ АЛЬБОМ КАРТОЧЕК**\nВыберите редкость для просмотра:", reply_markup=markup_stars, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("show_coll_"))
def process_collection_view(call):
    star_level = int(call.data.split("_")[-1])
    uid_str = str(call.from_user.id)
    my_full_coll = load_data('colls').get(uid_str, [])
    
    # Фильтруем те, что подходят по звездам
    filtered = [card for card in my_full_coll if card['stars'] == star_level]
    
    if not filtered:
        bot.answer_callback_query(call.id, f"У вас нет карт {star_level} звезд.", show_alert=True)
        return
    
    output_text = f"🗂 **ВАШИ КАРТЫ {star_level}⭐:**\n\n"
    for item in filtered:
        output_text += f"• {item['name']} ({item['pos']})\n"
        
    bot.send_message(call.message.chat.id, output_text, parse_mode="Markdown")

# --- [11] УПРАВЛЕНИЕ СОСТАВОМ (СЛОТЫ) ---

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_main_menu(message):
    if is_banned(message.from_user): return
    uid = message.from_user.id
    bot.send_message(message.chat.id, "📋 **РЕДАКТОР СОСТАВА**\n\nВыберите позицию, чтобы назначить игрока из коллекции.", reply_markup=make_squad_buttons(uid), parse_mode="Markdown")

def make_squad_buttons(uid):
    """Строит инлайн-меню из 7 кнопок (позиций)."""
    squad_data = load_data('squads')
    current_squad = squad_data.get(str(uid), [None] * 7)
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for i in range(7):
        slot = SQUAD_SLOTS[i]
        player_in_slot = current_squad[i]
        
        if player_in_slot:
            name_btn = f"{slot['label']}: {player_in_slot['name']} ({player_in_slot['stars']}⭐)"
        else:
            name_btn = f"{slot['label']}: ❌ Пусто"
            
        kb.add(types.InlineKeyboardButton(name_btn, callback_data=f"edit_slot_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_slot_"))
def show_players_for_slot(call):
    slot_id = int(call.data.split("_")[-1])
    uid_str = str(call.from_user.id)
    target_pos = SQUAD_SLOTS[slot_id]["code"]
    
    # Ищем в коллекции игрока с подходящей позицией
    user_coll = load_data('colls').get(uid_str, [])
    suitable_players = [p for p in user_coll if p['pos'].upper() == target_pos]
    
    if not suitable_players:
        bot.answer_callback_query(call.id, f"❌ У вас нет игроков позиции {target_pos} в коллекции!", show_alert=True)
        return
    
    kb_choice = types.InlineKeyboardMarkup(row_width=1)
    for p in suitable_players:
        kb_choice.add(types.InlineKeyboardButton(f"{p['name']} ({p['stars']}⭐)", callback_data=f"set_pl_{slot_id}_{p['name']}"))
    
    kb_choice.add(types.InlineKeyboardButton("🚫 Оставить пустым", callback_data=f"set_pl_{slot_id}_empty"))
    
    bot.edit_message_text(f"Выберите игрока на позицию **{target_pos}**:", call.message.chat.id, call.message.message_id, reply_markup=kb_choice, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_pl_"))
def finalize_slot_setting(call):
    # set_pl_ИНДЕКС_ИМЯ
    data_parts = call.data.split("_")
    s_idx = int(data_parts[2])
    p_name = data_parts[3]
    uid_str = str(call.from_user.id)
    
    sq_db = load_data('squads')
    if uid_str not in sq_db:
        sq_db[uid_str] = [None] * 7
        
    if p_name == "empty":
        sq_db[uid_str][s_idx] = None
    else:
        user_total_coll = load_data('colls').get(uid_str, [])
        # Находим объект карты по имени
        found_card = next((x for x in user_total_coll if x['name'] == p_name), None)
        sq_db[uid_str][s_idx] = found_card
        
    save_data(sq_db, 'squads')
    bot.edit_message_text("✅ Состав успешно обновлен!", call.message.chat.id, call.message.message_id, reply_markup=make_squad_buttons(uid_str))

# --- [12] АДМИН-ПАНЕЛЬ: ДОБАВЛЕНИЕ И ИЗМЕНЕНИЕ КАРТ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_admin_panel(message):
    if not is_admin(message.from_user): return
    bot.send_message(message.chat.id, "🛠 **ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# [ДОБАВЛЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_card_1(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Введите ФИО нового футболиста:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, admin_add_card_2)

def admin_add_card_2(message):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    name = message.text
    sent = bot.send_message(message.chat.id, "Введите позицию (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):")
    bot.register_next_step_handler(sent, admin_add_card_3, name)

def admin_add_card_3(message, name):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    pos = message.text.upper()
    sent = bot.send_message(message.chat.id, "Сколько звезд (от 1 до 5):")
    bot.register_next_step_handler(sent, admin_add_card_4, name, pos)

def admin_add_card_4(message, name, pos):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    try:
        stars = int(message.text)
        sent = bot.send_message(message.chat.id, "Теперь отправьте ФОТОГРАФИЮ этой карточки:")
        bot.register_next_step_handler(sent, admin_add_card_5, name, pos, stars)
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно ввести число (1-5).")

def admin_add_card_5(message, name, pos, stars):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фотография. Процесс отменен.")
        return
    
    c_db = load_data('cards')
    c_db.append({
        "name": name,
        "pos": pos,
        "stars": stars,
        "photo": message.photo[-1].file_id
    })
    save_data(c_db, 'cards')
    bot.send_message(message.chat.id, f"✅ Игрок {name} успешно добавлен в игру!", reply_markup=get_admin_keyboard())

# [ИЗМЕНЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_list(message):
    if not is_admin(message.from_user): return
    db_cards = load_data('cards')
    if not db_cards:
        bot.send_message(message.chat.id, "База карт пуста.")
        return
    
    markup_edit = types.InlineKeyboardMarkup()
    for card_obj in db_cards:
        markup_edit.add(types.InlineKeyboardButton(f"⚙️ {card_obj['name']}", callback_data=f"edit_card_{card_obj['name']}"))
    bot.send_message(message.chat.id, "Выберите игрока для редактирования:", reply_markup=markup_edit)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_card_"))
def admin_edit_field_choice(call):
    c_name = call.data.replace("edit_card_", "")
    kb_fields = types.InlineKeyboardMarkup(row_width=2)
    kb_fields.add(
        types.InlineKeyboardButton("Имя", callback_data=f"f_edit_{c_name}_name"),
        types.InlineKeyboardButton("Позиция", callback_data=f"f_edit_{c_name}_pos"),
        types.InlineKeyboardButton("Звезды", callback_data=f"f_edit_{c_name}_stars"),
        types.InlineKeyboardButton("Фото", callback_data=f"f_edit_{c_name}_photo")
    )
    bot.edit_message_text(f"Что именно меняем у игрока {c_name}?", call.message.chat.id, call.message.message_id, reply_markup=kb_fields)

@bot.callback_query_handler(func=lambda c: c.data.startswith("f_edit_"))
def admin_edit_input_start(call):
    # f_edit_ИМЯ_ПОЛЕ
    parts = call.data.split("_")
    c_name = parts[2]
    field_to_change = parts[3]
    
    msg = bot.send_message(call.message.chat.id, f"Введите новое значение для **{field_to_change}**:", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_edit_final_save, c_name, field_to_change)

def admin_edit_final_save(message, c_name, field_to_change):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    
    db_cards = load_data('cards')
    found = False
    for item in db_cards:
        if item['name'] == c_name:
            if field_to_change == "photo":
                if not message.photo:
                    bot.send_message(message.chat.id, "Ошибка: нужно отправить фото.")
                    return
                item[field_to_change] = message.photo[-1].file_id
            elif field_to_change == "stars":
                item[field_to_change] = int(message.text)
            else:
                item[field_to_change] = message.text if field_to_change != "pos" else message.text.upper()
            found = True
            break
            
    if found:
        save_data(db_cards, 'cards')
        bot.send_message(message.chat.id, "✅ Изменения применены успешно!", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "Ошибка: игрок не найден в базе.")

# [УДАЛЕНИЕ КАРТЫ]
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_list(message):
    if not is_admin(message.from_user): return
    db_cards = load_data('cards')
    markup_del = types.InlineKeyboardMarkup()
    for card_obj in db_cards:
        markup_del.add(types.InlineKeyboardButton(f"❌ Удалить {card_obj['name']}", callback_data=f"del_card_{card_obj['name']}"))
    bot.send_message(message.chat.id, "Выберите карту для безвозвратного удаления:", reply_markup=markup_del)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_card_"))
def admin_delete_confirm(call):
    c_name = call.data.replace("del_card_", "")
    db_cards = load_data('cards')
    # Фильтруем список, оставляя всех, кроме этого имени
    new_cards_list = [x for x in db_cards if x['name'] != c_name]
    save_data(new_cards_list, 'cards')
    bot.edit_message_text(f"🗑 Игрок **{c_name}** был удален из системы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- [13] АДМИН-ПАНЕЛЬ: ПРОМОКОДЫ ---

@bot.message_handler(func=lambda m: m.text == "🎟 +Промокод")
def admin_promo_add_1(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Напишите сам код (например: FOOTBALL2026):", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, admin_promo_add_2)

def admin_promo_add_2(message):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    code_str = message.text.strip().upper()
    
    markup_p_type = types.InlineKeyboardMarkup()
    markup_p_type.add(
        types.InlineKeyboardButton("🎫 Бесплатные прокруты", callback_data=f"p_type_{code_str}_rolls"),
        types.InlineKeyboardButton("💠 Очки (валюта)", callback_data=f"p_type_{code_str}_points"),
        types.InlineKeyboardButton("🍀 Удача (Luck)", callback_data=f"p_type_{code_str}_luck")
    )
    bot.send_message(message.chat.id, f"Какой бонус будет давать код `{code_str}`?", reply_markup=markup_p_type, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_type_"))
def admin_promo_add_3(call):
    # p_type_КОД_ТИП
    parts = call.data.split("_")
    code_str = parts[2]
    code_type = parts[3]
    
    msg = bot.send_message(call.message.chat.id, f"Введите ЧИСЛО (количество бонуса для {code_type}):")
    bot.register_next_step_handler(msg, admin_promo_final_save, code_str, code_type)

def admin_promo_final_save(message, code_str, code_type):
    try:
        val = float(message.text)
        db_promos = load_data('promos')
        db_promos[code_str] = {
            "type": code_type,
            "value": val
        }
        save_data(db_promos, 'promos')
        bot.send_message(message.chat.id, f"✅ Промокод `{code_str}` успешно создан!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "Ошибка! Нужно было ввести число. Попробуйте создать код заново.")

# [НОВАЯ ФУНКЦИЯ: УДАЛЕНИЕ ПРОМОКОДА]
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить промокод")
def admin_promo_delete_list(message):
    if not is_admin(message.from_user): return
    db_p = load_data('promos')
    if not db_p:
        bot.send_message(message.chat.id, "Активных промокодов нет.")
        return
        
    kb_del_p = types.InlineKeyboardMarkup(row_width=1)
    for code_name in db_p.keys():
        kb_del_p.add(types.InlineKeyboardButton(f"🗑 Удалить {code_name}", callback_data=f"del_promo_{code_name}"))
    
    bot.send_message(message.chat.id, "Выберите промокод для деактивации:", reply_markup=kb_del_p)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_promo_"))
def admin_promo_delete_execute(call):
    code_to_del = call.data.replace("del_promo_", "")
    db_p = load_data('promos')
    
    if code_to_del in db_p:
        del db_p[code_to_del]
        save_data(db_p, 'promos')
        bot.edit_message_text(f"✅ Промокод `{code_to_del}` удален из базы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "Код уже не существует.")

# --- [14] АДМИН-ПАНЕЛЬ: БАНЫ И ОБНУЛЕНИЕ ---

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_start(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Введите @username или ID для бана:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, process_ban_system, True)

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_start(message):
    if not is_admin(message.from_user): return
    sent = bot.send_message(message.chat.id, "Введите @username или ID для разбана:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(sent, process_ban_system, False)

def process_ban_system(message, is_blocking):
    if message.text == "❌ Отмена": return cancel_to_main(message)
    
    target_str = message.text.replace("@", "").lower().strip()
    db_bans = load_data('bans')
    
    if is_blocking:
        if target_str not in db_bans:
            db_bans.append(target_str)
            res_msg = f"✅ Пользователь `{target_str}` заблокирован."
        else:
            res_msg = "Он уже в черном списке."
    else:
        if target_str in db_bans:
            db_bans.remove(target_str)
            res_msg = f"✅ Пользователь `{target_str}` разблокирован."
        else:
            res_msg = "Пользователя нет в списке банов."
            
    save_data(db_bans, 'bans')
    bot.send_message(message.chat.id, res_msg, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_warning(message):
    if not is_admin(message.from_user): return
    kb_reset = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb_reset.add("🚨 ПОДТВЕРЖДАЮ ПОЛНОЕ УДАЛЕНИЕ", "❌ Отмена")
    bot.send_message(message.chat.id, "🚨 **КРИТИЧЕСКОЕ ДЕЙСТВИЕ**\n\nЭто удалит ВСЕХ пользователей, их ОЧКИ, КАРТЫ и СОСТАВЫ. Это нельзя отменить!", reply_markup=kb_reset, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚨 ПОДТВЕРЖДАЮ ПОЛНОЕ УДАЛЕНИЕ")
def admin_reset_final(message):
    if not is_admin(message.from_user): return
    # Очищаем основные файлы данных
    save_data({}, 'users')
    save_data({}, 'colls')
    save_data({}, 'squads')
    bot.send_message(message.chat.id, "🧨 База данных полностью очищена. Все игроки удалены.", reply_markup=get_admin_keyboard())

# --- [15] СЛУЖЕБНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_to_main_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def cancel_to_main(message):
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=get_main_keyboard(message.from_user.id))

# Запуск бота
if __name__ == "__main__":
    print("----------------------------")
    print("Бот запущен и готов к работе")
    print("----------------------------")
    bot.infinity_polling()
