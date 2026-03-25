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

# Характеристики игроков по звездам
STATS = {
    1: {"hp": 1500, "atk": 800, "chance": 50},
    2: {"hp": 3500, "atk": 1400, "chance": 30},
    3: {"hp": 6000, "atk": 2500, "chance": 12},
    4: {"hp": 10000, "atk": 4000, "chance": 6},
    5: {"hp": 14000, "atk": 6000, "chance": 2}
}

# Позиции в составе
POSITIONS = ["ГК (Вратарь)", "ЛЗ (Защитник)", "ПЗ (Защитник)", "ЦП (Полузащитник)", "ЛВ (Вингер)", "ПВ (Вингер)", "КФ (Нападающий)"]

# --- СИСТЕМА ДАННЫХ ---
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
arena_reqs = {} # Для хранения вызовов на бой

# --- КЛАВИАТУРЫ ---
def main_keyboard(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Крутить карту", "Коллекция")
    markup.row("Состав", "Арена", "Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить карту", "Удалить карту")
    markup.row("Изменить карту", "Назад в меню")
    return markup

def stars_filter_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⭐", callback_data="view_1"), 
               types.InlineKeyboardButton("⭐⭐", callback_data="view_2"))
    markup.row(types.InlineKeyboardButton("⭐⭐⭐", callback_data="view_3"), 
               types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="view_4"))
    markup.add(types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="view_5"))
    return markup

# --- ОБРАБОТЧИКИ МЕНЮ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username
    if uname:
        registered_users[uname.lower()] = uid
        save_db(registered_users, 'users')
    bot.send_message(message.chat.id, "💎 Добро пожаловать! Собирай футбольные карты и побеждай на арене.", 
                     reply_markup=main_keyboard(uname))

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в меню.", reply_markup=main_keyboard(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_info(message):
    bot.send_message(message.chat.id, "💎 **Премиум статус**\n\nПозволяет крутить карты без КД!\nДля покупки: @verybigsun", parse_mode="Markdown")

