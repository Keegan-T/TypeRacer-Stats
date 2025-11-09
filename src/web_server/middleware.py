import aiohttp_jinja2
from aiohttp import web

from utils.logging import log_error


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
