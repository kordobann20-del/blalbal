import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] НАСТРОЙКИ И КОНФИГУРАЦИЯ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
# Список админов (username без @)
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',      # Общий список всех существующих карт
    'colls': 'collections.json',# Кто какими картами владеет
    'squads': 'squads.json',    # Выставленные составы игроков
    'users': 'users_data.json', # Профили (очки, ники, юзернеймы)
    'bans': 'bans.json'         # Список заблокированных ID/Username
}

# Кулдаун на бесплатную крутку (10800 секунд = 3 часа)
COOLDOWN_ROLL = 10800

# Характеристики редкости: Шанс выпадения | Очки за карту | Сила атаки
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Список позиций на поле
POSITIONS_DATA = {
    0: {"label": "🧤 Вратарь (ГК)", "code": "ГК"},
    1: {"label": "🛡 Лев. Защитник (ЛЗ)", "code": "ЛЗ"},
    2: {"label": "🛡 Прав. Защитник (ПЗ)", "code": "ПЗ"},
    3: {"label": "👟 Центр. Полузащитник (ЦП)", "code": "ЦП"},
    4: {"label": "⚡️ Лев. Вингер (ЛВ)", "code": "ЛВ"},
    5: {"label": "⚡️ Прав. Вингер (ПВ)", "code": "ПВ"},
    6: {"label": "🎯 Форвард (КФ)", "code": "КФ"}
}

# --- [2] СИСТЕМА УПРАВЛЕНИЯ ДАННЫМИ (JSON) ---
def load_db(key):
    """Загрузка данных из файла. Создает файл, если его нет."""
    if not os.path.exists(FILES[key]):
        default = [] if key in ['cards', 'bans'] else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key in ['cards', 'bans'] else {}

def save_db(data, key):
    """Сохранение данных в файл."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация баз данных
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
ban_list = load_db('bans')
cooldowns = {} # Память для КД (сбрасывается при перезагрузке)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---
def is_admin(user):
    """Проверка прав администратора."""
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    """Проверка блокировки пользователя."""
    uname = user.username.lower() if user.username else None
    uid = str(user.id)
    return (uname in ban_list) or (uid in ban_list)

def get_power(uid):
    """Расчет силы состава (сумма атаки всех карт в слотах)."""
    sq = user_squads.get(str(uid), [None]*7)
    power = 0
    for player in sq:
        if player:
            power += STATS[player['stars']]['atk']
    return power

def main_kb(uid):
    """Главная клавиатура бота."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    try:
        user = bot.get_chat(uid)
        if is_admin(user):
            markup.add("🛠 Админ-панель")
    except: pass
    return markup

# --- [4] БАЗОВЫЕ КОМАНДЫ ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def handle_banned(m):
    bot.send_message(m.chat.id, "🚫 Доступ к боту заблокирован администрацией.")

@bot.message_handler(commands=['start'])
def send_welcome(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        users_data[uid] = {
            "nick": m.from_user.first_name,
            "score": 0,
            "username": (m.from_user.username.lower() if m.from_user.username else f"id{uid}")
        }
        save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Добро пожаловать в футбольный симулятор, {m.from_user.first_name}!", reply_markup=main_kb(uid))

# --- [5] СИСТЕМА ВЫПАДЕНИЯ КАРТ (ROLL) ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(m):
    uid = str(m.from_user.id)
    now = time.time()

    # Проверка КД (админам можно без очереди)
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
            left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
            hours = left // 3600
            minutes = (left % 3600) // 60
            return bot.send_message(m.chat.id, f"⏳ Кулдаун! Вы сможете крутить через {hours}ч {minutes}м.")

    if not cards:
        return bot.send_message(m.chat.id, "❌ В базе еще нет доступных карт. Попросите админа добавить их.")

    # Выбор редкости по шансам
    star_list = list(STATS.keys())
    star_weights = [STATS[s]['chance'] for s in star_list]
    selected_stars = random.choices(star_list, weights=star_weights)[0]

    # Поиск карт выбранной редкости
    pool = [c for c in cards if c['stars'] == selected_stars]
    if not pool: pool = cards # Если карт такой редкости нет, берем любую

    won = random.choice(pool)
    cooldowns[uid] = now # Установка КД
    
    if uid not in user_colls: user_colls[uid] = []
    
    # Проверка на дубликат
    is_duplicate = any(c['name'] == won['name'] for c in user_colls[uid])
    
    # Расчет очков (за повторку только 30%)
    pts = STATS[won['stars']]['score']
    if is_duplicate:
        pts = int(pts * 0.3)
        status_text = "🔄 ПОВТОРКА"
    else:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
        status_text = "✨ НОВАЯ КАРТА"

    users_data[uid]['score'] += pts
    save_db(users_data, 'users')

    caption = (f"⚽️ **Игрок:** {won['name']}\n"
               f"📋 **Статус:** {status_text}\n"
               f"🎯 **Позиция:** {won['pos']}\n"
               f"⭐ **Редкость:** {won['stars']} звёзд\n\n"
               f"💠 **Начислено:** +{pts:,} очков\n"
               f"💰 **Ваш счет:** {users_data[uid]['score']:,}")
    
    bot.send_photo(m.chat.id, won['photo'], caption=caption, parse_mode="Markdown")

# --- [6] ПРОФИЛЬ И ТОП ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_profile(m):
    uid = str(m.from_user.id)
    u = users_data.get(uid, {"nick": "Неизвестно", "score": 0, "username": "n/a"})
    count = len(user_colls.get(uid, []))
    power = get_power(uid)
    
    text = (f"👤 **Ваш профиль:**\n\n"
            f"Имя: {u['nick']}\n"
            f"💠 Очки: `{u['score']:,}`\n"
            f"🗂 Карт в коллекции: {count}\n"
            f"🛡 Сила состава: {power}\n"
            f"🆔 ID: `{uid}`")
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_top(m):
    # Сортировка всех игроков по очкам
    sorted_users = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    text = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        name = data.get('username', data['nick'])
        text += f"{i}. {name} — `{data['score']:,}` очков\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# --- [7] ПРОСМОТР КОЛЛЕКЦИИ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def show_collection(m):
    uid = str(m.from_user.id)
    if not user_colls.get(uid):
        return bot.send_message(m.chat.id, "🗂 У вас пока нет ни одной карты.")
    
    markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(f"{'⭐'*i} Показать", callback_data=f"list_stars_{i}"))
    bot.send_message(m.chat.id, "🗂 **Ваша коллекция (выберите редкость):**", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("list_stars_"))
