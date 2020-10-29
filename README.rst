Quart-Trio
==========

|Build Status| |docs| |pypi| |python| |license|

Quart-Trio is an extension for `Quart
<https://gitlab.com/pgjones/quart>`__ to support the `Trio
<https://trio.readthedocs.io/en/latest/>`_ event loop. This is an
alternative to using the asyncio event loop present in the Python
standard library and supported by default in Quart.

Quickstart
----------

QuartTrio can be installed via `pip
<https://docs.python.org/3/installing/index.html>`_,

.. code-block:: console

    $ pip install quart-trio

and requires Python 3.7.0 or higher (see `python version support
<https://pgjones.gitlab.io/quart/discussion/python_versions.html>`_ for
reasoning).

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
<https://pgjones.gitlab.io/quart-trio/tutorials/deployment.html>`_
documentation.

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

The `Quart-Trio <https://pgjones.gitlab.io/quart-trio/>`__ and `Quart
<https://pgjones.gitlab.io/quart/>`__ documentation are the best
places to start, after that try searching `stack overflow
<https://stackoverflow.com/questions/tagged/quart>`_, if you still
can't find an answer please `open an issue
<https://gitlab.com/pgjones/quart-trio/issues>`_.


.. |Build Status| image:: https://gitlab.com/pgjones/quart-trio/badges/master/pipeline.svg
   :target: https://gitlab.com/pgjones/quart-trio/commits/master

.. |docs| image:: https://img.shields.io/badge/docs-passing-brightgreen.svg
   :target: https://pgjones.gitlab.io/quart-trio/

.. |pypi| image:: https://img.shields.io/pypi/v/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |python| image:: https://img.shields.io/pypi/pyversions/quart-trio.svg
   :target: https://pypi.python.org/pypi/Quart-Trio/

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://gitlab.com/pgjones/quart-trio/blob/master/LICENSE
