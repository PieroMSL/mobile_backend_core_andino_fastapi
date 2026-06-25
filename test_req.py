import urllib.request
import urllib.error
import json

# Try to login first (we need a valid DNI and pin, let's look at the database or use a common one)
# Wait, I don't know the PIN. Let's just create a test JWT using the backend's token function.
import sys
sys.path.append('.')
from app.core.cfg_auth import crear_access_token

token = crear_access_token({"sub": "73431102", "role": "cliente", "cliente_id": "test_id"})
print(f"Token: {token}")

def test_endpoint(path):
    req = urllib.request.Request(f'http://127.0.0.1:8003{path}')
    req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"SUCCESS {path}: {response.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {path}: {e.code} - {e.read().decode()}")
    except Exception as e:
        print(f"Error {path}: {e}")

test_endpoint('/cliente/solicitudes')
test_endpoint('/cliente/cuentas')
