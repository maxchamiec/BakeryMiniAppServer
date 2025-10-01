import json
import logging
import os
import time
import hmac
import hashlib
import base64
import ssl
import aiohttp
from aiohttp import web
import aiohttp_cors
from collections import defaultdict
from datetime import datetime

from bot.config import config
from bot.security_manager import security_manager
from bot.security_headers import security_headers_middleware, create_content_hash

# Настраиваем логирование для API сервера
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Путь к файлу с данными о продуктах
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DATA_FILE = os.path.join(BASE_DIR, 'data', 'products_scraped.json')  # Старый парсер (сохранен)
MODX_CACHE_FILE = os.path.join(BASE_DIR, 'data', 'modx_cache.json')  # Новый MODX кэш

# MODX API Configuration
MODX_API_BASE_URL = os.environ.get('MODX_API_BASE_URL', 'https://drazhin.by')
MODX_API_TIMEOUT = int(os.environ.get('MODX_API_TIMEOUT', '10'))

# ===== SECURITY CONFIGURATION =====
# HMAC secret key for request signing (should be in environment variables)
HMAC_SECRET = os.environ.get('HMAC_SECRET', 'default-secret-key-change-in-production')
HMAC_ALGORITHM = 'sha256'

# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_HOUR = 100  # Max requests per hour per IP
RATE_LIMIT_BLOCK_DURATION = 3600    # Block duration in seconds (1 hour)

# In-memory storage for rate limiting (in production, use Redis)
rate_limit_storage = defaultdict(list)

# ===== HMAC SIGNATURE FUNCTIONS =====
def generate_hmac_signature(data: str, secret: str) -> str:
    """Generate HMAC signature for data"""
    signature = hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)

# ===== MODX API FUNCTIONS =====
async def load_products_from_modx_api(category_id: str = None) -> list:
    """Загружает товары через MODX API"""
    try:
        url = f"{MODX_API_BASE_URL}/api-products.json"
        params = {'category': category_id} if category_id else {}
        
        # Настройка SSL для Heroku
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=MODX_API_TIMEOUT)
        ) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('products', [])
                else:
                    text = await response.text()
                    logger.error(f"API: Ошибка MODX API: {response.status} - {text}")
                    return []
    except Exception as e:
        logger.error(f"API: Ошибка загрузки из MODX API: {e}")
        return []

async def load_categories_from_modx_api() -> list:
    """Загружает категории через MODX API"""
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
                    return data.get('categories', [])
                else:
                    text = await response.text()
                    logger.error(f"API: Ошибка MODX API: {response.status} - {text}")
                    return []
    except Exception as e:
        logger.error(f"API: Ошибка загрузки из MODX API: {e}")
        import traceback
        logger.error(f"API: Traceback: {traceback.format_exc()}")
        return []

# ===== RATE LIMITING FUNCTIONS =====
def check_rate_limit(ip_address: str) -> bool:
    """Check if IP address is within rate limits"""
    current_time = time.time()
    
    # Clean old entries
    rate_limit_storage[ip_address] = [
        timestamp for timestamp in rate_limit_storage[ip_address]
        if current_time - timestamp < 3600  # Keep only last hour
    ]
    
    # Check if limit exceeded
    if len(rate_limit_storage[ip_address]) >= RATE_LIMIT_REQUESTS_PER_HOUR:
        return False
    
    # Add current request
    rate_limit_storage[ip_address].append(current_time)
    return True

# ===== TOKEN GENERATION =====
def generate_auth_token() -> dict:
    """Generate authentication token for client"""
    timestamp = int(time.time())
    token_data = f"auth:{timestamp}"
    signature = generate_hmac_signature(token_data, HMAC_SECRET)
    
    return {
        "token": signature,
        "timestamp": timestamp,
        "expires_in": 3600  # 1 hour
    }

async def get_auth_token(request):
    """Generate authentication token for client"""
    try:
        client_ip = getattr(request, 'remote', None) or "unknown"
    except Exception:
        client_ip = "unknown"
    
    # Basic rate limiting for token requests (more strict)
    if not check_rate_limit(f"{client_ip}:token"):
        logger.warning(f"API: Token rate limit exceeded for IP {client_ip}")
        return web.json_response({"error": "Token rate limit exceeded"}, status=429)
    
    token_data = generate_auth_token()
    
    return web.json_response(token_data, headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })

