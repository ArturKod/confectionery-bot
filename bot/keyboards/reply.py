from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎂 Каталог")
    
    if not is_admin:
        builder.button(text="📋 Мои заказы")
    else:
        builder.button(text="⚙️ Панель админа")
        
    # Делаем по 2 кнопки в ряд
    builder.adjust(2) 
    return builder.as_markup(resize_keyboard=True)