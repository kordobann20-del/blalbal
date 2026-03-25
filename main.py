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
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json',
    'bans': 'bans.json'
}

COOLDOWN_ROLL = 10800
COOLDOWN_NICK = 1209600

STATS = {
    1: {"chance": 50, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 12, "score": 5000, "atk": 600},
    4: {"chance": 6, "score": 8000, "atk": 1000},
    5: {"chance": 2, "score": 10000, "atk": 1500}
}

POSITIONS_LIST = ["🧤 ГК", "🛡 ЛЗ", "🛡 ПЗ", "👟 ЦП", "⚡️ ЛВ", "⚡️ ПВ", "🎯 КФ"]

# --- [2] РАБОТА С БД ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key in ['cards', 'bans'] else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return [] if key in ['cards', 'bans'] else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
ban_list = load_db('bans') # Список забаненных юзернеймов
cooldowns = {} 
challenges = {}

# --- [3] ПРОВЕРКА БАНА ---
def is_banned(user):
    uname = user.username.lower() if user.username else None
    return uname in ban_list if uname else False

# --- [4] ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_power(uid):
    sq = user_squads.get(str(uid), [None]*7)
    return sum(STATS[p['stars']]['atk'] for p in sq if p)

def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    
    user_info = bot.get_chat(uid)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

