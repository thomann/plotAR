import json
import subprocess
import os
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import time

logger = logging.getLogger(__name__)

_host = None #: PlotHost
_last_plot = None
DEFAULT_SERVER = 'http://localhost:2908'

class PlotAR(object):
    def __init__(self, data, host=None):
        self.data = data
        self.plot_host = host
        global _last_plot
        _last_plot = self
    def _repr_html_(self):
        if self.plot_host is None:
            self.plot_host = get_host()
            if self.plot_host is None:
                return f"<pre>{self.data.get('metadata')}</pre>"
        # we set wsUrl empty to start that one "detached" so no keyboard no automatic updates from plots in other cells
        return f"<iframe width='100%' height='250px' src='{self.plot_host.external_url('keyboard.html')}&wsUrl='>"
    def write(self, filename, format='json', overwrite=False):
        p = Path(filename)
        if isinstance(format, str):
            format = [format]
        for f in format:
            if f == 'json':
                with open(filename, 'w') as file:
                    print(f"Writing JSON to {filename}")
                    json.dump(self.data, file)
            else:
                from .export import export
                export(self.data, filename, [f])

def _mk_val(df, val, n=None):
    if val is None:
        return None
    elif val is not None and isinstance(val, str) and val in df.columns:
        return df[val].values
    elif isinstance(val, float):
        if n is None:
            n = df.shape[0]
        return np.zeros((n,)) + val
    else:
        return np.array(val)


def plotar(data, col=None, size=None, *, xyz=None, type='p', lines=None, label=None,
           axis_names=None, col_labels=None,
           name=None, description=None, speed=None, auto_scale=True,
           digits=5, host=None, return_data=True, push_data=True):
    # TODO assert compatibility checks
    n = data.shape[0]
    df = None
    if isinstance(data, pd.DataFrame):
        df = data
        if xyz is not None:
            assert len(xyz)==3
            data = df[xyz].values
            axis_names = axis_names or xyz
        else:
            data = df.iloc[:,0:3].values
            axis_names = axis_names or df.columns[xyz].tolist()

    col   = _mk_val(df, col, n)
    size  = _mk_val(df, size, n)
    lines = _mk_val(df, lines, n)
    label = _mk_val(df, label, n)

    for i in [col, size, lines, label]:
        assert i is None or i.shape == (n,), f"Parameters need to have same length: {i} has shape {i.shape} but would need {(n,)}"
    if auto_scale:
        # have all variables scaled to [-1,1]
        if auto_scale == 1:
            data = scale(data, axis=(0,1))
        else:
            data = scale(data)
        if size is not None:
            # scale the sizes between 0.5 and 1.5:
            size = scale(size.reshape((-1, 1)))[:,0] + 1.5
    if col is not None and col.dtype == np.dtype('O'):
        x = pd.Series(col, dtype='category')
        col = x.cat.codes.values
        col_labels = x.cat.categories.values.tolist()
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
    if axis_names is not None: body['axis_names'] = axis_names
    if col_labels is not None: body['col_labels'] = col_labels

    metadata = { 'n': n, 'created': time.ctime() }
    metadata['name'] = name or "Dataset"
    if description is not None: metadata['description'] = description
    body['metadata'] = metadata
    # data_json = json.dumps(, allow_nan=False)
    plot_host = None
    if push_data:
        plot_host = get_host(host)
        plot_host.post(json=body)
    if return_data:
        return PlotAR(body, host=plot_host)

def linear(*args, group=None, width=1, push_data=True, return_data=True, **kwargs):
    body = plotar(*args, **kwargs, push_data=False, return_data=True).data
    data = body.get('data',[])
    col = body.get('col', [0] * len(data))
    group = group or col
    df = pd.DataFrame(dict(col=col, group=group))
    body['lines'] = [
        dict(col=int(c), width=width, points=d.index.to_list())
        for (c, g), d in df.groupby(['col', 'group'])
    ]
    plot_host = None
    if push_data:
        plot_host = get_host(kwargs.get('host'))
        plot_host.post(json=body)
    if return_data:
        return PlotAR(body, host=plot_host)

