from datetime import datetime

import requests

from config import get_value, log_action, set_value
from database import check_league, get_match, check_match_B, new_match, fix_match, del_match, finish_match
from keyboards import start_kb

params_basketball = {
    'sports': '3',
    'count': '1000',
    'antisports': '188',
    'mode': '4',
    'country': '1',
    'partner': '51',
    'getEmpty': 'true',
    'noFilterBlockEvent': 'true',
}


async def checkB():
    alert = None
    league = None
    mess_text, mess_board = None, None
    try:
        matches_data = requests.get(get_value('data', 'events_url'), params=params_basketball).json()
        for match_data in matches_data["Value"]:
            exclude = await check_league(match_data['LI'])
            # if exclude: continue
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

            match = await get_match(0, match_data['I'], period)

            if period < 4 and not match and 4.5 < period_time < 5 and game_total > 0:
                # проверка матча

                params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                               'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                               'partner': '51', 'grMode': '2', 'marketType': '1'}
                game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

                bk_total, bk_coeff = await check_match_B(game_data, 1)
                if bk_total:
                    # фиксация матча
                    league = (f"{game_data['CN']} / {game_data['L']}", game_data['LI'])
                    await new_match(0, game_data, bk_total, bk_coeff, float(get_value('data', 'betsizeB')))
                    alert = f"{chr(128269)} Обнаружен матч...\n\n" \
                            f"{chr(127967)} <b>{game_data['CN']} / {game_data['L']}</b>\n\n" \
                            f"{chr(9977)} {game_data['O1']} - {game_data['O2']}\n\n" \
                            f"{chr(127936)} Идёт {period}-я четверть [{score1}:{score2}]\n\n<pre>" \
                            f"{chr(127922)} Тотал: {bk_total}\n" \
                            f"{chr(128201)} Коэфф: {bk_coeff}</pre>\n"
                    await log_action(f"Анализ: {game_data['O1']} - {game_data['O2']} {score1}:{score2}")
                    mess_text = f'{chr(127936) * 5}\n\n{league[0]}\n{game_data["O1"]} - {game_data["O2"]}'
                    mess_board = await start_kb(admin=True, league=league[1])
                    return mess_text, mess_board, alert
            elif match and match[8] == -1 and 5 < period_time < 6:
                # повторная проверка
                params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                               'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                               'partner': '51', 'grMode': '2', 'marketType': '1'}
                game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

                bk_total, bk_coeff = await check_match_B(game_data)
                if bk_total:
                    # ставка на матч
                    await fix_match(0, game_data, bk_total, bk_coeff)
                    alert = f"{chr(9989)} Подходящий матч...\n\n" \
                            f"{chr(127967)} <b>{game_data['CN']} / {game_data['L']}</b>\n\n" \
                            f"{chr(9977)} {game_data['O1']} - {game_data['O2']}\n\n" \
                            f"{chr(127936)} Идёт {period}-я четверть [{score1}:{score2}]\n\n<pre>" \
                            f"{chr(127922)} Тотал: {bk_total}\n" \
                            f"{chr(128201)} Коэфф: {bk_coeff}</pre>\n"
                    await log_action(f"Сигнал: {game_data['O1']} - {game_data['O2']} {score1}:{score2}")
                else:
                    await del_match(0, game_data)
            else:
                match = await get_match(0, match_data['I'], period - 1)
                if not match: continue
                # четверть закончилась
                current_betsize = float(get_value('data', 'betsizeB'))
                score1 = match_data['SC']['PS'][match[5] - 1]["Value"]['S1']
                score2 = match_data['SC']['PS'][match[5] - 1]["Value"]['S2']
                total_bet = float(match[6])
                if total_bet > score1 + score2:
                    bet_result = 0.7 * current_betsize
                    await log_action(f"Выигрыш: {match[4]} {score1}:{score2} < {match[6]}")
                    alert = f"{chr(128994) * 3} Ставка сыграла...\n\n"
                else:
                    bet_result = -1 * current_betsize
                    await log_action(f"Проигрыш: {match[4]} {score1}:{score2} > {match[6]}")
                    alert = f"{chr(128308) * 3} Ставка проиграла...\n\n"
                current_balance = float(get_value('data', 'current_bankB'))
                new_balance = current_balance + bet_result
                set_value('data', 'current_bankB', str(new_balance))
                await finish_match(0, match_data, match[5], score1, score2, new_balance, bet_result)
                alert += f"{chr(127967)} <b>{match[3]}</b>\n\n" \
                         f"{chr(9977)} {match[4]}\n\n" \
                         f"{chr(127936)} Завершена {match[5]}-я четверть [{score1}:{score2}]\n\n<pre>" \
                         f"{chr(127922)} Тотал: {match[6]}\n" \
                         f"{chr(128201)} Коэфф: {match[7]}</pre>\n"
    except Exception as e:
        print(f'Ошибка получения данных: {e}')

    return mess_text, mess_board, alert