# --- ЛОГИКА АРЕНЫ ---

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith("арена") or m.text == "Арена"))
def arena_call(message):
    uid = str(message.from_user.id)
    target_id = None

    # Если игрок ответил на сообщение другого игрока
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
    else:
        # Если игрок ввел "Арена @username"
        parts = message.text.split()
        if len(parts) > 1:
            target_name = parts[1].replace("@", "").lower()
            target_id = registered_users.get(target_name)
    
    if not target_id:
        bot.send_message(message.chat.id, "⚠️ Чтобы вызвать на бой, ответь 'Арена' на сообщение игрока или напиши 'Арена @юзернейм'.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "Вы не можете вызвать самого себя!")
        return
    
    # Записываем вызов (ключ - кому брошен вызов, значение - кто бросил)
    arena_reqs[target_id] = uid
    bot.send_message(message.chat.id, "⚔️ Вызов брошен! Оппонент должен написать **Принять**, чтобы начать матч.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept(message):
    uid = str(message.from_user.id)
    
    if uid not in arena_reqs:
        return # Нет активных вызовов для этого игрока

    enemy_id = arena_reqs.pop(uid)
    
    # Функция расчета общей силы состава
    def get_team_power(user_id):
        squad = user_squads.get(str(user_id), [None]*7)
        hp, atk = 0, 0
        has_players = False
        for slot in squad:
            if slot:
                st = slot.get('stars', 1)
                hp += STATS[st]['hp']
                atk += STATS[st]['atk']
                has_players = True
        if not has_players: return 1000, 500 # Базовые статы если состав пуст
        return hp, atk

    p1_hp, p1_atk = get_team_power(uid)
    p2_hp, p2_atk = get_team_power(enemy_id)

    log = f"🏟 **МАТЧ НАЧАЛСЯ!**\n\n"
    for r in range(1, 6): # Максимум 5 раундов
        d1 = p1_atk + random.randint(-200, 400)
        d2 = p2_atk + random.randint(-200, 400)
        p2_hp -= d1
        p1_hp -= d2
        log += f"Раунд {r}: Урон {d1} ⚔️ Урон противника {d2}\n"
        if p1_hp <= 0 or p2_hp <= 0: break
    
    res = "Победа! 🎉" if p1_hp > p2_hp else "Поражение! 💀"
    bot.send_message(message.chat.id, log + f"\n🏆 **Итог: {res}**", parse_mode="Markdown")

# --- КРУТКА КАРТ ---

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_card(message):
    global cards, user_colls
    uid = str(message.from_user.id)
    uname = message.from_user.username
    now = time.time()

    if not cards:
        bot.send_message(message.chat.id, "⚠️ В базе нет карт! Админ должен их добавить.")
        return

    # Проверка КД
    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            rem = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Подожди еще {rem // 60} мин.")
            return

    # Рандом редкости
    rv = random.randint(1, 100)
    stars, acc = 1, 0
    for s, info in sorted(STATS.items(), key=lambda x: x[1]['chance']):
        acc += info['chance']
        if rv <= acc:
            stars = s
            break

    possible = [c for c in cards if c.get('stars', 1) == stars] or cards
    card = random.choice(possible)
    cooldowns[uid] = now

    if uid not in user_colls: user_colls[uid] = []
    if any(c['name'] == card['name'] for c in user_colls[uid]):
        bot.send_message(message.chat.id, f"🃏 Выпал {card['name']}, но он уже есть в коллекции.")
    else:
        user_colls[uid].append(card)
        save_db(user_colls, 'colls')
        bot.send_photo(message.chat.id, card['photo'], caption=f"✨ НОВЫЙ ИГРОК!\n\n{card['name']} {'⭐'*card['stars']}\n{card['desc']}")

# --- КОЛЛЕКЦИЯ ПО ЗВЕЗДАМ ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def collection_view(message):
    bot.send_message(message.chat.id, "Выберите ценность карточек:", reply_markup=stars_filter_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def filter_stars(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars]
    if not my:
        bot.answer_callback_query(call.id, "У тебя нет таких карт!")
        return
    txt = f"🗂 Твои игроки ({'⭐'*stars}):\n\n" + "\n".join([f"• {c['name']}" for c in my])
    bot.send_message(call.message.chat.id, txt)
    bot.answer_callback_query(call.id)

# --- СОСТАВ (ФУТБОЛЬНЫЙ) ---

def get_squad_kb(uid):
    uid = str(uid)
    kb = types.InlineKeyboardMarkup()
    squad = user_squads.get(uid, [None]*7)
    for i in range(7):
        name = squad[i]['name'] if (i < len(squad) and squad[i]) else "❌ Пусто"
        kb.add(types.InlineKeyboardButton(f"{POSITIONS[i]}: {name}", callback_data=f"sl_{i}"))
    return kb

@bot.message_handler(func=lambda m: m.text == "Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "⚔️ **Твой состав:**", reply_markup=get_squad_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("sl_"))
def squad_select(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: return bot.answer_callback_query(call.id, "Коллекция пуста!")
    
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({'⭐'*c['stars']})", callback_data=f"ap_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"ap_{idx}_none"))
    bot.edit_message_text(f"Позиция {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ap_"))
def squad_apply(call):
    p = call.data.split("_")
    idx, name = int(p[1]), p[2]
    uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    if name == "none":
        user_squads[uid][idx] = None
    else:
        user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None)
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- АДМИНКА ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm_panel(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "Админ-меню:", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def adm_start(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите название игрока:")
        bot.register_next_step_handler(msg, adm_stars)

def adm_stars(m):
    name = m.text
    msg = bot.send_message(message.chat.id, f"Звезды (1-5) для {name}:")
    bot.register_next_step_handler(msg, adm_photo, name)

def adm_photo(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте фото:")
        bot.register_next_step_handler(msg, adm_desc, name, stars)
    except: bot.send_message(m.chat.id, "Ошибка!")

def adm_desc(m, name, stars):
    if not m.photo: return
    fid = m.photo[-1].file_id
    msg = bot.send_message(m.chat.id, "Описание:")
    bot.register_next_step_handler(msg, adm_save, name, stars, fid)

def adm_save(m, name, stars, fid):
    global cards
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': stars, 'photo': fid, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Сохранено!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def adm_del(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Имя для удаления:")
        bot.register_next_step_handler(msg, adm_del_final)

def adm_del_final(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Удалено.", reply_markup=admin_keyboard())

bot.infinity_polling()
