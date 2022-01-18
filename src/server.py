import asyncio
import hashlib
import json
import logging
import os
import pathlib
import socket
import ssl
import time
import urllib.parse
import uuid

import aiofiles
import aiohttp
import aiohttp_jinja2
import jinja2
import soco
from aiohttp import web
from soco.music_services import MusicService

# SET UP LOGGING
logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)-25s: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# GET PROJECT ROOT FOLDER
PROJECT_ROOT = pathlib.Path(__file__).parent

# GET IP ADDRESS
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
HOST_IP_ADDRESS = s.getsockname()[0]
s.close()
logger.info(f"HOST_IP_ADDRESS: {HOST_IP_ADDRESS}")


class Server:
    def __init__(self, host, port, http, debug):
        self.app = None
        self.tasks = []
        self.host = host
        self.port = port
        self.http = http
        self.protocol = self._get_protocol()
        if debug:
            logger.info("Server starting in debug mode.")
            logging.getLogger().setLevel(logging.DEBUG)

    def start(self):
        """
        Starts the web server.
        """
        self.app = self._init_app()
        logger.info(f"Server starting on {self.protocol}://{self.host}:{self.port}")
        if self.http:
            web.run_app(self.app, host=self.host, port=self.port)
            return
        else:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain("domain_srv.crt", "domain_srv.key")
            web.run_app(
                self.app, host=self.host, port=self.port, ssl_context=ssl_context
            )

    async def _init_app(self):
        """
        Initializes the web application.
        """
        app = web.Application()
        app["websockets"] = {}
        app.on_shutdown.append(self._shutdown_app)
        aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader("src", "templates"))
        app.router.add_get("/", self.index)
        app.router.add_get("/image_proxy", self.image_proxy)
        app.router.add_static("/static/", path=PROJECT_ROOT / "static", name="static")
        return app

    async def _shutdown_app(self, app):
        """
        Called when the app shut downs. Perform clean-up.
        """
        for ws in app["websockets"].values():
            await ws.close()
        app["websockets"].clear()

    def _get_protocol(self):
        if self.http:
            return "http"
        else:
            return "https"

    def _get_page(self, request):
        """
        Returns the index page.
        """
        context = {}
        return aiohttp_jinja2.render_template("index.html", request, context)

    async def index(self, request):
        """
        Handles returning the index.html and then client web socket connections.
        """
        ws_current = web.WebSocketResponse()
        ws_ready = ws_current.can_prepare(request)
        logger.debug(ws_ready)
        if not ws_ready.ok:
            return self._get_page(request)
        await ws_current.prepare(request)

        ws_identifier = str(uuid.uuid4())[:8]
        request.app["websockets"][ws_identifier] = ws_current
        logger.info(f"Client {ws_identifier} connected.")

        while True:
            msg = await ws_current.receive()
            if msg.type != aiohttp.WSMsgType.TEXT:
                break
            await self._handle_message(request, ws_identifier, msg)
            await asyncio.sleep(0.01)
        self._remove_ws(request, ws_identifier)
        return ws_current

    async def image_proxy(self, request):
        """
        Handles /image_proxy requests.
        Requests always come in in form /image_proxy?url=image_url
        First, there's some clean-up done on the image_proxy folder, then
        Image_url is downloaded if hasn't been already, and then returned
        This ensures all image_proxy are served from the same domain (better browser compatibility)
        """
        params = request.rel_url.query
        # get image_proxy folder path
        dp = os.path.join(".", "image_proxy")
        if not os.path.exists(dp):
            os.mkdir(dp)

        # Do some clean-up of the image_proxy folder
        for f in os.listdir(dp):
            fp = os.path.join(dp, f)
            file_last_accessed = int(os.path.getatime(fp))
            now = int(time.time())
            if now - file_last_accessed > 8 * 60 * 60:
                logger.info(f"Images clean-up removing file: {fp}")
                os.remove(fp)

        # Now focus on the requested file
        async with aiohttp.ClientSession() as session:
            url = params["url"]
            url_hash = hashlib.sha1(url.encode("UTF-8")).hexdigest()
            fp = os.path.join(dp, url_hash + ".jpeg")
            if not os.path.exists(fp):
                async with session.get(url) as resp:
                    if resp.status == 200:
                        fp = os.path.join(dp, url_hash + ".jpeg")
                        async with aiofiles.open(fp, mode="wb+") as f:
                            await f.write(await resp.read())
                            await f.close()
            resp = web.FileResponse(fp)
            return resp

    def _remove_ws(self, request, ws_identifier):
        """
        Removes web socket from list stored by server
        """
        logger.info(f"Client {ws_identifier} disconnected.")
        del request.app["websockets"][ws_identifier]

    async def _handle_message(self, request, ws_identifier, msg):
        """
        Handles messages coming in from web socket connections.
        Routes actions after checking data in msg is compliant.
        """
        if msg.type != aiohttp.WSMsgType.TEXT:
            return
        data_dict = json.loads(msg.data)
        logger.info(f"Msg from client {ws_identifier}: {data_dict}")
        if "action" not in data_dict:
            return
        action = data_dict["action"]
        if action == "refresh":
            if "sonos_name" not in data_dict:
                return
            await self._send_sonos(request, ws_identifier, data_dict["sonos_name"])

    async def _send_sonos(self, request, ws_identifier, sonos_name):
        """
        Sends Sonos info to web socket.
        """
        try:
            logger.info(f"Responding to client {ws_identifier}")
            try:
                # get Sonos device and general info
                device = soco.discovery.by_name(sonos_name)
                transport_info = device.get_current_transport_info()
                logger.debug(f"transport info: {transport_info}")
                track_info = device.get_current_track_info()
                logger.debug(f"track info: {track_info}")
                media_info = device.get_current_media_info()
                logger.debug(f"media info: {media_info}")
            except Exception:
                raise
            # start getting the info we're interested in
            transport = transport_info["current_transport_state"]
            img_src = track_info["album_art"]
            if img_src != "":
                title = track_info["title"]
                artist = track_info["artist"]
                album = track_info["album"]
            # if there's no img_src in track info, we might be playing a radio station
            else:
                channel = media_info["channel"]
                tunein = MusicService("TuneIn")
                # search Tunein for value of channel
                results = tunein.search(category="stations", term=channel)
                if len(results) > 0:
                    result = results[0]
                    img_src = result.metadata["stream_metadata"].metadata["logo"]
                title = channel
                artist = ""
                album = ""
            # encode artwork URL ready for use as parameter
            img_src = urllib.parse.quote(img_src)
            # point artwork URL back to our server for serving/downloading
            img_src = f"{self.protocol}://{HOST_IP_ADDRESS}:{self.port}/image_proxy?url={img_src}"
            # Make context dict
            context = {
                "transport": transport,
                "title": title,
                "artist": artist,
                "album": album,
                "img_src": img_src,
            }
            html = aiohttp_jinja2.render_string("widget_sonos.html", request, context)
            print(html)
            logger.debug(f"Sending to client {ws_identifier}: {html}")
            # send HTML
            ws = request.app["websockets"][ws_identifier]
            await ws.send_json({"html": html})
        except ConnectionResetError:
            self._remove_ws(request, ws_identifier)
            return
