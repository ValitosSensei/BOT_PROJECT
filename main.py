import telebot
from telebot import types
import os

# Завантаження API токену з змінних середовища
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

if not API_TOKEN:
    raise Exception("Вкажіть TELEGRAM_API_TOKEN в змінних середовища!")

bot = telebot.TeleBot(API_TOKEN)

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Вітаю! Я ваш бот-помічник.\n"
        "Я можу допомогти з переглядом каталогу товарів, оформленням замовлень та іншими функціями.\n"
        "Використайте /help для перегляду команд."
    )
    bot.reply_to(message, welcome_text)

# Запуск бота (для використання поллингу)
if __name__ == '__main__':
    bot.polling(none_stop=True)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "/start - Запустити бота\n"
        "/help - Допомога\n"
        "/info - Інформація про бота\n"
        "/catalog - Перегляд каталогу товарів\n"
        "/order - Оформлення замовлення\n"
        "/feedback - Залишити відгук"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['info'])
def info_command(message):
    info_text = (
        "Я - Telegram бот для замовлення товарів та послуг.\n"
        "Мої функції включають перегляд каталогу, оформлення замовлення, адміністрування та підтримку користувачів."
    )
    bot.reply_to(message, info_text)

@bot.message_handler(commands=['catalog'])
def catalog_command(message):
    # Створення інлайн клавіатури з прикладом товарів
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Приклад товарів
    products = [
        {"name": "Товар 1", "price": "100 грн", "desc": "Опис товару 1"},
        {"name": "Товар 2", "price": "200 грн", "desc": "Опис товару 2"},
    ]
    for product in products:
        button_text = f"{product['name']} - {product['price']}"
        callback_data = f"product_{product['name']}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    bot.send_message(message.chat.id, "Оберіть товар для перегляду деталей:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
def product_details_callback(call):
    # Відображення детальної інформації про товар
    product_name = call.data.split('_', 1)[1]
    # Знайти деталі товару (зазвичай, через запит до бази даних)
    product_info = f"Детальна інформація про {product_name}: \nЦіна: 100 грн \nОпис: Це приклад опису."
    bot.send_message(call.message.chat.id, product_info)

@bot.message_handler(commands=['order'])
def order_command(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Підтвердити замовлення", callback_data="confirm_order"))
    markup.add(types.InlineKeyboardButton("Скасувати замовлення", callback_data="cancel_order"))
    bot.send_message(message.chat.id, "Ви бажаєте оформити замовлення?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_order", "cancel_order"])
def order_confirmation_callback(call):
    if call.data == "confirm_order":
        # Надіслати інформацію адміністраторам
        admin_message = f"Замовлення від користувача {call.from_user.username} ({call.from_user.id}) підтверджене."
        # Для прикладу, надсилаємо повідомлення самому собі (адміністратору); згодом замініть на ID адміністратора(-ів)
        bot.send_message(call.from_user.id, "Ваше замовлення оформлено. Очікуйте підтвердження від адміністратора.")
        # Надсилання повідомлення адміністратору (наприклад, через список ID)
        admin_ids = [123456789]  # Замініть на актуальні ID адміністраторів
        for admin_id in admin_ids:
            bot.send_message(admin_id, admin_message)
    else:
        bot.send_message(call.message.chat.id, "Замовлення скасовано.")

ADMIN_IDS = [123456789]  # Список ID адміністраторів

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id in ADMIN_IDS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("/add_item", "/remove_item", "/orders")
        bot.send_message(message.chat.id, "Меню адміністратора:", reply_markup=markup)
    else:
        bot.reply_to(message, "У вас немає доступу до адміністративного меню.")

@bot.message_handler(commands=['add_item'])
def add_item_command(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Надішліть дані нового товару у форматі: Назва | Ціна | Опис")
        # Далі – логіка для збереження товару (можна реалізувати через стан чи базу даних)
    else:
        bot.reply_to(message, "Ви не є адміністратором!")

@bot.message_handler(commands=['remove_item'])
def remove_item_command(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Надішліть назву товару для видалення.")
        # Далі – логіка пошуку товару і його видалення з бази даних
    else:
        bot.reply_to(message, "Ви не є адміністратором!")

@bot.message_handler(commands=['orders'])
def orders_command(message):
    if message.from_user.id in ADMIN_IDS:
        # Реалізуйте вибір замовлень з бази даних
        bot.reply_to(message, "Список замовлень:")
    else:
        bot.reply_to(message, "Ви не маєте доступу до списку замовлень!")

@bot.message_handler(commands=['hello'])
def hello_command(message):
    bot.reply_to(message, "Привіт! Як можу допомогти?")

@bot.message_handler(func=lambda m: "Які товари доступні?" in m.text)
def available_products(message):
    bot.reply_to(message, "Використайте команду /catalog для перегляду товарів.")

@bot.message_handler(commands=['feedback'])
def feedback_command(message):
    bot.reply_to(message, "Будь ласка, залиште свій відгук:")
    # Можна реалізувати збір і збереження відгуків для передачі адміністраторам

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("/start", "/catalog")
    markup.row("/info", "/help")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Вітаю! Я ваш бот-помічник.\n"
        "Я можу допомогти з переглядом каталогу товарів, оформленням замовлень та іншими функціями.\n"
        "Використайте /help для перегляду команд."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

def validate_price(price_str):
    try:
        price = float(price_str)
        return price > 0
    except ValueError:
        return False

@bot.message_handler(commands=['add_item'])
def add_item_command(message):
    if message.from_user.id in ADMIN_IDS:
        msg = bot.send_message(message.chat.id, "Надішліть дані нового товару у форматі: Назва | Ціна | Опис")
        bot.register_next_step_handler(msg, process_new_item)
    else:
        bot.reply_to(message, "Ви не є адміністратором!")

def process_new_item(message):
    try:
        name, price_str, description = map(str.strip, message.text.split('|'))
        if not validate_price(price_str):
            bot.reply_to(message, "Некоректне значення ціни. Спробуйте ще раз.")
            return
        # Логіка збереження товару (наприклад, у базу даних)
        bot.reply_to(message, f"Товар {name} додано до каталогу!")
    except Exception as e:
        bot.reply_to(message, "Невірний формат даних. Будь ласка, використовуйте формат: Назва | Ціна | Опис")

@bot.message_handler(commands=['pay'])
def pay_command(message):
    # Створення рахунку для користувача (симуляція)
    bot.send_message(message.chat.id, "Рахунок створено. Будь ласка, перейдіть за посиланням для оплати: https://example.com/payment")
    
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_payment", "cancel_payment"])
def payment_callback(call):
    if call.data == "confirm_payment":
        bot.send_message(call.message.chat.id, "Оплата підтверджена. Дякуємо за замовлення!")
    else:
        bot.send_message(call.message.chat.id, "Оплата скасована.")

import psycopg2
from psycopg2 import sql

# Припустимо, що DATABASE_URL містить повний URI для підключення
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL не задана у змінних середовища!")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Приклад функції додавання товару до бази даних
def add_product_to_db(name, price, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, description) VALUES (%s, %s, %s)",
        (name, price, description)
    )
    conn.commit()
    cursor.close()
    conn.close()

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

@bot.message_handler(func=lambda message: True)
def log_user_activity(message):
    logger.info(f"Користувач {message.from_user.id} запустив команду: {message.text}")
