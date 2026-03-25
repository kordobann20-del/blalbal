import telebot
from telebot import types
import random
import time

# ДАННЫЕ БОТА
TOKEN = "8791422162:AAHz3xKU4oKr8dwn_nc-qrpbd5JEGmuPYVw"
ADMINS = ["verybigsun", "Nazikrrk"]

bot = telebot.TeleBot(TOKEN)

# Данные в памяти
cards = []  
user_collections = {}  
user_cooldowns = {}    
admin_states = {}      

# Функция создания меню (Кнопки)
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_roll = types.KeyboardButton("Крутить карту")
    btn_coll = types.KeyboardButton("Коллекция")
    markup.add(btn_roll, btn_coll)
    return markup

# --- СТАРТ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Кнопки активированы. Теперь ты можешь играть.", 
        reply_markup=main_menu()
    )

# --- УДАЛИТЬ ВСЕ КАРТЫ (ТОЛЬКО АДМИН) ---
@bot.message_handler(commands=['delete_all'])
def delete_cards(message):
    current_user = message.from_user.username
    if current_user and current_user.lower() in [a.lower() for a in ADMINS]:
        cards.clear()
        bot.send_message(message.chat.id, "🗑 Все карты из игры удалены!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ Нет прав.")

# --- АДМИНКА: ДОБАВИТЬ КАРТУ ---
@bot.message_handler(commands=['add_card'])
def start_add_card(message):
    current_user = message.from_user.username
    if current_user and current_user.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(message.chat.id, "🛠 Введи название карты:")
        admin_states[message.from_user.id] = {'step': 1}
    else:
        bot.send_message(message.chat.id, "❌ Нет прав.")

# --- КРУТИТЬ КАРТУ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "крутить карту")
def roll_card(message):
    user_id = message.from_user.id
    now = time.time()

    if not cards:
        return bot.send_message(message.chat.id, "⚠️ Карт пока нет. Админы, добавьте их!", reply_markup=main_menu())

    if user_id in user_cooldowns:
        passed = now - user_cooldowns[user_id]
        if passed < 900:
            left = int((900 - passed) / 60)
            return bot.send_message(message.chat.id, f"⏳ Подожди еще {left} мин.", reply_markup=main_menu())

    card = random.choice(cards)
    
    if user_id not in user_collections:
        user_collections[user_id] = []
    
    user_collections[user_id].append(card)
    user_cooldowns[user_id] = now

    caption = f"🎁 Выпала карта: *{card['name']}*\n\n_{card['desc']}_"
    bot.send_photo(message.chat.id, card['photo'], caption=caption, parse_mode="Markdown", reply_markup=main_menu())

# --- КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "коллекция")
def show_collection(message):
    user_id = message.from_user.id
    user_cards = user_collections.get(user_id, [])

    if not user_cards:
        return bot.send_message(message.chat.id, "Твоя коллекция пуста.", reply_markup=main_menu())

    res = "🗂 **Твои карты:**\n"
    for i, c in enumerate(user_cards, 1):
        res += f"{i}. {c['name']}\n"
    
    bot.send_message(message.chat.id, res, parse_mode="Markdown", reply_markup=main_menu())

# --- ПОШАГОВАЯ ЛОГИКА АДМИНКИ ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_steps(message):
    u_id = message.from_user.id
    if u_id not in admin_states:
        return

    state = admin_states[u_id]

    if state['step'] == 1 and message.text:
        state['name'] = message.text
        state['step'] = 2
        bot.send_message(message.chat.id, f"Карта '{message.text}'. Отправь фото:")

    elif state['step'] == 2 and message.photo:
        state['photo'] = message.photo[-1].file_id
        state['step'] = 3
        bot.send_message(message.chat.id, "Теперь введи описание:")

    elif state['step'] == 3 and message.text:
        new_card = {
            'name': state['name'],
            'photo': state['photo'],
            'desc': message.text
        }
        cards.append(new_card)
        del admin_states[u_id]
        bot.send_message(message.chat.id, f"✅ Карта '{new_card['name']}' успешно добавлена!", reply_markup=main_menu())

bot.infinity_polling()
