import telebot
from telebot import types
import logging

# Налаштування
import os
API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '').split(',')]
logger = logging.getLogger(__name__)

# Ініціалізація бота
bot = telebot.TeleBot(API_TOKEN)

# Тимочасне сховище даних
users = {}
products = [
    {"id": 1, "name": "Товар 1", "price": 100, "description": "Опис товару 1"},
    {"id": 2, "name": "Товар 2", "price": 200, "description": "Опис товару 2"}
]
orders = []

# --- Обробники команд ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start', '/help', '/catalog', '/info')
    
    bot.reply_to(message, "Ласкаво просимо! Оберіть команду:", reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Доступні команди:
    /start - Початок роботи
    /help - Допомога
    /info - Інформація про бота
    /catalog - Перегляд каталогу
    /feedback - Залишити відгук
    """
    bot.reply_to(message, help_text)

# Додайте інші обробники команд за аналогією

# --- Інтерактивний каталог ---
@bot.message_handler(commands=['catalog'])
def show_catalog(message):
    markup = types.InlineKeyboardMarkup()
    for product in products:
        markup.add(types.InlineKeyboardButton(
            text=f"{product['name']} - {product['price']}₴",
            callback_data=f"product_{product['id']}"))
    bot.send_message(message.chat.id, "Оберіть товар:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
def product_details(call):
    product_id = int(call.data.split('_')[1])
    product = next(p for p in products if p['id'] == product_id)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Замовити", callback_data=f"order_{product_id}"))
    
    bot.send_message(
        call.message.chat.id,
        f"{product['name']}\n\n{product['description']}\n\nЦіна: {product['price']}₴",
        reply_markup=markup
    )

# --- Адмін-меню ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/add_item', '/remove_item', '/orders')
    bot.send_message(message.chat.id, "Адмін-панель", reply_markup=markup)

# Додайте інші функції адміністрування
if __name__ == '__main__':
    bot.infinity_polling()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Запуск бота...")
    bot.infinity_polling()