def callback_list_stars(call):
    star = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    my_cards = [c for c in user_colls.get(uid, []) if c['stars'] == star]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас нет карт такой редкости!", show_alert=True)
    
    text = f"🗂 **Ваши карты {star}⭐:**\n\n"
    for c in my_cards:
        text += f"• {c['name']} ({c['pos']})\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [8] УПРАВЛЕНИЕ СОСТАВОМ ---
def squad_kb(uid):
    markup = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        player = sq[i]
        label = POSITIONS_DATA[i]["label"]
        name = player['name'] if player else "❌ ПУСТО"
        markup.add(types.InlineKeyboardButton(f"{label}: {name}", callback_data=f"manage_slot_{i}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def show_squad(m):
    bot.send_message(m.chat.id, "📋 **Ваш текущий состав:**\n(Нажмите на позицию, чтобы выбрать игрока)", reply_markup=squad_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("manage_slot_"))
def callback_manage_slot(call):
    slot_idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    req_pos = POSITIONS_DATA[slot_idx]["code"]
    
    # Фильтруем карты игрока, подходящие под позицию
    valid_players = [c for c in user_colls.get(uid, []) if c['pos'].upper() == req_pos]
    
    markup = types.InlineKeyboardMarkup()
    if not valid_players:
        markup.add(types.InlineKeyboardButton("❌ Нет подходящих карт", callback_data="back_to_sq"))
    else:
        for p in valid_players:
            markup.add(types.InlineKeyboardButton(f"{p['name']} ({p['stars']}⭐)", callback_data=f"apply_{slot_idx}_{p['name']}"))
    
    markup.add(types.InlineKeyboardButton("🚫 Убрать из состава", callback_data=f"apply_{slot_idx}_none"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_sq"))
    
    bot.edit_message_text(f"Выберите игрока на позицию {req_pos}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("apply_"))
def callback_apply_player(call):
    parts = call.data.split("_")
    idx, name, uid = int(parts[1]), parts[2], str(call.from_user.id)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        # Проверяем, не занят ли игрок в другом слоте
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже на поле!", show_alert=True)
        
        target_card = next(c for c in user_colls[uid] if c['name'] == name)
        user_squads[uid][idx] = target_card
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав успешно обновлен!", call.message.chat.id, call.message.message_id, reply_markup=squad_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data == "back_to_sq")
def callback_back_to_sq(call):
    bot.edit_message_text("📋 **Ваш состав:**", call.message.chat.id, call.message.message_id, reply_markup=squad_kb(call.from_user.id))

# --- [9] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_menu(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Случайный противник", callback_data="pvp_random"))
    bot.send_message(m.chat.id, "🏟 **Арена ПВП**\nПобеда зависит от силы вашего состава!", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "pvp_random")
def callback_pvp_random(call):
    uid = str(call.from_user.id)
    p1_power = get_power(uid)
    
    if p1_power == 0:
        return bot.answer_callback_query(call.id, "❌ Сначала соберите состав!", show_alert=True)
    
    # Ищем игроков с силой выше 0
    opponents = [u_id for u_id in users_data if u_id != uid and get_power(u_id) > 0]
    
    if not opponents:
        return bot.answer_callback_query(call.id, "❌ Нет доступных противников.", show_alert=True)
    
    enemy_id = random.choice(opponents)
    p2_power = get_power(enemy_id)
    
    bot.send_message(call.message.chat.id, f"🏟 **Матч:** {users_data[uid]['nick']} (⚔️{p1_power}) VS {users_data[enemy_id]['nick']} (⚔️{p2_power})")
    time.sleep(1.5)
    
    # Шансовая победа
    total = p1_power + p2_power
    if random.uniform(0, total) <= p1_power:
        winner_id, prize = uid, int(p2_power * 0.2) + 500
        result_text = f"🏆 Победил **{users_data[uid]['nick']}**!"
    else:
        winner_id, prize = enemy_id, 0
        result_text = f"💀 Вы проиграли игроку **{users_data[enemy_id]['nick']}**."

    if prize > 0:
        users_data[winner_id]['score'] += prize
        save_db(users_data, 'users')
        result_text += f"\n💰 Награда: +{prize} очков."
        
    bot.send_message(call.message.chat.id, result_text)
    bot.answer_callback_query(call.id)

# --- [10] АДМИН-ПАНЕЛЬ И ПОЛНОЕ ОБНУЛЕНИЕ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def show_admin_panel(m):
    if not is_admin(m.from_user): return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "📝 Изменить карту")
    markup.row("🗑 Удалить карту", "🧨 Обнулить бота")
    markup.row("🚫 Забанить", "✅ Разбанить")
    markup.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **Управление игрой (Админ):**", reply_markup=markup)

# ГЛОБАЛЬНОЕ ОБНУЛЕНИЕ С ПОДТВЕРЖДЕНИЕМ
@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_confirm(m):
    if not is_admin(m.from_user): return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧨 ДА, СТЕРЕТЬ ВСЁ", callback_data="confirm_nuke_everything"))
    markup.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_reset"))
    bot.send_message(m.chat.id, "⚠ **ВНИМАНИЕ!** Это действие удалит:\n1. Все очки у всех игроков.\n2. Все собранные коллекции.\n3. Все составы.\nВы уверены?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "confirm_nuke_everything")
def callback_nuke(call):
    if not is_admin(call.from_user): return
    global users_data, user_colls, user_squads
    
    # Обнуляем очки во всех профилях
    for u in users_data:
        users_data[u]['score'] = 0
    
    # Полностью очищаем словари коллекций и составов
    user_colls = {}
    user_squads = {}
    
    # Синхронизируем файлы
    save_db(users_data, 'users')
    save_db(user_colls, 'colls')
    save_db(user_squads, 'squads')
    
    bot.edit_message_text("🧨 **Бот полностью обнулен!** Все ресурсы стерты.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Сброс завершен")

@bot.callback_query_handler(func=lambda c: c.data == "cancel_reset")
def callback_cancel_reset(call):
    bot.edit_message_text("❌ Действие отменено.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# --- [11] УПРАВЛЕНИЕ ИГРОКАМИ (БАН / РАЗБАН) ---
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_start(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для бана:")
        bot.register_next_step_handler(msg, admin_ban_save)

def admin_ban_save(m):
    target = m.text.replace("@", "").lower().strip()
    if target not in ban_list:
        ban_list.append(target)
        save_db(ban_list, 'bans')
        bot.send_message(m.chat.id, f"✅ Игрок {target} заблокирован.")
    else:
        bot.send_message(m.chat.id, "Игрок уже в бан-листе.")

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_start(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для разбана:")
        bot.register_next_step_handler(msg, admin_unban_save)

def admin_unban_save(m):
    target = m.text.replace("@", "").lower().strip()
    global ban_list
    if target in ban_list:
        ban_list.remove(target)
        save_db(ban_list, 'bans')
        bot.send_message(m.chat.id, f"✅ Игрок {target} разбанен.")
    else:
        bot.send_message(m.chat.id, "Игрок не найден в бане.")

# --- [12] ДОБАВЛЕНИЕ КАРТ (АДМИН) ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_1(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Имя футболиста:")
        bot.register_next_step_handler(msg, admin_add_2)

def admin_add_2(m):
    name = m.text
    codes = [v['code'] for v in POSITIONS_DATA.values()]
    msg = bot.send_message(m.chat.id, f"Позиция ({', '.join(codes)}):")
    bot.register_next_step_handler(msg, admin_add_3, name)

def admin_add_3(m, name):
    pos = m.text.upper().strip()
    msg = bot.send_message(m.chat.id, "Звезды (1-5):")
    bot.register_next_step_handler(msg, admin_add_4, name, pos)

def admin_add_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте фото (картинку):")
        bot.register_next_step_handler(msg, admin_add_fin, name, pos, stars)
    except:
        bot.send_message(m.chat.id, "Ошибка! Рейтинг должен быть цифрой.")

def admin_add_fin(m, name, pos, stars):
    if not m.photo:
        return bot.send_message(m.chat.id, "Ошибка! Вы не прислали фото.")
    global cards
    cards.append({
        "name": name, 
        "pos": pos, 
        "stars": stars, 
        "photo": m.photo[-1].file_id
    })
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успешно создана!")

# --- [13] КНОПКА НАЗАД ---
@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_to_main(m):
    bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(m.from_user.id))

# Запуск
print("Бот успешно запущен!")
bot.infinity_polling()
