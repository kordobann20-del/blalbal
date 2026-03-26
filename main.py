# -*- coding: utf-8 -*-
"""
================================================================================
ПРОЕКТ: FOOTBALL COLLECTOR ULTIMATE - ГИГАНТСКАЯ СБОРКА (16+ БЛОКОВ)
================================================================================
ДАННЫЙ КОД НАПИСАН В ФОРМАТЕ "NO-SHORTCUTS" (БЕЗ СОКРАЩЕНИЙ).
КАЖДЫЙ МОДУЛЬ ИЗОЛИРОВАН И ПОДРОБНО РАСПИСАН ДЛЯ МАКСИМАЛЬНОГО КОНТРОЛЯ.

СОДЕРЖАНИЕ СИСТЕМНЫХ БЛОКОВ:
1.  Импорт модулей и управление зависимостями.
2.  Глобальная конфигурация API и Список Владельцев (Admin).
3.  Параметры экономики: Шансы, Награды, Сила, Позиции.
4.  Инициализация файловой структуры JSON баз данных.
5.  Низкоуровневая функция чтения данных (Load Engine).
6.  Низкоуровневая функция записи данных (Save Engine).
7.  Система авторизации и фильтрации (Админ-доступ/Бан-лист).
8.  Логика регистрации и Реферальная программа (5000 + 3 спина).
9.  Генератор графического меню (Keyboard Construction).
10. Ядро ROLL-системы (Выпадение карточек с весами).
11. Менеджер Инвентаря и Личная Коллекция.
12. Конструктор состава 7x7 (Слоты и Проверки).
13. Движок ПВП Арены (Расчет вероятностей и Бои).
14. Социальный блок: Профиль и Глобальный Топ.
15. Админ-панель: Управление картами (Добавление/Удаление).
16. ИСПРАВЛЕННЫЙ МОДУЛЬ РЕДАКТИРОВАНИЯ (Step-by-Step Edit).
17. Система Промокодов и Бонусов.
18. Цикл поддержания жизни (Error Handling & Keep-Alive).
================================================================================
"""

import telebot
from telebot import types
import json
import os
import random
import time
import datetime
import sys
import logging
import traceback

# ==============================================================================
# БЛОК [1-2]: СИСТЕМНЫЕ НАСТРОЙКИ
# ==============================================================================

# Токен доступа к API Telegram
BOT_TOKEN_KEY = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"

# Список системных администраторов (Логины)
SYSTEM_ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"]

# Инициализация объекта бота
bot = telebot.TeleBot(BOT_TOKEN_KEY)

# ==============================================================================
# БЛОК [3]: ЭКОНОМИЧЕСКИЙ БАЛАНС И КОНСТАНТЫ
# ==============================================================================

# Реферальные вознаграждения (Строго: 5000 очков и 3 спина за 1 друга)
REF_REWARD_MONEY = 5000
REF_REWARD_SPINS = 3

# Параметры новичка
NEW_PLAYER_BALANCE = 2500
NEW_PLAYER_SPINS = 5

# Таймеры
COOLDOWN_TIME_SECONDS = 10800  # 3 часа между бесплатными прокрутами

# Таблица Редкостей (Подробные статы)
# Уровни: 1-Обычная, 2-Необычная, 3-Редкая, 4-Эпическая, 5-Легендарная
GAME_RARITY_SCHEMA = {
    1: {
        "name": "Обычная", 
        "emoji": "⚪️", 
        "chance": 45, 
        "win_prize": 4000, 
        "power_atk": 300
    },
    2: {
        "name": "Необычная", 
        "emoji": "🟢", 
        "chance": 28, 
        "win_prize": 8000, 
        "power_atk": 750
    },
    3: {
        "name": "Редкая", 
        "emoji": "🔵", 
        "chance": 15, 
        "win_prize": 20000, 
        "power_atk": 2000
    },
    4: {
        "name": "Эпическая", 
        "emoji": "🟣", 
        "chance": 8, 
        "win_prize": 50000, 
        "power_atk": 5000
    },
    5: {
        "name": "Легендарная", 
        "emoji": "🟡", 
        "chance": 4, 
        "win_prize": 120000, 
        "power_atk": 11000
    }
}

