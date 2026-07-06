import hashlib
import hmac
import json
from time import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .config import BOT_TOKEN, ADMIN_IDS, INIT_DATA_MAX_AGE
from .database import get_db
from . import models


def validate_init_data(init_data: str):
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(parsed.get("auth_date", 0))
    if time() - auth_date > INIT_DATA_MAX_AGE:
        return None

    user_json = parsed.get("user")
    if not user_json:
        return None

    return json.loads(user_json)


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(401, "Откройте приложение через Telegram")

    tg_user = validate_init_data(authorization[4:])
    if not tg_user:
        raise HTTPException(401, "Недействительные данные Telegram")

    user = db.query(models.User).filter_by(tg_id=tg_user["id"]).first()
    if not user:
        user = models.User(
            tg_id=tg_user["id"],
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            is_admin=tg_user["id"] in ADMIN_IDS,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.is_admin = user.tg_id in ADMIN_IDS
        db.commit()

    return user


def get_admin_user(user: models.User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Доступ запрещён")
    return user