# --- [5] РЕГИСТРАЦИЯ И ЗАЩИТА ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def banned_msg(m):
    bot.send_message(m.chat.id, "🚫 **Вы заблокированы в боте.**", parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_command(message):
    uid = str(message.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(message.chat.id, "👋 **Добро пожаловать!**\n\nВведите ваш **игровой ник**:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, register_user_nick)
    else:
        bot.send_message(message.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(uid))

def register_user_nick(message):
    uid = str(message.from_user.id)
    nick = message.text
    if not nick:
        msg = bot.send_message(message.chat.id, "❌ Введите ник!")
        return bot.register_next_step_handler(msg, register_user_nick)
    users_data[uid] = {"nick": nick, "score": 0, "last_nick_change": 0}
    save_db(users_data, 'users')
    bot.send_message(message.chat.id, f"✅ Профиль создан!", reply_markup=main_kb(uid))

# --- [6] КРУТКА КАРТ (ОБНОВЛЕННЫЙ ДИЗАЙН) ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(message):
    uid = str(message.from_user.id)
    now = time.time()
    user_info = bot.get_chat(uid)
    is_admin = user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]

    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL and not is_admin:
        left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
        return bot.send_message(message.chat.id, f"⏳ КД: `{left // 3600}ч {(left % 3600) // 60}м`", parse_mode="Markdown")

    if not cards: return bot.send_message(message.chat.id, "❌ Нет карт в базе.")

    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc: stars = s; break

    pool = [c for c in cards if c['stars'] == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    
    base_pts = STATS[won['stars']]['score']
    if is_dub:
        final_pts = int(base_pts * 0.3)
        status = "ПОВТОРКА"
    else:
        final_pts = base_pts
        status = "НОВАЯ КАРТА"
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    users_data[uid]['score'] += final_pts
    save_db(users_data, 'users')

    # ДИЗАЙН ПО ВАШЕМУ ШАБЛОНУ (ЖИРНЫЙ ШРИФТ)
    cap = (
        f"⚽️ *{won['name']}* (\"{status}\")\n\n"
        f"🎯 **Позиция:** {won['pos']}\n"
        f"📊 **Рейтинг:** {'⭐' * won['stars']}\n\n"
        f"💠 **Очки:** +{final_pts:,} | {users_data[uid]['score']:,}"
    )
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [7] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_menu(m):
    uid = str(m.from_user.id)
    if get_power(uid) == 0:
        return bot.send_message(m.chat.id, "❌ Сначала добавь игроков в **📋 Состав**!")
    
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎲 Рандом", callback_data="arena_random"),
           types.InlineKeyboardButton("🆔 По ID", callback_data="arena_by_id"))
    
    if m.reply_to_message and str(m.reply_to_message.from_user.id) in users_data:
        target_id = str(m.reply_to_message.from_user.id)
        if target_id != uid:
            kb.add(types.InlineKeyboardButton(f"⚔️ Вызвать {users_data[target_id]['nick']}", callback_data=f"challenge_{target_id}"))

    bot.send_message(m.chat.id, "🏟 **ПВП Арена**\nВыбери противника:", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_"))
def arena_actions(call):
    uid = str(call.from_user.id)
    action = call.data.split("_")[1]
    if action == "random":
        opps = [u for u in users_data.keys() if u != uid and get_power(u) > 0]
        if not opps: return bot.answer_callback_query(call.id, "Нет игроков!", show_alert=True)
        start_battle(call.message.chat.id, uid, random.choice(opps))
    elif action == "by_id":
        msg = bot.send_message(call.message.chat.id, "Введите ID игрока для вызова:")
        bot.register_next_step_handler(msg, lambda m: start_battle(m.chat.id, uid, m.text) if m.text in users_data else bot.send_message(m.chat.id, "❌ Не найден."))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("challenge_"))
def chall_init(call):
    uid, opp_id = str(call.from_user.id), call.data.split("_")[1]
    challenges[opp_id] = {"attacker": uid, "chat_id": call.message.chat.id, "time": time.time()}
    bot.send_message(call.message.chat.id, f"⚔️ {users_data[uid]['nick']} бросил вызов {users_data[opp_id]['nick']}!\nОтветь на это сообщение: **Принять**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def chall_accept(m):
    uid = str(m.from_user.id)
    if uid in challenges:
        start_battle(challenges[uid]['chat_id'], challenges[uid]['attacker'], uid)
        del challenges[uid]

def start_battle(chat_id, p1_id, p2_id):
    p1_p, p2_p = get_power(p1_id), get_power(p2_id)
    p1_n, p2_n = users_data[p1_id]['nick'], users_data[p2_id]['nick']
    bot.send_message(chat_id, f"🏟 **МАТЧ:** {p1_n} ({p1_p}) vs {p2_n} ({p2_p})")
    time.sleep(1)
    if p1_p > p2_p: winner_id, winner_nick, prize = p1_id, p1_n, int(p2_p * 0.3)
    elif p2_p > p1_p: winner_id, winner_nick, prize = p2_id, p2_n, int(p1_p * 0.3)
    else: return bot.send_message(chat_id, "🤝 Ничья!")
    users_data[winner_id]['score'] += prize
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Победил **{winner_nick}**!\n💰 Награда: **+{prize:,} очков**", parse_mode="Markdown")

# --- [8] АДМИНКА (БАН ПО ЮЗЕРНЕЙМУ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    user_info = bot.get_chat(m.from_user.id)
    if user_info.username and user_info.username.lower() in [a.lower() for a in ADMINS]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "🗑 Удалить карту")
        kb.row("🚫 Забанить", "✅ Разбанить")
        kb.row("🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Админка:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def adm_ban(m):
    msg = bot.send_message(m.chat.id, "Введите **username** игрока для бана (без @):")
    bot.register_next_step_handler(msg, lambda ms: ban_user(ms, True))

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def adm_unban(m):
    msg = bot.send_message(m.chat.id, "Введите **username** игрока для разбана (без @):")
    bot.register_next_step_handler(msg, lambda ms: ban_user(ms, False))

def ban_user(m, status):
    target = m.text.replace("@", "").lower().strip()
    if status:
        if target not in ban_list: ban_list.append(target)
        txt = f"🚫 Пользователь `{target}` забанен!"
    else:
        if target in ban_list: ban_list.remove(target)
        txt = f"✅ Пользователь `{target}` разбанен!"
    save_db(ban_list, 'bans')
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_add_1(m):
    msg = bot.send_message(m.chat.id, "Имя игрока:")
    bot.register_next_step_handler(msg, adm_add_2)

def adm_add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиция {name}:")
    bot.register_next_step_handler(msg, adm_add_3, name)

def adm_add_3(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Звезды (1-5):")
    bot.register_next_step_handler(msg, adm_add_4, name, pos)

def adm_add_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправь фото:")
        bot.register_next_step_handler(msg, adm_add_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "Нужно число!")

def adm_add_fin(m, name, pos, stars):
    if not m.photo: return
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта **{name}** успешно добавлена!", reply_markup=main_kb(m.from_user.id))

# --- [9] ОСТАЛЬНОЕ ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def prof(m):
    uid = str(m.from_user.id)
    d = users_data.get(uid, {"nick": "Игрок", "score": 0})
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Изменить ник", callback_data="change_nick"))
    bot.send_message(m.chat.id, f"👤 **Профиль:**\nНик: {d['nick']}\nОчки: {d['score']:,}\nID: `{uid}`", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def sq_menu(m):
    bot.send_message(m.chat.id, "📋 **Твой состав:**", reply_markup=get_sq_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"v_{i}"))
    bot.send_message(m.chat.id, "🗂 **Коллекция:**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def v_coll(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "Пусто!", show_alert=True)
    bot.send_message(call.message.chat.id, f"🗂 **{s}⭐:**\n" + "\n".join([f"• {c['name']}" for c in my]))

def get_sq_kb(uid):
    kb = types.InlineKeyboardMarkup(); sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        n = sq[i]['name'] if sq[i] else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {n}", callback_data=f"slot_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def s_pick(call):
    idx, uid = int(call.data.split("_")[1]), str(call.from_user.id)
    coll = user_colls.get(uid, [])
    kb = types.InlineKeyboardMarkup()
    for card in coll: kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"set_{idx}_{card['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text("Выбери игрока:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def s_save(call):
    parts = call.data.split("_"); idx, name, uid = int(parts[1]), parts[2], str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    if name != "none":
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else: user_squads[uid][idx] = None
    save_db(user_squads, 'squads'); bot.edit_message_text("✅ Готово!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_v(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП:**\n\n"
    for i, (u, d) in enumerate(top, 1): txt += f"{i}. {d['nick']} — {d['score']:,}\n"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back(m): bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
