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

# --- Conversor Inteligente e Blindado ---
def convert_url_to_api(web_url):
    try:
        # Se já for um link da API ou contiver os parâmetros limpos
        if "://wallapop.com" in web_url:
            return web_url
            
        # Abordagem direta por extração de texto (limpa colchetes, plicas e espaços)
        keywords = ""
        max_price = ""
        category_id = ""
        
        if "keywords=" in web_url:
            keywords = web_url.split("keywords=")[1].split("&")[0]
        if "max_sale_price=" in web_url:
            max_price = web_url.split("max_sale_price=")[1].split("&")[0]
        if "category_id=" in web_url:
            category_id = web_url.split("category_id=")[1].split("&")[0]
            
        # Se for um link antigo da Wallapop com 'category_ids'
        if "category_ids=" in web_url:
            category_id = web_url.split("category_ids=")[1].split("&")[0]

        # Monta a URL da API nativa com texto 100% limpo
        api_url = f"https://://wallapop.com/api/v3/general/search?keywords={keywords}&filters_source=search_box"
        if max_price:
            api_url += f"&max_sale_price={max_price}"
        if category_id:
            api_url += f"&category_ids={category_id}"
            
        api_url += "&order_by=newest"
        return api_url
    except Exception as e:
        print(f"[ERRO CONVERSOR] {e}")
        return None

# --- Extrator Ultra-Estável via API Interna ---
def get_listings(web_url):
    product_list = []
    api_url = convert_url_to_api(web_url)
    
    if not api_url:
        return product_list
        
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "DeviceOS": "iOS"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[API ERRO] Código {response.status_code} para o link convertido.")
            return product_list

        data = response.json()
        items = data.get('search_objects', [])
        print(f"[SUCESSO API] Itens localizados no servidor: {len(items)}")

        for item in items:
            try:
                title = item.get('title', 'Nintendo Switch')
                
                # Extração do preço
                price_data = item.get('price', {})
                if isinstance(price_data, dict):
                    price_val = price_data.get('amount') or price_data.get('cash') or 0
                else:
                    price_val = price_data or 0
                price = f"{price_val}€"
                
                web_slug = item.get('web_slug')
                if web_slug:
                    url_prod = f"https://wallapop.com{web_slug}"
                else:
                    continue

                product_info = {"title": str(title), "price": str(price), "url": str(url_prod)}
                product_list.append(product_info)
                
            except Exception:
                continue

    except Exception as e:
        print(f"[FALHA RECONEXÃO] Erro geral: {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ Sistema Ativo! Monitorização direta da API a cada 3 minutos.")

async def send_stopped_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "🛑 Pesquisa parada.")

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
            print(f"[ERRO FILA] Falha no processamento: {e}")

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
