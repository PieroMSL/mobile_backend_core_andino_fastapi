from app.core.cfg_database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
res = db.execute(text("SELECT dni_cliente, pin_hash FROM usuarios_cliente LIMIT 1")).fetchone()
print(f"User: {res}")
