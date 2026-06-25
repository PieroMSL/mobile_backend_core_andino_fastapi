import psycopg2
import json

def audit():
    conn = psycopg2.connect("dbname=bd_core_mobile user=postgres password=123456 host=localhost port=5432")
    cur = conn.cursor()
    
    # Get all 30 cases (prospectos)
    cur.execute("""
        SELECT 
            c.id, c.nombres, c.apellidos, 
            cb.calificacion_sbs AS buro_sbs, 
            sc.estado AS sol_estado, 
            cd.prioridad AS cartera_prioridad
        FROM clientes c
        LEFT JOIN (SELECT cliente_id, calificacion_sbs, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM consultas_buro) cb ON cb.cliente_id = c.id AND cb.rn=1
        LEFT JOIN (SELECT cliente_id, estado, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY created_at DESC) as rn FROM solicitudes_credito) sc ON sc.cliente_id = c.id AND sc.rn=1
        LEFT JOIN (SELECT cliente_id, prioridad, ROW_NUMBER() OVER(PARTITION BY cliente_id ORDER BY fecha_asignacion DESC) as rn FROM cartera_diaria) cd ON cd.cliente_id = c.id AND cd.rn=1
        WHERE c.es_prospecto = true
        ORDER BY c.created_at ASC
    """)
    rows = cur.fetchall()
    
    results = []
    
    for i, r in enumerate(rows):
        c_id, nombres, apellidos, buro, sol_est, prioridad = r
        cliente_nombre = f"{nombres} {apellidos}"
        
        if sol_est == 'rechazado':
            ficha_sbs = "RECHAZADO"
        elif buro:
            ficha_sbs = buro
        else:
            ficha_sbs = "NORMAL"
            
        results.append({
            "caso": i+1,
            "cliente": cliente_nombre,
            "buro_db": buro,
            "comite_db": sol_est,
            "cartera_prioridad": prioridad,
            "ficha_sbs": ficha_sbs
        })
        
    with open("audit_30.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Auditoria completa guardada en audit_30.json")

if __name__ == '__main__':
    audit()
