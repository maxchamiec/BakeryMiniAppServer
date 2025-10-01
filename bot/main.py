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
from aiohttp import web, ClientSession, TCPConnector  # Импортируем web для TCPSite

from bot.api_server import setup_api_server  # ИЗМЕНЕНО: Абсолютный импорт
from bot.config import (
    BOT_TOKEN, BASE_WEBAPP_URL, ADMIN_CHAT_ID, ADMIN_EMAIL, config
)  # ИЗМЕНЕНО: Абсолютный импорт
from bot.keyboards import generate_main_menu  # ИЗМЕНЕНО: Абсолютный импорт
from bot.security_manager import security_manager  # ИЗМЕНЕНО: Добавлен импорт security manager
from bot.security_middleware import security_middleware, fsm_context_middleware  # ИЗМЕНЕНО: Добавлен импорт security middleware


# Настраиваем логирование
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Инициализация бота и диспетчера
# Бот будет инициализирован в функции main() с IPv4 сессией
bot = None
dp = Dispatcher()

# Регистрируем security middleware
dp.message.middleware(security_middleware)
dp.callback_query.middleware(security_middleware)
dp.message.middleware(fsm_context_middleware)
dp.callback_query.middleware(fsm_context_middleware)


# Константы и пути к файлам
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DATA_FILE = os.path.join(BASE_DIR, 'data', 'products_scraped.json')
ORDER_COUNTER_FILE = os.path.join(BASE_DIR, 'data', 'order_counter.json')  # ИЗМЕНЕНИЕ: Путь к файлу счетчика



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
                    content = f.read().strip()
                    if not content:  # Проверяем, не пустой ли файл
                        logger.warning(f"Файл счетчика заказов {ORDER_COUNTER_FILE} пустой. "
                                      f"Создаем новый с начальными значениями.")
                        order_counter = 0
                        last_reset_month = datetime.datetime.now().month
                        # Создаем новый файл с правильной структурой
                        await save_order_counter({'counter': order_counter, 'month': last_reset_month})
                    else:
                        data = json.loads(content)
                        order_counter = data.get('counter', 0)
                        last_reset_month = data.get('month', datetime.datetime.now().month)

                        # Проверяем, если месяц в файле отличается от текущего
                        current_month = datetime.datetime.now().month
                        if last_reset_month != current_month:
                            logger.info(f"Месяц в файле ({last_reset_month}) отличается от текущего ({current_month}). "
                                      f"Счетчик будет сброшен при первом заказе в новом месяце.")
                            # НЕ сбрасываем счетчик здесь - только при генерации заказа
                            # last_reset_month остается старым до первого заказа
                            # Это позволяет сохранить последний счетчик предыдущего месяца

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Файл счетчика заказов не найден или поврежден: {e}. "
                              f"Начинаем с 0.")
                order_counter = 0
                last_reset_month = datetime.datetime.now().month
                # Создаем новый файл с правильной структурой
                await save_order_counter({'counter': order_counter, 'month': last_reset_month})
            except Exception as e:
                logger.error(f"Неизвестная ошибка при загрузке счетчика заказов: {e}")
                order_counter = 0
                last_reset_month = datetime.datetime.now().month
                # Создаем новый файл с правильной структурой
                await save_order_counter({'counter': order_counter, 'month': last_reset_month})
        else:
            logger.warning(f"Файл счетчика {ORDER_COUNTER_FILE} не найден. Создаем новый.")
            order_counter = 0
            last_reset_month = datetime.datetime.now().month
            # Создаем новый файл с правильной структурой
            await save_order_counter({'counter': order_counter, 'month': last_reset_month})


