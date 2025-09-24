#!/usr/bin/env python3
"""
MODX Cache Scheduler
Загружает данные из MODX API и сохраняет в JSON кэш каждые 60 секунд.
"""

import asyncio
import json
import logging
import os
import ssl
import aiohttp
from datetime import datetime
from typing import Dict, List, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
MODX_API_BASE_URL = os.environ.get('MODX_API_BASE_URL', 'https://drazhin.by')
MODX_API_TIMEOUT = int(os.environ.get('MODX_API_TIMEOUT', '10'))
CACHE_FILE_PATH = os.path.join('data', 'modx_cache.json')
CACHE_UPDATE_INTERVAL = 60  # секунд

# Создаем директорию data если не существует
os.makedirs('data', exist_ok=True)


async def load_products_from_modx_api() -> List[Dict[str, Any]]:
    """Загружает ВСЕ продукты из MODX API (без фильтрации по категории) с повторными попытками"""
    url = f"{MODX_API_BASE_URL}/api-products.json"
    
    for attempt in range(3):  # 3 попытки
        try:
            # Настройка SSL для Heroku
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=MODX_API_TIMEOUT)
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # MODX API возвращает структуру {'status': 'success', 'count': 68, 'products': [...]}
                        if isinstance(data, dict) and 'products' in data:
                            products = data['products']
                            if isinstance(products, list) and len(products) > 0:
                                logger.info(f"MODX Cache: Products loaded successfully: {len(products)} products")
                                return products
                            else:
                                logger.warning(f"MODX Cache: Products field is not a valid list: {type(products)} (attempt {attempt + 1})")
                                if attempt < 2:  # Не последняя попытка
                                    await asyncio.sleep(1)  # Ждем 1 секунду перед повтором
                                    continue
                                return []
                        else:
                            logger.warning(f"MODX Cache: Unexpected products data structure: {type(data)} (attempt {attempt + 1})")
                            if attempt < 2:
                                await asyncio.sleep(1)
                                continue
                            return []
                    else:
                        text = await response.text()
                        logger.error(f"MODX Cache: API error: {response.status} - {text} (attempt {attempt + 1})")
                        if attempt < 2:
                            await asyncio.sleep(1)
                            continue
                        return {}
        except Exception as e:
            logger.error(f"MODX Cache: Error loading products: {e} (attempt {attempt + 1})")
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {}
    
    return []


async def load_categories_from_modx_api() -> List[Dict[str, Any]]:
    """Загружает категории из MODX API"""
    try:
        url = f"{MODX_API_BASE_URL}/api-categories.json"
        
        # Настройка SSL для Heroku
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=MODX_API_TIMEOUT)
        ) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    categories = data.get('categories', [])
                    logger.info(f"MODX Cache: Categories loaded successfully: {len(categories)} categories")
                    return categories
                else:
                    text = await response.text()
                    logger.error(f"MODX Cache: API error: {response.status} - {text}")
                    return []
    except Exception as e:
        logger.error(f"MODX Cache: Error loading categories: {e}")
        return []


