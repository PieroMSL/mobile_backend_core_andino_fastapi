import psycopg2

def audit_50():
    conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            c.id, c.nombres, c.apellidos, 
            cd.tipo_gestion, cd.prioridad, cd.score_prioridad,
            cb.calificacion_sbs AS buro_sbs, 
            sc.estado AS sol_estado
        FROM clientes c
        JOIN cartera_diaria cd ON cd.cliente_id = c.id
        LEFT JOIN (SELECT cliente_id, calificacion_sbs, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM consultas_buro) cb ON cb.cliente_id = c.id AND cb.rn=1
        LEFT JOIN (SELECT cliente_id, estado, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM solicitudes_credito) sc ON sc.cliente_id = c.id AND sc.rn=1
        ORDER BY c.created_at ASC
    """)
    rows = cur.fetchall()
    
    print("| # | Cliente | Tipo Gestión | Prioridad Original | Buró SBS | Estado Solicitud | Riesgo Calculado (Actual) | Color Original | Color Actual (Riesgo) | Mismatch |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    
    for i, r in enumerate(rows):
        c_id, nombres, apellidos, tipo_gestion, prioridad, score, buro, sol_est = r
        cliente_nombre = f"{nombres} {apellidos}"
        
        # Calculate Riesgo as implemented in my previous fix
        if sol_est == 'rechazado':
            riesgo = "RECHAZADO"
        elif buro:
            riesgo = buro
        else:
            riesgo = "NORMAL"
            
        color_actual = "Verde"
        r_up = riesgo.upper()
        if r_up == 'CPP': color_actual = 'Ámbar'
        elif r_up in ('DEFICIENTE', 'DUDOSO', 'RECHAZADO'): color_actual = 'Rojo'
        elif r_up == 'PERDIDA': color_actual = 'Gris'
        
        color_original = "Verde"
        if prioridad.lower() == 'alta': color_original = 'Rojo'
        elif prioridad.lower() == 'media': color_original = 'Ámbar'
        
        mismatch = "SI" if color_original != color_actual else ""
        print(f"| {i+1} | {cliente_nombre} | {tipo_gestion} | {prioridad} | {buro or 'NULL'} | {sol_est or 'NULL'} | {riesgo} | {color_original} | {color_actual} | {mismatch} |")

if __name__ == '__main__':
    audit_50()
