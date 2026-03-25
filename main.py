import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФІГУРАЦІЯ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

FILES = {
    'cards': 'cards.json', 'colls': 'collections.json',
    'squads': 'squads.json', 'users': 'users_data.json', 'bans': 'bans.json'
}

COOLDOWN_ROLL = 10800
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Словник відповідності кнопок та кодів позицій
POSITIONS_DATA = {
    0: {"label": "🧤 ГК", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 КФ", "code": "КФ"}
}

# --- [2] РОБОТА З БД ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key in ['cards', 'bans'] else {}
        with open(FILES[key], 'w', encoding='utf-8') as f: json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return [] if key in ['cards', 'bans'] else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards'); user_colls = load_db('colls'); user_squads = load_db('squads')
users_data = load_db('users'); ban_list = load_db('bans'); cooldowns = {}; challenges = {}

# --- [3] ФУНКЦІЇ ПЕРЕВІРКИ ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    uname = user.username.lower() if user.username else None
    return uname in ban_list if uname else False

def get_power(uid):
    sq = user_squads.get(str(uid), [None]*7)
    return sum(STATS[p['stars']]['atk'] for p in sq if p)

def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    user = bot.get_chat(uid)
    if is_admin(user): markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРОТКА КОМАНД ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def check_ban(m): bot.send_message(m.chat.id, "🚫 Доступ ограничен.")

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
    bot.send_message(m.chat.id, f"⚽️ С возвращением, {users_data[uid]['nick']}!", reply_markup=main_kb(uid))

# --- [5] КРУТКА ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(m):
    uid = str(m.from_user.id)
    now = time.time()
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
            left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Подождите еще `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")

    if not cards: return bot.send_message(m.chat.id, "❌ Нет карт в базе.")

    stars = random.choices(list(STATS.keys()), weights=[s['chance'] for s in STATS.values()])[0]
    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    status = "ПОВТОРКА" if is_dub else "НОВАЯ КАРТА"
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub: 
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
        
    users_data[uid]['score'] += pts
    users_data[uid]['username'] = (m.from_user.username.lower() if m.from_user.username else f"id{uid}")
    save_db(users_data, 'users')
    
    cap = (f"⚽️ *{won['name']}* (\"{status}\")\n\n"
           f"🎯 **Позиция:** {won['pos']}\n"
           f"📊 **Рейтинг:** {'⭐'*won['stars']}\n\n"
           f"💠 **Очки:** +{pts:,} | Всего: {users_data[uid]['score']:,}")
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] ТОП ОЧКОВ ---
@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_scores(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ІГРОВЦІВ:**\n\n"
    for i, (u, d) in enumerate(top, 1):
        display = f"@{d['username']}" if not d['username'].startswith("id") else d['nick']
        txt += f"{i}. **{display}** — `{d['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# --- [7] СОСТАВ (З ПЕРЕВІРКОЮ ПОЗИЦІЙ) ---
def get_squad_kb(uid):
    kb = types.InlineKeyboardMarkup(); sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]
        label = POSITIONS_DATA[i]["label"]
        txt = f"{label}: {p['name'] if p else '❌'}"
        kb.add(types.InlineKeyboardButton(txt, callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m): bot.send_message(m.chat.id, "📋 **Твій склад:**\n*(Натисніть на слот, щоб обрати гравця на цю позицію)*", reply_markup=get_squad_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_select(call):
    idx, uid = int(call.data.split("_")[1]), str(call.from_user.id)
    required_pos = POSITIONS_DATA[idx]["code"] # Наприклад "ГК"
    
    # Фільтруємо колекцію: тільки ті, у кого позиція збігається
    valid_players = [c for c in user_colls.get(uid, []) if c['pos'].upper() == required_pos]
    
    kb = types.InlineKeyboardMarkup()
    if not valid_players:
        kb.add(types.InlineKeyboardButton("❌ Немає гравців для цієї позиції", callback_data="none"))
    else:
        for c in valid_players:
            kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"set_{idx}_{c['name']}"))
    
    kb.add(types.InlineKeyboardButton("🚫 Прибрати", callback_data=f"set_{idx}_none"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_squad"))
    
    bot.edit_message_text(f"Оберіть гравця на позицію {required_pos}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_squad")
def back_to_sq(call):
    bot.edit_message_text("📋 **Твій склад:**", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(call.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_player_to_squad(call):
    parts = call.data.split("_"); idx, name, uid = int(parts[1]), parts[2], str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        # Перевірка на дублікат в іншому слоті (хоча з фільтром по позиції це менш імовірно)
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Цей гравець вже в складі!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else:
        user_squads[uid][idx] = None
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Оновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- [8] АДМІН-ПАНЕЛЬ (ЗМІНА КАРТКИ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel(m):
    if is_admin(m.from_user):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "📝 Изменить карту")
        kb.row("🗑 Удалить карту", "🚫 Забанить")
        kb.row("✅ Разбанить", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Управление:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def edit_card_start(m):
    if not is_admin(m.from_user): return
    if not cards: return bot.send_message(m.chat.id, "Карт немає.")
    kb = types.InlineKeyboardMarkup()
    for c in cards: kb.add(types.InlineKeyboardButton(c['name'], callback_data=f"select_edit_{c['name']}"))
    bot.send_message(m.chat.id, "Яку карту змінити?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("select_edit_"))
def edit_card_menu(call):
    name = call.data.split("_")[2]
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Назва", callback_data=f"prop_name_{name}"))
    kb.add(types.InlineKeyboardButton("Рейтинг", callback_data=f"prop_star_{name}"))
    kb.add(types.InlineKeyboardButton("Фото", callback_data=f"prop_photo_{name}"))
    bot.edit_message_text(f"Що хочете змінити у {name}?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("prop_"))
def admin_edit_input_step(call):
    mode, name = call.data.split("_")[1], call.data.split("_")[2]
    prompts = {"name": "нову Назву", "star": "новий Рейтинг (1-5)", "photo": "нове Фото"}
    msg = bot.send_message(call.message.chat.id, f"Відправте {prompts[mode]} для {name}:")
    bot.register_next_step_handler(msg, admin_edit_save, mode, name)

def admin_edit_save(m, mode, name):
    for c in cards:
        if c['name'] == name:
            if mode == "name": c['name'] = m.text
            elif mode == "star":
                try: c['stars'] = int(m.text)
                except: return bot.send_message(m.chat.id, "Потрібне число!")
            elif mode == "photo":
                if m.photo: c['photo'] = m.photo[-1].file_id
                else: return bot.send_message(m.chat.id, "Це не фото!")
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Змінено!", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_card_1(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Ім'я гравця:")
    bot.register_next_step_handler(msg, add_card_2)

def add_card_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиція ({', '.join([v['code'] for v in POSITIONS_DATA.values()])}):")
    bot.register_next_step_handler(msg, add_card_3, name)

def add_card_3(m, name):
    pos = m.text.upper().strip() # Автоматично у верхній регістр для бази
    msg = bot.send_message(m.chat.id, "Зірки (1-5):")
    bot.register_next_step_handler(msg, add_card_4, name, pos)

def add_card_4(m, name, pos):
    try:
        s = int(m.text)
        msg = bot.send_message(m.chat.id, "Фото картки:")
        bot.register_next_step_handler(msg, add_card_fin, name, pos, s)
    except: bot.send_message(m.chat.id, "Введіть число!")

def add_card_fin(m, name, pos, stars):
    if not m.photo: return bot.send_message(m.chat.id, "Це не фото!")
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Картка додана!", reply_markup=main_kb(m.from_user.id))

# --- ПВП АРЕНА ТА ІНШЕ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"view_{i}"))
    bot.send_message(m.chat.id, "🗂 **Твоя колекція:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_"))
def view_coll_stars(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "Немає таких карт!", show_alert=True)
    txt = f"🗂 **Карти {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_main(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎲 Рандом", callback_data="arena_random"),
           types.InlineKeyboardButton("👤 По юзеру", callback_data="arena_by_user"))
    bot.send_message(m.chat.id, "🏟 **ПВП Арена:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_"))
def arena_cb(call):
    uid = str(call.from_user.id)
    if "random" in call.data:
        opps = [u for u in users_data if u != uid and get_power(u) > 0]
        if opps: start_battle(call.message.chat.id, uid, random.choice(opps))
        else: bot.answer_callback_query(call.id, "Немає суперників!", show_alert=True)
    else:
        msg = bot.send_message(call.message.chat.id, "Введіть юзернейм (без @):")
        bot.register_next_step_handler(msg, search_user_arena)
    bot.answer_callback_query(call.id)

def search_user_arena(m):
    target = m.text.replace("@", "").lower().strip()
    found = next((u for u, d in users_data.items() if d.get('username') == target), None)
    if found: start_battle(m.chat.id, str(m.from_user.id), found)
    else: bot.send_message(m.chat.id, "❌ Гравця не знайдено.")

def start_battle(chat_id, p1_id, p2_id):
    p1_atk, p2_atk = get_power(p1_id), get_power(p2_id)
    if p1_atk == 0 or p2_atk == 0: return bot.send_message(chat_id, "❌ Склади порожні!")
    total = p1_atk + p2_atk
    chance1 = (p1_atk / total) * 100
    res = random.uniform(0, 100)
    bot.send_message(chat_id, f"🏟 **БІЙ:** {users_data[p1_id]['nick']} ({p1_atk}) vs {users_data[p2_id]['nick']} ({p2_atk})")
    time.sleep(1)
    if res <= chance1: winner, prize = p1_id, int(p2_atk * 0.3)
    else: winner, prize = p2_id, int(p1_atk * 0.3)
    users_data[winner]['score'] += prize
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Переміг **{users_data[winner]['nick']}**!\n💰 Нагорода: `+{prize:,}`.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = str(m.from_user.id)
    d = users_data.get(uid, {"nick": "Player", "score": 0, "username": "n/a"})
    bot.send_message(m.chat.id, f"👤 **Профіль:**\n\nНик: **{d['nick']}**\nЮзер: @{d['username']}\n💰 Очки: `{d['score']:,}`\n🆔 `{uid}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m): bot.send_message(m.chat.id, "⚽️ Головне меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