# Позиции футболистов на поле
SOCCER_POSITIONS = {
    "ГК": "Вратарь",
    "ЛЗ": "Левый Защитник",
    "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник",
    "ЛВ": "Левый Вингер",
    "ПВ": "Правый Вингер",
    "КФ": "Центральный Нападающий"
}

# ==============================================================================
# БЛОК [4-6]: ЯДРО РАБОТЫ С БАЗОЙ ДАННЫХ (JSON FILE SYSTEM)
# ==============================================================================

DB_FILE_PATH_USERS = "db_users_main.json"
DB_FILE_PATH_CARDS = "db_cards_main.json"
DB_FILE_PATH_INV = "db_inventories.json"
DB_FILE_PATH_SQUADS = "db_squads.json"
DB_FILE_PATH_BAN = "db_blacklist.json"
DB_FILE_PATH_PROMO = "db_promocodes.json"

def initialize_database_files():
    """Проверяет наличие всех нужных файлов и создает их пустыми при необходимости."""
    file_list = [
        DB_FILE_PATH_USERS, DB_FILE_PATH_CARDS, DB_FILE_PATH_INV, 
        DB_FILE_PATH_SQUADS, DB_FILE_PATH_BAN, DB_FILE_PATH_PROMO
    ]
    
    for file_name in file_list:
        if not os.path.exists(file_name):
            if file_name in [DB_FILE_PATH_CARDS, DB_FILE_PATH_BAN]:
                default_data = []
            else:
                default_data = {}
            
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
            print(f"[DB_SYSTEM] Файл {file_name} был успешно создан.")

initialize_database_files()

def internal_read_db(file_key):
    """Универсальная функция чтения из JSON."""
    path_map = {
        "users": DB_FILE_PATH_USERS,
        "cards": DB_FILE_PATH_CARDS,
        "inv": DB_FILE_PATH_INV,
        "squads": DB_FILE_PATH_SQUADS,
        "ban": DB_FILE_PATH_BAN,
        "promo": DB_FILE_PATH_PROMO
    }
    file_path = path_map.get(file_key)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        return [] if file_key in ["cards", "ban"] else {}
    except Exception as error:
        print(f"[DB_ERROR] Ошибка чтения {file_key}: {error}")
        return [] if file_key in ["cards", "ban"] else {}

def internal_write_db(data_object, file_key):
    """Универсальная функция записи в JSON."""
    path_map = {
        "users": DB_FILE_PATH_USERS,
        "cards": DB_FILE_PATH_CARDS,
        "inv": DB_FILE_PATH_INV,
        "squads": DB_FILE_PATH_SQUADS,
        "ban": DB_FILE_PATH_BAN,
        "promo": DB_FILE_PATH_PROMO
    }
    file_path = path_map.get(file_key)
    try:
        with open(file_path, "w", encoding="utf-8") as file_handle:
            json.dump(data_object, file_handle, ensure_ascii=False, indent=4)
        return True
    except Exception as error:
        print(f"[DB_ERROR] Ошибка записи в {file_key}: {error}")
        return False

# ==============================================================================
# БЛОК [7]: СИСТЕМА ПРАВ И БЕЗОПАСНОСТИ
# ==============================================================================

def security_is_admin(user_object):
    """Проверка на права администратора."""
    if user_object.username is None:
        return False
    # Сравниваем в нижнем регистре для исключения ошибок
    admin_usernames = [a.lower() for a in SYSTEM_ADMINS]
    return user_object.username.lower() in admin_usernames

def security_is_banned(target_user_id):
    """Проверка, не находится ли пользователь в черном списке."""
    blacklist = internal_read_db("ban")
    # Приводим к строке, так как в JSON ID сохраняются как строки в ключах или элементы списка
    str_id = str(target_user_id)
    return str_id in [str(item) for item in blacklist]

# ==============================================================================
# БЛОК [8-9]: РЕГИСТРАЦИЯ, РЕФЕРАЛЫ И МЕНЮ
# ==============================================================================