# ИЗМЕНЕНИЕ: Новая функция для сохранения счетчика заказов в файл
async def save_order_counter(counter_data):
    """Сохраняет счетчик заказов в файл."""
    try:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(ORDER_COUNTER_FILE), exist_ok=True)

        # Используем синхронную операцию записи в файл
        with open(ORDER_COUNTER_FILE, 'w', encoding='utf-8') as f:
            json.dump(counter_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Счетчик заказов успешно сохранен: {counter_data}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении счетчика заказов: {e}")
        raise  # Перебрасываем ошибку, чтобы вызывающий код мог ее обработать


# ИЗМЕНЕНИЕ: Функция generate_order_number теперь асинхронная и работает с файлом
async def generate_order_number():
    """
    Генерирует уникальный номер заказа, сохраняя счетчик в файле.
    """
    global order_counter, last_reset_month

    try:
        now = datetime.datetime.now()
        current_month = now.month

        # Защита от одновременной записи
        async with order_counter_lock:
            # Проверяем, если месяц сменился
            if current_month != last_reset_month:
                order_counter = 0
                last_reset_month = current_month
                # Сохраняем обновленный счетчик с новым месяцем
                try:
                    await save_order_counter({'counter': order_counter, 'month': last_reset_month})
                except Exception as e:
                    logger.error(f"Ошибка при сохранении сброшенного счетчика: {e}")

            # Увеличиваем счетчик для нового заказа
            order_counter += 1

            # Сохраняем обновленный счетчик в файл
            try:
                # Убираем таймаут - на Heroku операции могут быть медленными
                await save_order_counter({'counter': order_counter, 'month': last_reset_month})
            except Exception as save_error:
                logger.error(f"Ошибка при сохранении счетчика: {save_error}")
                logger.error(f"Тип ошибки: {type(save_error).__name__}")
                # Продолжаем выполнение даже при ошибке сохранения

        # Форматируем дату и счетчик
        day = now.strftime("%d")
        month = now.strftime("%m")
        year = now.strftime("%y")

        # Форматируем счетчик до трех знаков
        order_sequence = str(order_counter).zfill(3)
        order_number = f"#{day}{month}{year}/{order_sequence}"

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


def clear_user_cart(user_id: int):
    """Очищает корзину пользователя."""
    if user_id in user_carts:
        del user_carts[user_id]


# ЗАГЛУШКА: Функция для очистки сообщений корзины (если она нужна)
# Если у тебя есть конкретная реализация этой функции, замени ее.
async def clear_user_cart_messages(chat_id: int):
    """Очищает сообщения корзины (заглушка)."""
    # Здесь может быть логика удаления предыдущих сообщений корбины
    pass


# ИЗМЕНЕНИЕ: Новая асинхронная функция для отправки email
async def send_email_notification(recipient_email: str, subject: str, body: str, sender_name: str = "Пекарня Дражина"):
    """Отправляет email уведомление."""
    if not config.ENABLE_EMAIL_NOTIFICATIONS:
        return
    
    try:

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{sender_name} <{ADMIN_EMAIL}>"
        msg['To'] = recipient_email

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            server.login(ADMIN_EMAIL, config.ADMIN_EMAIL_PASSWORD)
            server.send_message(msg)

        
        # Log security event
        security_manager._log_security_event("email_sent", {
            "recipient": recipient_email,
            "subject": subject
        })

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Ошибка аутентификации SMTP: {e}")
        logger.error("Убедитесь, что ADMIN_EMAIL_PASSWORD установлен правильно")
        logger.error("Для Gmail используйте App Password, а не обычный пароль")
        
        # Log security event
        security_manager._log_security_event("email_auth_failure", {
            "recipient": recipient_email,
            "error": str(e)
        })
        
    except smtplib.SMTPException as e:
        logger.error(f"Ошибка SMTP при отправке email: {e}")
        
        # Log security event
        security_manager._log_security_event("email_smtp_error", {
            "recipient": recipient_email,
            "error": str(e)
        })
        
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке email на {recipient_email}: {e}")
        
        # Log security event
        security_manager._log_security_event("email_error", {
            "recipient": recipient_email,
            "error": str(e),
            "error_type": type(e).__name__
        })


# ===============================
# Helper builders (presentation-only, no logic changes)
# ===============================

def cart_item_count(user_id: int) -> int:
    """Calculate total number of items in the user's cart."""
    return sum(get_user_cart(user_id).values())


def reply_main_menu_for(user_id: int) -> InlineKeyboardMarkup:
    """Return inline main menu keyboard configured for a given user's current cart state."""
    return generate_main_menu(cart_item_count(user_id))


def build_about_message() -> str:
    """Static HTML for the About section."""
    return (
        "<b>О пекарне Дражина</b>\n\n"
        "Наша пекарня — это место, где традиции встречаются с современными технологиями. "
        "Мы готовим хлеб и выпечку по классическим рецептам, используя только натуральные ингредиенты.\n\n"
        "🌾 Ремесленный подход\n"
        "🍞 Свежайшие продукты\n"
        "❤️ Любовь к своему делу\n\n"
        "Подробнее: https://drazhin.by/o-pekarne"
    )


def build_addresses_message() -> str:
    """Static HTML for the Addresses section."""
    return (
        "<b>📍 Наши магазины</b>\n\n"
        "🏬 <b>ТЦ \"Green City\"</b>\n"
        "ул. Притыцкого, 156, напротив Грин Сити\n"
        "🔗 <a href='https://maps.app.goo.gl/5oDagDvDidFYfm2X7'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEUl9'>Yandex</a>\n\n"
        "🏬 <b>ТЦ \"Замок\"</b>\n"
        "пр‑т Победителей, 65, 1 этаж возле «Ив Роше»\n"
        "🔗 <a href='https://maps.app.goo.gl/qzEXBGMsrWdS8LQT6'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEJ3Z'>Yandex</a>\n\n"
        "🏠 <b>ул. Л. Беды, 26</b>\n"
        "вход в WINE&SPIRITS\n"
        "🔗 <a href='https://maps.app.goo.gl/oXs1TJdSs9pgQE9SA'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIEXnX'>Yandex</a>\n\n"
        "🏠 <b>ул. Мстиславца, 8</b>\n"
        "в Маяк Минска, вход со двора\n"
        "🔗 <a href='https://maps.app.goo.gl/bKcMpqMHLwz6h3TX7'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIIYme'>Yandex</a>\n\n"
        "🏠 <b>ул. Лученка, 1</b>\n"
        "в ЖК «Минск Мир»\n"
        "🔗 <a href='https://maps.app.goo.gl/TmUrt73oDBWLXbK97'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHt1eOjv'>Yandex</a>\n\n"
        "🏠 <b>ул. Авиационная, 8</b>\n"
        "Копище, Новая Боровая\n"
        "🔗 <a href='https://maps.app.goo.gl/myWiaKVe5iN8su96A'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIIDl~'>Yandex</a>\n\n"
        "🏠 <b>ул. Нововиленская, 45</b>\n"
        "г. Минск\n"
        "🔗 <a href='https://maps.app.goo.gl/XZpmmiSFnWdpiNsWA'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHt1iZ6v'>Yandex</a>\n\n"
        "🏠 <b>ул. Морской риф 1/4</b>\n"
        "а/г Ратомка, ЖК «Пирс»\n"
        "🔗 <a href='https://maps.app.goo.gl/ig3KWvXrmczHP93u5'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIMRKA'>Yandex</a>\n\n"
        "🏠 <b>г. Заславль, ул. Вокзальная, 11</b>\n"
        "у ж/д станции «Беларусь»\n"
        "🔗 <a href='https://maps.app.goo.gl/YAwtb8zFt3h3TjiPA'>Google</a> | "
        "<a href='https://yandex.com/maps/-/CHTIMOpa'>Yandex</a>\n\n"
        "<b>📞 Наши контакты:</b>\n"
        " +375 (29) 117‑25‑77\n"
        "📧 info@drazhin.by\n"
        "<a href='https://drazhin.by/kontakty'>Подробнее на сайте</a>"
    )


def build_delivery_message() -> str:
    """Static HTML for the Delivery section."""
    return (
        "<b>Условия доставки</b>\n\n"
        "✅ Бесплатная доставка.\n"
        "❗️Минимальная сумма заказа для осуществления доставки — <b>70 рублей</b>.\n"
        "❗️❗️ Минимальная сумма заказа для доставки в праздничные и предпраздничные дни — <b>200 рублей</b>.\n\n"
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


# ===============================
# Inline keyboard callback handlers
# ===============================

@dp.callback_query(F.data == "info:about")
async def cb_about(callback: CallbackQuery):
    try:
        await callback.answer("ℹ️ О нас", show_alert=False)
    except Exception as e:
        logger.warning(f"Failed to answer about callback: {e}")
    text = build_about_message()
    await callback.message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_main_menu_for(callback.from_user.id)
    )


@dp.callback_query(F.data == "info:addresses")
async def cb_addresses(callback: CallbackQuery):
    try:
        await callback.answer("📍 Адреса отправлены", show_alert=False)
    except Exception as e:
        logger.warning(f"Failed to answer callback: {e}")

    text = build_addresses_message()
    try:
        await callback.message.answer(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_main_menu_for(callback.from_user.id)
        )
    except Exception as e:
        logger.error(f"Failed to send addresses message: {e}")


@dp.callback_query(F.data == "info:delivery")
async def cb_delivery(callback: CallbackQuery):
    try:
        await callback.answer("🚚 Условия доставки", show_alert=False)
    except Exception as e:
        logger.warning(f"Failed to answer delivery callback: {e}")
    text = build_delivery_message()
    await callback.message.answer(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=reply_main_menu_for(callback.from_user.id)
    )


# ===============================
# Хендлеры команд и сообщений
# ===============================
@dp.message(F.text == "/start")
async def command_start_handler(message: Message) -> None:
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Я бот-помощник пекарни Дражина. Используй меню ниже, "
        "чтобы выбрать категорию товаров или узнать информацию о нас.",
        reply_markup=reply_main_menu_for(message.from_user.id)
    )


