import asyncio
import logging
import json
import os
import re
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove, ReplyKeyboardMarkup, 
    KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiohttp import web  # Импортируем web для TCPSite

from .api_server import setup_api_server  # Убедитесь, что импортируется setup_api_server
from .config import (
    BOT_TOKEN, BASE_WEBAPP_URL, ADMIN_CHAT_ID, ADMIN_EMAIL
)  # ИЗМЕНЕНИЕ: Импортируем ADMIN_CHAT_ID и ADMIN_EMAIL
from .keyboards import generate_main_menu


# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Константы и пути к файлам
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DATA_FILE = os.path.join(BASE_DIR, 'data', 'products_scraped.json')
ORDER_COUNTER_FILE = os.path.join(BASE_DIR, 'data', 'order_counter.json')  # ИЗМЕНЕНИЕ: Путь к файлу счетчика

logger.info(f"Ожидаемый путь к файлу данных: {PRODUCTS_DATA_FILE}")
logger.info(f"Ожидаемый путь к файлу счетчика: {ORDER_COUNTER_FILE}")


# Глобальные переменные
products_data = {}
order_counter = 0
last_reset_month = 0
# ИЗМЕНЕНИЕ: Создаем Lock для безопасной работы с файлом счетчика
order_counter_lock = asyncio.Lock()


# Словари для маппинга
CATEGORY_MAP = {
    "🥨 Выпечка": "category_bakery",
    "🥐 Круассаны": "category_croissants",
    "🍞 Ремесленный хлеб": "category_artisan_bread",
    "🍰 Десерты": "category_desserts"
}

DELIVERY_MAP = {
    'courier': 'Доставка курьером',
    'pickup': 'Самовывоз'
}


# Словарь для хранения корзин пользователей
user_carts = {}  # user_id: {product_id: quantity, ...}


