import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from app.models.base import Base

@pytest.fixture(scope="session")
def postgres_engine():
    """
    Spins up a single Postgres testcontainer for the entire test session.
    """
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        yield engine
        engine.dispose()

@pytest.fixture(scope="function")
def postgres_db(postgres_engine):
    """
    Creates the schema before each test and drops it after,
    guaranteeing a completely clean DB per test.
    """
    # Create all tables
    Base.metadata.create_all(bind=postgres_engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    db = SessionLocal()
    
    yield db
    
    db.close()
    # Drop all tables after the test to ensure hermeticity
    Base.metadata.drop_all(bind=postgres_engine)
