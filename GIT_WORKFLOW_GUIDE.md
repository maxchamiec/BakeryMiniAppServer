# 📚 Bakery Bot — Git и деплой на A1 Cloud VPS

## 🎯 Обзор

Этот документ описывает **рабочий процесс для проекта Bakery Bot**: как вносить изменения, деплоить на VPS и работать с ветками.

---

## 🔑 Ключевая информация о проекте

### Репозиторий:
- **GitHub:** https://github.com/maxchamiec/BakeryMiniAppServer
- **Ветки:**
  - `main` — стабильная production версия
  - `WebApp_relocation290925` — основная ветка разработки
  - `WebApp_bugFixing021025` — текущая ветка с bugfixes (01.10.2025)

### VPS сервер (A1 Cloud Flex):
- **IP:** `178.163.244.86`
- **Домен:** `miniapp.drazhin.by`
- **SSH:** `ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86`
- **Директория проекта:** `/home/ubuntu/BakeryMiniAppServer`
- **Сервис бота:** `bakery-bot.service` (systemd)

### Важные пути:
- **Локально (Mac):** `/Users/Maksim_Chamiec/BakeryMiniAppServer`
- **На VPS:** `/home/ubuntu/BakeryMiniAppServer`
- **Конфиг production:** `env.production` (НЕ коммитить!)
- **SSH ключ:** `~/.ssh/id_rsa`

