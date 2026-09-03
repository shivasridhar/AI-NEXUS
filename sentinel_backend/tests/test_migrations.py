import pytest
from alembic.config import Config
from alembic import command
import os

@pytest.mark.pg
def test_alembic_migrations(postgres_engine):
    """
    Test that the Alembic migration chain runs cleanly against a real Postgres instance.
    This guarantees that the models and migrations are fully in sync and compatible 
    with Postgres data types like JSONB.
    """
    
    # We need to set the sqlalchemy url in the environment so alembic picks it up
    db_url = postgres_engine.url.render_as_string(hide_password=False)
    os.environ["ALEMBIC_DATABASE_URL"] = db_url

    # Initialize alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    # Run the migrations up to head
    command.upgrade(alembic_cfg, "head")
    
    # Run the migrations down to base
    command.downgrade(alembic_cfg, "base")
