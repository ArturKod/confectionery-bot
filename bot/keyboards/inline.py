from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_product_keyboard(product_id: int, is_admin: bool = False) -> InlineKeyboardMarkup | None:
    """Кнопка 'Заказать'. Возвращает None, если это админ."""
    if is_admin:
        return None # Админ не увидит кнопку
        
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Заказать", callback_data=f"buy_{product_id}")
    return builder.as_markup()

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.adjust(1)
    return builder.as_markup()