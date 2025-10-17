# Используем официальный Python образ
FROM python:3.11-slim

# Нестрочный вывод логов в stdout/stderr
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY REQUIREMENTS.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r REQUIREMENTS.txt

# Копируем код приложения
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Открываем порт для health-check (/health) и совместимости с оркестраторами
EXPOSE 8080

# Запускаем бота
CMD ["python", "bot.py"]
