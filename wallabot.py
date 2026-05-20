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

# --- Extrator com Logs de Diagnóstico Avançados ---
def get_listings(url):
    product_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        print(f"[DIAGNÓSTICO] A tentar ler o URL: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERRO REDE] Wallapop barrou o acesso com o status: {response.status_code}")
            return product_list

        # Procura o bloco JSON
        match = re.search(r'<script id="__NEXT_DATA__" type="application\/json">(.*?)<\/script>', response.text)
        
        if match:
            json_text = match.group(1)
            data = json.loads(json_text)
            
            # Tenta localizar a árvore de produtos em diferentes ramificações da Wallapop
            items = []
            paths_to_test = [
                ['props', 'pageProps', 'initKeywordsData', 'items'],
                ['props', 'pageProps', 'searchResult', 'items'],
                ['props', 'pageProps', 'seoStructuredData', 'itemListElement']
            ]
            
            for path in paths_to_test:
                try:
                    temp_data = data
                    for key in path:
                        temp_data = temp_data[key]
                    if temp_data:
                        items = temp_data
                        print(f"[SUCESSO JSON] Produtos localizados no caminho: {' -> '.join(path)}")
                        break
                except KeyError:
                    continue

            print(f"[DIAGNÓSTICO] Total de itens brutos detetados no JSON: {len(items)}")

            for item in items:
                try:
                    # Se for o formato estruturado do SEO, o mapeamento muda ligeiramente
                    if 'item' in item:
                        item = item['item']

                    title = item.get('title') or item.get('name') or 'Nintendo Switch'
                    
                    # Correção absoluta do Preço de forma aninhada
                    price_val = None
                    if 'price' in item:
                        if isinstance(item['price'], dict):
                            price_val = item['price'].get('amount') or item['price'].get('cash')
                        else:
                            price_val = item['price']
                    
                    if not price_val:
                        price_val = item.get('amount') or item.get('salePrice')

                    price = f"{price_val}€" if price_val else "Consultar Preço"

                    # Garante que criamos uma String limpa e válida para o histórico
                    web_slug = item.get('webSlug') or item.get('slug')
                    if web_slug:
                        url_prod = f"https://wallapop.com{web_slug}"
                    else:
                        # Fallback se o ID direto ou URL já vierem montados
                        url_prod = item.get('url') or item.get('href')
                    
                    if not url_prod:
                        continue

                    # Converte explicitamente para String normal para o histórico não falhar
                    url_prod = str(url_prod).split("?")[0]

                    product_info = {"title": str(title), "price": str(price), "url": url_prod}
                    product_list.append(product_info)
                    
                except Exception as item_err:
                    print(f"[ERRO ITEM] Falha ao ler um produto individual: {item_err}")
                    continue
        else:
            print("[CIBERSEGURANÇA] O bloco __NEXT_DATA__ não foi encontrado no HTML. A Wallapop barrou o servidor ou alterou a página.")

    except Exception as e:
        print(f"[ERRO GERAL] Falha crítica na requisição: {e}")
        
    return product_list

# --- Mensagens do Telegram ---
async def send_new_product_message(context: CallbackContext, chat_id, product):
    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
    await context.bot.send_message(chat_id, message, parse_mode="Markdown")

async def send_started_message(context: CallbackContext, chat_id):
    await context.bot.send_message(chat_id, "✅ Monitorização com logs de diagnóstico iniciada a cada 3 minutos.")

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
            print(f"[DIAGNÓSTICO] Produtos prontos para validação no histórico: {len(listings)}")
            for product in listings:
                if product['url'] not in history:
                    print(f"[TELEGRAM] A enviar novo anúncio: {product['title']}")
                    await send_new_product_message(context, chat_id, product)
                    history.add(product['url'])
            time.sleep(2)
        except Exception as e:
            print(f"[ERRO FILA] Falha no processamento da lista: {e}")

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
