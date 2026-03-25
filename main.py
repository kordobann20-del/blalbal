import telebot
from telebot import types
import random
import time
import json
import os

# --- НАСТРОЙКИ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users.json'
}

# --- СИСТЕМА СОХРАНЕНИЯ ---
def load_db(key):
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация данных
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

# Характеристики
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# --- КЛАВИАТУРЫ ---
def main_kb(username):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Крутить карту", "Коллекция")
    kb.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        kb.add("🛠 Админ-панель")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Добавить карту", "Удалить карту")
    kb.row("Назад в меню")
    return kb

def stars_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⭐", callback_data="filter_1"),
           types.InlineKeyboardButton("⭐⭐", callback_data="filter_2"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐", callback_data="filter_3"),
           types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="filter_4"))
    kb.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="filter_5"))
    return kb

# --- ОСНОВНАЯ ЛОГИКА ---
@bot.message_handler(commands=['start'])
def start(m):
    uname = m.from_user.username
    if uname:
        registered_users[uname.lower()] = str(m.from_user.id)
        save_db(registered_users, 'users')
    bot.send_message(m.chat.id, "💎 Добро пожаловать! Собирай карты и сражайся на арене.", reply_markup=main_kb(uname))

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back(m):
    bot.send_message(m.chat.id, "Главное меню:", reply_markup=main_kb(m.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium(m):
    bot.send_message(m.chat.id, "💎 Чтобы купить **Премиум**, пиши @verybigsun")

# --- КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "Коллекция")
def collection_start(m):
    bot.send_message(m.chat.id, "Выбери редкость карт:", reply_markup=stars_kb())

@bot.callback_query_handler(func=lambda call: call.data.startswith("filter_"))
def filter_collection(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my_cards = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, f"У тебя нет карт на {stars} звезд!")
    
    txt = f"🗂 Твои карты ({'⭐'*stars}):\n" + "\n".join([f"• {c['name']}" for c in my_cards])
    bot.send_message(call.message.chat.id, txt)
    bot.answer_callback_query(call.id)

# --- СОСТАВ (SQUAD) ---
def squad_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"Слот {i+1}: {name}", callback_data=f"sl_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "⚔️ **Твой состав (7 слотов):**", reply_markup=squad_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("sl_"))
def choose_for_squad(call):
    idx = call.data.split("_")[1]
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: return bot.answer_callback_query(call.id, "Коллекция пуста!")
    
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({'⭐'*c['stars']})", callback_data=f"set_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Очистить слот", callback_data=f"set_{idx}_empty"))
    bot.edit_message_text("Выбери карту для слота:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_to_squad(call):
    _, idx, cname = call.data.split("_")
    uid, idx = str(call.from_user.id), int(idx)
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if cname == "empty":
        user_squads[uid][idx] = None
    else:
        card = next((c for c in user_colls[uid] if c['name'] == cname), None)
        user_squads[uid][idx] = card
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=squad_kb(uid))

# --- КРУТКА ---
@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll(m):
    global cards, user_colls
    uid, uname, now = str(m.from_user.id), m.from_user.username, time.time()
    if not cards: return bot.send_message(m.chat.id, "Карт пока нет в игре.")
    
    if not (uname and uname.lower() in [a.lower() for a in ADMINS]):
        if uid in cooldowns and now - cooldowns[uid] < 300:
            return bot.send_message(m.chat.id, f"⏳ КД! Жди {int((300-(now-cooldowns[uid]))/60)} мин.")

    r = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if r <= acc: stars = s; break
    
    pool = [c for c in cards if c.get('stars', 1) == stars] or cards
    card = random.choice(pool)
    cooldowns[uid] = now

    if uid not in user_colls: user_colls[uid] = []
    if any(c['name'] == card['name'] for c in user_colls[uid]):
        bot.send_message(m.chat.id, f"🃏 Повторка: {card['name']}. Уже есть в коллекции!")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(m.chat.id, card['photo'], caption=f"✨ НОВАЯ КАРТА!\n{card['name']} {'⭐'*card['stars']}\n{card['desc']}")

# --- АРЕНА ---
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_call(m):
    uid, target_id = str(m.from_user.id), None
    if m.reply_to_message:
        target_id = str(m.reply_to_message.from_user.id)
    else:
        p = m.text.split()
        if len(p) > 1: target_id = registered_users.get(p[1].replace("@","").lower())
    
    if not target_id or uid == target_id: 
        return bot.send_message(m.chat.id, "❌ Укажи игрока (реплаем или Арена @юзернейм)")
    
    arena_reqs[target_id] = uid
    bot.send_message(m.chat.id, f"⚔️ Вызов брошен! Игрок должен написать 'Принять'.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_go(m):
    uid = str(m.from_user.id)
    if uid not in arena_reqs: return
    eid = arena_reqs.pop(uid)
    
    def get_stats(user_id):
        sq = [c for c in user_squads.get(user_id, []) if c]
        hp = sum(STATS[c['stars']]['hp'] for c in sq) if sq else 1000
        atk = sum(STATS[c['stars']]['atk'] for c in sq) if sq else 500
        return hp, atk

    h1, a1 = get_stats(uid); h2, a2 = get_stats(eid)
    log = "🏟 **БОЙ НА АРЕНЕ**\n\n"
    for r in range(1, 6):
        d1, d2 = a1 + random.randint(-100, 300), a2 + random.randint(-100, 300)
        h2 -= d1; h1 -= d2
        log += f"Раунд {r}: Урон {d1} | Враг урон {d2}\n"
        if h1 <= 0 or h2 <= 0: break
    
    res = "Победа!" if h1 > h2 else "Поражение!"
    bot.send_message(m.chat.id, log + f"\n🏆 Итог: {res}")

# --- АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(m.chat.id, "Меню администратора:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "Добавить карту")
def add_card_step(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите название карты:")
        bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, "Звезды (1-5):") or bot.register_next_step_handler(m, lambda s, n=m.text: bot.send_message(s.chat.id, "Фото:") or bot.register_next_step_handler(s, lambda p, n=n, s=s.text: bot.send_message(p.chat.id, "Описание:") or bot.register_next_step_handler(p, lambda d, n=n, s=s, p=p.photo[-1].file_id: save_new_card(d, n, s, p)))))

def save_new_card(m, name, stars, fid):
    cards.append({'name': name, 'stars': int(stars), 'photo': fid, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} добавлена!", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def delete_card_step(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "Введите название карты для удаления:")
        bot.register_next_step_handler(m, process_delete)

def process_delete(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Удалено.", reply_markup=admin_kb())

bot.infinity_polling()
