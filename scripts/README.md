# 🚀 Cache Management Scripts

Коллекция скриптов для управления кеш-версиями в Bakery Mini App.

## 📋 Обзор

Эта система заменяет старый `bump_cache.sh` более надежным и расширяемым решением на Python с bash-оберткой для совместимости.

## 🔧 Скрипты

### 1. `cache_manager.py` - Основной менеджер кеша

**Описание:** Комплексная система управления кеш-версиями для всех типов файлов.

**Возможности:**
- ✅ Обновление кеш-версий во всех файлах WebApp
- ✅ Автоматическое создание backup'ов
- ✅ Валидация изменений
- ✅ Rollback из backup'а
- ✅ Поддержка всех типов файлов (HTML, CSS, JS, SVG)
- ✅ Обработка `sprite.svg`, `main.min.css`, и всех SVG в `images/`

**Использование:**
```bash
# Обновить версию кеша
python3 scripts/cache_manager.py 1.3.111

# Обновить с кастомным timestamp
python3 scripts/cache_manager.py 1.3.111 --timestamp 1756284000

# Только валидация (без изменений)
python3 scripts/cache_manager.py 1.3.111 --validate-only

# Без создания backup
python3 scripts/cache_manager.py 1.3.111 --no-backup

# Rollback из backup
python3 scripts/cache_manager.py 1.3.111 --rollback
```

**Что обновляется:**
- `bot/web_app/index.html` - все ссылки на ресурсы
- `bot/web_app/style.css` - все `url()` ссылки
- `bot/web_app/main.min.css` - все `url()` ссылки
- `bot/web_app/script.js` - константа `CACHE_VERSION` и все ссылки на файлы
- `bot/web_app/sprite.svg` - любые ссылки на ресурсы
- `bot/web_app/images/*.svg` - все SVG файлы в папке images

### 2. `bump_cache.sh` - Bash обертка

**Описание:** Обновленная bash-обертка для `cache_manager.py` с улучшенной обработкой аргументов.

**Использование:**
```bash
# Стандартное обновление
./scripts/bump_cache.sh 1.3.111

# С кастомным timestamp
./scripts/bump_cache.sh 1.3.111 1756284000

# Только валидация
./scripts/bump_cache.sh 1.3.111 --validate-only

# Без backup
./scripts/bump_cache.sh 1.3.111 --no-backup

# Rollback
./scripts/bump_cache.sh 1.3.111 --rollback

# Помощь
./scripts/bump_cache.sh --help
```

### 3. `validate_cache.py` - Валидатор кеша

**Описание:** Независимый валидатор для проверки консистентности кеш-версий.

**Возможности:**
- ✅ Поиск дублированных параметров кеша
- ✅ Обнаружение неправильно сформированных параметров
- ✅ Проверка незакрытых кавычек
- ✅ Анализ консистентности версий
- ✅ Подробный отчет о найденных проблемах

**Использование:**
```bash
python3 scripts/validate_cache.py
```

### 4. `test_cache_manager.py` - Тестовый набор

**Описание:** Комплексные тесты для проверки функциональности системы управления кешем.

**Использование:**
```bash
python3 scripts/test_cache_manager.py
```

## 🎯 Workflow

### Стандартное обновление версии:
```bash
# 1. Проверить текущее состояние
python3 scripts/validate_cache.py

# 2. Обновить версию
./scripts/bump_cache.sh 1.3.111

# 3. Задеплоить
git add .
git commit -m 'Bump cache to 1.3.111'
git push
```

### Разработка и тестирование:
```bash
# 1. Запустить тесты
python3 scripts/test_cache_manager.py

# 2. Обновить с backup
./scripts/bump_cache.sh 1.3.111

# 3. Проверить результат
python3 scripts/validate_cache.py

# 4. При необходимости откатить
./scripts/bump_cache.sh 1.3.111 --rollback
```

## 🔍 Обработка файлов

