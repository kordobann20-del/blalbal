import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] НАСТРОЙКИ ---
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

# ШАНСЫ НА ВЫПАДЕНИЕ КАРТ (Твои любимые настройки)
RARITY_STATS = {
    1: {"chance": 30, "score": 1000, "atk": 100},   # Обычные
    2: {"chance": 30, "score": 3000, "atk": 450},   # Необычные
    3: {"chance": 25, "score": 7500, "atk": 1000},  # Редкие
    4: {"chance": 10, "score": 15000, "atk": 2500}, # Эпические
    5: {"chance": 5,  "score": 30000, "atk": 5000}  # Легендарные
}

# Названия позиций
POSITIONS_RU = {
    "ГК": "Вратарь", "ЛЗ": "Левый Защитник", "ПЗ": "Правый Защитник",
    "ЦП": "Центральный Полузащитник", "ЛВ": "Левый Вингер", "ПВ": "Правый Вингер", "КФ": "Нападающий"
}

# Схемы состава
SQUAD_SLOTS = {
    0: {"label": "🧤 ГК (Вратарь)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ (Защитник)", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ (Защитник)", "code": "ПЗ"},
    3: {"label": "👟 ЦП (Полузащитник)", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ (Вингер)", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ (Вингер)", "code": "ПВ"},
    6: {"label": "🎯 КФ (Нападающий)", "code": "КФ"}
}

# Словари для КД (в оперативной памяти)
roll_cooldowns = {}
pvp_cooldowns = {}

# --- [2] РАБОТА С БАЗОЙ ДАННЫХ ---
def load_data(key):
    """Загрузка данных из JSON файла"""
    if not os.path.exists(DB_FILES[key]):
        default = [] if key in ['cards', 'bans'] else {}
        with open(DB_FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(DB_FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key in ['cards', 'bans'] else {}

def save_data(data, key):
    """Сохранение данных в JSON файл"""
    with open(DB_FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---
def is_admin(user):
    """Проверка на права администратора"""
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    """Проверка, забанен ли пользователь"""
    bl = load_data('bans')
    uid = str(user.id)
    un = user.username.lower() if user.username else ""
    return (un in bl) or (uid in bl)

def get_team_power(uid):
    """Расчет общей силы состава игрока"""
    sq = load_data('squads').get(str(uid), [None]*7)
    power = 0
    for p in sq:
        if p:
            power += RARITY_STATS[p['stars']]['atk']
    return power

# --- [4] КЛАВИАТУРЫ ---
def main_kb(uid):
    """Главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    markup.row("🎟 Промокод", "👥 Рефералы")
    try:
        # Проверка админа для отображения кнопки
        user_info = bot.get_chat(uid)
        if is_admin(user_info):
            markup.add("🛠 Админ-панель")
    except:
        pass
    return markup

def cancel_kb():
    """Клавиатура отмены действия"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена")
    return markup

def admin_kb():
    """Меню администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "🗑 Удалить карту")
    markup.row("🎟 +Промокод", "🧨 Обнулить бота")
    markup.row("🚫 Забанить игрока", "✅ Разбанить игрока")
    markup.row("🏠 Назад в меню")
    return markup

# --- [5] СТАРТ И РЕФЕРАЛЬНАЯ СИСТЕМА ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    if is_banned(m.from_user):
        return bot.send_message(m.chat.id, "🚫 Вы забанены и не можете использовать бота.")
    
    u_db = load_data('users')
    uid = str(m.from_user.id)
    
    # Реферальная логика
    ref_id = None
    args = m.text.split()
    if len(args) > 1:
        ref_id = args[1]

    if uid not in u_db:
        uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
        u_db[uid] = {
            "nick": m.from_user.first_name, 
            "score": 0, 
            "username": uname, 
            "used_promos": [],
            "bonus_luck": 1.0,
            "referals_count": 0
        }
        # Награда пригласившему
        if ref_id and ref_id in u_db and ref_id != uid:
            u_db[ref_id]["score"] += 5000
            u_db[ref_id]["referals_count"] += 1
            bot.send_message(int(ref_id), "👥 По вашей ссылке зашел новый игрок! Вам начислено 5,000 очков.")

    save_data(u_db, 'users')
    bot.send_message(m.chat.id, f"⚽️ Привет, {m.from_user.first_name}! Это футбольный бот.\n\nКрути карты, собирай состав и сражайся на арене!", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def referals_view(m):
    if is_banned(m.from_user): return
    uid = m.from_user.id
    u_db = load_data('users')
    bot_name = bot.get_me().username
    ref_link = f"https://t.me/{bot_name}?start={uid}"
    
    count = u_db.get(str(uid), {}).get("referals_count", 0)
    
    msg = (f"👥 **РЕФЕРАЛЬНАЯ ПРОГРАММА**\n\n"
           f"Приглашайте друзей и получайте бонусы!\n"
           f"За каждого друга: **5,000 очков**.\n\n"
           f"Вы пригласили: **{count}** чел.\n\n"
           f"Ваша ссылка для приглашения:\n`{ref_link}`")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

# --- [6] ПРОМОКОДЫ ---
@bot.message_handler(func=lambda m: m.text == "🎟 Промокод")
def promo_entry(m):
    if is_banned(m.from_user): return
    bot.send_message(m.chat.id, "🎟 Введите промокод:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, promo_process)

def promo_process(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    
    code = m.text.strip().upper()
    uid = str(m.from_user.id)
    u_db = load_data('users')
    p_db = load_data('promos')
    
    if code not in p_db:
        return bot.send_message(m.chat.id, "❌ Такого промокода не существует.", reply_markup=main_kb(uid))
    
    if code in u_db[uid].get('used_promos', []):
        return bot.send_message(m.chat.id, "❌ Вы уже вводили этот промокод!", reply_markup=main_kb(uid))
    
    promo_data = p_db[code]
    if promo_data['type'] == 'points':
        u_db[uid]['score'] += int(promo_data['value'])
        res_msg = f"✅ Промокод активирован! Вы получили **{promo_data['value']}** очков."
    else:
        u_db[uid]['bonus_luck'] = float(promo_data['value'])
        res_msg = f"✅ Промокод активирован! Ваша удача увеличена в **{promo_data['value']} раз** на следующую крутку!"
    
    u_db[uid].setdefault('used_promos', []).append(code)
    save_data(u_db, 'users')
    bot.send_message(m.chat.id, res_msg, reply_markup=main_kb(uid), parse_mode="Markdown")

# --- [7] КРУТКА КАРТ (ROLL) ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_handler(m):
    if is_banned(m.from_user): return
    uid = str(m.from_user.id)
    u_db = load_data('users')
    now = time.time()
    
    # КД 3 часа для обычных игроков
    if not is_admin(m.from_user):
        if uid in roll_cooldowns and now - roll_cooldowns[uid] < 10800:
            rem = int(10800 - (now - roll_cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Кулдаун! Попробуйте через {rem//3600}ч {(rem%3600)//60}м")

    cards = load_data('cards')
    if not cards:
        return bot.send_message(m.chat.id, "❌ В магазине пока нет доступных карт.")

    # Рассчет шансов с учетом множителя промокода
    luck_multiplier = u_db[uid].get('bonus_luck', 1.0)
    weights = []
    for star in sorted(RARITY_STATS.keys()):
        base_chance = RARITY_STATS[star]['chance']
        if star >= 4: # Бонус только для редких (4 и 5 звезд)
            base_chance *= luck_multiplier
        weights.append(base_chance)

    selected_rarity = random.choices(list(sorted(RARITY_STATS.keys())), weights=weights)[0]
    pool = [c for c in cards if c['stars'] == selected_rarity]
    
    if not pool: # На случай если админ не добавил карты какой-то редкости
        pool = cards
        
    won_card = random.choice(pool)
    
    # Сброс КД и бонуса удачи
    roll_cooldowns[uid] = now
    u_db[uid]['bonus_luck'] = 1.0

    colls = load_data('colls')
    if uid not in colls: colls[uid] = []
    
    # Проверка на дубликат
    is_duplicate = any(c['name'] == won_card['name'] for c in colls[uid])
    
    if is_duplicate:
        points_gain = int(RARITY_STATS[won_card['stars']]['score'] * 0.3)
        status_text = "🔄 Повторка (Получено 30% стоимости)"
    else:
        points_gain = RARITY_STATS[won_card['stars']]['score']
        status_text = "✨ Новая карта в коллекцию!"
        colls[uid].append(won_card)
        save_data(colls, 'colls')

    u_db[uid]['score'] += points_gain
    save_data(u_db, 'users')

    stars_str = "⭐️" * won_card['stars']
    pos_full = POSITIONS_RU.get(won_card['pos'].upper(), won_card['pos'])
    
    caption = (
        f"⚽️ **{won_card['name']}**\n\n"
        f"📊 Рейтинг: {stars_str}\n"
        f"🎯 Позиция: {pos_full}\n\n"
        f"💠 {status_text}\n"
        f"💰 Очки: +{points_gain:,}\n"
        f"📈 Ваш баланс: {u_db[uid]['score']:,}"
    )
    bot.send_photo(m.chat.id, won_card['photo'], caption=caption, parse_mode="Markdown")

# --- [8] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def pvp_menu(m):
    if is_banned(m.from_user): return
    uid = str(m.from_user.id)
    now = time.time()
    
    if not is_admin(m.from_user):
        if uid in pvp_cooldowns and now - pvp_cooldowns[uid] < 900:
            rem = int(900 - (now - pvp_cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Ваши футболисты отдыхают. Ждите {rem//60} мин.")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Случайный матч", callback_data="pvp_random"))
    kb.add(types.InlineKeyboardButton("🔍 Найти по нику", callback_data="pvp_search"))
    bot.send_message(m.chat.id, "🏟 **ПВП АРЕНА**\n\nСоберите состав из 7 игроков в меню '📋 Состав' и докажите, кто лучший!", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "pvp_search")
def pvp_search_start(call):
    bot.send_message(call.message.chat.id, "Введите @username соперника:")
    bot.register_next_step_handler(call.message, pvp_search_finish)

def pvp_search_finish(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    target_un = m.text.replace("@", "").lower().strip()
    u_db = load_data('users')
    
    target_id = None
    for uid, data in u_db.items():
        if data.get('username', '').replace("@", "").lower() == target_un:
            target_id = uid
            break
            
    if target_id:
        run_battle_logic(m.chat.id, str(m.from_user.id), target_id)
    else:
        bot.send_message(m.chat.id, "❌ Игрок не найден в нашей базе.")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_random")
def pvp_random_start(call):
    u_db = load_data('users')
    my_id = str(call.from_user.id)
    # Ищем тех, у кого сила больше 0
    opponents = [uid for uid in u_db if uid != my_id and get_team_power(uid) > 0]
    
    if not opponents:
        return bot.answer_callback_query(call.id, "Соперников пока нет. Все тренируются!", show_alert=True)
        
    enemy_id = random.choice(opponents)
    run_battle_logic(call.message.chat.id, my_id, enemy_id)

def run_battle_logic(chat_id, p1_id, p2_id):
    u_db = load_data('users')
    p1_power = get_team_power(p1_id)
    p2_power = get_team_power(p2_id)
    
    if p1_power == 0:
        return bot.send_message(chat_id, "❌ Ваш состав пуст! Вы не можете играть в ПВП.")

    # Логика шансов: сила возводится в степень для большего разрыва, но шанс есть у каждого
    weight1 = p1_power ** 1.2
    weight2 = p2_power ** 1.2
    
    winner_id = random.choices([p1_id, p2_id], weights=[weight1, weight2])[0]
    
    # Награда победителю
    u_db[winner_id]['score'] += 1000
    save_data(u_db, 'users')
    
    # КД только инициатору
    p1_info = bot.get_chat(int(p1_id))
    if not is_admin(p1_info):
        pvp_cooldowns[p1_id] = time.time()

    battle_msg = (f"🏟 **МАТЧ ОКОНЧЕН**\n\n"
                  f"🛡 {u_db[p1_id]['nick']} (Сила: {p1_power})\n"
                  f"       **VS**\n"
                  f"🛡 {u_db[p2_id]['nick']} (Сила: {p2_power})\n\n"
                  f"🏆 Победитель: **{u_db[winner_id]['username']}**\n"
                  f"💰 Приз: +1,000 очков")
    bot.send_message(chat_id, battle_msg)

# --- [9] ПРОФИЛЬ, ТОП И КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_view(m):
    if is_banned(m.from_user): return
    uid = str(m.from_user.id)
    u_db = load_data('users')
    colls = load_data('colls')
    
    user = u_db[uid]
    msg = (f"👤 **ВАШ ПРОФИЛЬ**\n\n"
           f"📝 Имя: {user['nick']}\n"
           f"🔗 Юзер: {user['username']}\n"
           f"💠 Очки: `{user['score']:,}`\n"
           f"🗂 Коллекция: {len(colls.get(uid, []))} шт.\n"
           f"🛡 Сила команды: {get_team_power(uid)}")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_view(m):
    if is_banned(m.from_user): return
    u_db = load_data('users')
    top_list = sorted(u_db.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    text = "🏆 **ТОП-10 ИГРОКОВ ПО ОЧКАМ:**\n\n"
    for i, (uid, data) in enumerate(top_list, 1):
        text += f"{i}. {data['username']} — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def collection_view(m):
    if is_banned(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(f"{'⭐️'*i} Просмотр", callback_data=f"show_stars_{i}"))
    bot.send_message(m.chat.id, "🗂 **ВАША КОЛЛЕКЦИЯ**\nВыберите редкость:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("show_stars_"))
def collection_stars_list(call):
    stars = int(call.data.split("_")[-1])
    uid = str(call.from_user.id)
    my_cards = [c for c in load_data('colls').get(uid, []) if c['stars'] == stars]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас нет карт этой редкости!", show_alert=True)
    
    text = f"🗂 **КАРТЫ {stars}⭐️:**\n\n"
    for c in my_cards:
        text += f"• {c['name']} ({c['pos']})\n"
    bot.send_message(call.message.chat.id, text)

# --- [10] УПРАВЛЕНИЕ СОСТАВОМ ---
@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    if is_banned(m.from_user): return
    bot.send_message(m.chat.id, "📋 **ВАШ ТЕКУЩИЙ СОСТАВ:**\nНажмите на кнопку, чтобы изменить игрока.", reply_markup=get_squad_markup(m.from_user.id))

def get_squad_markup(uid):
    squad = load_data('squads').get(str(uid), [None]*7)
    markup = types.InlineKeyboardMarkup()
    for i in range(7):
        player = squad[i]
        label = SQUAD_SLOTS[i]["label"]
        btn_text = f"{label}: {player['name'] if player else '❌ Пусто'}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"edit_slot_{i}"))
    return markup

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_slot_"))
def squad_edit_slot(call):
    slot_idx = int(call.data.split("_")[-1])
    uid = str(call.from_user.id)
    pos_needed = SQUAD_SLOTS[slot_idx]["code"]
    
    # Фильтруем коллекцию игрока по нужной позиции
    my_col = load_data('colls').get(uid, [])
    options = [c for c in my_col if c['pos'].upper() == pos_needed]
    
    kb = types.InlineKeyboardMarkup()
    for card in options:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_p_{slot_idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"set_p_{slot_idx}_none"))
    
    bot.edit_message_text(f"Выберите игрока на позицию {pos_needed}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_p_"))
def squad_set_player(call):
    params = call.data.split("_")
    slot_idx = int(params[2])
    player_name = params[3]
    uid = str(call.from_user.id)
    
    s_db = load_data('squads')
    if uid not in s_db: s_db[uid] = [None]*7
    
    if player_name == "none":
        s_db[uid][slot_idx] = None
    else:
        # Ищем карту в коллекции
        c_db = load_data('colls').get(uid, [])
        found_card = next((c for c in c_db if c['name'] == player_name), None)
        s_db[uid][slot_idx] = found_card
        
    save_data(s_db, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_markup(uid))

# --- [11] АДМИН-ПАНЕЛЬ: КАРТЫ И ПРОМО ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel_view(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "🛠 **ПАНЕЛЬ УПРАВЛЕНИЯ**", reply_markup=admin_kb())

# Создание промокода
@bot.message_handler(func=lambda m: m.text == "🎟 +Промокод")
def admin_add_promo_1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Напишите НАЗВАНИЕ промокода (например: FREE2026):", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_add_promo_2)

def admin_add_promo_2(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    p_name = m.text.strip().upper()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Прокруты (Очки)", callback_data=f"ap_type_{p_name}_points"))
    kb.add(types.InlineKeyboardButton("🍀 Шансы (Удача)", callback_data=f"ap_type_{p_name}_luck"))
    bot.send_message(m.chat.id, f"Какую награду даст `{p_name}`?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_type_"))
def admin_add_promo_3(call):
    data = call.data.split("_")
    p_name = data[2]; p_type = data[3]
    
    prompt = "Введите количество ОЧКОВ:" if p_type == "points" else "Введите множитель ШАНСА (от 1.1 до 5.0):"
    bot.send_message(call.message.chat.id, prompt)
    bot.register_next_step_handler(call.message, admin_add_promo_fin, p_name, p_type)

def admin_add_promo_fin(m, p_name, p_type):
    try:
        val = float(m.text)
        if p_type == "luck" and (val < 1 or val > 5):
            return bot.send_message(m.chat.id, "❌ Множитель удачи должен быть в пределах от 1 до 5!")
        
        p_db = load_data('promos')
        p_db[p_name] = {"type": p_type, "value": val}
        save_data(p_db, 'promos')
        bot.send_message(m.chat.id, f"✅ Промокод `{p_name}` успешно создан!", reply_markup=admin_kb())
    except:
        bot.send_message(m.chat.id, "❌ Ошибка! Введите числовое значение.")

# Добавление карты
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_card_1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите имя футболиста:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_add_card_2)

def admin_add_card_2(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    c_name = m.text
    bot.send_message(m.chat.id, "Позиция (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_add_card_3, c_name)

def admin_add_card_3(m, c_name):
    if m.text == "❌ Отмена": return global_cancel(m)
    c_pos = m.text.upper()
    bot.send_message(m.chat.id, "Редкость (1-5 звезд):", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_add_card_4, c_name, c_pos)

def admin_add_card_4(m, c_name, c_pos):
    if m.text == "❌ Отмена": return global_cancel(m)
    try:
        c_stars = int(m.text)
        bot.send_message(m.chat.id, "Пришлите ФОТО карты:", reply_markup=cancel_kb())
        bot.register_next_step_handler(m, admin_add_card_fin, c_name, c_pos, c_stars)
    except:
        bot.send_message(m.chat.id, "Введите число!")

def admin_add_card_fin(m, c_name, c_pos, c_stars):
    if m.text == "❌ Отмена": return global_cancel(m)
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Нужно прислать именно фото. Начните сначала.")
    
    db = load_data('cards')
    db.append({
        "name": c_name, 
        "pos": c_pos, 
        "stars": c_stars, 
        "photo": m.photo[-1].file_id
    })
    save_data(db, 'cards')
    bot.send_message(m.chat.id, f"✅ Игрок {c_name} успешно добавлен!", reply_markup=admin_kb())

# Удаление карты
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_card_list(m):
    if not is_admin(m.from_user): return
    db = load_data('cards')
    if not db: return bot.send_message(m.chat.id, "Список пуст.")
    
    kb = types.InlineKeyboardMarkup()
    for card in db:
        kb.add(types.InlineKeyboardButton(f"❌ {card['name']}", callback_data=f"adm_del_{card['name']}"))
    bot.send_message(m.chat.id, "Выберите карту для удаления:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_"))
def admin_delete_card_exec(call):
    name = call.data.replace("adm_del_", "")
    db = load_data('cards')
    new_db = [c for c in db if c['name'] != name]
    save_data(new_db, 'cards')
    bot.edit_message_text(f"✅ Карта `{name}` удалена из базы.", call.message.chat.id, call.message.message_id)

# Обнуление
@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_ask(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True).row("🚨 ДА, УДАЛИТЬ ВСЁ", "❌ НЕТ")
    bot.send_message(m.chat.id, "⚠️ **ВНИМАНИЕ!** Это действие удалит прогресс, коллекции и составы ВСЕХ игроков. Продолжить?", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚨 ДА, УДАЛИТЬ ВСЁ")
def admin_reset_confirm(m):
    if not is_admin(m.from_user): return
    save_data({}, 'users')
    save_data({}, 'colls')
    save_data({}, 'squads')
    bot.send_message(m.chat.id, "🧨 База данных полностью очищена.", reply_markup=admin_kb())

# --- [12] БАН-СИСТЕМА ---
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить игрока")
def admin_ban_1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите @username или ID игрока для бана:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_ban_2)

def admin_ban_2(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    target = m.text.replace("@", "").lower().strip()
    bl = load_data('bans')
    bl.append(target)
    save_data(bl, 'bans')
    bot.send_message(m.chat.id, f"✅ Игрок `{target}` заблокирован.", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить игрока")
def admin_unban_1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите ник или ID для разбана:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, admin_unban_2)

def admin_unban_2(m):
    if m.text == "❌ Отмена": return global_cancel(m)
    target = m.text.replace("@", "").lower().strip()
    bl = load_data('bans')
    if target in bl:
        bl.remove(target)
        save_data(bl, 'bans')
        bot.send_message(m.chat.id, f"✅ Игрок `{target}` разблокирован.")
    else:
        bot.send_message(m.chat.id, "Его и так нет в списке.")

# --- [13] СЛУЖЕБНЫЕ КОМАНДЫ ---
@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "Вы вернулись в главное меню.", reply_markup=main_kb(str(m.from_user.id)))

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def global_cancel(m):
    bot.send_message(m.chat.id, "Действие отменено.", reply_markup=main_kb(str(m.from_user.id)))

# Запуск бота
print("Бот запущен...")
bot.infinity_polling()