@dp.message(F.text == "/menu")
async def command_menu_handler(message: Message) -> None:
    """Обработчик команды /menu."""
    await message.answer(
        "🍞 Главное меню пекарни Дражина:",
        reply_markup=reply_main_menu_for(message.from_user.id)
    )


@dp.message(F.text == "О нас")
async def about_us(message: Message):
    """Обработчик кнопки 'О нас'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = build_about_message()
    await message.answer(
        text, 
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_main_menu_for(message.from_user.id)
    )


@dp.message(F.text == "Наши адреса")
async def show_addresses(message: Message):
    """Обработчик кнопки 'Наши адреса'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = build_addresses_message()
    await message.answer(
        text,
        reply_markup=reply_main_menu_for(message.from_user.id),
        disable_web_page_preview=True, 
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text == "О доставке")
async def delivery_info(message: Message):
    """Обработчик кнопки 'О доставке'."""
    await clear_user_cart_messages(message.chat.id)  # Очищаем корзину, если пользователь переходит в другой раздел
    text = build_delivery_message()
    await message.answer(
        text, 
        reply_markup=reply_main_menu_for(message.from_user.id),
        disable_web_page_preview=True, 
        parse_mode=ParseMode.HTML
    )


@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Обработчик данных из Web App."""
    user_id = message.from_user.id
    web_app_data_raw = message.web_app_data.data

    try:
        data = json.loads(web_app_data_raw)
        action = data.get('action')

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

        order_details = data.get('order_details')
        cart_items = data.get('cart_items')
        total_amount = data.get('total_amount')

        # ИЗМЕНЕНИЕ: Более детальная проверка данных заказа
        if not order_details or not cart_items:
            logger.error(f"Неполные данные заказа от пользователя {user_id}. "
                        f"order_details: {order_details}, cart_items: {cart_items}")
            await message.answer(
                "Ошибка при оформлении заказа. Пожалуйста, попробуйте снова.", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            return
            
        # Проверяем total_amount отдельно с более детальным логированием
        if total_amount is None:
            logger.error(f"total_amount is None для пользователя {user_id}. "
                        f"order_details: {order_details}, cart_items: {cart_items}")
            await message.answer(
                "❌ Ошибка валидации данных:\n• Field total_amount must be number, got NoneType", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            return

        # Проверяем, что корзина не пустая
        if len(cart_items) == 0:
            logger.warning(f"Попытка оформить заказ с пустой корзиной от пользователя {user_id}")
            await message.answer(
                "Корзина пуста. Пожалуйста, добавьте товары в корзину перед оформлением заказа.", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            return

        # Проверяем, что сумма заказа больше 0
        if total_amount <= 0:
            logger.warning(f"Попытка оформить заказ с нулевой суммой от пользователя {user_id}")
            await message.answer(
                "Сумма заказа должна быть больше нуля. Пожалуйста, добавьте товары в корзину.", 
                reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
            )
            return

        
        # Очищаем корзину ПЕРЕД обработкой заказа, чтобы избежать дублирования
        try:
            clear_user_cart(user_id)
        except Exception as e:
            logger.error(f"Ошибка при очистке корзины: {e}")
        
        if order_details.get('deliveryMethod') == 'pickup':
            pass
        elif order_details.get('deliveryMethod') == 'courier':
            pass

        order_number = await generate_order_number()

        # Отправляем уведомления
        try:
            await _send_order_notifications(order_details, cart_items, total_amount, order_number, user_id)
        except Exception as notification_error:
            logger.error(f"Ошибка при отправке уведомлений: {notification_error}")
            logger.error(f"Тип ошибки: {type(notification_error).__name__}")
            # Продолжаем выполнение даже если уведомления не отправились

        # Отправляем краткое подтверждение пользователю с timeout
        try:
            await asyncio.wait_for(
                message.answer(
                    f"✅ Заказ оформлен! Детали отправлены вам в личные сообщения.",
                    reply_markup=generate_main_menu(sum(get_user_cart(user_id).values()))
                ),
                timeout=10.0  # 10 секунд timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout при отправке ответа пользователю.")
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа пользователю: {e}")
            # Пытаемся отправить простой ответ без форматирования
            try:
                await asyncio.wait_for(
                    message.answer(f"Заказ {order_number} оформлен!"),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout при отправке простого ответа.")
            except Exception as e2:
                logger.error(f"Критическая ошибка при отправке ответа: {e2}")

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


        # Валидация входных данных
        if not order_details or not cart_items or total_amount is None:
            logger.error(f"Неверные данные для уведомлений: order_details={order_details}, cart_items={cart_items}, total_amount={total_amount}")
            return

        delivery_method = order_details.get('deliveryMethod', 'N/A')
        delivery_text = DELIVERY_MAP.get(order_details.get('deliveryMethod'), 'N/A')
        phone_number = order_details.get('phone', 'N/A')
        formatted_phone = format_phone_telegram(phone_number)

        # Формируем сообщение для Telegram
        try:
            telegram_order_summary = _format_telegram_order_summary(
                order_number, order_details, cart_items, total_amount, 
                formatted_phone, delivery_text, user_id
            )
        except Exception as e:
            logger.error(f"Ошибка при формировании сообщения для Telegram: {e}")
            # Создаем простое сообщение как fallback
            user_link_fallback = f"\n[💬 Написать клиенту](tg://user?id={user_id})" if user_id else ""
            telegram_order_summary = f"*НОВЫЙ ЗАКАЗ {order_number}*\n\nОшибка при формировании детального сообщения. Проверьте логи.{user_link_fallback}"

        # ИЗМЕНЕНИЕ: Отправка сообщения администратору в Telegram с timeout
        if ADMIN_CHAT_ID:
            try:
                await asyncio.wait_for(
                    bot.send_message(
                        chat_id=int(ADMIN_CHAT_ID),
                        text=telegram_order_summary,
                        parse_mode=ParseMode.MARKDOWN
                    ),
                    timeout=10.0  # 10 секунд timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout при отправке заказа {order_number} администратору в Telegram. ID чата: {ADMIN_CHAT_ID}.")
            except Exception as e:
                logger.error(f"Ошибка при отправке заказа {order_number} "
                            f"администратору в Telegram. ID чата: {ADMIN_CHAT_ID}. Ошибка: {e}")
        else:
            logger.warning("ADMIN_CHAT_ID не установлен. "
                          "Заказ не будет отправлен администратору в Telegram.")

        # ИЗМЕНЕНИЕ: Формируем тело email и отправляем его
        try:
            email_subject = (f"Новый заказ {order_number} от "
                            f"{order_details.get('firstName', '')} {order_details.get('lastName', '')} - "
                            f"{total_amount:.2f} р.")
            email_body = _format_email_body(order_number, order_details, cart_items, 
                                           total_amount, delivery_text)
        except Exception as e:
            logger.error(f"Ошибка при формировании email уведомления: {e}")
            # Создаем простое email как fallback
            email_subject = f"Новый заказ {order_number}"
            email_body = f"""
            <html>
            <body>
                <h2>Новый заказ {order_number}</h2>
                <p>Ошибка при формировании детального email. Проверьте логи.</p>
                <p>Покупатель: {order_details.get('firstName', 'N/A')} {order_details.get('lastName', 'N/A')}</p>
                <p>Сумма: {total_amount:.2f} р.</p>
            </body>
            </html>
            """

        if ADMIN_EMAIL:
            admin_email_password = os.environ.get("ADMIN_EMAIL_PASSWORD")
            if admin_email_password:
                # Отправляем email синхронно, чтобы дождаться результата
                try:
                    await send_email_notification(ADMIN_EMAIL, email_subject, email_body, "Пекарня Дражина")
                except Exception as e:
                    logger.error(f"Ошибка при отправке email администратору: {e}")
            else:
                logger.error("Переменная окружения ADMIN_EMAIL_PASSWORD не установлена. "
                            "Email уведомление не будет отправлено.")
        else:
            logger.warning("ADMIN_EMAIL не установлен. Email уведомление не будет отправлено.")

        # Отправляем подтверждение заказа клиенту в Telegram с timeout
        if user_id:
            try:
                customer_message = _format_customer_telegram_message(
                    order_number, order_details, cart_items, total_amount, delivery_text
                )
                await asyncio.wait_for(
                    bot.send_message(
                        chat_id=user_id,
                        text=customer_message,
                        parse_mode=ParseMode.MARKDOWN
                    ),
                    timeout=10.0  # 10 секунд timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout при отправке подтверждения заказа клиенту {user_id} в Telegram.")
            except Exception as e:
                logger.error(f"Ошибка при отправке подтверждения заказа клиенту {user_id} в Telegram: {e}")
        else:
            logger.warning("User ID не доступен. Подтверждение заказа в Telegram клиенту не будет отправлено.")

        # Отправляем письмо пользователю
        user_email = order_details.get('email')
        if user_email:
            try:
                user_email_subject = f"Вы сделали заказ {order_number} в Telegram боте Пекарни Дражина"
                user_email_body = _format_user_email_body(order_number, order_details, cart_items, total_amount)
                asyncio.create_task(send_email_notification(user_email, user_email_subject, user_email_body, "Пекарня Дражина"))
            except Exception as e:
                logger.error(f"Ошибка при отправке письма пользователю: {e}")
        else:
            logger.warning("Email пользователя не указан. Письмо пользователю не будет отправлено.")


    except Exception as e:
        logger.error(f"Критическая ошибка при отправке уведомлений для заказа {order_number}: {e}")
        logger.error(f"Детали ошибки: {type(e).__name__}: {str(e)}")
        # Не перебрасываем ошибку, чтобы не прерывать обработку заказа
        logger.warning("Продолжаем обработку заказа без уведомлений")


def _format_customer_telegram_message(order_number: str, order_details: dict, 
                                     cart_items: list, total_amount: float, delivery_text: str) -> str:
    """Форматирует сообщение с подтверждением заказа для клиента в Telegram."""
    
    # Формируем список товаров
    items_text = ""
    for item in cart_items:
        item_total = float(item['price']) * int(item['quantity'])
        items_text += f"• {item['name']} — {item['quantity']} шт. x {item['price']} р. = {item_total:.2f} р.\n"
    
    # Формируем информацию о доставке
    delivery_info = ""
    if order_details.get('deliveryMethod') == 'courier':
        delivery_info = f"""📍 *Адрес доставки:*
{order_details.get('city', 'N/A')}, {order_details.get('addressLine', 'N/A')}
📅 *Дата доставки:* {order_details.get('deliveryDate', 'N/A')}"""
        if order_details.get('comment'):
            delivery_info += f"\n💬 *Комментарий:* {order_details.get('comment')}"
    
    elif order_details.get('deliveryMethod') == 'pickup':
        pickup_address_id = order_details.get('pickupAddress')
        pickup_details = _get_pickup_details(pickup_address_id) if pickup_address_id else {"name": "N/A", "address": "N/A", "hours": "N/A"}
        
        delivery_info = f"""🏪 *Пункт самовывоза:* {pickup_details['name']}
