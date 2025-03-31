import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from selenium import webdriver

HISTORY_FILE = "products_history.txt"
TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"
WALLAPOP_URL = "https://es.wallapop.com/app/search"

def load_history():
    pass

def save_history(history):
    pass

def get_listings(url):
    pass

def start(update: Update, context: CallbackContext):
    pass

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
