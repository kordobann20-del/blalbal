import telebot
import random
import time

# ДАННЫЕ БОТА
TOKEN = "8791422162:AAHz3xKU4oKr8dwn_nc-qrpbd5JEGmuPYVw"
ADMIN_ID = 1310344474  # Твой ID

bot = telebot.TeleBot(TOKEN)

# Данные в памяти (после перезапуска бота очистятся)
cards = []  # Список карточек: {'name': '', 'photo': '', 'desc': ''}
user_collections = {}  # Кто что выбил: {user_id: [карты]}
user_cooldowns = {}    # Время последнего прокрута: {user_id: timestamp}
admin_states = {}      # Для процесса создания карты

# --- КОМАНДА ДЛЯ ДОБАВЛЕНИЯ КАРТЫ (ТОЛЬКО АДМИН) ---
@bot.message_handler(commands=['add_card'])
def start_add_card(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🛠 Введите название новой карты:")
        admin_states[message.from_user.id] = {'step': 1}
    else:
        bot.send_message(message.chat.id, "❌ У тебя нет прав для этой команды.")

# --- ОСНОВНАЯ ИГРА: КРУТИТЬ КАРТУ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "крутить карту")
def roll_card(message):
    user_id = message.from_user.id
    now = time.time()

    if not cards:
        bot.reply_to(message, "⚠️ Карт пока нет в игре. Попроси админа добавить их!")
        return

    # Проверка КД (15 минут = 900 сек)
    if user_id in user_cooldowns:
        passed = now - user_cooldowns[user_id]
        if passed < 900:
            left = int((900 - passed) / 60)
            bot.reply_to(message, f"⏳ Подожди еще {left} мин. перед следующим прокрутом!")
            return

    # Выбираем рандомную карту
    card = random.choice(cards)
    
    # Сохраняем в коллекцию
    if user_id not in user_collections:
        user_collections[user_id] = []
    user_collections[user_id].append(card)
    
    # Ставим КД
    user_cooldowns[user_id] = now

    caption = f"🎁 Тебе выпала карта: *{card['name']}*\n\n_{card['desc']}_"
    bot.send_photo(message.chat.id, card['photo'], caption=caption, parse_mode="Markdown")

# --- КОЛЛЕКЦИЯ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "коллекция")
@bot.message_handler(commands=['collection'])
def show_collection(message):
    user_id = message.from_user.id
    user_cards = user_collections.get(user_id, [])

    if not user_cards:
        bot.reply_to(message, "Твоя коллекция пока пуста. Напиши 'Крутить карту'!")
        return

    res = "🗂 **Твои карты:**\n"
    for i, c in enumerate(user_cards, 1):
        res += f"{i}. {c['name']}\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

# --- ЛОГИКА АДМИНКИ (ПОШАГОВАЯ) ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_admin_steps(message):
    user_id = message.from_user.id
    if user_id not in admin_states:
        return

    state = admin_states[user_id]

    if state['step'] == 1 and message.text:
        state['name'] = message.text
        state['step'] = 2
        bot.send_message(message.chat.id, "Теперь отправь фото для карты:")

    elif state['step'] == 2 and message.photo:
        state['photo'] = message.photo[-1].file_id
        state['step'] = 3
        bot.send_message(message.chat.id, "И последнее — введи описание:")

    elif state['step'] == 3 and message.text:
        new_card = {
            'name': state['name'],
            'photo': state['photo'],
            'desc': message.text
        }
        cards.append(new_card)
        del admin_states[user_id]
        bot.send_message(message.chat.id, f"✅ Карта '{new_card['name']}' успешно добавлена!")

print("Бот запущен...")
bot.infinity_polling()
