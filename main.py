import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users.json'
}

# Очки и статы по звездам
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50, "score": 1000},
    2: {"hp": 3500, "atk": 1400, "chance": 30, "score": 3000},
    3: {"hp": 6000, "atk": 2500, "chance": 12, "score": 5000},
    4: {"hp": 10000, "atk": 4000, "chance": 6, "score": 8000},
    5: {"hp": 14000, "atk": 6000, "chance": 2, "score": 10000}
}

POSITIONS_LIST = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- СИСТЕМА БД ---

def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key == 'cards' else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return [] if key == 'cards' else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

def update_user_record(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        uname_lower = uname.lower()
        if registered_users.get(uname_lower) != uid:
            registered_users[uname_lower] = uid
            save_db(registered_users, 'users')

# --- КЛАВИАТУРЫ ---

def main_kb(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Удалить карту")
    markup.row("Назад в меню")
    return markup

# --- КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    update_user_record(message)
    welcome_text = (
        "🔥 **Добро пожаловать в FootCard — место, где рождаются легенды.**\n\n"
        "Здесь каждая карта — шанс поймать великого.\n\n"
        "🃏 **Твоя первая карточка уже ждёт. Забери её и начни путь чемпиона.**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_kb(message.from_user.username), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_cmd(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_kb(message.from_user.username))

# --- КРУТКА ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_cmd(message):
    global cards, user_colls
    update_user_record(message)
    uid = str(message.from_user.id)
    now = time.time()

    if not cards:
        return bot.send_message(message.chat.id, "❌ Карт пока нет.")

    if uid in cooldowns and now - cooldowns[uid] < 300 and message.from_user.username not in ADMINS:
        left = int(300 - (now - cooldowns[uid]))
        return bot.send_message(message.chat.id, f"⏳ Подожди {left // 60} мин. {left % 60} сек.")

    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc:
            stars = s
            break

    pool = [c for c in cards if c.get('stars', 1) == stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now

    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    status_label = "повторка" if is_dub else "новая карта"
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    cap = (
        f"⚽️ **{won['name']} ({status_label})**\n\n"
        f"Позиция: {won.get('pos', 'Не указана')}\n"
        f"Рейтинг: {'⭐' * won['stars']}\n\n"
        f"Очки: {STATS[won['stars']]['score']}"
    )
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- СОСТАВ (С ЗАЩИТОЙ ОТ ДУБЛЕЙ) ---

def get_sq_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(uid, [None]*7)
    for i in range(7):
        n = sq[i]['name'] if (i < len(sq) and sq[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS_LIST[i]}: {n}", callback_data=f"sl_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_view(m):
    bot.send_message(m.chat.id, "⚔️ Твой состав:", reply_markup=get_sq_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sl_"))
def slot_sel(call):
    idx = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: return bot.answer_callback_query(call.id, "Коллекция пуста!")
    
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"st_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"st_{idx}_none"))
    bot.edit_message_text(f"Выберите игрока на позицию {POSITIONS_LIST[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("st_"))
def slot_save(call):
    p = call.data.split("_"); idx, name = int(p[1]), p[2]; uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        # Проверка: не стоит ли этот игрок уже на другой позиции
        current_squad_names = [s['name'] for s in user_squads[uid] if s is not None]
        # Если мы меняем игрока на того же самого (на той же позиции), это ок. 
        # Если игрок уже есть на ДРУГОЙ позиции - запрет.
        if name in current_squad_names:
            # Проверяем, не тот ли это игрок, который уже стоит именно в этом слоте
            if not (user_squads[uid][idx] and user_squads[uid][idx]['name'] == name):
                return bot.answer_callback_query(call.id, "❌ Этот игрок уже есть в составе!", show_alert=True)

        user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None)
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- АДМИНКА ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm_menu(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(m.chat.id, "Админка:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "Добавить карту")
def adm_add_1(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Имя игрока:")
        bot.register_next_step_handler(msg, adm_add_2)

def adm_add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиция для {name}:")
    bot.register_next_step_handler(msg, adm_add_3, name)

def adm_add_3(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, f"Рейтинг (1-5 звезд) для {name}:")
    bot.register_next_step_handler(msg, adm_add_4, name, pos)

def adm_add_4(m, name, pos):
    try:
        s = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправь фото для {name}:")
        bot.register_next_step_handler(msg, adm_add_fin, name, pos, s)
    except: bot.send_message(m.chat.id, "Нужно число 1-5!")

def adm_add_fin(m, name, pos, s):
    if not m.photo: return bot.send_message(m.chat.id, "Нужно фото!")
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'pos': pos, 'stars': s, 'photo': m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Игрок {name} добавлен!", reply_markup=admin_kb())

# --- ОСТАЛЬНОЕ (АРЕНА И КОЛЛЕКЦИЯ) ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def arena_info(m):
    bot.reply_to(m, "⚔️ Напиши `Арена @username`.")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_call(m):
    uid = str(m.from_user.id)
    parts = m.text.split()
    if len(parts) < 2: return
    tid = registered_users.get(parts[1].replace("@", "").lower())
    if not tid or uid == tid: return bot.send_message(m.chat.id, "❌ Ошибка игрока.")
    arena_reqs[tid] = {"att_id": uid, "att_name": m.from_user.first_name}
    bot.send_message(m.chat.id, f"⚔️ {m.from_user.first_name} вызвал {parts[1]}! Напиши **Принять**.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_acc(m):
    did = str(m.from_user.id)
    if did not in arena_reqs: return
    req = arena_reqs.pop(did); aid = req["att_id"]
    def get_p(u):
        sq = user_squads.get(str(u), [None]*7)
        h, a = 0, 0
        for c in sq:
            if c:
                s = c.get('stars', 1)
                h += STATS[s]['hp']; a += STATS[s]['atk']
        return h, a
    h1, a1 = get_p(aid); h2, a2 = get_p(did)
    if h1 == 0 or h2 == 0: return bot.send_message(m.chat.id, "Пустой состав!")
    win = req["att_name"] if (h1+a1) > (h2+a2) else m.from_user.first_name
    bot.send_message(m.chat.id, f"🏆 Победитель: {win}")

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⭐", callback_data="v_1"), types.InlineKeyboardButton("⭐⭐", callback_data="v_2"))
    kb.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="v_3"), types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="v_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="v_5"))
    bot.send_message(m.chat.id, "Редкость:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def coll_view(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == s]
    if not my: return bot.answer_callback_query(call.id, "Нет карт!")
    txt = f"🗂 **Карты {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c.get('pos', '???')})" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def adm_del(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Имя для удаления:")
        bot.register_next_step_handler(msg, lambda ms: save_db([c for c in cards if c['name'].lower() != ms.text.lower()], 'cards'))

bot.infinity_polling()
