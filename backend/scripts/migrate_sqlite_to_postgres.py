from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import DATABASE_URL, engine, is_postgres_url
from app.models import CurriculumData, SavedPlan, Setting, User


SOURCE_DB_PATH = Path(__file__).resolve().parents[1] / "data.db"
BATCH_SIZE = 500


def build_source_session_factory() -> sessionmaker:
    from sqlalchemy import create_engine

    source_engine = create_engine(
        f"sqlite:///{SOURCE_DB_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=source_engine)


def serialize(instance, model):
    return {column.name: getattr(instance, column.name) for column in model.__table__.columns}


def yield_batches(source_session: Session, model):
    rows = source_session.query(model).order_by(model.id.asc()).yield_per(BATCH_SIZE)
    batch = []
    for row in rows:
        batch.append(serialize(row, model))
        if len(batch) >= BATCH_SIZE:
            yield batch
            batch = []
    if batch:
        yield batch


def count_rows(session: Session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def reset_sequence(target_session: Session, table_name: str) -> None:
    target_session.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
        )
    )


def main() -> None:
    if not SOURCE_DB_PATH.exists():
        raise SystemExit(f"SQLite source database not found: {SOURCE_DB_PATH}")

    if not is_postgres_url(DATABASE_URL):
        raise SystemExit("DATABASE_URL must point to Supabase/Postgres before running this migration.")

    SourceSession = build_source_session_factory()
    source_session = SourceSession()
    target_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    try:
        print("Source counts:")
        for model in [User, Setting, CurriculumData, SavedPlan]:
            print(f"- {model.__tablename__}: {count_rows(source_session, model)}")

        target_session.query(SavedPlan).delete(synchronize_session=False)
        target_session.query(CurriculumData).delete(synchronize_session=False)
        target_session.query(Setting).delete(synchronize_session=False)
        target_session.query(User).delete(synchronize_session=False)
        target_session.flush()

        for model in [User, Setting, CurriculumData, SavedPlan]:
            for batch in yield_batches(source_session, model):
                target_session.execute(model.__table__.insert(), batch)

        for table_name in ["users", "settings", "curriculum_data", "saved_plans"]:
            reset_sequence(target_session, table_name)

        target_session.commit()

        print("Target counts:")
        for model in [User, Setting, CurriculumData, SavedPlan]:
            print(f"- {model.__tablename__}: {count_rows(target_session, model)}")
    except Exception:
        target_session.rollback()
        raise
    finally:
        source_session.close()
        target_session.close()


if __name__ == "__main__":
    main()