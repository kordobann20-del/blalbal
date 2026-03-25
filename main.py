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
arena_reqs = {}

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
    bot.send_message(message.chat.id, "⚽ **Добро пожаловать в Football Card Bot!**\n\nСобирай карточки игроков, формируй состав и побеждай на Арене.", 
                     reply_markup=main_keyboard(uname), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "Назад в меню")
def back_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_keyboard(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_info(message):
    bot.send_message(message.chat.id, "💎 **Премиум статус**\n\nПозволяет крутить карты без КД (ожидания)!\nДля покупки пиши: @verybigsun", parse_mode="Markdown")

# --- ЛОГИКА АРЕНЫ ---

@bot.message_handler(func=lambda m: m.text == "Арена")
def arena_main(message):
    bot.reply_to(message, "⚔️ **Вы на Арене!**\n\nЧтобы бросить вызов:\n1. Напиши `Арена @юзернейм` (игрок должен быть в боте)\n2. Или **ответь** (реплаем) словом `Арена` на сообщение другого игрока.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith("арена") or m.text.lower() == "арена"))
def arena_call(message):
    uid = str(message.from_user.id)
    target_id = None
    target_name = "Оппонент"

    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        target_name = message.reply_to_message.from_user.first_name
    else:
        parts = message.text.split()
        if len(parts) > 1:
            raw_name = parts[1].replace("@", "").lower()
            target_id = registered_users.get(raw_name)
            target_name = parts[1]

    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден. Он должен хотя бы раз нажать /start в боте.")
        return

    if uid == target_id:
        bot.send_message(message.chat.id, "❌ Нельзя вызвать самого себя!")
        return

    if not any(user_squads.get(uid, [None]*7)):
        bot.send_message(message.chat.id, "❌ Твой состав пуст! Сначала выбей карты и поставь их в меню 'Состав'.")
        return

    arena_reqs[target_id] = {"attacker_id": uid, "attacker_name": message.from_user.first_name}
    bot.send_message(message.chat.id, f"⚔️ **{message.from_user.first_name}** бросил вызов **{target_name}**!\n\nОппонент должен написать: **Принять**")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "принять")
def arena_accept(message):
    def_id = str(message.from_user.id)
    if def_id not in arena_reqs: return

    req = arena_reqs.pop(def_id)
    att_id = req["attacker_id"]
    att_name = req["attacker_name"]
    def_name = message.from_user.first_name
    
    def get_team_power(user_id):
        squad = user_squads.get(str(user_id), [None]*7)
        hp, atk = 0, 0
        for slot in squad:
            if slot:
                st = slot.get('stars', 1)
                hp += STATS[st]['hp']
                atk += STATS[st]['atk']
        return hp, atk

    p1_hp, p1_atk = get_team_power(att_id)
    p2_hp, p2_atk = get_team_power(def_id)

    if p1_hp == 0 or p2_hp == 0:
        bot.send_message(message.chat.id, "❌ У одного из игроков пустой состав. Бой невозможен.")
        return

    log = f"🏟 **МАТЧ НАЧАЛСЯ!**\n👟 {att_name} VS {def_name}\n\n"
    for r in range(1, 4):
        d1 = p1_atk + random.randint(-100, 400)
        d2 = p2_atk + random.randint(-100, 400)
        p2_hp -= d1; p1_hp -= d2
        log += f"Раунд {r}: {att_name} нанес {d1} ⚔️ {def_name} нанес {d2}\n"
        if p1_hp <= 0 or p2_hp <= 0: break
    
    winner, loser = (att_name, def_name) if p1_hp > p2_hp else (def_name, att_name)
    bot.send_message(message.chat.id, log + f"\n🏆 **ИТОГИ МАТЧА:**\n🥇 **Победитель:** {winner}\n💀 **Проигравший:** {loser}", parse_mode="Markdown")

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

    is_admin = uname and uname.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if uid in cooldowns and now - cooldowns[uid] < 300:
            rem = int(300 - (now - cooldowns[uid]))
            bot.send_message(message.chat.id, f"⏳ Подожди еще {rem // 60} мин {rem % 60} сек.")
            return

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
        bot.send_photo(message.chat.id, card['photo'], caption=f"✨ **НОВЫЙ ИГРОК!**\n\nИмя: {card['name']}\nРедкость: {'⭐'*card['stars']}\nОписание: {card['desc']}", parse_mode="Markdown")

# --- КОЛЛЕКЦИЯ ---

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def collection_view(message):
    bot.send_message(message.chat.id, "Выберите редкость карточек:", reply_markup=stars_filter_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def filter_stars(call):
    stars = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my = [c for c in user_colls.get(uid, []) if c.get('stars', 1) == stars]
    if not my:
        bot.answer_callback_query(call.id, "У тебя нет таких карт!")
        return
    txt = f"🗂 **Твои игроки ({'⭐'*stars}):**\n\n" + "\n".join([f"• {c['name']}" for c in my])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- СОСТАВ ---

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
    bot.send_message(m.chat.id, "⚔️ **Твой футбольный состав (7 позиций):**", reply_markup=get_squad_kb(m.from_user.id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sl_"))
def squad_select(call):
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    coll = user_colls.get(uid, [])
    if not coll: 
        bot.answer_callback_query(call.id, "Твоя коллекция пуста!")
        return
    kb = types.InlineKeyboardMarkup()
    for c in coll:
        kb.add(types.InlineKeyboardButton(f"{c['name']} ({c['stars']}⭐)", callback_data=f"ap_{idx}_{c['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"ap_{idx}_none"))
    bot.edit_message_text(f"Выберите игрока на позицию {POSITIONS[idx]}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ap_"))
def squad_apply(call):
    p = call.data.split("_")
    idx, name = int(p[1]), p[2]
    uid = str(call.from_user.id)
    if uid not in user_squads: user_squads[uid] = [None]*7
    user_squads[uid][idx] = None if name == "none" else next((c for c in user_colls[uid] if c['name'] == name), None)
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Состав обновлен!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- АДМИН-ПАНЕЛЬ ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm_panel(m):
    if m.from_user.username in ADMINS:
        bot.send_message(m.chat.id, "⚙️ Панель администратора:", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text in ["Добавить карту", "Изменить карту"])
def adm_start(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите имя игрока:")
        bot.register_next_step_handler(msg, adm_stars)

def adm_stars(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите звезды (1-5) для {name}:")
    bot.register_next_step_handler(msg, adm_photo, name)

def adm_photo(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"Отправьте фото для {name}:")
        bot.register_next_step_handler(msg, adm_desc, name, stars)
    except: bot.send_message(m.chat.id, "Ошибка! Нужно число.")

def adm_desc(m, name, stars):
    if not m.photo: 
        bot.send_message(m.chat.id, "Ошибка! Вы не прислали фото.")
        return
    fid = m.photo[-1].file_id
    msg = bot.send_message(m.chat.id, "Введите описание карты:")
    bot.register_next_step_handler(msg, adm_save, name, stars, fid)

def adm_save(m, name, stars, fid):
    global cards
    # Обновляем или добавляем (удаляем старую если была)
    cards = [c for c in cards if c['name'].lower() != name.lower()]
    cards.append({'name': name, 'stars': stars, 'photo': fid, 'desc': m.text})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успешно сохранена!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "Удалить карту")
def adm_del(m):
    if m.from_user.username in ADMINS:
        msg = bot.send_message(m.chat.id, "Введите имя игрока для удаления:")
        bot.register_next_step_handler(msg, adm_del_final)

def adm_del_final(m):
    global cards
    cards = [c for c in cards if c['name'].lower() != m.text.lower()]
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, "✅ Карта удалена.", reply_markup=admin_keyboard())

bot.infinity_polling()
