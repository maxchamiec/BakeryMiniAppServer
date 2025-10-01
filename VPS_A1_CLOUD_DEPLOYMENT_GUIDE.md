# 🚀 Руководство по развертыванию на A1 Cloud Flex VPS

## 📋 Оглавление

1. [Обзор](#обзор)
2. [Предварительные требования](#предварительные-требования)
3. [Настройка VPS](#настройка-vps)
4. [Развертывание приложения](#развертывание-приложения)
5. [Настройка Nginx и HTTPS](#настройка-nginx-и-https)
6. [Автоматическое развертывание из GitHub](#автоматическое-развертывание-из-github)
7. [Решение проблем](#решение-проблем)

---

## 🎯 Обзор

Этот проект развернут на **A1 Cloud Flex VPS** с доменом **miniapp.drazhin.by**.

### 🏗️ Архитектура:

```
Пользователь
    ↓
https://miniapp.drazhin.by/bot-app/ (HTTPS, Let's Encrypt)
    ↓
Nginx (443) → Reverse Proxy
    ↓
Python Bot (127.0.0.1:8080)
    ↓
MODX API (https://drazhin.by/api-*.json)
```

---

## 🔧 Предварительные требования

### VPS:
- **Провайдер:** A1 Cloud Flex
- **IP:** 178.163.244.86
- **OS:** Ubuntu 22.04 (Jammy)
- **RAM:** 1 GB
- **vCPU:** 1
- **Домен:** miniapp.drazhin.by

### Локальная машина:
- SSH ключ (`~/.ssh/id_rsa`)
- Git
- Python 3.10+

---

## 🛠️ Настройка VPS

### 1. SSH доступ

#### На локальной машине:

```bash
# Создайте SSH ключ (если еще нет)
ssh-keygen -t rsa -b 4096 -C "bakery-app@a1cloud"

# Скопируйте публичный ключ
cat ~/.ssh/id_rsa.pub
```

#### В A1 Cloud Flex консоли:

1. Перейдите в **Compute → Instances**
2. Создайте новый инстанс
3. Выберите **Ubuntu 22.04**
4. Добавьте **SSH ключ**
5. Настройте **Security Groups**:
   - **Входящий TCP 22** (SSH) - 0.0.0.0/0
   - **Входящий TCP 80** (HTTP) - 0.0.0.0/0
   - **Входящий TCP 443** (HTTPS) - 0.0.0.0/0
   - **Входящий TCP 8080** (Bot API) - 0.0.0.0/0
   - **Входящий Any** - 0.0.0.0/0

#### Cloud Init (опционально):

```yaml
#cloud-config
password: YourSecurePassword123
chpasswd:
  expire: false
ssh_pwauth: true
users:
  - name: ubuntu
    ssh_authorized_keys:
      - ssh-rsa YOUR_PUBLIC_KEY_HERE bakery-app@a1cloud
```

### 2. Подключение к VPS

```bash
# Настройте SSH config
nano ~/.ssh/config
```

Добавьте:

```
Host bakery-vps
    HostName 178.163.244.86
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

Подключитесь:

```bash
ssh bakery-vps
```

### 3. Установка зависимостей

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python и pip
sudo apt install python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx jq -y

# Установите дополнительные инструменты
sudo apt install curl wget htop nano -y
```

### 4. ⚠️ Критическое исправление: Отключение IPv6

**A1 Cloud Flex блокирует IPv6 для Telegram API**, что вызывает timeout ошибки.

```bash
# Отключите IPv6 на уровне системы
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1

# Сделайте постоянным
echo "net.ipv6.conf.all.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf

# Проверьте
ping -c 3 -4 api.telegram.org  # Должно работать
ping -c 3 -6 api.telegram.org  # Должно НЕ работать
```

---

## 🚀 Развертывание приложения

### 1. Клонирование репозитория

```bash
# На VPS
cd ~
git clone https://github.com/maxchamiec/BakeryMiniAppServer.git
cd BakeryMiniAppServer
```

### 2. Создание виртуального окружения

```bash
# Создайте venv
python3 -m venv venv

# Активируйте venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

```bash
# Скопируйте .env в env.production
cp .env env.production

# Отредактируйте env.production
nano env.production
```

**Важные переменные:**

```env
ENVIRONMENT=production
BOT_TOKEN=YOUR_BOT_TOKEN
BASE_WEBAPP_URL=https://miniapp.drazhin.by/bot-app/
ADMIN_CHAT_ID=YOUR_CHAT_ID
ADMIN_EMAIL=your@email.com
ADMIN_EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
ENABLE_EMAIL_NOTIFICATIONS=true
ENABLE_ORDER_COUNTER=true
```

### 4. Настройка systemd службы

```bash
# Создайте службу
sudo nano /etc/systemd/system/bakery-bot.service
```

Содержимое:

```ini
[Unit]
Description=Bakery Bot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/BakeryMiniAppServer
Environment=PATH=/home/ubuntu/BakeryMiniAppServer/venv/bin
ExecStart=/home/ubuntu/BakeryMiniAppServer/venv/bin/python3 start_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Включите службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bakery-bot
sudo systemctl start bakery-bot
sudo systemctl status bakery-bot
```

---

## 🔒 Настройка Nginx и HTTPS

### 1. Настройка DNS

В cPanel вашего хостинга (hoster.by):

1. Перейдите в **Zone Editor**
2. Добавьте **A-запись**:
   - **Имя:** miniapp
   - **Тип:** A
   - **Запись:** 178.163.244.86
   - **TTL:** 3600

### 2. Настройка Nginx

```bash
# Создайте конфигурацию
sudo nano /etc/nginx/sites-available/bakery-bot
```

Содержимое:

```nginx
server {
    listen 80;
    server_name miniapp.drazhin.by;

    # Для Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        try_files $uri =404;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name miniapp.drazhin.by;
    
    # SSL сертификаты (будут созданы Certbot)
    ssl_certificate /etc/letsencrypt/live/miniapp.drazhin.by/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/miniapp.drazhin.by/privkey.pem;

    # Проксирование на Python бота
    location /bot-app/ {
        proxy_pass http://127.0.0.1:8080/bot-app/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/bakery-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Получение SSL сертификата

```bash
# Создайте директорию для ACME challenge
sudo mkdir -p /var/www/letsencrypt

# Получите сертификат
sudo certbot --nginx -d miniapp.drazhin.by
```

---

## 🔄 Автоматическое развертывание из GitHub

См. отдельный документ: [GITHUB_DEPLOY_GUIDE.md](GITHUB_DEPLOY_GUIDE.md)

---

## 🐛 Решение проблем

### Проблема 1: Telegram API Timeout

**Симптомы:**
- `HTTP Client says - Request timeout error`
- Сообщения не отправляются
- Бот зависает

**Решение:**
```bash
# Отключите IPv6
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1

# Перезапустите бота
sudo systemctl restart bakery-bot
```

### Проблема 2: categoriesData is not defined

**Симптомы:**
- `ReferenceError: categoriesData is not defined`
- Категории не загружаются

**Решение:**
Добавлена глобальная переменная в `script.js`:
```javascript
let categoriesData = [];
```

### Проблема 3: Медленная обработка заказов

**Симптомы:**
- Заказы обрабатываются 3-4 минуты
- Бот зависает

**Решение:**
Добавлен timeout для отправки сообщений:
```python
await asyncio.wait_for(
    bot.send_message(...),
    timeout=10.0
)
```

### Проблема 4: ERR_TOO_MANY_REDIRECTS

**Симптомы:**
- Браузер показывает `ERR_TOO_MANY_REDIRECTS`

**Решение:**
Исправлена конфигурация Nginx - `proxy_pass` должен указывать на `/bot-app/`, а не на `/`.

### Проблема 5: 504 Gateway Time-out

**Симптомы:**
- Nginx возвращает 504
- WebApp не загружается

**Решение:**
Увеличьте timeout в Nginx (опционально):
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

---

## 📊 Мониторинг

### Логи бота:

```bash
# Просмотр логов в реальном времени
sudo journalctl -u bakery-bot -f

# Последние 100 строк
sudo journalctl -u bakery-bot | tail -100

# Поиск ошибок
sudo journalctl -u bakery-bot | grep -i error
```

### Статус бота:

```bash
sudo systemctl status bakery-bot
```

### Логи Nginx:

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### Проверка порта:

```bash
sudo ss -tlnp | grep 8080
```

---

## 🎊 Итоговая конфигурация

### ✅ Что работает:

- **VPS сервер:** A1 Cloud Flex (178.163.244.86)
- **SSH доступ:** Настроен через ключ
- **Бот:** Запущен через systemd (автозапуск)
- **API сервер:** Работает на порту 8080
- **MODX кэш:** Загружается успешно (101KB)
- **Nginx:** Проксирует запросы с HTTPS
- **SSL сертификат:** Let's Encrypt (miniapp.drazhin.by)
- **Домен:** miniapp.drazhin.by → 178.163.244.86
- **Веб-приложение:** https://miniapp.drazhin.by/bot-app/
- **API:** Отдает данные (200 OK, 193KB)
- **Заказы:** Обрабатываются за 4 секунды
- **Email:** Отправляются успешно
- **Telegram:** Работает с IPv4

### 📈 Производительность:

- **Обработка заказа:** 4 секунды (оптимизировано с 4 минут)
- **API ответ:** ~200ms
- **MODX кэш:** Обновляется каждую минуту
- **Память:** ~110MB
- **CPU:** Minimal usage

---

## 🔗 Полезные ссылки

- **Веб-приложение:** https://miniapp.drazhin.by/bot-app/
- **Telegram бот:** @drazhin_bot
- **Основной сайт:** https://drazhin.by/
- **GitHub:** https://github.com/maxchamiec/BakeryMiniAppServer
- **A1 Cloud Flex:** https://console.a1digital.by/

---

## 📞 Контакты

- **Администратор:** maxvindsvalr@gmail.com
- **Telegram:** @drazhin_bot

---

**Дата создания:** 1 октября 2025  
**Версия:** 1.0  
**Статус:** ✅ Работает в продакшене

