from decimal import Decimal
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, or_f

from bot.repositories.order import OrderRepository
from bot.models.models import OrderStatus, Order
from bot.states import AdminState
from bot.config import settings

router = Router()

# ==========================================
# 1. УВЕДОМЛЕНИЕ О НОВОМ ЗАКАЗЕ
# ==========================================
async def notify_admin_new_order(bot: Bot, admin_id: int, order: Order):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласовать", callback_data=f"admin_agree_{order.id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel_{order.id}")
    builder.adjust(2)
    
    product_name = order.items[0].product.name if order.items else "Товар"
    text = (
        f"🔥 <b>НОВЫЙ ЗАКАЗ №{order.id}</b>\n\n"
        f"🎂 Товар: {product_name}\n"
        f"👤 Клиент: {order.user.full_name}\n"
        f"📞 Телефон: {order.user.phone}\n"
        f"📅 Дата: {order.desired_date.strftime('%d.%m.%Y') if order.desired_date else 'Не указана'}\n"
        f"💰 Базовая сумма: {int(order.total_price)} руб.\n\n"
        f"<i>Свяжитесь с клиентом для уточнения деталей.</i>"
    )
    await bot.send_message(admin_id, text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==========================================
# 2. СОГЛАСОВАНИЕ ЗАКАЗА (Ввод цены и комментов)
# ==========================================
@router.callback_query(F.data.startswith("admin_agree_"))
async def admin_start_agree(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    await state.set_state(AdminState.waiting_for_new_price)
    
    await callback.message.answer(f"Введите итоговую стоимость для заказа №{order_id} (в рублях, только цифры):")
    await callback.answer()

@router.message(AdminState.waiting_for_new_price)
async def admin_process_price(message: Message, state: FSMContext):
    try:
        text_clean = message.text.replace(',', '.').strip()
        price = Decimal(text_clean)
    except:
        await message.answer("❌ Пожалуйста, введите число (например: 3500 или 3500.50)")
        return
    
    # Сохраняем как строку, чтобы Redis FSM не выдавал ошибку сериализации
    await state.update_data(new_price=str(price))
    await state.set_state(AdminState.waiting_for_admin_comment)
    await message.answer("Введите комментарий/опции к заказу (например: 'Надпись Happy Birthday, доставка').\nИли напишите 'нет'.")

@router.message(AdminState.waiting_for_admin_comment)
async def admin_process_comment(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    comment = message.text
    data = await state.get_data()
    order_id = data['order_id']
    
    order = await OrderRepository.get_by_id(session, order_id)
    
    order.total_price = Decimal(data['new_price'])
    order.comment = comment
    order.status = OrderStatus.WAITING_FOR_PAYMENT
    await session.commit()
    
    await state.clear()
    
    await message.answer(f"✅ Заказ №{order_id} согласован. Клиенту отправлены реквизиты.")
    
    req_text = (
        f"🤝 <b>Ваш заказ №{order.id} согласован!</b>\n\n"
        f"💰 Итоговая сумма: {int(order.total_price)} руб.\n"
        f"📝 Детали: {comment}\n\n"
        f"<b>Для подтверждения заказа внесите предоплату (50% или 100%):</b>\n"
        f"📱 СБП по номеру: +7 (999) 123-45-67 (Иван И.)\n"
        f"💳 Карта: 2200 0000 0000 0000\n\n"
        f"<i>После оплаты нажмите кнопку ниже.</i>"
    )
    
    client_builder = InlineKeyboardBuilder()
    client_builder.button(text="✅ Я оплатил(а)", callback_data=f"client_paid_{order.id}")
    
    await bot.send_message(order.user.tg_id, req_text, reply_markup=client_builder.as_markup(), parse_mode="HTML")


# ==========================================
# 3. КЛИЕНТ НАЖАЛ "Я ОПЛАТИЛ"
# ==========================================
@router.callback_query(F.data.startswith("client_paid_"))
async def client_paid(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = await OrderRepository.get_by_id(session, order_id)
    
    if order.status != OrderStatus.WAITING_FOR_PAYMENT:
        await callback.answer("Статус заказа уже изменен.", show_alert=True)
        return
        
    order.status = OrderStatus.PAID
    await session.commit()
    
    await callback.message.edit_text("⏳ Спасибо! Мы проверяем поступление средств. Ожидайте подтверждения.")
    await callback.answer()
    
    admin_builder = InlineKeyboardBuilder()
    admin_builder.button(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_pay_{order.id}")
    
    await bot.send_message(
        settings.ADMIN_ID, 
        f"💰 Клиент нажал «Я оплатил» по заказу №{order.id}.\nПроверьте банк и подтвердите.", 
        reply_markup=admin_builder.as_markup()
    )


# ==========================================
# 4. АДМИН ПОДТВЕРЖДАЕТ ОПЛАТУ
# ==========================================
@router.callback_query(F.data.startswith("admin_confirm_pay_"))
async def admin_confirm_payment(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[3])
    order = await OrderRepository.get_by_id(session, order_id)
    
    order.status = OrderStatus.COOKING
    await session.commit()
    
    await callback.message.edit_text(f"✅ Оплата по заказу №{order_id} подтверждена. Заказ передан в производство.")
    await callback.answer()
    
    await bot.send_message(order.user.tg_id, f"🎉 Оплата получена! Ваш заказ №{order.id} передан кондитеру. Мы сообщим, когда он будет готов.")


# ==========================================
# 5. ОТМЕНА АДМИНОМ
# ==========================================
@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel_order(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order = await OrderRepository.get_by_id(session, order_id)
    
    if order.status in [OrderStatus.CANCELLED, OrderStatus.COMPLETED]:
        await callback.answer("Этот заказ уже отменен или завершен.", show_alert=True)
        return

    order.status = OrderStatus.CANCELLED
    await session.commit()
    
    await callback.message.edit_text(f"❌ Заказ №{order.id} отменен вами.")
    
    try:
        await bot.send_message(
            order.user.tg_id, 
            f"😔 К сожалению, ваш заказ №{order.id} был отменен. Пожалуйста, свяжитесь с нами для уточнения деталей."
        )
    except Exception:
        pass
    await callback.answer("Заказ отменен.")


# ==========================================
# 6. ПАНЕЛЬ АДМИНА (Список заказов)
# ==========================================
@router.message(or_f(Command("admin"), F.text == "⚙️ Панель админа"))
async def admin_panel(message: Message, session: AsyncSession):
    if message.from_user.id != settings.ADMIN_ID:
        return # Игнорируем, если пишет не админ

    orders = await OrderRepository.get_all_active_orders(session)
    if not orders:
        await message.answer("Активных заказов нет. Можно отдохнуть! ☕")
        return

    await message.answer("📋 <b>Активные заказы:</b>", parse_mode="HTML")
    
    for order in orders:
        product_name = order.items[0].product.name if order.items else "Товар"
        
        # Красиво форматируем статус
        status_text = order.status.value
        
        text = (
            f"<b>Заказ №{order.id}</b> (Статус: <i>{status_text}</i>)\n"
            f"Товар: {product_name}\n"
            f"Дата: {order.desired_date.strftime('%d.%m.%Y') if order.desired_date else 'Не указана'}"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="Управлять ➡️", callback_data=f"admin_manage_{order.id}")
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==========================================
# 7. УПРАВЛЕНИЕ КОНКРЕТНЫМ ЗАКАЗОМ
# ==========================================
@router.callback_query(F.data.startswith("admin_manage_"))
async def admin_manage_order(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order = await OrderRepository.get_by_id(session, order_id)
    
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    product_name = order.items[0].product.name if order.items else "Товар"
    client_name = order.user.full_name if order.user else "Клиент"
    phone = order.user.phone if order.user else "Нет"
    
    text = (
        f"🔍 <b>Детали заказа №{order.id}</b>\n\n"
        f"Статус: <b>{order.status.value}</b>\n"
        f"🎂 Товар: {product_name}\n"
        f"👤 Клиент: {client_name}\n"
        f"📞 Телефон: {phone}\n"
        f"📅 Дата: {order.desired_date.strftime('%d.%m.%Y') if order.desired_date else 'Не указана'}\n"
        f"💰 Сумма: {int(order.total_price)} руб.\n"
        f"📝 Комментарий: {order.comment or 'Нет'}\n"
    )

    builder = InlineKeyboardBuilder()
    
    # Логика кнопок в зависимости от текущего статуса
    if order.status == OrderStatus.COOKING:
        builder.button(text="✅ Заказ готов (К выдаче)", callback_data=f"admin_set_ready_{order.id}")
    elif order.status == OrderStatus.READY:
        builder.button(text="🏁 Завершить заказ", callback_data=f"admin_set_completed_{order.id}")
    elif order.status == OrderStatus.NEW:
        builder.button(text="✅ Согласовать", callback_data=f"admin_agree_{order.id}")
    
    builder.button(text="🔙 Закрыть", callback_data="close_admin_msg")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==========================================
# 8. СМЕНА СТАТУСОВ (Готов / Завершен)
# ==========================================
@router.callback_query(F.data.startswith("admin_set_ready_"))
async def admin_set_ready(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    order_id = int(callback.data.split("_")[3])
    order = await OrderRepository.get_by_id(session, order_id)
    
    order.status = OrderStatus.READY
    await session.commit()
    
    await callback.answer("Статус изменен на 'Готов'")
    await callback.message.edit_text(f"✅ Заказ №{order_id} готов к выдаче. Клиент уведомлен.")
    
    await bot.send_message(
        order.user.tg_id, 
        f"🎉 Отличные новости! Ваш заказ №{order.id} готов. Ждем вас за самовывозом!"
    )

@router.callback_query(F.data.startswith("admin_set_completed_"))
async def admin_set_completed(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    order_id = int(callback.data.split("_")[3])
    order = await OrderRepository.get_by_id(session, order_id)
    
    order.status = OrderStatus.COMPLETED
    await session.commit()
    
    await callback.answer("Заказ завершен")
    await callback.message.edit_text(f"🏁 Заказ №{order_id} завершен и выдан.")
    
    await bot.send_message(
        order.user.tg_id, 
        f"✨ Спасибо за заказ! Будем рады видеть вас снова. Заказ №{order.id} завершен."
    )


# ==========================================
# 9. ВСПОМОГАТЕЛЬНЫЕ КНОПКИ
# ==========================================
@router.callback_query(F.data == "close_admin_msg")
async def close_admin_msg(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()