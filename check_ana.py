import psycopg2

conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
cur = conn.cursor()
cur.execute("SELECT c.nombres, c.apellidos, cb.calificacion_sbs FROM clientes c LEFT JOIN consultas_buro cb ON cb.cliente_id = c.id WHERE c.nombres = 'Ana' AND c.apellidos LIKE 'Lazo%'")
print(cur.fetchall())
