# 🚀 Инструкции по деплою на Hoster.by

## 📋 Подготовленные файлы

### Основные файлы для загрузки:
- ✅ `requirements.txt` - зависимости Python
- ✅ `env.production` - переменные окружения для production
- ✅ `start_bot.py` - скрипт запуска приложения
- ✅ `wsgi.py` - WSGI entry point (если потребуется)
- ✅ `Caddyfile` - конфигурация для Caddy (если поддерживается)

### Структура проекта:
```
BakeryMiniAppServer/
├── bot/                    # Основной код бота
│   ├── main.py            # Главный файл приложения
│   ├── config.py          # Конфигурация (уже обновлен)
│   ├── api_server.py      # API сервер (порты обновлены)
│   ├── security_*.py      # Модули безопасности
│   ├── parser.py          # Парсер продуктов
│   ├── keyboards.py       # Клавиатуры бота
│   └── web_app/           # Веб-приложение
├── data/                  # Данные приложения
├── scripts/               # Утилиты
├── tests/                 # Тесты
└── requirements.txt       # Зависимости
```

## 🔧 Шаги деплоя на Hoster.by

### 1. Подготовка файлов
```bash
# Создайте архив проекта (исключая ненужные файлы)
tar -czf bakery-bot.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='temp-cert' \
  --exclude='*.log' \
  bot/ data/ scripts/ tests/ requirements.txt env.production start_bot.py wsgi.py Caddyfile
```

### 2. Загрузка на сервер
- Загрузите архив через панель управления Hoster.by
- Распакуйте в корневую директорию сайта
- Переименуйте `env.production` в `.env`

### 3. Настройка переменных окружения
Отредактируйте `.env` файл:
```bash
# Обязательно измените эти значения:
BOT_TOKEN=ваш_реальный_токен_бота
ADMIN_CHAT_ID=ваш_telegram_id
ADMIN_EMAIL=ваш_email@gmail.com
ADMIN_EMAIL_PASSWORD=ваш_app_password
HMAC_SECRET=случайная_строка_для_безопасности
WEBHOOK_SECRET=другая_случайная_строка
```

### 4. Установка зависимостей
```bash
# В панели управления или через SSH:
pip install -r requirements.txt
```

### 5. Настройка домена
- В панели управления Hoster.by настройте поддомен `miniapp.drazhin.by`
- Убедитесь, что SSL сертификат активен

### 6. Запуск приложения
```bash
# Вариант 1: Прямой запуск
python start_bot.py

# Вариант 2: Через WSGI (если поддерживается)
python wsgi.py

# Вариант 3: Как сервис (если есть доступ к systemd)
sudo systemctl start bakery-bot
```

## ⚙️ Возможные настройки в панели Hoster.by

### Python Application:
- **Entry Point**: `start_bot.py` или `wsgi.py`
- **Python Version**: 3.11+
- **Working Directory**: корень проекта
- **Environment Variables**: загрузить из `.env`

### Web Server:
- **Domain**: `miniapp.drazhin.by`
- **SSL**: включить Let's Encrypt
- **Proxy**: настроить на порт 80

## 🔍 Проверка работоспособности

### 1. Проверка API:
```bash
curl https://miniapp.drazhin.by/bot-app/
curl https://miniapp.drazhin.by/bot-app/api/categories
```

### 2. Проверка бота:
- Отправьте команду `/start` боту
- Проверьте, что открывается веб-приложение

### 3. Проверка логов:
```bash
# Если есть доступ к логам
tail -f /path/to/logs/bot.log
```

## 🆘 Устранение неполадок

### Проблема: Бот не отвечает
- Проверьте BOT_TOKEN
- Убедитесь, что приложение запущено
- Проверьте логи на ошибки

### Проблема: Веб-приложение не открывается
- Проверьте BASE_WEBAPP_URL
- Убедитесь, что домен настроен правильно
- Проверьте SSL сертификат

### Проблема: Email не отправляются
- Проверьте SMTP настройки
- Для Gmail используйте App Password
- Проверьте ADMIN_EMAIL и ADMIN_EMAIL_PASSWORD

## 📞 Поддержка

Если возникнут проблемы:
1. Обратитесь в техподдержку Hoster.by
2. Проверьте логи приложения
3. Убедитесь, что все переменные окружения настроены правильно

## 🔐 Безопасность

- ✅ Все секретные ключи в `.env` файле
- ✅ HMAC подписи для API запросов
- ✅ Rate limiting включен
- ✅ SSL сертификат настроен
- ✅ Безопасные HTTP заголовки

---
**Готово к деплою! 🎉**
