from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

markup_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Доба'
                     'вить мем',
                callback_data='add_meme',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Случайный общий',
                callback_data='random_public',
            ),
            InlineKeyboardButton(
                text='Случайный личный',
                callback_data='random_saved',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Мои сохры',
                callback_data='list_saved',
            ),
        ],
        [
            InlineKeyboardButton(
                text='Популярный',
                callback_data='popular',
            ),
        ],
    ],
)


async def keyboard() -> InlineKeyboardMarkup:
    return markup_keyboard
