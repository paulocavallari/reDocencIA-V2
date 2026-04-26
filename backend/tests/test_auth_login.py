from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import User
from app.routers.auth import router as auth_router
from app.security import hash_password


def _build_auth_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_router)

    def _override_get_db():
        db = SessionTesting()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionTesting


def _seed_user(session_factory):
    with session_factory() as session:
        session.add(
            User(
                nome="Professor Teste",
                email="professor@escola.com",
                username="professor.teste",
                password_hash=hash_password("Senha@123"),
                is_admin=False,
            )
        )
        session.commit()


def test_login_accepts_username_and_email_identifiers():
    app, session_factory = _build_auth_client()
    _seed_user(session_factory)
    client = TestClient(app)

    by_username = client.post(
        "/api/auth/login",
        json={"username": "professor.teste", "password": "Senha@123"},
    )
    by_email = client.post(
        "/api/auth/login",
        json={"username": "professor@escola.com", "password": "Senha@123"},
    )

    assert by_username.status_code == 200
    assert by_email.status_code == 200
    assert by_username.json()["user"]["username"] == "professor.teste"
    assert by_email.json()["user"]["email"] == "professor@escola.com"


def test_login_falls_back_to_supabase_for_email_when_local_password_fails(monkeypatch):
    app, session_factory = _build_auth_client()
    _seed_user(session_factory)
    client = TestClient(app)

    from app.routers import auth as auth_router

    def fake_authenticate_supabase_credentials(email, password):
        if email == "professor@escola.com" and password == "SenhaNova@123":
            return {
                "email": "professor@escola.com",
                "user_metadata": {"nome": "Professor Teste", "username": "professor.teste"},
                "app_metadata": {"role": "authenticated"},
            }
        return None

    monkeypatch.setattr(auth_router, "authenticate_supabase_credentials", fake_authenticate_supabase_credentials)

    response = client.post(
        "/api/auth/login",
        json={"username": "professor@escola.com", "password": "SenhaNova@123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "professor@escola.com"