async def save_cache_to_file(products_data: List[Dict[str, Any]], 
                           categories_data: List[Dict[str, Any]]) -> bool:
    """Сохраняет данные в JSON файл атомарно"""
    try:
        timestamp = datetime.now().isoformat()
        version = f"v{int(datetime.now().timestamp())}"
        
        # Преобразуем массив продуктов в структуру по категориям
        products_by_category = {}
        for product in products_data:
            category_id = product.get('parent_id')
            if category_id:
                category_key = f"category_{category_id}"
                if category_key not in products_by_category:
                    products_by_category[category_key] = []
                
                # Преобразуем продукт в формат для frontend
                formatted_product = {
                    "id": product['id'],
                    "name": product['pagetitle'],
                    "url": f"https://drazhin.by/{product.get('alias', '')}",
                    "image": product.get('image', ''),
                    "price": str(product['price']),
                    "short_description": product.get('product_description', 'N/A'),
                    "weight": str(product['weight']),
                    "for_vegans": product.get('product_vegan', 'N/A'),
                    "availability_days": product.get('product_days_order', 'N/A'),
                    "ingredients": product.get('product_structure', 'N/A'),
                    "calories": product.get('product_calories', 'N/A'),
                    "energy_value": product.get('product_bgu', 'N/A'),
                    "images": product.get('images', []),
                    "menuindex": product.get('menuindex', 0)
                }
                products_by_category[category_key].append(formatted_product)
        
        # Сортируем продукты по menuindex
        for category_key in products_by_category:
            products_by_category[category_key].sort(key=lambda x: int(x.get('menuindex', 0)))
        
        # Подготавливаем данные для сохранения
        cache_data = {
            "products": products_by_category,
            "categories": categories_data if isinstance(categories_data, list) else [],
            "metadata": {
                "last_updated": timestamp,
                "version": version,
                "products_count": len(products_data),
                "categories_count": len(categories_data) if isinstance(categories_data, list) else 0
            }
        }
        
        # Атомарная запись через временный файл
        temp_file = f"{CACHE_FILE_PATH}.tmp"
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        # Атомарное переименование
        os.rename(temp_file, CACHE_FILE_PATH)
        
        logger.info(f"MODX Cache: Cache updated successfully - version {version}")
        logger.info(f"MODX Cache: Products: {cache_data['metadata']['products_count']}, Categories: {cache_data['metadata']['categories_count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"MODX Cache: Error saving cache: {e}")
        # Удаляем временный файл если он существует
        temp_file = f"{CACHE_FILE_PATH}.tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False


async def update_cache():
    """Обновляет кэш данных из MODX API"""
    logger.info("MODX Cache: Starting cache update...")
    
    try:
        # Загружаем данные параллельно
        products_task = load_products_from_modx_api()
        categories_task = load_categories_from_modx_api()
        
        products_data, categories_data = await asyncio.gather(
            products_task, 
            categories_task,
            return_exceptions=True
        )
        
        # Проверяем результаты
        if isinstance(products_data, Exception):
            logger.error(f"MODX Cache: Products loading failed: {products_data}")
            return False
            
        if isinstance(categories_data, Exception):
            logger.error(f"MODX Cache: Categories loading failed: {categories_data}")
            return False
        
        # Проверяем что данные не пустые и правильного типа
        if not isinstance(products_data, list):
            logger.error(f"MODX Cache: Products data is not a list: {type(products_data)}")
            return False
            
        if not isinstance(categories_data, list):
            logger.error(f"MODX Cache: Categories data is not a list: {type(categories_data)}")
            return False
            
        if not products_data and not categories_data:
            logger.warning("MODX Cache: Both products and categories are empty")
            return False
        
        # Сохраняем в файл
        success = await save_cache_to_file(products_data, categories_data)
        
        if success:
            logger.info("MODX Cache: Cache update completed successfully")
        else:
            logger.error("MODX Cache: Cache update failed")
            
        return success
        
    except Exception as e:
        logger.error(f"MODX Cache: Unexpected error during cache update: {e}")
        return False


async def cache_update_loop():
    """Основной цикл обновления кэша"""
    logger.info(f"MODX Cache: Starting cache scheduler (interval: {CACHE_UPDATE_INTERVAL}s)")
    
    # Первоначальное обновление
    await update_cache()
    
    # Цикл обновления
    while True:
        try:
            await asyncio.sleep(CACHE_UPDATE_INTERVAL)
            await update_cache()
        except KeyboardInterrupt:
            logger.info("MODX Cache: Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"MODX Cache: Error in update loop: {e}")
            await asyncio.sleep(10)  # Ждем 10 секунд при ошибке


async def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Режим для scheduler job - выполнить один раз
        logger.info("MODX Cache: Starting one-time cache update")
        try:
            await update_cache()
            logger.info("MODX Cache: One-time update completed")
        except Exception as e:
            logger.error(f"MODX Cache: One-time update failed: {e}")
    else:
        # Режим для worker dyno - бесконечный цикл
        logger.info("MODX Cache: Starting MODX Cache Scheduler")
        try:
            await cache_update_loop()
        except KeyboardInterrupt:
            logger.info("MODX Cache: Scheduler terminated")
        except Exception as e:
            logger.error(f"MODX Cache: Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
