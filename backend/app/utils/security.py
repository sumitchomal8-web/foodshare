from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str)->bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub" : user_id,
        "role" : role,
        "exp" : expire,
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms = [ALGORITHM],
    )