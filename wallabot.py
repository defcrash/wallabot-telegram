import os
import time
import json
import re
import http.server
import socketserver
import threading
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

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

# --- Extrator Inteligente Ultra-Leve (Sem Navegador/Sem Selenium) ---
def get_listings(url):
    product_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"
    }
    
    try:
        # Faz o download do texto puro da página em milissegundos
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Wallapop respondeu com erro {response.status_code}")
            return product_list

        # Procura o bloco JSON __NEXT_DATA__ diretamente no texto usando Expressões Regulares (Regex)
        match = re.search(r'<script id="__NEXT_DATA__" type="application\/json">(.*?)<\/script>', response.text)
        
        if match:
            json_text = match.group(1)
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
                    
                    # Extração precisa do preço dentro do objeto nativo
                    price_data = item.get('price', {})
                    if isinstance(price_data, dict):
                        price_val = price_data.get('amount') or price_data.get('cash')
                    else:
                        price_val = price_data
                    
                    if not price_val:
                        price_val = item.get('price')

                    price = f"{price_val}€" if price_val else "Ver no Link"

                    web_slug = item.get('webSlug')
                    if web_slug:
                        url_prod = f"https://wallapop.com{web_slug}"
                    else:
                        continue

                    product_info = {"title": title, "price": price, "url": url_prod}
                    product_list.append(product_info)
                    
                except Exception:
                    continue
        else:
            print("Não foi possível localizar o bloco de dados oculto da Wallapop.")

    except Exception as e:
        print(f"Erro na requisição direta: {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ Sistema de Monitorização Ativo 24/7! Busca ultra-rápida a cada 3 minutos.")

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
            time.sleep(2)
        except Exception as e:
            print(f"Erro na fila: {e}")

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
