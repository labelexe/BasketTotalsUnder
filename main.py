import asyncio
import os
from datetime import datetime
from io import StringIO

import aioschedule
import requests
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import ParseMode, BotCommand, Message, User, CallbackQuery
from aiogram.utils import executor

from config import get_value, log_action, set_value
from database import db_start, get_match, new_match, check_league, add_user, create_HTML, exclude_league, \
    check_match, get_users, fix_match, del_match, finish_match, reset_stats, read_query

from keyboards import start_kb

bot = Bot(token=get_value('data', 'bot'), parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

params_live = {
    'sports': '3',
    'count': '1000',
    'antisports': '188',
    'mode': '4',
    'country': '1',
    'partner': '51',
    'getEmpty': 'true',
    'noFilterBlockEvent': 'true',
}


@dp.message_handler(CommandStart())
async def start(message: Message):
    await message.delete()
    user = User.get_current()
    mess_text = f'Бот предназначен для отслеживания баскетбольных матчей.\n\n' \
                f'Cвяжитесь с разработчиком, если хотите узнать больше о боте.'
    mess_board = await start_kb(admin=False)
    await message.answer(text=mess_text, reply_markup=mess_board)
    await add_user(user.id)
    await log_action('запустил бота', user)


@dp.message_handler(commands="stats")
async def stats(message: Message):
    await message.delete()
    user = User.get_current()
    if str(user.id) in get_value('data', 'admins'):
        html = await create_HTML()
        file = StringIO()
        file.name = 'Статистика.html'
        file.write(html)
        file.seek(0)
        await message.answer_document(document=file, caption=f'{chr(128202)} Статистика')
        await log_action('получил статистику', user)


@dp.message_handler(commands="reset")
async def reset(message: Message):
    user = User.get_current()
    await message.delete()
    if str(user.id) in get_value('data', 'admins'):
        await reset_stats()
        await log_action('сбросил статистику', user)


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
            BotCommand("reset", "Сбросить статистику"),
            BotCommand("stats", "Получить статистику"),
            BotCommand("start", "Перезапустить бота"),
        ]
    )


async def check():
    matches_data = requests.get(get_value('data', 'events_url'), params=params_live).json()

    for match_data in matches_data["Value"]:
        league = None
        alert = None
        exclude = await check_league(match_data['LI'])
        if exclude: continue
        try:
            period = match_data['SC']['CP']
            period_time = datetime.utcfromtimestamp(match_data['SC']['TS'])
            period_time = period_time.minute + period_time.second / 60
            period_time = period_time - (10 * (period - 1))
            try:
                score1 = match_data['SC']['PS'][period - 1]["Value"]['S1']
            except:
                score1 = 0
            try:
                score2 = match_data['SC']['PS'][period - 1]["Value"]['S2']
            except:
                score2 = 0
            game_total = score1 + score2
        except:
            continue

        match = await get_match(match_data['I'], period)

        if period < 4 and not match and 4.5 < period_time < 5 and game_total > 0:
            # проверка матча

            params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                           'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                           'partner': '51', 'grMode': '2', 'marketType': '1'}
            game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

            league = (f"{game_data['CN']} / {game_data['L']}", game_data['LI'])

            bk_total, bk_coeff = await check_match(game_data)
            if bk_total:
                # фиксация матча
                await new_match(game_data, bk_total, bk_coeff, float(get_value('data', 'betsize')))
                alert = f"{chr(128269)} Обнаружен матч...\n\n" \
                        f"{chr(127967)} <b>{game_data['CN']} / {game_data['L']}</b>\n\n" \
                        f"{chr(9977)} {game_data['O1']} - {game_data['O2']}\n\n" \
                        f"{chr(127936)} Идёт {period}-я четверть [{score1}:{score2}]\n\n<pre>" \
                        f"{chr(127922)} Тотал: {bk_total}\n" \
                        f"{chr(128201)} Коэфф: {bk_coeff}</pre>\n"
                await log_action(f"Анализ: {game_data['O1']} - {game_data['O2']} {score1}:{score2}")
        elif match and match[8] == -1 and 5 < period_time < 6:
            # повторная проверка
            params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                           'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                           'partner': '51', 'grMode': '2', 'marketType': '1'}
            game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

            bk_total, bk_coeff = await check_match(game_data, 1)
            if bk_total:
                # ставка на матч
                await fix_match(game_data, bk_total, bk_coeff)
                alert = f"{chr(9989)} Подходящий матч...\n\n" \
                        f"{chr(127967)} <b>{game_data['CN']} / {game_data['L']}</b>\n\n" \
                        f"{chr(9977)} {game_data['O1']} - {game_data['O2']}\n\n" \
                        f"{chr(127936)} Идёт {period}-я четверть [{score1}:{score2}]\n\n<pre>" \
                        f"{chr(127922)} Тотал: {bk_total}\n" \
                        f"{chr(128201)} Коэфф: {bk_coeff}</pre>\n"
                await log_action(f"Сигнал: {game_data['O1']} - {game_data['O2']} {score1}:{score2}")
            else:
                await del_match(game_data)
        else:
            match = await get_match(match_data['I'], period - 1)
            if not match: continue
            # четверть закончилась
            score1 = match_data['SC']['PS'][match[5] - 1]["Value"]['S1']
            score2 = match_data['SC']['PS'][match[5] - 1]["Value"]['S2']
            total_bet = float(match[6])
            if total_bet > score1+score2:
                bet_result = 0.7 * float(get_value('data', 'betsize'))
                await log_action(f"Выигрыш: {match[4]} {score1}:{score2} < {match[6]}")
                alert = f"{chr(128994) * 3} Ставка сыграла...\n\n"
            else:
                bet_result = -1 * float(get_value('data', 'betsize'))
                await log_action(f"Проигрыш: {match[4]} {score1}:{score2} > {match[6]}")
                alert = f"{chr(128308) * 3} Ставка проиграла...\n\n"
            new_balance = float(get_value('data', 'current_bank')) + bet_result
            set_value('data', 'current_bank', new_balance)
            await finish_match(match_data, match[5], score1, score2, new_balance)
            alert += f"{chr(127967)} <b>{match[3]}</b>\n\n" \
                     f"{chr(9977)} {match[4]}\n\n" \
                     f"{chr(127936)} Завершена {match[5]}-я четверть [{score1}:{score2}]\n\n<pre>" \
                     f"{chr(127922)} Тотал: {match[6]}\n" \
                     f"{chr(128201)} Коэфф: {match[7]}</pre>\n"

        if alert:
            CHANNEL = get_value('data', 'channel')
            mess = await bot.send_message(chat_id=CHANNEL, text=alert)
            await log_action(f'Сообщение в канал')

            if league:
                for admin in get_value('data', 'admins').split('|'):
                    try:
                        mess_text = f'{league[0]}'
                        mess_board = await start_kb(admin=True, league=league[1])
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
