import os
import time
import json
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

# --- Extrator Científico via JSON Oculto (Correção de Preço Ativada) ---
def get_listings(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.set_page_load_timeout(30)
    product_list = []
    
    try:
        driver.get(url)
        time.sleep(6)
        
        json_element = driver.find_element(By.ID, "__NEXT_DATA__")
        json_text = json_element.get_attribute("innerHTML")
        data = json.loads(json_text)
        
        try:
            items = data['props']['pageProps']['initKeywordsData']['items']
        except KeyError:
            try:
                items = data['props']['pageProps']['searchResult']['items']
            except KeyError:
                items = []

        for item in items:
            try:
                title = item.get('title', 'Nintendo Switch (Ver Link)')
                
                # --- EXTRAÇÃO DE PREÇO ADAPTIVA ---
                price_data = item.get('price')
                price_val = None

                if isinstance(price_data, dict):
                    # Tenta ler as chaves comuns em objetos de preço modernos da Wallapop
                    price_val = price_data.get('amount') or price_data.get('cash') or price_data.get('total')
                elif isinstance(price_data, (int, float)):
                    # Se vier diretamente como número bruto
                    price_val = price_data
                
                # Se ainda assim não encontrar no objeto 'price', procura no topo do item
                if not price_val:
                    price_val = item.get('amount') or item.get('salePrice')

                # Formata a string final para o Telegram
                if price_val is not None:
                    price = f"{price_val}€"
                else:
                    price = "Consultar no Link"
                # ----------------------------------

                web_slug = item.get('webSlug')
                if web_slug:
                    url_prod = f"https://wallapop.com{web_slug}"
                else:
                    continue

                product_info = {"title": title, "price": price, "url": url_prod}
                product_list.append(product_info)
                
            except Exception:
                continue

    except Exception as e:
        print(f"Erro ao processar estrutura JSON: {e}")
    finally:
        driver.quit()
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ A pesquisa na Wallapop foi REINICIADA! Monitorização de dados brutos ativa a cada 3 minutos.")

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
            print(f"Erro na fila de processamento: {e}")

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
