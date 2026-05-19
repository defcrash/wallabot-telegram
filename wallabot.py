import os
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

import http.server
import socketserver
import threading

# Cria um servidor web falso numa porta qualquer para a Render ficar feliz
def run_fake_server():
    PORT = int(os.getenv("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

# Inicia o servidor web falso numa linha paralela (thread)
threading.Thread(target=run_fake_server, daemon=True).start()


HISTORY_FILE = "products_history.txt"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
WALLAPOP_URL = os.getenv("WALLAPOP_URL")


def load_history():
    history = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as file:
            history.update(file.read().splitlines())
    return history


def save_history(history):
    with open(HISTORY_FILE, 'w') as file:
        for product in history:
            file.write(f"{product}\n")


def get_listings(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(10)


    all_products = driver.find_elements(
        By.CLASS_NAME, "item-card_ItemCard--vertical__CNrfk")
    product_list = []

    for product in all_products:
        try:
            try:
                title = product.find_element(
                    By.CLASS_NAME, "item-card_ItemCard__title__5TocV").text
            except NoSuchElementException:
                title = None

            try:
                price = product.find_element(
                    By.CLASS_NAME, "item-card_ItemCard__price__pVpdc").text
            except NoSuchElementException:
                price = None

            try:
                url = product.get_attribute("href")
            except NoSuchElementException:
                url = None
            product_info = {"title": title, "price": price, "url": url}
            product_list.append(product_info)

        except Exception as e:
            print(f"Error processing the product: {e}")
            continue

    driver.quit()
    return product_list


async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"New product found:\n\nTitle: {product['title']}\nPrice: {product['price']}\nURL: {product['url']}"
    await context.bot.send_message(chat_id, message)


async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "Product search started!")


async def send_stopped_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "Product search stopped!")


async def check_new_products(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    history = load_history()
    
    # Divide a variável WALLAPOP_URL por vírgulas, limpando espaços
    urls = [url.strip() for url in WALLAPOP_URL.split(",")]
    
    # Corre o monitor para cada um dos links configurados
    for url in urls:
        if not url:
            continue
        try:
            listings = get_listings(url)
            for product in listings:
                if product['url'] not in history:
                    await send_new_product_message(context, chat_id, product)
                    history.add(product['url'])
            time.sleep(2) # Pequena pausa entre links para evitar bloqueios
        except Exception as e:
            print(f"Erro ao processar o link {url}: {e}")

    save_history(history)


async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await send_started_message(context, chat_id)
    context.job_queue.run_repeating(
        check_new_products, interval=60, first=0, data={'chat_id': chat_id})


async def stop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.job_queue.stop()
    await send_stopped_message(context, chat_id)

application = Application.builder().token(TELEGRAM_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stop", stop))

application.run_polling()