# Путь к директории с файлами Web App
WEB_APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_app')

# Глобальная переменная для хранения данных о продуктах
products_data = {}

# Глобальная переменная для хранения MODX кэша
modx_cache_data = {}

# API rate limiting store
api_rate_limit_store = defaultdict(list)

async def load_products_data_for_api():
    """Загружает данные о продуктах из JSON-файла для API (старый парсер)."""
    global products_data
    if os.path.exists(PRODUCTS_DATA_FILE):
        try:
            with open(PRODUCTS_DATA_FILE, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"API: Ошибка при чтении JSON-файла '{PRODUCTS_DATA_FILE}': {e}")
            products_data = {} # Сброс данных, если файл поврежден
        except Exception as e:
            logger.error(f"API: Неизвестная ошибка при загрузке данных о продуктах: {e}")
            products_data = {}
    else:
        logger.warning(f"API: Файл '{PRODUCTS_DATA_FILE}' не найден. API не сможет отдавать данные о продуктах.")
        products_data = {}


async def load_modx_cache_data():
    """Загружает данные из MODX кэша."""
    global modx_cache_data
    if os.path.exists(MODX_CACHE_FILE):
        try:
            with open(MODX_CACHE_FILE, 'r', encoding='utf-8') as f:
                modx_cache_data = json.load(f)
            logger.info(f"API: MODX cache loaded successfully - version {modx_cache_data.get('metadata', {}).get('version', 'unknown')}")
        except json.JSONDecodeError as e:
            logger.error(f"API: Ошибка при чтении MODX кэша '{MODX_CACHE_FILE}': {e}")
            modx_cache_data = {}
        except Exception as e:
            logger.error(f"API: Неизвестная ошибка при загрузке MODX кэша: {e}")
            modx_cache_data = {}
    else:
        logger.warning(f"API: MODX кэш '{MODX_CACHE_FILE}' не найден. Используем fallback на MODX API.")
        modx_cache_data = {}


def get_modx_cache_products():
    """Возвращает продукты из MODX кэша."""
    # Перезагружаем кэш при каждом запросе
    if os.path.exists(MODX_CACHE_FILE):
        try:
            with open(MODX_CACHE_FILE, 'r', encoding='utf-8') as f:
                current_cache = json.load(f)
                return current_cache.get('products', {})
        except json.JSONDecodeError:
            return {}
    return {}


def get_modx_cache_categories():
    """Возвращает категории из MODX кэша."""
    # Перезагружаем кэш при каждом запросе
    if os.path.exists(MODX_CACHE_FILE):
        try:
            with open(MODX_CACHE_FILE, 'r', encoding='utf-8') as f:
                current_cache = json.load(f)
                return current_cache.get('categories', [])
        except json.JSONDecodeError:
            return []
    return []


def get_modx_cache_metadata():
    """Возвращает метаданные MODX кэша."""
    # Перезагружаем кэш при каждом запросе
    logger.info(f"API: Checking MODX cache file: {MODX_CACHE_FILE}")
    if os.path.exists(MODX_CACHE_FILE):
        try:
            # Проверяем размер файла
            file_size = os.path.getsize(MODX_CACHE_FILE)
            logger.info(f"API: MODX cache file size: {file_size} bytes")
            
            with open(MODX_CACHE_FILE, 'r', encoding='utf-8') as f:
                current_cache = json.load(f)
                metadata = current_cache.get('metadata', {})
                logger.info(f"API: MODX cache metadata loaded - version {metadata.get('version', 'unknown')}")
                return metadata
        except json.JSONDecodeError as e:
            logger.error(f"API: JSON decode error in MODX cache: {e}")
            return {}
    else:
        logger.warning(f"API: MODX cache file not found: {MODX_CACHE_FILE}")
    return {}

