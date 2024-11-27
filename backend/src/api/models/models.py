from pydantic import BaseModel
from typing import Literal

class FeedbackInput(BaseModel):
    id_query: str
    feedback: Literal['up', 'down', None]

class LoginInput(BaseModel):
    username: str
    password: str

