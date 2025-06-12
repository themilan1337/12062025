from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.crud import UserDAO
from auth.execptions import (InvalidTokenException, TokenExpiredException,
                             UserNotFoundException, raise_http_exception)
from auth.models import User
from auth.utils import decode_access_token
from database import get_async_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    try:
        email = decode_access_token(token)
        db_user = await UserDAO.get_user_by_email_or_raise(email, db)
        return User(
            id=db_user.id,
            email=db_user.email
        )
    except (
        InvalidTokenException,
        TokenExpiredException,
        UserNotFoundException
    ) as e:
        raise_http_exception(e)
