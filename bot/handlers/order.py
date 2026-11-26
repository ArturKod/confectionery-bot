from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
import re
from datetime import datetime
# ... остальные импорты

from bot.states import OrderState
from bot.keyboards.inline import get_confirm_keyboard
from bot.repositories.product import ProductRepository
from bot.repositories.user import UserRepository
from bot.repositories.order import OrderRepository
from bot.models.models import Product
from bot.handlers.admin import notify_admin_new_order
from bot.config import settings # Импортируем настройки для ADMIN_ID

router = Router()

# 1. Пользователь нажал "Заказать"
@router.callback_query(F.data.startswith("buy_"))
async def start_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    product_id = int(callback.data.split("_")[1])
    await state.update_data(product_id=product_id)
    await state.set_state(OrderState.waiting_for_phone)
    
    await callback.message.answer("Отлично! Введите ваш номер телефона для связи:")
    await callback.answer()

# 2. Получаем телефон
@router.message(StateFilter(OrderState.waiting_for_phone))
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Регулярное выражение для РФ номеров (поддерживает +7, 8, пробелы, скобки)
    pattern = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
    
    if not re.match(pattern, phone):
        await message.answer("❌ Неверный формат номера. Пожалуйста, введите номер в формате: +7 (999) 123-45-67 или 89991234567")
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_date)
    await message.answer("Отлично. На какую дату вам нужен заказ? (Напишите в формате ДД.ММ.ГГГГ)")

# 3. Получаем дату
@router.message(StateFilter(OrderState.waiting_for_date))
async def process_date(message: Message, state: FSMContext, session: AsyncSession):
    try:
        desired_date = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пожалуйста, напишите так: 25.12.2026")
        return

    # Проверяем, что дата не в прошлом
    if desired_date.date() < datetime.now().date():
        await message.answer("❌ Эта дата уже в прошлом. Пожалуйста, выберите будущую дату:")
        return

    await state.update_data(desired_date=desired_date.isoformat())
    data = await state.get_data()
    
    product = await session.get(Product, data['product_id'])
    
    text = (
        f"Проверьте ваш заказ:\n\n"
        f"🎂 Товар: {product.name}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📅 Дата: {message.text}\n"
        f"💰 Сумма: {int(product.price)} руб.\n\n"
        f"Всё верно?"
    )
    await state.set_state(OrderState.waiting_for_confirm)
    await message.answer(text, reply_markup=get_confirm_keyboard())
    
# 4. Подтверждение
@router.callback_query(StateFilter(OrderState.waiting_for_confirm), F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    
    user = await UserRepository.get_by_tg_id(session, callback.from_user.id)
    product = await session.get(Product, data['product_id'])
    desired_date = datetime.fromisoformat(data['desired_date'])

    # Создаем заказ в БД (теперь возвращает объект со связями)
    order = await OrderRepository.create_order(
        session, user, product, data['phone'], desired_date
    )
    
    await state.clear()
    await callback.message.edit_text(f"✅ Спасибо! Ваш заказ №{order.id} принят в обработку. Мы свяжемся с вами.")
    
    # Отправляем уведомление админу
    await notify_admin_new_order(bot, settings.ADMIN_ID, order)

# 5. Отмена
@router.callback_query(StateFilter(OrderState.waiting_for_confirm), F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Оформление заказа отменено.")