import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ И НАСТРОЙКИ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Пути к файлам базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json',
    'bans': 'bans.json'
}

# Характеристики редкости (Шанс, Очки за выпадение, Сила в ПВП)
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Словари для корректного отображения позиций на русском
POSITIONS_LABELS = {
    "ГК": "Вратарь",
    "ЛЗ": "Левый Защитник",
    "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник",
    "ЛВ": "Левый Вингер",
    "ПВ": "Правый Вингер",
    "КФ": "Нападающий"
}

# Данные для формирования состава (индекс кнопки : название и код)
POSITIONS_DATA = {
    0: {"label": "🧤 Вратарь (ГК)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 Нападающий (КФ)", "code": "КФ"}
}

# --- [2] ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ---
def load_db(key):
    """Загрузка данных из JSON файла."""
    if not os.path.exists(FILES[key]):
        # Если файла нет, создаем пустой список или словарь в зависимости от типа данных
        default = [] if key in ['cards', 'bans'] else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] if key in ['cards', 'bans'] else {}

def save_db(data, key):
    """Сохранение данных в JSON файл."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---
def is_admin(user):
    """Проверка, является ли пользователь администратором."""
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    """Проверка, находится ли пользователь в черном списке."""
    ban_list = load_db('bans')
    username = user.username.lower() if user.username else None
    user_id = str(user.id)
    return (username in ban_list) or (user_id in ban_list)

def get_total_power(uid):
    """Расчет общей силы состава для ПВП арены."""
    user_squads = load_db('squads')
    squad = user_squads.get(str(uid), [None] * 7)
    total_atk = 0
    for player in squad:
        if player:
            stars = player.get('stars', 1)
            total_atk += STATS[stars]['atk']
    return total_atk

# --- [4] ГЛАВНЫЕ КЛАВИАТУРЫ ---
def get_main_keyboard(uid):
    """Клавиатура главного меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    
    # Кнопка админ-панели видна только админам
    try:
        user = bot.get_chat(uid)
        if is_admin(user):
            markup.add("🛠 Админ-панель")
    except:
        pass
    return markup

