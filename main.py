import telebot
from telebot import types
import random
import time
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]
bot = telebot.TeleBot(TOKEN)

FILES = {'cards': 'cards.json', 'colls': 'collections.json', 'squads': 'squads.json', 'users': 'users.json'}

# Характеристики
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# --- СИСТЕМА БД ---
def load_db(key):
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
registered_users = load_db('users')
cooldowns = {}
arena_reqs = {}

# --- КЛАВИАТУРЫ ---
def main_kb(username):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Крутить карту", "Коллекция")
    kb.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]: kb.add("🛠 Админ-панель")
    return kb

def squad_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        card_name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(text=f"Слот {i+1}: {card_name}", callback_data=f"select_{i}"))
    return kb

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(m):
    uname = m.from_user.username
    if uname:
        registered_users[uname.lower()] = str(m.from_user.id)
        save_db(registered_users, 'users')
    bot.send_message(m.chat.id, "🎮 Добро пожаловать! Собери свой непобедимый состав.", reply_markup=main_kb(uname))

# --- МЕНЮ СОСТАВА ---
@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "⚔️ **Твой состав (7 карт):**\nНажми на слот, чтобы выбрать карту.", 
                     reply_markup=squad_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def choose_card(call):
    slot_index = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    
    if not coll:
        return bot.answer_callback_query(call.id, "У тебя нет карт в коллекции!")

    kb = types.InlineKeyboardMarkup()
    for card in coll:
        kb.add(types.InlineKeyboardButton(text=f"{card['name']} ({'⭐'*card['stars']})", 
                                          callback_data=f"set_{slot_index}_{card['name']}"))
    bot.edit_message_text("Выбери карту для этого слота:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_card(call):
    _, slot, cname = call.data.split("_")
    uid = str(call.from_user.id)
    slot = int(slot)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    # Находим карту в коллекции
    card_data = next((c for c in user_colls[uid] if c['name'] == cname), None)
    if card_data:
        user_squads[uid][slot] = card_data
        save_db(user_squads, 'squads')
        bot.edit_message_text(f"✅ Карта {cname} установлена в слот {slot+1}!", 
                             call.message.chat.id, call.message.message_id, reply_markup=squad_kb(uid))

# --- КРУТКА ---
@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll(m):
    global cards, user_colls
    uid, uname, now = str(m.from_user.id), m.from_user.username, time.time()
    
    if not cards: return bot.send_message(m.chat.id, "Карты не добавлены.")
    if not (uname and uname.lower() in [a.lower() for a in ADMINS]):
        if uid in cooldowns and now - cooldowns[uid] < 300:
            return bot.send_message(m.chat.id, f"⏳ Жди {int((300-(now-cooldowns[uid]))/60)} мин.")

    # Рандом по звездам
    r = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']; 
        if r <= acc: stars = s; break
    
    pool = [c for c in cards if c.get('stars', 1) == stars] or cards
    card = random.choice(pool)
    
    if uid not in user_colls: user_colls[uid] = []
    cooldowns[uid] = now

    if any(c['name'] == card['name'] for c in user_colls[uid]):
        bot.send_message(m.chat.id, f"🃏 Повторка: {card['name']}. У тебя она уже есть.")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(m.chat.id, card['photo'], caption=f"✨ НОВАЯ КАРТА!\n{card['name']} {'⭐'*card['stars']}\n{card['desc']}")

# --- АРЕНА ---
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_start(m):
    uid, target_id = str(m.from_user.id), None
    if m.reply_to_message: target_id = str(m.reply_to_message.from_user.id)
    else:
        p = m.text.split()
        if len(p) > 1: target_id = registered_users.get(p[1].replace("@","").lower())
    
    if not target_id or uid == target_id: return bot.send_message(m.chat.id, "Укажи игрока!")
    arena_reqs[target_id] = uid
    bot.send_message(m.chat.id, "⚔️ Вызов брошен! Оппонент должен написать 'Принять'.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_go(m):
    uid = str(m.from_user.id)
    if uid not in arena_reqs: return
    eid = arena_reqs.pop(uid)
    
    def get_power(user_id):
        sq = [c for c in user_squads.get(user_id, []) if c]
        hp = sum(STATS[c['stars']]['hp'] for c in sq) if sq else 1000
        atk = sum(STATS[c['stars']]['atk'] for c in sq) if sq else 500
        return hp, atk

    h1, a1 = get_power(uid); h2, a2 = get_power(eid)
    log = "🏁 БОЙ!\n"
    for r in range(1, 6):
        d1, d2 = a1 + random.randint(-100, 300), a2 + random.randint(-100, 300)
        h2 -= d1; h1 -= d2
        log += f"Р{r}: Ты {d1} | Враг {d2}\n"
        if h1 <= 0 or h2 <= 0: break
    
    res = "Победа!" if h1 > h2 else "Поражение!"
    bot.send_message(m.chat.id, log + f"🏆 {res}")

# --- АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm(m):
    if m.from_user.username in ADMINS:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("Добавить карту", "Назад в меню")
        bot.send_message(m.chat.id, "Админ-меню:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "Добавить карту")
def add_c(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "Название карты:")
        bot.register_next_step_handler(m, lambda ms: bot.send_message(ms.chat.id, "Звезды (1-5):") or bot.register_next_step_handler(ms, lambda s: bot.send_message(s.chat.id, "Фото:") or bot.register_next_step_handler(s, lambda p: bot.send_message(p.chat.id, "Описание:") or bot.register_next_step_handler(p, lambda d: finalize_add(d, ms.text, s.text, p)))))

def finalize_add(m, name, stars, photo_msg):
    cards.append({'name': name, 'stars': int(stars), 'photo': photo_msg.photo[-1].file_id, 'desc': m.text})
    save_db(cards, 'cards'); bot.send_message(m.chat.id, "✅ Карта добавлена!")

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back(m): bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user.username))

bot.infinity_polling()
