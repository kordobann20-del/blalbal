import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] НАСТРОЙКИ И ТОКЕН ---
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

# Настройки редкости
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

POSITIONS_LABELS = {
    "ГК": "Вратарь",
    "ЛЗ": "Лев. Защитник",
    "ПЗ": "Прав. Защитник",
    "ЦП": "Центр. Полузащитник",
    "ЛВ": "Лев. Вингер",
    "ПВ": "Прав. Вингер",
    "КФ": "Нападающий"
}

POSITIONS_DATA = {
    0: {"label": "🧤 ГК", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 КФ", "code": "КФ"}
}

# --- [2] ФУНКЦИИ БАЗЫ ДАННЫХ ---
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

# --- [4] ОБРАБОТЧИКИ КОМАНД ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def banned_msg(m):
    bot.send_message(m.chat.id, "🚫 Вы заблокированы.")

@bot.message_handler(commands=['start'])
def start_cmd(m):
    users_data = load_db('users')
    uid = str(m.from_user.id)
    uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    
    users_data[uid] = {
        "nick": m.from_user.first_name,
        "score": users_data.get(uid, {}).get('score', 0),
        "username": uname
    }
    save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Привет, {m.from_user.first_name}!", reply_markup=main_kb(uid))

# --- [5] КРУТКА КАРТ (ROLL) ---
cooldowns = {}
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(m):
    uid = str(m.from_user.id)
    now = time.time()
    COOLDOWN_ROLL = 10800

    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
            left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Ждите {left//3600}ч {(left%3600)//60}м")

    cards_list = load_db('cards')
    user_colls = load_db('colls')
    users_data = load_db('users')

    if not cards_list:
        return bot.send_message(m.chat.id, "❌ Карт еще нет.")

    sel_stars = random.choices(list(STATS.keys()), weights=[STATS[s]['chance'] for s in STATS.keys()])[0]
    pool = [c for c in cards_list if c['stars'] == sel_stars] or cards_list
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    users_data[uid]['score'] = users_data.get(uid, {}).get('score', 0) + pts
    save_db(users_data, 'users')

    status = "Новая карта!" if not is_dub else "Повторка"
    cap = (f"⚽️ **{won['name']}** (\"{status}\")\n\n"
           f"🎯 **Позиция:** {POSITIONS_LABELS.get(won['pos'], won['pos'])}\n"
           f"📊 **Рейтинг:** {'⭐'*won['stars']}\n\n"
           f"💠 **Очки:** +{pts:,} | {users_data[uid]['score']:,}")
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] ПРОФИЛЬ (ОБНОВЛЯЕТ ЮЗЕРНЕЙМ СРАЗУ) ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_view(m):
    users_data = load_db('users')
    user_colls = load_db('colls')
    uid = str(m.from_user.id)
    
    # Сразу обновляем юзернейм при заходе в профиль
    current_uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    if uid not in users_data:
        users_data[uid] = {"nick": m.from_user.first_name, "score": 0, "username": current_uname}
    else:
        users_data[uid]["username"] = current_uname
    save_db(users_data, 'users')

    u = users_data[uid]
    count = len(user_colls.get(uid, []))
    power = get_power(uid)
    
    text = (f"👤 **ПРОФИЛЬ:**\n\n"
            f"📝 **Имя:** {u['nick']}\n"
            f"🔗 **Юзернейм:** {u['username']}\n"
            f"💠 **Очки:** `{u['score']:,}`\n"
            f"🗂 **Коллекция:** {count} шт.\n"
            f"🛡 **Сила состава:** {power}")
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# --- [7] ТОП ОЧКОВ ---
@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_view(m):
    users_data = load_db('users')
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    text = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        text += f"{i}. {data.get('username', 'id'+uid)} — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# --- [8] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def pvp_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Случайный бой", callback_data="p_rand"))
    kb.add(types.InlineKeyboardButton("🔍 Бой по юзернейму", callback_data="p_user"))
    bot.send_message(m.chat.id, "🏟 **АРЕНА:**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "p_user")
def pvp_user(call):
    msg = bot.send_message(call.message.chat.id, "Введите @username противника:")
    bot.register_next_step_handler(msg, pvp_exec_user)

def pvp_exec_user(m):
    target_un = m.text.replace("@", "").lower().strip()
    users_data = load_db('users')
    target_id = next((uid for uid, d in users_data.items() if d.get('username', '').replace("@", "").lower() == target_un), None)
    if target_id:
        battle(m.chat.id, str(m.from_user.id), target_id)
    else: bot.send_message(m.chat.id, "❌ Не найден.")

@bot.callback_query_handler(func=lambda c: c.data == "p_rand")
def pvp_rand(call):
    users_data = load_db('users')
    uid = str(call.from_user.id)
    opps = [u for u in users_data if u != uid and get_power(u) > 0]
    if not opps: return bot.answer_callback_query(call.id, "Нет врагов!", show_alert=True)
    battle(call.message.chat.id, uid, random.choice(opps))

def battle(chat_id, p1, p2):
    users_data = load_db('users')
    p1_p, p2_p = get_power(p1), get_power(p2)
    if p1_p == 0: return bot.send_message(chat_id, "❌ Собери состав!")
    winner = random.choices([p1, p2], weights=[p1_p, p2_p])[0]
    users_data[winner]['score'] += 1000
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Победил: {users_data[winner].get('username')} (+1000)")

# --- [9] АДМИН-ПАНЕЛЬ (ИСПРАВЛЕННАЯ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_menu(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить карту", "📝 Изменить карту")
    kb.row("🗑 Удалить карту", "🧨 Обнулить бота")
    kb.row("🚫 Забанить", "✅ Разбанить")
    kb.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **АДМИН-ПАНЕЛЬ:**", reply_markup=kb)

# ИЗМЕНЕНИЕ КАРТЫ
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_list(m):
    if not is_admin(m.from_user): return
    cards_list = load_db('cards')
    if not cards_list: return bot.send_message(m.chat.id, "Карт нет.")
    kb = types.InlineKeyboardMarkup()
    for c in cards_list:
        kb.add(types.InlineKeyboardButton(f"📝 {c['name']}", callback_data=f"edit_c_{c['name']}"))
    bot.send_message(m.chat.id, "Какую карту изменить?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_c_"))
