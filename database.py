import sqlite3

from config import DB_FILE


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
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                match_date TEXT,
                league TEXT,
                teams TEXT,
                period INTEGER,
                total TEXT,
                coef float,
                result bit)""")
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


async def create_HTML():
    bets = await read_query(f"SELECT * FROM bets WHERE result > 0 ORDER BY ID", all=True)

    color1 = ' bgcolor=dcf8dc style="text-align: center;"'
    color2 = ' bgcolor=dcdcf8 style="text-align: center;"'
    header_style = ' style="text-align: center; color: #ffffff" bgcolor="000000"'
    header = f'<thead>\n<tr{header_style}>\n'
    for value in ['Дата', 'Лига', 'Матч', 'Период', 'Тотал', 'Кф']:
        header += f'<th>{value}</th>'
    header += '\n</thead>\n'

    html = f'<table width="100%" border="1" class="dataframe">\n<tbody>\n'
    html += header
    if bets:
        for bet in bets:
            color = color1 if bet[8] == 2 else color2
            html += f'<td{color}>{bet[2]}</td>\n' \
                    f'<td{color}>{bet[3]}</td>\n' \
                    f'<td{color}>{bet[4]}</td>\n' \
                    f'<td{color}>{bet[5]}</td>\n' \
                    f'<td{color}>{bet[6]}</td>\n' \
                    f'<td{color}>{bet[7]}</td>\n' \
                    f'</tr>\n'
    html += '</tbody>\n</table>'
    return html


async def get_match(match_id, period):
    match = await read_query(f"SELECT * FROM bets "
                             f"WHERE match_id = {match_id} and period = {period} "
                             f"and result < 1")
    return match


async def check_match(match_data):
    bkcoeff = 0
    bktotal = 0
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
            if panel["PN"] == f'{period}-я Четверть':
                for odds in panel["GE"]:
                    if odds["G"] == 4:
                        for total_list in odds["E"]:
                            for total in total_list:
                                if total["T"] == 9:
                                    if abs(1.7 - total["C"]) < abs(1.7 - bkcoeff):
                                        bkcoeff = total["C"]
                                        bktotal = total["P"]
                                else:
                                    continue
                    else:
                        continue
            else:
                continue
    except Exception as e:
        return None, None

    if (bktotal - 10) / 2 > game_total:
        return bktotal, bkcoeff
    else:
        return None, None


async def new_match(game_data, total, coef):
    await execute_query(f"INSERT INTO bets (match_id, league, teams, period, total, coef, result) "
                        f"VALUES ({game_data['I']}, '{game_data['CN']} / {game_data['L']}', "
                        f"'{game_data['O1']} - {game_data['O2']}', {game_data['SC']['CP']}, "
                        f"'{total}', '{coef}', -1)")


async def fix_match(game_data, total, coef):
    await execute_query(f"UPDATE bets SET result = 0, total = {total}, coef = {coef} "
                        f"WHERE match_id = {game_data['I']} and period={game_data['SC']['CP']}")


async def del_match(game_data):
    await execute_query(f"DELETE FROM bets "
                        f"WHERE match_id = {game_data['I']} and period={game_data['SC']['CP']}")


async def finish_match(game_data, period, score1, score2):
    await execute_query(f"UPDATE bets "
                        f"SET result = case when total > {score1+score2} then 2 else 1 end, "
                        f"match_date = datetime('now'), "
                        f"total = total || ' [{score1}' || ':' || '{score2}]' "
                        f"WHERE match_id = {game_data['I']} and period={period}")
    return await read_query(f"SELECT * FROM bets WHERE match_id = {game_data['I']} and period = {period}")


async def reset_stats():
    await execute_query(f"DELETE FROM bets")
