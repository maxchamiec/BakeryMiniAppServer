# parser.py (Предполагаемый путь: C:\Users\Maksim_Chamiec\Documents\Drazhin_bakery_bot\bot\parser.py)

import logging
from bs4 import BeautifulSoup
from aiohttp import ClientSession, ClientResponseError, TCPConnector
import socket
import asyncio
import json
from urllib.parse import urljoin
import os
import uuid # Импортируем модуль uuid для генерации уникальных ID (альтернативный метод)

# ===== МЕТОДЫ ГЕНЕРАЦИИ ID ПРОДУКТОВ =====
# ТЕКУЩИЙ МЕТОД: Использование data-id с веб-страницы
# - Преимущества: Консистентные ID, надежная работа с корзиной
# - Недостатки: Зависимость от структуры веб-страницы
#
# АЛЬТЕРНАТИВНЫЙ МЕТОД: Генерация UUID (закомментирован)
# - Преимущества: Уникальные ID, независимость от веб-страницы
# - Недостатки: Новые ID при каждом запуске, проблемы с корзиной
# ===== КОНЕЦ МЕТОДОВ ГЕНЕРАЦИИ ID =====

# ===== Блок для отладки логирования - НАЧАЛО =====
# Удаляем все существующие обработчики для корневого логгера,
# чтобы гарантировать, что мы не конфликтуем с другими настройками.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Настраиваем логирование с уровнем DEBUG и выводом в консоль
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
logger.debug("Логирование настроено. Это сообщение должно быть видно.")
# ===== Блок для отладки логирования - КОНЕЦ =====

BASE_URL = "https://drazhin.by/"

# --- ДОБАВЛЕННЫЕ СТРОКИ ДЛЯ ОПРЕДЕЛЕНИЯ ПУТИ К ФАЙЛУ С ОТЛАДКОЙ ---
current_file_path = os.path.abspath(__file__)
logger.debug(f"DEBUG PATH: 1. os.path.abspath(__file__) -> {current_file_path}")

current_dir = os.path.dirname(current_file_path)
logger.debug(f"DEBUG PATH: 2. os.path.dirname(current_file_path) -> {current_dir}")

# Предполагаем, что родительская директория 'bot' это корневая директория проекта
ROOT_DIR = os.path.dirname(current_dir)
logger.debug(f"DEBUG PATH: 3. os.path.dirname(current_dir) (ROOT_DIR) -> {ROOT_DIR}")

DATA_DIR = os.path.join(ROOT_DIR, 'data')
logger.debug(f"DEBUG PATH: 4. os.path.join(ROOT_DIR, 'data') (DATA_DIR) -> {DATA_DIR}")

OUTPUT_FILE_PATH = os.path.join(DATA_DIR, 'products_scraped.json')
logger.debug(f"DEBUG PATH: 5. os.path.join(DATA_DIR, 'products_scraped.json') (OUTPUT_FILE_PATH) -> {OUTPUT_FILE_PATH}")
# --- КОНЕЦ ДОБАВЛЕННЫХ СТРОК С ОТЛАДКОЙ ---