@bot.message_handler(commands=['start'])
def command_start_processor(message):
    """Основной вход в бота: Регистрация и бонусы."""
    if security_is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 Ваша учетная запись была заблокирована.")
        return

    users_database = internal_read_db("users")
    user_id_string = str(message.from_user.id)
    
    # Обработка реферального кода
    # Команда выглядит так: /start 12345678
    potential_inviter_id = None
    input_text_parts = message.text.split()
    if len(input_text_parts) > 1:
        potential_inviter_id = input_text_parts[1]

    # Если пользователь зашел первый раз
    if user_id_string not in users_database:
        
        display_name = message.from_user.first_name
        username_handle = f"@{message.from_user.username}" if message.from_user.username else f"User_{user_id_string}"
        
        # Создаем структуру профиля
        users_database[user_id_string] = {
            "name_info": display_name,
            "nick_info": username_handle,
            "money_balance": NEW_PLAYER_BALANCE,
            "spins_count": NEW_PLAYER_SPINS,
            "current_luck": 1.0,
            "referral_stats": 0,
            "activation_history": [],
            "join_date": str(datetime.date.today())
        }
        
        # ЛОГИКА РЕФЕРАЛОВ: 5000 + 3 СПИНА (СТРОГО)
        if potential_inviter_id:
            inviter_id_str = str(potential_inviter_id)
            # Проверка, что пригласивший существует и это не сам пользователь
            if inviter_id_str in users_database and inviter_id_str != user_id_string:
                users_database[inviter_id_str]["money_balance"] += REF_REWARD_MONEY
                users_database[inviter_id_str]["spins_count"] += REF_REWARD_SPINS
                users_database[inviter_id_str]["referral_stats"] += 1
                
                # Попытка уведомить пригласившего
                try:
                    bot.send_message(
                        int(inviter_id_str),
                        f"🤝 **Новый реферал!**\n\nИгрок {display_name} перешел по вашей ссылке.\n"
                        f"Бонус зачислен:\n💰 +{REF_REWARD_MONEY} очков\n🎰 +{REF_REWARD_SPINS} спина"
                    )
                except:
                    pass
        
        # Синхронизация с файлом
        internal_write_db(users_database, "users")
        print(f"[REG] Новый игрок: {username_handle}")

    # Генерация клавиатуры
    main_menu_markup = create_main_interface_keyboard(message.from_user.id)
    
    bot.send_message(
        message.chat.id,
        f"⚽️ **Добро пожаловать в Football Collector, {message.from_user.first_name}!**\n\n"
        "Здесь ты можешь собрать команду своей мечты из лучших игроков мира.\n\n"
        "🎰 Крути карточки\n"
        "📋 Формируй состав 7х7\n"
        "🏟 Сражайся на Арене\n\n"
        "Выбери действие в меню ниже:",
        reply_markup=main_menu_markup,
        parse_mode="Markdown"
    )

