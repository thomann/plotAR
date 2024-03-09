import json
from pathlib import Path
import logging

import click
import ssl
import uuid
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.log import enable_pretty_logging

import pyqrcode

from .export import data2usd_ascii, data2usdz, data2gltf, data2obj

from . import __version__

ALLOWED_ORIGINS = ["https://plotar.glitch.me", "https://thomann.github.io", ]

handler = logging.StreamHandler() # FileHandler(log_file_filename)
enable_pretty_logging()
for i in ["tornado.access","tornado.application","tornado.general"]:
    logger = logging.getLogger(i)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MainHandler(tornado.web.RequestHandler):
    """ Renders the index file """

    def get(self):
        return self.write(json.dumps(DATA)+"\n")

    def post(self):
        global DATA
        DATA = json.loads(self.request.body)
        self.broadcastRefresh()
        return self.write("OK\n")

    def broadcastRefresh(self):
        broadcast({'key': 'reload_data'})

    def check_xsrf_cookie(self):
        """Bypass xsrf cookie checks when token-authenticated"""
        # TODO check whether we really are alrady authenticated - else
        #  this opens some security problems!
        print("check_xsrf_cookie")
        return

_external_base_url = None
_base_path = '/'
_token = None
_IP = None
def external_url(client_url, file='index.html', request: tornado.httputil.HTTPServerRequest = None):
    global _external_base_url, _IP, _token
    from urllib.parse import urlparse, urljoin
    o = urlparse(client_url)
    tok = f'?token={_token}' if _token is not None else ''
    if o.hostname not in ["localhost","127.0.0.1","0.0.0.0",]:
        # client is using a host that is probably better
        # than what we would get out of get_ip, so use that
        # this is also important in Reverse Proxy-Settings, eg. on binderhub
        return urljoin(client_url, file+tok)
    if _external_base_url is None:
        if _IP is None:
            _IP = get_ip()
        port = f':{_PORT}' if _PORT is not None else ''
        protocol = 'http'
        if request is not None and request.protocol == 'https':
            protocol = 'https'
        _external_base_url = f'{protocol}://{_IP}{port}{_base_path}'
    return _external_base_url+file+tok

class QRHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        # TODO check these arguments - they could be malicious!
        client_url = self.get_argument('location')
        file = self.get_argument('file', 'index.html')
        print(client_url)
        url = external_url(client_url, file=file, request=self.request)
        result = { 'qr': pyqrcode.QRCode(url).code, 'url': url }
        return self.write(json.dumps(result)+"\n")

class DataHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        return self.write(json.dumps(DATA)+"\n")

class StatusHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        self.set_header("X-PlotAR-Version", __version__)
        return self.write(json.dumps(status())+"\n")

from . import export

class USDHandler(tornado.web.RequestHandler):
    """Renders the USDZ format used on iOS"""
    def get(self):
        if self.request.path.endswith(".usda"):
            result, _assets = data2usd_ascii(DATA)

            self.write(result)
            self.set_header('Content-Type', 'text/plain')
            return
        result = data2usdz(DATA)

        self.write(result)
        self.set_header('Content-Type', 'model/vnd.usd+zip')

class GLTFHandler(tornado.web.RequestHandler):
    """Renders the GLTF format used on Android"""
    def get(self):
        result = data2gltf(DATA).format_gltf()

        self.write(result)
        self.set_header('Content-Type', 'model/gltf+json')

        # TODO Check whether this makes sense in general
        # something like this is needed to host the vr.html on a https-server
        # and connect from that one to this server
        self.set_header('Access-Control-Allow-Origin', '*')
    
    def options(self):
        self.set_status(204)
        self.finish()

class GLBHandler(tornado.web.RequestHandler):
    """Renders the GLTF format used on Android"""
    def get(self):
        result = data2gltf(DATA).format_glb()

        self.write(result)
        self.set_header('Content-Type', 'model/gltf-binary')

class OBJHandler(tornado.web.RequestHandler):
    """Renders the USDA format usably on iOS"""
    def get(self):
        result = data2obj(DATA)

        self.set_header('Content-Type', 'text/plain')
        self.write(result)

def defaultData():
    import numpy as np
    from .client import plotar
    data = np.random.normal(size=(100,3))
    col = np.random.randint(4, size=100)
    return plotar(data, col, return_data=True, host=None, name='Gaussian Sample', push_data=False ).data

# The list of currently connected clients
CLIENTS = {}
DATA = {}
try:
    DATA = defaultData()
except Exception as e:
    logger.info("Could not load data.json: ", e)
_PORT = None

def broadcast(message):
    if not isinstance(message, str):
        message = json.dumps(message)
    print(f"Sending message: {message}")
    for i,c in CLIENTS.items():
        print(f"Sending to client {i}")
        c.write_message(message)

def broadcast_status():
    broadcast(status())


def status():
    dev, contr, focus = 0, 0, 0
    for c in CLIENTS.values():
        dev += int(c.is_device)
        contr += int(c.is_controller)
        focus += int(c.has_focus)
    status = {'numDevices': dev, 'numControllers': contr, 'numFocus': focus}
    md = DATA['metadata'] if DATA is not None and 'metadata' in DATA else {}
    return {'status': status, 'metadata': md}


