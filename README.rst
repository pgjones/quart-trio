Quart-Trio
==========

|Build Status| |pypi| |python| |license|

Quart-Trio is an extension for `Quart
<https://gitlab.com/pgjones/quart>`_ to support the `Trio
<https://trio.readthedocs.io/en/latest/>`_ event loop. This is an
alternative to using the asyncio event loop present in the Python
standard library and supported by default in Quart.

Usage
-----

To enable trio support, simply use the ``QuartTrio`` app class rather
than the ``Quart`` app class,

.. code-block:: python

    from quart_trio import QuartTrio

    app = QuartTrio(__name__)

    @app.route('/')
    async def index():
        await trio.sleep(0.01)
        async with trio.open_nursery as nursery:
            nursery.start_soon(...)
        return ...

A more concrete example of Quart Trio in usage, which also
demonstrates the clarity of the Trio API is given below. This example
demonstrates a simple broadcast to all chat server with a server
initiated heartbeat.

.. code-block:: python

    app = QuartTrio(__name__)

    connections = set()

    async def ws_receive():
        while True:
            data = await websocket.receive()
            for connection in connections:
                await connection.send(data)

    async def ws_send():
        while True:
            await trio.sleep(1)
            await websocket.send("Heatbeat")

    @app.websocket('/ws')
    async def ws():
        connections.add(websocket._get_current_object())
        async with trio.open_nursery() as nursery:
            nursery.start_soon(ws_receive)
            nursery.start_soon(ws_send)
        connections.remove(websocket._get_current_object())

Background Tasks
~~~~~~~~~~~~~~~~

To start a task in Trio you need a nursery, for a background task you
need a nursery that exists after the request has completed. In
Quart-Trio this nursery exists on the app,

.. code-block:: python

    @app.route("/")
    async def trigger_job():
        app.nursery.start_soon(background_task)
        return "Started", 201

Deployment
----------

To run Quart-Trio in production you should use an ASGI server that
supports Trio. At the moment only `Hypercorn
<https://gitlab.com/pgjones/hypercorn>`_ does so.

Contributing
------------

Quart-Trio is developed on `GitLab
<https://gitlab.com/pgjones/quart-trio>`_. You are very welcome to
open `issues <https://gitlab.com/pgjones/quart-trio/issues>`_ or
propose `merge requests
<https://gitlab.com/pgjones/quart-trio/merge_requests>`_.

Testing
~~~~~~~

The best way to test Quart-Trio is with Tox,

.. code-block:: console

    $ pip install tox
    $ tox

this will check the code style and run the tests.

Help
----

This README is the best place to start, after that try opening an
`issue <https://gitlab.com/pgjones/quart-trio/issues>`_.


.. |Build Status| image:: https://gitlab.com/pgjones/quart-trio/badges/master/build.svg
   :target: https://gitlab.com/pgjones/quart-trio/commits/master

.. |pypi| image:: https://img.shields.io/pypi/v/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |python| image:: https://img.shields.io/pypi/pyversions/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://gitlab.com/pgjones/quart-trio/blob/master/LICENSE
