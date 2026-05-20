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

# --- Servidor Falso Otimizado (Correção de Congelamento) ---
def run_fake_server():
    PORT = int(os.getenv("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    # Permite reutilizar a porta para evitar erros de bind pendentes
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[SERVIDOR] Porta {PORT} aberta e ativa para a Render.")
        httpd.serve_forever()

# Inicia o servidor web em paralelo para libertar o fluxo do Telegram
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

# --- Extrator via API Móvel Oficial ---
def get_listings(keywords, max_price, category_id=None):
    product_list = []
    search_query = keywords.replace(" ", "%20")
    
    api_url = f"https://wallapop.com{search_query}&max_sale_price={max_price}&order_by=newest&filters_source=search_box"
    if category_id:
        api_url += f"&category_ids={category_id}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "DeviceOS": "iOS"
    }
    
    try:
        print(f"[API] A consultar dados na Wallapop para: {keywords}")
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[API] Erro {response.status_code} para: {keywords}")
            return product_list

        data = response.json()
        items = data.get('search_objects', [])
        print(f"[API SUCESSO] Encontrados {len(items)} artigos para: {keywords}")

        for item in items:
            try:
                title = item.get('title', 'Artigo Wallapop')
                
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
        print(f"[API ERRO LIGAÇÃO] {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ A pesquisa de consolas foi INICIADA! A monitorizar a cada 3 minutos.")

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

# --- Comandos Ativadores (Reintroduzidos) ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"[COMANDO] /start recebido do chat ID: {chat_id}")
    await send_started_message(context, chat_id)
    
    # Remove qualquer busca anterior ativa para este chat para evitar duplicados
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    context.job_queue.run_repeating(
        check_new_products, interval=180, first=0, name=str(chat_id), data={'chat_id': chat_id})

async def stop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"[COMANDO] /stop recebido do chat ID: {chat_id}")
    
    # Desliga a busca especificamente para este chat
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    await send_stopped_message(context, chat_id)

# --- Inicialização Padrão Polling ---
if __name__ == "__main__":
    print("[SISTEMA] A iniciar escuta de comandos por Polling...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.run_polling()
