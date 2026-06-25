import requests
import json

def test():
    # Login
    r = requests.post('http://127.0.0.1:8000/auth/login', json={"codigo_empleado": "0001", "password": "1234"})
    if r.status_code != 200:
        print("Login failed")
        return
    token = r.json()['access_token']
    
    # Get Cartera
    r = requests.get('http://127.0.0.1:8000/cartera', headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        print("Cartera failed")
        return
    data = r.json()
    
    for item in data[:5]:
        print(item.get('cliente_nombre'), item.get('riesgo'), item.get('prioridad'))

if __name__ == '__main__':
    test()
