import telebot
from telebot import types
import random
import time

TOKEN = "8791422162:AAHz3xKU4oKr8dwn_nc-qrpbd5JEGmuPYVw"
ADMINS = ["verybigsun", "Nazikrrk"]

bot = telebot.TeleBot(TOKEN)

# Данные
cards = []  
user_collections = {}  
user_cooldowns = {}    
states = {} # Состояния для админов: {user_id: {'step': 1, 'action': 'edit', 'card_name': ''}}

# --- КЛАВИАТУРЫ ---
def main_menu(user_id, username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_roll = types.KeyboardButton("Крутить карту")
    btn_coll = types.KeyboardButton("Коллекция")
    markup.add(btn_roll, btn_coll)
    
    # Если админ — добавляем кнопку админки
    if username and username.lower() in [a.lower() for a in ADMINS]:
        markup.add(types.KeyboardButton("🛠 Админ-панель"))
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

# --- ОБРАБОТКА КОМАНД ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Используй кнопки для игры.", 
                     reply_markup=main_menu(message.from_user.id, message.from_user.username))

@bot.message_handler(func=lambda m: m.text == "Назад в меню" or m.text == "Отмена")
def back_to_main(message):
    states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Возвращаю в главное меню.", 
                     reply_markup=main_menu(message.from_user.id, message.from_user.username))

# --- АДМИН-ПАНЕЛЬ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def open_admin(message):
    if message.from_user.username and message.from_user.username.lower() in [a.lower() for a in ADMINS]:
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "Список команд")
def list_commands(message):
    text = ("📜 **Список команд:**\n"
            "/start - запуск бота\n"
            "/add_card - быстрое добавление\n"
            "/delete_all - удалить все карты\n"
            "Команда 'Крутить карту' - получить карту\n"
            "Команда 'Коллекция' - твои карты")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- ЛОГИКА АДМИНКИ (Добавление, Удаление, Изменение) ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    u_id = message.from_user.id
    user_text = message.text
    username = message.from_user.username

    # 1. КРУТИТЬ КАРТУ
    if user_text == "Крутить карту":
        now = time.time()
        if not cards:
            return bot.send_message(message.chat.id, "⚠️ Карт нет.")
        if u_id in user_cooldowns and now - user_cooldowns[u_id] < 900:
            return bot.send_message(message.chat.id, f"⏳ Жди {int((900-(now-user_cooldowns[u_id]))/60)} мин.")
        
        card = random.choice(cards)
        if u_id not in user_collections: user_collections[u_id] = []
        user_collections[u_id].append(card)
        user_cooldowns[u_id] = now
        bot.send_photo(message.chat.id, card['photo'], caption=f"🎁 *{card['name']}*\n\n{card['desc']}", parse_mode="Markdown")

    # 2. КОЛЛЕКЦИЯ
    elif user_text == "Коллекция":
        my_cards = user_collections.get(u_id, [])
        if not my_cards: return bot.send_message(message.chat.id, "Коллекция пуста.")
        res = "🗂 **Твои карты:**\n" + "\n".join([f"- {c['name']}" for c in my_cards])
        bot.send_message(message.chat.id, res, parse_mode="Markdown")

    # 3. АДМИН-ЛОГИКА
    elif username and username.lower() in [a.lower() for a in ADMINS]:
        if user_text == "Добавить карту":
            states[u_id] = {'action': 'add', 'step': 1}
            bot.send_message(message.chat.id, "Введите название новой карты:")
        
        elif user_text == "Удалить карту":
            states[u_id] = {'action': 'delete'}
            bot.send_message(message.chat.id, "Введите точное название карты для удаления:")
            
        elif user_text == "Изменить карту":
            states[u_id] = {'action': 'edit_search'}
            bot.send_message(message.chat.id, "Введите название карты, которую хотите изменить:")

        # --- ОБРАБОТКА ШАГОВ ---
        elif u_id in states:
            state = states[u_id]
            
            # Удаление
            if state['action'] == 'delete':
                global cards
                cards = [c for c in cards if c['name'].lower() != user_text.lower()]
                bot.send_message(message.chat.id, f"✅ Если карта '{user_text}' была в списке, она удалена.", reply_markup=admin_menu())
                del states[u_id]

            # Изменение (Поиск)
            elif state['action'] == 'edit_search':
                found = next((c for c in cards if c['name'].lower() == user_text.lower()), None)
                if found:
                    state['card_name'] = found['name']
                    state['action'] = 'edit_choice'
                    bot.send_message(message.chat.id, f"Карта '{found['name']}' найдена. Что меняем?", reply_markup=edit_menu())
                else:
                    bot.send_message(message.chat.id, "Карта не найдена. Попробуй еще раз.")

            # Изменение (Выбор поля)
            elif state['action'] == 'edit_choice':
                if user_text == "Изменить название": state['field'] = 'name'
                elif user_text == "Изменить фото": state['field'] = 'photo'
                elif user_text == "Изменить описание": state['field'] = 'desc'
                state['action'] = 'edit_final'
                bot.send_message(message.chat.id, "Введите новое значение (или пришлите фото):")

            # Изменение (Сохранение)
            elif state['action'] == 'edit_final':
                for c in cards:
                    if c['name'] == state['card_name']:
                        if state['field'] == 'photo' and message.photo:
                            c['photo'] = message.photo[-1].file_id
                        else:
                            c[state['field']] = message.text
                bot.send_message(message.chat.id, "✅ Изменено!", reply_markup=admin_menu())
                del states[u_id]

            # Добавление (шаги 1-3 обрабатываются в handle_photo ниже, тут только текст)
            elif state['action'] == 'add':
                if state['step'] == 1:
                    state['name'] = user_text
                    state['step'] = 2
                    bot.send_message(message.chat.id, "Отправь фото:")
                elif state['step'] == 3:
                    cards.append({'name': state['name'], 'photo': state['photo'], 'desc': user_text})
                    bot.send_message(message.chat.id, "✅ Карта добавлена!", reply_markup=admin_menu())
                    del states[u_id]

# Отдельный обработчик для фото (для добавления)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    u_id = message.from_user.id
    if u_id in states and states[u_id]['action'] == 'add' and states[u_id]['step'] == 2:
        states[u_id]['photo'] = message.photo[-1].file_id
        states[u_id]['step'] = 3
        bot.send_message(message.chat.id, "Фото принято. Введи описание:")
    elif u_id in states and states[u_id]['action'] == 'edit_final' and states[u_id]['field'] == 'photo':
        for c in cards:
            if c['name'] == states[u_id]['card_name']:
                c['photo'] = message.photo[-1].file_id
        bot.send_message(message.chat.id, "✅ Фото изменено!", reply_markup=admin_menu())
        del states[u_id]

bot.infinity_polling()
