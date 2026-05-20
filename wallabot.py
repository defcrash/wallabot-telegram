import os
import time
import http.server
import socketserver
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

load_dotenv()

HISTORY_FILE = "products_history.txt"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WALLAPOP_URL = os.getenv("WALLAPOP_URL")

# --- Servidor Falso para a Render não ir abaixo ---
def run_fake_server():
    PORT = int(os.getenv("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# --- Funções de Histórico ---
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

# --- Extrator Otimizado com Limites de Tempo Alargados ---
def get_listings(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    
    # Define limites de tempo para o Chrome não ficar "preso" para sempre se a rede falhar
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    
    try:
        driver.get(url)
        time.sleep(8)  # Tempo equilibrado para carregar o conteúdo na Render
    except Exception as page_error:
        print(f"Aviso no carregamento da página: {page_error}")

    # Captura os links dos produtos usando um padrão XPATH universal
    all_products = driver.find_elements(By.XPATH, "//a[contains(@href, '/item/')]")
    product_list = []

    for product in all_products:
        try:
            url_prod = product.get_attribute("href")
            if not url_prod or "/item/" not in url_prod:
                continue

            # CORREÇÃO CRÍTICA: Mantém o link como string limpa, removendo parâmetros de tracking
            if "?" in url_prod:
                url_prod = url_prod.split("?")[0]

            # Extração do Título
            title = product.get_attribute("title")
            if not title:
                try:
                    title = product.find_element(By.XPATH, ".//p[contains(@class, 'title')]").text
                except NoSuchElementException:
                    try:
                        title = product.find_element(By.XPATH, ".//div[contains(@class, 'ItemCard__info')]").text
                    except NoSuchElementException:
                        title = "Nintendo Switch (Consulte o Link)"

            # Extração do Preço (Procura o símbolo do Euro €)
            try:
                price = product.find_element(By.XPATH, ".//*[contains(text(), '€')]").text
            except NoSuchElementException:
                price = "Ver Preço na Aplicação"

            product_info = {"title": title, "price": price, "url": url_prod}
            
            # Evita duplicados na lista temporária
            if product_info not in product_list:
                product_list.append(product_info)

        except Exception as e:
            continue

    driver.quit()
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ A pesquisa na Wallapop foi INICIADA com sucesso! A monitorizar os seus múltiplos links a cada 3 minutos.")

async def send_stopped_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "🛑 A pesquisa foi PARADA. Use /start para retomar.")

# --- Processador de Fila de Busca ---
async def check_new_products(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    history = load_history()
    
    urls = [url.strip() for url in WALLAPOP_URL.split(",")]
    
    for url in urls:
        if not url:
            continue
        try:
            listings = get_listings(url)
            for product in listings:
                if product['url'] not in history:
                    await send_new_product_message(context, chat_id, product)
                    history.add(product['url'])
            time.sleep(3)
        except Exception as e:
            print(f"Erro ao processar o link: {e}")

    save_history(history)

# --- Comandos Ativadores ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await send_started_message(context, chat_id)
    context.job_queue.run_repeating(
        check_new_products, interval=180, first=0, data={'chat_id': chat_id})

async def stop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    await context.job_queue.stop()
    await send_stopped_message(context, chat_id)

# --- Inicialização do Bot ---
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stop", stop))
application.run_polling()
