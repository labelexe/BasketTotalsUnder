from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def start_kb(admin=False, league=None):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text=f'{chr(128241)} Разработчик',
                                    url='tg://resolve?domain=AntonioSim'))
    if league and admin:
        markup.insert(InlineKeyboardButton(text=f'{chr(9760)} Исключить лигу',
                                           callback_data=f'exclude:{league}'))
    return markup