def admin_edit_step1(call):
    name = call.data.replace("edit_c_", "")
    msg = bot.send_message(call.message.chat.id, f"Меняем {name}. Введите: `Новое имя, Позиция, Звезды` (через запятую)\nПример: Messi, КФ, 5", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_edit_step2, name)

def admin_edit_step2(m, old_name):
    try:
        cards_list = load_db('cards')
        data = m.text.split(",")
        new_n, new_p, new_s = data[0].strip(), data[1].strip().upper(), int(data[2].strip())
        for c in cards_list:
            if c['name'] == old_name:
                c['name'], c['pos'], c['stars'] = new_n, new_p, new_s
                break
        save_db(cards_list, 'cards')
        bot.send_message(m.chat.id, "✅ Карта изменена!")
    except: bot.send_message(m.chat.id, "❌ Ошибка формата!")

# БАН И РАЗБАН
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для бана:")
        bot.register_next_step_handler(msg, admin_ban_exec)

def admin_ban_exec(m):
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    if target not in bans:
        bans.append(target)
        save_db(bans, 'bans')
        bot.send_message(m.chat.id, f"✅ {target} забанен.")

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для разбана:")
        bot.register_next_step_handler(msg, admin_unban_exec)

def admin_unban_exec(m):
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    if target in bans:
        bans.remove(target)
        save_db(bans, 'bans')
        bot.send_message(m.chat.id, f"✅ {target} разбанен.")

