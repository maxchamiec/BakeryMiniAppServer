# 🚀 Финальная настройка на Hoster.by

## 📋 Текущий статус:
✅ **Код загружен** в `/home/drazhinb/miniapp/`  
✅ **Приложение настроено** в панели управления  
✅ **URL настроен**: `miniapp.drazhin.by/bot-app/`  
✅ **Python 3.11.13** установлен  

## 🔧 Что нужно сделать:

### 1. **Обновить wsgi.py файл**
Скопируйте содержимое файла `wsgi_hoster.py` в `/home/drazhinb/miniapp/wsgi.py` на сервере.

### 2. **Изменить настройки в панели управления:**
- **Файл запуска**: `/home/drazhinb/miniapp/wsgi.py` (вместо bot/main.py)
- **Точка входа**: `application` (оставить как есть)

### 3. **Установить зависимости:**
В разделе "Кофигурационные файлы" нажмите **"Запустить pip install"** и введите:
```
requirements.txt
```

### 4. **Создать .env файл:**
Создайте файл `/home/drazhinb/miniapp/.env` с содержимым:
```bash
# Bot Configuration
BOT_TOKEN=ваш_реальный_токен_бота
ADMIN_CHAT_ID=ваш_telegram_id

# Web App Configuration  
BASE_WEBAPP_URL=https://miniapp.drazhin.by/bot-app/

# Email Configuration
ADMIN_EMAIL=ваш_email@example.com
ADMIN_EMAIL_PASSWORD=пароль_для_email

# Security
WEBHOOK_SECRET=случайная_строка_для_безопасности
HMAC_SECRET=другая_случайная_строка

# Parser Configuration
PARSER_ENABLED=true
PARSER_INTERVAL=3600
```

### 5. **Проверить работу:**
1. Сохраните настройки в панели управления
2. Откройте `https://miniapp.drazhin.by/bot-app/`
3. Должна открыться страница с информацией о боте

## 🐛 Отладка:

### Если что-то не работает:
1. **Проверьте логи** в разделе "Файл логов Passenger"
2. **Используйте отладочную версию**: измените точку входа на `debug_application`
3. **Проверьте переменные окружения**: убедитесь, что .env файл создан

### Команды для проверки:
```bash
# Проверить файлы
ls -la /home/drazhinb/miniapp/

# Проверить Python
python3.11 --version

# Проверить зависимости
pip3.11 list | grep aiogram
```

## ✅ После успешной настройки:
- Бот будет запущен в фоновом режиме
- Веб-приложение будет доступно по URL
- Логи будут записываться в указанный файл
- Парсер будет работать автоматически

## 🔗 Полезные ссылки:
- **Панель управления**: [Hoster.by Control Panel]
- **Документация**: [hoster_by_deploy.md](./hoster_by_deploy.md)
- **Чек-лист**: [deploy_checklist.md](./deploy_checklist.md)