def animate(data, xyz, *, animation_frame, group=None,
        duration_seconds=30, tstart=None, time_codes_per_second=None, time_values=None,
        auto_scale=True, push_data=True, return_data=True, **kwargs):
    if group is None:
        group = pd.Series(1)
    if not isinstance(group, list):
        group = [group]
    data = pd.DataFrame(data).sort_values(group + [animation_frame])
    assert not any( data[group+[animation_frame]].duplicated() ), f'data has to be unique w.r.t. animation_frame ({animation_frame}) and group ({group})'
    if auto_scale:
        # have all variables scaled to [-1,1]
        data[xyz] = scale(data[xyz].values)
        # TODO also normalise scale
        # if size is not None:
        #     # scale the sizes between 0.5 and 1.5:
        #     size = scale(size.reshape((-1, 1)))[:,0] + 1.5
    if tstart is None:
        # take first of group
        data_start = data.groupby(group).first().reset_index()
    else:
        data_start = data.loc[data[animation_frame] == tstart]
    body = plotar(data=data_start, xyz=xyz, **kwargs, push_data=False, return_data=True).data
    animation_data = [
        df[xyz].values.tolist()
        for _, df in data.groupby(group)
    ]

    time_values = _mk_val(data, animation_frame)
    time_labels = None
    try:
        time_values = pd.to_datetime(time_values, errors='raise')
        time_labels = [[0.0,time_values.min()], [1.0,time_values.max()]]
        range = 1.0 if time_values.max() == time_values.min() else (time_values.max()-time_values.min())
        time_values = (time_values - time_values.min()) / range
    except:
        if pd.api.types.is_numeric_dtype(time_values):
            range = time_values.max()-time_values.min()
            time_values = (time_values - time_values.min()) / (range if range >0 else 1)
    time_values = pd.Series(time_values)
    # Now we assume that time_values actually is 
    time_labels = [ [t,str(l)] for t,l in time_labels ] if time_labels is not None else []
    if time_codes_per_second is None:
        time_range = (time_values.max()-time_values.min())
        time_codes_per_second = time_range / duration_seconds
    time_values = [
        time_values.loc[ind].values.tolist()
        for _,ind in data.reset_index(drop=True).groupby(group).groups.items()
    ]

    body['animation'] = dict(data=animation_data, time_labels=time_labels, time_values=time_values,
                         time_codes_per_second=time_codes_per_second)
    
    plot_host = None
    if push_data:
        plot_host = get_host(kwargs.get('host'))
        plot_host.post(json=body)
    if return_data:
        return PlotAR(body, host=plot_host)

def surfacevr(data, col=None, x=None, y=None, surfacecolor=None,
           name=None, description=None, speed=None, auto_scale=True,
           digits=5, host=None, return_data=True, push_data=True):
    # TODO assert compatibility checks
    n,m = data.shape
    for i in [col]:
        assert i is None or i.shape == data.shape, f"Parameters need to have same shape: {i} has shape {i.shape} but would need {data.shape}"
    if auto_scale:
        # have the data scaled to [-1,1]
        a,b = data.min(),data.max()
        if a <= 0 <= b:
            # keep the 0 at 0 and scale around that
            mx = max(-a,b)
            mx = mx or 1 # set to 1 if 0
            data = data / mx
        else:
            data = scale(data, axis=(0,1))
        x = scale(x)
        y = scale(y)
    # TODO: remove NAs
    body = {'surface': {'data':data.tolist(), 'col':col, 'shape': (n,m)},'speed': 0, 'protocolVersion': '0.3.0'}
    if x is not None:
        body['surface']['x'] = np.array(x).tolist()
    if y is not None:
        body['surface']['y'] = np.array(y).tolist()
    if surfacecolor is not None: body['surface']['surfacecolor'] = surfacecolor
    if speed is not None: body['speed'] = speed
    metadata = { 'n': n, 'm': m, 'created': time.ctime() }
    metadata['name'] = name or f"Dataset {n}x{m}"
    if description is not None: metadata['description'] = description
    body['metadata'] = metadata
    plot_host = None
    if push_data:
        plot_host = get_host(host)
        plot_host.post(json=body)
    if return_data:
        return PlotAR(body, host=plot_host)


