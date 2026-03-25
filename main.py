import telebot
from telebot import types
import random
import time
import json
import os

TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]

bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json'
}

def load_db(key):
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if key != 'cards' else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
cooldowns = {}
arena_requests = {} # {target_id: requester_id}

# Характеристики по звездам
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# --- КЛАВИАТУРЫ ---
def main_menu(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Крутить карту", "Коллекция")
    markup.add("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def coll_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⭐", "⭐⭐", "⭐⭐⭐")
    markup.add("⭐⭐⭐⭐", "⭐⭐⭐⭐⭐")
    markup.add("Назад в меню")
    return markup

# --- ЛОГИКА ВЫПАДЕНИЯ ---
@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards: return bot.send_message(message.chat.id, "Карт нет.")
    
    is_adm = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_adm:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            return bot.reply_to(message, f"⏳ Жди {int((300-(now-cooldowns[uid]))/60)} мин.")

    # Рандом по шансам
    rand_val = random.randint(1, 100)
    target_stars = 1
    accum = 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        accum += info['chance']
        if rand_val <= accum:
            target_stars = s
            break
    
    possible = [c for c in cards if c.get('stars', 1) == target_stars]
    if not possible: possible = cards # Фолбек если нет карт такой редкости
    
    card = random.choice(possible)
    stars_str = "⭐" * card.get('stars', 1)
    
    if uid not in user_colls: user_colls[uid] = []
    
    # Проверка на повторку
    if any(c['name'] == card['name'] for c in user_colls[uid]):
        bot.send_message(message.chat.id, f"🃏 Выпала повторка: {card['name']}. В коллекцию не добавлена.")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(message.chat.id, card['photo'], caption=f"✨ НОВАЯ КАРТА!\n{card['name']} {stars_str}\n\n{card['desc']}")
    
    cooldowns[uid] = now

# --- КОЛЛЕКЦИЯ И ФИЛЬТРЫ ---
@bot.message_handler(func=lambda m: m.text == "Коллекция")
def show_coll(message):
    bot.send_message(message.chat.id, "Выбери редкость:", reply_markup=coll_menu())

@bot.message_handler(func=lambda m: m.text in ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"])
def filter_coll(message):
    uid = str(message.from_user.id)
    stars_count = len(message.text)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars_count]
    
    if not my: return bot.send_message(message.chat.id, f"У тебя нет карт на {message.text}")
    
    res = f"🗂 Карты {message.text}:\n" + "\n".join([f"- {c['name']}" for c in my])
    bot.send_message(message.chat.id, res)

# --- АРЕНА (РЕПЛАЙ И ВЫЗОВ) ---
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("арена"))
def arena_call(message):
    uid = str(message.from_user.id)
    target_id = None
    
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
    else:
        # Логика поиска по юзернейму (упрощенно)
        bot.send_message(message.chat.id, "Чтобы вызвать, ответь на сообщение игрока словом 'Арена'")
        return

    if uid == target_id: return bot.reply_to(message, "Нельзя биться с собой!")
    
    arena_requests[target_id] = uid
    bot.send_message(message.chat.id, f"⚔️ Игрок @{message.from_user.username} вызвал тебя на дуэль! Напиши 'Принять', чтобы начать.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept(message):
    uid = str(message.from_user.id)
    if uid not in arena_requests: return
    
    enemy_id = arena_requests[uid]
    del arena_requests[uid]
    
    # Логика боя
    p1_squad = user_squads.get(uid, [])
    p2_squad = user_squads.get(enemy_id, [])
    
    if len(p1_squad) < 1 or len(p2_squad) < 1:
        return bot.send_message(message.chat.id, "У одного из игроков пустой состав!")

    # Суммируем статы состава
    def get_power(squad):
        hp = sum(STATS[c.get('stars', 1)]['hp'] for c in squad)
        atk = sum(STATS[c.get('stars', 1)]['atk'] for c in squad)
        return hp, atk

    hp1, atk1 = get_power(p1_squad)
    hp2, atk2 = get_power(p2_squad)
    
    log = "🏁 БИТВА НАЧАЛАСЬ!\n\n"
    for r in range(1, 6):
        dmg1 = atk1 + random.randint(-200, 500)
        dmg2 = atk2 + random.randint(-200, 500)
        hp2 -= dmg1
        hp1 -= dmg2
        log += f"Раунд {r}: Удар {dmg1} | Соперник удар {dmg2}\n"
        if hp1 <= 0 or hp2 <= 0: break
    
    winner = "Ничья"
    if hp1 > hp2: winner = f"@{message.from_user.username}"
    elif hp2 > hp1: winner = "Вызыватель"
    
    log += f"\n🏆 Победитель: {winner}!"
    bot.send_message(message.chat.id, log)

# --- АДМИНКА (Добавление со звездами) ---
@bot.message_handler(commands=['add_card'])
def adm_add(message):
    if message.from_user.username in ADMINS:
        bot.send_message(message.chat.id, "Назови карту:")
        bot.register_next_step_handler(message, add_step_1)

def add_step_1(message):
    name = message.text
    bot.send_message(message.chat.id, "Сколько звезд (1-5):")
    bot.register_next_step_handler(message, add_step_2, name)

def add_step_2(message, name):
    try:
        stars = int(message.text)
        bot.send_message(message.chat.id, "Пришли фото:")
        bot.register_next_step_handler(message, add_step_3, name, stars)
    except: bot.send_message(message.chat.id, "Ошибка, надо число.")

def add_step_3(message, name, stars):
    if message.photo:
        pid = message.photo[-1].file_id
        bot.send_message(message.chat.id, "Описание:")
        bot.register_next_step_handler(message, add_step_4, name, stars, pid)

def add_step_4(message, name, stars, pid):
    cards.append({'name': name, 'stars': stars, 'photo': pid, 'desc': message.text})
    save_db(cards, 'cards')
    bot.send_message(message.chat.id, f"✅ Карта {name} ({stars}⭐) добавлена!")

@bot.message_handler(commands=['start', 'help'])
def help_cmd(message):
    bot.send_message(message.chat.id, "Меню:", reply_markup=main_menu(message.from_user.username))

# Запуск
bot.infinity_polling()
