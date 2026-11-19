import time
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Simple in-memory sliding window rate limiter
IP_REQUEST_HISTORY: Dict[str, List[float]] = {}
GENERAL_RATE_LIMIT = 200  # requests per minute per IP
LOGIN_RATE_LIMIT = 15     # login attempts per minute per IP
WINDOW_SIZE = 60          # 1 minute

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (allows necessary CDNs for fonts, QR, PDF)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https://fonts.googleapis.com https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:* https://*.vercel.app https://api.groq.com;"
        )
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Determine limit based on endpoint
        limit = GENERAL_RATE_LIMIT
        path = request.url.path
        if "/auth/login" in path:
            limit = LOGIN_RATE_LIMIT

        timestamps = IP_REQUEST_HISTORY.get(client_ip, [])
        # Filter timestamps within current window
        timestamps = [t for t in timestamps if now - t < WINDOW_SIZE]
        
        if len(timestamps) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests. Please slow down.",
                    "status": 429
                }
            )

        timestamps.append(now)
        IP_REQUEST_HISTORY[client_ip] = timestamps

        return await call_next(request)