async def get_products_from_category_page(session, category_url):
    logger.debug(f"Запрос страницы категории: {category_url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    try:
        async with session.get(category_url, headers=headers) as response:
            response.raise_for_status() # Вызывает исключение для HTTP ошибок 4xx/5xx
            html_content = await response.text()
            logger.debug(f"Первые 500 символов полученного HTML для {category_url}:\n{html_content[:500]}")

            try:
                soup = BeautifulSoup(html_content, 'lxml', from_encoding="utf-8")
            except Exception as e:
                logger.warning(f"Ошибка при парсинге с lxml, пробуем html.parser: {e}")
                soup = BeautifulSoup(html_content, 'html.parser', from_encoding="utf-8")

            # Новый селектор для каждого блока товара
            # Ищем div с классом 'product-item'
            product_elements = soup.select('div.product-item')

            if not product_elements:
                logger.debug(f"Всего найдено заготовок товаров на странице {category_url}: 0")
                return []

            products_on_page = []
            for i, product_element in enumerate(product_elements):
                # Название и относительный URL
                # Ищем внутри текущего product_element
                title_link_element = product_element.select_one('a.open-product-modal.product-item__title')

                if not title_link_element:
                    # Если ссылка в блоке текста не найдена, попробуем главную ссылку
                    title_link_element = product_element.select_one('a.open-product-modal')
                    if not title_link_element:
                        logger.debug(f"Пропуск товара {i} на {category_url}: не найден селектор для названия и ссылки.")
                        continue

                product_name = title_link_element.get_text(strip=True)
                product_relative_url = title_link_element.get('href')
                
                # Извлекаем data-id из ссылки продукта
                product_data_id = title_link_element.get('data-id')
                if not product_data_id:
                    logger.debug(f"Пропуск товара {i} на {category_url}: не найден data-id.")
                    continue

                if not product_name or not product_relative_url:
                    logger.debug(f"Пропуск товара {i} на {category_url}: не удалось извлечь название или URL.")
                    continue

                # !!! ИСПРАВЛЕНИЕ: Используем urljoin для надежного формирования URL продукта
                product_url = urljoin(BASE_URL, product_relative_url)

                # Изображение
                img_element = product_element.select_one('picture source:nth-of-type(1)') # Первый source для webp
                image_url = None
                if img_element and img_element.get('srcset'):
                    srcset_values = img_element.get('srcset').split(',')
                    if srcset_values:
                        image_url_part = srcset_values[0].strip().split(' ')[0]
                        if image_url_part.startswith('//'):
                            image_url = f"https:{image_url_part}"
                        elif image_url_part.startswith('/'):
                            image_url = f"{BASE_URL.rstrip('/')}{image_url_part}"
                        else:
                            image_url = f"{BASE_URL}{image_url_part}"

                # Цена
                price_element = product_element.select_one('div.curent-price')
                price_text = price_element.get_text(strip=True) if price_element else 'N/A'
                price = price_text.replace('р.', '').strip()

                products_on_page.append({
                    'name': product_name,
                    'url': product_url,
                    'image_url': image_url,
                    'price': price,
                    'short_description': 'N/A', # Временно N/A
                    'weight': 'N/A', # Здесь временно N/A, будет обновлено
                    'for_vegans': 'N/A', # Временно N/A
                    'availability_days': 'N/A', # Временно N/A
                    'ingredients': 'N/A', # Временно N/A
                    'calories': 'N/A', # Временно N/A
                    'energy_value': 'N/A', # Временно N/A
                    'data_id': product_data_id # Добавляем data-id из веб-страницы
                })
                logger.debug(f"Найдена заготовка товара: {product_name} ({product_url})")

            logger.debug(f"Всего найдено заготовок товаров на странице {category_url}: {len(products_on_page)}")
            return products_on_page

    except ClientResponseError as e:
        logger.error(f"Ошибка HTTP при получении товаров из категории {category_url}: {e} - Статус: {e.status}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при парсинге категории {category_url}: {e}")
        return []

# НОВАЯ ФУНКЦИЯ для парсинга деталей продукта
async def get_product_details(session, product_url):
    logger.debug(f"Запрос страницы деталей продукта: {product_url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    details = {
        'short_description': 'N/A',
        'weight': 'N/A',
        'for_vegans': 'N/A',
        'availability_days': 'N/A',
        'ingredients': 'N/A',
        'calories': 'N/A',
        'energy_value': 'N/A'
    }
    try:
        async with session.get(product_url, headers=headers) as response:
            response.raise_for_status()
            html_content = await response.text()
            # logger.debug(f"Первые 5000 символов HTML деталей для {product_url}:\n{html_content[:5000]}") # Можно раскомментировать для отладки
            soup = BeautifulSoup(html_content, 'lxml', from_encoding="utf-8") # lxml или html.parser

            # Извлечение веса (селектор подтвержден)
            weight_element = soup.select_one('div.options-item__size span.fw-600')
            if weight_element:
                details['weight'] = weight_element.get_text(strip=True).replace('гр.', '').replace('гр', '').strip()
                logger.debug(f"Найдено детали: Вес: {details['weight']}")
            # Если такой структуры нет, возможно, есть другая, как в предоставленном вами HTML:
            else: # Добавляем запасной вариант, если основной селектор не сработал
                weight_alt_element = soup.select_one('div.product__text-part .wight')
                if weight_alt_element:
                    # Ищем текст внутри .wight, игнорируя span "Вес:"
                    weight_text = weight_alt_element.get_text(strip=True)
                    # Можно использовать regex или просто str.replace, чтобы убрать "Вес:"
                    details['weight'] = weight_text.replace('Вес:', '').replace('гр.', '').replace('гр', '').strip()
                    logger.debug(f"Найдено детали (ALT): Вес: {details['weight']}")

            # !!! ИСПРАВЛЕНИЕ: Извлечение дней доступности
            # Новый селектор для div.days > span
            availability_element = soup.select_one('div.days span')
            if availability_element:
                details['availability_days'] = availability_element.get_text(strip=True)
                logger.debug(f"Найдено детали: Дни доступности: {details['availability_days']}")
            else: # Предыдущий, более общий селектор, если этот не сработал (хотя теперь он менее точен)
                availability_element_old = soup.select_one('div.product-item__bottom-text')
                if availability_element_old:
                    availability_text_old = availability_element_old.get_text(strip=True)
                    if "выпекаем" in availability_text_old or "доступ" in availability_text_old.lower():
                        details['availability_days'] = availability_text_old
                        logger.debug(f"Найдено детали (OLD): Дни доступности: {details['availability_days']}")


            # Извлечение состава
            ingredients_header = soup.find('div', class_='product-description__item', string=lambda text: text and 'Состав продукта' in text)
            if ingredients_header:
                ingredients_value_element = ingredients_header.find_next_sibling('div', class_='product-description__text')
                if ingredients_value_element:
                    details['ingredients'] = ingredients_value_element.get_text(strip=True)
                    logger.debug(f"Найдено детали: Состав: {details['ingredients'][:50]}...")
            # !!! ИСПРАВЛЕНИЕ: Альтернативный селектор для состава
            else:
                ingredients_alt_element = soup.select_one('div.product__text-part .structure')
                if ingredients_alt_element:
                    ingredients_text = ingredients_alt_element.get_text(strip=True)
                    details['ingredients'] = ingredients_text.replace('Состав:', '').strip()
                    logger.debug(f"Найдено детали (ALT): Состав: {details['ingredients'][:50]}...")

            # Извлечение калорийности
            calories_header = soup.find('div', class_='product-description__item', string=lambda text: text and 'Калорийность' in text)
            if calories_header:
                calories_value_element = calories_header.find_next_sibling('div', class_='product-description__text')
                if calories_value_element:
                    details['calories'] = calories_value_element.get_text(strip=True)
                    logger.debug(f"Найдено детали: Калорийность: {details['calories']}")
            # !!! ИСПРАВЛЕНИЕ: Альтернативный селектор для калорийности
            else:
                calories_alt_element = soup.select_one('div.product__text-part .calories')
                if calories_alt_element:
                    calories_text = calories_alt_element.get_text(strip=True)
                    details['calories'] = calories_text.replace('Калорийность:', '').strip()
                    logger.debug(f"Найдено детали (ALT): Калорийность: {details['calories']}")

            # Извлечение энергетической ценности
            energy_header = soup.find('div', class_='product-description__item', string=lambda text: text and 'Энергетическая ценность' in text)
            if energy_header:
                energy_value_element = energy_header.find_next_sibling('div', class_='product-description__text')
                if energy_value_element:
                    details['energy_value'] = energy_value_element.get_text(strip=True)
                    logger.debug(f"Найдено детали: Энергетическая ценность: {details['energy_value']}")
            # !!! ИСПРАВЛЕНИЕ: Альтернативный селектор для энергетической ценности
            else:
                energy_alt_element = soup.select_one('div.product__text-part .bgu') # bgu - вероятно, Белки/Жиры/Углеводы
                if energy_alt_element:
                    energy_text = energy_alt_element.get_text(strip=True)
                    details['energy_value'] = energy_text.replace('Энергетическая ценность:', '').strip()
                    logger.debug(f"Найдено детали (ALT): Энергетическая ценность: {details['energy_value']}")

            # Извлечение краткого описания
            short_desc_element = soup.select_one('div.short-description p')
            if short_desc_element:
                details['short_description'] = short_desc_element.get_text(strip=True)
                logger.debug(f"Найдено детали: Краткое описание: {details['short_description'][:50]}...")
            else:
                # Альтернативный селектор
                short_desc_alt_element = soup.select_one('div.short-description')
                if short_desc_alt_element:
                    details['short_description'] = short_desc_alt_element.get_text(strip=True)
                    logger.debug(f"Найдено детали (ALT): Краткое описание: {details['short_description'][:50]}...")

            # Извлечение информации о веганстве
            # Ищем элемент с текстом "Подходит веганам"
            vegan_spans = soup.find_all('span', string=lambda text: text and 'Подходит веганам' in text)
            if vegan_spans:
                details['for_vegans'] = 'Y'
                logger.debug(f"Найдено детали: Подходит веганам: Y")
            else:
                # Альтернативный поиск - ищем SVG иконку вегана
                vegan_svg = soup.select_one('svg.svg-vegan')
                if vegan_svg:
                    details['for_vegans'] = 'Y'
                    logger.debug(f"Найдено детали (ALT): Подходит веганам: Y (найдена SVG иконка)")
                else:
                    details['for_vegans'] = 'N/A'
                    logger.debug(f"Найдено детали: Подходит веганам: N/A")

            return details

    except ClientResponseError as e:
        logger.error(f"Ошибка HTTP при получении деталей продукта {product_url}: {e} - Статус: {e.status}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при парсинге деталей продукта {product_url}: {e}")
    return details

async def main():
    logger.info("Парсер начал работу в функции main.")

    categories = {
        "category_bakery": "https://drazhin.by/vypechka/",
        "category_croissants": "https://drazhin.by/kruassany/",
        "category_artisan_bread": "https://drazhin.by/remeslennyy-hleb/",
        "category_desserts": "https://drazhin.by/deserty/"
    }

    scraped_data = {
        "category_bakery": [],
        "category_croissants": [],
        "category_artisan_bread": [],
        "category_desserts": []
    }

    connector = TCPConnector(family=socket.AF_INET)
    async with ClientSession(connector=connector) as session:
        for category_name, category_url in categories.items():
            # Шаг 1: Парсинг страниц категорий для получения базовой информации и URL продукта
            products_from_category = await get_products_from_category_page(session, category_url)

            # Шаг 2: Для каждого продукта, спарсить его детальную страницу
            detailed_products = []
            for product_base_info in products_from_category:
                product_url = product_base_info['url'] # Используем URL, который уже получили
                product_details = await get_product_details(session, product_url)

                # Объединяем базовую информацию с детальной
                combined_product_info = {**product_base_info, **product_details}

                # ИСПОЛЬЗУЕМ data-id из веб-страницы вместо генерации UUID
                combined_product_info['id'] = combined_product_info['data_id']
                # Удаляем временное поле data_id, оставляем только id
                del combined_product_info['data_id']
                
                # АЛЬТЕРНАТИВНЫЙ ВАРИАНТ: Генерация UUID (закомментирован)
                # combined_product_info['id'] = str(uuid.uuid4()) 

                detailed_products.append(combined_product_info)
                logger.info(f"Спарсены детали для: {product_base_info['name']} с ID: {combined_product_info['id']} (data-id с веб-страницы)") # Логируем ID

            scraped_data[category_name] = detailed_products
            logger.info(f"Завершено парсинг категории {category_name}. Найдено {len(detailed_products)} полных товаров.")

    # --- ИЗМЕНЕННЫЙ БЛОК ДЛЯ СОХРАНЕНИЯ, ПЕРЕМЕЩЕННЫЙ ВНУТРЬ main() ---
    # Убедимся, что папка 'data' существует
    os.makedirs(DATA_DIR, exist_ok=True) 

    with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    logger.info(f"Данные успешно сохранены в {OUTPUT_FILE_PATH}") 
    logger.info("Парсер завершил работу.")
    # --- КОНЕЦ ИЗМЕНЕННОГО БЛОКА ---

if __name__ == "__main__":
    asyncio.run(main())