class PlotARWebSocketHandler(tornado.websocket.WebSocketHandler):
    """ The chat implemententation, all data send to server is json, all responses are json """

    def open(self):
        print("Client connecting /ws")
        self.is_device = False
        self.is_controller = False
        self.has_focus = False
        self.id = str(uuid.uuid4())
        CLIENTS[self.id] = self

    def on_message(self, message):
        print(f"got message: {message}")
        try:
            body = json.loads(message)
        except:
            return self.write_message('Format error')
        body['sender_id'] = str(self.id)
        sendStatus = False
        if 'focus' in body:
            self.has_focus = bool(body['focus'])
            sendStatus = True
        if 'controller' in body:
            self.is_controller = bool(body['controller'])
            sendStatus = True
        if 'device' in body:
            self.is_device = bool(body['device'])
            sendStatus = True
        if sendStatus:
            broadcast_status()
            return
        if 'whoami' in body:
            self.write_message(json.dumps({ 'whoami': {'id': str(self.id)}}))
            return
        if 'to' in body:
            to = CLIENTS.get(body['to'])
            if to is None:
                logging.warning(f"Client {body['to']} not found!")
            else:
                to.write_message(body)
            return
        if 'shutdown' in body and body['shutdown']:
            _app.stop()
        broadcast(body)

    def on_close(self):
        del CLIENTS[self.id]
        broadcast_status()
    
    def check_origin(self, origin):
        super_origin = super().check_origin(origin)
        if super_origin or origin in ALLOWED_ORIGINS or \
                origin.startswith("https://localhost:") or origin.startswith("http://localhost:"):
            return True
        print(f"Not allowed origin for {origin}")
    def check_xsrf_cookie(self):
        """Bypass xsrf cookie checks when token-authenticated"""
        # TODO check whether we really are alrady authenticated - else
        # this opens some security problems?
        print("check_xsrf_cookie for websocket")
        return

def html(x):
    pth = Path(__file__).parent / 'html' / x
    ret = str(pth)
    return ret


_mappings = [
    (r"/", MainHandler),
    (r"/data.json", DataHandler),
    (r"/status.json", StatusHandler),
    (r"/qr.json", QRHandler),
    (r"/data.usdz", USDHandler),
    (r"/data.usda", USDHandler),
    (r"/data.gltf", GLTFHandler),
    (r"/data.glb", GLBHandler),
    (r"/data.obj", OBJHandler),
    (r"/ws", PlotARWebSocketHandler),
    (r"/index.html(.*)", tornado.web.StaticFileHandler, {"path": html('index.html')}),
    (r"/model", tornado.web.RedirectHandler, {"url": "/model.html"}),
    (r"/vr", tornado.web.RedirectHandler, {"url": "/vr.html"}),
    (r"/keyboard", tornado.web.RedirectHandler, {"url": "/keyboard.html"}),
    (r"/model.html(.*)", tornado.web.StaticFileHandler, {"path": html('model.html')}),
    (r"/vr.html(.*)", tornado.web.StaticFileHandler, {"path": html('vr.html')}),
    (r"/favicon.ico(.*)", tornado.web.StaticFileHandler, {"path": html('favicon.ico')}),
    (r"/keyboard.html(.*)", tornado.web.StaticFileHandler, {"path": html('keyboard.html')}),
    (r"/js/(.*)", tornado.web.StaticFileHandler, {"path": html('js')}),
    (r"/textures/(.*)", tornado.web.StaticFileHandler, {"path": html('textures')}),
]
#_app = tornado.web.Application(_mappings)

@click.command()
@click.option('-p', '--port', default=2908, help="Port to listen on")
# @click.option('-h', '--host', default=, help="format: gltf usdz usda obj. Default is to take extension of out or else gltf")
@click.option('-d', '--data', default=None, type=click.File(), help="Data.json file to open initially")
@click.option('--debug/--no-debug', default=False, help="Start Server in Debug mode (autoreload)")
@click.option('--ssl-prefix', default=None, type=click.Path(), help="If specified a HTTPS server is started and this path is used with extensions .crt and .key to get certificate and private key")
def start_server(port=2908, data=None, debug=False, ssl_prefix=None):
    """Start the plotar server"""
    _start_server(port=port, data=data, debug=debug, ssl_prefix=ssl_prefix)


def _start_server(port=2908, data=None, debug=False, ssl_prefix=None):
    print(f"Welcome to PlotAR")
    global _PORT, _app, DATA
    if data:
        global DATA
        DATA = json.load(data)

    ssl_ctx = None
    if ssl_prefix is not None:
        ssl_prefix = Path(ssl_prefix)
        if str(ssl_prefix)[-1] == "." and not ssl_prefix.with_suffix('.crt').exists() and not ssl_prefix.with_suffix('.key').exists():
            ssl_prefix = Path(str(ssl_prefix)[:-1])
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(ssl_prefix.with_suffix('.crt'), ssl_prefix.with_suffix('.key'))

    _app = tornado.web.Application(_mappings, debug=debug, ssl_options=ssl_ctx)
    _PORT = port
    http_server = tornado.httpserver.HTTPServer(_app, ssl_options=ssl_ctx)
    http_server.listen(port)
    ip = get_ip()
    print(f"Open http://{ip}:{port}/keyboard.html")
    tornado.ioloop.IOLoop.instance().start()

    print("hello")


def get_ip():
    """Get the publicly visible IP address."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
    # see https://stackoverflow.com/a/28950776
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    start_server()
