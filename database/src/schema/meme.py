from typing import TypedDict, Union


class Meme(TypedDict):
    id: str
    creator_id: int
    description: str
    image_url: str
    is_public: bool
    likes: int
    dislikes: int
    user_rating: Union[bool, None]
    is_saved: bool


class AddMeme(TypedDict):
    creator_id: int
    description: str
    image_url: str


class RandomMeme(TypedDict):
    user_id: int
    public_only: bool