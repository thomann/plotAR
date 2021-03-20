import json
from pathlib import Path
import logging

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.log import enable_pretty_logging

import pyqrcode

from . import __version__

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

_external_url = None
_base_path = '/'
_token = None
_IP = None
def external_url(client_url, file='index.html'):
    from urllib.parse import urlparse, urljoin
    o = urlparse(client_url)
    if o.hostname not in ["localhost","127.0.0.1","0.0.0.0",]:
        # client is using a host that is probably better
        # than what we would get out of get_ip, so use that
        # this is also important in Reverse Proxy-Settings, eg. on binderhub
        return urljoin(client_url, 'index.html')
    global _external_url, _IP, _token
    if _external_url is None:
        if _IP is None:
            _IP = get_ip()
        tok = f'?token={_token}' if _token is not None else ''
        port = f':{_PORT}' if _PORT is not None else ''
        _external_url = f'http://{_IP}{port}{_base_path}{file}{tok}'
    return _external_url

class QRHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        # TODO check these arguments - they could be malicious!
        client_url = self.get_argument('location')
        file = self.get_argument('file', 'index.html')
        print(client_url)
        url = external_url(client_url, file=file)
        result = { 'qr': pyqrcode.QRCode(url).code, 'url': url }
        return self.write(json.dumps(result)+"\n")

class DataHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        return self.write(json.dumps(DATA)+"\n")

class StatusHandler(tornado.web.RequestHandler):
    """Renders QR Codes"""
    def get(self):
        self.set_header("X-Plotvr-Version", __version__)
        return self.write(json.dumps(status())+"\n")

from . import export

class USDHandler(tornado.web.RequestHandler):
    """Renders the USDZ format used on iOS"""
    def get(self):
        result = export.data2usdz(DATA)

        self.write(result)
        self.set_header('Content-Type', 'model/vnd.usd+zip')

class GLTFHandler(tornado.web.RequestHandler):
    """Renders the GLTF format used on Android"""
    def get(self):
        result = export.data2gltf(DATA)

        self.write(result)
        self.set_header('Content-Type', 'model/gltf+json')

class OBJHandler(tornado.web.RequestHandler):
    """Renders the USDA format usably on iOS"""
    def get(self):
        result = export.data2obj(DATA)

        self.set_header('Content-Type', 'text/plain')
        self.write(result)

def defaultData():
    import numpy as np
    from .client import plotvr
    data = np.random.normal(size=(100,3))
    col = np.random.randint(4, size=100)
    return plotvr(data, col, return_data=True, host=None, name='Gaussian Sample', push_data=False )

# The list of currently connected clients
CLIENTS = []
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
    for i,c in enumerate(CLIENTS):
        print(f"Sending to client {i}")
        c.write_message(message)

def broadcast_status():
    broadcast(status())


def status():
    dev, contr, focus = 0, 0, 0
    for c in CLIENTS:
        dev += int(c.is_device)
        contr += int(c.is_controller)
        focus += int(c.has_focus)
    status = {'numDevices': dev, 'numControllers': contr, 'numFocus': focus}
    md = DATA['metadata'] if DATA is not None and 'metadata' in DATA else {}
    return {'status': status, 'metadata': md}


class PlotVRWebSocketHandler(tornado.websocket.WebSocketHandler):
    """ The chat implemententation, all data send to server is json, all responses are json """

    def open(self):
        print("Client connecting /ws")
        self.is_device = False
        self.is_controller = False
        self.has_focus = False
        CLIENTS.append(self)

    def on_message(self, message):
        print(f"got message: {message}")
        try:
            body = json.loads(message)
        except:
            return self.write_message('Format error')
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
        if 'shutdown' in body and body['shutdown']:
            _app.stop()
        broadcast(body)

    def on_close(self):
        CLIENTS.remove(self)
        broadcast_status()

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
    (r"/data.gltf", GLTFHandler),
    (r"/data.obj", OBJHandler),
    (r"/ws", PlotVRWebSocketHandler),
    (r"/index.html(.*)", tornado.web.StaticFileHandler, {"path": html('index.html')}),
    (r"/keyboard.html(.*)", tornado.web.StaticFileHandler, {"path": html('keyboard.html')}),
    (r"/js/(.*)", tornado.web.StaticFileHandler, {"path": html('js')}),
    (r"/textures/(.*)", tornado.web.StaticFileHandler, {"path": html('textures')})
]
#_app = tornado.web.Application(_mappings)

def start_server(port=2908):
    print(f"Welcome to PlotVR server on port {port}")
    global _PORT, _app
    _app = tornado.web.Application(_mappings)
    _PORT = port
    _app.listen(port)
    tornado.ioloop.IOLoop.instance().start()
    print("hello")

def get_ip():
    """Get the publicly visible IP address."""
    # see https://stackoverflow.com/a/28950776
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    start_server()
