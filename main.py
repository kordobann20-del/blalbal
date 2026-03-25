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

# --- [3] ФУНКЦИИ ПРОВЕРКИ ---
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
    if is_admin(bot.get_chat(uid)): markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРАБОТКА КОМАНД ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def check_ban(m): bot.send_message(m.chat.id, "🚫 Доступ ограничен.")

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        msg = bot.send_message(m.chat.id, "⚽️ Введите ваш игровой ник:")
        bot.register_next_step_handler(msg, reg_nick)
    else: bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(uid))

def reg_nick(m):
    uid = str(m.from_user.id)
    users_data[uid] = {"nick": m.text, "score": 0, "username": (m.from_user.username.lower() if m.from_user.username else None)}
    save_db(users_data, 'users'); bot.send_message(m.chat.id, "✅ Готово!", reply_markup=main_kb(uid))

# --- [5] КРУТКА (БЕЗ КД ДЛЯ АДМИНОВ) ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    # Проверка КД (Админы пропускаются)
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
    status = "Повторка.." if is_dub else "Новая карта!"
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub: 
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
        
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    cap = (f"⚽️ *{won['name']}* (\"{status}\")\n\n"
           f"🎯 *Позиция:* {won['pos']}\n"
           f"📊 *Рейтинг:* {'⭐'*won['stars']}\n\n"
           f"💠 *Очки:* +{pts:,} | {users_data[uid]['score']:,}")
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [6] КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6): kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"view_{i}"))
    bot.send_message(m.chat.id, "🗂 **Твоя коллекция по рейтингу:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_"))
def view_coll_stars(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c['stars'] == s]
    if not my: return bot.answer_callback_query(call.id, "У вас пока нет таких карт!", show_alert=True)
    txt = f"🗂 **Карты {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [7] ТОП ОЧКОВ ---
