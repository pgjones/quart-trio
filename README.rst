Quart-Trio
==========

|Build Status| |docs| |pypi| |python| |license|

Quart-Trio is an extension for `Quart
<https://github.com/pallets/quart>`__ to support the `Trio
<https://trio.readthedocs.io/en/latest/>`_ event loop. This is an
alternative to using the asyncio event loop present in the Python
standard library and supported by default in Quart.

Quickstart
----------

QuartTrio can be installed via `pip
<https://docs.python.org/3/installing/index.html>`_,

.. code-block:: console

    $ pip install quart-trio

and requires Python 3.8 or higher (see `python version support
<https://quart.palletsprojects.com/en/latest/discussion/python_versions.html>`_
for reasoning).

A minimal Quart example is,

.. code-block:: python

    from quart import websocket
    from quart_trio import QuartTrio

    app = QuartTrio(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    @app.websocket('/ws')
    async def ws():
        while True:
            await websocket.send('hello')

    app.run()

if the above is in a file called ``app.py`` it can be run as,

.. code-block:: console

    $ python app.py

To deploy in a production setting see the `deployment
<https://quart-trio.readthedocs.io/en/latest/tutorials/deployment.html>`_
documentation.

Contributing
------------

Quart-Trio is developed on `GitHub
<https://github.com/pgjones/quart-trio>`_. You are very welcome to
open `issues <https://github.com/pgjones/quart-trio/issues>`_ or
propose `merge requests
<https://github.com/pgjones/quart-trio/merge_requests>`_.

Testing
~~~~~~~

The best way to test Quart-Trio is with Tox,

.. code-block:: console

    $ pip install tox
    $ tox

this will check the code style and run the tests.

Help
----

The `Quart-Trio <https://quart-trio.readthedocs.io>`__ and `Quart
<https://quart.palletsprojects.com>`__ documentation are the best
places to start, after that try searching `stack overflow
<https://stackoverflow.com/questions/tagged/quart>`_, if you still
can't find an answer please `open an issue
<https://github.com/pgjones/quart-trio/issues>`_.


.. |Build Status| image:: https://github.com/pgjones/quart-trio/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/pgjones/quart-trio/commits/main

.. |docs| image:: https://img.shields.io/badge/docs-passing-brightgreen.svg
   :target: https://quart-trio.readthedocs.io

.. |pypi| image:: https://img.shields.io/pypi/v/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |python| image:: https://img.shields.io/pypi/pyversions/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/pgjones/quart-trio/blob/main/LICENSE
