.. _background_tasks:

Background Tasks
================

A background task runs whilst the app handles requests, for example it
could be started in a ``before_serving`` method and persist for the
lifetime of the app, or duing a request and persist until it
completes. In any case the task must be managed with care as starting,
error handling, and cancellation are more complicated with background
tasks.

To create a background task a nursery must be used. The nursery must
also persist beyond the scope/lifespan of a request, ideally matching
the lifespan of the app itself. In Quart-Trio this nursery is
available on the ``app`` (note also ``current_app``),

.. code-block:: python

    @app.before_serving
    async def startup():
        app.nursery.start_soon(background_task)

    @app.route("/")
    async def index():
        app.nursery.start_soon(background_task)
        return ...

Error handling
--------------

Background tasks may raise exceptions, which if not handled will cause
the app nursery to close (and result in the ASGI server handling the
error). Therefore it is best to handle any errors directly, e.g.

.. code-block:: python

    async def wrap_background_task(coro_function, *args):
        try:
            await coro_function(*args)
        except (trio.MultiError, Exception):
            log.exception(...)
            # Do something else?

    @app.route("/")
    async def index():
        app.nursery.start_soon(wrap_background_task(background_task))
        return ...

Testing background tasks
------------------------

By default the Quart test client is scoped to requests without any
ability to run background tasks. To test with background tasks the
``test_app`` context manager must be used. This creates the nursery on
the app which exists during the context. For example,

.. code-block:: python

    async def test_something():
        async with app.test_app() as test_app:
            assert test_app.nursery is not None
            test_client = test_app.test_client()
            test_client.get(...)
        assert app.nursery is None
