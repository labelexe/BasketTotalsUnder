import asyncio
import os
from datetime import datetime
from io import StringIO

import aioschedule
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import ParseMode, BotCommand, Message, User, CallbackQuery
from aiogram.utils import executor

from config import get_value, log_action
from database import add_user, create_HTML, exclude_league, db_start
from hockey import checkH
from basketball import checkB
from keyboards import start_kb

bot = Bot(token=get_value('data', 'bot'), parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)


@dp.message_handler(CommandStart())
async def start(message: Message):
    await message.delete()
    user = User.get_current()
    mess_text = f'Бот предназначен для отслеживания спортивных событий.\n\n' \
                f'Cвяжитесь с разработчиком, если хотите узнать больше о боте.'
    mess_board = await start_kb(admin=False)
    await message.answer(text=mess_text, reply_markup=mess_board)
    await add_user(user.id)
    await log_action('запустил бота', user)


@dp.message_handler(commands="basketball")
async def stats1(message: Message):
    await message.delete()
    user = User.get_current()
    if str(user.id) in get_value('data', 'admins'):
        html = await create_HTML(0)
        file = StringIO()
        file.name = 'Статистика "Баскетбол".html'
        file.write(html)
        file.seek(0)
        await message.answer_document(document=file, caption=f'{chr(127936)} Статистика')
        await log_action('получил статистику "Баскетбол"', user)


@dp.message_handler(commands="hockey")
async def stats2(message: Message):
    await message.delete()
    user = User.get_current()
    if str(user.id) in get_value('data', 'admins'):
        html = await create_HTML(1)
        file = StringIO()
        file.name = 'Статистика "Хоккей".html'
        file.write(html)
        file.seek(0)
        await message.answer_document(document=file, caption=f'{chr(127954)} Статистика')
        await log_action('получил статистику "Хоккей"', user)


@dp.message_handler()
async def any_message(message: Message):
    await message.delete()


@dp.callback_query_handler()
async def cb_message(call: CallbackQuery):
    if call.data.startswith('exclude'):
        league = call.data.split(':')[1]
        await exclude_league(league)
    await call.message.delete()


async def active_sign():
    with open(f"check_state", "w", encoding='utf-8') as file:
        file.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        # print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Проверка сообщений...')


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            BotCommand("basketball", 'Статистика "Баскетбол"'),
            BotCommand("hockey", 'Статистика "Хоккей"'),
            BotCommand("start", "Перезапустить бота"),
        ]
    )


async def check():
    mess_text, mess_board, alert = await checkB()
    if alert:
        await bot.send_message(chat_id=get_value('data', 'channelB'), text=alert)

    if mess_text and mess_board:
        for admin in get_value('data', 'admins').split('|'):
            try:
                await bot.send_message(chat_id=admin, text=mess_text, reply_markup=mess_board)
            except:
                pass

    mess_text, mess_board, alert = await checkH()
    if alert:
        await bot.send_message(chat_id=get_value('data', 'channelH'), text=alert)

    if mess_text and mess_board:
        for admin in get_value('data', 'admins').split('|'):
            try:
                await bot.send_message(chat_id=admin, text=mess_text, reply_markup=mess_board)
            except:
                pass

async def check_matches():
    aioschedule.every(5).seconds.do(check)
    aioschedule.every(10).seconds.do(active_sign)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp):
    await set_default_commands(dp)
    await db_start()
    asyncio.create_task(check_matches())
    os.system('cls')
    await log_action(f"<Бот @BasketTotalsUnderBot запущен>")


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
