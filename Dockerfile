# 1. Usa a imagem oficial estável do Python
FROM python:3.10-slim

# 2. Instala dependências do sistema e utilitários
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Descarrega e instala o Google Chrome estável oficial
RUN wget -q -O - https://google.com | apt-key add - \
    && echo "deb [arch=amd64] http://google.com stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 4. Define a pasta de trabalho
WORKDIR /app

# 5. Copia os ficheiros
COPY requirements.txt .
COPY wallabot.py .

# 6. Instala as bibliotecas de Python incluindo o gestor automático de drivers (webdriver-manager)
RUN pip install --no-cache-dir python-telegram-bot[ext] selenium python-dotenv webdriver-manager

# 7. Executa o script
CMD ["python", "wallabot.py"]
