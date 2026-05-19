# Usa uma imagem oficial do Python que já vem com o Chrome e o Chromedriver instalados
FROM joyzoursae/selenium-python-chrome:latest

# Define a pasta de trabalho dentro do servidor
WORKDIR /app

# Copia os ficheiros do seu GitHub para o servidor
COPY requirements.txt .
COPY wallabot.py .

# Instala as bibliotecas de Python necessárias (como o telebot ou requests)
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar o seu monitor automaticamente
CMD ["python", "wallabot.py"]
