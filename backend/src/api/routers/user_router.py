from pydantic import Field
from fastapi import status, HTTPException, APIRouter, Depends, Response, Cookie
from typing import Optional
import uuid

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta


from pydantic import BaseModel
from ..auth import  auth

from src.broker.ContextBroker import ContextBroker

router = APIRouter()

class User(BaseModel):
    username: str

class LoginData(BaseModel):
    user: User
    expires: str 

class LoginResponse(BaseModel):
    status: str
    access_token: str
    token_type: str
    data: LoginData = Field(...)

def create_session():
    session_id = str(uuid.uuid4()) 
    return session_id