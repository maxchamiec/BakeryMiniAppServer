# 🔄 Автоматическое развертывание из GitHub на A1 Cloud Flex VPS

## 📋 Оглавление

1. [Обзор](#обзор)
2. [Настройка SSH для GitHub](#настройка-ssh-для-github)
3. [Создание deploy скрипта](#создание-deploy-скрипта)
4. [Настройка GitHub Actions](#настройка-github-actions)
5. [Ручное развертывание](#ручное-развертывание)
6. [Решение проблем](#решение-проблем)

---

## 🎯 Обзор

Автоматическое развертывание позволяет обновлять приложение на VPS при каждом push в GitHub.

### 🔄 Процесс:

```
Git Push → GitHub → GitHub Actions → SSH → VPS → Deploy
```

---

## 🔐 Настройка SSH для GitHub

### 1. Создание deploy ключа

На локальной машине:

```bash
# Создайте отдельный ключ для деплоя
ssh-keygen -t rsa -b 4096 -C "github-deploy@bakery" -f ~/.ssh/github_deploy_bakery

# Скопируйте публичный ключ
cat ~/.ssh/github_deploy_bakery.pub
```

### 2. Добавление ключа на VPS

На VPS:

```bash
# Добавьте публичный ключ в authorized_keys
echo "ssh-rsa YOUR_DEPLOY_KEY github-deploy@bakery" >> ~/.ssh/authorized_keys

# Проверьте права
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 3. Добавление ключа в GitHub Secrets

1. Перейдите в **GitHub → Settings → Secrets and variables → Actions**
2. Нажмите **New repository secret**
3. Добавьте секреты:
   - **Name:** `VPS_SSH_KEY`
   - **Value:** Содержимое `~/.ssh/github_deploy_bakery` (приватный ключ)
   
   - **Name:** `VPS_HOST`
   - **Value:** `178.163.244.86`
   
   - **Name:** `VPS_USER`
   - **Value:** `ubuntu`

---

## 📝 Создание deploy скрипта

### На VPS создайте скрипт:

```bash
nano ~/BakeryMiniAppServer/deploy_from_github.sh
```

Содержимое:

```bash
#!/bin/bash

# Deploy script for Bakery Bot on A1 Cloud Flex VPS
# This script pulls latest changes from GitHub and restarts the bot

set -e

echo "🚀 Starting deployment from GitHub..."

# Navigate to project directory
cd /home/ubuntu/BakeryMiniAppServer

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Update dependencies if requirements.txt changed
if git diff HEAD@{1} HEAD --name-only | grep requirements.txt; then
    echo "📦 Updating dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

# Restart bot
echo "🔄 Restarting bot service..."
sudo systemctl restart bakery-bot

# Check status
echo "✅ Checking bot status..."
sleep 3
sudo systemctl status bakery-bot --no-pager

# Show recent logs
echo "📋 Recent logs:"
sudo journalctl -u bakery-bot | tail -20

echo "🎉 Deployment completed successfully!"
```

Сделайте исполняемым:

```bash
chmod +x ~/BakeryMiniAppServer/deploy_from_github.sh
```

### Настройка sudo без пароля для деплоя:

```bash
# Добавьте правило sudo
echo "ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart bakery-bot, /bin/systemctl status bakery-bot, /usr/bin/journalctl -u bakery-bot" | sudo tee /etc/sudoers.d/bakery-deploy
sudo chmod 440 /etc/sudoers.d/bakery-deploy
```

---

## 🤖 Настройка GitHub Actions

### Создайте файл workflow:

```bash
# На локальной машине
mkdir -p .github/workflows
nano .github/workflows/deploy.yml
```

Содержимое:

```yaml
name: Deploy to A1 Cloud Flex VPS

on:
  push:
    branches:
      - main
      - WebApp_relocation290925
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 Checkout code
      uses: actions/checkout@v3
    
    - name: 🔐 Setup SSH
      uses: webfactory/ssh-agent@v0.8.0
      with:
        ssh-private-key: ${{ secrets.VPS_SSH_KEY }}
    
    - name: 🚀 Deploy to VPS
      env:
        VPS_HOST: ${{ secrets.VPS_HOST }}
        VPS_USER: ${{ secrets.VPS_USER }}
      run: |
        ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST << 'EOF'
          cd /home/ubuntu/BakeryMiniAppServer
          git pull origin main
          
          # Update dependencies if needed
          if git diff HEAD@{1} HEAD --name-only | grep requirements.txt; then
            source venv/bin/activate
            pip install -r requirements.txt
            deactivate
          fi
          
          # Restart bot
          sudo systemctl restart bakery-bot
          
          # Wait and check status
          sleep 5
          sudo systemctl status bakery-bot --no-pager || true
        EOF
    
    - name: ✅ Deployment complete
      run: echo "🎉 Deployment to VPS completed successfully!"
```

Закоммитьте и отправьте:

```bash
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions deployment workflow"
git push origin main
```

---

## 🛠️ Ручное развертывание

### Из локальной машины:

```bash
# Подключитесь к VPS
ssh bakery-vps

# Перейдите в проект
cd ~/BakeryMiniAppServer

# Обновите код
git pull origin main

# Перезапустите бота
sudo systemctl restart bakery-bot

# Проверьте статус
sudo systemctl status bakery-bot

# Проверьте логи
sudo journalctl -u bakery-bot -f
```

### Через deploy скрипт:

```bash
ssh bakery-vps "cd ~/BakeryMiniAppServer && ./deploy_from_github.sh"
```

---

## 🚨 Решение проблем

### Проблема: GitHub Actions не может подключиться

**Решение:**
```bash
# Проверьте SSH ключ в GitHub Secrets
# Убедитесь, что публичный ключ добавлен в ~/.ssh/authorized_keys на VPS
cat ~/.ssh/authorized_keys
```

### Проблема: Permission denied при git pull

**Решение:**
```bash
# На VPS настройте git
cd ~/BakeryMiniAppServer
git config --global --add safe.directory /home/ubuntu/BakeryMiniAppServer

# Или клонируйте заново
cd ~
rm -rf BakeryMiniAppServer
git clone https://github.com/maxchamiec/BakeryMiniAppServer.git
```

### Проблема: Бот не перезапускается после деплоя

**Решение:**
```bash
# Проверьте права sudo
sudo visudo -c

# Проверьте файл sudoers
sudo cat /etc/sudoers.d/bakery-deploy

# Проверьте systemd службу
sudo systemctl status bakery-bot
```

---

## 📊 Мониторинг деплоя

### Логи GitHub Actions:

1. Перейдите в **GitHub → Actions**
2. Выберите последний workflow run
3. Просмотрите логи каждого шага

### Проверка на VPS:

```bash
# Проверьте последний коммит
cd ~/BakeryMiniAppServer
git log -1

# Проверьте статус бота
sudo systemctl status bakery-bot

# Проверьте логи
sudo journalctl -u bakery-bot | tail -50
```

---

## 🎯 Best Practices

1. **Тестируйте локально** перед push
2. **Используйте ветки** для экспериментов
3. **Делайте бэкапы** перед большими изменениями
4. **Мониторьте логи** после деплоя
5. **Проверяйте веб-приложение** после обновления

---

## 🔄 Workflow развертывания

### Стандартный процесс:

```bash
# 1. Локальная разработка
git checkout -b feature/new-feature
# ... делаете изменения ...
git add .
git commit -m "Add new feature"

# 2. Тестирование
python3 start_bot.py  # Локально

# 3. Merge в main
git checkout main
git merge feature/new-feature

# 4. Push на GitHub
git push origin main

# 5. GitHub Actions автоматически развернет на VPS

# 6. Проверка на VPS
ssh bakery-vps "sudo journalctl -u bakery-bot -f"
```

---

## 📞 Контакты

- **Администратор:** maxvindsvalr@gmail.com
- **GitHub:** https://github.com/maxchamiec/BakeryMiniAppServer

---

**Дата создания:** 1 октября 2025  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию

