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

# Названия файлов базы данных
FILES = {
    'cards': 'cards.json',      # Все карты в игре
    'colls': 'collections.json',# Коллекции игроков
    'squads': 'squads.json',    # Выставленные составы
    'users': 'users_data.json', # Очки и профили
    'bans': 'bans.json'         # Список заблокированных
}

# Настройки редкости и силы
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Позиции игроков
POSITIONS_DATA = {
    0: {"label": "🧤 Вратарь (ГК)", "code": "ГК"},
    1: {"label": "🛡 Лев. Защитник (ЛЗ)", "code": "ЛЗ"},
    2: {"label": "🛡 Прав. Защитник (ПЗ)", "code": "ПЗ"},
    3: {"label": "👟 Центр. Полузащитник (ЦП)", "code": "ЦП"},
    4: {"label": "⚡️ Лев. Вингер (ЛВ)", "code": "ЛВ"},
    5: {"label": "⚡️ Прав. Вингер (ПВ)", "code": "ПВ"},
    6: {"label": "🎯 Форвард (КФ)", "code": "КФ"}
}

# --- [2] РАБОТА С ДАННЫМИ ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key in ['cards', 'bans'] else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key in ['cards', 'bans'] else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация переменных
cards = load_db('cards')
user_colls = load_db('colls')
user_squads = load_db('squads')
users_data = load_db('users')
ban_list = load_db('bans')
cooldowns = {}

# --- [3] ПРОВЕРКИ И ЛОГИКА ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    u = user.username.lower() if user.username else None
    uid = str(user.id)
    return (u in ban_list) or (uid in ban_list)

def get_power(uid):
    """Считает общую силу состава игрока"""
    sq = user_squads.get(str(uid), [None]*7)
    power = 0
    for p in sq:
        if p: power += STATS[p['stars']]['atk']
    return power

def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    try:
        user = bot.get_chat(uid)
        if is_admin(user): markup.add("🛠 Админ-панель")
    except: pass
    return markup

# --- [4] ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(func=lambda m: is_banned(m.from_user))
def check_ban_status(m):
    bot.send_message(m.chat.id, "🚫 Вы заблокированы и не можете играть.")

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        users_data[uid] = {
            "nick": m.from_user.first_name, 
            "score": 0, 
            "username": (m.from_user.username.lower() if m.from_user.username else f"id{uid}")
        }
        save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Привет, {m.from_user.first_name}! Готов собрать лучшую команду?", reply_markup=main_kb(uid))

# --- [5] ПВП АРЕНА (ДИНАМИЧЕСКИЕ ШАНСЫ) ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def pvp_main_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Случайный противник", callback_data="pvp_mode_random"))
    kb.add(types.InlineKeyboardButton("🔍 Вызвать по юзернейму", callback_data="pvp_mode_user"))
    bot.send_message(m.chat.id, "🏟 **ДОБРО ПОЖАЛОВАТЬ НА АРЕНУ**\n\nЗдесь решает сила состава, но у каждого есть шанс на чудо!", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_mode_user")
def pvp_user_input(call):
    msg = bot.send_message(call.message.chat.id, "Введите @username игрока, которого хотите вызвать:")
    bot.register_next_step_handler(msg, pvp_user_execute)

def pvp_user_execute(m):
    target_un = m.text.replace("@", "").lower().strip()
    target_id = None
    for uid, data in users_data.items():
        if data.get('username') == target_un:
            target_id = uid
            break
    
    if target_id:
        if target_id == str(m.from_user.id):
            return bot.send_message(m.chat.id, "❌ Нельзя играть против самого себя!")
        calculate_pvp_battle(m.chat.id, str(m.from_user.id), target_id)
    else:
        bot.send_message(m.chat.id, "❌ Игрок не найден в базе данных.")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_mode_random")
def pvp_random_execute(call):
    uid = str(call.from_user.id)
    opponents = [u_id for u_id in users_data if u_id != uid and get_power(u_id) > 0]
    if not opponents:
        return bot.answer_callback_query(call.id, "❌ Сейчас нет игроков с готовым составом!", show_alert=True)
    
    target_id = random.choice(opponents)
    calculate_pvp_battle(call.message.chat.id, uid, target_id)

def calculate_pvp_battle(chat_id, p1_id, p2_id):
    p1_power = get_power(p1_id)
    p2_power = get_power(p2_id)
    
    if p1_power == 0:
        return bot.send_message(chat_id, "❌ Ваш состав пуст! Поставьте игроков в меню '📋 Состав'.")

    # ЛОГИКА ШАНСОВ: Победа зависит от доли силы в общей сумме
    # Если силы равны — шанс 50/50. Если один сильнее в 2 раза — шанс ~66/33.
    total_power = p1_power + p2_power
    p1_chance = (p1_power / total_power) * 100
    
    bot.send_message(chat_id, f"🎬 **Матч начинается!**\n\n🏠 {users_data[p1_id]['nick']} (⚔️{p1_power})\n🚀 {users_data[p2_id]['nick']} (⚔️{p2_power})\n\n📊 Ваши шансы на победу: {p1_chance:.1f}%")
    time.sleep(2)

    # Определение победителя по весам
    winner_id = random.choices([p1_id, p2_id], weights=[p1_power, p2_power])[0]
    
    prize = 1000
    users_data[winner_id]['score'] += prize
    save_db(users_data, 'users')
    
    result_text = f"🏁 **ФИНАЛЬНЫЙ СВИСТОК!**\n\n🏆 Победитель: **{users_data[winner_id]['nick']}**\n💰 Награда: +{prize} очков!"
    bot.send_message(chat_id, result_text, parse_mode="Markdown")

# --- [6] ПОЛНАЯ АДМИН-ПАНЕЛЬ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_menu(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить карту", "📝 Изменить карту")
    kb.row("🗑 Удалить карту", "🧨 Обнулить бота")
    kb.row("🚫 Забанить", "✅ Разбанить")
    kb.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА**", reply_markup=kb)

# УДАЛЕНИЕ КАРТЫ (ВЫБОР ИЗ СПИСКА)
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def admin_delete_list(m):
    if not is_admin(m.from_user): return
    if not cards: return bot.send_message(m.chat.id, "❌ Карт в базе нет.")
    
    kb = types.InlineKeyboardMarkup()
    for c in cards:
        kb.add(types.InlineKeyboardButton(f"❌ {c['name']} ({c['stars']}⭐)", callback_data=f"adm_del_{c['name']}"))
    bot.send_message(m.chat.id, "Выберите карту, которую нужно СТЕРЕТЬ из игры:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_"))