# УДАЛЕНИЕ КАРТЫ
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_del_list(m):
    if not is_admin(m.from_user): return
    cards_list = load_db('cards')
    kb = types.InlineKeyboardMarkup()
    for c in cards_list:
        kb.add(types.InlineKeyboardButton(f"❌ {c['name']}", callback_data=f"del_c_{c['name']}"))
    bot.send_message(m.chat.id, "Удалить карту:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_c_"))
def admin_del_exec(call):
    name = call.data.replace("del_c_", "")
    cards_list = load_db('cards')
    cards_list = [c for c in cards_list if c['name'] != name]
    save_db(cards_list, 'cards')
    bot.edit_message_text(f"✅ {name} удалена.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_all(m):
    if not is_admin(m.from_user): return
    users_data = load_db('users')
    for u in users_data: users_data[u]['score'] = 0
    save_db(users_data, 'users')
    save_db({}, 'colls'); save_db({}, 'squads')
    bot.send_message(m.chat.id, "🧨 Обнулено.")

# ДОБАВЛЕНИЕ КАРТЫ
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_card_1(m):
    if is_admin(m.from_user):
        bot.register_next_step_handler(bot.send_message(m.chat.id, "Имя:"), add_card_2)

def add_card_2(m):
    n = m.text
    bot.register_next_step_handler(bot.send_message(m.chat.id, "Поз (ГК, ЛЗ...):"), add_card_3, n)

def add_card_3(m, n):
    p = m.text.upper()
    bot.register_next_step_handler(bot.send_message(m.chat.id, "Звезды (1-5):"), add_card_4, n, p)

def add_card_4(m, n, p):
    s = int(m.text)
    bot.register_next_step_handler(bot.send_message(m.chat.id, "Фото:"), add_card_fin, n, p, s)

def add_card_fin(m, n, p, s):
    if m.photo:
        cards_list = load_db('cards')
        cards_list.append({"name": n, "pos": p, "stars": s, "photo": m.photo[-1].file_id})
        save_db(cards_list, 'cards')
        bot.send_message(m.chat.id, "✅ Добавлена!")

# --- [10] КОЛЛЕКЦИЯ И СОСТАВ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_view(m):
    user_colls = load_db('colls')
    uid = str(m.from_user.id)
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(f"{'⭐'*i} Показать", callback_data=f"v_{i}"))
    bot.send_message(m.chat.id, "🗂 **Коллекция:**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def coll_list(call):
    s = int(call.data[2:])
    user_colls = load_db('colls')
    my = [c for c in user_colls.get(str(call.from_user.id), []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "Нет таких карт!", show_alert=True)
    txt = f"🗂 **{s}⭐:**\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_view(m):
    bot.send_message(m.chat.id, "📋 **СОСТАВ:**", reply_markup=get_sq_kb(m.from_user.id))

def get_sq_kb(uid):
    user_squads = load_db('squads')
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]; l = POSITIONS_DATA[i]["label"]
        kb.add(types.InlineKeyboardButton(f"{l}: {p['name'] if p else '❌'}", callback_data=f"sl_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("sl_"))
def sl_select(call):
    idx, uid = int(call.data[3:]), str(call.from_user.id)
    user_colls = load_db('colls')
    pos = POSITIONS_DATA[idx]["code"]
    valid = [c for c in user_colls.get(uid, []) if c['pos'].upper() == pos]
    kb = types.InlineKeyboardMarkup()
    for v in valid: kb.add(types.InlineKeyboardButton(v['name'], callback_data=f"st_{idx}_{v['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"st_{idx}_none"))
    bot.edit_message_text(f"Выбор на {pos}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("st_"))
def st_apply(call):
    p = call.data.split("_")
    idx, name, uid = int(p[1]), p[2], str(call.from_user.id)
    user_squads = load_db('squads')
    user_colls = load_db('colls')
    if uid not in user_squads: user_squads[uid] = [None]*7
    user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None) if name != "none" else None
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "⚽️ Меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
