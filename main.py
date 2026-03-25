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
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json',
    'bans': 'bans.json'
}

# Кулдаун на бесплатную крутку (3 часа)
COOLDOWN_ROLL = 10800

# Характеристики редкости
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Названия позиций для красивого вывода
POSITIONS_LABELS = {
    "ГК": "Вратарь",
    "ЛЗ": "Лев. Защитник",
    "ПЗ": "Прав. Защитник",
    "ЦП": "Центр. Полузащитник",
    "ЛВ": "Лев. Вингер",
    "ПВ": "Прав. Вингер",
    "КФ": "Нападающий"
}

# Коды позиций для кнопок
POSITIONS_DATA = {
    0: {"label": "🧤 ГК", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 КФ", "code": "КФ"}
}

# --- [2] СИСТЕМА ПРЯМОГО ЧТЕНИЯ БД ---
def load_db(key):
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
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [3] ПРОВЕРКИ ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    ban_list = load_db('bans')
    u = user.username.lower() if user.username else None
    uid = str(user.id)
    return (u in ban_list) or (uid in ban_list)

def get_power(uid):
    user_squads = load_db('squads')
    sq = user_squads.get(str(uid), [None]*7)
    return sum(STATS[p['stars']]['atk'] for p in sq if p)

def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    try:
        user = bot.get_chat(uid)
        if is_admin(user): markup.add("🛠 Админ-панель")
    except: pass
    return markup

# --- [4] ОБРАБОТЧИКИ (START / BAN) ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def handle_banned(m):
    bot.send_message(m.chat.id, "🚫 Вы заблокированы администрацией.")

@bot.message_handler(commands=['start'])
def send_welcome(m):
    users_data = load_db('users')
    uid = str(m.from_user.id)
    uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    
    users_data[uid] = {
        "nick": m.from_user.first_name,
        "score": users_data.get(uid, {}).get('score', 0),
        "username": uname
    }
    save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Добро пожаловать, {m.from_user.first_name}!", reply_markup=main_kb(uid))

# --- [5] СИСТЕМА ВЫПАДЕНИЯ КАРТ (ROLL) ---
cooldowns = {}

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card_logic(m):
    uid = str(m.from_user.id)
    now = time.time()

    # Проверка кулдауна
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
            left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Кулдаун! Ждите еще {left//3600}ч {(left%3600)//60}м")

    # Чтение актуальной базы
    cards_list = load_db('cards')
    user_colls = load_db('colls')
    users_data = load_db('users')

    if not cards_list:
        return bot.send_message(m.chat.id, "❌ В игре пока нет карт. Попросите админа добавить их!")

    # Выбор редкости
    star_weights = [STATS[s]['chance'] for s in STATS.keys()]
    selected_stars = random.choices(list(STATS.keys()), weights=star_weights)[0]
    
    pool = [c for c in cards_list if c['stars'] == selected_stars]
    if not pool: pool = cards_list # Защита, если нужной редкости нет

    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    
    # Проверка на дубликат
    is_duplicate = any(c['name'] == won['name'] for c in user_colls[uid])
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_duplicate else 1))
    
    if not is_duplicate:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    users_data[uid]['score'] = users_data.get(uid, {}).get('score', 0) + pts
    save_db(users_data, 'users')

    # Формирование стиля сообщения (как ты просил)
    status_text = "Новая карта!" if not is_duplicate else "Повторка"
    pos_label = POSITIONS_LABELS.get(won['pos'].upper(), won['pos'])
    stars_str = "⭐" * won['stars']
    
    caption = (f"⚽️ **{won['name']}** (\"{status_text}\")\n\n"
               f"🎯 **Позиция:** {pos_label}\n"
               f"📊 **Рейтинг:** {stars_str}\n\n"
               f"💠 **Очки:** +{pts:,} | {users_data[uid]['score']:,}")
    
    bot.send_photo(m.chat.id, won['photo'], caption=caption, parse_mode="Markdown")

