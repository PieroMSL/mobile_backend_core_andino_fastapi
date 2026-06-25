import psycopg2
conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
cur = conn.cursor()
cur.execute("SELECT c.nombres, c.apellidos, cd.tipo_gestion, cd.prioridad FROM cartera_diaria cd JOIN clientes c ON c.id=cd.cliente_id WHERE cd.tipo_gestion='RECUPERACION_MORA' ORDER BY c.nombres")
for row in cur.fetchall():
    print(f"{row[0]} {row[1]} | {row[2]} | {row[3]}")
