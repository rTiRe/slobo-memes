from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


markup_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Добавить мем',
                callback_data='add_meme',
            ),
        ],
    ],
)


async def keyboard() -> InlineKeyboardMarkup:
    return markup_keyboard