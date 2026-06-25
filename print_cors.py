from main import app
from fastapi.middleware.cors import CORSMiddleware
for m in app.user_middleware:
    if m.cls == CORSMiddleware:
        print(f"CORS allow_origins: {m.kwargs.get('allow_origins')}")
