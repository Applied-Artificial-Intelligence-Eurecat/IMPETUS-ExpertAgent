from jwt import ExpiredSignatureError, InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.security import OAuth2PasswordBearer
from fastapi import Cookie
from datetime import datetime, timedelta, timezone

import jwt

from src.api.config.config import settings

from datetime import timedelta

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/token")
bearer_scheme = HTTPBearer()


JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 60 minutes


async def is_bearer_token_authorised(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_token():
    expiration =  datetime.now(timezone.utc)  + timedelta(days=365 * 10)  # Token válido por 10 años
    token = jwt.encode({"exp": expiration}, JWT_SECRET, algorithm="HS256")
    return token

def get_session(session_id: str = Cookie(None)):
    if session_id is None:
        raise HTTPException(status_code=403, detail="Session ID missing")
    return session_id

def verify_token(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return token

def create_access_token(*, data: dict, expires_delta: timedelta):
    token = jwt.encode(data, JWT_SECRET)
    return token