# --- [6] ПРОФИЛЬ И ТОП (ПО ЮЗЕРНЕЙМАМ) ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_profile(m):
    users_data = load_db('users')
    user_colls = load_db('colls')
    uid = str(m.from_user.id)
    
    u = users_data.get(uid, {"nick": m.from_user.first_name, "score": 0, "username": "n/a"})
    count = len(user_colls.get(uid, []))
    power = get_power(uid)
    
    text = (f"👤 **СТАТИСТИКА ИГРОКА**\n\n"
            f"📝 **Ник:** {u['nick']}\n"
            f"🔗 **Юзернейм:** {u['username']}\n"
            f"💠 **Очки:** `{u['score']:,}`\n"
            f"🗂 **Коллекция:** {count} шт.\n"
            f"🛡 **Сила состава:** {power}")
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def show_top_10(m):
    users_data = load_db('users')
    # Сортировка по очкам
    sorted_top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    text = "🏆 **ТОП-10 ИГРОКОВ (ПО ЮЗЕРНЕЙМАМ):**\n\n"
    for i, (uid, data) in enumerate(sorted_top, 1):
        display_name = data.get('username', f"id{uid}")
        text += f"{i}. {display_name} — `{data['score']:,}` очков\n"
    
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# --- [7] ПРОСМОТР КОЛЛЕКЦИИ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def show_collection_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(f"{'⭐'*i} Показать", callback_data=f"view_{i}"))
    bot.send_message(m.chat.id, "🗂 **Ваша коллекция (выберите редкость):**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_"))
def callback_show_list(call):
    star_level = int(call.data.split("_")[1])
    user_colls = load_db('colls')
    uid = str(call.from_user.id)
    
    my_cards = [card for card in user_colls.get(uid, []) if card['stars'] == star_level]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас нет таких карт!", show_alert=True)
    
    text = f"🗂 **Ваши карты {star_level}⭐:**\n\n"
    for c in my_cards:
        text += f"• {c['name']} ({c['pos']})\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [8] ПВП АРЕНА (ДИНАМИЧЕСКИЕ ШАНСЫ) ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_main(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Случайный бой", callback_data="arena_rand"))
    kb.add(types.InlineKeyboardButton("🔍 Вызвать по юзернейму", callback_data="arena_user"))
    bot.send_message(m.chat.id, "🏟 **АРЕНА ПВП**\nПобеждает тот, чей состав сильнее (в процентах)!", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "arena_user")
def arena_call_user(call):
    msg = bot.send_message(call.message.chat.id, "Введите @username соперника:")
    bot.register_next_step_handler(msg, arena_execute_user)

def arena_execute_user(m):
    target_un = m.text.replace("@", "").lower().strip()
    users_data = load_db('users')
    target_id = None
    for uid, d in users_data.items():
        if d.get('username', '').replace("@", "").lower() == target_un:
            target_id = uid
            break
    
    if target_id:
        if target_id == str(m.from_user.id):
            return bot.send_message(m.chat.id, "❌ Нельзя играть с самим собой!")
        start_battle(m.chat.id, str(m.from_user.id), target_id)
    else:
        bot.send_message(m.chat.id, "❌ Игрок не найден.")

@bot.callback_query_handler(func=lambda c: c.data == "arena_rand")
def arena_call_rand(call):
    users_data = load_db('users')
    uid = str(call.from_user.id)
    opponents = [u for u in users_data if u != uid and get_power(u) > 0]
    if not opponents:
        return bot.answer_callback_query(call.id, "Нет доступных врагов!", show_alert=True)
    start_battle(call.message.chat.id, uid, random.choice(opponents))

def start_battle(chat_id, p1_id, p2_id):
    users_data = load_db('users')
    p1_p, p2_p = get_power(p1_id), get_power(p2_id)
    
    if p1_p == 0:
        return bot.send_message(chat_id, "❌ Ваш состав пуст! Поставьте игроков в '📋 Состав'.")

    total = p1_p + p2_p
    p1_chance = (p1_p / total) * 100
    
    bot.send_message(chat_id, f"🏟 **МАТЧ:**\n{users_data[p1_id]['username']} (⚔️{p1_p}) VS {users_data[p2_id]['username']} (⚔️{p2_p})\n📊 Ваш шанс: {p1_chance:.1f}%")
    time.sleep(2)
    
    winner = random.choices([p1_id, p2_id], weights=[p1_p, p2_p])[0]
    users_data[winner]['score'] += 1000
    save_db(users_data, 'users')
    
    bot.send_message(chat_id, f"🏆 Победил: **{users_data[winner]['username']}**! (+1000 очков)")

