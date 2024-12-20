from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from src.handlers.router import router
from src.keyboards.meme import keyboard
from src.keyboards.request_meme import keyboard as request_keyboard
from src.states.states import AddMemeStates, MainStates, MemeStates
from src.storage.rabbitmq import publish_message_with_response
from src.templates.env import render
from src.utils.edit_or_send_message import edit_or_send_message
from src.utils.image import Image


@router.callback_query(
    MainStates.main_menu,
    F.data == 'add_meme',
    flags={'new_state': AddMemeStates.request_meme},
)
async def request_meme(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    message = await query.message.edit_text(
        text=render('request_meme.jinja2'),
        reply_markup=await request_keyboard(),
    )
    await state.update_data(request_message=message.message_id)


@router.message(
    AddMemeStates.request_meme,
    flags={'new_state': AddMemeStates.process_meme},
)
async def process_meme(message: Message, state: FSMContext) -> None:
    await message.delete()
    state_data = await state.get_data()
    request_message = state_data.get('request_message')
    if not message.photo:
        message_args = {
            'text': render('no_photo_in_meme.jinja2'),
            'reply_markup': await request_keyboard(),
            'chat_id': message.chat.id,
        }
        await state.set_state(AddMemeStates.request_meme)
        await edit_or_send_message(message_args, request_message)
        return
    if message.caption and len(message.caption) > 250:
        message_args = {
            'text': render('caption_too_long.jinja2'),
            'reply_markup': await request_keyboard(),
            'chat_id': message.chat.id,
        }
        await state.set_state(AddMemeStates.request_meme)
        await edit_or_send_message(message_args, request_message)
        return
    file_url = await Image.get_telegram_url(message.photo[-1].file_id)
    publish_result = await publish_message_with_response(
        'add_meme',
        {
            'creator_id': message.from_user.id,
            'description': message.html_text,
            'image_url': file_url,
        },
    )
    message_args = {
        'text': render(
            'meme.jinja2',
            description=publish_result['description'],
        ),
        'reply_markup': await keyboard(
            is_owner=publish_result['creator_id'] == message.from_user.id,
            is_saved=publish_result['is_saved'],
            is_public=publish_result['is_public'],
            likes=publish_result['likes'],
            dislikes=publish_result['dislikes'],
            user_rating=publish_result['user_rating'],
        ),
        'chat_id': message.chat.id,
        'link_preview_options': LinkPreviewOptions(
            url=publish_result['image_url'],
            show_above_text=True,
            prefer_large_media=True,
        ),
    }
    await state.set_state(MemeStates.show)
    await edit_or_send_message(message_args, request_message)
    await state.set_data(
        {
            'meme_id': publish_result['id'],
        },
    )