def scale(data, axis=(0,)):
    if data is None:
        return None
    if min(data.shape) == 0:
        return data
    ranges = np.array(data.max(axis) - data.min(axis))
    ranges[ranges == 0] = 1
    data = (data - data.min((0,))) / ranges * 2 - 1
    return data


def controller(width="100%", height="400px"):
    url = get_host().external_url("keyboard.html")
    if is_in_jupyter():
        try:
            from IPython.display import IFrame
            return IFrame(url, width=width, height=height)
        except ImportError:
            return url
    else:
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
        if is_in_colab():
            from google.colab.output import eval_js
            ext_url = eval_js("google.colab.kernel.proxyPort(2908)")
            _host = PlotHost('http://localhost:2908',external_url=ext_url)
            try:
                status = _host.status()
            except:
                start_server_process()
            return _host
        jpy = my_jupyter_server()
        if jpy is not None:
            hub_prefix = os.getenv("JUPYTERHUB_SERVICE_PREFIX")
            if hub_prefix is None:
                ext = jpy['url'] + "plotar/"
            else:
                # on jupyter-/binderhub we don't know the external hostname,
                # so we use an absolute URL
                ext = hub_prefix+"plotar/"
            _host = PlotHost(jpy['url']+"plotar/", external_url=ext, params=jpy['params'], headers=jpy['headers'])
        else:
            _host = PlotHost(DEFAULT_SERVER)
    return _host

def set_default_host(host='https://localhost:2908', ignore_ssl_warnings=None):
    global _host
    _host = PlotHost(host, ignore_ssl_warnings=ignore_ssl_warnings)

class PlotHost:
    def __init__(self, url: str, external_url: str = None, params='', headers={}, ignore_ssl_warnings=None):
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
        self.verify = True
        if self.url.startswith("https://"):
            # on localhost by default ignore_ssl_warnings
            is_localhost = self.url.startswith("https://localhost:") or self.url.startswith("https://127.0.0.1:")
            if ignore_ssl_warnings == True or (ignore_ssl_warnings is None and is_localhost):
                import urllib3
                urllib3.disable_warnings()
                self.verify = False
    def internal_url(self, path):
        '''Shows the URL that is '''
        return self.url + path #+ self.params
    def external_url(self, path):
        return self._external_url + path + self.params
    def post(self, json):
        response = requests.post(self.internal_url(""), json=json, headers=self.headers, verify=self.verify)
        response.raise_for_status()
    def get(self, path):
        response = requests.get(self.internal_url(path), headers=self.headers, verify=self.verify)
        response.raise_for_status()
        return response.json()
    def status(self):
        return self.get("status.json")
    def __repr__(self):
        return f"PlotHost({self.url})"
    def _repr_html_(self):
        return f"PlotAR at <a href='{self.url}'>{self.url}</a>"

def my_jupyter_server(verbose=False, jupyter_parent_pid=None):
    servers = []
    imported_notebookapp = imported_serverapp = False
    try:
        from jupyter_server import serverapp
        servers += serverapp.list_running_servers()
        imported_serverapp = True
    except ImportError:
        pass
    try:
        from notebook import notebookapp
        imported_notebookapp = True
        servers += notebookapp.list_running_servers()
    except ImportError:
        pass
    if not len(servers):
        if verbose:
            import warnings
            warnings.warn(f"no running jupyter server found - imported jupyter_server: {imported_serverapp} notebook: {imported_notebookapp}")
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

def start_server_process(port: int = 2908, showServerURL=False):
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
    
    proc = subprocess.Popen([python, '-m', 'plotar.server', '--port', str(port)])

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

def is_in_jupyter() -> bool:
    # https://stackoverflow.com/a/39662359/6400719
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
    except:
        return False  # Probably standard Python interpreter
    return False


def is_in_colab() -> bool:
    # https://stackoverflow.com/a/39662359/6400719
    try:
        from IPython import get_ipython
        return 'google.colab' in str(get_ipython()) #if hasattr(__builtins__,'__IPYTHON__') else False
    except:
        return False  # Probably standard Python interpreter
