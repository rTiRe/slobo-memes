"""Module for responses from telegram via webhook."""
from asyncio import Task, create_task
from typing import Any

from aiogram.methods.base import TelegramMethod
from aiogram.types import Update
from fastapi.responses import ORJSONResponse
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.router import router
from src.background_tasks import background_tasks
from src.bot import get_bot, get_dp


@router.post('/bot')
async def bot_webhook(request: Request) -> JSONResponse:
    """Request a data from telegram.

    Args:
        request: Request - HTTP request.

    Returns:
        JSONResponse - JSON-formatted response class.
    """
    data = await request.json()
    update = Update(**data)
    dp = get_dp()
    task: Task[TelegramMethod[Any] | None] = create_task(
        dp.feed_webhook_update(get_bot(), update),
    )
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return ORJSONResponse({'message': 'OK'})
