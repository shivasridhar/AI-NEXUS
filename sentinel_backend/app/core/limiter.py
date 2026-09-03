from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.api.dependencies import decode_and_verify_token

def get_rate_limit_key(request: Request) -> str:
    # Try to retrieve user ID from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            user_id = decode_and_verify_token(token)
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    # Fallback to client IP
    return get_remote_address(request)

# Define Limiter with a general default limit of 100/minute
limiter = Limiter(key_func=get_rate_limit_key, default_limits=["100/minute"])