def get_cancel_keyboard():
    """Клавиатура для отмены действия."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена")
    return markup

# --- [5] ОБРАБОТЧИКИ ОБЩИХ КОМАНД ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def handle_banned(m):
    bot.send_message(m.chat.id, "🚫 Ваш доступ к боту заблокирован администрацией.")

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def handle_global_cancel(m):
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, "Действие отменено. Возврат в главное меню.", reply_markup=get_main_keyboard(uid))

@bot.message_handler(commands=['start'])
def handle_start(m):
    users_data = load_db('users')
    uid = str(m.from_user.id)
    username = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    
    # Регистрация или обновление данных пользователя
    users_data[uid] = {
        "nick": m.from_user.first_name,
        "score": users_data.get(uid, {}).get('score', 0),
        "username": username
    }
    save_db(users_data, 'users')
    
    bot.send_message(m.chat.id, f"⚽️ Добро пожаловать, {m.from_user.first_name}!", reply_markup=get_main_keyboard(uid))

# --- [6] ЛОГИКА ВЫПАДЕНИЯ КАРТ (ROLL) ---
user_cooldowns = {}

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def handle_roll(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    # Кулдаун 3 часа (10800 секунд) для обычных игроков
    if not is_admin(m.from_user):
        if uid in user_cooldowns and now - user_cooldowns[uid] < 10800:
            remaining = int(10800 - (now - user_cooldowns[uid]))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return bot.send_message(m.chat.id, f"⏳ Перезарядка! Попробуйте через {hours}ч {minutes}м.")

    all_cards = load_db('cards')
    if not all_cards:
        return bot.send_message(m.chat.id, "❌ В игре пока нет доступных карт. Ждите обновлений от админов!")

    # Выбор редкости на основе шансов
    weights = [STATS[s]['chance'] for s in STATS.keys()]
    selected_stars = random.choices(list(STATS.keys()), weights=weights)[0]
    
    # Фильтруем карты по выбранной редкости
    possible_cards = [c for c in all_cards if c['stars'] == selected_stars]
    if not possible_cards:
        possible_cards = all_cards # Если карт такой редкости нет, берем любую
    
    won_card = random.choice(possible_cards)
    user_cooldowns[uid] = now
    
    # Обновление коллекции и очков
    user_collections = load_db('colls')
    users_stats = load_db('users')
    
    if uid not in user_collections:
        user_collections[uid] = []
        
    is_duplicate = any(card['name'] == won_card['name'] for card in user_collections[uid])
    
    # Очки: за повторку даем 30%
    reward_points = int(STATS[won_card['stars']]['score'] * (0.3 if is_duplicate else 1))
    
    if not is_duplicate:
        user_collections[uid].append(won_card)
        save_db(user_collections, 'colls')

    users_stats[uid]['score'] = users_stats.get(uid, {}).get('score', 0) + reward_points
    save_db(users_stats, 'users')

    # Формирование сообщения
    status_text = "✨ НОВАЯ КАРТА!" if not is_duplicate else "♻️ ПОВТОРКА"
    position_name = POSITIONS_LABELS.get(won_card['pos'].upper(), won_card['pos'])
    
    caption = (
        f"🏆 **{won_card['name']}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"ℹ️ Статус: {status_text}\n"
        f"🎯 Позиция: {position_name}\n"
        f"⭐️ Редкость: {'⭐' * won_card['stars']}\n"
        f"💠 Очки: +{reward_points:,}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 Ваш баланс: {users_stats[uid]['score']:,} очков"
    )
    
    bot.send_photo(m.chat.id, won_card['photo'], caption=caption, parse_mode="Markdown")

# --- [7] ПРОФИЛЬ И ТОП-10 ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def handle_profile(m):
    users_data = load_db('users')
    user_collections = load_db('colls')
    uid = str(m.from_user.id)
    
    # Обновляем юзернейм при каждом просмотре профиля
    current_username = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    if uid not in users_data:
        users_data[uid] = {"nick": m.from_user.first_name, "score": 0, "username": current_username}
    else:
        users_data[uid]["username"] = current_username
    save_db(users_data, 'users')

    user = users_data[uid]
    collection_count = len(user_collections.get(uid, []))
    power = get_total_power(uid)
    
    profile_text = (
        f"👤 **ВАШ ИГРОВОЙ ПРОФИЛЬ**\n\n"
        f"📝 Имя: {user['nick']}\n"
        f"🔗 Юзернейм: {user['username']}\n"
        f"💠 Очки: `{user['score']:,}`\n"
        f"🗂 Коллекция: {collection_count} шт.\n"
        f"🛡 Сила состава: {power}"
    )
    bot.send_message(m.chat.id, profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def handle_top(m):
    users_data = load_db('users')
    # Сортировка по очкам (топ 10)
    sorted_users = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    top_text = "🏆 **ТОП-10 ЛУЧШИХ ИГРОКОВ:**\n\n"
    for index, (uid, data) in enumerate(sorted_users, 1):
        name = data.get('username', f"id{uid}")
        top_text += f"{index}. {name} — `{data['score']:,}` очков\n"
    
    bot.send_message(m.chat.id, top_text, parse_mode="Markdown")

# --- [8] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def handle_pvp_menu(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Случайный противник", callback_data="pvp_random"))
    markup.add(types.InlineKeyboardButton("🔍 Найти по @username", callback_data="pvp_search"))
    bot.send_message(m.chat.id, "🏟 **ДОБРО ПОЖАЛОВАТЬ НА АРЕНУ**\n\nЗдесь побеждает тот, чей состав сильнее. Победитель получает +1,000 очков!", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "pvp_search")
def pvp_callback_search(call):
    msg = bot.send_message(call.message.chat.id, "Введите @username игрока, которого хотите вызвать на бой (или нажмите /cancel):")
    bot.register_next_step_handler(msg, pvp_step_search_execute)

def pvp_step_search_execute(m):
    if m.text == "/cancel" or m.text == "❌ Отмена":
        return handle_global_cancel(m)
        
    target_username = m.text.replace("@", "").lower().strip()
    users_data = load_db('users')
    
    found_id = None
    for uid, data in users_data.items():
        if data.get('username', '').replace("@", "").lower() == target_username:
            found_id = uid
            break
            
    if found_id:
        process_pvp_battle(m.chat.id, str(m.from_user.id), found_id)
    else:
        bot.send_message(m.chat.id, "❌ Игрок с таким юзернеймом не найден в базе данных.")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_random")
def pvp_callback_random(call):
    users_data = load_db('users')
    my_id = str(call.from_user.id)
    
    # Ищем игроков, у которых есть хоть кто-то в составе
    possible_opponents = [uid for uid in users_data if uid != my_id and get_total_power(uid) > 0]
    
    if not possible_opponents:
        return bot.answer_callback_query(call.id, "❌ Противников пока нет. Попробуйте позже!", show_alert=True)
    
    opponent_id = random.choice(possible_opponents)
    process_pvp_battle(call.message.chat.id, my_id, opponent_id)

def process_pvp_battle(chat_id, player1_id, player2_id):
    users_data = load_db('users')
    p1_power = get_total_power(player1_id)
    p2_power = get_total_power(player2_id)
    
    if p1_power == 0:
        return bot.send_message(chat_id, "❌ У вас пустой состав! Соберите команду в меню '📋 Состав'.")

    # Вероятность победы зависит от силы
    total_chance = p1_power + p2_power
    winner_id = random.choices([player1_id, player2_id], weights=[p1_power, p2_power])[0]
    
    # Награда победителю
    users_data[winner_id]['score'] += 1000
    save_db(users_data, 'users')
    
    p1_name = users_data[player1_id].get('username', 'Игрок 1')
    p2_name = users_data[player2_id].get('username', 'Игрок 2')
    
    result_text = (
        f"🏟 **РЕЗУЛЬТАТ БОЯ:**\n\n"
        f"👤 {p1_name} (Сила: {p1_power})\n"
        f"       🆚\n"
        f"👤 {p2_name} (Сила: {p2_power})\n\n"
        f"🏆 **ПОБЕДИТЕЛЬ:** {users_data[winner_id].get('username')}! (+1,000 очков)"
    )
    bot.send_message(chat_id, result_text, parse_mode="Markdown")

# --- [9] ПОЛНАЯ АДМИН-ПАНЕЛЬ С ОТМЕНОЙ И ПОДТВЕРЖДЕНИЕМ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def handle_admin_menu(m):
    if not is_admin(m.from_user): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "📝 Изменить карту")
    markup.row("🗑 Удалить карту", "🧨 Обнулить бота")
    markup.row("🚫 Забанить", "✅ Разбанить")
    markup.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **ПАНЕЛЬ АДМИНИСТРАТОРА:**", reply_markup=markup)

# --- АДМИН: ДОБАВЛЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_step1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите ФИО или имя игрока:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(m, admin_add_step2)

def admin_add_step2(m):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    player_name = m.text
    bot.send_message(m.chat.id, "Введите позицию (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(m, admin_add_step3, player_name)

def admin_add_step3(m, name):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    position = m.text.upper().strip()
    bot.send_message(m.chat.id, "Введите редкость (число звезд от 1 до 5):", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(m, admin_add_step4, name, position)

def admin_add_step4(m, name, pos):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    try:
        stars = int(m.text)
        if not (1 <= stars <= 5): raise ValueError
        bot.send_message(m.chat.id, "Теперь отправьте ФОТОГРАФИЮ карты игрока:", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(m, admin_add_final, name, pos, stars)
    except ValueError:
        bot.send_message(m.chat.id, "❌ Ошибка! Нужно ввести число от 1 до 5. Попробуйте снова:")
        bot.register_next_step_handler(m, admin_add_step4, name, pos)

def admin_add_final(m, name, pos, stars):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    if not m.photo:
        bot.send_message(m.chat.id, "❌ Это не фотография. Пожалуйста, отправьте фото:")
        bot.register_next_step_handler(m, admin_add_final, name, pos, stars)
        return

    cards_db = load_db('cards')
    cards_db.append({
        "name": name,
        "pos": pos,
        "stars": stars,
        "photo": m.photo[-1].file_id
    })
    save_db(cards_db, 'cards')
    
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, f"✅ Карта '{name}' успешно добавлена в игру!", reply_markup=get_main_keyboard(uid))

# --- АДМИН: УДАЛЕНИЕ КАРТЫ (ИСПРАВЛЕНО) ---
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_list(m):
    if not is_admin(m.from_user): return
    cards_db = load_db('cards')
    if not cards_db:
        return bot.send_message(m.chat.id, "❌ Список карт пуст.")

    markup = types.InlineKeyboardMarkup()
    for card in cards_db:
        markup.add(types.InlineKeyboardButton(f"❌ Удалить {card['name']} ({card['stars']}⭐)", callback_data=f"adm_del_{card['name']}"))
    
    bot.send_message(m.chat.id, "Выберите карту, которую хотите навсегда удалить из игры:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_"))
def admin_delete_execute(call):
    card_name = call.data.replace("adm_del_", "")
    cards_db = load_db('cards')
    
    # Фильтруем список, исключая удаляемую карту
    updated_cards = [c for c in cards_db if c['name'] != card_name]
    save_db(updated_cards, 'cards')
    
    bot.answer_callback_query(call.id, f"Карта {card_name} удалена")
    bot.edit_message_text(f"✅ Карта **{card_name}** была успешно удалена из системы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- АДМИН: ИЗМЕНЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_list(m):
    if not is_admin(m.from_user): return
    cards_db = load_db('cards')
    if not cards_db: return bot.send_message(m.chat.id, "Карт нет.")

    markup = types.InlineKeyboardMarkup()
    for card in cards_db:
        markup.add(types.InlineKeyboardButton(f"📝 {card['name']}", callback_data=f"adm_ed_sel_{card['name']}"))
    bot.send_message(m.chat.id, "Какую карту вы хотите отредактировать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ed_sel_"))
def admin_edit_input(call):
    card_name = call.data.replace("adm_ed_sel_", "")
    bot.send_message(call.message.chat.id, f"Вы редактируете: {card_name}\n\nВведите новые данные в формате:\n`Новое Имя, Позиция, Звезды` (через запятую)", parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(call.message, admin_edit_save, card_name)

def admin_edit_save(m, old_name):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    try:
        cards_db = load_db('cards')
        data_parts = m.text.split(",")
        new_name = data_parts[0].strip()
        new_pos = data_parts[1].strip().upper()
        new_stars = int(data_parts[2].strip())
        
        for card in cards_db:
            if card['name'] == old_name:
                card['name'], card['pos'], card['stars'] = new_name, new_pos, new_stars
                break
        save_db(cards_db, 'cards')
        
        uid = str(m.from_user.id)
        bot.send_message(m.chat.id, f"✅ Данные карты {new_name} успешно обновлены!", reply_markup=get_main_keyboard(uid))
    except:
        bot.send_message(m.chat.id, "❌ Ошибка формата! Введите: Имя, Позиция, Звезды")
        bot.register_next_step_handler(m, admin_edit_save, old_name)

# --- АДМИН: ОБНУЛЕНИЕ (С ПОДТВЕРЖДЕНИЕМ) ---
@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_nuke_confirmation(m):
    if not is_admin(m.from_user): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✅ ДА, ПОЛНОЕ ОБНУЛЕНИЕ", "❌ НЕТ, Я ПЕРЕДУМАЛ")
    bot.send_message(m.chat.id, "🚨 **ВНИМАНИЕ!**\n\nЭто действие удалит ВСЕ очки, коллекции и составы у всех игроков. Это нельзя отменить. Вы уверены?", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ ДА, ПОЛНОЕ ОБНУЛЕНИЕ")
def admin_nuke_execute(m):
    if not is_admin(m.from_user): return
    
    users_db = load_db('users')
    for uid in users_db:
        users_db[uid]['score'] = 0
    save_db(users_db, 'users')
    save_db({}, 'colls')
    save_db({}, 'squads')
    
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, "🧨 База данных успешно очищена. Все игроки обнулены.", reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "❌ НЕТ, Я ПЕРЕДУМАЛ")
def admin_nuke_cancel(m):
    handle_global_cancel(m)

# --- АДМИН: БАН / РАЗБАН ---
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_step1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите @username или ID игрока для блокировки:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(m, admin_ban_execute)

def admin_ban_execute(m):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    bans.append(target)
    save_db(bans, 'bans')
    bot.send_message(m.chat.id, f"✅ Игрок '{target}' добавлен в черный список.", reply_markup=get_main_keyboard(str(m.from_user.id)))

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_step1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите @username или ID для разблокировки:", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(m, admin_unban_execute)

def admin_unban_execute(m):
    if m.text == "❌ Отмена": return handle_global_cancel(m)
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    if target in bans:
        updated_bans = [b for b in bans if b != target]
        save_db(updated_bans, 'bans')
        bot.send_message(m.chat.id, f"✅ Игрок '{target}' разблокирован.", reply_markup=get_main_keyboard(str(m.from_user.id)))
    else:
        bot.send_message(m.chat.id, "❌ Данный игрок не найден в списке забаненных.")

# --- [10] ПРОСМОТР КОЛЛЕКЦИИ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def handle_collection_menu(m):
    markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(f"{'⭐' * i} Показать категорию", callback_data=f"view_coll_{i}"))
    bot.send_message(m.chat.id, "🗂 **ВАША КОЛЛЕКЦИЯ КАРТ**\n\nВыберите редкость для просмотра:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_coll_"))
def callback_collection_list(call):
    stars = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    all_colls = load_db('colls')
    
    my_cards = [c for c in all_colls.get(uid, []) if c['stars'] == stars]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас нет карт такой редкости!", show_alert=True)
    
    text = f"🗂 **ВАШИ КАРТЫ {stars}⭐:**\n\n"
    for card in my_cards:
        text += f"• {card['name']} ({card['pos']})\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# --- [11] УПРАВЛЕНИЕ СОСТАВОМ (ПОЛНАЯ ЛОГИКА) ---
@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def handle_squad_menu(m):
    bot.send_message(m.chat.id, "📋 **ВАШ ТЕКУЩИЙ СОСТАВ:**\n\nНажмите на позицию, чтобы выбрать игрока из коллекции.", reply_markup=get_squad_markup(m.from_user.id))

def get_squad_markup(uid):
    user_squads = load_db('squads')
    squad = user_squads.get(str(uid), [None] * 7)
    markup = types.InlineKeyboardMarkup()
    
    for i in range(7):
        player = squad[i]
        pos_info = POSITIONS_DATA[i]
        button_text = f"{pos_info['label']}: {player['name'] if player else '❌ Не выбран'}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"squad_idx_{i}"))
    return markup

@bot.callback_query_handler(func=lambda c: c.data.startswith("squad_idx_"))
def callback_squad_select_player(call):
    index = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    pos_code = POSITIONS_DATA[index]["code"]
    
    user_colls = load_db('colls')
    # Ищем все карты игрока, которые подходят на эту позицию
    available_players = [c for c in user_colls.get(uid, []) if c['pos'].upper() == pos_code.upper()]
    
    markup = types.InlineKeyboardMarkup()
    for player in available_players:
        markup.add(types.InlineKeyboardButton(f"{player['name']} ({player['stars']}⭐)", callback_data=f"squad_set_{index}_{player['name']}"))
    
    markup.add(types.InlineKeyboardButton("🚫 Очистить позицию", callback_data=f"squad_set_{index}_none"))
    
    bot.edit_message_text(f"Выберите игрока на позицию {pos_code}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("squad_set_"))
def callback_squad_apply_change(call):
    parts = call.data.split("_")
    index = int(parts[2])
    player_name = parts[3]
    uid = str(call.from_user.id)
    
    user_squads = load_db('squads')
    user_colls = load_db('colls')
    
    if uid not in user_squads:
        user_squads[uid] = [None] * 7
        
    if player_name == "none":
        user_squads[uid][index] = None
    else:
        # Находим полную инфу о карте в коллекции
        card_data = next((c for c in user_colls.get(uid, []) if c['name'] == player_name), None)
        user_squads[uid][index] = card_data
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_markup(uid))

# --- [12] КНОПКА ВОЗВРАТА ---
@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def handle_back_home(m):
    bot.send_message(m.chat.id, "⚽️ Вы вернулись в главное меню.", reply_markup=get_main_keyboard(str(m.from_user.id)))

# --- ЗАПУСК ---
if __name__ == "__main__":
    print(">>> Бот запущен и готов к работе! (Версия: Полная / RU)")
    bot.infinity_polling()
