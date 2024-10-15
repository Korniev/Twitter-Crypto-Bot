FROM python:3.11-slim

# Встановимо всі необхідні пакети для роботи з SSL та іншими залежностями
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl

# Створюємо робочий каталог у контейнері
WORKDIR /app

# Копіюємо файл залежностей requirements.txt у контейнер
COPY requirements.txt requirements.txt

# Встановлюємо всі залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код у контейнер
COPY . .

# Запускаємо скрипт
CMD ["python3", "main.py"]
