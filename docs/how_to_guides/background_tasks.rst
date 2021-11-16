.. _background_tasks:

Background Tasks
================

Background tasks work with the same API as for `Quart
<https://pgjones.gitlab.io/quart/how_to_guides/background_tasks.html>`_
with the tasks themselves running on a nursery stored on the app,
``app.nursery``.

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
