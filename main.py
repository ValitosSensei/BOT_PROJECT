import os
import logging
import psycopg2
from psycopg2 import sql
from telebot import TeleBot, types
from dotenv import load_dotenv

# Завантаження змінних оточення
load_dotenv()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Підключення до PostgreSQL
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

# Ініціалізація бота
bot = TeleBot(os.environ['API_TOKEN'])

# Мови та локалізації
LANGUAGES = {
    'en': {
        'welcome': "Welcome! Choose command:",
        'product_list': "Available products:",
        # ... інші переклади
    },
    'uk': {
        'welcome': "Ласкаво просимо! Оберіть команду:",
        'product_list': "Доступні товари:",
        # ... інші переклади
    }
}

# --- Допоміжні функції ---
def get_user_language(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT language FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone()[0] if cur.rowcount else 'uk'

def log_user_action(user_id, action):
    logger.info(f"User {user_id}: {action}")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_logs (user_id, action) 
                VALUES (%s, %s)
            """, (user_id, action))

# --- Обробники команд ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, state, language) 
                VALUES (%s, 'main_menu', 'uk')
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*['/catalog', '/help', '/info', '/language'])
    
    bot.send_message(
        message.chat.id,
        LANGUAGES[get_user_language(user_id)]['welcome'],
        reply_markup=markup
    )
    log_user_action(user_id, "Started bot")

# --- Каталог товарів ---
@bot.message_handler(commands=['catalog'])
def handle_catalog(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price FROM products")
            products = cur.fetchall()
    
    markup = types.InlineKeyboardMarkup()
    for product in products:
        markup.add(types.InlineKeyboardButton(
            text=f"{product[1]} - {product[2]}₴",
            callback_data=f"product_{product[0]}"
        ))
    
    bot.send_message(
        message.chat.id,
        LANGUAGES[lang]['product_list'],
        reply_markup=markup
    )
    log_user_action(user_id, "Opened catalog")

# --- Адмін-меню ---
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    user_id = message.from_user.id
    if user_id not in [int(id) for id in os.environ['ADMIN_IDS'].split(',')]:
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*['/add_product', '/remove_product', '/view_orders'])
    
    bot.send_message(message.chat.id, "Адмін-панель", reply_markup=markup)
    log_user_action(user_id, "Accessed admin panel")

# --- Інтеграція з базою даних ---
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    state VARCHAR(50),
                    language VARCHAR(2)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    price NUMERIC,
                    description TEXT
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

if __name__ == '__main__':
    init_db()
    logger.info("Starting bot...")
    bot.infinity_polling()
