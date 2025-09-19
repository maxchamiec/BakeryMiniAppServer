#!/bin/bash

# Команды для перезапуска приложения на сервере
# Выполняйте по порядку:

echo "🔄 Перезапуск приложения..."

# 1. Подключение к серверу
echo "1. Подключение к серверу:"
echo "ssh root@miniapp.drazhin.by"

# 2. Переход в директорию приложения
echo "2. Переход в директорию:"
echo "cd /home/drazhinb/miniapp"

# 3. Остановка текущего процесса (если запущен)
echo "3. Остановка текущего процесса:"
echo "pkill -f wsgi.py"
echo "pkill -f python3"

# 4. Обновление кода из GitHub
echo "4. Обновление кода:"
echo "git fetch origin"
echo "git checkout WebApp_relocation02"
echo "git pull origin WebApp_relocation02"

# 5. Установка зависимостей (если нужно)
echo "5. Установка зависимостей:"
echo "pip3 install -r requirements.txt"

# 6. Перезапуск через Passenger
echo "6. Перезапуск через Passenger:"
echo "touch tmp/restart.txt"

# 7. Проверка статуса
echo "7. Проверка статуса:"
echo "ps aux | grep wsgi"
echo "tail -f log/production.log"

# 8. Проверка доступности
echo "8. Проверка доступности:"
echo "curl -I http://miniapp.drazhin.by/bot-app/"

echo ""
echo "✅ Готово! Приложение перезапущено."