📍 *Адрес самовывоза:* {pickup_details['address']}
🕐 *Время работы:* {pickup_details['hours']}
📅 *Дата самовывоза:* {order_details.get('deliveryDate', 'N/A')}"""
        if order_details.get('commentPickup'):
            delivery_info += f"\n💬 *Комментарий:* {order_details.get('commentPickup')}"
    
    # Формируем информацию о способе оплаты
    payment_method = order_details.get('paymentMethod', 'N/A')
    payment_text = ""
    if payment_method == 'cash':
        payment_text = "Оплата наличными при получении товара"
    elif payment_method == 'card':
        payment_text = "Оплата картой при получении товара"
    elif payment_method == 'erip':
        payment_text = "Онлайн оплата ЕРИП"
    else:
        payment_text = f"Способ оплаты: {payment_method}"
    
    message = f"""✅ *ЗАКАЗ ПОДТВЕРЖДЕН!*

🧾 *Номер заказа:* `{order_number}`

👤 *Ваши данные:*
{order_details.get('lastName', 'N/A')} {order_details.get('firstName', 'N/A')} {order_details.get('middleName', 'N/A')}
📞 Телефон: `{order_details.get('phone', 'N/A')}`
📧 Email: `{order_details.get('email', 'N/A')}`

🛒 *Ваш заказ:*
{items_text}
💰 *Общая сумма: {total_amount:.2f} р.*

