# Руководство по включению парсера как fallback

## 🔄 Как включить парсер как fallback

Если MODX API недоступен, можно включить парсер как резервный источник данных.

### 1. В файле `bot/api_server.py`:

#### В функции `setup_api_server()`:
```python
# Раскомментировать эту строку:
await load_products_data_for_api()
```

#### В функции `get_products_for_webapp()`:
```python
# Раскомментировать весь блок FALLBACK:
await load_products_data_for_api()
if products_data:
    if category_key:
        products_in_category = products_data.get(category_key, [])
        if products_in_category:
            return web.json_response(products_in_category, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
    else:
        return web.json_response(products_data, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
```

#### В функции `get_categories_for_webapp()`:
```python
# Раскомментировать весь блок FALLBACK:
await load_products_data_for_api()
if products_data:
    categories_list = []
    for key, products in products_data.items():
        if products: # Убедимся, что в категории есть продукты
            # Берем первое изображение из первого продукта в категории как изображение для категории
            category_image = products[0].get('image_url', '')
            categories_list.append({
                "key": key,
                "name": products[0].get('category_name', key), # Используем название категории из первого продукта
                "image": category_image
            })
    return web.json_response(categories_list, headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })
```

### 2. Убедиться, что файл `data/products_scraped.json` существует:

```bash
# Запустить парсер для создания файла
python parser_job.py

# Или скопировать существующий файл
cp data/products_scraped.json.backup data/products_scraped.json
```

### 3. Логика работы:

1. **Сначала** пытается загрузить данные из MODX API
2. **Если MODX API недоступен** - загружает данные из парсера (JSON файл)
3. **Если и парсер недоступен** - возвращает ошибку

### 4. Преимущества такого подхода:

- ✅ **Надежность** - если MODX API упадет, парсер продолжит работать
- ✅ **Гибкость** - можно переключаться между источниками данных
- ✅ **Совместимость** - старый код парсера сохранен
- ✅ **Простота** - достаточно раскомментировать несколько строк

### 5. Мониторинг:

```python
# В логах будет видно, какой источник данных используется:
# "API: Загружено X товаров из MODX API" - используется MODX API
# "API: Данные о продуктах успешно загружены из data/products_scraped.json" - используется парсер
```

## 🚨 Важные замечания:

1. **Формат данных** - парсер и MODX API возвращают данные в разном формате
2. **Производительность** - парсер загружает все данные в память при старте
3. **Актуальность** - данные парсера нужно обновлять вручную
4. **Размер файла** - JSON файл может быть большим

## 🔧 Настройка для продакшена:

### Вариант 1: Только MODX API (рекомендуется)
```python
# Оставить закомментированным
# await load_products_data_for_api()
```

### Вариант 2: MODX API + парсер как fallback
```python
# Раскомментировать для включения fallback
await load_products_data_for_api()
```

### Вариант 3: Только парсер (для тестирования)
```python
# Закомментировать MODX API вызовы и раскомментировать парсер
```
