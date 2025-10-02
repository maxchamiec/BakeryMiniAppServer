from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from .config import SecureConfig

# Получаем URL из конфигурации
config = SecureConfig()
BASE_WEBAPP_URL = config.BASE_WEBAPP_URL

# Базовые URL для reply-кнопок (указаны явно по требованию)
REPLY_BASE_WEBAPP_URL = "https://miniapp.drazhin.by/bot-app/"
REPLY_MENU_URL = f"{REPLY_BASE_WEBAPP_URL}?view=categories#"
REPLY_CART_URL = f"{REPLY_BASE_WEBAPP_URL}?view=cart#"


def _build_web_app_url(view: str) -> str:
    """Формирует URL для inline-кнопок с учётом возможного query у BASE_WEBAPP_URL."""
    separator = '&' if '?' in BASE_WEBAPP_URL else '?'
    return f"{BASE_WEBAPP_URL}{separator}view={view}"

# Reply-клавиатура "назад в меню"
back_to_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Назад в меню")]
    ],
    resize_keyboard=True,
    is_persistent=True,
    one_time_keyboard=False,
    input_field_placeholder="Выберите категорию или действие ⬇️"
)


def generate_reply_main_menu(cart_items_count: int = 0) -> ReplyKeyboardMarkup:
    cart_button_text = (
        f"🛒 Проверить корзину ({cart_items_count})" if cart_items_count > 0 else "🛒 Проверить корзину"
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Наше меню", web_app=WebAppInfo(url=REPLY_MENU_URL))],
            [KeyboardButton(text="Проверить корзину", web_app=WebAppInfo(url=REPLY_CART_URL))],
            [
                KeyboardButton(text="Наши адреса"),
                KeyboardButton(text="О доставке"),
                KeyboardButton(text="О нас")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите категорию или действие ⬇️"
    )
    return keyboard


def generate_inline_main_menu(cart_items_count: int = 0) -> InlineKeyboardMarkup:
    cart_button_text = (
        f"🛒 Проверить корзину ({cart_items_count})" if cart_items_count > 0 else "🛒 Проверить корзину"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Наше меню",
                web_app=WebAppInfo(url=_build_web_app_url("categories"))
            )
        ],
        [
            InlineKeyboardButton(
                text=cart_button_text,
                web_app=WebAppInfo(url=_build_web_app_url("cart"))
            )
        ],
        [
            InlineKeyboardButton(text="Наши адреса", callback_data="info:addresses"),
            InlineKeyboardButton(text="О доставке", callback_data="info:delivery"),
            InlineKeyboardButton(text="О нас", callback_data="info:about"),
        ]
    ])
    return keyboard
