.. _deployment:

Deploying Quart-Trio
====================

It is not recommended to run Quart-Trio apps directly (via
:meth:`~quart_trio.app.QuartTrio.run`) in production. Instead it is
recommended that `Hypercorn <https://github.com/pgjones/hypercorn>`_
is used. This is becuase the :meth:`~quart_trio.app.QuartTrio.run`
enables features that help development yet slow production
performance. Hypercorn is installed with QuartTrio and will be used to
serve requests in development mode by default (e.g. with
:meth:`~quart_trio.app.QuartTrio.run`).

Hypercorn is recommended as it is the only ASGI server that supports
Trio.

To use Quart with an ASGI server simply point the server at the Quart
application, for example for a simple application in a file called
``example.py``,

.. code-block:: python

    from quart_trio import QuartTrio

    app = QuartTrio(__name__)

    @app.route('/')
    async def hello():
        return 'Hello World'

you can run with Hypercorn using,

.. code-block:: bash

    hypercorn -k trio example:app

See the `Hypercorn docs <https://hypercorn.readthedocs.io/>`_.
