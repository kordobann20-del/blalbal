import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
# Обновленный список администраторов (без @)
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users.json'
}

# Характеристики по редкости
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

POSITIONS = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- СИСТЕМА СОХРАНЕНИЯ ---

def load_db(key):
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
    markup.row("Состав", "Арена") # Кнопка Премиум удалена
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Изменить карту")
    markup.row("Удалить карту", "Назад в меню")
    return markup

# --- ОСНОВНЫЕ КОМАНДЫ ---

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

# --- КРУТКА КАРТ (ROLL) ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_cmd(message):
    global cards, user_colls
    update_user_record(message)
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        return bot.send_message(message.chat.id, "❌ Карт еще нет в базе!")

    # КД 5 минут для всех (так как Премиум удален)
    is_adm = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_adm:
        if uid in cooldowns and now - cooldowns[uid] < 300:
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
    
    status = "✨ **Статус: Повторка**" if is_dub else "✨ **Статус: Новая карта!**"
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    cap = (
        f"🃏 **Игрок: {won['name']}**\n"
        f"Редкость: {'⭐' * won['stars']}\n"
        f"Описание: {won.get('desc', 'Отсутствует')}\n\n"
        f"{status}"
    )
    bot.send_photo(message.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- АРЕНА ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def arena_info(message):
    bot.reply_to(message, "⚔️ Напиши `Арена @username` или ответь на сообщение игрока словом `Арена`.")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_call(message):
    update_user_record(message)
    uid = str(message.from_user.id)
    tid = None
    tname = "Игрок"

    if message.reply_to_message:
        tid = str(message.reply_to_message.from_user.id)
        tname = message.reply_to_message.from_user.first_name
    else:
        parts = message.text.split()
        if len(parts) > 1:
            raw = parts[1].replace("@", "").lower()
            tid = registered_users.get(raw)
            tname = parts[1]

    if not tid:
        return bot.send_message(message.chat.id, "❌ Игрок не найден в базе.")
    if uid == tid:
        return bot.send_message(message.chat.id, "❌ Нельзя вызвать себя.")
    if not any(user_squads.get(uid, [None]*7)):
        return bot.send_message(message.chat.id, "❌ Твой состав пуст!")

    arena_reqs[tid] = {"att_id": uid, "att_name": message.from_user.first_name}
    bot.send_message(message.chat.id, f"⚔️ **{message.from_user.first_name}** вызвал **{tname}**!\nНапиши **Принять**.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept(message):
    did = str(message.from_user.id)
    if did not in arena_reqs: return
    req = arena_reqs.pop(did)
    aid, aname = req["att_id"], req["att_name"]
    dname = message.from_user.first_name
    
    def get_p(u):
        sq = user_squads.get(str(u), [None]*7)
        h, a = 0, 0
        for c in sq:
            if c:
                s = c.get('stars', 1)
                h += STATS[s]['hp']; a += STATS[s]['atk']
        return h, a

    h1, a1 = get_p(aid); h2, a2 = get_p(did)
    log = f"🏟 **МАТЧ:** {aname} vs {dname}\n\n"
    for r in range(1, 4):
        d1, d2 = a1 + random.randint(0, 300), a2 + random.randint(0, 300)
        h2 -= d1; h1 -= d2
        log += f"Раунд {r}: {aname} -{d1} | {dname} -{d2}\n"
    
    win = aname if h1 > h2 else dname
    bot.send_message(message.chat.id, log + f"\n🏆 **Победитель:** {win}")

# --- СОСТАВ ---

def get_sq_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(uid, [None]*7)
    for i in range(7):
        n = sq[i]['name'] if (i < len(sq) and sq[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {n}", callback_data=f"sl_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_view(m):
    bot.send_message(m.chat.id, "⚔️ Твой состав (7 слотов):", reply_markup=get_sq_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sl_"))
def slot_sel(call):
    idx = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"st_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"st_{idx}_none"))
    bot.edit_message_text(f"Позиция {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("st_"))
def slot_save(call):
    p = call.data.split("_"); idx, name = int(p[1]), p[2]; uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    user_squads[uid][idx] = None if name == "none" else next((c for c in user_colls[uid] if c['name'] == name), None)
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_sq_kb(uid))

# --- КОЛЛЕКЦИЯ ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⭐", callback_data="v_1"), types.InlineKeyboardButton("⭐⭐", callback_data="v_2"))
    kb.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="v_3"), types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="v_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="v_5"))
    bot.send_message(m.chat.id, "Выберите редкость:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def coll_view(call):
    s = int(call.data.split("_")[1]); uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == s]
    if not my: return bot.answer_callback_query(call.id, "У вас нет таких карт.")
    txt = f"🗂 **Ваши карты {s}⭐:**\n\n" + "\n".join([f"• {c['name']}" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- АДМИН-ПАНЕЛЬ (ОПИСАНИЕ ВЕРНУЛОСЬ) ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm_menu(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(m.chat.id, "⚙️ Панель администратора:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def adm_add_1(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Введите имя игрока:")
        bot.register_next_step_handler(msg, adm_add_2)

def adm_add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите звезды (1-5) для {name}:")
    bot.register_next_step_handler(msg, adm_add_3, name)

def adm_add_3(m, name):
    try:
        s = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправьте фото для {name}:")
        bot.register_next_step_handler(msg, adm_add_4, name, s)
    except: bot.send_message(m.chat.id, "Ошибка! Введите число.")

def adm_add_4(m, name, s):
    if not m.photo: return
    fid = m.photo[-1].file_id
    msg = bot.send_message(m.chat.id, "Введите ОПИСАНИЕ игрока:") # Вернули описание
    bot.register_next_step_handler(msg, adm_add_fin, name, s, fid)

def adm_add_fin(m, name, s, fid):
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': s, 'photo': fid, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успешно сохранена!", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def adm_del(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Имя карты для удаления:")
        bot.register_next_step_handler(msg, adm_del_fin)

def adm_del_fin(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Карта удалена из базы.")

bot.infinity_polling()
