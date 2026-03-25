import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] НАСТРОЙКИ БОТА ---
TOKEN = "8660223435:AAF12SYO3Cv9Fb6du30sStGEyQSyAJFiTiE"
ADMINS = ["merkafor", "Bju_Bet", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

# Файлы базы данных
FILES = {
    'cards': 'cards.json',
    'colls': 'collections.json',
    'squads': 'squads.json',
    'users': 'users_data.json',
    'bans': 'bans.json'
}

# Шансы и награды за редкость
STATS = {
    1: {"chance": 40, "score": 1000, "atk": 100},
    2: {"chance": 30, "score": 3000, "atk": 300},
    3: {"chance": 20, "score": 5000, "atk": 600},
    4: {"chance": 10, "score": 8000, "atk": 1000},
    5: {"chance": 5, "score": 15000, "atk": 2000}
}

# Красивые названия для вывода в сообщении выпадения
POSITIONS_LABELS = {
    "ГК": "Вратарь",
    "ЛЗ": "Лев. Защитник",
    "ПЗ": "Прав. Защитник",
    "ЦП": "Центр. Полузащитник",
    "ЛВ": "Лев. Вингер",
    "ПВ": "Прав. Вингер",
    "КФ": "Нападающий"
}

# Коды для системы состава
POSITIONS_DATA = {
    0: {"label": "🧤 Вратарь (ГК)", "code": "ГК"},
    1: {"label": "🛡 ЛЗ", "code": "ЛЗ"},
    2: {"label": "🛡 ПЗ", "code": "ПЗ"},
    3: {"label": "👟 ЦП", "code": "ЦП"},
    4: {"label": "⚡️ ЛВ", "code": "ЛВ"},
    5: {"label": "⚡️ ПВ", "code": "ПВ"},
    6: {"label": "🎯 КФ", "code": "КФ"}
}

# --- [2] ФУНКЦИИ РАБОТЫ С БАЗОЙ (БЕЗ КЭШИРОВАНИЯ) ---
def load_db(key):
    """Принудительное чтение файла для актуальности данных."""
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
    """Запись в файл."""
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- [3] ВСПОМОГАТЕЛЬНЫЕ ПРОВЕРКИ ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def is_banned(user):
    ban_list = load_db('bans')
    u = user.username.lower() if user.username else None
    uid = str(user.id)
    return (u in ban_list) or (uid in ban_list)

def get_power(uid):
    """Считает общую силу состава игрока."""
    user_squads = load_db('squads')
    sq = user_squads.get(str(uid), [None]*7)
    power = 0
    for player in sq:
        if player:
            power += STATS[player['stars']]['atk']
    return power

# --- [4] КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("📋 Состав", "👤 Профиль")
    markup.row("🏆 Топ очков", "🏟 ПВП Арена")
    try:
        user = bot.get_chat(uid)
        if is_admin(user):
            markup.add("🛠 Админ-панель")
    except:
        pass
    return markup

def cancel_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена")
    return markup

# --- [5] ОБРАБОТЧИК КНОПКИ ОТМЕНА ---
@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def global_cancel_handler(m):
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, "Действие отменено. Возврат в главное меню.", reply_markup=main_kb(uid))

# --- [6] КОМАНДА START ---
@bot.message_handler(commands=['start'])
def handle_start(m):
    if is_banned(m.from_user):
        return bot.send_message(m.chat.id, "🚫 Вы заблокированы.")
    
    users_data = load_db('users')
    uid = str(m.from_user.id)
    uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    
    users_data[uid] = {
        "nick": m.from_user.first_name,
        "score": users_data.get(uid, {}).get('score', 0),
        "username": uname
    }
    save_db(users_data, 'users')
    bot.send_message(m.chat.id, f"⚽️ Привет, {m.from_user.first_name}! Ты в игре.", reply_markup=main_kb(uid))

