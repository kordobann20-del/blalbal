import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ И НАСТРОЙКИ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
# Список ников администраторов без @
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Пути к файлам базы данных
FILES = {
    'cards': 'cards.json',      # Список всех созданных карт
    'colls': 'collections.json',# Кто какой картой владеет
    'squads': 'squads.json',    # Выбранные составы игроков
    'users': 'users_data.json'  # Данные пользователей (ники, очки)
}

# Настройка шансов выпадения и очков за редкость
# 10800 секунд = 3 часа
COOLDOWN_TIME = 10800 

STATS = {
    1: {"chance": 50, "score": 1000},
    2: {"chance": 30, "score": 3000},
    3: {"chance": 12, "score": 5000},
    4: {"chance": 6, "score": 8000},
    5: {"chance": 2, "score": 10000}
}

# Список позиций для состава
POSITIONS_LIST = ["🧤 ГК", "🛡 ЛЗ", "🛡 ПЗ", "👟 ЦП", "⚡️ ЛВ", "⚡️ ПВ", "🎯 КФ"]

# --- [2] ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ---

def load_db(key):
    """Загрузка данных из JSON файла"""
    if not os.path.exists(FILES[key]):
        default = [] if key == 'cards' else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key == 'cards' else {}

def save_db(data, key):
    """Сохранение данных в JSON файл"""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация баз данных в памяти
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
cooldowns = {} # Временное хранилище КД (сбрасывается при перезапуске бота)

# --- [3] ФУНКЦИИ КЛАВИАТУР ---

def main_kb(uid):
    """Главное меню бота"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "🏟 Арена")
    markup.row("🏆 Топ очков", "🔝 Топ карт")
    
    # Проверка на админа для кнопки панели
    user_info = bot.get_chat(uid)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_kb():
    """Меню администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить карту", "🗑 Удалить карту")
    markup.row("🏠 Назад в меню")
    return markup

# --- [4] РЕГИСТРАЦИЯ И СТАРТ ---