@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_scores(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (u, d) in enumerate(top, 1):
        txt += f"{i}. **{d['nick']}** — `{d['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# --- [8] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "арена")
def group_call(m):
    if not m.reply_to_message: return
    atk_id, def_id = str(m.from_user.id), str(m.reply_to_message.from_user.id)
    if def_id not in users_data: return bot.reply_to(m, "❌ Соперник не зарегистрирован.")
    challenges[def_id] = {"attacker": atk_id, "chat_id": m.chat.id, "time": time.time()}
    bot.send_message(m.chat.id, f"⚔️ {users_data[atk_id]['nick']} вызывает {users_data[def_id]['nick']}!\nОтветь: **Принять**")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def accept_battle(m):
    uid = str(m.from_user.id)
    if uid in challenges:
        start_battle(challenges[uid]['chat_id'], challenges[uid]['attacker'], uid)
        del challenges[uid]

@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def arena_main(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎲 Рандом", callback_data="arena_random"),
           types.InlineKeyboardButton("👤 По юзернейму", callback_data="arena_by_user"))
    bot.send_message(m.chat.id, "🏟 **ПВП Арена:**", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_"))
def arena_cb(call):
    uid = str(call.from_user.id)
    if "random" in call.data:
        opps = [u for u in users_data if u != uid and get_power(u) > 0]
        if opps: start_battle(call.message.chat.id, uid, random.choice(opps))
        else: bot.answer_callback_query(call.id, "Нет соперников!", show_alert=True)
    else:
        msg = bot.send_message(call.message.chat.id, "Введите юзернейм игрока (без @):")
        bot.register_next_step_handler(msg, search_user_arena)
    bot.answer_callback_query(call.id)

def search_user_arena(m):
    target = m.text.replace("@", "").lower().strip()
    found = next((u for u, d in users_data.items() if d.get('username') == target), None)
    if found: start_battle(m.chat.id, str(m.from_user.id), found)
    else: bot.send_message(m.chat.id, "❌ Игрок не найден.")

def start_battle(chat_id, p1_id, p2_id):
    p1_atk, p2_atk = get_power(p1_id), get_power(p2_id)
    if p1_atk == 0 or p2_atk == 0: return bot.send_message(chat_id, "❌ Составы пусты!")
    
    total = p1_atk + p2_atk
    chance1 = (p1_atk / total) * 100
    res = random.uniform(0, 100)
    
    bot.send_message(chat_id, f"🏟 **БОЙ:** {users_data[p1_id]['nick']} ({p1_atk}) vs {users_data[p2_id]['nick']} ({p2_atk})")
    time.sleep(1)
    
    if res <= chance1:
        winner, prize = p1_id, int(p2_atk * 0.3)
    else:
        winner, prize = p2_id, int(p1_atk * 0.3)

    users_data[winner]['score'] += prize
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Победил **{users_data[winner]['nick']}**!\n💰 Награда: `+{prize:,}` очков.", parse_mode="Markdown")

# --- [9] СОСТАВ ---
def get_squad_kb(uid):
    kb = types.InlineKeyboardMarkup(); sq = user_squads.get(str(uid), [None]*7)
    for i, p in enumerate(sq):
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {p['name'] if p else '❌'}", callback_data=f"slot_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m): bot.send_message(m.chat.id, "📋 **Твой состав:**", reply_markup=get_squad_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def slot_select(call):
    idx, uid = int(call.data.split("_")[1]), str(call.from_user.id)
    kb = types.InlineKeyboardMarkup()
    for c in user_colls.get(uid, []):
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"set_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"set_{idx}_none"))
    bot.edit_message_text("Выбери игрока в состав:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_player_to_squad(call):
    parts = call.data.split("_"); idx, name, uid = int(parts[1]), parts[2], str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name != "none":
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже на другой позиции!", show_alert=True)
        user_squads[uid][idx] = next(c for c in user_colls[uid] if c['name'] == name)
    else: user_squads[uid][idx] = None
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- [10] АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel(m):
    if is_admin(m.from_user):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "📝 Изменить карту")
        kb.row("🗑 Удалить карту", "🚫 Забанить")
        kb.row("✅ Разбанить", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Управление игрой:**", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def adm_delete_card_start(m):
    if not is_admin(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    for c in cards: kb.add(types.InlineKeyboardButton(f"❌ {c['name']}", callback_data=f"del_{c['name']}"))
    bot.send_message(m.chat.id, "Выберите карту для удаления:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def adm_delete_card_fin(call):
    name = call.data.split("_")[1]; global cards
    cards = [c for c in cards if c['name'] != name]
    save_db(cards, 'cards')
    bot.edit_message_text(f"✅ Карта {name} удалена!", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_card_1(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Введите имя игрока:")
    bot.register_next_step_handler(msg, add_card_2)

def add_card_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиция для {name}:")
    bot.register_next_step_handler(msg, add_card_3, name)

def add_card_3(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Звезды (1-5):")
    bot.register_next_step_handler(msg, add_card_4, name, pos)

def add_card_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте фото карты:")
        bot.register_next_step_handler(msg, add_card_fin, name, pos, stars)
    except: bot.send_message(m.chat.id, "❌ Ошибка: введите число (1-5)")

def add_card_fin(m, name, pos, stars):
    if not m.photo: return bot.send_message(m.chat.id, "❌ Это не фото!")
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта **{name}** успешно добавлена!", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def edit_card_start(m):
    if not is_admin(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    for c in cards: kb.add(types.InlineKeyboardButton(c['name'], callback_data=f"edit_{c['name']}"))
    bot.send_message(m.chat.id, "Выберите карту для изменения:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def edit_card_step(call):
    name = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введите (Позиция, Звезды) через запятую:")
    bot.register_next_step_handler(msg, edit_card_fin, name)

def edit_card_fin(m, name):
    try:
        new_pos, new_stars = m.text.split(",")
        for c in cards:
            if c['name'] == name:
                c['pos'], c['stars'] = new_pos.strip(), int(new_stars)
        save_db(cards, 'cards'); bot.send_message(m.chat.id, "✅ Карта изменена!")
    except: bot.send_message(m.chat.id, "❌ Формат: Позиция, 5")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = str(m.from_user.id)
    d = users_data.get(uid, {"nick": "Player", "score": 0})
    bot.send_message(m.chat.id, f"👤 *Профиль:*\n\n🪪 *Ник:* **{d['nick']}**\n💰 *Очки:* `{d['score']:,}`\n🆔 `{uid}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def ban_start(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Юзернейм для бана (без @):")
    bot.register_next_step_handler(msg, lambda ms: (ban_list.append(ms.text.lower()), save_db(ban_list,'bans'), bot.send_message(ms.chat.id,"🚫 Забанен")))

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def unban_start(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Юзернейм для разбана:")
    bot.register_next_step_handler(msg, lambda ms: (ban_list.remove(ms.text.lower()) if ms.text.lower() in ban_list else None, save_db(ban_list,'bans'), bot.send_message(ms.chat.id,"✅ Разбанен")))

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m): bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(m.from_user.id))

bot.infinity_polling()