### HTML файлы (`index.html`)
- `<script src="...">` теги
- `<link href="...">` теги  
- `<img src="...">` теги

**Пример:**
```html
<!-- До -->
<script src="script.js?v=1.3.109&t=1756284000"></script>
<!-- После -->
<script src="script.js?v=1.3.111&t=1756912558"></script>
```

### CSS файлы (`style.css`, `main.min.css`)
- `url()` функции
- `background-image` свойства

**Пример:**
```css
/* До */
background-image: url('images/bg.jpg?v=1.3.109&t=1756284000');
/* После */
background-image: url('images/bg.jpg?v=1.3.111&t=1756912558');
```

### JavaScript файлы (`script.js`)
- Константа `CACHE_VERSION`
- Строковые литералы с путями к файлам
- Template literals (backticks)

**Пример:**
```javascript
// До
const CACHE_VERSION = '1.3.109';
const img = 'images/icon.svg?v=1.3.109&t=1756284000';
// После
const CACHE_VERSION = '1.3.111';
const img = 'images/icon.svg?v=1.3.111&t=1756912558';
```

### SVG файлы
- Любые ссылки на другие ресурсы
- `xlink:href` атрибуты

## 🛡️ Безопасность и Backup

### Автоматические Backup'ы
- Создаются автоматически перед каждым обновлением
- Сохраняются в `backup_cache_[timestamp]/`
- Содержат копии всех измененных файлов

### Rollback
```bash
# Откатить к последнему backup'у
./scripts/bump_cache.sh 1.3.111 --rollback
```

### Валидация
- Автоматическая валидация после каждого обновления
- Независимая валидация через `validate_cache.py`
- Проверка синтаксиса и консистентности

## 🚨 Решение проблем

### Проблема: "Unclosed quotes"
```bash
# Запустить валидацию для диагностики
python3 scripts/validate_cache.py

# Исправить вручную или откатить
./scripts/bump_cache.sh --rollback
```

### Проблема: "Version inconsistency"
```bash
# Принудительно синхронизировать все версии
./scripts/bump_cache.sh 1.3.111 --no-backup
```

### Проблема: "Backup not found"
```bash
# Проверить доступные backup'ы
ls -la backup_cache_*

# Или создать обновление без rollback
./scripts/bump_cache.sh 1.3.111
```

## 📈 Улучшения по сравнению со старым `bump_cache.sh`

### ✅ Исправленные проблемы:
1. **Inconsistent versions** - Теперь все файлы обновляются синхронно
2. **Regex issues** - Более точные regex patterns для каждого типа файла
3. **Version verification** - Полная валидация вместо проверки только последней цифры
4. **Bash variables in Python** - Убрана проблема с heredoc
5. **Relative paths** - Правильная обработка всех типов путей
6. **File type coverage** - Поддержка всех файлов включая `main.min.css` и SVG
7. **Encoding issues** - Явное указание UTF-8
8. **No rollback** - Добавлен функционал отката
9. **Error handling** - Подробная диагностика ошибок
10. **Testing** - Комплексное тестирование

### 🚀 Новые возможности:
- Автоматические backup'ы
- Rollback функциональность
- Независимая валидация
- Поддержка всех типов файлов
- Подробная отчетность
- Comprehensive тестирование
- Лучшая обработка ошибок

## 📝 Совместимость

- **Python 3.7+** - Основные скрипты
- **Bash 4.0+** - Wrapper скрипт
- **UTF-8** - Кодировка файлов
- **Unix-like systems** - macOS, Linux

## 🤝 Использование в CI/CD

```yaml
# Пример для GitHub Actions
- name: Update cache version
  run: |
    ./scripts/bump_cache.sh ${{ github.run_number }}
    git add .
    git commit -m "Bump cache to ${{ github.run_number }}"
```

---

**Создано:** Сентябрь 2025  
**Автор:** AI Assistant  
**Версия:** 1.0.0