🚚 *Способ получения:* {delivery_text}
{delivery_info}

💳 *Способ оплаты:* {payment_text}

📞 *Мы свяжемся с вами в ближайшее время для подтверждения заказа.*

Спасибо за ваш заказ! 🙏"""
    
    return message


def _format_telegram_order_summary(order_number: str, order_details: dict, 
                                  cart_items: list, total_amount: float,
                                  formatted_phone: str, delivery_text: str, user_id: int = None) -> str:
    """Форматирует сводку заказа для Telegram."""

    # Формируем кликабельную ссылку на пользователя, если user_id доступен
    user_link = ""
    if user_id:
        user_link = f"\n[💬 Написать клиенту](tg://user?id={user_id})"

    summary = (f"*НОВЫЙ ЗАКАЗ {order_number}*\n\n"
               f"*Покупатель:*\n"
               f"Фамилия: `{order_details.get('lastName', 'N/A')}`\n"
               f"Имя: `{order_details.get('firstName', 'N/A')}`\n"
               f"Отчество: `{order_details.get('middleName', 'N/A')}`\n"
               f"Телефон: [{formatted_phone}](tel:{formatted_phone}){user_link}\n"
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
        pickup_address_id = order_details.get('pickupAddress')
        pickup_details = _get_pickup_details(pickup_address_id) if pickup_address_id else {"name": "N/A", "address": "N/A", "hours": "N/A"}
        
        summary += (f"Способ получения: {delivery_text}\n"
                   f"Пункт самовывоза: `{pickup_details['name']}`\n"
                   f"Адрес самовывоза: `{pickup_details['address']}`\n"
                   f"Время работы: `{pickup_details['hours']}`\n")
        if order_details.get('commentPickup'):
            summary += f"Комментарий к самовывозу: `{order_details.get('commentPickup', 'N/A')}`\n"

    summary += f"\n*Состав заказа:*\n"
    for item in cart_items:
        try:
            price_float = float(item.get('price', 0))
            quantity = int(item.get('quantity', 0))
            total_item_float = price_float * quantity
            summary += (f"- `{item.get('name', 'N/A')}` x `{quantity}` шт. "
                       f"(`{price_float:.2f}` р. / шт.) = `{total_item_float:.2f}` р.\n")
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при форматировании товара {item.get('name', 'Unknown')}: {e}")
            summary += f"- `{item.get('name', 'N/A')}` x `{item.get('quantity', 0)}` шт. (ошибка форматирования)\n"

    # Добавляем информацию о способе оплаты
    payment_method = order_details.get('paymentMethod', 'N/A')
    payment_text = ""
    if payment_method == 'cash':
        payment_text = "Оплата наличными при получении товара"
    elif payment_method == 'card':
        payment_text = "Оплата картой при получении товара"
    elif payment_method == 'erip':
        payment_text = "Онлайн оплата ЕРИП"
    else:
        payment_text = f"Способ оплаты: {payment_method}"
    
    summary += f"\n*Способ оплаты:* {payment_text}\n"
    summary += f"\n*Общая сумма заказа:* `{total_amount:.2f}` р."
    return summary


def _format_payment_method_html(payment_method: str) -> str:
    """Форматирует способ оплаты для HTML."""
    if payment_method == 'cash':
        return "Оплата наличными при получении товара"
    elif payment_method == 'card':
        return "Оплата картой при получении товара"
    elif payment_method == 'erip':
        return "Онлайн оплата ЕРИП"
    else:
        return f"Способ оплаты: {payment_method}"


def _get_pickup_details(pickup_address_id: str) -> dict:
    """Возвращает детальную информацию о пункте самовывоза по ID."""
    pickup_details = {
        "1": {
            "name": "ТЦ Green City",
            "address": "г. Минск, ул. Притыцкого, 156, напротив 7-8 касс",
            "hours": "пн-вс. 10:00 - 22:00"
        },
        "2": {
            "name": "ТЦ Замок",
            "address": "г. Минск, пр-т.Победителей, 65, 1-й этаж, на углу магазина \"Ив Роше\"",
            "hours": "пн-вс. 10:00 - 22:00"
        },
        "3": {
            "name": "Новая Боровая",
            "address": "Копище, ул.Авиационная, 8",
            "hours": "пн-вс. 08:30 - 22:00"
        },
        "5": {
            "name": "ул. Л. Беды 26",
            "address": "Минск, ул. Л.Беды, 26, внутри помещения винного магазина WINE&SPIRITS",
            "hours": "пн-вс. с 09-00 до 21-00"
        },
        "6": {
            "name": "Маяк Минска – ул. Мстиславца 8",
            "address": "г. Минск, ул. Мстиславца, 8, вход со двора напротив детской площадки, рядом с 3 подъездом жилого дома",
            "hours": "пн-вс. с 8:30 до 21:00"
        },
        "7": {
            "name": "г. Заславль",
            "address": "г. Заславль, ул. Вокзальная, 11, железнодорожная станция \"Беларусь\"",
            "hours": "ежедневно с 7-00 до 19-00"
        },
        "8": {
            "name": "Минск Мир, ул. Лученка 1",
            "address": "г. Минск, ул. Лученка, 1, внутри помещения винного магазина WINE&SPIRITS",
            "hours": "ежедневно с 9:30 до 21:30"
        },
        "9": {
            "name": "ЖК Пирс, а/г Ратомка Морской риф 1/4",
            "address": "а/г Ратомка ул. Морской риф 1/4, вход со стороны улицы вверх по лестнице на второй этаж.",
            "hours": "пн-вс. с 8:00 до 20:00"
        },
        "10": {
            "name": "ул. Нововиленская, 45",
            "address": "г. Минск, ул. Нововиленская 45.",
            "hours": "пн-вс. с 8:00 до 20:00"
        }
    }
    return pickup_details.get(pickup_address_id, {"name": "Неизвестный адрес", "address": "N/A", "hours": "N/A"})


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
    
    # Обработка информации о самовывозе
    pickup_info = ""
    if order_details.get('deliveryMethod') == 'pickup':
        pickup_address_id = order_details.get('pickupAddress')
        if pickup_address_id:
            pickup_details = _get_pickup_details(pickup_address_id)
            pickup_info = f"""
                <p><b>Пункт самовывоза:</b> {pickup_details['name']}</p>
                <p><b>Адрес пункта самовывоза:</b> {pickup_details['address']}</p>
                <p><b>Время работы:</b> {pickup_details['hours']}</p>
            """
        else:
            pickup_info = "<p><b>Адрес самовывоза:</b> N/A</p>"
    
    pickup_comment = ("<p><b>Комментарий к самовывозу:</b> " + order_details.get('commentPickup', 'N/A') + "</p>" 
                     if (order_details.get('deliveryMethod') == 'pickup' and order_details.get('commentPickup')) else "")



    # Формируем строки таблицы для товаров
    table_rows = ""
    for item in cart_items:
        try:
            price_float = float(item.get('price', 0))
            quantity = int(item.get('quantity', 0))
            total_item = price_float * quantity
            table_rows += f"""
                                                <tr>
                                                    <td>{item.get('name', 'N/A')}</td>
                                                    <td>{quantity} шт.</td>
                                                    <td>{price_float:.2f} р.</td>
                                                    <td>{total_item:.2f} р.</td>
                                                </tr>
                                                """
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при форматировании товара для email {item.get('name', 'Unknown')}: {e}")
            table_rows += f"""
                                                <tr>
                                                    <td>{item.get('name', 'N/A')}</td>
                                                    <td>{item.get('quantity', 0)} шт.</td>
                                                    <td>ошибка</td>
                                                    <td>ошибка</td>
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
                        {pickup_info}
                        {pickup_comment}

                        <h3>💳 Способ оплаты:</h3>
                        {_format_payment_method_html(order_details.get('paymentMethod', 'N/A'))}

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


