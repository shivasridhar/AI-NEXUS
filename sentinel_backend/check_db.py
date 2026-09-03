from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.append(os.getcwd())
from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

result = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'canonical_events';"))
columns = result.fetchall()
if not columns:
    print("Table canonical_events does not exist!")
else:
    print("canonical_events columns:")
    for c in columns:
        print(f"- {c[0]}: {c[1]}")
