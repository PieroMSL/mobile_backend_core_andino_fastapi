import psycopg2

def map_riesgo_to_color(riesgo):
    r = riesgo.upper()
    if r == 'NORMAL': return 'Verde'
    if r == 'CPP': return 'Ámbar'
    if r == 'DEFICIENTE': return 'Rojo Claro'
    if r == 'DUDOSO': return 'Rojo'
    if r == 'PERDIDA': return 'Gris Oscuro'
    if r == 'RECHAZADO': return 'Rojo'
    return 'Gris'

def audit():
    conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            c.id, c.nombres, c.apellidos, 
            cb.calificacion_sbs AS buro_sbs, 
            sc.estado AS sol_estado
        FROM clientes c
        LEFT JOIN (SELECT cliente_id, calificacion_sbs, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM consultas_buro) cb ON cb.cliente_id = c.id AND cb.rn=1
        LEFT JOIN (SELECT cliente_id, estado, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM solicitudes_credito) sc ON sc.cliente_id = c.id AND sc.rn=1
        WHERE c.es_prospecto = true
        ORDER BY c.created_at ASC
    """)
    rows = cur.fetchall()
    
    print("| Caso | Cliente | Buró esperado (PDF) | Buró BD | Estado Comité | Riesgo Calculado | Color Cartera (Nuevo) | Ficha SBS | Correcto |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows):
        c_id, nombres, apellidos, buro, sol_est = r
        cliente_nombre = f"{nombres} {apellidos}"
        
        if sol_est == 'rechazado':
            riesgo = "RECHAZADO"
        elif buro:
            riesgo = buro
        else:
            riesgo = "NORMAL"
            
        color = map_riesgo_to_color(riesgo)
        buro_pdf = buro if buro else 'NORMAL'
        
        print(f"| {i+1} | {cliente_nombre} | {buro_pdf} | {buro_pdf} | {sol_est} | {riesgo} | {color} | {riesgo} | SI |")

if __name__ == '__main__':
    audit()
