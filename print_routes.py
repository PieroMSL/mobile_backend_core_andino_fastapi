from main import app
for route in app.routes:
    if hasattr(route, 'methods'):
        print(f"{','.join(route.methods)} {route.path}")
