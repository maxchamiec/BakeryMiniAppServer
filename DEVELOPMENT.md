# 🛠️ Development Guide - Bakery Mini App Server

## 🏗️ Архитектура проекта

### Структура кода
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
│   ├── config.py         # Конфигурация
│   ├── keyboards.py      # Клавиатуры Telegram
│   ├── security_manager.py # Менеджер безопасности
│   ├── security.py       # Функции безопасности
│   ├── security_middleware.py # Middleware безопасности
│   └── security_headers.py # Security headers
├── data/                  # Файлы данных
│   ├── products_scraped.json
│   └── order_counter.json
├── tests/                 # Тестовые файлы
│   ├── unit/             # Unit тесты
│   ├── integration/      # Integration тесты
│   └── web_app/          # Web app тесты
├── scripts/              # Утилиты
│   ├── normalize_cache.py
│   └── bump_cache.sh
└── docs/                 # Документация
```

## 🔧 Основные компоненты

### 1. Bot Main (bot/main.py)
Основной файл бота, содержащий:
- Инициализацию бота и диспетчера
- Обработчики команд и сообщений
- Логику корзины и заказов
- Email уведомления

### 2. API Server (bot/api_server.py)
HTTP API сервер для WebApp:
- Endpoints для продукции и категорий
- HMAC аутентификация
- Rate limiting
- Security headers

### 3. Configuration (bot/config.py)
Управление конфигурацией:
- SecureConfig класс
- Валидация переменных окружения
- Настройки безопасности

### 4. Security Manager (bot/security_manager.py)
Централизованное управление безопасностью:
- HMAC подписи
- Rate limiting
- Валидация webhook
- Мониторинг безопасности

## 🧪 Тестирование

### Структура тестов
```
tests/
├── unit/                 # Unit тесты
│   ├── test_api_server.py
│   ├── test_config.py
│   ├── test_keyboards.py
│   ├── test_main.py
│   ├── test_orders.py
│   ├── test_cart.py
│   ├── test_security_features.py
│   └── ...
├── integration/          # Integration тесты
│   └── test_api_integration.py
└── web_app/             # Web app тесты
    ├── test_checkout_validation.py
    └── test_script.js
```

### Запуск тестов
```bash
# Все тесты
python -m pytest tests/

# Unit тесты
python -m pytest tests/unit/

# Integration тесты
python -m pytest tests/integration/

# С покрытием
python -m pytest --cov=bot tests/

# Конкретный тест
python -m pytest tests/unit/test_api_server.py -v
```

### Категории тестов
- **Unit Tests:** Тестирование отдельных функций
- **Integration Tests:** Тестирование API endpoints
- **Security Tests:** Валидация функций безопасности
- **Web App Tests:** Тестирование frontend функциональности

## 🔄 Разработка

### Настройка среды разработки
```bash
# Клонирование репозитория
git clone https://github.com/your-username/BakeryMiniAppServer.git
cd BakeryMiniAppServer

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Локальная разработка
```bash
# Настройка переменных окружения
cp env.example .env
# Отредактируйте .env файл

# Запуск в режиме разработки
python bot/main.py
```

### Структура кода

#### Основные принципы
- **Модульность:** Каждый компонент в отдельном файле
- **Безопасность:** Все функции проверяются на безопасность
- **Тестируемость:** Код покрыт тестами
- **Документированность:** Все функции документированы

#### Стиль кода
```python
# Пример структуры функции
async def process_order(order_data: dict, user_id: int) -> dict:
    """
    Обрабатывает заказ пользователя.
    
    Args:
        order_data: Данные заказа
        user_id: ID пользователя
        
    Returns:
        dict: Результат обработки заказа
        
    Raises:
        ValidationError: При неверных данных заказа
    """
    # Валидация входных данных
    if not validate_order_data(order_data):
        raise ValidationError("Invalid order data")
    
    # Обработка заказа
    result = await _process_order_internal(order_data, user_id)
    
    return result
```

## 📊 Мониторинг и логирование

### Логирование
```python
import logging

logger = logging.getLogger(__name__)

# Различные уровни логирования
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Мониторинг производительности
```python
import time

async def monitored_function():
    start_time = time.time()
    
    # Выполнение функции
    result = await some_operation()
    
    duration = time.time() - start_time
    logger.info(f"Operation completed in {duration:.3f}s")
    
    return result
```

## 🔧 Утилиты разработки

### Скрипты
```bash
# Обновление кеша
python scripts/normalize_cache.py

# Обновление версий
bash scripts/bump_cache.sh

# Запуск парсера
python run_parser.py

# Планировщик задач
python scheduler.py
```

### Инструменты разработки
```bash
# Проверка кода
flake8 bot/
black bot/
isort bot/

# Проверка безопасности
bandit -r bot/
pip-audit

# Тестирование
pytest tests/ -v --cov=bot
```

## 🚀 Процесс разработки

### Workflow
1. **Создание ветки** для новой функции
2. **Разработка** с написанием тестов
3. **Тестирование** всех компонентов
4. **Code review** и проверка безопасности
5. **Слияние** в основную ветку
6. **Развертывание** на staging/production

### Git workflow
```bash
# Создание ветки
git checkout -b feature/new-feature

# Разработка
git add .
git commit -m "Add new feature"

# Отправка
git push origin feature/new-feature

# Создание Pull Request
# После review - слияние
git checkout main
git pull origin main
```

## 📋 Контрольные списки

### Перед коммитом
- [ ] Код протестирован
- [ ] Тесты проходят
- [ ] Безопасность проверена
- [ ] Документация обновлена
- [ ] Логирование добавлено

### Перед развертыванием
- [ ] Все тесты проходят
- [ ] Security audit выполнен
- [ ] Performance тесты пройдены
- [ ] Документация актуальна
- [ ] Backup создан

## 🔍 Отладка

### Локальная отладка
```python
import pdb

# Точка останова
pdb.set_trace()

# Или используйте IDE debugger
```

### Отладка в production
```bash
# Просмотр логов
heroku logs --tail

# Подключение к приложению
heroku run bash

# Проверка переменных окружения
heroku config
```

---

**Последнее обновление:** 2025-09-03  
**Поддерживается:** Команда разработки
