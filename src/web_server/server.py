import aiohttp_jinja2
import jinja2
from aiohttp import web
from discord.ext import commands

from config import SOURCE_DIR, ROOT_DIR
from utils.logging import log
from web_server.middleware import error_middleware
from web_server.routes.race import race_page


class WebServer(commands.Cog):
    """Cog to manage the aiohttp web server and its background tasks."""

    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application(middlewares=[error_middleware])
        self.runner = None
        self.site = None

        # Routes
        self.app.router.add_get("/race/{username}/{number}", race_page)

        # Templates
        aiohttp_jinja2.setup(self.app, loader=jinja2.FileSystemLoader(str(SOURCE_DIR / "web_server" / "templates")))

        # Static files
        self.app.router.add_static("/static", path=str(SOURCE_DIR / "web_server" / "static"), name="static")
        self.app.router.add_static("/assets", path=str(ROOT_DIR / "assets"), name="assets")

        self.bot.loop.create_task(self.start_web_server())

    async def cog_unload(self):
        await self.stop_web_server()

    async def start_web_server(self):
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host="0.0.0.0", port=80)
        await self.site.start()

        log("Web server started on port 80")

    async def stop_web_server(self):
        """Stop the web server."""
        if self.runner:
            await self.runner.cleanup()

        log("Web server stopped")


async def setup(bot):
    await bot.add_cog(WebServer(bot))
