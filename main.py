import asyncio
import aiohttp
from aiogram import Bot

# ================= НАСТРОЙКИ БОТА =================
API_TOKEN = '8664334759:AAGh8PnFp4ykyOcJuw_rB3veV5Yjgw5Dncg'
CHAT_ID = 8262187026  # Твой Telegram ID

bot = Bot(token=API_TOKEN)

# Параметры лота и комиссий
STARS_AMOUNT = 100            # Количество звёзд в лоте
COST_PER_STAR_USD = 0.015     # Фиксированная цена 1 звезды в USD (себестоимость)
MIN_PROFIT_TON = 0.001        # Минимальный чистый плюс в TON

FUNPAY_WITHDRAW_FEE = 0.06    # 6% вывод USDT с FunPay
SWAP_FEE = 0.015              # 1.5% своп USDT -> TON на DEX

# ================= БЕСПЛАТНЫЕ API (БЕЗ КЛЮЧЕЙ) =================
async def fetch_ton_usdt(session: aiohttp.ClientSession) -> float:
    """Динамический курс TON/USDT с Bybit"""
    url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=TONUSDT"
    async with session.get(url, timeout=3) as resp:
        data = await resp.json()
        return float(data['result']['list'][0]['lastPrice'])

async def fetch_usdt_rub(session: aiohttp.ClientSession) -> float:
    """Курс USDT/RUB с OKX"""
    url = "https://www.okx.com/api/v5/market/ticker?instId=USDT-RUB"
    async with session.get(url, timeout=3) as resp:
        data = await resp.json()
        return float(data['data'][0]['last'])

# ================= РАСЧЁТ ДИНАМИЧЕСКОЙ ЦЕНЫ =================
def calculate_price_rub(ton_usdt: float, usdt_rub: float) -> float:
    # 1. ДИНАМИКА: Считаем, сколько TON прямо СЕЙЧАС стоит 1 звезда
    cost_per_star_ton = COST_PER_STAR_USD / ton_usdt
    
    # 2. Общий закуп пака в TON + минимальный плюс
    total_needed_ton = (STARS_AMOUNT * cost_per_star_ton) + MIN_PROFIT_TON
    
    # 3. Переводим нужные TON в USDT и затем в Рубли
    needed_usdt = total_needed_ton * ton_usdt
    needed_rub = needed_usdt * usdt_rub
    
    # 4. Накидываем комиссии (FunPay 6% + Swap 1.5%), чтобы выйти в плюс
    net_factor = (1 - FUNPAY_WITHDRAW_FEE) * (1 - SWAP_FEE)
    final_price_rub = needed_rub / net_factor
    
    return final_price_rub

# ================= ОСНОВНОЙ ЦИКЛ =================
async def monitor_loop():
    last_sent_price = None

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 1. Тянем свежие курсы
                ton_usdt, usdt_rub = await asyncio.gather(
                    fetch_ton_usdt(session),
                    fetch_usdt_rub(session)
                )

                # 2. Считаем цену с учётом плавающего курса TON
                target_price = calculate_price_rub(ton_usdt, usdt_rub)

                # 3. Отправляем строго при изменении >= 1 рубля
                if last_sent_price is None:
                    price_to_send = round(target_price)
                    await bot.send_message(chat_id=CHAT_ID, text=str(price_to_send))
                    last_sent_price = target_price
                else:
                    if abs(target_price - last_sent_price) >= 1.0:
                        price_to_send = round(target_price)
                        await bot.send_message(chat_id=CHAT_ID, text=str(price_to_send))
                        last_sent_price = target_price

            except Exception as e:
                pass

            await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(monitor_loop())
