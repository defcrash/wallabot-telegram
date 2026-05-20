import os
import time
import http.server
import socketserver
import threading
import requests
from urllib.parse import urlparse, parse_qs
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

# --- Conversor de Link Web para Chamada de API Nativa Otimizado ---
def convert_url_to_api(web_url):
    try:
        parsed_url = urlparse(web_url)
        params = parse_qs(parsed_url.query)
        
        # Extrai os filtros limpando os caracteres de listas do Python
        keywords = params.get('keywords', [''])[0]
        max_price = params.get('max_sale_price', [''])[0]
        category_id = params.get('category_id', [''])[0] # Corrigido de category_ids para category_id
        
        # Substitui espaços vazios por %20 para links válidos
        keywords = keywords.replace(" ", "%20")
        
        # Monta o pedido com os valores limpos em formato string puro
        api_url = f"https://wallapop.com{keywords}&filters_source=search_box"
        
        if max_price:
            api_url += f"&max_sale_price={max_price}"
        if category_id:
            api_url += f"&category_ids={category_id}"
            
        api_url += "&order_by=newest"
        return api_url
    except Exception as e:
        print(f"[ERRO INTERNO CONVERSOR] {e}")
        return None

# --- Extrator Ultra-Estável via API Interna ---
def get_listings(web_url):
    product_list = []
    api_url = convert_url_to_api(web_url)
    
    if not api_url:
        print("[ERRO URL] Não foi possível converter o link.")
        return product_list
        
    headers = {
        "User-Agent": "Wallapop/3.166.0 (iPhone; iOS 16.0; Scale/3.00)",
        "Accept": "application/json",
        "DeviceOS": "iOS"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[API ERRO] Código de resposta: {response.status_code}")
            return product_list

        data = response.json()
        # Aceder diretamente à lista de objetos enviados pelo servidor
        items = data.get('search_objects', [])
        print(f"[SUCESSO API] Itens localizados no servidor Wallapop: {len(items)}")

        for item in items:
            try:
                title = item.get('title', 'Nintendo Switch')
                price_val = item.get('price', {}).get('amount') or item.get('price', 0)
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
        print(f"[FALHA RECONEXÃO] Erro ao contactar a API: {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ Sistema de Monitorização por API ativo a cada 3 minutos!")

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
