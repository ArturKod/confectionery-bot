from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.repositories.user import UserRepository
from bot.repositories.order import OrderRepository

router = Router()

# Обратите внимание: добавили F в импорты выше, 
# а также фильтр F.text для кнопки из меню
@router.message(or_f(Command("my_orders"), F.text == "📋 Мои заказы"))
async def show_my_orders(message: Message, session: AsyncSession):
    user = await UserRepository.get_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Вы еще не зарегистрированы. Напишите /start")
        return

    orders = await OrderRepository.get_user_orders(session, user.id)
    if not orders:
        await message.answer("У вас пока нет активных заказов.")
        return

    await message.answer("📋 Ваши заказы:")
    
    for order in orders:
        product_name = order.items[0].product.name if order.items else "Товар"
        
        # Красиво выводим статус
        text = (
            f"📦 <b>Заказ №{order.id}</b>\n"
            f"Товар: {product_name}\n"
            f"Статус: <b>{order.status.value}</b>\n"
            f"Сумма: {int(order.total_price)} руб.\n"
            f"Дата: {order.desired_date.strftime('%d.%m.%Y') if order.desired_date else 'Не указана'}"
        )
        await message.answer(text, parse_mode="HTML")