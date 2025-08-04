# Настройка Heroku - Переменные окружения

Ваше приложение успешно развернуто на Heroku! 🎉

**URL приложения:** https://bakery-mini-app-server-440955f475ad.herokuapp.com/

## Необходимые переменные окружения

Установите следующие переменные окружения в настройках Heroku:

```bash
# Обязательные переменные
heroku config:set BOT_TOKEN="ваш_токен_бота"
heroku config:set ADMIN_CHAT_ID="ваш_id_администратора"
heroku config:set ADMIN_EMAIL="ваш_email@example.com"

# Опциональные переменные (уже установлены)
BASE_WEBAPP_URL="https://bakery-mini-app-server-440955f475ad.herokuapp.com/bot-app/"
SMTP_SERVER="smtp.gmail.com"
ADMIN_EMAIL_PASSWORD="пароль_для_smtp"  # если нужны email уведомления
```

## Как установить переменные

### Через CLI:
```bash
heroku config:set BOT_TOKEN="ваш_токен_бота"
heroku config:set ADMIN_CHAT_ID="ваш_id_администратора"
heroku config:set ADMIN_EMAIL="ваш_email@example.com"
```

### Через веб-интерфейс:
1. Перейдите на https://dashboard.heroku.com/apps/bakery-mini-app-server/settings
2. Нажмите "Reveal Config Vars"
3. Добавьте переменные по одной

## Проверка статуса

```bash
# Проверить статус приложения
heroku ps

# Посмотреть логи
heroku logs --tail

# Открыть приложение
heroku open
```

## Полезные команды

```bash
# Перезапустить приложение
heroku restart

# Проверить переменные окружения
heroku config

# Обновить код
git push heroku WebApp_To_Heroku:main
```

## Структура URL

- **Главная страница:** https://bakery-mini-app-server-440955f475ad.herokuapp.com/
- **Веб-приложение:** https://bakery-mini-app-server-440955f475ad.herokuapp.com/bot-app/
- **API категорий:** https://bakery-mini-app-server-440955f475ad.herokuapp.com/bot-app/api/categories
- **API продуктов:** https://bakery-mini-app-server-440955f475ad.herokuapp.com/bot-app/api/products

## Статус: ✅ РАБОТАЕТ

- ✅ Веб-сервер запущен
- ✅ Telegram бот подключен
- ✅ API работает
- ✅ Данные загружены (67 продуктов в 4 категориях)
- ✅ Счетчик заказов инициализирован 