# --- [7] КРУТКА КАРТ (ROLL) ---
cooldowns = {}

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll_logic(m):
    if is_banned(m.from_user): return
    
    uid = str(m.from_user.id)
    now = time.time()
    COOLDOWN_TIME = 10800 # 3 часа

    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < COOLDOWN_TIME:
            left = int(COOLDOWN_TIME - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ Ждите {left//3600}ч {(left%3600)//60}м")

    cards_list = load_db('cards')
    user_colls = load_db('colls')
    users_data = load_db('users')

    if not cards_list:
        return bot.send_message(m.chat.id, "❌ Админы еще не добавили карты в игру!")

    # Логика шансов
    star_weights = [STATS[s]['chance'] for s in STATS.keys()]
    sel_stars = random.choices(list(STATS.keys()), weights=star_weights)[0]
    
    pool = [c for c in cards_list if c['stars'] == sel_stars]
    if not pool: pool = cards_list
    
    won = random.choice(pool)
    cooldowns[uid] = now
    
    if uid not in user_colls: user_colls[uid] = []
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')

    users_data[uid]['score'] = users_data.get(uid, {}).get('score', 0) + pts
    save_db(users_data, 'users')

    # Оформление по твоему запросу
    status_label = "Новая карта!" if not is_dub else "Повторка"
    pos_label = POSITIONS_LABELS.get(won['pos'].upper(), won['pos'])
    
    caption = (f"⚽️ **{won['name']}** (\"{status_label}\")\n\n"
               f"🎯 **Позиция:** {pos_label}\n"
               f"📊 **Рейтинг:** {'⭐️' * won['stars']}\n\n"
               f"💠 **Очки:** +{pts:,} | {users_data[uid]['score']:,}")
    
    bot.send_photo(m.chat.id, won['photo'], caption=caption, parse_mode="Markdown")

# --- [8] ПРОФИЛЬ И ТОП ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_logic(m):
    if is_banned(m.from_user): return
    
    users_data = load_db('users')
    user_colls = load_db('colls')
    uid = str(m.from_user.id)
    
    # Обновляем юзернейм сразу
    current_uname = f"@{m.from_user.username}" if m.from_user.username else f"id{uid}"
    if uid not in users_data:
        users_data[uid] = {"nick": m.from_user.first_name, "score": 0, "username": current_uname}
    else:
        users_data[uid]["username"] = current_uname
    save_db(users_data, 'users')

    u = users_data[uid]
    pwr = get_power(uid)
    count = len(user_colls.get(uid, []))
    
    text = (f"👤 **ВАШ ПРОФИЛЬ**\n\n"
            f"📝 **Ник:** {u['nick']}\n"
            f"🔗 **Юзернейм:** {u['username']}\n"
            f"💠 **Очки:** `{u['score']:,}`\n"
            f"🗂 **Коллекция:** {count} шт.\n"
            f"🛡 **Сила состава:** {pwr}")
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Топ очков")
def top_logic(m):
    if is_banned(m.from_user): return
    users_data = load_db('users')
    top = sorted(users_data.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    text = "🏆 **ТОП-10 ИГРОКОВ (ПО ЮЗЕРНЕЙМАМ):**\n\n"
    for i, (uid, data) in enumerate(top, 1):
        name = data.get('username', f"id{uid}")
        text += f"{i}. {name} — `{data['score']:,}`\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# --- [9] ПВП АРЕНА ---
@bot.message_handler(func=lambda m: m.text == "🏟 ПВП Арена")
def pvp_menu_logic(m):
    if is_banned(m.from_user): return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Случайный бой", callback_data="pvp_rand"))
    kb.add(types.InlineKeyboardButton("🔍 Поиск по юзернейму", callback_data="pvp_user"))
    bot.send_message(m.chat.id, "🏟 **АРЕНА ПВП**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "pvp_user")
def pvp_search_user(call):
    msg = bot.send_message(call.message.chat.id, "Введите @username соперника (или нажмите /cancel):")
    bot.register_next_step_handler(msg, pvp_exec_search)

def pvp_exec_search(m):
    if m.text == "/cancel" or m.text == "❌ Отмена": return global_cancel_handler(m)
    target = m.text.replace("@", "").lower().strip()
    users_data = load_db('users')
    found_id = None
    for uid, d in users_data.items():
        if d.get('username', '').replace("@", "").lower() == target:
            found_id = uid
            break
    if found_id:
        execute_battle(m.chat.id, str(m.from_user.id), found_id)
    else:
        bot.send_message(m.chat.id, "❌ Игрок не найден в базе.")

@bot.callback_query_handler(func=lambda c: c.data == "pvp_rand")
def pvp_rand_logic(call):
    users_data = load_db('users')
    uid = str(call.from_user.id)
    opps = [u for u in users_data if u != uid and get_power(u) > 0]
    if not opps:
        return bot.answer_callback_query(call.id, "Нет доступных противников!", show_alert=True)
    execute_battle(call.message.chat.id, uid, random.choice(opps))

def execute_battle(chat_id, p1, p2):
    users_data = load_db('users')
    p1_p, p2_p = get_power(p1), get_power(p2)
    if p1_p == 0: return bot.send_message(chat_id, "❌ Твой состав пуст!")
    
    winner_id = random.choices([p1, p2], weights=[p1_p, p2_p])[0]
    users_data[winner_id]['score'] += 1000
    save_db(users_data, 'users')
    bot.send_message(chat_id, f"🏆 Победил: **{users_data[winner_id].get('username')}** (+1000 очков!)")

# --- [10] АДМИН-ПАНЕЛЬ (ПОЛНАЯ ЛОГИКА С ОТМЕНОЙ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_main_menu(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Добавить карту", "📝 Изменить карту")
    kb.row("🗑 Удалить карту", "🧨 Обнулить бота")
    kb.row("🚫 Забанить", "✅ Разбанить")
    kb.row("🏠 Назад в меню")
    bot.send_message(m.chat.id, "🛠 **УПРАВЛЕНИЕ БОТОМ:**", reply_markup=kb)

# ДОБАВЛЕНИЕ
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_add_1(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите ИМЯ игрока:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, adm_add_2)

def adm_add_2(m):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    name = m.text
    bot.send_message(m.chat.id, "Введите ПОЗИЦИЮ (ГК, ЛЗ, ПЗ, ЦП, ЛВ, ПВ, КФ):", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, adm_add_3, name)

def adm_add_3(m, n):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    pos = m.text.upper().strip()
    bot.send_message(m.chat.id, "Введите РЕЙТИНГ (1-5 звезд):", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, adm_add_4, n, pos)

def adm_add_4(m, n, p):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    try:
        stars = int(m.text)
        bot.send_message(m.chat.id, "Пришлите ФОТО игрока:", reply_markup=cancel_kb())
        bot.register_next_step_handler(m, adm_add_fin, n, p, stars)
    except:
        bot.send_message(m.chat.id, "❌ Нужно ввести число от 1 до 5!")
        bot.register_next_step_handler(m, adm_add_4, n, p)

def adm_add_fin(m, n, p, s):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    if m.photo:
        cards = load_db('cards')
        cards.append({"name": n, "pos": p, "stars": s, "photo": m.photo[-1].file_id})
        save_db(cards, 'cards')
        bot.send_message(m.chat.id, f"✅ Карта {n} успешно добавлена!", reply_markup=main_kb(str(m.from_user.id)))
    else:
        bot.send_message(m.chat.id, "❌ Это не фото! Попробуйте снова.")

# ИЗМЕНЕНИЕ КАРТЫ
@bot.message_handler(func=lambda m: m.text == "📝 Изменить карту")
def adm_edit_list(m):
    if not is_admin(m.from_user): return
    cards = load_db('cards')
    if not cards: return bot.send_message(m.chat.id, "Карт нет.")
    kb = types.InlineKeyboardMarkup()
    for c in cards:
        kb.add(types.InlineKeyboardButton(f"📝 {c['name']} ({c['stars']}⭐)", callback_data=f"edit_card_{c['name']}"))
    bot.send_message(m.chat.id, "Какую карту изменить?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_card_"))
def adm_edit_input(call):
    name = call.data.replace("edit_card_", "")
    bot.send_message(call.message.chat.id, f"Меняем {name}.\nВведите данные: `Новое имя, Позиция, Звезды` (через запятую)\nПример: Messi, КФ, 5", parse_mode="Markdown", reply_markup=cancel_kb())
    bot.register_next_step_handler(call.message, adm_edit_save, name)

def adm_edit_save(m, old_name):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    try:
        cards = load_db('cards')
        parts = m.text.split(",")
        n_name, n_pos, n_stars = parts[0].strip(), parts[1].strip().upper(), int(parts[2].strip())
        for c in cards:
            if c['name'] == old_name:
                c['name'], c['pos'], c['stars'] = n_name, n_pos, n_stars
                break
        save_db(cards, 'cards')
        bot.send_message(m.chat.id, "✅ Карта обновлена!", reply_markup=main_kb(str(m.from_user.id)))
    except:
        bot.send_message(m.chat.id, "❌ Ошибка! Формат: Имя, Позиция, Звезды")

# БАН / РАЗБАН
@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def adm_ban_start(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите @username игрока для бана:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, adm_ban_exec)

def adm_ban_exec(m):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    bans.append(target)
    save_db(bans, 'bans')
    bot.send_message(m.chat.id, f"✅ Игрок {target} заблокирован.", reply_markup=main_kb(str(m.from_user.id)))

@bot.message_handler(func=lambda m: m.text == "✅ Разбанить")
def adm_unban_start(m):
    if not is_admin(m.from_user): return
    bot.send_message(m.chat.id, "Введите @username игрока для разбана:", reply_markup=cancel_kb())
    bot.register_next_step_handler(m, adm_unban_exec)

def adm_unban_exec(m):
    if m.text == "❌ Отмена": return global_cancel_handler(m)
    target = m.text.replace("@", "").lower().strip()
    bans = load_db('bans')
    if target in bans:
        while target in bans: bans.remove(target)
        save_db(bans, 'bans')
        bot.send_message(m.chat.id, f"✅ Игрок {target} разблокирован.", reply_markup=main_kb(str(m.from_user.id)))
    else:
        bot.send_message(m.chat.id, "❌ Игрок не был в бане.")

# ПОДТВЕРЖДЕНИЕ ОБНУЛЕНИЯ
@bot.message_handler(func=lambda m: m.text == "🧨 Обнулить бота")
def adm_nuke_confirm(m):
    if not is_admin(m.from_user): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✅ ДА, ОБНУЛИТЬ", "❌ НЕТ, ОТМЕНА")
    bot.send_message(m.chat.id, "⚠️ **ВНИМАНИЕ!** Это действие удалит все очки и коллекции у ВСЕХ игроков. Вы уверены?", parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "✅ ДА, ОБНУЛИТЬ")
def adm_nuke_exec(m):
    if not is_admin(m.from_user): return
    users = load_db('users')
    for u in users: users[u]['score'] = 0
    save_db(users, 'users')
    save_db({}, 'colls')
    save_db({}, 'squads')
    bot.send_message(m.chat.id, "🧨 Бот полностью обнулен!", reply_markup=main_kb(str(m.from_user.id)))

@bot.message_handler(func=lambda m: m.text == "❌ НЕТ, ОТМЕНА")
def adm_nuke_cancel(m):
    bot.send_message(m.chat.id, "Обнуление отменено.", reply_markup=main_kb(str(m.from_user.id)))

# --- [11] КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def coll_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(f"{'⭐'*i} Показать", callback_data=f"coll_view_{i}"))
    bot.send_message(m.chat.id, "🗂 **ВАША КОЛЛЕКЦИЯ:**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("coll_view_"))
def coll_list_show(call):
    stars = int(call.data.split("_")[2])
    my_cards = [c for c in load_db('colls').get(str(call.from_user.id), []) if c['stars'] == stars]
    if not my_cards:
        return bot.answer_callback_query(call.id, "У вас нет карт этой редкости!", show_alert=True)
    txt = f"🗂 **Карты {stars}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my_cards])
    bot.send_message(call.message.chat.id, txt)

# --- [12] СОСТАВ (ПОЛНЫЙ КОД) ---
@bot.message_handler(func=lambda m: m.text == "📋 Состав")
def squad_main(m):
    bot.send_message(m.chat.id, "📋 **ВАШ СОСТАВ:**", reply_markup=get_squad_kb(m.from_user.id))

def get_squad_kb(uid):
    user_squads = load_db('squads')
    kb = types.InlineKeyboardMarkup()
    sq = user_squads.get(str(uid), [None]*7)
    for i in range(7):
        p = sq[i]; label = POSITIONS_DATA[i]["label"]
        kb.add(types.InlineKeyboardButton(f"{label}: {p['name'] if p else '❌'}", callback_data=f"sq_idx_{i}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("sq_idx_"))
def squad_select_player(call):
    idx = int(call.data.split("_")[2])
    uid = str(call.from_user.id)
    pos_code = POSITIONS_DATA[idx]["code"]
    user_colls = load_db('colls')
    valid = [c for c in user_colls.get(uid, []) if c['pos'].upper() == pos_code]
    
    kb = types.InlineKeyboardMarkup()
    for v in valid:
        kb.add(types.InlineKeyboardButton(v['name'], callback_data=f"sq_set_{idx}_{v['name']}"))
    kb.add(types.InlineKeyboardButton("🚫 Убрать", callback_data=f"sq_set_{idx}_none"))
    bot.edit_message_text(f"Игроки на {pos_code}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sq_set_"))
def squad_apply(call):
    p = call.data.split("_")
    idx, name, uid = int(p[2]), p[3], str(call.from_user.id)
    user_squads = load_db('squads')
    user_colls = load_db('colls')
    if uid not in user_squads: user_squads[uid] = [None]*7
    
    if name == "none":
        user_squads[uid][idx] = None
    else:
        user_squads[uid][idx] = next((c for c in user_colls[uid] if c['name'] == name), None)
    
    save_db(user_squads, 'squads')
    bot.edit_message_text("✅ Обновлено!", call.message.chat.id, call.message.message_id, reply_markup=get_squad_kb(uid))

# --- [13] КНОПКА НАЗАД ---
@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_btn(m):
    bot.send_message(m.chat.id, "⚽️ Главное меню:", reply_markup=main_kb(m.from_user.id))

# ЗАПУСК
print("Бот успешно запущен!")
bot.infinity_polling()