def admin_delete_confirm(call):
    card_name = call.data.replace("adm_del_", "")
    global cards
    cards = [c for c in cards if c['name'] != card_name]
    save_db(cards, 'cards')
    bot.edit_message_text(f"✅ Карта **{card_name}** полностью удалена из системы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ИЗМЕНЕНИЕ КАРТЫ
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def admin_edit_list(m):
    if not is_admin(m.from_user): return
    if not cards: return bot.send_message(m.chat.id, "❌ Изменять нечего.")
    
    kb = types.InlineKeyboardMarkup()
    for c in cards:
        kb.add(types.InlineKeyboardButton(f"📝 {c['name']}", callback_data=f"adm_edit_{c['name']}"))
    bot.send_message(m.chat.id, "Какую карту вы хотите отредактировать?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_edit_"))
def admin_edit_step1(call):
    card_name = call.data.replace("adm_edit_", "")
    msg = bot.send_message(call.message.chat.id, f"Вы меняете карту: **{card_name}**\n\nВведите новые данные строго через запятую:\n`Новое Имя, Позиция, Звезды` (Пример: Messi, КФ, 5)", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_edit_finalize, card_name)

def admin_edit_finalize(m, old_name):
    try:
        data = m.text.split(",")
        new_name = data[0].strip()
        new_pos = data[1].strip().upper()
        new_stars = int(data[2].strip())
        
        for c in cards:
            if c['name'] == old_name:
                c['name'], c['pos'], c['stars'] = new_name, new_pos, new_stars
                break
        save_db(cards, 'cards')
        bot.send_message(m.chat.id, f"✅ Карта успешно обновлена на {new_name}!")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка! Напишите данные через запятую, как в примере.")

# ПОЛНОЕ ОБНУЛЕНИЕ
@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def admin_reset_ask(m):
    if not is_admin(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🧨 ДА, СБРОСИТЬ ВСЁ", callback_data="nuke_confirm_final"))
    kb.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="nuke_cancel"))
    bot.send_message(m.chat.id, "❗ **ВНИМАНИЕ**\n\nЭто удалит все ОЧКИ и все КАРТЫ у всех игроков. База станет пустой. Продолжаем?", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "nuke_confirm_final")
