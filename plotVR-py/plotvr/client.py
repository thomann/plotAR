import json
import subprocess
import os
import logging

import numpy as np
import requests
import time

logger = logging.getLogger(__name__)

_host = None #: PlotHost
DEFAULT_SERVER = 'http://localhost:2908'


def plotvr(data, col=None, size=None, type='p', lines=None, label=None,
           name=None, description=None, speed=None, auto_scale=True,
           digits=5, host=None, return_data=False, push_data=True):
    # TODO assert compatibility checks
    n = data.shape[0]
    for i in [col, size, lines, label]:
        assert i is None or i.shape == (n,), f"Parameters need to have same length: {i} has shape {i.shape} but would need {(n,)}"
    if auto_scale:
        # have all variables scaled to [-1,1]
        ranges = data.max(0) - data.min(0)
        ranges[ranges == 0] = 1
        data = (data - data.min(0)) / ranges * 2 - 1
    if col is None:
        payload = data[:,:3]
    else:
        payload = np.hstack((data[:,:3],col.reshape((-1,1))))
    # todo: remove NAs, center and scale...
    body = {'data': payload.tolist(),'speed': 0, 'protocolVersion': '0.3.0'}
    if col is not None: body['col'] = col.tolist()
    if size is not None: body['size'] = size.tolist()
    if type is not None: body['type'] = type
    if label is not None: body['label'] = label.tolist()
    if speed is not None: body['speed'] = speed
    metadata = { 'n': n, 'created': time.ctime() }
    metadata['name'] = name or "Dataset"
    if description is not None: metadata['description'] = description
    body['metadata'] = metadata
    # data_json = json.dumps(, allow_nan=False)
    if push_data:
        plot_host = get_host(host)
        plot_host.post(json=body)
    if return_data:
        return body


def controller(width="100%", height="200px"):
    url = get_host().external_url("keyboard.html")
    try:
        from IPython.display import IFrame
        return IFrame(url, width=width, height=height)
    except ImportError:
        return url


def viewer(width="100%", height="400px"):
    url = get_host().external_url("index.html")
    try:
        from IPython.display import IFrame
        return IFrame(url, width=width, height=height)
    except ImportError:
        return url


def get_host(host=None):
    global _host
    if host is not None:
        return PlotHost(host)
    if _host is None:
        # actual detection code
        jpy = my_jupyter_server()
        if jpy is not None:
            hub_prefix = os.getenv("JUPYTERHUB_SERVICE_PREFIX")
            if hub_prefix is None:
                ext = jpy['url'] + "plotvr/"
            else:
                # on jupyter-/binderhub we don't know the external hostname,
                # so we use an absolute URL
                ext = hub_prefix+"plotvr/"
            _host = PlotHost(jpy['url']+"plotvr/", external_url=ext, params=jpy['params'], headers=jpy['headers'])
        else:
            _host = PlotHost(DEFAULT_SERVER)
    return _host


class PlotHost:
    def __init__(self, url: str, external_url: str = None, params='', headers={}):
        self.url = url
        if url is None or len(url) == 0 or not isinstance(url, str):
            raise ValueError("URL must be not None and a non-empty string.")
        if self.url[-1] != '/':
            self.url += '/'
        if external_url is None:
            external_url = self.url
        self._external_url = external_url
        self.params = "?"+params
        self.headers = headers
    def internal_url(self, path):
        '''Shows the URL that is '''
        return self.url + path #+ self.params
    def external_url(self, path):
        return self._external_url + path + self.params
    def post(self, json):
        requests.post(self.internal_url(""), json=json, headers=self.headers)
    def __repr__(self):
        return f"PlotHost({self.url})"
    def _repr_html_(self):
        return f"PlotVR at <a href='{self.url}'>{self.url}</a>"

def my_jupyter_server(verbose=False, jupyter_parent_pid=None):
    try:
        from notebook import notebookapp
    except ImportError:
        return None
    servers = list(notebookapp.list_running_servers())
    if not len(servers):
        if verbose:
            import warnings
            warnings.warn("no running jupyter server found")
        return None
    server_pid = os.getenv('JPY_PARENT_PID', jupyter_parent_pid)
    if server_pid is None:
        if len(servers) > 1:
            pass
        jpy = servers[0]
    else:
        for s in servers:
            if str(s['pid']) == server_pid:
                jpy = s
                break
        else:
            # no matching pid found...
            if verbose:
                print('no matching jupyter server found!')
            jpy = servers[0]
    if jpy is None:
        return None
    return dict(url=jpy['url'],
                params="token="+jpy['token'],
                headers={'Authorization': 'token ' + jpy['token']},
                )

def start_server_process(port: int = 2908, showServerURL=True):
    """Start Server in another process.

    Parameters
    ----------
    port
        The port on which to run the server (default is 2908).

    Returns
    -------
    Completed Process of `subprocess.run`.

    """
    import sys
    python = sys.executable
    # or os.__file__.split("lib/")[0],"bin","python") ?
    
    proc = subprocess.Popen([python, '-m', 'plotvr.server', str(port)])

    if showServerURL:
        url = _host+'/index.html'
        try:
            response = requests.get(_host+"/qr.json")
            response.raise_for_status()
            url = response.json()['url']
        except Exception as ex:
            print("Problem getting external IP: ", ex)
            pass
        try:
            from IPython.display import display, SVG, HTML
            import pyqrcode
            from io import BytesIO
            io = BytesIO()
            pyqrcode.QRCode(url).svg(io, scale=4)
            img = io.getvalue().decode('utf-8')
            display(HTML(f'Visit: <a href="{url}">{url}</a>'))
            display(SVG(img))
        except ImportError:
            print(f"Visit: {url}")

    return proc
