# 🥖 Bakery Mini App Server

Telegram WebApp для пекарни Дражина с полным функционалом заказа выпечки.

## 🎯 Обзор

Этот проект представляет собой полнофункциональное Telegram WebApp для пекарни, включающее:
- Каталог продукции с категориями
- Корзину покупок
- Оформление заказов
- Уведомления по email
- Систему безопасности

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.11+
- Git
- Heroku CLI
- Telegram Bot Token

### Установка
```bash
git clone <repository-url>
cd BakeryMiniAppServer
pip install -r requirements.txt
```

### Настройка окружения
Скопируйте `env.example` в `.env` и настройте:
```bash
cp env.example .env
# Отредактируйте .env с вашими значениями
```

## 🔧 Конфигурация

### Обязательные переменные окружения
```bash
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_telegram_user_id
ADMIN_EMAIL=your_email@example.com
BASE_WEBAPP_URL=https://your-app.herokuapp.com/bot-app/
```

### Дополнительные переменные окружения
```bash
ADMIN_EMAIL_PASSWORD=your_smtp_password
SMTP_SERVER=smtp.gmail.com
HMAC_SECRET=your_hmac_secret_key
```

## 🚀 Развертывание

### Heroku (Рекомендуется)

1. **Создайте Heroku приложение:**
```bash
heroku create your-app-name
```

2. **Установите переменные окружения:**
```bash
heroku config:set BOT_TOKEN="your_token"
heroku config:set ADMIN_CHAT_ID="your_id"
heroku config:set ADMIN_EMAIL="your_email"
heroku config:set BASE_WEBAPP_URL="https://your-app.herokuapp.com/bot-app/"
```

3. **Разверните:**
```bash
git push heroku main
```

## 🛠️ Структура проекта

```
BakeryMiniAppServer/
├── bot/                    # Основной код приложения
│   ├── web_app/           # Файлы веб-приложения
│   │   ├── index.html     # Главный HTML файл
│   │   ├── script.js      # JavaScript приложение
│   │   ├── style.css      # CSS стили
│   │   └── images/        # Статические изображения
│   ├── api_server.py      # API сервер
│   ├── main.py           # Основной файл бота
│   ├── parser.py         # Парсер продукции
│   └── config.py         # Конфигурация
├── data/                  # Файлы данных
│   ├── products_scraped.json
│   └── order_counter.json
├── tests/                 # Тестовые файлы
├── scripts/              # Утилиты
└── docs/                 # Документация
```

## 🔑 Основные функции

### 1. Управление данными клиентов
- **Автозаполнение форм:** Запоминает информацию о клиентах
- **Хранение 1 год:** Данные сохраняются для повторных клиентов
- **Приватность:** Только локальное хранение, без серверного хранения

### 2. Управление продукцией
- **Автоматический парсинг:** Обновляет данные о продукции каждый час
- **Фильтрация по категориям:** Организованный показ продукции
- **Оптимизация изображений:** Ленивая загрузка и сжатие

### 3. Обработка заказов
- **Управление корзиной:** Добавление/удаление товаров с контролем количества
- **Валидация форм:** Комплексная валидация ввода
- **Отслеживание заказов:** Уникальные номера заказов и статус

## 📊 API Endpoints

```
GET /bot-app/api/products          # Получить всю продукцию
GET /bot-app/api/products?category=bread  # Получить продукцию по категории
GET /bot-app/api/categories        # Получить категории продукции
GET /bot-app/api/auth/token        # Получить токен аутентификации
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Запустить все тесты
python -m pytest tests/

# Запустить конкретные категории тестов
python -m pytest tests/unit/
python -m pytest tests/integration/

# Запустить с покрытием
python -m pytest --cov=bot tests/
```

### Категории тестов
- **Unit Tests:** Тестирование отдельных функций
- **Integration Tests:** Тестирование API endpoints
- **Security Tests:** Валидация функций безопасности
- **Performance Tests:** Нагрузочное и стресс-тестирование

## 🔄 История версий

### Текущая версия: 1.3.108
- ✅ HMAC аутентификация подписей
- ✅ Реализация rate limiting
- ✅ Валидация Telegram WebApp
- ✅ Улучшения безопасности

### Предыдущие версии
- **1.3.97:** Начальная реализация безопасности
- **1.3.95:** Сохранение данных клиентов
- **1.3.90:** Базовый функционал
- **1.3.85:** Основная функциональность

---

**Последнее обновление:** 2025-09-03  
**Поддерживается:** Команда разработки  
**Контакт по безопасности:** security@drazhin.by