async def check_api_rate_limit(request, action: str = "api_request") -> bool:
    """Check API rate limiting."""
    if not config.ENABLE_RATE_LIMITING:
        return True
    
    # Get client IP - fix for potential blocking
    try:
        client_ip = request.headers.get('X-Forwarded-For') or getattr(request, 'remote', None) or "unknown"
    except Exception:
        client_ip = "unknown"
    
    current_time = time.time()
    key = f"api_{client_ip}_{action}"
    
    # Clean old entries
    api_rate_limit_store[key] = [
        timestamp for timestamp in api_rate_limit_store[key]
        if current_time - timestamp < config.RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(api_rate_limit_store[key]) >= config.RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"🚫 API rate limit exceeded for IP {client_ip}, action: {action}")
        security_manager._log_security_event("api_rate_limit_exceeded", {
            "client_ip": client_ip,
            "action": action,
            "current_count": len(api_rate_limit_store[key])
        })
        return False
    
    # Add current request
    api_rate_limit_store[key].append(current_time)
    return True

async def get_products_for_webapp(request):
    """Отдает данные о продуктах для Web App, с возможностью фильтрации по категории."""
    
    # ===== RATE LIMITING =====
    try:
        client_ip = getattr(request, 'remote', None) or "unknown"
    except Exception:
        client_ip = "unknown"
    if not check_rate_limit(client_ip):
        logger.warning(f"API: Rate limit exceeded for IP {client_ip}")
        return web.json_response({"error": "Rate limit exceeded"}, status=429, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    # ===== HMAC SIGNATURE VERIFICATION =====
    signature = request.headers.get('X-Signature')
    timestamp = request.headers.get('X-Timestamp')
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    
    if not signature or not timestamp:
        logger.warning(f"API: Missing signature or timestamp from {client_ip}")
        return web.json_response({"error": "Missing signature"}, status=403, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    # Check timestamp (prevent replay attacks)
    current_time = int(time.time())
    request_time = int(timestamp)
    if abs(current_time - request_time) > 300:  # 5 minutes tolerance
        logger.warning(f"API: Timestamp too old from {client_ip}")
        return web.json_response({"error": "Request expired"}, status=403, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    # Use Telegram initData as secret (unique per session)
    hmac_secret = init_data if init_data else HMAC_SECRET
    
    # Verify signature - use only path without query parameters
    request_data = f"{request.method}:{request.url.path}:{timestamp}"
    if not verify_hmac_signature(request_data, signature, hmac_secret):
        logger.warning(f"API: Invalid signature from {client_ip}")
        return web.json_response({"error": "Invalid signature"}, status=403, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    requested_category = request.query.get('category')

    # Пытаемся загрузить из MODX кэша
    try:
        products = get_modx_cache_products()
        
        if not products:
            # Fallback на MODX API если кэш пустой
            logger.warning("API: MODX cache products empty, falling back to MODX API")
            # Преобразуем requested_category в category_id для MODX API
            category_id = None
            if requested_category and requested_category.startswith('category_'):
                category_id = requested_category.replace('category_', '')
            
            products = await load_products_from_modx_api(category_id)
        
        if products:
            
            # Если запрашивается конкретная категория, фильтруем продукты по parent_id
            if requested_category and category_id:
                filtered_products = [p for p in products if p.get('parent_id') == category_id]
                products = filtered_products
            
            # Преобразуем MODX API данные в формат парсера (по категориям)
            products_by_category = {}
            
            for product in products:
                try:
                    product_category_id = product['parent_id']
                except KeyError as e:
                    logger.error(f"API: Ошибка в структуре продукта: {e}, продукт: {product}")
                    continue
                
                # Создаем ключ категории в формате парсера
                category_key = f"category_{product_category_id}"
                
                if category_key not in products_by_category:
                    products_by_category[category_key] = []
                
                # Преобразуем продукт в формат парсера
                try:
                    # Очищаем цену и вес от пробелов и запятых
                    clean_price = str(product['price']).replace(' ', '').replace(',', '.')
                    clean_weight = str(product['weight']).replace(' ', '').replace(',', '.')
                    
                    formatted_product = {
                        "id": product['id'],
                        "name": product['pagetitle'],
                        "url": f"https://drazhin.by/{product.get('alias', '')}",
                        "image": product.get('image', ''),
                        "price": str(float(clean_price)),
                        "short_description": product.get('product_description', 'N/A'),
                        "weight": str(int(float(clean_weight))),
                        "for_vegans": product.get('product_vegan', 'N/A'),
                        "availability_days": product.get('product_days_order', 'N/A'),
                        "ingredients": product.get('product_structure', 'N/A'),
                        "calories": product.get('product_calories', 'N/A'),
                        "energy_value": product.get('product_bgu', 'N/A'),
                        "images": product.get('images', []),
                        "menuindex": product.get('menuindex', 0)
                    }
                    
                    products_by_category[category_key].append(formatted_product)
                except (ValueError, KeyError) as e:
                    logger.error(f"API: Ошибка форматирования продукта {product.get('id', 'unknown')}: {e}")
                    continue
            
            # Сортируем продукты по menuindex
            for category_key in products_by_category:
                products_by_category[category_key].sort(key=lambda x: int(x.get('menuindex', 0)))
            
            # Если запрашивается конкретная категория, возвращаем только её
            if requested_category:
                if requested_category in products_by_category:
                    # Получаем информацию о категории
                    categories = await load_categories_from_modx_api()
                    category_info = None
                    if categories:
                        for cat in categories:
                            if cat['id'] == category_id:
                                category_info = {
                                    "id": cat['id'],
                                    "name": cat['name'],
                                    "key": requested_category
                                }
                                break
                    
                    
                    # Возвращаем объект с информацией о категории и продуктами
                    response_data = {
                        "category": category_info,
                        "products": products_by_category[requested_category]
                    }
                    
                    return web.json_response(response_data, headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    })
                else:
                    logger.warning(f"API: Категория {requested_category} не найдена в products_by_category")
                    return web.json_response({"error": "Category not found"}, status=404, headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    })
            else:
                # Возвращаем все категории
                return web.json_response(products_by_category, headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                })
        else:
            logger.warning("API: MODX API не вернул данные о продуктах.")
            
            # FALLBACK: Парсер закомментирован - используем только MODX API
            # if products_data:
            #     if category_key:
            #         products_in_category = products_data.get(category_key, [])
            #         if not products_in_category:
            #             logger.warning(f"API: Категория '{category_key}' не найдена или пуста.")
            #             return web.json_response({"error": "Category not found or empty"}, status=404, headers={
            #                 'Cache-Control': 'no-cache, no-store, must-revalidate',
            #                 'Pragma': 'no-cache',
            #                 'Expires': '0'
            #             })
            #         return web.json_response(products_in_category, headers={
            #             'Cache-Control': 'no-cache, no-store, must-revalidate',
            #             'Pragma': 'no-cache',
            #             'Expires': '0'
            #         })
            #     else:
            #         return web.json_response(products_data, headers={
            #             'Cache-Control': 'no-cache, no-store, must-revalidate',
            #             'Pragma': 'no-cache',
            #             'Expires': '0'
            #         })
            
            return web.json_response({"error": "No products available from MODX API"}, status=404, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
        
    except Exception as e:
        logger.error(f"API: Ошибка загрузки продуктов: {e}")
        import traceback
        logger.error(f"API: Traceback: {traceback.format_exc()}")
        return web.json_response({"error": "Failed to load products"}, status=500, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })

async def get_all_data_for_webapp(request):
    """Отдает ВСЕ данные (продукты + категории) из MODX кэша."""
    # Check rate limiting
    if not await check_api_rate_limit(request, "get_all_data"):
        return web.json_response({"error": "Rate limit exceeded"}, status=429, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    # Пытаемся загрузить из MODX кэша
    try:
        products = get_modx_cache_products()
        categories = get_modx_cache_categories()
        metadata = get_modx_cache_metadata()
        
        if products or categories:
            # Возвращаем данные из кэша
            response_data = {
                "products": products,
                "categories": categories,
                "metadata": metadata
            }
            
            logger.info(f"API: All data served from MODX cache - version {metadata.get('version', 'unknown')}")
            return web.json_response(response_data, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
        else:
            # Fallback на MODX API если кэш пустой
            logger.warning("API: MODX cache is empty, falling back to MODX API")
            products = await load_products_from_modx_api()
            categories = await load_categories_from_modx_api()
            
            response_data = {
                "products": products,
                "categories": categories,
                "metadata": {
                    "source": "modx_api_fallback",
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            return web.json_response(response_data, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
            
    except Exception as e:
        logger.error(f"API: Error serving all data: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)


async def get_categories_for_webapp(request):
    """Отдает список категорий для Web App."""
    # Check rate limiting
    if not await check_api_rate_limit(request, "get_categories"):
        return web.json_response({"error": "Rate limit exceeded"}, status=429, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
    
    # Пытаемся загрузить из MODX кэша
    try:
        categories = get_modx_cache_categories()
        
        if categories:
            # Возвращаем категории из кэша
            logger.info(f"API: Categories served from MODX cache - {len(categories)} categories")
            return web.json_response(categories, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
        else:
            # Fallback на MODX API
            logger.warning("API: MODX cache categories empty, falling back to MODX API")
            categories = await load_categories_from_modx_api()
            
            if categories:
                # Преобразуем формат для фронтенда
                categories_list = []
                for category in categories:
                    # Создаем ключ категории в формате парсера
                    category_key = f"category_{category['id']}"
                    
                    categories_list.append({
                        "key": category_key,
                        "name": category['name'],
                        "image": category.get('image', ''),  # Используем изображение из MODX API
                        "menuindex": category.get('menuindex', 0)  # Добавляем menuindex для сортировки
                    })
            
                # Логируем порядок до сортировки
                before_sort = [f"{cat['name']}({cat['menuindex']})" for cat in categories_list]
                
                # Сортируем категории по menuindex
                categories_list.sort(key=lambda x: x.get('menuindex', 0))
                
                # Логируем порядок после сортировки
                after_sort = [f"{cat['name']}({cat['menuindex']})" for cat in categories_list]
                
                return web.json_response(categories_list, headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                })
            else:
                logger.warning("API: MODX API не вернул данные о категориях.")
                
                # FALLBACK: Парсер закомментирован - используем только MODX API
            # if products_data:
            #     categories_list = []
            #     for key, products in products_data.items():
            #         if products: # Убедимся, что в категории есть продукты
            #             # Берем первое изображение из первого продукта в категории как изображение для категории
            #             category_image = products[0].get('image', '')
            #             categories_list.append({
            #                 "key": key,
            #                 "name": products[0].get('category_name', key), # Используем название категории из первого продукта
            #                 "image": category_image
            #             })
            #     return web.json_response(categories_list, headers={
            #         'Cache-Control': 'no-cache, no-store, must-revalidate',
            #         'Pragma': 'no-cache',
            #         'Expires': '0'
            #     })
            
            return web.json_response({"error": "No categories available from MODX API"}, status=404, headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
        
    except Exception as e:
        logger.error(f"API: Ошибка загрузки категорий: {e}")
        return web.json_response({"error": "Failed to load categories"}, status=500, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })

async def serve_main_app_page(request):
    """Отдает главный HTML файл Web App."""
    return web.FileResponse(os.path.join(WEB_APP_DIR, 'index.html'))

async def setup_api_server():
    """Настраивает и возвращает AioHTTP Web Application Runner."""
    app = web.Application()

    # Add security headers middleware
    app.middlewares.append(security_headers_middleware)

    # Загружаем данные о продуктах при настройке сервера (ПАРСЕР - ЗАКОММЕНТИРОВАН)
    # await load_products_data_for_api()
    
    # Загружаем MODX кэш при настройке сервера
    # MODX кэш будет загружаться при каждом запросе
    # await load_modx_cache_data()  # Убрано - загружаем при каждом запросе

    # ДОБАВЛЕНО: Перенаправление с корневого пути на '/bot-app/'
    app.router.add_get('/', lambda r: web.HTTPFound('/bot-app/'))

    # 1. Маршрут для получения ВСЕХ данных (продукты + категории)
    app.router.add_get('/bot-app/api/all', get_all_data_for_webapp)

    # 2. Маршрут для получения всех продуктов (или по категории) - СОХРАНЕН для совместимости
    app.router.add_get('/bot-app/api/products', get_products_for_webapp)

    # 3. Маршрут для получения категорий - СОХРАНЕН для совместимости
    app.router.add_get('/bot-app/api/categories', get_categories_for_webapp)
    
    # 3. Маршрут для получения токена аутентификации
    app.router.add_get('/bot-app/api/auth/token', get_auth_token)

    # 3. Маршрут для главной страницы Web App
    app.router.add_get('/bot-app/', serve_main_app_page)

    # 4. Маршрут для статических файлов Web App (CSS, JS, images) внутри /bot-app/
    # Добавляем обработчик для статических файлов с контролем кеширования
    async def serve_static_with_cache_control(request):
        """Serves static files with proper cache control headers."""
        file_path = request.match_info.get('filename', '')
        full_path = os.path.join(WEB_APP_DIR, file_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            # Read file content first
            try:
                with open(full_path, 'rb') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {full_path}: {e}")
                return web.Response(status=500, text="Error reading file")
            
            # Определяем тип содержимого на основе расширения файла
            content_type = 'text/html'
            if file_path.endswith('.css'):
                content_type = 'text/css'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.png'):
                content_type = 'image/png'
            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif file_path.endswith('.svg'):
                content_type = 'image/svg+xml'
            

            
            # Check if file has version query parameter (e.g., ?v=1.2.0)
            query_string = request.query_string
            has_version = 'v=' in query_string
            
            # Create stable content hash for ETag
            content_hash = create_content_hash(content)
            
            if has_version:
                # Versioned files should be cached for a long time
                headers = {
                    'Content-Type': content_type,
                    'Cache-Control': 'public, max-age=31536000',  # 1 year
                    'ETag': f'"{content_hash}"'
                }
            else:
                # Non-versioned files should not be cached
                headers = {
                    'Content-Type': content_type,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            
            return web.Response(body=content, headers=headers)
        else:
            return web.Response(status=404, text="File not found")
    
    # Маршрут для статических файлов с умным контролем кеширования
    app.router.add_get(r'/bot-app/{filename:.+\.(css|js|png|jpg|jpeg|svg|ico)}', serve_static_with_cache_control)
    


    # 5. Маршрут-заглушка для любых других путей внутри /bot-app/, которые не являются статическими файлами или API
    # Исключаем /api/ из перехвата, чтобы API эндпоинты работали корректно
    async def serve_app_page_fallback(request):
        path = request.match_info.get('tail', '')
        # Если это API путь, возвращаем 404
        if path.startswith('api/'):
            return web.Response(status=404, text="API endpoint not found")
        # Иначе показываем главную страницу
        return await serve_main_app_page(request)
    
    app.router.add_get('/bot-app/{tail:.*}', serve_app_page_fallback)

    # 6. Security.txt endpoint
    async def serve_security_txt(request):
        """Serve security.txt file."""
        security_txt_path = os.path.join(BASE_DIR, '.well-known', 'security.txt')
        if os.path.exists(security_txt_path):
            return web.FileResponse(security_txt_path, headers={'Content-Type': 'text/plain'})
        else:
            return web.Response(status=404, text="Security policy not found")

    app.router.add_get('/.well-known/security.txt', serve_security_txt)


        # Настройка CORS для разрешения запросов с вашего домена Web App
    cors = aiohttp_cors.setup(app, defaults={
            "*" : aiohttp_cors.ResourceOptions(
                allow_credentials=False,  # Disabled for security
                expose_headers=["Content-Type", "Cache-Control", "ETag"],
                allow_headers=["Content-Type", "Accept", "Origin"],
                allow_methods=["GET", "POST", "PUT", "DELETE"]
            )
        })

    # Применяем CORS ко всем маршрутам
    for route in list(app.router.routes()):
        cors.add(route)

    runner = web.AppRunner(app)
    await runner.setup()

    return runner

if __name__ == '__main__':
    import asyncio
    async def main_api():
        runner = await setup_api_server()
        site = web.TCPSite(runner, '0.0.0.0', 8080)  # nosec B104 - Web server needs to bind to all interfaces
        await site.start()
        # Keep the server running indefinitely
        await asyncio.Event().wait() 

    asyncio.run(main_api())