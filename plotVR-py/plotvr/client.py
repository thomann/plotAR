import json
import subprocess

import numpy as np
import requests

_host = "http://localhost:2908"

def plotvr(data, col, host="http://localhost:2908"):
    global _host
    _host = host
    payload = np.hstack((data[:,:3],col.reshape((-1,1))))
    # todo: remove NAs, center and scale...
    body = {'data': payload.tolist(),'speed': 0}
    # data_json = json.dumps(, allow_nan=False)
    requests.post(host, json=body)

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
