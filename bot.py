import logging
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from news_fetcher import get_stock_news

# Hardcoded bot token
TOKEN = ""

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Ensure database exists and is initialized
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, stock_symbol TEXT)"
    )
    conn.commit()
    conn.close()

init_db()

# Synchronous function to send news updates
async def send_news(context: CallbackContext):
    logging.info("Checking for stock news...")
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    for user_id, stock_symbol in users:
        logging.info(f"Fetching news for {stock_symbol}")
        news = get_stock_news(stock_symbol)
        if news:
            for article in news:
                logging.info(f"Sending news for {stock_symbol}")
                try:
                    # Await the send_message call
                    await context.bot.send_message(chat_id=user_id, text=article)
                except Exception as e:
                    logging.error(f"Error sending message to {user_id}: {e}")
        else:
            logging.info(f"No news found for {stock_symbol}")
    conn.close()

# Start command handler (remains async)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Use /subscribe <stock_symbol> to get news updates.")

# Subscribe command handler (remains async)
async def subscribe(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    stock_symbol = " ".join(context.args).upper()
    if not stock_symbol:
        await update.message.reply_text("Usage: /subscribe <stock_symbol>")
        return

    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, stock_symbol) VALUES (?, ?)", (user_id, stock_symbol))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Subscribed to news updates for {stock_symbol}")

# Unsubscribe command handler (remains async)
async def unsubscribe(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text("Unsubscribed from stock news updates.")

# Function to run the async send_news function in the scheduler
def run_async_send_news(app_bot):
    # Run the async function in an event loop
    asyncio.create_task(send_news(app_bot))

# Main function to start the bot
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Schedule job to run every 1 minute (60 seconds)
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_async_send_news, IntervalTrigger(minutes=1), id="send_stock_news", args=[app.bot])
    scheduler.start()

    logging.info("Bot is running using long polling...")
    app.run_polling()

if __name__ == "__main__":
    main()