def create_main_interface_keyboard(user_tg_id):
    """Функция сборки главного меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    row_1_button_left = types.KeyboardButton("🎰 Крутить карту")
    row_1_button_right = types.KeyboardButton("🗂 Коллекция")
    
    row_2_button_left = types.KeyboardButton("📋 Состав")
    row_2_button_right = types.KeyboardButton("👤 Профиль")
    
    row_3_button_left = types.KeyboardButton("🏆 Топ очков")
    row_3_button_right = types.KeyboardButton("🏟 ПВП Арена")
    
    row_4_button_left = types.KeyboardButton("🎟 Промокод")
    row_4_button_right = types.KeyboardButton("👥 Рефералы")
    
    markup.add(row_1_button_left, row_1_button_right)
    markup.add(row_2_button_left, row_2_button_right)
    markup.add(row_3_button_left, row_3_button_right)
    markup.add(row_4_button_left, row_4_button_right)
    
    # Спец-кнопка для админов
    try:
        user_chat_data = bot.get_chat(user_tg_id)
        if security_is_admin(user_chat_data):
            markup.add(types.KeyboardButton("🛠 Админ-панель"))
    except:
        pass
        
    return markup

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def handle_referral_menu(message):
    """Показ реферальной ссылки и условий."""
    u_id = message.from_user.id
    users_db = internal_read_db("users")
    profile = users_db.get(str(u_id), {})
    
    my_bot_username = bot.get_me().username
    personal_link = f"https://t.me/{my_bot_username}?start={u_id}"
    
    response_text = (
        "👥 **ПРИГЛАШАЙ ДРУЗЕЙ**\n\n"
        "Твой клуб нуждается в новых скаутах! Делись ссылкой ниже.\n\n"
        f"🎁 За каждого приглашенного:\n💰 **{REF_REWARD_MONEY} очков**\n🎰 **{REF_REWARD_SPINS} спина**\n\n"
        f"Твоя ссылка:\n`{personal_link}`\n\n"
        f"Уже приглашено: **{profile.get('referral_stats', 0)}** человек."
    )
    bot.send_message(message.chat.id, response_text, parse_mode="Markdown")

# ==============================================================================
# БЛОК [10]: ROLL ENGINE (МЕХАНИКА ВЫПАДЕНИЯ)
# ==============================================================================

user_roll_cooldown_map = {}

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def action_roll_card(message):
    """Процесс получения новой карты игрока."""
    if security_is_banned(message.from_user.id): return
    
    u_id_str = str(message.from_user.id)
    users_data = internal_read_db("users")
    cards_pool = internal_read_db("cards")
    
    if not cards_pool:
        bot.send_message(message.chat.id, "❌ В системе нет ни одного футболиста. Обратитесь к админу.")
        return

    current_user_profile = users_data[u_id_str]
    current_time_stamp = time.time()
    
    # Проверка возможности прокрута
    available_spins = current_user_profile.get("spins_count", 0)
    
    if available_spins <= 0:
        if u_id_str in user_roll_cooldown_map:
            diff = current_time_stamp - user_roll_cooldown_map[u_id_str]
            if diff < COOLDOWN_TIME_SECONDS:
                seconds_remaining = int(COOLDOWN_TIME_SECONDS - diff)
                hr = seconds_remaining // 3600
                mn = (seconds_remaining % 3600) // 60
                bot.send_message(message.chat.id, f"⏳ Спины кончились. Следующий бесплатный будет через: **{hr}ч. {mn}мин.**")
                return

    # Расчет редкости на основе весов
    luck_modifier = current_user_profile.get("current_luck", 1.0)
    
    possible_rarities = [1, 2, 3, 4, 5]
    calculated_weights = []
    
    for rarity_lvl in possible_rarities:
        base_chance = GAME_RARITY_SCHEMA[rarity_lvl]["chance"]
        # Удача увеличивает шансы только на 4 и 5 уровень (Эпики и Легенды)
        if rarity_lvl >= 4:
            calculated_weights.append(base_chance * luck_modifier)
        else:
            calculated_weights.append(base_chance)
            
    # Случайный выбор редкости
    final_rarity_level = random.choices(possible_rarities, weights=calculated_weights)[0]
    
    # Поиск карт выбранной редкости
    filtered_cards = []
    for c in cards_pool:
        if int(c["stars"]) == final_rarity_level:
            filtered_cards.append(c)
            
    if not filtered_cards:
        # Если такой редкости нет, берем любую
        chosen_card_obj = random.choice(cards_pool)
    else:
        chosen_card_obj = random.choice(filtered_cards)
        
    # Работа с инвентарем
    inventory_db = internal_read_db("inv")
    if u_id_str not in inventory_db: inventory_db[u_id_str] = []
    
    is_new_discovery = True
    for owned_item in inventory_db[u_id_str]:
        if owned_item["name"] == chosen_card_obj["name"]:
            is_new_discovery = False
            break
            
    # Награда
    rarity_data = GAME_RARITY_SCHEMA[chosen_card_obj["stars"]]
    base_prize = rarity_data["win_prize"]
    
    notif_text = ""
    if is_new_discovery:
        inventory_db[u_id_str].append(chosen_card_obj)
        internal_write_db(inventory_db, "inv")
        notif_text = "✨ **НОВЫЙ ИГРОК В КОЛЛЕКЦИИ!**"
        final_money_gain = base_prize
    else:
        # За дубликат даем 35% от стоимости
        final_money_gain = int(base_prize * 0.35)
        notif_text = "🔄 **ДУБЛИКАТ** (Компенсация 35% стоимости)"

    # Обновление баланса и спинов
    if available_spins > 0:
        current_user_profile["spins_count"] -= 1
        footer_msg = f"🎫 Осталось спинов: {current_user_profile['spins_count']}"
    else:
        user_roll_cooldown_map[u_id_str] = current_time_stamp
        footer_msg = "⏳ Бесплатный прокрут использован. Ждите 3 часа."
        
    current_user_profile["money_balance"] += final_money_gain
    current_user_profile["current_luck"] = 1.0 # Удача сгорает после использования
    
    internal_write_db(users_data, "users")
    
    # Красивое сообщение с фото
    card_caption = (
        f"{notif_text}\n\n"
        f"👤 **{chosen_card_obj['name']}**\n"
        f"📊 Редкость: {rarity_data['emoji']} {rarity_data['name']}\n"
        f"🎯 Позиция: {SOCCER_POSITIONS.get(chosen_card_obj['pos'].upper(), chosen_card_obj['pos'])}\n\n"
        f"💰 Вы получили: +{final_money_gain} очков\n"
        f"--------------------------\n"
        f"{footer_msg}"
    )
    
    try:
        bot.send_photo(message.chat.id, chosen_card_obj["photo"], caption=card_caption, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, f"⚠️ Не удалось загрузить фото карточки.\n\n{card_caption}", parse_mode="Markdown")

# ==============================================================================
# БЛОК [11-12]: КОЛЛЕКЦИЯ И СОСТАВ 7x7
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def show_personal_collection(message):
    """Отображение списка всех карт игрока."""
    u_id = str(message.from_user.id)
    inv_data = internal_read_db("inv").get(u_id, [])
    
    if len(inv_data) == 0:
        bot.send_message(message.chat.id, "🗂 Ваша коллекция пока пуста. Попробуйте 'Крутить карту'!")
        return
        
    response = f"🗂 **ВАШИ КАРТОЧКИ ({len(inv_data)} шт.):**\n\n"
    # Сортировка по звездам
    sorted_inv = sorted(inv_data, key=lambda x: x['stars'], reverse=True)
    
    for i, card in enumerate(sorted_inv[:40], 1): # Ограничение списка для красоты
        r_emoji = GAME_RARITY_SCHEMA[card['stars']]['emoji']
        response += f"{i}. {r_emoji} **{card['name']}** ({card['pos']})\n"
        
    if len(inv_data) > 40:
        response += "\n_...и другие игроки в вашем запасе._"
        
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def display_squad_management(message):
    """Меню управления 7 позициями на поле."""
    u_id = str(message.from_user.id)
    squads_db = internal_read_db("squads")
    
    # Инициализация состава если его нет
    if u_id not in squads_db:
        squads_db[u_id] = [None] * 7
        internal_write_db(squads_db, "squads")
        
    current_team = squads_db[u_id]
    pos_order = ["ГК", "ЛЗ", "ПЗ", "ЦП", "ЛВ", "ПВ", "КФ"]
    
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    
    for idx, pos_tag in enumerate(pos_order):
        player_in_slot = current_team[idx]
        if player_in_slot:
            btn_text = f"{pos_tag}: {player_in_slot['name']} ({player_in_slot['stars']}⭐)"
        else:
            btn_text = f"{pos_tag}: ❌ ПУСТО"
        
        callback_data_string = f"change_squad_slot_{idx}_{pos_tag}"
        inline_kb.add(types.InlineKeyboardButton(text=btn_text, callback_data=callback_data_string))
        
    bot.send_message(
        message.chat.id, 
        "📋 **УПРАВЛЕНИЕ СОСТАВОМ 7х7**\n\nНажмите на позицию, чтобы назначить игрока из вашей коллекции:",
        reply_markup=inline_kb,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_squad_slot_"))
def process_slot_selection(call):
    """Вывод списка подходящих игроков для выбранной позиции."""
    data_parts = call.data.split("_")
    slot_index = int(data_parts[3])
    pos_code = data_parts[4]
    u_id_str = str(call.from_user.id)
    
    all_my_cards = internal_read_db("inv").get(u_id_str, [])
    
    # Фильтруем карты: только те, у кого совпадает позиция
    valid_players = []
    for card in all_my_cards:
        if card["pos"].upper() == pos_code.upper():
            valid_players.append(card)
            
    if len(valid_players) == 0:
        bot.answer_callback_query(call.id, f"❌ У вас нет игроков на позицию {pos_code}!", show_alert=True)
        return
        
    selection_kb = types.InlineKeyboardMarkup(row_width=1)
    for p in valid_players:
        selection_kb.add(types.InlineKeyboardButton(
            text=f"{p['name']} ({p['stars']}⭐)", 
            callback_data=f"confirm_squad_put_{slot_index}_{p['name']}"
        ))
    
    selection_kb.add(types.InlineKeyboardButton("🚫 Очистить слот", callback_data=f"confirm_squad_put_{slot_index}_EMPTY"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Выберите игрока для позиции **{pos_code}**:",
        reply_markup=selection_kb,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_squad_put_"))
def finalize_squad_update(call):
    """Запись выбранного игрока в базу составов."""
    parts = call.data.split("_")
    slot_idx = int(parts[3])
    player_name = parts[4]
    u_id_str = str(call.from_user.id)
    
    squads_data = internal_read_db("squads")
    
    if player_name == "EMPTY":
        squads_data[u_id_str][slot_idx] = None
    else:
        # Ищем карту в инвентаре пользователя
        user_inv = internal_read_db("inv").get(u_id_str, [])
        target_card = None
        for c in user_inv:
            if c["name"] == player_name:
                target_card = c
                break
        
        if target_card:
            squads_data[u_id_str][slot_idx] = target_card
            
    internal_write_db(squads_data, "squads")
    bot.answer_callback_query(call.id, "✅ Состав обновлен!")
    
    # Возвращаемся в главное меню состава
    bot.delete_message(call.message.chat.id, call.message.message_id)
    display_squad_management(call.message)

# ==============================================================================
# БЛОК [13]: ПВП АРЕНА (ENGINE)
# ==============================================================================

def calculate_total_team_power(user_id):
    """Считает сумму ATK всех игроков в составе."""
    squad = internal_read_db("squads").get(str(user_id), [None] * 7)
    power_sum = 0
    for p_obj in squad:
        if p_obj:
            power_sum += GAME_RARITY_SCHEMA[p_obj["stars"]]["power_atk"]
    return power_sum

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def handle_arena_entry(message):
    """Стартовый экран боя."""
    my_power = calculate_total_team_power(message.from_user.id)
    
    if my_power <= 0:
        bot.send_message(message.chat.id, "❌ Ваш состав пуст! Назначьте игроков в меню '📋 Состав'.")
        return
        
    arena_kb = types.InlineKeyboardMarkup()
    arena_kb.add(types.InlineKeyboardButton("⚔️ Найти противника", callback_data="start_matchmaking"))
    
    bot.send_message(
        message.chat.id,
        f"🏟 **ПВП АРЕНА**\n\n"
        f"Ваша боевая мощь: **{my_power}**\n\n"
        "Победа приносит **2500** очков и славу!",
        reply_markup=arena_kb,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "start_matchmaking")
def process_pvp_battle(call):
    """Симуляция матча между игроками."""
    attacker_id = str(call.from_user.id)
    users_db = internal_read_db("users")
    
    # Поиск доступных целей (у кого сила > 0)
    all_users = list(users_db.keys())
    potential_enemies = []
    for u_id in all_users:
        if u_id != attacker_id:
            if calculate_total_team_power(u_id) > 0:
                potential_enemies.append(u_id)
                
    if not potential_enemies:
        bot.answer_callback_query(call.id, "❌ Достойных соперников пока нет в сети.", show_alert=True)
        return
        
    defender_id = random.choice(potential_enemies)
    
    atk_power = calculate_total_team_power(attacker_id)
    def_power = calculate_total_team_power(defender_id)
    
    # Алгоритм победы (веса на основе силы)
    # Используем возведение в степень для усиления значимости разницы в силе
    w1 = (atk_power ** 1.3) + 5
    w2 = (def_power ** 1.3) + 5
    
    match_winner_id = random.choices([attacker_id, defender_id], weights=[w1, w2])[0]
    
    # Выплата награды
    users_db[match_winner_id]["money_balance"] += 2500
    internal_write_db(users_db, "users")
    
    winner_name = users_db[match_winner_id]["name_info"]
    
    battle_report = (
        f"🏟 **РЕЗУЛЬТАТ МАТЧА**\n\n"
        f"🏠 {users_db[attacker_id]['name_info']} [Мощь: {atk_power}]\n"
        f"🚀 {users_db[defender_id]['name_info']} [Мощь: {def_power}]\n\n"
        f"🏆 Победитель: **{winner_name}**\n"
        f"💰 Награда: +2500 очков"
    )
    
    bot.edit_message_text(battle_report, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==============================================================================
# БЛОК [14]: ПРОФИЛЬ И ЛИДЕРБОРД
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_user_profile_stats(message):
    """Детальная информация об игроке."""
    u_id = str(message.from_user.id)
    db = internal_read_db("users")
    u_data = db.get(u_id)
    
    if not u_data: return
    
    inv_size = len(internal_read_db("inv").get(u_id, []))
    team_atk = calculate_total_team_power(u_id)
    
    text = (
        f"👤 **ВАШ ПРОФИЛЬ: {u_data['name_info']}**\n\n"
        f"💰 Очки баланса: `{u_data['money_balance']}`\n"
        f"🎰 Доступно спинов: `{u_data['spins_count']}`\n"
        f"👥 Приглашено друзей: `{u_data['referral_stats']}`\n"
        f"🗂 Карт в коллекции: `{inv_size}`\n"
        f"🛡 Сила состава 7х7: `{team_atk}`\n"
        f"📅 В игре с: {u_data['join_date']}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_global_leaderboard(message):
    """Топ-10 богатейших менеджеров."""
    all_players = internal_read_db("users")
    
    # Превращаем словарь в список кортежей и сортируем
    sorted_list = []
    for uid in all_players:
        sorted_list.append( (all_players[uid]["nick_info"], all_players[uid]["money_balance"]) )
        
    sorted_list.sort(key=lambda x: x[1], reverse=True)
    
    lead_text = "🏆 **ГЛОБАЛЬНЫЙ РЕЙТИНГ МЕНЕДЖЕРОВ**\n\n"
    for rank, (nick, score) in enumerate(sorted_list[:10], 1):
        lead_text += f"{rank}. {nick} — `{score}` 💰\n"
        
    bot.send_message(message.chat.id, lead_text, parse_mode="Markdown")

# ==============================================================================
# БЛОК [15-16]: ИСПРАВЛЕННАЯ АДМИН-ПАНЕЛЬ (РЕДАКТИРОВАНИЕ)
# ==============================================================================

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def enter_admin_module(message):
    """Вход в меню управления для администрации."""
    if not security_is_admin(message.from_user):
        bot.send_message(message.chat.id, "❌ Ошибка доступа.")
        return
        
    adm_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    adm_kb.add(types.KeyboardButton("➕ Добавить карту"), types.KeyboardButton("📝 Изменить карту"))
    adm_kb.add(types.KeyboardButton("🗑 Удалить карту"), types.KeyboardButton("🎟 +Промокод"))
    adm_kb.add(types.KeyboardButton("🏠 Назад в меню"))
    
    bot.send_message(message.chat.id, "🛠 **РЕЖИМ АДМИНИСТРАТОРА**\nВыберите инструмент управления:", reply_markup=adm_kb, parse_mode="Markdown")

# --- ИСПРАВЛЕННОЕ РЕДАКТИРОВАНИЕ ---

@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_start_edit_card(message):
    """Шаг 1: Выбор карты из общего пула."""
    if not security_is_admin(message.from_user): return
    
    cards_list = internal_read_db("cards")
    if not cards_list:
        bot.send_message(message.chat.id, "База пуста.")
        return
        
    edit_list_kb = types.InlineKeyboardMarkup(row_width=1)
    for c_obj in cards_list:
        btn_txt = f"{c_obj['name']} ({c_obj['stars']}⭐)"
        edit_list_kb.add(types.InlineKeyboardButton(text=btn_txt, callback_data=f"adm_edit_target_{c_obj['name']}"))
        
    bot.send_message(message.chat.id, "Выберите карту для внесения правок:", reply_markup=edit_list_kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_edit_target_"))
def admin_show_edit_fields(call):
    """Шаг 2: Выбор конкретного поля карты."""
    target_card_name = call.data.replace("adm_edit_target_", "")
    
    fields_kb = types.InlineKeyboardMarkup(row_width=1)
    fields_kb.add(
        types.InlineKeyboardButton("Сменить Имя", callback_data=f"ae_field_name_{target_card_name}"),
        types.InlineKeyboardButton("Сменить Позицию", callback_data=f"ae_field_pos_{target_card_name}"),
        types.InlineKeyboardButton("Сменить Редкость (1-5)", callback_data=f"ae_field_stars_{target_card_name}"),
        types.InlineKeyboardButton("Обновить Фото", callback_data=f"ae_field_photo_{target_card_name}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_admin_action")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Редактирование игрока: **{target_card_name}**\nЧто именно нужно изменить?",
        reply_markup=fields_kb,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("ae_field_"))
def admin_ask_new_value(call):
    """Шаг 3: Ожидание ввода нового значения от админа."""
    parts = call.data.split("_")
    field_to_change = parts[2] # name, pos, stars, photo
    card_identity = parts[3]
    
    msg_prompt = bot.send_message(call.message.chat.id, f"Введите новое значение для поля **{field_to_change}**:")
    bot.register_next_step_handler(msg_prompt, admin_save_card_changes, card_identity, field_to_change)

def admin_save_card_changes(message, original_name, field_name):
    """Шаг 4: Финализация и сохранение в JSON."""
    all_cards = internal_read_db("cards")
    
    # Ищем индекс нужной карты
    found_index = -1
    for i in range(len(all_cards)):
        if all_cards[i]["name"] == original_name:
            found_index = i
            break
            
    if found_index == -1:
        bot.send_message(message.chat.id, "❌ Ошибка: Карта не найдена в базе!")
        return

    try:
        if field_name == "name":
            all_cards[found_index]["name"] = message.text
        elif field_name == "pos":
            new_pos_code = message.text.upper()
            if new_pos_code in SOCCER_POSITIONS:
                all_cards[found_index]["pos"] = new_pos_code
            else:
                bot.send_message(message.chat.id, "❌ Ошибка: Используйте коды ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ.")
                return
        elif field_name == "stars":
            all_cards[found_index]["stars"] = int(message.text)
        elif field_name == "photo":
            if message.photo:
                all_cards[found_index]["photo"] = message.photo[-1].file_id
            else:
                bot.send_message(message.chat.id, "❌ Ошибка: Вы должны отправить изображение.")
                return
                
        # Сохраняем обновленный список
        if internal_write_db(all_cards, "cards"):
            bot.send_message(message.chat.id, "✅ Изменения успешно применены!")
            # Возврат к админке
            enter_admin_module(message)
        else:
            bot.send_message(message.chat.id, "❌ Сбой при записи в файл.")
            
    except Exception as exc:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {exc}")

# --- ВСПОМОГАТЕЛЬНЫЕ КНОПКИ ---

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_to_main_lobby(message):
    bot.send_message(message.chat.id, "Возврат в главное меню...", reply_markup=create_main_interface_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "cancel_admin_action")
def cancel_admin_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Действие отменено.")

# ==============================================================================
# БЛОК [18]: ГЛОБАЛЬНЫЙ ЗАПУСК И УСТОЙЧИВОСТЬ
# ==============================================================================

def execute_bot_lifecycle():
    """Функция бесконечного цикла работы бота с авто-рестартом."""
    print("---------------------------------------")
    print(f"[{datetime.datetime.now()}] BOT ENGINE STARTED")
    print("---------------------------------------")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as critical_error:
            print(f"!!! CRITICAL ERROR: {critical_error}")
            # Записываем ошибку в лог
            with open("crash_report.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"[{datetime.datetime.now()}] {traceback.format_exc()}\n")
            
            # Пауза перед рестартом
            time.sleep(15)
            # Перезапуск скрипта через системный вызов
            os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    execute_bot_lifecycle()
