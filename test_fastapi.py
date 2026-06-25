import requests

print('=== HACIENDO LOGIN ===')
res = requests.post('http://127.0.0.1:8003/cliente/login', json={
    'numero_documento': '73431102',
    'password': 'admin'
})
print('Status Login:', res.status_code)
if res.status_code != 200:
    print('Login falló:', res.text)
    exit(1)

token = res.json()['access_token']
print('Token JWT:', token[:20] + '...')

print('=== GET /cliente/cuentas ===')
res2 = requests.get('http://127.0.0.1:8003/cliente/cuentas', headers={
    'Authorization': f'Bearer {token}'
})
print('Status Cuentas:', res2.status_code)
print('Response Cuentas:', res2.text)
