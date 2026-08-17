import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from db import init_db
from handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    # Инициализация БД
    init_db()

    # Регистрация роутеров
    dp.include_router(router)

    # Установка команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать")
    ])

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())