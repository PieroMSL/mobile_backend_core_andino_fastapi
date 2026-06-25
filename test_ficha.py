import psycopg2
from app.database import SessionLocal
from app.repositories.rep_ficha import obtener_ficha

def test_ficha():
    # We will get IDs of Filoctetes and Aquiles
    conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
    cur = conn.cursor()
    cur.execute("SELECT id, nombres FROM clientes WHERE nombres LIKE '%Filoctetes%' OR nombres LIKE '%Aquiles%'")
    rows = cur.fetchall()
    
    db = SessionLocal()
    for row in rows:
        c_id, c_name = row
        data = obtener_ficha(db, str(c_id))
        print(f"[{c_name}] -> Riesgo final: {data['cliente']['calificacion_sbs']}")

if __name__ == '__main__':
    test_ficha()
