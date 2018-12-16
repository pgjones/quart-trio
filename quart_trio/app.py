import warnings
from functools import partial
from typing import Any, Optional

import hypercorn.trio.run
import trio
from hypercorn.config import Config as HyperConfig
from quart import Quart
from quart.logging import create_serving_logger

from .asgi import TrioASGIHTTPConnection, TrioASGIWebsocketConnection
from .request import TrioRequest, TrioWebsocket
from .testing import TrioQuartClient


class QuartTrio(Quart):
    asgi_http_class = TrioASGIHTTPConnection
    asgi_websocket_class = TrioASGIWebsocketConnection
    request_class = TrioRequest
    test_client_class = TrioQuartClient
    websocket_class = TrioWebsocket

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._first_request_lock = trio.Lock()

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: Optional[bool] = None,
        access_log_format: str = "%(h)s %(r)s %(s)s %(b)s %(D)s",
        keep_alive_timeout: int = 5,
        use_reloader: bool = False,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        ciphers: Optional[str] = None,
        keyfile: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Run this application.

        This is best used for development only, see using Gunicorn for
        production servers.

        Arguments:
            host: Hostname to listen on. By default this is loopback
                only, use 0.0.0.0 to have the server listen externally.
            port: Port number to listen on.
            access_log_format: The format to use for the access log,
                by default this is %(h)s %(r)s %(s)s %(b)s %(D)s.
            keep_alive_timeout: Timeout in seconds to keep an inactive
                connection before closing.
            use_reloader: Automatically reload on code changes.
            ca_certs: Path to the SSL CA certificate file.
            certfile: Path to the SSL certificate file.
            ciphers: Ciphers to use for the SSL setup.
            keyfile: Path to the SSL key file.
        """
        if kwargs:
            warnings.warn(
                "Additional arguments, {}, are not yet supported".format(",".join(kwargs.keys()))
            )
        config = HyperConfig()
        config.access_log_format = access_log_format
        config.access_logger = create_serving_logger()
        config.ca_certs = ca_certs
        config.certfile = certfile
        if ciphers is not None:
            config.ciphers = ciphers
        if debug is not None:
            config.debug = debug
        config.error_logger = config.access_logger
        config.host = host
        config.keep_alive_timeout = keep_alive_timeout
        config.keyfile = keyfile
        config.port = port
        config.use_reloader = use_reloader

        scheme = "http" if config.ssl_enabled is None else "https"
        print(  # noqa: T001
            "Running on {}://{}:{} (CTRL + C to quit)".format(scheme, config.host, config.port)
        )

        # These next two lines are a messy hack, whilst the Hypercorn
        # library interface is finalised.
        config.application_path = None
        hypercorn.trio.run.load_application = lambda *_: self
        try:
            trio.run(partial(hypercorn.trio.run.run_single, config))
        finally:
            # Reset the first request, so as to enable reuse.
            self._got_first_request = False