@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка команды /start"""
    uid = str(message.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(message.chat.id, "👋 **Добро пожаловать в FootCard!**\n\nПридумай и введи свой **игровой ник** для регистрации:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, register_user_nick)
    else:
        nick = users_data[uid]['nick']
        bot.send_message(message.chat.id, f"⚽️ Рады видеть тебя снова, **{nick}**!", reply_markup=main_kb(uid), parse_mode="Markdown")

def register_user_nick(message):
    """Сохранение ника пользователя"""
    uid = str(message.from_user.id)
    nick = message.text
    if not nick:
        msg = bot.send_message(message.chat.id, "❌ Ник не может быть пустым. Введи снова:")
        return bot.register_next_step_handler(msg, register_user_nick)
    
    users_data[uid] = {"nick": nick, "score": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Игровой профиль **{nick}** создан!", reply_markup=main_kb(uid), parse_mode="Markdown")

# --- [5] ЛОГИКА ВЫПАДЕНИЯ КАРТ ---

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(message):
    """Процесс получения новой карты"""
    uid = str(message.from_user.id)
    now = time.time()
    
    if uid not in users_data:
        return start_command(message)

    # Проверка прав администратора для пропуска КД
    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    # Проверка кулдауна (3 часа)
    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_TIME and not is_admin:
        left = int(COOLDOWN_TIME - (now - cooldowns[uid]))
        h = left // 3600
        m = (left % 3600) // 60
        s = left % 60
        return bot.send_message(message.chat.id, f"⏳ **Твои футболисты отдыхают!**\n\nЗаходи через: `{h}ч {m}м {s}с`", parse_mode="Markdown")

    if not cards:
        return bot.send_message(message.chat.id, "⚠️ **В игре пока нет доступных карт.** Свяжитесь с админом.")

    # Выбор редкости (звездности)
    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc:
            stars = s
            break

    # Выбираем карту из пула нужной редкости
    potential_cards = [c for c in cards if c['stars'] == stars]
    if not potential_cards: 
        potential_cards = cards # Если карт с таким рейтингом нет, даем любую

    won_card = random.choice(potential_cards)
    cooldowns[uid] = now # Обновляем время последней крутки
    
    if uid not in user_colls:
        user_colls[uid] = []
    
    # Проверка на повторку
    is_duplicate = any(c['name'] == won_card['name'] for c in user_colls[uid])
    status_text = "повторка" if is_duplicate else "новая карта"
    reward_points = STATS[won_card['stars']]['score']
    
    # Если карта новая, добавляем в коллекцию и начисляем очки
    if not is_duplicate:
        user_colls[uid].append(won_card)
        users_data[uid]['score'] += reward_points
        save_db(user_colls, 'colls')
        save_db(users_data, 'users')

    # Красивое оформление сообщения
    current_nick = users_data[uid]['nick']
    card_caption = (
        f"🏃‍♂️ **{won_card['name']} ({status_text})**\n"
        f"👤 Владелец: **{current_nick}**\n\n"
        f"╔════════════════════╗\n"
        f"  📊 **ХАРАКТЕРИСТИКИ:**\n"
        f"  ├ Позиция: **{won_card.get('pos', 'Неизвестно')}**\n"
        f"  ├ Рейтинг: **{'⭐' * won_card['stars']}**\n"
        f"  └ Очки:    **+{reward_points:,}**\n"
        f"╚════════════════════╝\n\n"
        f"💰 Твой общий счет: **{users_data[uid]['score']:,}**"
    )
    
    bot.send_photo(message.chat.id, won_card['photo'], caption=card_caption, parse_mode="Markdown")

# --- [6] ТАБЛИЦЫ ЛИДЕРОВ (ТОПЫ) ---

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_top_scores(message):
    """Вывод топ-10 игроков по очкам"""
    # Сортируем пользователей по убыванию очков
    top_list = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    response = "🏆 **ТОП-10 ИГРОКОВ ПО ОЧКАМ:**\n\n"
    for i, (uid, data) in enumerate(top_list, 1):
        response += f"{i}. **{data['nick']}** — `{data['score']:,}` очков\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔝 Топ карт")
def show_top_cards(message):
    """Вывод топ-10 игроков по количеству уникальных карт"""
    top_list = sorted(user_colls.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    
    response = "🔝 **ЛИДЕРЫ ПО КОЛЛЕКЦИИ:**\n\n"
    for i, (uid, coll) in enumerate(top_list, 1):
        # Достаем ник из данных пользователей по ID
        player_nick = users_data.get(uid, {}).get('nick', 'Аноним')
        response += f"{i}. **{player_nick}** — `{len(coll)}` уникальных карт\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# --- [7] УПРАВЛЕНИЕ СОСТАВОМ ---

def get_squad_inline_keyboard(uid):
    """Создание кнопок для выбора позиций в составе"""
    kb = types.InlineKeyboardMarkup()
    # Загружаем состав или создаем пустой из 7 слотов
    user_sq = user_squads.get(str(uid), [None]*7)
    
    for i in range(7):
        slot_name = user_sq[i]['name'] if user_sq[i] else "⚠️ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {slot_name}", callback_data=f"pos_idx_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def open_squad_menu(message):
    """Открытие меню состава"""
    bot.send_message(message.chat.id, "📋 **Твой основной состав:**\n(Выбери позицию для изменения)", 
                     reply_markup=get_squad_inline_keyboard(message.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pos_idx_"))
def show_available_players_for_slot(call):
    """Показать список карт игрока для выбора в слот"""
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    player_collection = user_colls.get(uid, [])
    
    if not player_collection:
        return bot.answer_callback_query(call.id, "Твоя коллекция пуста! Крути карты.", show_alert=True)
    
    kb = types.InlineKeyboardMarkup()
    for card in player_collection:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_sq_{idx}_{card['name']}"))
    
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"set_sq_{idx}_none"))
    
    bot.edit_message_text(f"🎯 Выбери игрока на позицию **{POSITIONS_LIST[idx]}**:", 
                          call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_sq_"))
def save_player_to_squad(call):
    """Сохранение выбранного игрока в слот с проверкой на дубликаты"""
    data_parts = call.data.split("_")
    idx = int(data_parts[2])
    card_name = data_parts[3]
    uid = str(call.from_user.id)
    
    if uid not in user_squads:
        user_squads[uid] = [None]*7
        
    if card_name != "none":
        # ПРОВЕРКА: Не стоит ли этот игрок уже на другой позиции?
        # Итерируем по всем слотам кроме текущего (idx)
        for i, card in enumerate(user_squads[uid]):
            if card and card['name'] == card_name and i != idx:
                return bot.answer_callback_query(call.id, "❌ Этот игрок уже на поле в другой позиции!", show_alert=True)
        
        # Находим данные карты в коллекции пользователя
        selected_card = next(c for c in user_colls[uid] if c['name'] == card_name)
        user_squads[uid][idx] = selected_card
    else:
        user_squads[uid][idx] = None
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, 
                          reply_markup=get_squad_inline_keyboard(uid), parse_mode="Markdown")

# --- [8] ПАНЕЛЬ АДМИНИСТРАТОРА ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_main_menu(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(m.chat.id, "🛠 **Режим редактирования игры:**", reply_markup=admin_kb(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_step_1_name(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "📝 Введи **имя** футболиста:")
        bot.register_next_step_handler(msg, admin_add_step_2_pos)

def admin_add_step_2_pos(m):
    player_name = m.text
    msg = bot.send_message(m.chat.id, f"📍 Введи **позицию** для {player_name} (например, Защитник):")
    bot.register_next_step_handler(msg, admin_add_step_3_stars, player_name)

def admin_add_step_3_stars(m, player_name):
    player_pos = m.text
    msg = bot.send_message(m.chat.id, "⭐ Введи **рейтинг** (число от 1 до 5):")
    bot.register_next_step_handler(msg, admin_add_step_4_photo, player_name, player_pos)

def admin_add_step_4_photo(m, player_name, player_pos):
    try:
        stars = int(m.text)
        if not (1 <= stars <= 5): raise ValueError
        msg = bot.send_message(m.chat.id, f"🖼 Отправь **фото** для игрока {player_name}:")
        bot.register_next_step_handler(msg, admin_add_final, player_name, player_pos, stars)
    except:
        bot.send_message(m.chat.id, "❌ Ошибка! Нужно ввести число от 1 до 5. Попробуй снова через меню.")

def admin_add_final(m, player_name, player_pos, stars):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Это не фото! Операция отменена.")
    
    global cards
    # Удаляем старую версию карты с таким же именем, если она была
    cards = [c for c in cards if c['name'].lower() != player_name.lower()]
    
    # Добавляем новую карту (берем лучшее качество фото)
    new_card = {
        "name": player_name,
        "pos": player_pos,
        "stars": stars,
        "photo": m.photo[-1].file_id
    }
    cards.append(new_card)
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Игрок **{player_name}** успешно добавлен в игру!", reply_markup=admin_kb(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def admin_go_back_to_main(m):
    bot.send_message(m.chat.id, "Выходим в главное меню...", reply_markup=main_kb(m.from_user.id))

# --- [9] ЗАПУСК БОТА ---

bot.infinity_polling()