# --- [9] АДМИН-ПАНЕЛЬ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel_view(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить карту", "📝 Изменить карту")
    kb.row("🗑 Удалить карту", "🧨 Обнулить бота")
    kb.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **УПРАВЛЕНИЕ:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_card(m):
    if not is_admin(m.from_user): return
    cards_list = load_db('cards')
    kb = types.InlineKeyboardMarkup()
    for c in cards_list:
        kb.add(types.InlineKeyboardButton(f"❌ {c['name']} ({c['stars']}⭐)", callback_data=f"del_{c['name']}"))
    bot.send_message(m.chat.id, "Выберите карту для удаления:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def callback_del_execute(call):
    name = call.data.replace("del_", "")
    cards_list = load_db('cards')
    cards_list = [c for c in cards_list if c['name'] != name]
    save_db(cards_list, 'cards')
    bot.edit_message_text(f"✅ Карта {name} удалена.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_nuke(m):
    if not is_admin(m.from_user): return
    users_data = load_db('users')
    for u in users_data: users_data[u]['score'] = 0
    save_db(users_data, 'users')
    save_db({}, 'colls')
    save_db({}, 'squads')
    bot.send_message(m.chat.id, "🧨 Бот полностью обнулен (очки и коллекции стерты).")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_start(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите имя игрока:")
        bot.register_next_step_handler(msg, admin_add_pos)

def admin_add_pos(m):
    name = m.text
    msg = bot.send_message(m.chat.id, "Позиция (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):")
    bot.register_next_step_handler(msg, admin_add_stars, name)

def admin_add_stars(m, name):
    pos = m.text.upper().strip()
    msg = bot.send_message(m.chat.id, "Звезды (1-5):")
    bot.register_next_step_handler(msg, admin_add_photo, name, pos)

def admin_add_photo(m, name, pos):
    stars = int(m.text)
    msg = bot.send_message(m.chat.id, "Пришлите фото карты:")
    bot.register_next_step_handler(msg, admin_add_final, name, pos, stars)

def admin_add_final(m, n, p, s):
    if m.photo:
        cards_list = load_db('cards')
        cards_list.append({"name": n, "pos": p, "stars": s, "photo": m.photo[-1].file_id})
        save_db(cards_list, 'cards')
        bot.send_message(m.chat.id, f"✅ Карта {n} добавлена!")

# --- [10] УПРАВЛЕНИЕ СОСТАВОМ ---
@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "📋 **ВАШ СОСТАВ:**", reply_markup=get_squad_kb(m.from_user.id))

def get_squad_kb(uid):
    user_squads = load_db('squads')
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]; label = POSITIONS_DATA[i]["label"]
        kb.add(types.InlineKeyboardButton(f"{label}: {p['name'] if p else '❌'}", callback_data=f"slot_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def callback_select_slot(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    user_colls = load_db('colls')
    pos_code = POSITIONS_DATA[idx]["code"]
    valid = [c for c in user_colls.get(uid, []) if c['pos'].upper() == pos_code]
    
    kb = types.InlineKeyboardMarkup()
    for v in valid:
        kb.add(types.InlineKeyboardButton(v['name'], callback_data=f"set_{idx}_{v['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text(f"Игроки на позицию {pos_code}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def callback_apply_player(call):
    p = call.data.split("_")
    idx, name, uid = int(p[1]), p[2], str(call.from_user.id)
    user_squads = load_db('squads')
    user_colls = load_db('colls')
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else:
        user_squads[uid][idx] = None
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_btn(m):
    bot.send_message(m.chat.id, "⚽️ Меню:", reply_markup=main_kb(m.from_user.id))

# Запуск
print("Бот успешно запущен!")
bot.infinity_polling()
