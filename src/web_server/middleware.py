import time
from collections import defaultdict

import aiohttp_jinja2
from aiohttp import web

from utils.logging import log, log_error


class RateLimiter:
    def __init__(self, rate=60, per=60):
        """
        rate: number of requests allowed
        per: time period in seconds
        """
        self.rate = rate
        self.per = per
        self.clients = defaultdict(list)

    def is_allowed(self, client_id):
        now = time.time()
        # Remove timestamps older than the time window
        self.clients[client_id] = [
            timestamp for timestamp in self.clients[client_id]
            if now - timestamp < self.per
        ]

        # Check if under rate limit
        if len(self.clients[client_id]) < self.rate:
            self.clients[client_id].append(now)
            return True
        return False


rate_limiter = RateLimiter(rate=15, per=60)


@web.middleware
async def request_logging_middleware(request, handler):
    start_time = time.time()
    client_ip = request.headers.get('X-Real-IP', request.remote)

    try:
        response = await handler(request)
        status = response.status
    except web.HTTPException as e:
        status = e.status
        raise
    except Exception:
        status = 500
        raise
    finally:
        duration = (time.time() - start_time) * 1000

        # Skip logging for static assets and status checks
        if not request.path.startswith('/static') and not request.path.startswith('/assets'):
            log_message = f"**Web Request:** `{request.method} {request.path}` | IP: `{client_ip}` | Status: `{status}` | `{duration:.0f}ms`"
            log(log_message)

    return response


@web.middleware
async def security_headers_middleware(request, handler):
    response = await handler(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
    return response


@web.middleware
async def rate_limit_middleware(request, handler):
    # Exempt import endpoints from rate limiting
    if request.path.startswith('/import'):
        return await handler(request)

    # Get client IP (check X-Real-IP header for reverse proxy setups)
    client_ip = request.headers.get('X-Real-IP', request.remote)

    if not rate_limiter.is_allowed(client_ip):
        return web.Response(
            status=429,
            text="Rate limit exceeded. Please try again later.",
            headers={'Retry-After': '60'}
        )

    return await handler(request)


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)

    except web.HTTPNotFound:
        return aiohttp_jinja2.render_template(
            template_name="error.html",
            request=request,
            context={
                "status": 404,
                "error": "Page Not Found",
                "message": "This page doesn't exist.",
            },
            status=404,
        )

    except ValueError as e:
        return aiohttp_jinja2.render_template(
            "error.html",
            request=request,
            context={
                "status": 500,
                "error": f"Server Error",
                "message": str(e),
            },
            status=404,
        )

    except Exception as e:
        log_error("WebServer Error", e)

        return aiohttp_jinja2.render_template(
            template_name="error.html",
            request=request,
            context={
                "status": 500,
                "error": "Internal Server Error",
            },
            status=500,
        )
