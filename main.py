import os
import telebot
from telebot import types
from db import get_db_connection, init_db
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logging.info(f"User {message.from_user.id} started bot")


# Ініціалізація бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Ініціалізація бази
init_db()

# ======================
# Команда /start
# ======================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/help', '/catalog', '/info', '/feedback')
    bot.send_message(message.chat.id, "Привіт! Я бот-магазин 🎉", reply_markup=markup)
    bot.send_message(message.chat.id, "Ось що я вмію:\n/help — список команд\n/catalog — каталог товарів")

# ======================
# Команда /help
# ======================
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "/start — почати\n/help — допомога\n/catalog — каталог\n/info — про бота\n/feedback — залишити відгук")

# ======================
# Команда /info
# ======================
@bot.message_handler(commands=['info'])
def info_command(message):
    bot.reply_to(message, "🤖 Це бот демонстраційного магазину. Тут ви можете переглянути товари та зробити замовлення!")

# ======================
# Команда /catalog
# ======================
@bot.message_handler(commands=['catalog'])
def catalog_command(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products")
    products = cur.fetchall()
    cur.close()
    conn.close()

    if not products:
        bot.send_message(message.chat.id, "Каталог поки що порожній 😢")
        return

    for prod in products:
        prod_id, name, price = prod
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Детальніше", callback_data=f"product_{prod_id}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"{name}\nЦіна: {price} грн", reply_markup=markup)

# ======================
# Обробка натискань кнопок (деталі товару)
# ======================
@bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
def callback_product_detail(call):
    prod_id = call.data.split("_")[1]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, description FROM products WHERE id = %s", (prod_id,))
    prod = cur.fetchone()
    cur.close()
    conn.close()

    if prod:
        name, price, desc = prod
        text = f"🛍 {name}\n💵 Ціна: {price} грн\n📄 Опис: {desc}"
        bot.send_message(call.message.chat.id, text)

# ======================
# Команда /feedback
# ======================
@bot.message_handler(commands=['feedback'])
def feedback_command(message):
    msg = bot.send_message(message.chat.id, "✍️ Залиште свій відгук:")
    bot.register_next_step_handler(msg, save_feedback)

def save_feedback(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feedback (user_id, message) VALUES (%s, %s)", (message.from_user.id, message.text))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Дякуємо за відгук! 🙌")

# ======================
# Запуск бота
# ======================
print("Бот запущено...")
bot.polling()

# 🔒 Список ID адміністраторів
ADMINS = [123456789]  # заміни на свій Telegram ID

# 🛒 Команда /order — імітація оформлення замовлення
@bot.message_handler(commands=['order'])
def order_command(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM products")
    products = cur.fetchall()
    cur.close()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for prod in products:
        markup.add(types.InlineKeyboardButton(prod[1], callback_data=f"order_{prod[0]}"))

    bot.send_message(message.chat.id, "Оберіть товар для замовлення:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_"))
def handle_order(call):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, product_id) VALUES (%s, %s)", (user_id, product_id))
    conn.commit()

    # Повідомлення для адміна
    for admin in ADMINS:
        bot.send_message(admin, f"Нове замовлення від користувача {user_id}\nТовар ID: {product_id}")

    bot.send_message(call.message.chat.id, "✅ Замовлення оформлено!")
    cur.close()
    conn.close()

# 🔧 /admin меню
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('/add_item', '/remove_item', '/orders')
        bot.send_message(message.chat.id, "Панель адміністратора 🛠", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⛔️ У вас немає прав доступу.")

# ➕ Додавання товару
@bot.message_handler(commands=['add_item'])
def add_item(message):
    if message.from_user.id not in ADMINS:
        return bot.send_message(message.chat.id, "⛔️ Ви не адміністратор.")
    msg = bot.send_message(message.chat.id, "Введіть товар у форматі:\nНазва, Ціна, Опис")
    bot.register_next_step_handler(msg, save_new_product)

def save_new_product(message):
    try:
        name, price, desc = message.text.split(",", 2)
        price = float(price.strip())  # Валідація
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, description) VALUES (%s, %s, %s)", (name.strip(), price, desc.strip()))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "✅ Товар додано.")
    except:
        bot.send_message(message.chat.id, "❌ Невірний формат. Спробуйте знову.")

# ❌ Видалення товару
@bot.message_handler(commands=['remove_item'])
def remove_item(message):
    if message.from_user.id not in ADMINS:
        return bot.send_message(message.chat.id, "⛔️ Ви не адміністратор.")
    msg = bot.send_message(message.chat.id, "Введіть ID товару для видалення:")
    bot.register_next_step_handler(msg, delete_product)

def delete_product(message):
    try:
        prod_id = int(message.text)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (prod_id,))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "✅ Товар видалено.")
    except:
        bot.send_message(message.chat.id, "❌ Помилка при видаленні.")

# 📦 Список замовлень
@bot.message_handler(commands=['orders'])
def orders_list(message):
    if message.from_user.id not in ADMINS:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT orders.id, orders.user_id, products.name 
        FROM orders JOIN products ON orders.product_id = products.id
    """)
    orders = cur.fetchall()
    cur.close()
    conn.close()

    if not orders:
        bot.send_message(message.chat.id, "Немає замовлень.")
    else:
        text = "\n".join([f"#{o[0]} — Користувач: {o[1]}, Товар: {o[2]}" for o in orders])
        bot.send_message(message.chat.id, text)

# 💬 Прості відповіді на запити
@bot.message_handler(func=lambda msg: msg.text.lower() in ["як зробити замовлення?", "які товари доступні?"])
def simple_answers(message):
    if "замовлення" in message.text:
        bot.send_message(message.chat.id, "Щоб зробити замовлення, скористайся командою /order.")
    else:
        bot.send_message(message.chat.id, "Доступні товари можна переглянути через /catalog.")