def admin_reset_do(call):
    global users_data, user_colls, user_squads
    for u in users_data: users_data[u]['score'] = 0
    user_colls.clear()
    user_squads.clear()
    save_db(users_data, 'users')
    save_db(user_colls, 'colls')
    save_db(user_squads, 'squads')
    bot.edit_message_text("🧨 **БОТ ПОЛНОСТЬЮ ОБНУЛЕН!** Все ресурсы стерты.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "nuke_cancel")
def admin_reset_no(call):
    bot.edit_message_text("❌ Сброс отменен.", call.message.chat.id, call.message.message_id)

# --- [7] УПРАВЛЕНИЕ БАНОМ ---
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban_p1(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для блокировки:")
        bot.register_next_step_handler(msg, admin_ban_p2)

def admin_ban_p2(m):
    target = m.text.replace("@", "").lower().strip()
    if target not in ban_list:
        ban_list.append(target)
        save_db(ban_list, 'bans')
        bot.send_message(m.chat.id, f"✅ Пользователь {target} забанен.")

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def admin_unban_p1(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите @username или ID для разбана:")
        bot.register_next_step_handler(msg, admin_unban_p2)

def admin_unban_p2(m):
    target = m.text.replace("@", "").lower().strip()
    if target in ban_list:
        ban_list.remove(target)
        save_db(ban_list, 'bans')
        bot.send_message(m.chat.id, f"✅ Пользователь {target} разблокирован.")

# --- [8] ДОБАВЛЕНИЕ КАРТЫ ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def admin_add_p1(m):
    if is_admin(m.from_user):
        msg = bot.send_message(m.chat.id, "Введите имя футболиста:")
        bot.register_next_step_handler(msg, admin_add_p2)

def admin_add_p2(m):
    n = m.text
    msg = bot.send_message(m.chat.id, "Введите позицию (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):")
    bot.register_next_step_handler(msg, admin_add_p3, n)

def admin_add_p3(m, n):
    p = m.text.upper().strip()
    msg = bot.send_message(m.chat.id, "Сколько звезд (1-5)?")
    bot.register_next_step_handler(msg, admin_add_p4, n, p)

def admin_add_p4(m, n, p):
    try:
        s = int(m.text)
        msg = bot.send_message(m.chat.id, "Отправьте ФОТО карты:")
        bot.register_next_step_handler(msg, admin_add_final, n, p, s)
    except: bot.send_message(m.chat.id, "❌ Звезды должны быть числом!")

def admin_add_final(m, n, p, s):
    if not m.photo: return bot.send_message(m.chat.id, "❌ Нужно отправить именно фото!")
    cards.append({"name": n, "pos": p, "stars": s, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {n} успешно добавлена!")

# --- [9] СИСТЕМА СОСТАВА ---
@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_menu(m):
    bot.send_message(m.chat.id, "📋 **ВАШ СОСТАВ**\n\nНажмите на позицию, чтобы поставить игрока:", reply_markup=get_squad_kb(m.from_user.id), parse_mode="Markdown")

def get_squad_kb(uid):
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]
        label = POSITIONS_DATA[i]["label"]
        name = p['name'] if p else "❌ ПУСТО"
        kb.add(types.InlineKeyboardButton(f"{label}: {name}", callback_data=f"sq_slot_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("sq_slot_"))
def squad_select_player(call):
    idx = int(call.data.replace("sq_slot_", ""))
    uid = str(call.from_user.id)
    pos_code = POSITIONS_DATA[idx]["code"]
    
    # Только те карты, которые подходят по позиции
    available = [c for c in user_colls.get(uid, []) if c['pos'].upper() == pos_code]
    
    kb = types.InlineKeyboardMarkup()
    for card in available:
        kb.add(types.InlineKeyboardButton(f"{card['name']} ({card['stars']}⭐)", callback_data=f"sq_set_{idx}_{card['name']}"))
    
    kb.add(types.InlineKeyboardButton("🚫 Убрать игрока", callback_data=f"sq_set_{idx}_none"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="sq_back"))
    bot.edit_message_text(f"Выберите игрока на позицию {pos_code}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sq_set_"))
def squad_apply(call):
    data = call.data.split("_")
    idx, name, uid = int(data[2]), data[3], str(call.from_user.id)
    
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        # Проверка, чтобы один и тот же игрок не был в двух слотах
        if any(s and s['name'] == name for i, s in enumerate(user_squads[uid]) if i != idx):
            return bot.answer_callback_query(call.id, "❌ Этот игрок уже в составе!", show_alert=True)
        
        card = next(c for c in user_colls[uid] if c['name'] == name)
        user_squads[uid][idx] = card
        
    save_db(user_squads, 'squads')
    bot.edit_message_text("📋 **Обновленный состав:**", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "sq_back")
def squad_back_btn(call):
    bot.edit_message_text("📋 **ВАШ СОСТАВ**", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(call.from_user.id), parse_mode="Markdown")

# --- [10] КРУТКА, ПРОФИЛЬ, ТОП ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_card(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    if not is_admin(m.from_user) and uid in cooldowns and now - cooldowns[uid] < COOLDOWN_ROLL:
        left = int(COOLDOWN_ROLL - (now - cooldowns[uid]))
        return bot.send_message(m.chat.id, f"⏳ Нужно подождать еще {left//3600}ч {(left%3600)//60}м")

    if not cards: return bot.send_message(m.chat.id, "❌ Админ еще не добавил карты в игру.")

    star_weights = [STATS[s]['chance'] for s in STATS.keys()]
    sel_stars = random.choices(list(STATS.keys()), weights=star_weights)[0]
    
    pool = [c for c in cards if c['stars'] == sel_stars] or cards
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
    
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    bot.send_photo(m.chat.id, won['photo'], caption=f"⚽️ **{won['name']}**\n{'🔄 ПОВТОРКА' if is_dub else '✨ НОВАЯ КАРТА'}\n⭐ {won['stars']} звезд\n💠 +{pts} очков!")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_view(m):
    uid = str(m.from_user.id)
    u = users_data.get(uid, {"nick": "x", "score": 0})
    bot.send_message(m.chat.id, f"👤 **ПРОФИЛЬ:** {u['nick']}\n\n💠 Очки: `{u['score']:,}`\n🗂 Коллекция: {len(user_colls.get(uid, []))} карт\n⚔️ Сила состава: {get_power(uid)}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_view(m):
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        txt += f"{i}. {data['nick']} — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(m.from_user.id))

# Запуск
print("Бот в сети!")
bot.infinity_polling()
