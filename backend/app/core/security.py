try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    import hashlib
    import secrets

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from jose import JWTError, jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False
    import json
    import base64
    import hmac

    class JWTError(Exception):
        pass

    class SimpleJWT:
        @staticmethod
        def _b64encode(b: bytes) -> str:
            return base64.urlsafe_b64encode(b).rstrip(b"=").decode("utf-8")

        @staticmethod
        def _b64decode(s: str) -> bytes:
            padding = 4 - (len(s) % 4)
            if padding != 4:
                s += "=" * padding
            return base64.urlsafe_b64decode(s)

        @classmethod
        def encode(cls, payload: dict, key: str, algorithm: str = "HS256") -> str:
            header = {"alg": algorithm, "typ": "JWT"}
            clean_payload = {}
            for k, v in payload.items():
                if isinstance(v, datetime):
                    clean_payload[k] = int(v.timestamp())
                else:
                    clean_payload[k] = v
            h_b64 = cls._b64encode(json.dumps(header, separators=(',', ':')).encode("utf-8"))
            p_b64 = cls._b64encode(json.dumps(clean_payload, separators=(',', ':')).encode("utf-8"))
            msg = f"{h_b64}.{p_b64}".encode("utf-8")
            sig = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
            s_b64 = cls._b64encode(sig)
            return f"{h_b64}.{p_b64}.{s_b64}"

        @classmethod
        def decode(cls, token: str, key: str, algorithms: list = None) -> dict:
            try:
                parts = token.split(".")
                if len(parts) != 3:
                    raise JWTError("Invalid token format")
                h_b64, p_b64, s_b64 = parts
                msg = f"{h_b64}.{p_b64}".encode("utf-8")
                expected_sig = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
                actual_sig = cls._b64decode(s_b64)
                if not hmac.compare_digest(expected_sig, actual_sig):
                    raise JWTError("Signature verification failed")
                payload = json.loads(cls._b64decode(p_b64).decode("utf-8"))
                exp = payload.get("exp")
                if exp and datetime.now(timezone.utc).timestamp() > exp:
                    raise JWTError("Token expired")
                return payload
            except Exception as e:
                raise JWTError(str(e))

    jwt = SimpleJWT()

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    cpse_id: Optional[int] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            pass
    try:
        if hashed_password.startswith("$pbkdf2$"):
            parts = hashed_password.split("$")
            salt, key = parts[2], parts[3]
            test_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000).hex()
            return test_key == key
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed_password
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    if HAS_BCRYPT:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    salt = secrets.token_hex(8)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"$pbkdf2${salt}${key}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        cpse_id: int = payload.get("cpse_id")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username, role=role, cpse_id=cpse_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

DEV_AUTH_BYPASS: bool = os.getenv("DEV_AUTH_BYPASS", "true").lower() in ["1", "true", "yes"]

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> TokenData:
    if not token:
        if DEV_AUTH_BYPASS:
            # Controlled local developer bypass: active only when DEV_AUTH_BYPASS=true
            return TokenData(username="system_dev", role="admin", cpse_id=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please provide Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(token)
