# 🚀 Bakery Bot — Быстрая инструкция по деплою

## 📌 Ключевая информация

### Сервер VPS (A1 Cloud Flex):
```
IP: 178.163.244.86
Домен: miniapp.drazhin.by
SSH: ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86
Директория: /home/ubuntu/BakeryMiniAppServer
```

### Текущая ветка:
```
WebApp_bugFixing021025
```

---

## ⚡ БЫСТРЫЙ ДЕПЛОЙ (самый частый случай)

### Сценарий: Исправили баг → деплой на сервер

```bash
# 1️⃣ Сохранить изменения в Git (на Mac)
cd /Users/Maksim_Chamiec/BakeryMiniAppServer
git add .
git commit -m "🔧 Fix bug description"
git push origin WebApp_bugFixing021025

# 2️⃣ Деплой на VPS (одной командой)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"

# 3️⃣ Проверить, что всё работает
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 20 --no-pager"
```

**Готово!** 🎉

---

## 📝 ДЕПЛОЙ ОДНОГО ФАЙЛА (для срочных исправлений)

Если нужно быстро обновить только `bot/main.py` без Git:

```bash
# 1️⃣ Скопировать файл на VPS
scp -i ~/.ssh/id_rsa bot/main.py ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/bot/main.py

# 2️⃣ Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

## 🧹 ДЕПЛОЙ С ОЧИСТКОЙ КЕША

Если после деплоя изменения не работают (Python использует старый кеш):

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin WebApp_bugFixing021025 && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  find . -name '*.pyc' -delete 2>/dev/null; \
  sudo systemctl restart bakery-bot && \
  sleep 8 && \
  sudo journalctl -u bakery-bot -n 20 --no-pager"
```

---

## 🔄 ВОССТАНОВЛЕНИЕ env.production

Если после `git pull` бот не стартует (ошибка "Invalid BOT_TOKEN"):

```bash
# 1️⃣ Скопировать правильный env.production на VPS
scp -i ~/.ssh/id_rsa env.production ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/env.production

# 2️⃣ Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

## 📊 МОНИТОРИНГ И ЛОГИ

### Просмотр логов бота

```bash
# Последние 50 строк
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 50 --no-pager"

# Логи в реальном времени (Ctrl+C для выхода)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -f"

# Только ошибки
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 100 --no-pager | grep -E 'ERROR|FAIL|Exception'"
```

---

### Проверка статуса бота

```bash
# Статус сервиса
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl status bakery-bot --no-pager"

# Проверить, работает ли API
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "curl -s http://127.0.0.1:8080/bot-app/api/all | jq -c '{categories: (.categories | length), products: (.products | keys | length)}'"

# Проверить версию кеша MODX
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "cat /home/ubuntu/BakeryMiniAppServer/data/modx_cache.json | jq -c '.metadata'"
```

---

## 🔧 КОМАНДЫ УПРАВЛЕНИЯ БОТОМ

### Перезапуск бота

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

### Остановка бота

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl stop bakery-bot"
```

---

### Запуск бота

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl start bakery-bot"
```

---

### Убить процесс на порту 8080 (если бот не стартует)

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo fuser -k 8080/tcp && sudo systemctl restart bakery-bot"
```

---

## 🔀 ПЕРЕКЛЮЧЕНИЕ ВЕТОК НА VPS

### Если нужно переключить VPS на другую ветку

```bash
# Проверить текущую ветку на VPS
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "cd /home/ubuntu/BakeryMiniAppServer && git branch"

# Переключиться на нужную ветку
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git fetch origin && \
  git checkout WebApp_bugFixing021025 && \
  git pull origin WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"
```

---

### Если ветка не существует на VPS (создать новую)

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git fetch origin && \
  git checkout -b WebApp_newFeature origin/WebApp_newFeature && \
  sudo systemctl restart bakery-bot"
```

---

## ⏪ ОТКАТ ИЗМЕНЕНИЙ

### Откатить VPS к предыдущей версии

```bash
# Откатиться к последнему стабильному коммиту с GitHub
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git fetch origin && \
  git reset --hard origin/WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"
```

---

### Откатить к конкретному коммиту

```bash
# Сначала найдите hash коммита
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "cd /home/ubuntu/BakeryMiniAppServer && git log --oneline -10"

# Откатитесь к нужному коммиту (замените <commit-hash>)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git reset --hard <commit-hash> && \
  sudo systemctl restart bakery-bot"
```

---

## ❌ TROUBLESHOOTING

### Проблема: Бот не перезапускается (порт 8080 занят)

**Решение:**
```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  sudo fuser -k 8080/tcp 2>/dev/null; \
  sudo systemctl restart bakery-bot"
```

---

### Проблема: Python кеш не обновляется

**Решение:**
```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  find . -name '*.pyc' -delete 2>/dev/null; \
  sudo systemctl restart bakery-bot"
```

---

### Проблема: "Invalid BOT_TOKEN format"

**Причина:** `env.production` был перезаписан из Git.

**Решение:**
```bash
scp -i ~/.ssh/id_rsa env.production ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/env.production
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

### Проблема: "Your local changes would be overwritten"

**Решение:**
```bash
# Сохранить локальные изменения на VPS
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git stash && \
  git pull origin WebApp_bugFixing021025 && \
  git stash pop && \
  sudo systemctl restart bakery-bot"
```

---

## 📁 ЧТО НЕ КОММИТИТЬ

### ❌ НИКОГДА не добавляйте в Git:

- `env.production` — содержит секретные ключи (BOT_TOKEN, пароли)
- `data/` — данные приложения (кеш, счётчики заказов)
- `venv/` — виртуальное окружение Python
- `__pycache__/` и `*.pyc` — Python кеш
- `telegram-webapp-mcp/` — MCP серверы (только для локальной разработки)
- `logs/` и `*.log` — логи

**Эти файлы уже в `.gitignore` и игнорируются автоматически!** ✅

---

## 🎯 ЧЕКЛИСТ ПЕРЕД ДЕПЛОЕМ

- [ ] Изменения протестированы локально
- [ ] Все файлы добавлены (`git add`)
- [ ] Создан коммит с понятным сообщением
- [ ] Изменения отправлены на GitHub (`git push`)
- [ ] VPS обновлён (`git pull` на сервере)
- [ ] Бот перезапущен (`systemctl restart`)
- [ ] Логи проверены (нет ошибок)
- [ ] Функционал протестирован (заказы, кнопки, API)

---

## 📞 Полезные ссылки

- **GitHub:** https://github.com/maxchamiec/BakeryMiniAppServer
- **WebApp:** https://miniapp.drazhin.by/bot-app/
- **Telegram Bot:** @drazhin_bot
- **VPS IP:** 178.163.244.86

---

**Готово! 🚀 Теперь у вас есть краткая инструкция для работы с Bakery Bot!**

