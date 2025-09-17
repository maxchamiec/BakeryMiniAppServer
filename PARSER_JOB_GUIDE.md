# 🤖 Руководство по автоматическому парсингу

Система автоматического парсинга продуктов каждые 3 минуты с возможностью включения/выключения.

## 📁 Файлы системы

- `parser_job.py` - Основной скрипт автоматического парсинга
- `manage_parser.sh` - Скрипт управления для обычного сервера
- `bakery-parser.service` - Systemd сервис для Linux
- `data/parser_job_control.json` - Файл управления состоянием

## 🚀 Быстрый старт

### 1. Тестирование (без сервиса)

```bash
# Показать статус
python3 parser_job.py status

# Включить автоматический парсинг
python3 parser_job.py enable

# Запустить один раз
python3 parser_job.py run-once

# Выключить автоматический парсинг
python3 parser_job.py disable
```

### 2. Установка на обычный сервер

```bash
# Установить systemd сервис
./manage_parser.sh install

# Запустить сервис
./manage_parser.sh start

# Включить автозапуск
./manage_parser.sh enable

# Включить автоматический парсинг
./manage_parser.sh parsing-on
```

## 📊 Команды управления

### Основные команды

| Команда | Описание |
|---------|----------|
| `python3 parser_job.py start` | Запустить автоматический парсинг |
| `python3 parser_job.py enable` | Включить автоматический парсинг |
| `python3 parser_job.py disable` | Выключить автоматический парсинг |
| `python3 parser_job.py status` | Показать статус системы |
| `python3 parser_job.py run-once` | Запустить парсинг один раз |

### Управление сервисом (Linux)

| Команда | Описание |
|---------|----------|
| `./manage_parser.sh install` | Установить systemd сервис |
| `./manage_parser.sh start` | Запустить сервис |
| `./manage_parser.sh stop` | Остановить сервис |
| `./manage_parser.sh restart` | Перезапустить сервис |
| `./manage_parser.sh enable` | Включить автозапуск |
| `./manage_parser.sh disable` | Выключить автозапуск |
| `./manage_parser.sh parsing-on` | Включить автоматический парсинг |
| `./manage_parser.sh parsing-off` | Выключить автоматический парсинг |
| `./manage_parser.sh status` | Показать статус |
| `./manage_parser.sh logs` | Показать логи |

## ⚙️ Настройка

### Интервал парсинга

По умолчанию парсинг запускается каждые 3 минуты. Чтобы изменить интервал, отредактируйте переменную `PARSER_INTERVAL` в файле `parser_job.py`:

```python
# Интервал между запусками (в секундах) - 3 минуты
PARSER_INTERVAL = 3 * 60  # 180 секунд
```

### Пути к файлам

В файле `bakery-parser.service` обновите пути:

```ini
WorkingDirectory=/path/to/BakeryMiniAppServer
ExecStart=/usr/bin/python3 /path/to/BakeryMiniAppServer/parser_job.py start
Environment=PYTHONPATH=/path/to/BakeryMiniAppServer
```

## 📈 Мониторинг

### Статус системы

```bash
python3 parser_job.py status
```

Показывает:
- Включен ли автоматический парсинг
- Количество запусков
- Время последнего запуска
- Время следующего запуска
- Последний успешный запуск
- Последняя ошибка

### Логи

```bash
# Логи systemd сервиса
./manage_parser.sh logs

# Или напрямую
sudo journalctl -u bakery-parser -f
```

## 🔧 Устранение неполадок

### Проблема: Сервис не запускается

```bash
# Проверить статус
systemctl status bakery-parser

# Проверить логи
journalctl -u bakery-parser -n 50

# Перезапустить
./manage_parser.sh restart
```

### Проблема: Парсинг не работает

```bash
# Проверить статус парсинга
python3 parser_job.py status

# Запустить вручную
python3 parser_job.py run-once

# Включить автоматический парсинг
python3 parser_job.py enable
```

### Проблема: Файл управления поврежден

```bash
# Удалить файл управления (будет создан заново)
rm data/parser_job_control.json

# Перезапустить сервис
./manage_parser.sh restart
```

## 🛡️ Безопасность

### Ограничения ресурсов

Сервис настроен с ограничениями:
- Память: 512MB
- CPU: 50%

### Права доступа

Сервис запускается от пользователя `www-data` с минимальными правами.

## 📋 Миграция с Heroku

### 1. Подготовка

```bash
# Скопировать файлы на новый сервер
scp parser_job.py user@server:/path/to/BakeryMiniAppServer/
scp manage_parser.sh user@server:/path/to/BakeryMiniAppServer/
scp bakery-parser.service user@server:/path/to/BakeryMiniAppServer/
```

### 2. Установка

```bash
# На новом сервере
cd /path/to/BakeryMiniAppServer
chmod +x manage_parser.sh
./manage_parser.sh install
```

### 3. Запуск

```bash
# Запустить сервис
./manage_parser.sh start

# Включить автозапуск
./manage_parser.sh enable

# Включить автоматический парсинг
./manage_parser.sh parsing-on
```

### 4. Отключение Heroku Scheduler

В Heroku отключите старый scheduler, так как теперь парсинг будет работать на новом сервере.

## ✅ Преимущества новой системы

1. **Надежность** - Не засыпает как Heroku
2. **Контроль** - Можно включать/выключать в любой момент
3. **Мониторинг** - Подробные логи и статус
4. **Гибкость** - Легко изменить интервал
5. **Производительность** - Работает на обычном сервере
6. **Безопасность** - Ограничения ресурсов

## 🔄 Автоматическое обновление

Система автоматически:
- Обновляет файл `data/products_scraped.json`
- Логирует все операции
- Отслеживает ошибки
- Планирует следующие запуски
- Сохраняет статистику