def _format_user_email_body(order_number: str, order_details: dict, cart_items: list,
                           total_amount: float) -> str:
    """Форматирует письмо для пользователя с подтверждением заказа."""

    # Проверяем доступность данных продуктов
    global products_data
    if not products_data:
        logger.error("Данные продуктов не загружены!")
        products_data = {}

    # Создаем кэш для быстрого поиска товаров по ID
    products_cache = {}
    for category_products in products_data.values():
        for product in category_products:
            products_cache[product.get('id')] = product

    # Формируем строки таблицы для товаров
    table_rows = ""
    for item in cart_items:
        try:
            price_float = float(item.get('price', 0))
            quantity = int(item.get('quantity', 0))
            total_item = price_float * quantity

            # Получаем полную информацию о товаре из кэша
            product_id = item.get('id')
            full_product_info = products_cache.get(product_id)

            # Используем полную информацию о товаре или данные из корзины
            product_name = full_product_info.get('name', item.get('name', 'N/A')) if full_product_info else item.get('name', 'N/A')
            product_image = full_product_info.get('image_url', '') if full_product_info else ''
            product_url = full_product_info.get('url', '#') if full_product_info else '#'
            product_weight = full_product_info.get('weight', 'N/A') if full_product_info else 'N/A'

            table_rows += f"""
                                                <tr>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">
                                                        <img src="{product_image}" alt="{product_name}" 
                                                             title="{product_name}" style="width:90px;height:113px">
                                                    </td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">
                                                        <a href="{product_url}" style="color:#348eda" target="_blank">
                                                            {product_name}
                                                        </a>
                                                    </td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">{quantity} шт.</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">{product_weight} гр.</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">{price_float:.2f} р.</td>
                                                </tr>
                                                """
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при форматировании товара для письма пользователю {item.get('name', 'Unknown')}: {e}")
            table_rows += f"""
                                                <tr>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">-</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">{item.get('name', 'N/A')}</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">{item.get('quantity', 0)} шт.</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">-</td>
                                                    <td style="font-family:Arial;text-align:left;color:#111111">-</td>
                                                </tr>
                                                """

    # Формируем информацию о доставке
    delivery_info = ""
    if order_details.get('deliveryMethod') == 'courier':
        delivery_info = f"""
        <p style="font-family:Arial;color:#111111;margin:20px">
            <strong>Способ получения:</strong> Доставка курьером<br>
            <strong>Город:</strong> {order_details.get('city', 'N/A')}<br>
            <strong>Адрес:</strong> {order_details.get('addressLine', 'N/A')}<br>
            <strong>Дата доставки:</strong> {order_details.get('deliveryDate', 'N/A')}
        </p>
        """
        if order_details.get('comment'):
            delivery_info += f"""
        <p style="font-family:Arial;color:#111111;margin:20px">
            <strong>Комментарий к доставке:</strong> {order_details.get('comment')}
        </p>
        """

    elif order_details.get('deliveryMethod') == 'pickup':
        pickup_address_id = order_details.get('pickupAddress')
        pickup_details = _get_pickup_details(pickup_address_id) if pickup_address_id else {"name": "N/A", "address": "N/A", "hours": "N/A"}
        
        delivery_info = f"""
        <p style="font-family:Arial;color:#111111;margin:20px">
            <strong>Способ получения:</strong> Самовывоз<br>
            <strong>Пункт самовывоза:</strong> {pickup_details['name']}<br>
            <strong>Адрес пункта самовывоза:</strong> {pickup_details['address']}<br>
            <strong>Время работы:</strong> {pickup_details['hours']}<br>
            <strong>Дата самовывоза:</strong> {order_details.get('deliveryDate', 'N/A')}
        </p>
        """
        if order_details.get('commentPickup'):
            delivery_info += f"""
        <p style="font-family:Arial;color:#111111;margin:20px">
            <strong>Комментарий к самовывозу:</strong> {order_details.get('commentPickup')}
        </p>
        """


    user_email_body = f"""
    <html>
    <head></head>
    <body>
        <div style="margin:0;padding:0;background:#f6f6f6">
            <div style="height:100%;padding-top:20px;background:#f6f6f6">
                <a href="https://drazhin.by" target="_blank">
                    <img style="display:block;margin:auto" src="https://drazhin.by//content/other/email_logo_drazhin.png" alt="https://drazhin.by">
                </a>

                <table style="padding:0 20px 20px 20px;width:100%;background:#f6f6f6;margin-top:10px">
                    <tbody>
                        <tr>
                            <td></td>
                            <td style="border:1px solid #f0f0f0;background:#ffffff;width:800px;margin:auto">
                                <div>
                                    <table style="width:100%">
                                        <tbody>
                                            <tr>
                                                <td>
                                                    <h3 style="font-family:Arial;color:#111111;font-weight:200;line-height:1.2em;margin:40px 20px;font-size:22px">
                                                        Вы сделали заказ {order_number} в Telegram боте Пекарни Дражина
                                                    </h3>

                                                    <p style="font-family:Arial;color:#111111;margin:20px">
                                                        <strong>Покупатель:</strong><br>
                                                        {order_details.get('lastName', 'N/A')} {order_details.get('firstName', 'N/A')} {order_details.get('middleName', 'N/A')}<br>
                                                        <strong>Телефон:</strong> {order_details.get('phone', 'N/A')}<br>
                                                        <strong>Email:</strong> {order_details.get('email', 'N/A')}
                                                    </p>

                                                    {delivery_info}

                                                    <h4 style="font-family:Arial;color:#111111;margin:20px">
                                                        <strong>Способ оплаты:</strong> {_format_payment_method_html(order_details.get('paymentMethod', 'N/A'))}
                                                    </h4>

                                                    <table style="width:90%;margin:auto">
                                                        <thead>
                                                            <tr>
                                                                <th style="font-family:Arial;text-align:left;color:#111111"> </th>
                                                                <th style="font-family:Arial;text-align:left;color:#111111">Наименование</th>
                                                                <th style="font-family:Arial;text-align:left;color:#111111">Количество</th>
                                                                <th style="font-family:Arial;text-align:left;color:#111111">Вес</th>
                                                                <th style="font-family:Arial;text-align:left;color:#111111">Стоимость</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {table_rows}
                                                        </tbody>
                                                    </table>

                                                    <h3 style="font-family:Arial;color:#111111;font-weight:200;line-height:1.2em;margin:40px 20px;font-size:22px">
                                                        Итого: <strong>{total_amount:.2f}</strong> р.
                                                    </h3>

                                                    <p style="font-family:Arial;color:#111111;margin:20px">
                                                        Спасибо за ваш заказ! Мы свяжемся с вами в ближайшее время для подтверждения.
                                                    </p>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </td>
                            <td></td>
                        </tr>
                    </tbody>
                </table>

                <table style="clear:both!important;width:100%">
                    <tbody>
                        <tr>
                            <td></td>
                            <td>
                                <div>
                                    <table style="width:100%;text-align:center">
                                        <tbody>
                                            <tr>
                                                <td align="center">
                                                    <p style="font-family:Arial;color:#666666;font-size:12px">
                                                        <a href="https://drazhin.by" style="color:#999999" target="_blank">
                                                            Пекарня Дражина
                                                        </a>
                                                    </p>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </td>
                            <td></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return user_email_body


@dp.message(F.text)
async def block_text_input(message: Message):
    """Блокирует текстовый ввод, если он не является командой или кнопкой."""
    allowed_texts = list(CATEGORY_MAP.keys()) + [
        "О нас", "Наши адреса", "О доставке", "/start", "/menu"
    ]

    if (message.text not in allowed_texts and 
        not re.match(r"🛒 Проверить корзину(\s\(\d+\))?", message.text)):
        await message.answer(
            "⚠️ Пожалуйста, используйте кнопки внизу для управления ботом 👇",
            reply_markup=reply_main_menu_for(message.from_user.id)
        )


async def main():
    """Главная функция для запуска бота."""
    global bot
    
    # ИСПРАВЛЕНО: Инициализируем бота с дефолтной сессией (aiogram создаст свою)
    bot = Bot(token=BOT_TOKEN)
    
    await load_products_data()
    # Загружаем счетчик заказов
    await load_order_counter()

    # Включение хендлера для Web App данных
    dp.message.register(handle_web_app_data, F.web_app_data)

    # Настраиваем API сервер
    runner = await setup_api_server()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)  # nosec B104 - Web server needs to bind to all interfaces

    # Запускаем security monitoring если включено
    security_task = None
    if config.ENABLE_SECURITY_MONITORING:
        security_task = asyncio.create_task(security_monitoring_loop())
        logger.info("🔒 Security monitoring запущен")

    web_server_task = asyncio.create_task(site.start())
    bot_polling_task = asyncio.create_task(dp.start_polling(bot))

    logger.info(f"API сервер запущен на http://0.0.0.0:{port}")
    logger.info("Бот начал опрос...")

    try:
        tasks = [bot_polling_task, web_server_task]
        if security_task:
            tasks.append(security_task)
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Остановка API сервера...")
        await runner.cleanup()
        logger.info("API сервер остановлен.")
        logger.info("Закрытие сессии бота...")
        await bot.session.close()
        logger.info("Сессия бота закрыта.")


async def security_monitoring_loop():
    """Loop для постоянного мониторинга безопасности."""
    while True:
        try:
            # Проверяем webhook security
            webhook_status = await security_manager.monitor_webhook_security()
            if not webhook_status.get("secure", True):
                logger.warning(f"🚨 Webhook security issue detected: {webhook_status}")
                
                # Автоматически удаляем подозрительные webhooks
                if webhook_status.get("status") in ["Suspicious webhook detected", "Untrusted webhook domain"]:
                    logger.warning("🚨 Attempting to delete suspicious webhook...")
                    delete_result = await security_manager.delete_webhook()
                    if delete_result.get("success"):
                        logger.info("✅ Suspicious webhook deleted successfully")
                    else:
                        logger.error(f"❌ Failed to delete suspicious webhook: {delete_result}")
            
            # Очищаем старые данные
            await security_manager.cleanup_old_data()
            
            # Получаем security report
            report = security_manager.get_security_report()
            logger.info(f"🔒 Security report: {report}")
            
            # Ждем 1 час перед следующей проверкой
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"🚨 Error in security monitoring loop: {e}")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке


if __name__ == "__main__":
    asyncio.run(main())