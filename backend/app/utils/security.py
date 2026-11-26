"""
app/utils/security.py  — Person A
Spec Section 6.1: Password hashing and JWT helpers.

Functions:
  hash_password(password: str) -> str
  verify_password(plain_password: str, password_hash: str) -> bool
  create_access_token(user_id: str, role: str) -> str
  decode_access_token(token: str) -> dict   raises JWTError if invalid/expired
"""
from datetime import datetime, timezone, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_ctx.verify(plain_password, password_hash)


def create_access_token(user_id: str, role: str) -> str:
    """
    Returns a signed HS256 JWT.
    Payload: { sub: <user_id str>, role: <role>, exp: <UTC timestamp> }
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT.
    Returns the payload dict.
    Raises jose.JWTError if the token is invalid or expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
