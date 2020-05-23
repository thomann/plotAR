import json
import subprocess

import numpy as np
import requests
import time

_host = "http://localhost:2908"

def plotvr(data, col=None, size=None, type='p', lines=None, label=None,
           name=None, description=None, speed=None, auto_scale=True,
           digits=5, host="http://localhost:2908", return_data=False):
    global _host
    _host = host
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
    if host is not None:
        requests.post(host, json=body)
    if return_data:
        return body

def controller(width="100%", height="200px"):
    url = _host + "/keyboard.html"
    try:
        from IPython.display import IFrame
        return IFrame(url, width=width, height=height)
    except ImportError:
        return url

def viewer(width="100%", height="400px"):
    url = _host + "/index.html"
    try:
        from IPython.display import IFrame
        return IFrame(url, width=width, height=height)
    except ImportError:
        return url

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
