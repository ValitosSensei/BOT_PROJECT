import telebot
from telebot import types
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_IDS = [123456789]  # заміни на свій Telegram ID

# Підключення до бази
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Створення таблиць
cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    price NUMERIC
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    product_id INTEGER REFERENCES products(id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    message TEXT
);
""")
conn.commit()

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/catalog', '/help', '/info', '/feedback')
    bot.send_message(message.chat.id,
                     f"Привіт, {message.from_user.first_name}! Я бот-магазин. Обери команду з меню.",
                     reply_markup=markup)

# Команда /help
@bot.message_handler(commands=['help'])
def help_msg(message):
    bot.send_message(message.chat.id, """
Доступні команди:
/start — запуск
/catalog — каталог товарів
/order — оформити замовлення
/feedback — залишити відгук
/info — інформація про бота
/admin — меню для адміну
""")

# Команда /info
@bot.message_handler(commands=['info'])
def info(message):
    bot.send_message(message.chat.id, "Я простий Telegram бот-магазин з каталогом і замовленнями.")

# Каталог
@bot.message_handler(commands=['catalog'])
def catalog(message):
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    if not products:
        bot.send_message(message.chat.id, "Каталог порожній.")
        return

    for product in products:
        product_id, name, desc, price = product
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton(f"Замовити {name}", callback_data=f"order_{product_id}"))
        bot.send_message(message.chat.id, f"🛍️ {name}\n💬 {desc}\n💰 {price} грн", reply_markup=btn)

# Обробка замовлення
@bot.callback_query_handler(func=lambda call: call.data.startswith("order_"))
def confirm_order(call):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    username = call.from_user.username or "NoUsername"
    cur.execute("INSERT INTO purchases (user_id, username, product_id) VALUES (%s, %s, %s)",
                (user_id, username, product_id))
    conn.commit()
    bot.answer_callback_query(call.id, "Замовлення прийнято!")
    bot.send_message(call.message.chat.id, "✅ Ваше замовлення підтверджено!")
    for admin in ADMIN_IDS:
        bot.send_message(admin, f"Нове замовлення від @{username} на товар ID {product_id}")

# Команда /order
@bot.message_handler(commands=['order'])
def user_order(message):
    bot.send_message(message.chat.id, "Використай /catalog щоб замовити товар.")

# Відгук
@bot.message_handler(commands=['feedback'])
def feedback(message):
    msg = bot.send_message(message.chat.id, "Напиши свій відгук:")
    bot.register_next_step_handler(msg, save_feedback)

def save_feedback(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    msg_text = message.text
    cur.execute("INSERT INTO feedback (user_id, username, message) VALUES (%s, %s, %s)",
                (user_id, username, msg_text))
    conn.commit()
    bot.send_message(message.chat.id, "Дякую за відгук!")
    for admin in ADMIN_IDS:
        bot.send_message(admin, f"Новий відгук від @{username}: {msg_text}")

# Команда /admin
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "Адмін-команди:\n/add_item\n/remove_item\n/orders")
    else:
        bot.send_message(message.chat.id, "У вас немає доступу.")

# Додавання товару
@bot.message_handler(commands=['add_item'])
def add_item(message):
    if message.from_user.id in ADMIN_IDS:
        msg = bot.send_message(message.chat.id, "Введи товар у форматі: Назва | Опис | Ціна")
        bot.register_next_step_handler(msg, save_item)

def save_item(message):
    try:
        name, desc, price = message.text.split("|")
        price = float(price.strip())
        cur.execute("INSERT INTO products (name, description, price) VALUES (%s, %s, %s)",
                    (name.strip(), desc.strip(), price))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Товар додано.")
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Помилка: " + str(e))

# Видалення товару
@bot.message_handler(commands=['remove_item'])
def remove_item(message):
    if message.from_user.id in ADMIN_IDS:
        msg = bot.send_message(message.chat.id, "Введи ID товару для видалення:")
        bot.register_next_step_handler(msg, delete_item)

def delete_item(message):
    try:
        product_id = int(message.text.strip())
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        bot.send_message(message.chat.id, "🗑️ Товар видалено.")
    except:
        bot.send_message(message.chat.id, "⚠️ Некоректний ID.")

# Перегляд замовлень
@bot.message_handler(commands=['orders'])
def orders(message):
    if message.from_user.id in ADMIN_IDS:
        cur.execute("SELECT * FROM purchases")
        orders = cur.fetchall()
        if not orders:
            bot.send_message(message.chat.id, "Немає замовлень.")
        for o in orders:
            bot.send_message(message.chat.id, f"ID: {o[0]} | User: @{o[2]} | Product ID: {o[3]}")

# Запуск бота
bot.polling(none_stop=True)
