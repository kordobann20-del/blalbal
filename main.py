import telebot
from telebot import types
import random
import time
import json
import os

# НОВИЙ ТОКЕН
TOKEN = "8771453170:AAFJXQ7jBhwRQleTKZRnCFhEW0wmRQLxr3c"
ADMINS = ["verybigsun", "Nazikrrk"]

bot = telebot.TeleBot(TOKEN)

# Файл для збереження карток (щоб не зникали після перезапуску на Railway)
CARDS_FILE = 'cards.json'

def load_data():
    if os.path.exists(CARDS_FILE):
        try:
            with open(CARDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data():
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=4)

# Ініціалізація
cards = load_data()
user_collections = {}
user_cooldowns = {}
states = {}

# --- КЛАВІАТУРИ ---
def main_menu(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Крутить карту", "Коллекция")
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Добавить карту", "Удалить карту")
    markup.add("Изменить карту", "Список команд")
    markup.add("Назад в меню")
    return markup

def edit_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Изменить название", "Изменить фото", "Изменить описание")
    markup.add("Отмена")
    return markup

# --- СТАРТ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Используй кнопки для игры.", 
                     reply_markup=main_menu(message.from_user.username))

@bot.message_handler(func=lambda m: m.text in ["Назад в меню", "Отмена"])
def back_to_main(message):
    states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Ок, возвращаемся.", reply_markup=main_menu(message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_admin(message):
    if message.from_user.username and message.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(message.chat.id, "Админ-панель открыта:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "Список команд")
def list_commands(message):
    text = "📜 Команды:\n/start - Меню\nКрутить карту\nКоллекция\n🛠 В админке: Добавить, Удалить, Изменить."
    bot.send_message(message.chat.id, text)

# --- ОСНОВНА ЛОГІКА ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    global cards # Важливо для Railway
    u_id = message.from_user.id
    user_text = message.text
    username = message.from_user.username

    if user_text == "Крутить карту":
        now = time.time()
        if not cards: return bot.send_message(message.chat.id, "⚠️ Карт пока нет в игре.")
        if u_id in user_cooldowns and now - user_cooldowns[u_id] < 900:
            left = int((900 - (now - user_cooldowns[u_id])) / 60)
            return bot.send_message(message.chat.id, f"⏳ Подожди еще {left} мин.")
        
        card = random.choice(cards)
        if u_id not in user_collections: user_collections[u_id] = []
        user_collections[u_id].append(card)
        user_cooldowns[u_id] = now
        bot.send_photo(message.chat.id, card['photo'], caption=f"🎁 *{card['name']}*\n\n{card['desc']}", parse_mode="Markdown")

    elif user_text == "Коллекция":
        my = user_collections.get(u_id, [])
        if not my: return bot.send_message(message.chat.id, "Твоя коллекция пока пуста.")
        res = "🗂 Твои карты:\n" + "\n".join([f"- {c['name']}" for c in my])
        bot.send_message(message.chat.id, res)

    # Адмін-функції
    elif username and username.lower() in [a.lower() for a in ADMINS]:
        if user_text == "Добавить карту":
            states[u_id] = {'action': 'add', 'step': 1}
            bot.send_message(message.chat.id, "Введите название новой карты:")
        elif user_text == "Удалить карту":
            states[u_id] = {'action': 'delete'}
            bot.send_message(message.chat.id, "Введите название карты для удаления:")
        elif user_text == "Изменить карту":
            states[u_id] = {'action': 'edit_search'}
            bot.send_message(message.chat.id, "Введите название карты для изменения:")
        
        elif u_id in states:
            state = states[u_id]
            if state['action'] == 'delete':
                cards = [c for c in cards if c['name'].lower() != user_text.lower()]
                save_data()
                bot.send_message(message.chat.id, f"✅ Карта удалена.", reply_markup=admin_menu())
                del states[u_id]
            
            elif state['action'] == 'edit_search':
                found = next((c for c in cards if c['name'].lower() == user_text.lower()), None)
                if found:
                    state['card_name'] = found['name']
                    state['action'] = 'edit_choice'
                    bot.send_message(message.chat.id, "Что меняем?", reply_markup=edit_menu())
                else: bot.send_message(message.chat.id, "Карта не найдена.")

            elif state['action'] == 'edit_choice':
                if user_text == "Изменить название": state['field'] = 'name'
                elif user_text == "Изменить фото": state['field'] = 'photo'
                elif user_text == "Изменить описание": state['field'] = 'desc'
                state['action'] = 'edit_final'
                bot.send_message(message.chat.id, "Введи новое значение:")

            elif state['action'] == 'edit_final':
                for c in cards:
                    if c['name'] == state['card_name']:
                        c[state['field']] = user_text
                save_data()
                bot.send_message(message.chat.id, "✅ Изменено!", reply_markup=admin_menu())
                del states[u_id]

            elif state['action'] == 'add' and state['step'] == 1:
                state['name'] = user_text
                state['step'] = 2
                bot.send_message(message.chat.id, "Теперь отправь фото:")

            elif state['action'] == 'add' and state['step'] == 3:
                cards.append({'name': state['name'], 'photo': state['photo'], 'desc': user_text})
                save_data()
                bot.send_message(message.chat.id, "✅ Карта добавлена!", reply_markup=admin_menu())
                del states[u_id]

# Окремий хендлер для фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    u_id = message.from_user.id
    if u_id in states:
        state = states[u_id]
        if state['action'] == 'add' and state['step'] == 2:
            state['photo'] = message.photo[-1].file_id
            state['step'] = 3
            bot.send_message(message.chat.id, "Теперь введи описание:")
        elif state['action'] == 'edit_final' and state['field'] == 'photo':
            for c in cards:
                if c['name'] == state['card_name']:
                    c['photo'] = message.photo[-1].file_id
            save_data()
            bot.send_message(message.chat.id, "✅ Фото изменено!", reply_markup=admin_menu())
            del states[u_id]

# Запуск бота з авто-перезапуском при помилках
def run_bot():
    while True:
        try:
            print("Бот запускается...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