# Функции для загрузки данных
async def load_products_data():
    """Загружает данные о продуктах из JSON-файла."""
    global products_data
    if os.path.exists(PRODUCTS_DATA_FILE):
        try:
            with open(PRODUCTS_DATA_FILE, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            logger.info(f"Данные о продуктах успешно загружены из {PRODUCTS_DATA_FILE}. "
                       f"Найдено категорий: {len(products_data)}")
            for category, products in products_data.items():
                logger.info(f"Категория '{category}': найдено {len(products)} продуктов.")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при чтении JSON-файла '{PRODUCTS_DATA_FILE}': {e}")
            products_data = {}  # Сброс данных, если файл поврежден
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке данных о продуктах: {e}")
            products_data = {}
    else:
        logger.warning(f"Файл '{PRODUCTS_DATA_FILE}' не найден. "
                      f"Бот не сможет отдавать данные о продуктах.")
        products_data = {}


# ИЗМЕНЕНИЕ: Новая функция для загрузки счетчика заказов из файла
async def load_order_counter():
    """Загружает счетчик заказов из файла."""
    global order_counter, last_reset_month
    async with order_counter_lock:
        if os.path.exists(ORDER_COUNTER_FILE):
            try:
                with open(ORDER_COUNTER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    order_counter = data.get('counter', 0)
                    last_reset_month = data.get('month', datetime.datetime.now().month)
                logger.info(f"Счетчик заказов успешно загружен из {ORDER_COUNTER_FILE}: "
                           f"{order_counter}, Месяц: {last_reset_month}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Файл счетчика заказов не найден или поврежден: {e}. "
                              f"Начинаем с 0.")
                order_counter = 0
                last_reset_month = datetime.datetime.now().month
            except Exception as e:
                logger.error(f"Неизвестная ошибка при загрузке счетчика заказов: {e}")
                order_counter = 0
                last_reset_month = datetime.datetime.now().month
        else:
            logger.warning(f"Файл счетчика {ORDER_COUNTER_FILE} не найден. Начинаем с 0.")
            order_counter = 0
            last_reset_month = datetime.datetime.now().month


# ИЗМЕНЕНИЕ: Новая функция для сохранения счетчика заказов в файл
async def save_order_counter(counter_data):
    """Сохраняет счетчик заказов в файл."""
    async with order_counter_lock:
        try:
            with open(ORDER_COUNTER_FILE, 'w', encoding='utf-8') as f:
                json.dump(counter_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении счетчика заказов: {e}")


# ИЗМЕНЕНИЕ: Функция generate_order_number теперь асинхронная и работает с файлом
async def generate_order_number():
    """
    Генерирует уникальный номер заказа, сохраняя счетчик в файле.
    """
    global order_counter, last_reset_month

    try:
        now = datetime.datetime.now()
        current_month = now.month
        logger.info(f"Начинаем генерацию номера заказа. Текущий месяц: {current_month}, "
                   f"последний сброс: {last_reset_month}, счетчик: {order_counter}")

        # Защита от одновременной записи
        async with order_counter_lock:
            # Проверяем, если месяц сменился
            if current_month != last_reset_month:
                logger.info(f"Сменился месяц. Сбрасываем счетчик заказов с {order_counter} на 0.")
                order_counter = 0
                last_reset_month = current_month

            # Увеличиваем счетчик для нового заказа
            order_counter += 1
            logger.info(f"Счетчик увеличен до: {order_counter}")

            # Сохраняем обновленный счетчик в файл
            try:
                await save_order_counter({'counter': order_counter, 'month': last_reset_month})
                logger.info(f"Счетчик успешно сохранен в файл: {order_counter}")
            except Exception as save_error:
                logger.error(f"Ошибка при сохранении счетчика: {save_error}")
                # Продолжаем выполнение даже если не удалось сохранить

        # Форматируем дату и счетчик
        day = now.strftime("%d")
        month = now.strftime("%m")

        # Форматируем счетчик до трех знаков
        order_sequence = str(order_counter).zfill(3)
        order_number = f"#{day}{month}/{order_sequence}"
        
        logger.info(f"Сгенерирован номер заказа: {order_number}")
        return order_number
        
    except Exception as e:
        logger.error(f"Критическая ошибка при генерации номера заказа: {e}")
        # Возвращаем номер заказа с временной меткой как fallback
        fallback_number = f"#ERROR_{int(now.timestamp())}"
        logger.warning(f"Используем fallback номер заказа: {fallback_number}")
        return fallback_number


# Утилиты для форматирования
def format_phone_telegram(phone: str) -> str:
    """
    Преобразует белорусский номер в формат +37544746-01-99 для Telegram.
    Если номер не белорусский (не начинается с 375), возвращает как введено.
    """
    digits = re.sub(r'\D', '', phone)

    if digits.startswith('375') and len(digits) == 12:
        return f"+{digits[0:3]}{digits[3:5]}{digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    return phone


# Функции для работы с корзиной
def get_user_cart(user_id: int) -> dict:
    """Получает корзину пользователя."""
    return user_carts.setdefault(user_id, {})


def update_cart_item_quantity(user_id: int, product_id: str, quantity: int):
    """Обновляет количество товаров в корзине."""
    cart = get_user_cart(user_id)
    if quantity <= 0:
        if product_id in cart:
            del cart[product_id]
    else:
        cart[product_id] = quantity
    logger.info(f"Корзина пользователя {user_id} обновлена: {cart}")


def clear_user_cart(user_id: int):
    """Очищает корзину пользователя."""
    if user_id in user_carts:
        del user_carts[user_id]
    logger.info(f"Корзина пользователя {user_id} очищена.")


# ЗАГЛУШКА: Функция для очистки сообщений корзины (если она нужна)
# Если у тебя есть конкретная реализация этой функции, замени ее.
async def clear_user_cart_messages(chat_id: int):
    """Очищает сообщения корзины (заглушка)."""
    logger.info(f"Функция clear_user_cart_messages вызвана для чата {chat_id}. (ЗАГЛУШКА)")
    # Здесь может быть логика удаления предыдущих сообщений корбины
    pass


# ИЗМЕНЕНИЕ: Новая асинхронная функция для отправки email
async def send_email_notification(recipient_email: str, subject: str, body: str):
    """Отправляет email уведомление."""
    try:
        logger.info(f"Начинаем отправку email на {recipient_email}")
        
        sender_email = ADMIN_EMAIL  # Email отправителя из переменных окружения
        sender_password = os.environ.get("ADMIN_EMAIL_PASSWORD")  # Пароль отправителя из переменных окружения
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")  # SMTP сервер (по умолчанию Gmail)
        smtp_port = int(os.environ.get("SMTP_PORT", 587))  # Порт SMTP (по умолчанию для TLS)

        if not sender_email or not sender_password:
            logger.error("Переменные окружения ADMIN_EMAIL или ADMIN_EMAIL_PASSWORD не установлены. "
                        "Email не будет отправлен.")
            return

        logger.info(f"Настройки SMTP: сервер={smtp_server}, порт={smtp_port}, отправитель={sender_email}")

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        logger.info("Подключаемся к SMTP серверу...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info("Запускаем TLS...")
            server.starttls()  # Начать TLS шифрование
            logger.info("Авторизуемся на сервере...")
            server.login(sender_email, sender_password)
            logger.info("Отправляем сообщение...")
            server.send_message(msg)
            
        logger.info(f"Email успешно отправлен на {recipient_email} с темой '{subject}'.")
        
    except smtplib.SMTPException as e:
        logger.error(f"Ошибка SMTP при отправке email: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке email на {recipient_email}: {e}")


# Хендлеры команд и сообщений
@dp.message(F.text == "/start")
async def command_start_handler(message: Message) -> None:
    """Обработчик команды /start."""
    user_id = message.from_user.id
    cart_count = sum(get_user_cart(user_id).values())
    await message.answer(
        "Привет! Я бот-помощник пекарни Дражина. Используй меню ниже, "
        "чтобы выбрать категорию товаров или узнать информацию о нас.",
        reply_markup=generate_main_menu(cart_count)
    )


@dp.message(F.text == "ℹ️ О нас")
async def about_us(message: Message):
    """Обработчик кнопки 'О нас'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = (
        "<b>О пекарне Дражина</b>\n\n"
        "Наша пекарня — это место, где традиции встречаются с современными технологиями. "
        "Мы готовим хлеб и выпечку по классическим рецептам, используя только натуральные ингредиенты.\n\n"
        "🌾 Ремесленный подход\n"
        "🍞 Свежайшие продукты\n"
        "❤️ Любовь к своему делу\n\n"
        "Подробнее: https://drazhin.by/o-pekarne"
    )
    await message.answer(
        text, 
        parse_mode=ParseMode.HTML, 
        reply_markup=generate_main_menu(sum(get_user_cart(message.from_user.id).values()))
    )


@dp.message(F.text == "📍 Наши адреса")
async def show_addresses(message: Message):
    """Обработчик кнопки 'Наши адреса'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = (
        "<b>📍 Наши магазины</b>\n\n"
        "🏬 <b>ТЦ \"Green City\"</b>\n"
        "ул. Притыцкого, 156, напротив Грин Сити\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEUl9'>Yandex</a>\n\n"

        "🏬 <b>ТЦ \"Замок\"</b>\n"
        "пр‑т Победителей, 65, 1 этаж возле «Ив Роше»\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEJ3Z'>Yandex</a>\n\n"

        "🏠 <b>ул. Л. Беды, 26</b>\n"
        "вход в WINE&SPIRITS\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEXnX'>Yandex</a>\n\n"

        "🏠 <b>ул. Мстиславца, 8</b>\n"
        "в Маяк Минска, вход со двора\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIIYme'>Yandex</a>\n\n"

        "🏠 <b>ул. Лученка, 1</b>\n"
        "в ЖК «Minsk World»\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIII6lt'>Yandex</a>\n\n"

        "🏠 <b>ул. Авиационная, 8</b>\n"
        "Копище, Новая Боровая\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIIDl~'>Yandex</a>\n\n"

        "🏠 <b>ул. Нововиленская, 45</b>\n"
        "Minsk\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIIDl~'>Yandex</a>\n\n"

        "🏠 <b>ул. Морской риф 1/4</b>\n"
        "а/г Ратомка, ЖК «Пирс»\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIMRKA'>Yandex</a>\n\n"

        "🏠 <b>г. Заславль, ул. Вокзальная, 11</b>\n"
        "у ж/д станции «Беларусь»\n"
        "🔗 <a href='http://maps.google.com/maps?q=53.9006,27.5670'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIMOpa'>Yandex</a>\n\n"

        "<b>📞 Наши контакты:</b>\n"
        " +375 (29) 117‑25‑77\n"
        "📧 info@drazhin.by\n"
        "<a href='https://drazhin.by/kontakty'>Подробнее на сайте</a>"
    )
    await message.answer(
        text, 
        reply_markup=generate_main_menu(sum(get_user_cart(message.from_user.id).values())),
        disable_web_page_preview=True, 
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text == "⚡ О доставке")
async def delivery_info(message: Message):
    """Обработчик кнопки 'О доставке'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = (
        "<b>🚚 Условия доставки</b>\n\n"
        "✅ Бесплатная доставка.\n"
        "❗️Минимальная сумма заказа для осуществления доставки — <b>70 рублей</b>.\n"
        "🔴 Минимальная сумма заказа для доставки в праздничные и предпраздничные дни — <b>200 рублей</b>.\n\n"
        "<b>🕒 Время доставки</b>\n"
        "Мы доставляем заказы ежедневно с <b>12:30 до 17:00</b>.\n"
        "<b>День в день</b>. Доставим товары день в день при оформлении заказа <b>до 11:00</b>.\n"
        "<b>На завтра</b>. Заказы, оформленные <b>после 11:00</b>, доставляются на следующий день.\n"
        "<b>🗺 Зона доставки</b>\n\n"
        "<a href=\"https://yandex.com/maps/157/minsk/?from=mapframe&ll=27.513432%2C53.935659&mode=usermaps&source=mapframe&um=constructor%3Acaf348232a3eb659f0e8355c6c34c51b8307a553b53ad5723ecfdb4ff43ad6da&utm_source=mapframe&z=10.6\">📍 Посмотреть карту зоны доставки</a>\n\n"
        "<b>📞 Контакты для уточнений</b>\n"
        "Телефон: +375 (29) 117‑25‑77\n"
        "📧 info@drazhin.by\n"
        "<a href='https://drazhin.by/kontakty'>Подробнее на сайте</a>"
    )
    await message.answer(
        text, 
        reply_markup=generate_main_menu(sum(get_user_cart(message.from_user.id).values())),
        disable_web_page_preview=True, 
        parse_mode=ParseMode.HTML
    )


@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Обработчик данных из Web App."""
    user_id = message.from_user.id
    web_app_data_raw = message.web_app_data.data
    logger.info(f"Получены данные из Web App для пользователя {user_id}: {web_app_data_raw}")

    try:
        data = json.loads(web_app_data_raw)
        action = data.get('action')
        logger.info(f"Действие Web App: {action}")

        if action == 'update_cart':
            await _handle_update_cart(message, data, user_id)
        elif action == 'checkout_order':
            await _handle_checkout_order(message, data, user_id)
        else:
            await message.answer(
                "Неизвестное действие из Web App.", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            logger.warning(f"Получено неизвестное действие из Web App для пользователя {user_id}: {action}")

    except json.JSONDecodeError:
        logger.error(f"Неверный формат JSON данных из Web App для пользователя {user_id}: {web_app_data_raw}")
        await message.answer(
            "Ошибка обработки данных из Web App. Пожалуйста, попробуйте снова.", 
            reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
        )
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке данных из Web App для пользователя {user_id}: {e}")
        await message.answer(
            "Произошла внутренняя ошибка. Пожалуйста, попробуйте позже.", 
            reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
        )


async def _handle_update_cart(message: Message, data: dict, user_id: int):
    """Обрабатывает обновление корзины из Web App."""
    cart_items = data.get('cart', [])
    current_cart = get_user_cart(user_id)

    # Очищаем корзину перед обновлением, чтобы избежать устаревших данных
    clear_user_cart(user_id)

    for item in cart_items:
        product_id = item.get('id')
        quantity = item.get('quantity')
        if product_id and quantity is not None:
            update_cart_item_quantity(user_id, product_id, quantity)

    cart_count = sum(get_user_cart(user_id).values())
    await message.answer(
        f"Корзина обновлена. Товаров в корзине: {cart_count}.",
        reply_markup=generate_main_menu(cart_count)
    )
    logger.info(f"Корзина пользователя {user_id} успешно обновлена из Web App. "
               f"Текущая корзина: {get_user_cart(user_id)}")


async def _handle_checkout_order(message: Message, data: dict, user_id: int):
    """Обрабатывает оформление заказа из Web App."""
    try:
        logger.info(f"Начинаем обработку заказа для пользователя {user_id}")
        
        order_details = data.get('order_details')
        cart_items = data.get('cart_items')
        total_amount = data.get('total_amount')

        # ИЗМЕНЕНИЕ: Более детальная проверка данных заказа
        if not order_details or not cart_items or total_amount is None:
            logger.error(f"Неполные данные заказа от пользователя {user_id}. "
                        f"order_details: {order_details}, cart_items: {cart_items}, "
                        f"total_amount: {total_amount}")
            await message.answer(
                "Ошибка при оформлении заказа. Пожалуйста, попробуйте снова.", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            return

        logger.info(f"Данные заказа валидны. Генерируем номер заказа...")
        order_number = await generate_order_number()
        logger.info(f"Номер заказа сгенерирован: {order_number}")

        # Отправляем уведомления
        logger.info("Начинаем отправку уведомлений...")
        try:
            await _send_order_notifications(order_details, cart_items, total_amount, order_number, user_id)
            logger.info("Уведомления отправлены успешно")
        except Exception as notification_error:
            logger.error(f"Ошибка при отправке уведомлений: {notification_error}")
            # Продолжаем выполнение даже если уведомления не отправились

        # Очищаем корзину после успешного заказа
        logger.info(f"Очищаем корзину пользователя {user_id}")
        clear_user_cart(user_id)
        logger.info(f"Корзина пользователя {user_id} очищена после оформления заказа {order_number}.")

        await message.answer(
            f"Спасибо за ваш заказ! Мы свяжемся с вами в ближайшее время для подтверждения.\n"
            f"<b>Ваш номер заказа:</b> <code>{order_number}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
        )
        logger.info(f"Ответ пользователю {user_id} отправлен успешно")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке заказа для пользователя {user_id}: {e}")
        await message.answer(
            "Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте позже или свяжитесь с нами.", 
            reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
        )


async def _send_order_notifications(order_details: dict, cart_items: list, 
                                  total_amount: float, order_number: str, user_id: int):
    """Отправляет уведомления о новом заказе."""
    try:
        logger.info(f"Начинаем формирование уведомлений для заказа {order_number}")
        
        delivery_method = order_details.get('deliveryMethod', 'N/A')
        delivery_text = DELIVERY_MAP.get(order_details.get('deliveryMethod'), 'N/A')
        phone_number = order_details.get('phone', 'N/A')
        formatted_phone = format_phone_telegram(phone_number)

        # Формируем сообщение для Telegram
        logger.info("Формируем сообщение для Telegram...")
        telegram_order_summary = _format_telegram_order_summary(
            order_number, order_details, cart_items, total_amount, 
            formatted_phone, delivery_text
        )
        logger.info("Сообщение для Telegram сформировано")

        # ИЗМЕНЕНИЕ: Отправка сообщения администратору в Telegram
        if ADMIN_CHAT_ID:
            try:
                logger.info(f"Отправляем сообщение администратору в Telegram. Chat ID: {ADMIN_CHAT_ID}")
                await bot.send_message(
                    chat_id=int(ADMIN_CHAT_ID),
                    text=telegram_order_summary,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Заказ {order_number} от пользователя {user_id} "
                           f"успешно отправлен администратору в Telegram.")
            except Exception as e:
                logger.error(f"Ошибка при отправке заказа {order_number} "
                            f"администратору в Telegram. ID чата: {ADMIN_CHAT_ID}. Ошибка: {e}")
        else:
            logger.warning("ADMIN_CHAT_ID не установлен. "
                          "Заказ не будет отправлен администратору в Telegram.")

        # ИЗМЕНЕНИЕ: Формируем тело email и отправляем его
        logger.info("Формируем email уведомление...")
        email_subject = (f"Новый заказ {order_number} от "
                        f"{order_details.get('firstName', '')} {order_details.get('lastName', '')} - "
                        f"{total_amount:.2f} р.")
        email_body = _format_email_body(order_number, order_details, cart_items, 
                                       total_amount, delivery_text)
        logger.info("Email уведомление сформировано")

        if ADMIN_EMAIL:
            admin_email_password = os.environ.get("ADMIN_EMAIL_PASSWORD")
            if admin_email_password:
                logger.info(f"Отправляем email уведомление на {ADMIN_EMAIL}")
                # Запускаем отправку email в фоновом режиме
                asyncio.create_task(send_email_notification(ADMIN_EMAIL, email_subject, email_body))
                logger.info("Задача отправки email создана")
            else:
                logger.error("Переменная окружения ADMIN_EMAIL_PASSWORD не установлена. "
                            "Email уведомление не будет отправлено.")
        else:
            logger.warning("ADMIN_EMAIL не установлен. Email уведомление не будет отправлено.")
            
        logger.info(f"Все уведомления для заказа {order_number} обработаны")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке уведомлений для заказа {order_number}: {e}")
        raise  # Перебрасываем ошибку выше


def _format_telegram_order_summary(order_number: str, order_details: dict, 
                                  cart_items: list, total_amount: float,
                                  formatted_phone: str, delivery_text: str) -> str:
    """Форматирует сводку заказа для Telegram."""
    summary = (f"*НОВЫЙ ЗАКАЗ {order_number}*\n\n"
               f"*Покупатель:*\n"
               f"Фамилия: `{order_details.get('lastName', 'N/A')}`\n"
               f"Имя: `{order_details.get('firstName', 'N/A')}`\n"
               f"Отчество: `{order_details.get('middleName', 'N/A')}`\n"
               f"Телефон: `{formatted_phone}`\n"
               f"Email: `{order_details.get('email', 'N/A')}`\n"
               f"Дата доставки/самовывоза: `{order_details.get('deliveryDate', 'N/A')}`\n\n")

    summary += f"*Данные о доставке:* \n"
    if order_details.get('deliveryMethod') == 'courier':
        summary += (f"Способ получения: {delivery_text}\n"
                   f"Город: `{order_details.get('city', 'N/A')}`\n"
                   f"Адрес: `{order_details.get('addressLine', 'N/A')}`\n")
        if order_details.get('comment'):
            summary += f"Комментарий к доставке: `{order_details.get('comment', 'N/A')}`\n"
    elif order_details.get('deliveryMethod') == 'pickup':
        summary += (f"Способ получения: {delivery_text}\n"
                   f"Адрес самовывоза: `{order_details.get('pickupAddress', 'N/A')}`\n")

    summary += f"\n*Состав заказа:*\n"
    for item in cart_items:
        price_float = float(item.get('price', 0))
        total_item_float = (float(item.get('total', 0)) if item.get('total') is not None 
                           else (price_float * item.get('quantity', 0)))
        summary += (f"- `{item.get('name', 'N/A')}` x `{item.get('quantity', 0)}` шт. "
                   f"(`{price_float:.2f}` р. / шт.) = `{total_item_float:.2f}` р.\n")

    summary += f"\n*Общая сумма заказа:* `{total_amount:.2f}` р."
    return summary


def _format_email_body(order_number: str, order_details: dict, cart_items: list,
                      total_amount: float, delivery_text: str) -> str:
    """Форматирует тело письма для email уведомления."""
    # Формируем строки для условной вставки в HTML
    courier_city = ("<p><b>Город:</b> " + order_details.get('city', 'N/A') + "</p>" 
                   if order_details.get('deliveryMethod') == 'courier' else "")
    courier_address = ("<p><b>Адрес:</b> " + order_details.get('addressLine', 'N/A') + "</p>" 
                      if order_details.get('deliveryMethod') == 'courier' else "")
    courier_comment = ("<p><b>Комментарий к доставке:</b> " + order_details.get('comment', 'N/A') + "</p>" 
                      if (order_details.get('deliveryMethod') == 'courier' and order_details.get('comment')) else "")
    pickup_address = ("<p><b>Адрес самовывоза:</b> " + order_details.get('pickupAddress', 'N/A') + "</p>" 
                     if order_details.get('deliveryMethod') == 'pickup' else "")

    # Формируем строки таблицы для товаров
    table_rows = ""
    for item in cart_items:
        total_item = (float(item.get('total', 0)) if item.get('total') is not None 
                     else (float(item.get('price', 0)) * item.get('quantity', 0)))
        table_rows += f"""
                                                <tr>
                                                    <td>{item.get('name', 'N/A')}</td>
                                                    <td>{item.get('quantity', 0)} шт.</td>
                                                    <td>{float(item.get('price', 0)):.2f} р.</td>
                                                    <td>{total_item:.2f} р.</td>
                                                </tr>
                                                """

    email_body = f"""
                    <html>
                    <head></head>
                    <body>
                        <h2>Новый заказ {order_number}</h2>
                        <h3>Покупатель:</h3>
                        <ul>
                            <li><b>Фамилия:</b> {order_details.get('lastName', 'N/A')}</li>
                            <li><b>Имя:</b> {order_details.get('firstName', 'N/A')}</li>
                            <li><b>Отчество:</b> {order_details.get('middleName', 'N/A')}</li>
                            <li><b>Телефон:</b> {order_details.get('phone', 'N/A')}</li>
                            <li><b>Email:</b> {order_details.get('email', 'N/A')}</li>
                            <li><b>Дата доставки/самовывоза:</b> {order_details.get('deliveryDate', 'N/A')}</li>
                        </ul>
                        <h3>Способ получения: {delivery_text}</h3>
                        {courier_city}
                        {courier_address}
                        {courier_comment}
                        {pickup_address}

                        <h3>🛍️ Состав заказа:</h3>
                        <table border="1" cellpadding="5" cellspacing="0" style="width:100%; border-collapse: collapse;">
                            <thead>
                                <tr>
                                    <th>Название</th>
                                    <th>Кол-во</th>
                                    <th>Цена за шт.</th>
                                    <th>Всего</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                        <h3>Общая сумма заказа: {total_amount:.2f} р.</h3>
                    </body>
                    </html>
                    """
    return email_body


@dp.message(F.text)
async def block_text_input(message: Message):
    """Блокирует текстовый ввод, если он не является командой или кнопкой."""
    allowed_texts = list(CATEGORY_MAP.keys()) + [
        "ℹ️ О нас", "📍 Наши адреса", "⚡ О доставке", "/start"
    ]
    
    if (message.text not in allowed_texts and 
        not re.match(r"🛒 Проверить корзину(\s\(\d+\))?", message.text)):
        await message.answer("⚠️ Пожалуйста, используйте кнопки внизу для управления ботом 👇")


async def main():
    """Главная функция для запуска бота."""
    logger.info("Загрузка данных о продуктах при запуске бота...")
    await load_products_data()
    # Загружаем счетчик заказов
    await load_order_counter()

    # Включение хендлера для Web App данных
    dp.message.register(handle_web_app_data, F.web_app_data)

    # Настраиваем API сервер
    runner = await setup_api_server()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)

    web_server_task = asyncio.create_task(site.start())
    bot_polling_task = asyncio.create_task(dp.start_polling(bot))

    logger.info(f"API сервер запущен на http://0.0.0.0:{port}")
    logger.info("Бот начал опрос...")

    try:
        await asyncio.gather(bot_polling_task, web_server_task)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Остановка API сервера...")
        await runner.cleanup()
        logger.info("API сервер остановлен.")
        logger.info("Закрытие сессии бота...")
        await bot.session.close()
        logger.info("Сессия бота закрыта.")


if __name__ == "__main__":
    asyncio.run(main())