from datetime import datetime

import requests

from config import get_value, log_action, set_value
from database import check_league, get_match, check_match_B, new_match, fix_match, del_match, finish_match, check_matchH
from keyboards import start_kb

params_hockey = {
    'sports': '2',
    'count': '1000',
    'antisports': '188',
    'mode': '4',
    'country': '1',
    'partner': '51',
    'getEmpty': 'true',
    'noFilterBlockEvent': 'true',
}


async def checkH():
    alert = None
    league = None
    mess_text, mess_board = None, None
    try:
        matches_data = requests.get(get_value('data', 'events_url'), params=params_hockey).json()
        for match_data in matches_data["Value"]:
            league = None
            alert = None
            exclude = await check_league(match_data['LI'])
            if exclude: continue
            try:
                period = match_data['SC']['CP']
                period_time = datetime.utcfromtimestamp(match_data['SC']['TS'])
                match_time = period_time.minute + period_time.second / 60
            except:
                period = 1
                match_time = 0

            match = await get_match(1, match_data['I'], period)

            if period <= 1 and not match:
                # проверка матча

                params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                               'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                               'partner': '51', 'grMode': '2', 'marketType': '1'}
                game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

                bk_total, bk_coeff = await check_matchH(game_data)
                if bk_total:
                    # фиксация матча
                    league = (f"{game_data['CN']} / {game_data['L']}", game_data['LI'])
                    await new_match(1, game_data, bk_total, bk_coeff, float(get_value('data', 'betsizeH')))
                    await log_action(f"Анализ: {game_data['O1']} - {game_data['O2']}")
                    # mess_text = f"{chr(127954) * 5}\n\n{league[0]}\n{game_data['O1']} - {game_data['O2']}"
                    # mess_board = await start_kb(admin=True, league=league[1])
                    return None, None, None  #mess_text, mess_board, alert
            elif match and match_time == 40:
                # повторная проверка
                params_game = {'id': match_data['I'], 'lng': 'ru', 'cfview': '0', 'isSubGames': 'true',
                               'GroupEvents': 'true', 'allEventsGroupSubGames': 'true', 'countevents': '5000',
                               'partner': '51', 'grMode': '2', 'marketType': '1'}
                game_data = (requests.get(get_value('data', 'match_url'), params=params_game).json())["Value"]

                bk_total, bk_coeff = await check_matchH(game_data)
                if bk_total > match[6] * 1.5:
                    # ставка на матч
                    await fix_match(game_data, bk_total, bk_coeff)
                    alert = f"{chr(9989)} Подходящий матч...\n\n" \
                            f"{chr(127967)} <b>{game_data['CN']} / {game_data['L']}</b>\n\n" \
                            f"{chr(9977)} {game_data['O1']} - {game_data['O2']}\n\n" \
                            f"{chr(127922)} Тотал: {bk_total}\n" \
                            f"{chr(128201)} Коэфф: {bk_coeff}</pre>\n"
                    await log_action(f"Сигнал: {game_data['O1']} - {game_data['O2']} ТМ{bk_total} @ {bk_coeff}")
                else:
                    await del_match(1, game_data)
            elif match and match_time >= 60:
                current_betsize = float(get_value('data', 'betsizeH'))
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
                new_balance = float(get_value('data', 'current_bankH')) + bet_result
                set_value('data', 'current_bankH', str(new_balance))
                await finish_match(1, match_data, match[5], score1, score2, new_balance, bet_result)

                alert += f"{chr(129349)} <b>{match[3]}</b>\n\n" \
                         f"{chr(9977)} {match[4]}\n\n" \
                         f"{chr(127936)} Завершена {match[5]}-я четверть [{score1}:{score2}]\n\n<pre>" \
                         f"{chr(127922)} Тотал: {match[6]}\n" \
                         f"{chr(128201)} Коэфф: {match[7]}</pre>\n"
    except Exception as e:
        print(f'Ошибка получения данных: {e}')

    return mess_text, mess_board, alert
