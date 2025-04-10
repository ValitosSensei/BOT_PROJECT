import os
import telebot
from telebot import types
import psycopg2
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

bot = telebot.TeleBot(BOT_TOKEN)

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL)

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT,
            price NUMERIC,
            description TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            product_id INT,
            confirmed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def seed_products_if_empty():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        products = [
            ("Ноутбук Lenovo", 18999.99, "15.6” FullHD, Intel i5, 8GB RAM, SSD 512GB"),
            ("Смартфон Samsung A53", 12999.00, "6.5” AMOLED, 128GB, 5G"),
            ("Навушники Sony WH-1000XM4", 8999.99, "Безпровідні з шумозаглушенням"),
            ("Монітор LG 27\"", 7499.50, "27” IPS, 75Hz, FullHD"),
            ("Клавіатура Logitech", 1299.00, "Механічна, RGB, USB")
        ]
        cur.executemany("INSERT INTO products (name, price, description) VALUES (%s, %s, %s)", products)
        conn.commit()
    cur.close()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/catalog', '/help', '/info')
    bot.send_message(message.chat.id,
                     f"Привіт, {message.from_user.first_name}! 👋\nЯ — бот-магазин. Обери команду нижче:",
                     reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, """📌 Доступні команди:
/start — почати
/catalog — переглянути каталог
/order — оформити замовлення
/info — інформація про бота
/feedback — залишити відгук
/admin — меню адміністратора (для адмінів)
""")

@bot.message_handler(commands=['info'])
def info_cmd(message):
    bot.send_message(message.chat.id, "🛒 Я — Telegram-магазин бот. Тут ти можеш переглядати товари та робити замовлення!")

@bot.message_handler(commands=['catalog'])
def catalog(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products")
    for row in cur.fetchall():
        prod_id, name, price = row
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("Деталі", callback_data=f"details_{prod_id}"))
        bot.send_message(message.chat.id, f"{name}\n💸 {price} грн", reply_markup=btn)
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("details_"))
def show_details(call):
    prod_id = int(call.data.split("_")[1])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, description FROM products WHERE id=%s", (prod_id,))
    product = cur.fetchone()
    if product:
        name, price, desc = product
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("Замовити", callback_data=f"order_{prod_id}"))
        bot.send_message(call.message.chat.id, f"📦 {name}\n💸 {price} грн\n📝 {desc}", reply_markup=btn)
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_"))
def confirm_order(call):
    prod_id = int(call.data.split("_")[1])
    user = call.from_user
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, username, product_id) VALUES (%s, %s, %s)",
                (user.id, user.username, prod_id))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(call.message.chat.id, "✅ Замовлення оформлено. Адміністратор звʼяжеться з вами.")
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📥 НОВЕ ЗАМОВЛЕННЯ від @{user.username} (ID: {user.id}) на товар {prod_id}")

@bot.message_handler(commands=['feedback'])
def feedback(message):
    bot.send_message(message.chat.id, "✍️ Напишіть ваш відгук:")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feedback (user_id, username, message) VALUES (%s, %s, %s)",
                (message.from_user.id, message.from_user.username, message.text))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Дякуємо за відгук!")
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📢 ВІДГУК від @{message.from_user.username}: {message.text}")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.send_message(message.chat.id, "⛔ Ти не адміністратор.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/add_item', '/remove_item', '/orders')
    bot.send_message(message.chat.id, "🔧 Адмін-меню:", reply_markup=markup)

@bot.message_handler(commands=['add_item'])
def add_item(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "Введіть назву, ціну, опис через | (наприклад: Назва|999.99|Опис):")
    bot.register_next_step_handler(message, save_new_product)

def save_new_product(message):
    try:
        name, price, desc = message.text.split("|")
        price = float(price)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, description) VALUES (%s, %s, %s)",
                    (name.strip(), price, desc.strip()))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "✅ Товар додано.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Помилка. Спробуйте ще раз у форматі: Назва|999.99|Опис")

@bot.message_handler(commands=['remove_item'])
def remove_item(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "Введіть ID товару для видалення:")
    bot.register_next_step_handler(message, delete_product)

def delete_product(message):
    try:
        prod_id = int(message.text)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=%s", (prod_id,))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "🗑️ Товар видалено.")
    except:
        bot.send_message(message.chat.id, "❌ Невірний ID.")

@bot.message_handler(commands=['orders'])
def view_orders(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, o.user_id, o.username, p.name, o.created_at FROM orders o
        JOIN products p ON o.product_id = p.id ORDER BY o.created_at DESC
    """)
    text = "\n".join([f"{row[0]}. @{row[2]} - {row[3]} ({row[4]})" for row in cur.fetchall()]) or "Немає замовлень."
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, f"📦 Замовлення:\n{text}")

# Ініціалізація
create_tables()
seed_products_if_empty()
bot.polling(none_stop=True)
