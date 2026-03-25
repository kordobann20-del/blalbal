import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ ---
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
POSITIONS_LIST = ["🧤 ГК", "🛡 ЛЗ", "🛡 ПЗ", "👟 ЦП", "⚡️ ЛВ", "⚡️ ПВ", "🎯 КФ"]

# --- [2] РАБОТА С БД ---
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

# --- [3] ФУНКЦИИ ---
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
    u_info = bot.get_chat(uid)
    if u_info.username and u_info.username.lower() in [a.lower() for a in ADMINS]: markup.add("🛠 Админ-панель")
    return markup

# --- [4] БЛОКИРОВКА И СТАРТ ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def check_ban(m): bot.send_message(m.chat.id, "🚫 Доступ ограничен.")

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(m.chat.id, "⚽️ Введите ваш игровой ник:")
        bot.register_next_step_handler(msg, reg_nick)
    else: bot.send_message(m.chat.id, "⚽️ Меню:", reply_markup=main_kb(uid))

def reg_nick(m):
    uid = str(m.from_user.id)
    users_data[uid] = {"nick": m.text, "score": 0, "last_nick_change": 0, "username": (m.from_user.username.lower() if m.from_user.username else None)}
    save_db(users_data, 'users'); bot.send_message(m.chat.id, "✅ Готово!", reply_markup=main_kb(uid))

# --- [5] КРУТКА ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(m):
    uid = str(m.from_user.id)
    if uid in cooldowns and time.time() - cooldowns[uid] < COOLDOWN_ROLL:
        return bot.send_message(m.chat.id, "⏳ Еще не время.")
    
    stars = random.choices(list(STATS.keys()), weights=[s['chance'] for s in STATS.values()])[0]
    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = time.time()
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    status = "ПОВТОРКА" if is_dub else "НОВАЯ КАРТА"
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub: user_colls[uid].append(won); save_db(user_colls, 'colls')
    users_data[uid]['score'] += pts; save_db(users_data, 'users')
    
    cap = f"⚽️ *{won['name']}* (\"{status}\")\n\n🎯 **Позиция:** {won['pos']}\n📊 **Рейтинг:** {'⭐'*won['stars']}\n\n💠 **Очки:** +{pts:,} | {users_data[uid]['score']:,}"
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] ПВП АРЕНА (НОВАЯ ЛОГИКА) ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "арена")
def group_call(m):
    if not m.reply_to_message: return
    atk_id, def_id = str(m.from_user.id), str(m.reply_to_message.from_user.id)
    if def_id not in users_data: return bot.reply_to(m, "❌ Игрок не зарегистрирован.")
    challenges[def_id] = {"attacker": atk_id, "chat_id": m.chat.id, "time": time.time()}
    bot.send_message(m.chat.id, f"⚔️ {users_data[atk_id]['nick']} вызывает {users_data[def_id]['nick']}!\nОтветь: **Принять**")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def accept(m):
    uid = str(m.from_user.id)
    if uid in challenges:
        start_battle(challenges[uid]['chat_id'], challenges[uid]['attacker'], uid)
        del challenges[uid]

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_m(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎲 Рандом", callback_data="arena_random"),
           types.InlineKeyboardButton("👤 По юзернейму", callback_data="arena_by_user"))
    bot.send_message(m.chat.id, "🏟 ПВП Арена:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_"))
def arena_cb(call):
    if "random" in call.data:
        opps = [u for u in users_data if u != str(call.from_user.id) and get_power(u) > 0]
        if opps: start_battle(call.message.chat.id, str(call.from_user.id), random.choice(opps))
    else:
        msg = bot.send_message(call.message.chat.id, "Введите юзернейм (без @):")
        bot.register_next_step_handler(msg, search_user)

def search_user(m):
    target = m.text.replace("@", "").lower()
    found = next((u for u, d in users_data.items() if d.get('username') == target), None)
    if found: start_battle(m.chat.id, str(m.from_user.id), found)
    else: bot.send_message(m.chat.id, "❌ Не найден.")

