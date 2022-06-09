import os
import sys
from configparser import ConfigParser
import pathlib

# determine if application is a script file or frozen exe
from datetime import datetime

dir_path = ''
if getattr(sys, 'frozen', False):
    dir_path = os.path.dirname(sys.executable)
elif __file__:
    dir_path = pathlib.Path.cwd()
print(f'Рабочая папка {dir_path}')
CFG_FILE = os.path.join(dir_path, 'settings.ini')
print(f'Файл настроек {CFG_FILE}')
DB_FILE = os.path.join(dir_path, 'database.db')
print(f'Файл БД {DB_FILE}')


def get_value(node, param):
    try:
        settings = ConfigParser()
        settings.read(CFG_FILE)
        value = str(settings[node][param])
        return value
    except:
        return None


def set_value(node, param, value):
    try:
        settings = ConfigParser()
        settings.read(CFG_FILE)
        settings.set(node, param, value)
        with open(CFG_FILE, "w") as config_file:
            settings.write(config_file)
        return True
    except:
        return False


async def log_action(action, user=None):
    if user:
        print(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} === [{user.id}] {user.full_name}: {action}')
    else:
        print(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} === {action}')


