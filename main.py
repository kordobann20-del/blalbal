import telebot
from telebot import types
import random
import time
import json
import os

# Твои данные
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]

bot = telebot.TeleBot(TOKEN)

# Файлы для хранения данных
CARDS_FILE = 'cards.json'
COLLECTIONS_FILE = 'collections.json'

# Функции для работы с данными
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {} if 'collections' in filename else []
    return {} if 'collections' in filename else []

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загружаем данные при старте
cards = load_json(CARDS_FILE)
user_collections = load_json(COLLECTIONS_FILE) # {user_id: [cards]}
user_cooldowns = {}
states = {}

# Главное меню
def main_menu(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Крутить карту", "Коллекция")
    markup.add("Премиум")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Добавить карту", "Удалить карту")
    markup.add("Изменить карту", "Список команд")
    markup.add("Назад в меню")
    return markup

# --- ОБРАБОТКА ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Игра готова.", 
                     reply_markup=main_menu(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Премиум")
def premium_info(message):
    bot.send_message(message.chat.id, "Чтобы купить премиум, пиши к @verybigsun")

@bot.message_handler(func=lambda m: m.text in ["Назад в меню", "Отмена"])
def back(message):
    states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Крутить карту")
def roll_card(message):
    global cards, user_collections
    u_id = str(message.from_user.id) # JSON ключи всегда строки
    username = message.from_user.username
    now = time.time()

    if not cards:
        return bot.send_message(message.chat.id, "⚠️ Карт пока нет.")

    # Проверка КД: если не админ, проверяем 5 минут (300 сек)
    is_admin = username and username.lower() in [a.lower() for a in ADMINS]
    if not is_admin:
        if u_id in user_cooldowns and now - user_cooldowns[u_id] < 300:
            left = int((300 - (now - user_cooldowns[u_id])) / 60)
            return bot.send_message(message.chat.id, f"⏳ КД! Жди {left} мин.")

    card = random.choice(cards)
    
    # Сохраняем в коллекцию
    if u_id not in user_collections:
        user_collections[u_id] = []
    user_collections[u_id].append(card)
    
    # Сохраняем КД и БД
    user_cooldowns[u_id] = now
    save_json(user_collections, COLLECTIONS_FILE)

    bot.send_photo(message.chat.id, card['photo'], 
                   caption=f"🎁 Карта: *{card['name']}*\n\n{card['desc']}", 
                   parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "Коллекция")
def show_coll(message):
    u_id = str(message.from_user.id)
    my = user_collections.get(u_id, [])
    if not my: return bot.send_message(message.chat.id, "Пусто.")
    
    res = "🗂 Твои карты:\n" + "\n".join([f"- {c['name']}" for c in my])
    bot.send_message(message.chat.id, res)

# Админ-панель и шаги (Добавление/Удаление/Изменение)
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_adm(message):
    if message.from_user.username and message.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(message.chat.id, "Админ-меню:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    global cards
    u_id = message.from_user.id
    username = message.from_user.username
    
    if username and username.lower() in [a.lower() for a in ADMINS]:
        if message.text == "Добавить карту":
            states[u_id] = {'action': 'add', 'step': 1}
            bot.send_message(message.chat.id, "Название:")
        elif message.text == "Удалить карту":
            states[u_id] = {'action': 'delete'}
            bot.send_message(message.chat.id, "Название для удаления:")
        
        elif u_id in states:
            state = states[u_id]
            if state['action'] == 'delete':
                cards = [c for c in cards if c['name'].lower() != message.text.lower()]
                save_json(cards, CARDS_FILE)
                bot.send_message(message.chat.id, "✅ Удалено.", reply_markup=admin_menu())
                del states[u_id]
            elif state['action'] == 'add' and state['step'] == 1:
                state['name'] = message.text
                state['step'] = 2
                bot.send_message(message.chat.id, "Шли фото:")
            elif state['action'] == 'add' and state['step'] == 3:
                cards.append({'name': state['name'], 'photo': state['photo'], 'desc': message.text})
                save_json(cards, CARDS_FILE)
                bot.send_message(message.chat.id, "✅ Добавлена!", reply_markup=admin_menu())
                del states[u_id]

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    u_id = message.from_user.id
    if u_id in states and states[u_id]['action'] == 'add' and states[u_id]['step'] == 2:
        states[u_id]['photo'] = message.photo[-1].file_id
        states[u_id]['step'] = 3
        bot.send_message(message.chat.id, "Введи описание:")

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
