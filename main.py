import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ И НАСТРОЙКИ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
# Список админов, у которых есть доступ к спец. панели
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Пути к файлам базы данных (JSON)
FILES = {
    'cards': 'cards.json',      # Все существующие в игре карты
    'colls': 'collections.json',# Личные коллекции игроков
    'squads': 'squads.json',    # Выставленные составы игроков
    'users': 'users_data.json', # Данные профиля (очки, ники)
    'bans': 'bans.json'         # Список забаненных
}

# Кулдаун на крутку карты (3 часа в секундах)
COOLDOWN_ROLL = 10800

# Настройки редкости карт: шанс выпадения, очки за новую карту и сила атаки (atk)
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Данные о позициях на поле (код должен совпадать с тем, что в карте)
POSITIONS_DATA = {
    0: {"label": "🧤 ГК", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 КФ", "code": "КФ"}
}

# --- [2] ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ---
def load_db(key):
    """Загружает данные из JSON файла. Если файла нет — создает пустой."""
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
    """Сохраняет данные в указанный JSON файл."""
    with open(FILES[key], 'w', encoding='utf-8') as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация данных при запуске
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
ban_list = load_db('bans')
cooldowns = {} # Временная память для кулдаунов (сбрасывается при перезапуске бота)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---
def is_admin(user):
    """Проверяет, является ли пользователь админом."""
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    """Проверяет наличие пользователя в черном списке."""
    uname = user.username.lower() if user.username else None
    return uname in ban_list if uname else False

def get_power(uid):
    """Считает общую силу состава игрока на основе звезд карт."""
    sq = user_squads.get(str(uid), [None]*7)
    return sum(STATS[p['stars']]['atk'] for p in sq if p)

def main_kb(uid):
    """Главное меню бота."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    user = bot.get_chat(uid)
    if is_admin(user): 
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОСНОВНЫЕ ОБРАБОТЧИКИ (КОМАНДЫ) ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def check_ban(m):
    bot.send_message(m.chat.id, "🚫 Вы заблокированы в боте.")

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        users_data[uid] = {
            "nick": m.from_user.first_name, 
            "score": 0, 
            "username": (m.from_user.username.lower() if m.from_user.username else f"id{uid}")
        }
        save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Добро пожаловать, {users_data[uid]['nick']}!", reply_markup=main_kb(uid))

# --- [5] СИСТЕМА КРУТКИ КАРТ ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    # Проверка Кулдауна (админам можно без очереди)
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
            left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ КД! Жди еще `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")

    if not cards: 
        return bot.send_message(m.chat.id, "❌ Админы еще не добавили карты в игру.")

    # Логика выпадения карты
    stars = random.choices(list(STATS.keys()), weights=[s['chance'] for s in STATS.values()])[0]
    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now # Ставим КД
    
    if uid not in user_colls: user_colls[uid] = []
    
    # Проверка на дубликат
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    status = "ПОВТОРКА" if is_dub else "НОВАЯ КАРТА"
    
    # Очки (за повторку 30%)
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub: 
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
        
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    cap = (f"⚽️ *{won['name']}* (\"{status}\")\n\n"
           f"🎯 **Позиция:** {won['pos']}\n"
           f"📊 **Редкость:** {'⭐'*won['stars']}\n\n"
           f"💠 **Очки:** +{pts:,} | Итого: {users_data[uid]['score']:,}")
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] ПРОФИЛЬ И КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = str(m.from_user.id)
    d = users_data.get(uid, {"nick": "Игрок", "score": 0, "username": "n/a"})
    count = len(user_colls.get(uid, []))
    text = (f"👤 **Твой профиль:**\n\n"
            f"Ник: **{d['nick']}**\n"
            f"Юзер: @{d['username']}\n"
            f"💠 Очки: `{d['score']:,}`\n"
            f"🗂 Собрано карт: **{count}**\n"
            f"🆔 `{uid}`")
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    uid = str(m.from_user.id)
    if not user_colls.get(uid):
        return bot.send_message(m.chat.id, "🗂 Твоя коллекция пока пуста. Выбивай карты!")
    
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): 
        kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"view_{i}"))
    bot.send_message(m.chat.id, "🗂 **Просмотр коллекции по звездам:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_"))
def view_coll_stars(call):
    s = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: 
        return bot.answer_callback_query(call.id, "У тебя нет карт такой редкости!", show_alert=True)
    
    txt = f"🗂 **Твои карты {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [7] УПРАВЛЕНИЕ СОСТАВОМ (С ПРОВЕРКОЙ ПОЗИЦИЙ) ---
def get_squad_kb(uid):
    """Генерирует кнопки состава для выбора слота."""
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]
        label = POSITIONS_DATA[i]["label"]
        txt = f"{label}: {p['name'] if p else '❌ Пусто'}"
        kb.add(types.InlineKeyboardButton(txt, callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    uid = str(m.from_user.id)
    if not user_colls.get(uid):
        return bot.send_message(m.chat.id, "❌ У тебя нет игроков для состава!")
    bot.send_message(m.chat.id, "📋 **Твой состав (нажми на слот):**", reply_markup=get_squad_kb(uid), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_select(call):
    idx, uid = int(call.data.split("_")[1]), str(call.from_user.id)
    required_pos = POSITIONS_DATA[idx]["code"]
    
    # Фильтруем только тех игроков, чья позиция совпадает со слотом
    valid_players = [c for c in user_colls.get(uid, []) if c['pos'].upper() == required_pos]
    
    kb = types.InlineKeyboardMarkup()
    if not valid_players:
        kb.add(types.InlineKeyboardButton("❌ Нет подходящих игроков", callback_data="none"))
    else:
        for c in valid_players:
            kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"set_{idx}_{c['name']}"))
    
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"set_{idx}_none"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_squad"))
    
    bot.edit_message_text(f"Выбор на позицию {required_pos}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_squad")
def back_to_sq(call):
    bot.edit_message_text("📋 **Твой состав:**", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(call.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_player_to_squad(call):
    parts = call.data.split("_")
    idx, name, uid = int(parts[1]), parts[2], str(call.from_user.id)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        # Проверка, чтобы один и тот же игрок не стоял в двух местах
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже в составе!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else:
        user_squads[uid][idx] = None
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- [8] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_main(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎲 Рандомный бой", callback_data="arena_random"),
           types.InlineKeyboardButton("👤 По юзернейму", callback_data="arena_by_user"))
    bot.send_message(m.chat.id, "🏟 **Добро пожаловать на Арену!**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_"))
def arena_cb(call):
    uid = str(call.from_user.id)
    if "random" in call.data:
        # Ищем оппонентов с ненулевой силой
        opps = [u for u in users_data if u != uid and get_power(u) > 0]
        if opps: start_battle(call.message.chat.id, uid, random.choice(opps))
        else: bot.answer_callback_query(call.id, "Никого нет на арене!", show_alert=True)
    else:
        msg = bot.send_message(call.message.chat.id, "Введи юзернейм противника (без @):")
        bot.register_next_step_handler(msg, search_user_arena)
    bot.answer_callback_query(call.id)

def search_user_arena(m):
    target = m.text.replace("@", "").lower().strip()
    found = next((u for u, d in users_data.items() if d.get('username') == target), None)
    if found: start_battle(m.chat.id, str(m.from_user.id), found)
    else: bot.send_message(m.chat.id, "❌ Игрок не найден.")

def start_battle(chat_id, p1_id, p2_id):
    p1_atk, p2_atk = get_power(p1_id), get_power(p2_id)
    if p1_atk == 0 or p2_atk == 0: 
        return bot.send_message(chat_id, "❌ У одного из бойцов пустой состав!")
    
    total = p1_atk + p2_atk
    res = random.uniform(0, 100)
    
    bot.send_message(chat_id, f"🏟 **МАТЧ НАЧАЛСЯ!**\n\n🏠 {users_data[p1_id]['nick']} (Сила: {p1_atk})\nVS\n🚀 {users_data[p2_id]['nick']} (Сила: {p2_atk})")
    time.sleep(2)
    
    # Шанс победы зависит от силы атаки
    if res <= (p1_atk / total * 100):
        winner, prize = p1_id, int(p2_atk * 0.3)
    else:
        winner, prize = p2_id, int(p1_atk * 0.3)
    
    users_data[winner]['score'] += prize
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Победил **{users_data[winner]['nick']}**!\n💰 Выигрыш: `+{prize:,}` очков.", parse_mode="Markdown")

# --- [9] АДМИН-ПАНЕЛЬ И ПОЛНОЕ ОБНУЛЕНИЕ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить карту", "🗑 Удалить карту")
    kb.row("📝 Изменить карту", "🧨 Обнулить бота")
    kb.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **Админка:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def reset_confirm(m):
    if not is_admin(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ ДА, ОБНУЛИТЬ ВСЁ", callback_data="confirm_full_reset"))
    kb.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_reset"))
    bot.send_message(m.chat.id, "❗ **ВНИМАНИЕ!**\nВсе очки, коллекции и составы игроков будут безвозвратно удалены. Подтверждаешь?", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "confirm_full_reset")
def full_reset_logic(call):
    if not is_admin(call.from_user): return
    global users_data, user_colls, user_squads
    
    # 1. Обнуляем очки в профилях
    for uid in users_data: users_data[uid]['score'] = 0
    # 2. Очищаем все коллекции
    user_colls = {}
    # 3. Очищаем все составы
    user_squads = {}
    
    # Сохраняем пустые/обновленные данные
    save_db(users_data, 'users')
    save_db(user_colls, 'colls')
    save_db(user_squads, 'squads')
    
    bot.edit_message_text("🧨 **БОТ ПОЛНОСТЬЮ ОБНУЛЕН!**\nНачат новый сезон.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Обнуление завершено!")

@bot.callback_query_handler(func=lambda c: c.data == "cancel_reset")
def cancel_reset(call):
    bot.edit_message_text("❌ Обнуление отменено.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# --- [10] ДОБАВЛЕНИЕ / УДАЛЕНИЕ КАРТ (АДМИН) ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_card_1(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Введите имя футболиста:")
    bot.register_next_step_handler(msg, add_card_2)

def add_card_2(m):
    name = m.text
    codes = [v['code'] for v in POSITIONS_DATA.values()]
    msg = bot.send_message(m.chat.id, f"Введите позицию ({', '.join(codes)}):")
    bot.register_next_step_handler(msg, add_card_3, name)

def add_card_3(m, name):
    pos = m.text.upper().strip()
    msg = bot.send_message(m.chat.id, "Введите кол-во звезд (1-5):")
    bot.register_next_step_handler(msg, add_card_4, name, pos)

def add_card_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте фото игрока:")
        bot.register_next_step_handler(msg, add_card_fin, name, pos, stars)
    except: 
        bot.send_message(m.chat.id, "Ошибка! Нужно ввести число.")

def add_card_fin(m, name, pos, stars):
    if not m.photo: return bot.send_message(m.chat.id, "Ошибка! Нужно отправить фото.")
    global cards
    # Удаляем старую карту с таким именем, если есть
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успешно добавлена!", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_scores(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (u, d) in enumerate(top, 1):
        display = f"@{d['username']}" if not d['username'].startswith("id") else d['nick']
        txt += f"{i}. **{display}** — `{d['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(m.from_user.id))

# Запуск бота
print("Бот запущен...")
bot.infinity_polling()
