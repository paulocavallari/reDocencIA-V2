from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RegisterResponse, TokenResponse, UserCreate, UserLogin, UserRead
from app.security import (
    authenticate_supabase_credentials,
    create_access_token,
    create_supabase_auth_user,
    get_current_user,
    get_or_create_supabase_user,
    hash_password,
    is_supabase_admin_registration_enabled,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    auth_mode: str | None = None,
):
    email_in_use = db.query(User).filter(User.email == payload.email).first()
    if email_in_use:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado.")

    username_in_use = db.query(User).filter(User.username == payload.username).first()
    if username_in_use:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já cadastrado.")

    if auth_mode == "supabase":
        if not is_supabase_admin_registration_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SUPABASE_ASSISTED_SIGNUP_UNAVAILABLE",
            )

        supabase_user = create_supabase_auth_user(
            nome=payload.nome,
            email=payload.email,
            username=payload.username,
            password=payload.password,
        )
        return RegisterResponse(
            assisted_login=True,
            email=supabase_user.get("email") or payload.email,
        )

    user = User(
        nome=payload.nome,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.username)
    return RegisterResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    identifier = payload.username.strip()
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == identifier.lower(),
                func.lower(User.email) == identifier.lower(),
            )
        )
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        if "@" in identifier:
            supabase_user = authenticate_supabase_credentials(identifier, payload.password)
            if supabase_user is not None:
                resolved_user = get_or_create_supabase_user(db, supabase_user)
                if resolved_user is not None:
                    token = create_access_token(resolved_user.username)
                    return TokenResponse(access_token=token, user=UserRead.model_validate(resolved_user))

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.")

    token = create_access_token(user.username)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
