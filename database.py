import sqlite3

from config import DB_FILE, log_action, get_value, set_value


async def db_start():
    global base, cur
    base = sqlite3.connect(DB_FILE)
    cur = base.cursor()
    if base:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tgid INTEGER NOT NULL UNIQUE)
            ;
            CREATE TABLE IF NOT EXISTS excluded (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL UNIQUE)
            ;
            CREATE TABLE IF NOT EXISTS Bbets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER UNIQUE,
                match_date TEXT,
                league TEXT,
                teams TEXT,
                period INTEGER,
                total TEXT,
                coef float,
                result bit,
                betsize float,
                balance float)
            ;
            CREATE TABLE IF NOT EXISTS Bresults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT,
                league TEXT,
                teams TEXT,
                period INTEGER,
                total TEXT,
                coef float,
                betsize float,
                balance float,
                result integer)
            ;
            CREATE TABLE IF NOT EXISTS Hbets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER UNIQUE,
                match_date TEXT,
                league TEXT,
                teams TEXT,
                period INTEGER,
                total TEXT,
                coef float,
                result bit,
                betsize float,
                balance float)
            ;
            CREATE TABLE IF NOT EXISTS Hresults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT,
                league TEXT,
                teams TEXT,
                period INTEGER,
                total TEXT,
                coef float,
                betsize float,
                balance float,
                result integer)""")
        base.commit()
        print(f"База данных подключена...")
    else:
        print(f"База данных не подключена...")


async def execute_query(query):
    try:
        cur.execute(query)
        base.commit()
        return True
    except Exception as e:
        return False


async def read_query(query, all=False):
    try:
        if all:
            return cur.execute(query).fetchall()
        else:
            return cur.execute(query).fetchone()
    except:
        return None


async def add_user(user):
    await execute_query(f"INSERT INTO users (tgid) VALUES ({user})")


async def get_users():
    return await read_query(f"SELECT * FROM users", True)


async def exclude_league(league):
    await execute_query(f"INSERT INTO excluded (league_id) VALUES ({int(league)})")


async def check_league(league):
    records = await read_query(f"SELECT ID FROM excluded WHERE league_id = {int(league)}")
    if records:
        return True
    else:
        return False


async def create_HTML(sport):
    bets = await read_query(f"SELECT * FROM {'B' if sport == 0 else 'H'}results ORDER BY ID", all=True)

    color1 = ' bgcolor=dcf8dc style="text-align: center;"'
    color2 = ' bgcolor=f8dcdc style="text-align: center;"'
    header_style = ' style="text-align: center; color: #ffffff" bgcolor="000000"'
    header = f'<thead>\n<tr{header_style}>\n'
    for value in ['Дата', 'Лига', 'Матч', 'Период', 'Тотал', 'Кф', 'Ставка', 'Баланс']:
        header += f'<th>{value}</th>'
    header += '\n</thead>\n'

    html = f'<table width="100%" border="1" class="dataframe">\n<tbody>\n'
    html += header
    if bets:
        for bet in bets:
            color = color1 if bet[9] == 1 else color2
            html += f'<td{color}>{bet[1]}</td>\n' \
                    f'<td{color}>{bet[2]}</td>\n' \
                    f'<td{color}>{bet[3]}</td>\n' \
                    f'<td{color}>{bet[4]}</td>\n' \
                    f'<td{color}>{bet[5]}</td>\n' \
                    f'<td{color}>{bet[6]}</td>\n' \
                    f'<td{color}>{bet[7]}</td>\n' \
                    f'<td{color}>{bet[8]}</td>\n' \
                    f'</tr>\n'
    html += '</tbody>\n</table>'
    return html


async def get_match(sport, match_id, period):
    match = await read_query(f"SELECT * FROM {'B' if sport == 0 else 'H'}bets "
                             f"WHERE match_id = {match_id} and period = {period} "
                             f"and result < 1")
    return match


async def check_match_B(match_data, first=None):
    _coef = 0
    _total = 0
    add = 12 if first else 10
    period = match_data["SC"]["CP"]
    try:
        score1 = match_data['SC']['PS'][period - 1]["Value"]['S1']
    except Exception as e:
        score1 = 0
    try:
        score2 = match_data['SC']['PS'][period - 1]["Value"]['S2']
    except Exception as e:
        score2 = 0
    game_total = score1 + score2

    try:
        for panel in match_data["SG"]:
            try:
                if panel["PN"] == f'{period}-я Четверть':
                    for odds in panel["GE"]:
                        if odds["G"] == 4:
                            for total_list in odds["E"]:
                                for total in total_list:
                                    if total["T"] == 10:
                                        bkcf = total["C"]
                                        bktl = total["P"]
                                        if bkcf >= float(get_value('data', 'coefB')) and \
                                                (bkcf < _coef or _coef == 0) and \
                                                (bktl - add) / 2 > game_total:
                                            _coef = bkcf
                                            _total = bktl
                                    else:
                                        continue
                        else:
                            continue
                else:
                    continue
            except Exception as e:
                continue
    except Exception as e:
        return None, None

    if _coef > 0:
        return _total, _coef
    else:
        return None, None


async def check_matchH(match_data):
    _coef = 0
    _total = 0
    try:
        for odds in match_data["GE"]:
            if odds["G"] == 4:
                for total_list in odds["E"]:
                    for total in total_list:
                        if total["T"] == 9:
                            bkcf = total["C"]
                            bktl = total["P"]
                            if abs(float(get_value('data', 'coefH')) - bkcf) < abs(_coef - bkcf):
                                _coef = bkcf
                                _total = bktl
                            else:
                                continue
                        else:
                            continue
            else:
                continue
    except Exception as e:
        return None, None

    if _coef > 0:
        return _total, _coef
    else:
        return None, None


async def new_match(sport, game_data, total, coef, betsize):
    await execute_query(
        f"INSERT INTO {'B' if sport == 0 else 'H'}bets (match_id, league, teams, period, total, coef, result, betsize) "
        f"VALUES ({game_data['I']}, '{game_data['CN']} / {game_data['L']}', "
        f"'{game_data['O1']} - {game_data['O2']}', {game_data['SC']['CP']}, "
        f"'{total}', '{coef}', -1, {betsize})")


async def fix_match(sport, game_data, total, coef):
    await execute_query(f"UPDATE {'B' if sport == 0 else 'H'}bets SET result = 0, total = {total}, coef = {coef} "
                        f"WHERE match_id = {game_data['I']} and period={game_data['SC']['CP']}")


async def del_match(sport, game_data):
    await execute_query(f"DELETE FROM {'B' if sport == 0 else 'H'}bets "
                        f"WHERE match_id = {game_data['I']} and period={game_data['SC']['CP']}")


async def finish_match(sport, game_data, period, score1, score2, balance, bet_result):
    await execute_query(f"UPDATE {'B' if sport == 0 else 'H'}bets "
                        f"SET result = {0 if bet_result<0 else 1}, "
                        f"match_date = datetime('now'), "
                        f"total = total || ' [{score1}' || ':' || '{score2}]',"
                        f"balance = {balance} "
                        f"WHERE match_id = {game_data['I']} and period={period}")

    res = await read_query(f"SELECT * from {'B' if sport == 0 else 'H'}bets "
                           f"WHERE match_id = {game_data['I']} and period={period}")

    await execute_query(f"INSERT INTO {'B' if sport == 0 else 'H'}results "
                        f"(match_date, league, teams, period, total, coef, betsize, balance, result)"
                        f"VALUES (datetime('now'), '{game_data['CN']} / {game_data['L']}', "
                        f"'{game_data['O1']} - {game_data['O2']}', {period}, "
                        f"'{res[6]}', '{res[7]}', {res[9]}, {balance}, {0 if bet_result<0 else 1})")


async def reset_stats():
    await execute_query(f"DELETE FROM bets")
    set_value('data', 'current_bank', get_value('data', 'start_bank'))
