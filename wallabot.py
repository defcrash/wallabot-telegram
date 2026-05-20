import os
import time
import http.server
import socketserver
import threading
import requests
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application

load_dotenv()

HISTORY_FILE = "products_history.txt"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- CONFIGURAÇÃO CRÍTICA AUTOMÁTICA ---
# Substitua o número abaixo pelo Chat ID longo do seu grupo do Telegram (obtido no JsonDumpBot, ex: -100xxxxxxxxxx)
CHAT_ID = -6791211542 

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

# --- Loop de Busca Perpétuo Autónomo ---
async def monitor_loop(application):
    print("[BOT] Ciclo de monitorização automática INICIADO!")
    
    # Envia uma mensagem inicial para o grupo a avisar que ligou
    try:
        await application.bot.send_message(CHAT_ID, "🚀 *Monitor de Consolas Ativo!* A procurar pechinchas na Wallapop de 3 em 3 minutos...", parse_mode="Markdown")
    except Exception as t_err:
        print(f"[ERRO TELEGRAM] Não conseguiu enviar mensagem inicial. Verifique o CHAT_ID ou se o bot está no grupo: {t_err}")

    while True:
        try:
            print("[BOT] A iniciar varrimento das URLs...")
            history = load_history()
            
            # Procura 1: Nintendo Switch OLED até 150€
            listings_oled = get_listings(keywords="nintendo switch oled", max_price="150")
            # Procura 2: Nintendo Switch até 100€ na categoria 24200 (Consolas)
            listings_normal = get_listings(keywords="nintendo switch", max_price="100", category_id="24200")
            
            all_listings = listings_oled + listings_normal
            
            novos_produtos = 0
            for product in all_listings:
                if product['url'] not in history:
                    message = f"🚨 *NOVO ARTIGO DETETADO!* 🚨\n\n🎯 *Título:* {product['title']}\n💰 *Preço:* {product['price']}\n\n🔗 *Link Direto:* {product['url']}"
                    await application.bot.send_message(CHAT_ID, message, parse_mode="Markdown")
                    history.add(product['url'])
                    novos_produtos += 1
                    time.sleep(1) # Pequena pausa entre mensagens
            
            save_history(history)
            print(f"[BOT] Varrimento concluído. {novos_produtos} novos alertas enviados. A aguardar 3 minutos...")
            
        except Exception as loop_err:
            print(f"[ERRO LOOP] Falha no ciclo: {loop_err}")
            
        await asyncio.sleep(180) # Aguarda 3 minutos de forma assíncrona pura

# --- Inicialização Direta sem Polling de comandos ---
async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    await application.initialize()
    await application.start()
    
    # Arranca o nosso loop eterno
    await monitor_loop(application)

if __name__ == "__main__":
    print("[SISTEMA] A arrancar o bot em modo automático...")
    asyncio.run(main())
