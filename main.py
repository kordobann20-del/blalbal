import telebot
from telebot import types

TOKEN = '8791422162:AAHz3xKU4oKr8dwn_nc-qrpbd5JEGmuPYVw'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Как дела? 😊")
    btn2 = types.KeyboardButton("Какой сейчас год? 📅")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "Привет! Бот запущен! 🚀", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "Как дела? 😊":
        bot.send_message(message.chat.id, "У меня все отлично! 😎")
    elif message.text == "Какой сейчас год? 📅":
        bot.send_message(message.chat.id, "Сейчас 2026 год!")
    else:
        bot.send_message(message.chat.id, "Нажми на одну из кнопок!")

if __name__ == "__main__":
    bot.infinity_polling()
