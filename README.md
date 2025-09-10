# Wallabot Telegram

## 📌 Table of Contents
- [English Version](#english-version)
- [Versión en Español](#versión-en-español)

---

# English Version

A Python-based scraper that monitors [Wallapop](https://es.wallapop.com/) for new product listings and instantly notifies you via a Telegram bot.  
The goal is to give you **real-time alerts** when a new item matching your search appears, so you can act faster than others.

---

## ✨ Features
- Scrapes Wallapop listings using **Selenium**.
- Detects new items and keeps track of previously seen products.
- Sends instant notifications through a **Telegram bot**.
- Configurable search URL, Telegram token, and Chromedriver path via `.env` file.
- Start and stop the bot easily with Telegram commands:
  - `/start` → Begin monitoring.
  - `/stop` → Stop monitoring.

---

## ⚙️ Requirements
- [Python 3.8+](https://www.python.org/downloads/)  
- [Google Chrome](https://www.google.com/chrome/) installed on your system.  
- [Chromedriver](https://googlechromelabs.github.io/chrome-for-testing/) matching your Chrome version.  
- A Telegram bot token (create one with [BotFather](https://t.me/botfather)).  

---

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/agilalonso/wallabot-telegram.git
   cd wallabot-telegram
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment variables:

   Copy the example file and update it with your own values:
   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and set:
   - **TELEGRAM_TOKEN** → Token from your Telegram bot.  
   - **CHROMEDRIVER_PATH** → Absolute path to your local Chromedriver.  
   - **WALLAPOP_URL** → The Wallapop search URL you want to monitor. **Make sure the listings are sorted by 'Most recent' for accurate real-time alerts.**

---

## ▶️ Usage

Run the bot with:

```bash
python wallabot.py
```

In Telegram:
- Send `/start` to your bot to begin monitoring.  
- Send `/stop` to pause monitoring.  

The bot will send you alerts with the **title, price, and link** of any new product found.

---

## 📁 Project Structure
```
.
├── wallabot.py            # Main bot script
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── .env                   # Actual environment variables (not committed)
├── LICENSE                # License file (MIT)
└── products_history.txt   # Keeps track of already-seen items
```

---

## 📜 License
This project is licensed under the MIT License.  
See [LICENSE](./LICENSE) for details.

---

# Versión en Español

Un scraper hecho en Python que monitoriza [Wallapop](https://es.wallapop.com/) en busca de nuevos productos y te notifica al instante mediante un bot de Telegram.  
El objetivo es que recibas **alertas en tiempo real** cuando aparezca un artículo nuevo en tu búsqueda, para que puedas reaccionar antes que los demás.

---

## ✨ Funcionalidades
- Hace scraping de anuncios en Wallapop usando **Selenium**.  
- Detecta nuevos productos y guarda un historial de los ya vistos.  
- Envía notificaciones instantáneas a través de un **bot de Telegram**.  
- Configuración mediante archivo `.env` para la URL de búsqueda, token de Telegram y ruta de Chromedriver.  
- Control sencillo desde Telegram:
  - `/start` → Comienza a monitorizar.  
  - `/stop` → Detiene la monitorización.  

---

## ⚙️ Requisitos
- [Python 3.8+](https://www.python.org/downloads/)  
- [Google Chrome](https://www.google.com/chrome/) instalado en tu sistema.  
- [Chromedriver](https://googlechromelabs.github.io/chrome-for-testing/) compatible con tu versión de Chrome.  
- Un token de bot de Telegram (se crea con [BotFather](https://t.me/botfather)).  

---

## 📦 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/agilalonso/wallabot-telegram.git
   cd wallabot-telegram
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura tus variables de entorno:

   Copia el archivo de ejemplo y edítalo con tus propios valores:
   ```bash
   cp .env.example .env
   ```

   Después edita `.env` y define:  
   - **TELEGRAM_TOKEN** → Token de tu bot de Telegram.  
   - **CHROMEDRIVER_PATH** → Ruta absoluta a tu Chromedriver.  
   - **WALLAPOP_URL** → La URL de búsqueda de Wallapop que quieres monitorizar. **Asegúrate de que los resultados estén ordenados por 'Más reciente' para recibir alertas en tiempo real correctamente.** 

---

## ▶️ Uso

Ejecuta el bot con:

```bash
python wallabot.py
```

En Telegram:  
- Envía `/start` a tu bot para empezar la monitorización.  
- Envía `/stop` para detenerla.  

El bot te enviará alertas con el **título, precio y enlace** de cada nuevo producto encontrado.

---

## 📁 Estructura del Proyecto
```
.
├── wallabot.py            # Script principal del bot
├── requirements.txt       # Dependencias de Python
├── .env.example           # Variables de entorno de ejemplo
├── .env                   # Variables de entorno reales (no se suben al repo)
├── LICENSE                # Archivo de licencia (MIT)
└── products_history.txt   # Guarda el historial de productos vistos
```

---

## 📜 Licencia
Este proyecto está bajo la licencia MIT.  
Consulta [LICENSE](./LICENSE) para más información.

