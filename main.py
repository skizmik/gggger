import asyncio
import aiohttp
import sys
from aiogram import Bot

# ================= НАСТРОЙКИ =================
API_TOKEN = 'ТВОЙ_ТОКЕН_БОТА'
CHAT_ID = 123456789  # Твой Telegram ID

bot = Bot(token=API_TOKEN)

STARS_AMOUNT = 100            # Количество звёзд в лоте
COST_PER_STAR_USD = 0.015     # Цена 1 звезды в USD
MIN_PROFIT_TON = 0.001        # Минимальный плюс в TON

FUNPAY_WITHDRAW_FEE = 0.06    # 6% вывод USDT
SWAP_FEE = 0.015              # 1.5% своп DEX

# ================= API КУРСОВ (С ЗАПАСНЫМИ ВАРИАНТАМИ) =================

async def fetch_ton_usdt(session: aiohttp.ClientSession) -> float:
    # Вариант 1: Bybit
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=TONUSDT"
        async with session.get(url, timeout=5) as resp:
            data = await resp.json()
            return float(data['result']['list'][0]['lastPrice'])
    except Exception:
        pass

    # Вариант 2: Gate.io (запасной)
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=TON_USDT"
        async with session.get(url, timeout=5) as resp:
            data = await resp.json()
            return float(data[0]['last'])
    except Exception as e:
        raise RuntimeError(f"Не удалось получить курс TON/USDT: {e}")

async def fetch_usdt_rub(session: aiohttp.ClientSession) -> float:
    # Вариант 1: OKX
    try:
        url = "https://www.okx.com/api/v5/market/ticker?instId=USDT-RUB"
        async with session.get(url, timeout=5) as resp:
            data = await resp.json()
            return float(data['data'][0]['last'])
    except Exception:
        pass

    # Вариант 2: Gate.io (запасной)
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=USDT_RUB"
        async with session.get(url, timeout=5) as resp:
            data = await resp.json()
            return float(data[0]['last'])
    except Exception as e:
        raise RuntimeError(f"Не удалось получить курс USDT/RUB: {e}")

# ================= РАСЧЁТ ЦЕНЫ =================

def calculate_price_rub(ton_usdt: float, usdt_rub: float) -> float:
    cost_per_star_ton = COST_PER_STAR_USD / ton_usdt
    total_needed_ton = (STARS_AMOUNT * cost_per_star_ton) + MIN_PROFIT_TON
    
    needed_usdt = total_needed_ton * ton_usdt
    needed_rub = needed_usdt * usdt_rub
    
    net_factor = (1 - FUNPAY_WITHDRAW_FEE) * (1 - SWAP_FEE)
    return needed_rub / net_factor

# ================= ОСНОВНОЙ ЦИКЛ =================

async def monitor_loop():
    last_sent_price = None
    print("Бот успешно запущен и мониторит рынки...")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                ton_usdt, usdt_rub = await asyncio.gather(
                    fetch_ton_usdt(session),
                    fetch_usdt_rub(session)
                )

                target_price = calculate_price_rub(ton_usdt, usdt_rub)
                price_to_send = round(target_price)

                if last_sent_price is None:
                    await bot.send_message(chat_id=CHAT_ID, text=str(price_to_send))
                    print(f"Первая цена отправлена: {price_to_send} руб. (TON: {ton_usdt}$, RUB: {usdt_rub})")
                    last_sent_price = target_price
                else:
                    if abs(target_price - last_sent_price) >= 1.0:
                        await bot.send_message(chat_id=CHAT_ID, text=str(price_to_send))
                        print(f"Цена изменилась -> Отправлено: {price_to_send} руб.")
                        last_sent_price = target_price

            except Exception as e:
                print(f"[Ошибка при расчёте/отправке]: {e}")

            await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(monitor_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен пользователем.")
        sys.exit(0)
