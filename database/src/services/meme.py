import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select, func

from src.models import Meme, Rating, Saved
from src.schema.meme import Meme as MemeDict
from src.utils.inject_database import Provide, inject
from src.storage.database import get_db


class MemeService:
    @staticmethod
    @inject
    async def __get_mark_count(
        meme: Meme,
        mark: bool,
        session: AsyncSession = Provide(get_db),
    ) -> int:
        statement = select(func.count()).where(
            Rating.meme_id == meme.id,
            Rating.is_like == mark,
        ).select_from(Rating)
        return (await session.execute(statement)).scalar()

    @staticmethod
    @inject
    async def build_meme_response(
        meme: Meme,
        user_id: int,
        likes: Optional[int] = None,
        dislikes: Optional[int] = None,
        user_rating: Optional[bool] = None,
        is_saved: Optional[bool] = None,
        pagination: tuple[str | None, str | None] = (None, None),
        session: AsyncSession = Provide(get_db),
    ) -> MemeDict:
        if likes is None:
            likes = await MemeService.__get_mark_count(meme, True)
        if dislikes is None:
            dislikes = await MemeService.__get_mark_count(meme, False)
        if user_rating is None:
            user_rating = await session.execute(
                select(Rating).where(Rating.meme_id == meme.id, Rating.user_id == user_id)
            )
            user_rating: Rating = user_rating.scalars().first()
            user_rating = user_rating.is_like if user_rating is not None else None
        if is_saved is None:
            is_saved = await session.execute(
                select(Saved).where(Saved.meme_id == meme.id, Saved.user_id == user_id)
            )
            is_saved = is_saved.scalars().first() is not None
        return MemeDict(
            id=str(meme.id),
            creator_id=meme.creator_id,
            description=meme.description,
            image_url=meme.image_url,
            is_public=meme.is_public,
            likes=likes,
            dislikes=dislikes,
            user_rating=user_rating,
            is_saved=is_saved,
            pagination=pagination,
        )

    @staticmethod
    @inject
    async def add_meme(
        creator_id: int,
        description: str,
        image_url: str,
        session: AsyncSession = Provide(get_db),
    ) -> MemeDict:
        new_meme = Meme(
            creator_id=creator_id,
            description=description,
            image_url=image_url,
        )
        session.add(new_meme)
        await session.flush()
        new_save = Saved(
            meme_id=new_meme.id,
            user_id=creator_id,
        )
        session.add(new_save)
        await session.commit()
        return await MemeService.build_meme_response(
            new_meme,
            creator_id,
            likes=0,
            dislikes=0,
            user_rating=None,
            is_saved=True,
        )

    @staticmethod
    @inject
    async def get_random_meme(
        user_id: int,
        public_only: bool,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        if public_only:
            statement = select(Meme).where(Meme.is_public == True)
        else:
            statement = select(Meme).where(Saved.user_id == user_id).join(
                Saved,
                Saved.meme_id == Meme.id,
            )
        meme = await session.execute(statement.order_by(func.random()).limit(1))
        meme = meme.scalars().first()
        if not meme:
            return None
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def rate_meme(
        meme_id: uuid.UUID,
        user_id: int,
        new_rating: bool,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        meme = await session.get(Meme, meme_id)
        if not meme:
            return None
        statement = select(Rating).where(Rating.meme_id == meme_id, Rating.user_id == user_id)
        rating = await session.execute(statement)
        rating = rating.scalars().first()
        if rating:
            rating.is_like = new_rating
        else:
            rating = Rating(meme_id=meme_id, user_id=user_id, is_like=new_rating)
            session.add(rating)
        await session.commit()
        return await MemeService.build_meme_response(
            meme,
            user_id,
            user_rating=rating.is_like
        )

    @staticmethod
    @inject
    async def remove_rating(
        meme_id: uuid.UUID,
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        meme = await session.get(Meme, meme_id)
        if not meme:
            return None
        statement = select(Rating).where(Rating.meme_id == meme_id, Rating.user_id == user_id)
        rating = await session.execute(statement)
        rating = rating.scalars().first()
        if rating:
            await session.delete(rating)
            await session.commit()
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def add_to_saved(
        meme_id: uuid.UUID,
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> MemeDict:
        try:
            saved = Saved(meme_id=meme_id, user_id=user_id)
            session.add(saved)
            await session.commit()
        except IntegrityError:
            await session.rollback()
        meme = await session.get(Meme, meme_id)
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def remove_from_saved(
        meme_id: uuid.UUID,
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> MemeDict:
        statement = select(Saved).where(Saved.meme_id == meme_id, Saved.user_id == user_id)
        saved = await session.execute(statement)
        saved = saved.scalars().first()
        if saved:
            await session.delete(saved)
            await session.commit()
        meme = await session.get(Meme, meme_id)
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def change_visibility(
        meme_id: uuid.UUID,
        user_id: int,
        new_visibility: bool,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        statement = select(Meme).where(Meme.id == meme_id, Meme.creator_id == user_id)
        meme = await session.execute(statement)
        meme = meme.scalars().first()
        if not meme:
            return None
        meme.is_public = new_visibility
        await session.commit()
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def get_saved_meme_neighbors(
        user_id: int,
        saved_id: str,
        session: AsyncSession = Provide(get_db),
    ) -> tuple[str | None, str | None]:
        next_statement = (
            select(Saved.id)
            .where(Saved.user_id == user_id, Saved.id > saved_id)
            .order_by(Saved.id.asc())
            .limit(1)
        )
        prev_statement = (
            select(Saved.id)
            .where(Saved.user_id == user_id, Saved.id < saved_id)
            .order_by(Saved.id.desc())
            .limit(1)
        )
        next_result = (await session.execute(next_statement)).scalar()
        prev_result = (await session.execute(prev_statement)).scalar()
        if isinstance(next_result, uuid.UUID):
            next_result = str(next_result)
        if isinstance(prev_result, uuid.UUID):
            prev_result = str(prev_result)
        return (prev_result, next_result)

    @staticmethod
    @inject
    async def get_saved_meme_by_id(
        user_id: int,
        saved_id: str,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        statement = (
            select(Meme)
            .join(Saved, Saved.meme_id == Meme.id)
            .where(Saved.id == saved_id)
        )
        result = await session.execute(statement)
        meme = result.scalars().first()
        if not meme:
            return None
        neightbours = await MemeService.get_saved_meme_neighbors(
            user_id,
            saved_id,
        )
        return await MemeService.build_meme_response(meme, user_id, pagination=neightbours)

    @staticmethod
    @inject
    async def get_first_saved_meme(
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        statement = (
            select(Saved.id).where(
                Saved.user_id == user_id
            ).order_by(
                Saved.id.asc()
            ).limit(1)
        )
        result = (await session.execute(statement)).scalar()
        if result:
            return await MemeService.get_saved_meme_by_id(user_id, result)

    @staticmethod
    @inject
    async def popular_meme(
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> Optional[MemeDict]:
        likes_statement = select(
            Rating.meme_id, func.count(Rating.id).label('like_count'),
        ).where(
            Rating.is_like.is_(True),
        ).group_by(
            Rating.meme_id,
        ).subquery()
        statement = select(Meme).join(
            likes_statement, Meme.id == likes_statement.c.meme_id,
        ).order_by(
            likes_statement.c.like_count.desc(),
        ).limit(1)
        meme = (await session.execute(statement)).scalars().first()
        if not meme:
            return None
        return await MemeService.build_meme_response(meme, user_id)

    @staticmethod
    @inject
    async def delete_meme(
        meme_id: uuid.UUID,
        user_id: int,
        session: AsyncSession = Provide(get_db),
    ) -> bool:
        statement = select(Meme).where(Meme.id == meme_id, Meme.creator_id == user_id)
        meme = await session.execute(statement)
        meme = meme.scalars().first()
        if not meme:
            return False
        await session.delete(meme)
        await session.commit()
        return True