def start_battle(chat_id, p1_id, p2_id):
    p1_atk, p2_atk = get_power(p1_id), get_power(p2_id)
    if p1_atk == 0 or p2_atk == 0: return bot.send_message(chat_id, "❌ У одного из игроков пустой состав!")
    
    total = p1_atk + p2_atk
    chance1 = (p1_atk / total) * 100
    res = random.uniform(0, 100)
    
    bot.send_message(chat_id, f"🏟 **МАТЧ:** {users_data[p1_id]['nick']} ({p1_atk}) vs {users_data[p2_id]['nick']} ({p2_atk})")
    time.sleep(1)
    
    if res <= chance1:
        win_id, prize = p1_id, int(p2_atk * 0.3)
        bot.send_message(chat_id, f"🏆 Победил {users_data[win_id]['nick']}!\n💰 Награда: +{prize}")
        users_data[win_id]['score'] += prize; save_db(users_data, 'users')
    else:
        win_id, prize = p2_id, int(p1_atk * 0.3)
        bot.send_message(chat_id, f"🏆 Победил {users_data[win_id]['nick']}!\n💰 Награда: +{prize}")
        users_data[win_id]['score'] += prize; save_db(users_data, 'users')

# --- [7] СОСТАВ (ПРОВЕРКА НА УНИКАЛЬНОСТЬ) ---
def get_sq_kb(uid):
    kb = types.InlineKeyboardMarkup(); sq = user_squads.get(str(uid), [None]*7)
    for i, p in enumerate(sq):
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {p['name'] if p else '❌'}", callback_data=f"slot_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_p(call):
    p = call.data.split("_"); idx, name, uid = int(p[1]), p[2], str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        # Проверка: нет ли этого игрока на другой позиции
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже на другой позиции!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else: user_squads[uid][idx] = None
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- [8] АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    u = bot.get_chat(m.from_user.id)
    if u.username and u.username.lower() in [a.lower() for a in ADMINS]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "📝 Изменить карту")
        kb.row("🚫 Забанить", "✅ Разбанить")
        kb.add("🏠 Назад в меню")
        bot.send_message(m.chat.id, "Управление:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def edit_card_start(m):
    kb = types.InlineKeyboardMarkup()
    for c in cards: kb.add(types.InlineKeyboardButton(c['name'], callback_data=f"edit_{c['name']}"))
    bot.send_message(m.chat.id, "Выберите карту:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def edit_choice(call):
    name = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введите новые данные для {name} через запятую (Позиция, Звезды):")
    bot.register_next_step_handler(msg, edit_fin, name)

def edit_fin(m, name):
    try:
        new_pos, new_stars = m.text.split(",")
        for c in cards:
            if c['name'] == name:
                c['pos'], c['stars'] = new_pos.strip(), int(new_stars)
        save_db(cards, 'cards'); bot.send_message(m.chat.id, "✅ Изменено!")
    except: bot.send_message(m.chat.id, "❌ Ошибка формата.")

# --- ОСТАЛЬНОЕ (Профиль, Коллекция, Бан) ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def prof(m):
    d = users_data.get(str(m.from_user.id), {"nick": "Player", "score": 0})
    bot.send_message(m.chat.id, f"👤 {d['nick']}\n💰 Очки: {d['score']:,}\n🆔 `{m.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def sq_m(m): bot.send_message(m.chat.id, "📋 Состав:", reply_markup=get_sq_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_s(call):
    idx, uid = int(call.data.split("_")[1]), str(call.from_user.id)
    kb = types.InlineKeyboardMarkup()
    for c in user_colls.get(uid, []):
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"set_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text("Выбери игрока:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def ban_start(m):
    msg = bot.send_message(m.chat.id, "Юзернейм для бана:")
    bot.register_next_step_handler(msg, lambda ms: (ban_list.append(ms.text.lower().replace("@","")), save_db(ban_list,'bans'), bot.send_message(ms.chat.id,"🚫 Бан")))

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_c(m):
    msg = bot.send_message(m.chat.id, "Имя:")
    bot.register_next_step_handler(msg, lambda ms: bot.register_next_step_handler(bot.send_message(ms.chat.id,"Поз:"), lambda m2: bot.register_next_step_handler(bot.send_message(m2.chat.id,"⭐ (1-5):"), lambda m3: bot.register_next_step_handler(bot.send_message(m3.chat.id,"Фото:"), lambda m4: (cards.append({"name":ms.text,"pos":m2.text,"stars":int(m3.text),"photo":m4.photo[-1].file_id}), save_db(cards,'cards'), bot.send_message(m4.chat.id,"✅ Добавлен"))))))

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back(m): bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
