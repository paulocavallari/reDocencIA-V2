from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


@lru_cache
def load_env_file_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_config_value(key: str, default: str | None = None) -> str | None:
    def sanitize(raw: str) -> str:
        return (
            raw.strip()
            .replace("\\r", "")
            .replace("\\n", "")
            .replace("\r", "")
            .replace("\n", "")
        )

    value = os.getenv(key)
    if value is not None:
        value = sanitize(value)
        if value:
            return value

    file_value = load_env_file_values().get(key)
    if file_value is not None:
        file_value = sanitize(file_value)
        if file_value:
            return file_value

    return default


SECRET_KEY = get_config_value("REDOCENCIA_SECRET_KEY", "redocencia-dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
SUPABASE_URL = get_config_value("SUPABASE_URL")
SUPABASE_ANON_KEY = get_config_value("SUPABASE_ANON_KEY") or get_config_value("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SERVICE_ROLE_KEY = get_config_value("SUPABASE_SERVICE_ROLE_KEY")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_user_from_local_token(token: str, db: Session) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        return None

    if not username:
        return None
    return db.query(User).filter(User.username == username).first()


def fetch_supabase_user(token: str) -> dict | None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None

    try:
        response = httpx.get(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
            timeout=10.0,
        )
    except httpx.HTTPError:
        return None

    if not response.is_success:
        return None
    return response.json()


def authenticate_supabase_credentials(email: str, password: str) -> dict | None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None

    try:
        response = httpx.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "password": password,
            },
            timeout=10.0,
        )
    except httpx.HTTPError:
        return None

    if not response.is_success:
        return None

    payload = response.json()
    if not isinstance(payload, dict):
        return None
    user = payload.get("user")
    return user if isinstance(user, dict) else None


def is_supabase_admin_registration_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def extract_supabase_error_message(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        for key in ("msg", "message", "error_description", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def create_supabase_auth_user(nome: str, email: str, username: str, password: str) -> dict:
    if not is_supabase_admin_registration_enabled():
        raise RuntimeError("Supabase admin registration is not configured.")

    try:
        response = httpx.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users",
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            },
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "nome": nome,
                    "full_name": nome,
                    "username": username,
                },
            },
            timeout=10.0,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível comunicar com o Supabase Auth.",
        ) from error

    detail = extract_supabase_error_message(response)
    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="O Supabase limitou temporariamente novos cadastros. Tente novamente em alguns minutos.",
        )

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        lowered_detail = (detail or "").lower()
        if "already" in lowered_detail and ("registered" in lowered_detail or "exists" in lowered_detail):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado.")
        if "invalid email" in lowered_detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail or "Não foi possível concluir o cadastro no Supabase.",
        )

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail or "O Supabase Auth recusou o cadastro.",
        )

    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def build_unique_username(db: Session, preferred_username: str) -> str:
    base_username = re.sub(r"[^a-zA-Z0-9_.-]+", "", preferred_username or "usuario")[:40] or "usuario"
    candidate = base_username
    suffix = 1
    while db.query(User).filter(User.username == candidate).first() is not None:
        suffix_text = f"-{suffix}"
        candidate = f"{base_username[: max(1, 40 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return candidate


def get_or_create_supabase_user(db: Session, supabase_user: dict) -> User | None:
    email = supabase_user.get("email")
    if not email:
        return None

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user is not None:
        return existing_user

    metadata = supabase_user.get("user_metadata") or {}
    app_metadata = supabase_user.get("app_metadata") or {}
    username = build_unique_username(db, metadata.get("username") or email.split("@", 1)[0])
    nome = metadata.get("nome") or metadata.get("full_name") or username

    user = User(
        nome=nome,
        email=email,
        username=username,
        password_hash=hash_password(secrets.token_urlsafe(24)),
        is_admin=app_metadata.get("role") == "admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente.")

    token = credentials.credentials

    local_user = get_user_from_local_token(token, db)
    if local_user is not None:
        return local_user

    supabase_user = fetch_supabase_user(token)
    if supabase_user is not None:
        user = get_or_create_supabase_user(db, supabase_user)
        if user is not None:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao admin.")
    return current_user
