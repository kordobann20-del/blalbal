import telebot
from telebot import types
import os

# Вставь свой токен сюда или настрой через переменные окружения
TOKEN = os.getenv('TOKEN') 
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    # Создаем кнопки для выбора
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Как дела? 😊")
    btn2 = types.KeyboardButton("Какой сейчас год? 📅")
    btn3 = types.KeyboardButton("Кто ты? 🤖")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, "Привет! Выбери вопрос на кнопках ниже:", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_questions(message):
    if message.text == "Как дела? 😊":
        bot.send_message(message.chat.id, "У меня отлично, я же программа! А у тебя как?")
        
    elif message.text == "Какой сейчас год? 📅":
        bot.send_message(message.chat.id, "Сейчас 2026 год. Время летит!")
        
    elif message.text == "Кто ты? 🤖":
        bot.send_message(message.chat.id, "Я твой первый простой бот на Python!")
        
    else:
        bot.send_message(message.chat.id, "Я пока не знаю ответа на это. Нажми на кнопку!")

if __name__ == "__main__":
    print("Бот запущен и ждет вопросов...")
    bot.infinity_polling()
