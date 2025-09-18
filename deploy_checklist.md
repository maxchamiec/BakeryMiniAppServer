# ✅ Чек-лист для деплоя на Hoster.by

## 📦 Файлы готовы к загрузке

### ✅ Основные файлы:
- [ ] `requirements.txt` - обновлен с дополнительными зависимостями
- [ ] `env.production` - шаблон переменных окружения
- [ ] `start_bot.py` - скрипт запуска приложения
- [ ] `wsgi.py` - WSGI entry point (резервный вариант)
- [ ] `Caddyfile` - конфигурация для Caddy
- [ ] `hoster_by_deploy.md` - подробные инструкции

### ✅ Обновленные конфигурации:
- [ ] `bot/config.py` - BASE_WEBAPP_URL изменен на `https://miniapp.drazhin.by/bot-app/`
- [ ] `bot/main.py` - порт изменен с 8080 на 80
- [ ] `bot/api_server.py` - порт изменен с 8080 на 80
- [ ] `env.example` и `env_template` - порты обновлены
- [ ] `README.md` - документация обновлена

## 🔧 Перед деплоем

### 1. Подготовка переменных окружения:
```bash
# Скопируйте env.production в .env и заполните:
BOT_TOKEN=ваш_реальный_токен
ADMIN_CHAT_ID=ваш_telegram_id  
ADMIN_EMAIL=ваш_email@gmail.com
ADMIN_EMAIL_PASSWORD=ваш_gmail_app_password
HMAC_SECRET=сгенерируйте_случайную_строку
WEBHOOK_SECRET=еще_одну_случайную_строку
```

### 2. Создание архива:
```bash
tar -czf bakery-bot-deploy.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='temp-cert' \
  --exclude='*.log' \
  --exclude='bandit-report.json' \
  --exclude='security_report.json' \
  bot/ data/ scripts/ tests/ requirements.txt env.production start_bot.py wsgi.py Caddyfile *.md
```

## 🚀 Шаги деплоя

### 1. В панели управления Hoster.by:
- [ ] Загрузить архив `bakery-bot-deploy.tar.gz`
- [ ] Распаковать в корневую директорию сайта
- [ ] Переименовать `env.production` в `.env`
- [ ] Отредактировать `.env` с реальными значениями

### 2. Настройка Python приложения:
- [ ] Указать Python версию 3.11+
- [ ] Entry point: `start_bot.py`
- [ ] Working directory: корень проекта
- [ ] Environment variables: загрузить из `.env`

### 3. Настройка домена:
- [ ] Поддомен: `miniapp.drazhin.by`
- [ ] SSL сертификат: включить Let's Encrypt
- [ ] Proxy: настроить на порт 80

### 4. Установка зависимостей:
```bash
pip install -r requirements.txt
```

### 5. Запуск приложения:
```bash
python start_bot.py
```

## 🔍 Проверка после деплоя

### API тесты:
- [ ] `curl https://miniapp.drazhin.by/bot-app/` - главная страница
- [ ] `curl https://miniapp.drazhin.by/bot-app/api/categories` - API категорий
- [ ] `curl https://miniapp.drazhin.by/bot-app/api/products` - API продуктов

### Telegram бот:
- [ ] Отправить `/start` боту
- [ ] Проверить, что открывается веб-приложение
- [ ] Проверить работу корзины
- [ ] Проверить оформление заказа

### Email уведомления:
- [ ] Сделать тестовый заказ
- [ ] Проверить получение email администратору
- [ ] Проверить получение email клиенту

## 🆘 Возможные проблемы

### Если бот не отвечает:
- [ ] Проверить BOT_TOKEN в `.env`
- [ ] Проверить, что приложение запущено
- [ ] Проверить логи на ошибки

### Если веб-приложение не открывается:
- [ ] Проверить BASE_WEBAPP_URL в `.env`
- [ ] Проверить настройки домена
- [ ] Проверить SSL сертификат

### Если email не отправляются:
- [ ] Проверить SMTP настройки в `.env`
- [ ] Для Gmail использовать App Password
- [ ] Проверить ADMIN_EMAIL и ADMIN_EMAIL_PASSWORD

## 📞 Контакты для поддержки

- **Hoster.by техподдержка**: для вопросов по хостингу
- **Telegram Bot API**: для вопросов по боту
- **Gmail SMTP**: для настроек email

---
**Все готово для деплоя! 🎉**
