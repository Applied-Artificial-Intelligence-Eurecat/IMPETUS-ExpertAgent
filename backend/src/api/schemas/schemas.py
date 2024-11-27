from pydantic import BaseModel
from typing import Literal
from typing import List, Any, Optional


class ThumbsFeedback(BaseModel):
    thumbs: Literal['up', 'down']

class Login(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True


class LLMQuery(BaseModel):
    query_message: str

class Answer(BaseModel):
    status: str
    content: str
    query_id: str
    documents: List[Any]
    datetime: Optional[str] = None