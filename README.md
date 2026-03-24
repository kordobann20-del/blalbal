import telebot
from telebot import types

# Твой токен уже вставлен в код
TOKEN = '8791422162:AAHz3xKU4oKr8dwn_nc-qrpbd5JEGmuPYVw'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    # Главное меню с кнопками-вопросами
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Как дела? 😊")
    btn2 = types.KeyboardButton("Какой сейчас год? 📅")
    btn3 = types.KeyboardButton("Кто тебя создал? 🤖")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}! 👋\nЯ твой новый бот. Выбери любой вопрос ниже:", 
        reply_markup=markup
    )

@bot.message_handler(content_types=['text'])
def handle_questions(message):
    # Логика ответов на вопросы
    if message.text == "Как дела? 😊":
        bot.send_message(message.chat.id, "У меня всё супер! Работаю на полную мощность. ⚡️ Как твои успехи в программировании?")
        
    elif message.text == "Какой сейчас год? 📅":
        bot.send_message(message.chat.id, "На календаре 2026 год. Будущее уже здесь! 🚀")
        
    elif message.text == "Кто тебя создал? 🤖":
        bot.send_message(message.chat.id, "Меня создал крутой разработчик, который сейчас учится кодить на Python! 😎")
        
    else:
        # Если пользователь написал что-то свое
        bot.send_message(message.chat.id, "Интересный вопрос! Но я пока умею отвечать только на те, что на кнопках. Попробуй их! 👇")

if __name__ == "__main__":
    print("Бот успешно запущен! Проверь его в Telegram.")
    bot.infinity_polling()
