from . import server

from notebook.notebookapp import *

# Jupyter Extension points
def _jupyter_server_extension_paths():
    return [{
        'module': 'plotar.jupyter_server_extension',
    }]

def load_jupyter_server_extension(nbapp: NotebookApp):
    from notebook.base.handlers import AuthenticatedHandler, IPythonHandler
    from tornado.web import RequestHandler, authenticated
    # Set up handlers picked up via config
    base_url = nbapp.base_url
    server._base_path = base_url + 'plotar/'
    server._token = nbapp.token
    server._PORT = nbapp.port

    mappings = []
    for path, handler, *args in server._mappings:
        if not issubclass(handler, AuthenticatedHandler):
            ## Actually we should have some of the Handlers maybe inherit from API handler,
            ## so they do not redirect to the login page :-|
            class _MixinHandler(handler, IPythonHandler):
                pass
            _MixinHandler.__name__ = f"_{handler.__name__}_JupyterMixin"
            for name in dir(handler):
                if name.upper() not in RequestHandler.SUPPORTED_METHODS:
                    continue
                func = getattr(handler, name)
                if func is not RequestHandler._unimplemented_method:
                    setattr(_MixinHandler, name, authenticated(func))
            handler = _MixinHandler
        mappings.append((base_url+r'plotar'+path,handler) + tuple(args) )

    nbapp.web_app.add_handlers('.*', mappings)
