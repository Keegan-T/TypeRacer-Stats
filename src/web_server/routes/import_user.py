import asyncio

from aiohttp import web

from api.users import get_racer
from commands.account.download import run as run_import
from commands.locks import import_lock
from database.main import users
from utils.logging import log_error
from web_server.import_state import ImportState


async def trigger_import(request):
    """POST endpoint to trigger a user import."""
    data = await request.json()
    username = data.get("username")
    universe = data.get("universe", "play")

    if not username:
        return web.json_response({"error": "Username is required"}, status=400)

    # Validate username format
    if len(username) > 40:
        return web.json_response({"error": "Invalid username format"}, status=400)

    # Check if already imported
    user = users.get_user(username, universe)
    if user:
        return web.json_response({
            "status": "already_imported",
            "message": f"User {username} is already imported"
        })

    # Validate user exists and has races BEFORE starting import
    try:
        racer = await get_racer(username, universe)
        if not racer:
            return web.json_response({
                "status": "error",
                "error": f"User '{username}' does not exist"
            }, status=404)

        if racer.get("total_races", 0) == 0:
            return web.json_response({
                "status": "error",
                "error": f"User '{username}' has not completed any races in the {universe} universe"
            }, status=400)
    except Exception as e:
        return web.json_response({
            "status": "error",
            "error": f"Failed to validate user: {str(e)}"
        }, status=500)

    # Check if an import is in progress
    if import_lock.locked():
        current_import = ImportState.get_current_import()
        if current_import and current_import["username"] == username:
            return web.json_response({
                "status": "importing",
                "message": f"User {username} is currently being imported",
                "username": username,
                "elapsed": current_import["elapsed"]
            })
        else:
            return web.json_response({
                "status": "locked",
                "message": "Another user is currently being imported. Please try again later.",
                "current_user": current_import["username"] if current_import else None
            }, status=429)

    # Start the import in the background
    asyncio.create_task(_run_import(username, universe))

    return web.json_response({
        "status": "started",
        "message": f"Import started for {username}. This may take several minutes.",
        "username": username
    })


async def _run_import(username, universe):
    """Internal function to run the import with proper state tracking."""
    try:
        async with import_lock:
            ImportState.start_import(username, universe)
            try:
                await run_import(username=username, universe=universe)
            except Exception as e:
                log_error(f"Web import error for {username}", e)
                raise
            finally:
                ImportState.finish_import()
    except Exception as e:
        # Ensure state is cleared even if something goes wrong
        ImportState.finish_import()
        log_error(f"Web import failed for {username}", e)


async def import_status(request):
    """GET endpoint to check import status for a user."""
    username = request.match_info.get("username")
    universe = request.query.get("universe", "play")

    if not username:
        return web.json_response({"error": "Username is required"}, status=400)

    # Check if user is imported
    user = users.get_user(username, universe)
    if user:
        return web.json_response({
            "status": "imported",
            "message": f"User {username} is imported",
            "username": username
        })

    # Check if currently being imported
    current_import = ImportState.get_current_import()
    if current_import and current_import["username"] == username:
        return web.json_response({
            "status": "importing",
            "message": f"User {username} is currently being imported",
            "username": username,
            "elapsed": current_import["elapsed"]
        })

    # Check if another import is in progress
    if import_lock.locked() and current_import:
        return web.json_response({
            "status": "locked",
            "message": "Another user is currently being imported",
            "current_user": current_import["username"]
        })

    # Not imported and not being imported
    return web.json_response({
        "status": "not_imported",
        "message": f"User {username} has not been imported",
        "username": username
    })
