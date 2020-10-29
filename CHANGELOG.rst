0.6.0 2020-10-29
----------------

* Bugfix logger setup with run and run_task.
* Introduce a test_app method, this ensures lifespan aspects are run
  (background tasks, before/after serving).
* Implement request body init fixing issues with asyncio usage.
* Add more detailed documentation.

0.5.1 2020-03-26
----------------

* Bugfix ensure websocket disconnect cancels the connection's tasks.

0.5.0 2020-02-09
----------------

* Support Python 3.8.
* Upgrade to Quart >= 0.11.
* Bugfix allow for no request timeouts.
* Follow Quart and add a run_task method.
* Add run_sync functionality.

0.4.0 2019-08-30
----------------

* Bugfix ensure the response timeout has a default.
* Support Quart >= 0.10.0

0.3.0 2019-04-22
----------------

* Fixed import of RequestTimeout from quart.
* Upgrade to ASGI 3.0 (Lifespan spec 2.0).
* Bugfix prevent MultiErrors from crahsing the app.
* Add py.typed for PEP 561 compliance.
* Handle individual exceptions in MultiErrors.

0.2.0 2019-01-29
----------------

* Use the latest Hypercorn and Quart run definition.
* Allow for background tasks to be started, the app now has a nursery
  for background tasks.
* Support Quart >= 0.8.0.
* Support serving static files.

0.1.0 2018-12-17
----------------

* Released initial alpha version.
