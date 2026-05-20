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

# --- Servidor Falso Otimizado para a Render ---
def run_fake_server():
    PORT = int(os.getenv("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
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

# --- Extrator via API Geral Otimizado (Correção da Rota e Paginação) ---
def get_listings(keywords, max_price, category_id=None):
    product_list = []
    search_query = keywords.replace(" ", "%20")
    
    # Rota oficial e atualizada da API da Wallapop com parâmetros obrigatórios
    api_url = f"https://wallapop.com{search_query}&max_sale_price={max_price}&order_by=newest&is_first_page=true&filters_source=quick_filters"
    
    if category_id:
        api_url += f"&category_ids={category_id}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[API] Erro {response.status_code} para: {keywords}")
            return product_list

        data = response.json()
        
        # A rota 'general/search' organiza os produtos dentro de 'search_objects'
        items = data.get('search_objects', [])
        if not items:
            items = data.get('data', {}).get('items', [])
            
        print(f"[API SUCESSO] {keywords}: Detetados {len(items)} artigos estruturados.")

        for item in items:
            try:
                # Trata a estrutura de dados interna da API geral
                title = item.get('title') or item.get('title', {}).get('text') or 'Artigo Wallapop'
                
                price_data = item.get('price', {})
                if isinstance(price_data, dict):
                    price_val = price_data.get('amount') or price_data.get('cash') or 0
                else:
                    price_val = price_data or 0
                price = f"{price_val}€"
                
                web_slug = item.get('web_slug') or item.get('slug')
                if web_slug:
                    url_prod = f"https://wallapop.com{web_slug}"
                else:
                    item_id = item.get('id')
                    if item_id:
                        url_prod = f"https://wallapop.com{item_id}"
                    else:
                        continue

                product_info = {"title": str(title), "price": str(price), "url": str(url_prod)}
                product_list.append(product_info)
            except Exception:
                continue
    except Exception as e:
        print(f"[API ERRO] {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ A pesquisa de consolas foi INICIADA! A monitorizar a cada 3 minutos via API pública.")

async def send_stopped_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "🛑 A pesquisa foi PARADA. Pode ir dormir descansado!")

# --- Processador de Fila de Busca ---
async def check_new_products(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    print(f"[BOT] A iniciar varrimento para o chat: {chat_id}")
    history = load_history()
    
    listings_oled = get_listings(keywords="nintendo switch oled", max_price="150")
    listings_normal = get_listings(keywords="nintendo switch", max_price="100", category_id="24200")
    
    all_listings = listings_oled + listings_normal
    
    novos_produtos = 0
    for product in all_listings:
        if product['url'] not in history:
            await send_new_product_message(context, chat_id, product)
            history.add(product['url'])
            novos_produtos += 1
            time.sleep(1)
            
    save_history(history)
    print(f"[BOT] Varrimento concluído. {novos_produtos} alertas enviados. A aguardar 3 minutos...")

# --- Comandos Ativadores ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"[COMANDO] /start recebido do chat ID: {chat_id}")
    await send_started_message(context, chat_id)
    
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    context.job_queue.run_repeating(
        check_new_products, interval=180, first=0, name=str(chat_id), data={'chat_id': chat_id})

async def stop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"[COMANDO] /stop recebido do chat ID: {chat_id}")
    
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    await send_stopped_message(context, chat_id)

# --- Inicialização ---
if __name__ == "__main__":
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.run_polling()
