import asyncio
import logging
import sys
import random
import time
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# Ваши данные
TOKEN = "8664334759:AAGh8PnFp4ykyOcJuw_rB3veV5Yjgw5Dncg"
CHAT_ID = -8262187026

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояние для отслеживания последней отправленной цены
state = {
    "last_sent_price": None
}

async def get_current_price() -> float:
    """
    Автономный расчет стоимости без внешних API.
    Цена генерируется автоматически на основе базовой формулы 
    и текущего времени/небольшого случайного шага.
    """
    base_price = 1500.0
    
    # Добавляем небольшое симулированное изменение на основе текущего времени и рандома,
    # чтобы цифра иногда менялась (превышая или не превышая порог в 1 рубль)
    time_factor = int(time.time() // 10) % 20  клиентское колебание
    random_drift = random.choice([-2.5, -1.0, 0.0, 1.0, 2.5])
    
    current_price = base_price + time_factor + random_drift
    return round(current_price, 2)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Автономный бот запущен и рассчитывает стоимость.")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Команда /info для вывода подробной информации с комиссиями"""
    current_price = await get_current_price()
    commission = round(current_price * 0.02, 2) # Пример расчета комиссии 2%
    total = round(current_price + commission, 2)
    
    info_text = (
        "📊 **Подробный отчёт:**\n\n"
        f"• Текущая базовая стоимость: {current_price} руб.\n"
        f"• Комиссия системы (2%): {commission} руб.\n"
        f"• Итоговая сумма к расчету: {total} руб.\n"
        "• Порог погрешности: ±1 руб. (изменения на 1 руб. и менее игнорируются)"
    )
    await message.answer(info_text, parse_mode="Markdown")

async def price_checker_loop():
    """Фоновый цикл проверки цены каждую секунду"""
    while True:
        try:
            current_price = await get_current_price()
            
            # Если отправляем впервые
            if state["last_sent_price"] is None:
                state["last_sent_price"] = current_price
                await bot.send_message(CHAT_ID, f"{int(current_price)}")
            else:
                # Вычисляем абсолютную разницу
                difference = abs(current_price - state["last_sent_price"])
                
                # Если изменилось больше, чем на рубль
                if difference > 1.0:
                    state["last_sent_price"] = current_price
                    await bot.send_message(CHAT_ID, f"{int(current_price)}")
                    
        except Exception as e:
            logging.error(f"Ошибка в цикле расчета цены: {e}")
            
        # Задержка в 1 секунду
        await asyncio.sleep(1)

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Запускаем фоновую задачу параллельно с ботом
    asyncio.create_task(price_checker_loop())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