---

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Деплой изменений на VPS](#деплой-изменений-на-vps)
3. [Работа с ветками](#работа-с-ветками)
4. [Откат изменений](#откат-изменений)
5. [Мониторинг и логи](#мониторинг-и-логи)
6. [Troubleshooting](#troubleshooting)

---

## 1. Быстрый старт

### 🚀 Типичный рабочий процесс (изменения → деплой)

```bash
# 1️⃣ На локальном Mac: внести изменения в код
# ... (редактирование файлов в Cursor) ...

# 2️⃣ Проверить, что изменилось
cd /Users/Maksim_Chamiec/BakeryMiniAppServer
git status

# 3️⃣ Добавить файлы в коммит
git add bot/main.py bot/api_server.py

# 4️⃣ Создать коммит
git commit -m "🔧 Fix bug in order processing"

# 5️⃣ Отправить на GitHub
git push origin WebApp_bugFixing021025

# 6️⃣ Деплой на VPS (обновить код и перезапустить бота)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"

# 7️⃣ Проверить, что бот работает
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 20 --no-pager"
```

**Готово!** 🎉 Ваши изменения на VPS!

---

## 2. Деплой изменений на VPS

### ⚡ Быстрый деплой (Git pull + restart)

**Самый частый сценарий** — обновить код на VPS и перезапустить бота:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"
```

---

### 🔧 Деплой одного файла (без Git, для срочных исправлений)

Если нужно быстро обновить только один файл:

```bash
# 1. Скопировать файл на VPS
scp -i ~/.ssh/id_rsa bot/main.py ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/bot/main.py

# 2. Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"

# 3. Проверить статус
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl status bakery-bot --no-pager"
```

---

### 🧹 Деплой с очисткой Python кеша

Если изменения не применяются (Python использует старые `.pyc` файлы):

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

### 🔄 Деплой с восстановлением env.production

Если `git pull` удалил секретные данные из `env.production`:

```bash
# 1. Скопировать env.production на VPS
scp -i ~/.ssh/id_rsa env.production ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/env.production

# 2. Обновить код
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin WebApp_bugFixing021025 && \
  sudo systemctl restart bakery-bot"
```

---

## 3. Работа с ветками

### 📌 Какую ветку использовать?

**Текущие активные ветки:**
- `WebApp_bugFixing021025` — **ТЕКУЩАЯ** (bugfixes, 01.10.2025)
- `WebApp_relocation290925` — основная ветка разработки
- `main` — стабильная production версия

**Правило:**
- 🔧 **Для исправлений** → используйте `WebApp_bugFixing021025`
- ✨ **Для новых фич** → создайте новую ветку от `WebApp_relocation290925`
- ⚠️ **main** — только для стабильных релизов (merge только после тестирования!)

---

### 🔀 Переключение между ветками

```bash
# На Mac: посмотреть текущую ветку
cd /Users/Maksim_Chamiec/BakeryMiniAppServer
git branch

# Переключиться на другую ветку
git checkout WebApp_bugFixing021025

# Создать новую ветку для новой фичи
git checkout -b WebApp_newFeature021025
```

---

### 📤 Отправка ветки на GitHub

```bash
# Отправить текущую ветку на GitHub
git push origin WebApp_bugFixing021025

# Создать новую ветку и сразу отправить
git checkout -b WebApp_newFeature021025
git push -u origin WebApp_newFeature021025
```

---

## 4. Деплой на VPS

### 🔧 Метод 1: Ручной деплой (через Git pull)

**Когда использовать:** Для быстрых исправлений, тестирования.

```bash
# 1. Подключиться к VPS
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86

# 2. Перейти в директорию проекта
cd /home/ubuntu/BakeryMiniAppServer

# 3. Обновить код с GitHub
git pull origin main

# 4. Перезапустить бота
sudo systemctl restart bakery-bot

# 5. Проверить статус
sudo systemctl status bakery-bot

# 6. Посмотреть логи
sudo journalctl -u bakery-bot -n 50 --no-pager
```

---

### ⚡ Метод 2: Деплой одного файла (через SCP)

**Когда использовать:** Для быстрого обновления одного файла без Git.

```bash
# Скопировать файл на VPS
scp -i ~/.ssh/id_rsa bot/main.py ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/bot/main.py

# Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"

# Проверить статус
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl status bakery-bot --no-pager"
```

---

### 🚀 Метод 3: Полный деплой с очисткой кеша

**Когда использовать:** Когда изменения не применяются из-за Python кеша.

```bash
# Всё в одной команде
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin main && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  find . -name '*.pyc' -delete 2>/dev/null; \
  sudo systemctl restart bakery-bot && \
  sleep 8 && \
  sudo journalctl -u bakery-bot -n 20 --no-pager"
```

---

### 🔄 Метод 4: Деплой с восстановлением env.production

**Когда использовать:** Когда `git reset --hard` удалил локальные изменения в `env.production`.

```bash
# 1. Скопировать env.production на VPS
scp -i ~/.ssh/id_rsa env.production ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/env.production

# 2. Обновить код
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "cd /home/ubuntu/BakeryMiniAppServer && git pull origin main"

# 3. Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

## 5. Откат изменений

### ⏪ Отменить локальные изменения (не закоммиченные)

```bash
# Отменить изменения в конкретном файле
git checkout -- bot/main.py

# Отменить все локальные изменения
git checkout -- .

# Удалить неотслеживаемые файлы
git clean -fd
```

---

### 🔙 Откатить последний коммит (но оставить изменения в файлах)

```bash
# Откатить последний коммит, изменения останутся в файлах
git reset --soft HEAD~1

# Откатить последний коммит, изменения останутся в рабочей директории (unstaged)
git reset HEAD~1

# Откатить последний коммит, удалить изменения полностью (⚠️ ОСТОРОЖНО!)
git reset --hard HEAD~1
```

---

### 🔄 Откатить изменения на VPS

```bash
# Откатиться к конкретному коммиту
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git reset --hard <commit-hash> && \
  sudo systemctl restart bakery-bot"

# Откатиться к последнему коммиту с GitHub (удалив локальные изменения)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git fetch origin && \
  git reset --hard origin/main && \
  sudo systemctl restart bakery-bot"
```

---

## 6. Troubleshooting

### ❌ Проблема: "Permission denied" при push

**Причина:** Нет доступа к GitHub.

**Решение:**
```bash
# Проверить, что используется правильный remote
git remote -v

# Если используется SSH, проверить ключи
ssh -T git@github.com

# Если используется HTTPS, проверить credentials
git config credential.helper
```

---

### ❌ Проблема: "Your local changes would be overwritten by merge"

**Причина:** Локальные изменения конфликтуют с удалёнными.

**Решение:**
```bash
# Вариант 1: Сохранить локальные изменения и применить позже
git stash
git pull origin main
git stash pop

# Вариант 2: Удалить локальные изменения
git reset --hard
git pull origin main
```

---

### ❌ Проблема: Бот не перезапускается после деплоя

**Причина:** Порт 8080 занят старым процессом.

**Решение:**
```bash
# Убить процесс на порту 8080 и перезапустить
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  sudo fuser -k 8080/tcp 2>/dev/null; \
  sudo systemctl restart bakery-bot"
```

---

### ❌ Проблема: Python кеш не обновляется

**Причина:** Python использует старые `.pyc` файлы.

**Решение:**
```bash
# Очистить Python кеш и перезапустить
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  find . -name '*.pyc' -delete 2>/dev/null; \
  sudo systemctl restart bakery-bot"
```

---

### ❌ Проблема: "Invalid BOT_TOKEN format" после git pull

**Причина:** `env.production` был перезаписан из Git.

**Решение:**
```bash
# Скопировать правильный env.production на VPS
scp -i ~/.ssh/id_rsa env.production ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/env.production

# Перезапустить бота
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot"
```

---

## 🎯 Рекомендуемый рабочий процесс

### Для разработки новой фичи:

```bash
# 1. Создать новую ветку
git checkout -b feature/my-new-feature

# 2. Внести изменения в файлы
# ... (редактирование кода) ...

# 3. Проверить изменения
git status
git diff

# 4. Добавить файлы и создать коммит
git add .
git commit -m "✨ Add new feature: my awesome feature"

# 5. Отправить на GitHub
git push origin feature/my-new-feature

# 6. Протестировать на VPS (опционально)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git fetch origin && \
  git checkout feature/my-new-feature && \
  git pull origin feature/my-new-feature && \
  sudo systemctl restart bakery-bot"

# 7. Если всё работает — влить в main
git checkout main
git merge feature/my-new-feature
git push origin main
```

---

### Для срочных исправлений (hotfix):

```bash
# 1. Убедиться, что вы на main
git checkout main
git pull origin main

# 2. Внести исправления
# ... (редактирование кода) ...

# 3. Быстрый коммит и push
git add .
git commit -m "🔥 Hotfix: critical bug fix"
git push origin main

# 4. Деплой на VPS
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin main && \
  sudo systemctl restart bakery-bot"

# 5. Проверить логи
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 30 --no-pager"
```

---

## 🚀 Быстрые команды деплоя

### Полный деплой (Git pull + restart)

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin main && \
  sudo systemctl restart bakery-bot && \
  sleep 5 && \
  sudo systemctl status bakery-bot --no-pager"
```

---

### Деплой с очисткой кеша

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin main && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  sudo systemctl restart bakery-bot && \
  sleep 8 && \
  sudo journalctl -u bakery-bot -n 20 --no-pager"
```

---

### Деплой одного файла (без Git)

```bash
# Скопировать и перезапустить
scp -i ~/.ssh/id_rsa bot/main.py ubuntu@178.163.244.86:/home/ubuntu/BakeryMiniAppServer/bot/main.py && \
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl restart bakery-bot && sleep 5 && sudo systemctl status bakery-bot --no-pager"
```

---

## 🔍 Мониторинг и логи

### Просмотр логов

```bash
# Последние 50 строк логов
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 50 --no-pager"

# Логи в реальном времени (Ctrl+C для выхода)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -f"

# Логи с фильтром (только ошибки)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot -n 100 --no-pager | grep -E 'ERROR|FAIL|Exception'"

# Логи за конкретный период
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo journalctl -u bakery-bot --since '09:30:00' --no-pager"
```

---

### Проверка статуса бота

```bash
# Проверить, запущен ли бот
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "sudo systemctl status bakery-bot --no-pager"

# Проверить, работает ли API
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "curl -s http://127.0.0.1:8080/bot-app/api/all | jq -c '{categories_count: (.categories | length), products_count: (.products | keys | length)}'"

# Проверить версию кеша MODX
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "cat /home/ubuntu/BakeryMiniAppServer/data/modx_cache.json | jq -c '.metadata'"
```

---

## 📁 Важные файлы и что НЕ нужно коммитить

### ✅ Коммитить в Git:

- `bot/` — код бота
- `requirements.txt` — зависимости Python
- `start_bot.py` — точка входа
- `scheduler_modx.py` — обновление кеша MODX
- `env.production.example` — пример конфигурации (БЕЗ секретов!)
- Документация (`.md` файлы)

### ❌ НЕ коммитить в Git (уже в `.gitignore`):

- `env.production` — содержит секретные ключи (BOT_TOKEN, пароли)
- `data/` — данные приложения (кеш, счётчики)
- `venv/` — виртуальное окружение Python
- `__pycache__/` — Python кеш
- `*.pyc` — скомпилированные Python файлы
- `telegram-webapp-mcp/` — MCP серверы (только для локальной разработки)
- `logs/` — логи приложения
- `*.log` — файлы логов

---

## 🔐 Безопасность

### ⚠️ НИКОГДА НЕ КОММИТЬТЕ:

- `BOT_TOKEN` — токен Telegram бота
- `ADMIN_EMAIL_PASSWORD` — пароль email
- `SECRET_KEY` — секретный ключ для HMAC
- Любые пароли, ключи API, токены доступа

### ✅ Вместо этого:

1. Храните секреты в `env.production` (который в `.gitignore`)
2. Создайте `env.production.example` с плейсхолдерами:
   ```env
   BOT_TOKEN=YOUR_BOT_TOKEN_HERE
   ADMIN_EMAIL_PASSWORD=YOUR_PASSWORD_HERE
   SECRET_KEY=YOUR_SECRET_KEY_HERE
   ```
3. Коммитьте только `.example` файл
4. На VPS вручную создайте `env.production` с реальными значениями

---

## 🔄 Синхронизация между локальным Mac и VPS

### Обновить VPS с локального Mac:

```bash
# 1. Закоммитить изменения локально
cd /Users/Maksim_Chamiec/BakeryMiniAppServer
git add .
git commit -m "🔧 My changes"
git push origin main

# 2. Обновить VPS
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git pull origin main && \
  sudo systemctl restart bakery-bot"
```

---

### Получить изменения с VPS на локальный Mac:

```bash
# 1. На VPS: закоммитить изменения (если есть)
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git add . && \
  git commit -m '🔧 Changes from VPS' && \
  git push origin main"

# 2. На Mac: получить изменения
cd /Users/Maksim_Chamiec/BakeryMiniAppServer
git pull origin main
```

---

## 📊 Проверка состояния

### На локальном Mac:

```bash
cd /Users/Maksim_Chamiec/BakeryMiniAppServer

# Какая ветка активна
git branch

# Последний коммит
git log -1 --oneline

# Есть ли незакоммиченные изменения
git status
```

---

### На VPS:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  git branch && \
  echo '---' && \
  git log -1 --oneline && \
  echo '---' && \
  git status"
```

---

## 🧹 Очистка и обслуживание

### Очистка Git репозитория:

```bash
# Удалить ветки, которые уже влиты в main
git branch --merged | grep -v "\*" | xargs -n 1 git branch -d

# Очистить удалённые ветки
git fetch --prune

# Оптимизировать репозиторий (сжать историю)
git gc --aggressive --prune=now
```

---

### Очистка VPS:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@178.163.244.86 "\
  cd /home/ubuntu/BakeryMiniAppServer && \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  find . -name '*.pyc' -delete 2>/dev/null; \
  find . -name '*.log' -mtime +7 -delete 2>/dev/null; \
  echo 'Cleanup completed'"
```

---

## 🎓 Полезные алиасы для Git

Добавьте в `~/.gitconfig` или `~/.zshrc`:

```bash
# В ~/.zshrc
alias gs='git status'
alias ga='git add'
alias gc='git commit -m'
alias gp='git push origin'
alias gl='git log --oneline -10'
alias gd='git diff'

# Использование:
gs           # git status
ga .         # git add .
gc "Fix bug" # git commit -m "Fix bug"
gp main      # git push origin main
```

---

## 📞 Контакты и ссылки

- **GitHub репозиторий:** https://github.com/maxchamiec/BakeryMiniAppServer
- **VPS IP:** 178.163.244.86
- **WebApp URL:** https://miniapp.drazhin.by/bot-app/
- **Telegram bot:** @drazhin_bot

---

## 🎯 Итоговый чеклист для деплоя

- [ ] Изменения протестированы локально
- [ ] Все файлы добавлены в Git (`git add`)
- [ ] Создан коммит с понятным сообщением (`git commit`)
- [ ] Изменения отправлены на GitHub (`git push`)
- [ ] VPS обновлён (`git pull` на сервере)
- [ ] Бот перезапущен (`systemctl restart`)
- [ ] Логи проверены (нет ошибок)
- [ ] Функционал протестирован (заказы, кнопки, API)

---

**Готово! 🚀 Теперь у вас есть полное руководство по работе с Git и деплою на VPS!**

