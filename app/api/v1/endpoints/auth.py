from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError

from app.db.session import get_db
from app.crud import get_user_by_username, create_user
from app.schemas import Token, UserCreate, UserResponse
from app.core.security import (
    create_token_pair,
    decode_token,
)
from app.core.hashing import Hasher

import logging

logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


class RefreshTokenRequest(BaseModel):
    refresh_token: str


def _build_token_response(username: str) -> Token:
    token_pair = create_token_pair(username)
    return Token(**token_pair)


@router.post("/login", response_model=Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Any = Depends(get_db)):
    logger.debug(f"Login attempt for user: {form_data.username}")
    
    # Explicitly check for empty credentials (though OAuth2PasswordRequestForm should handle it)
    if not form_data.username or not form_data.password:
        logger.warning(f"Empty credentials provided for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )
        
    try:
        user = get_user_by_username(db, form_data.username)
        if not user or not Hasher.verify_password(form_data.password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Successful login for user: {form_data.username}")
        return _build_token_response(user.username)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login for user {form_data.username}: {str(e)}", exc_info=True)
        # Re-raise to be caught by global exception handler, but we've logged it
        raise


@router.post("/refresh", response_model=Token)
def refresh_access_token(payload: RefreshTokenRequest, db: Any = Depends(get_db)):
    if not payload.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required",
        )

    try:
        token_payload = decode_token(payload.refresh_token)
        if str(token_payload.get("token_type") or "") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = token_payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = get_user_by_username(db, username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info("Refreshing token for user: %s", username)
        return _build_token_response(user.username)
    except JWTError as exc:
        logger.warning("Invalid refresh token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error refreshing token: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Any = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 创建用户
    new_user = create_user(db=db, user=user)
    logger.info(f"New user {new_user.username} registered")
    
    return new_user
