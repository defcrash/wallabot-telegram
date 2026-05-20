import os
import time
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

# --- Extrator via API Móvel com Parâmetros Diretos ---
def get_listings(keywords, max_price, category_id=None):
    product_list = []
    
    # Substitui espaços por %20 para o link ficar correto
    search_query = keywords.replace(" ", "%20")
    
    # Reconstrói a URL nativa que a App de telemóvel da Wallapop usa
    api_url = f"https://wallapop.com{search_query}&max_sale_price={max_price}&order_by=newest&filters_source=search_box"
    
    if category_id:
        api_url += f"&category_ids={category_id}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "DeviceOS": "iOS"
    }
    
    try:
        print(f"[API] A consultar dados: {keywords} até {max_price}€")
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[API ERRO] Código do servidor: {response.status_code}")
            return product_list

        data = response.json()
        items = data.get('search_objects', [])
        print(f"[SUCESSO] Detetados {len(items)} artigos na API para: {keywords}")

        for item in items:
            try:
                title = item.get('title', 'Artigo Wallapop')
                
                # Extração do preço
                price_data = item.get('price', {})
                if isinstance(price_data, dict):
                    price_val = price_data.get('amount') or price_data.get('cash') or 0
                else:
                    price_val = price_data or 0
                price = f"{price_val}€"
                
                web_slug = item.get('web_slug')
                if web_slug:
                    url_prod = f"https://pt.wallapop.com/item/{web_slug}"
                else:
                    continue

                product_info = {"title": str(title), "price": str(price), "url": str(url_prod)}
                product_list.append(product_info)
                
            except Exception:
                continue

    except Exception as e:
        print(f"[FALHA] Erro na ligação: {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ Monitorização direta por API ativada a cada 3 minutos!")

async def send_stopped_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "🛑 Pesquisa parada.")

# --- Processador de Fila de Busca ---
async def check_new_products(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    history = load_history()
    
    # Executa a busca 1: Nintendo Switch OLED
    listings_oled = get_listings(keywords="nintendo switch oled", max_price="160")
    # Executa a busca 2: Nintendo Switch Normal na categoria de Consolas (24200)
    listings_normal = get_listings(keywords="nintendo switch", max_price="100", category_id="24200")
    
    # Junta as duas listas de resultados
    all_listings = listings_oled + listings_normal
    
    for product in all_listings:
        if product['url'] not in history:
            await send_new_product_message(context, chat_id, product)
            history.add(product['url'])
            
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
