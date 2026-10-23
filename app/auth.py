import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pwdlib import PasswordHash
from .db import db

hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

def secret():
    value = os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("Set JWT_SECRET to at least 32 random characters")
    return value

def token_for(user_id):
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc)+timedelta(hours=8), "iss": "az900-study"}, secret(), algorithm="HS256")

def current_user(auth=Depends(bearer)):
    try:
        if auth is None:
            raise ValueError()
        claims = jwt.decode(auth.credentials, secret(), algorithms=["HS256"], issuer="az900-study", options={"require":["exp","sub","iss"]})
        user_id = int(claims["sub"])
        with db() as c:
            if not c.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
                raise ValueError()
        return user_id
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Please sign in", headers={"WWW-Authenticate":"Bearer"})
