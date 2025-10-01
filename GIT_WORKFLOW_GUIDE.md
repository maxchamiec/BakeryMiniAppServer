# 📚 Git, GitHub и деплой на VPS — Полное руководство

## 🎯 Обзор

Этот документ описывает полный рабочий процесс для работы с Git, GitHub и деплоем приложения на A1 Cloud Flex VPS.

---

## 📋 Содержание

1. [Основные команды Git](#основные-команды-git)
2. [Работа с ветками](#работа-с-ветками)
3. [Коммиты и push на GitHub](#коммиты-и-push-на-github)
4. [Деплой на VPS](#деплой-на-vps)
5. [Откат изменений](#откат-изменений)
6. [Troubleshooting](#troubleshooting)

---

## 1. Основные команды Git

### 🔍 Проверка статуса

```bash
# Проверить текущий статус (что изменено, что не добавлено в коммит)
git status

# Посмотреть изменения в файлах
git diff

# Посмотреть изменения только в конкретном файле
git diff bot/main.py

# Посмотреть последние коммиты
git log --oneline -10
```

---

### ➕ Добавление файлов в коммит

```bash
# Добавить конкретный файл
git add bot/main.py

# Добавить все изменённые файлы
git add .

# Добавить несколько файлов
git add bot/main.py bot/api_server.py

# Добавить все файлы в директории
git add bot/
```

---

### 📝 Создание коммита

```bash
# Создать коммит с сообщением
git commit -m "🔧 Fix email blocking event loop"

# Создать коммит с многострочным сообщением
git commit -m "🔧 Fix email blocking event loop

- Moved email sending to separate thread
- Prevents 502 errors during order processing
- Fixes bot becoming unresponsive"

# Добавить все изменения и сделать коммит за один раз
git commit -am "Quick fix"
```

**💡 Хорошие практики для commit messages:**
- Используйте эмодзи в начале: 🔧 (fix), ✨ (feature), 📚 (docs), 🎨 (style), ⚡ (performance)
- Первая строка — краткое описание (до 50 символов)
- Следующие строки — детали изменений
- Пишите на английском языке

---

## 2. Работа с ветками

### 📌 Текущая структура веток

```
main                     ← Production (стабильная версия)
WebApp_relocation290925  ← Development (разработка новых фич)
```

---

### 🔀 Переключение между ветками

```bash
# Посмотреть все ветки
git branch -a

# Переключиться на ветку main
git checkout main

# Переключиться на ветку разработки
git checkout WebApp_relocation290925

# Создать новую ветку и переключиться на неё
git checkout -b feature/new-feature
```

---

### 🔄 Синхронизация веток

```bash
# Обновить локальную ветку с GitHub
git pull origin main

# Влить изменения из main в текущую ветку
git merge main

# Влить изменения из WebApp_relocation290925 в main
git checkout main
git merge WebApp_relocation290925
```

---

## 3. Коммиты и push на GitHub

### 🚀 Отправка изменений на GitHub

```bash
# Отправить изменения в текущей ветке на GitHub
git push origin main

# Отправить изменения в ветку разработки
git push origin WebApp_relocation290925

# Принудительная отправка (⚠️ ОСТОРОЖНО! Может удалить изменения других разработчиков)
git push --force origin main  # ❌ НЕ ДЕЛАЙТЕ ЭТО БЕЗ НЕОБХОДИМОСТИ!
```

---

### 📦 Полный цикл: изменения → GitHub

```bash
# 1. Проверить, что изменилось
git status

# 2. Добавить файлы в коммит
git add bot/main.py bot/api_server.py

# 3. Создать коммит
git commit -m "🔧 Fix bot hanging after orders"

# 4. Отправить на GitHub
git push origin main
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

