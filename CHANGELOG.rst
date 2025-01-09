0.12.0 2025-01-09
-----------------

* Forward task_status to hypercorn.
* Support Python 3.13, and 3.12 drop Python 3.8 and 3.7.

0.11.1 2023-11-19
-----------------

* Support Quart 0.19.4 and the event_class.
* Bugfix the run_task usage.

0.11.0 2023-10-07
-----------------

* Turn all MultiError occurrences into BaseExceptionGroup.
* Bugfix form response file saving.
* Support Quart 0.19 or greater.
* Officially support Python 3.12 drop Python 3.7.

0.10.0 2022-08-14
-----------------

* Bugfix missing websocket_received event.
* Support Quart 0.18.0 or greater.

0.9.1 2022-01-02
----------------

* Bugfix filter out cancelled errors from MultiErrors.
* Bugfix wrong lock class on TrioRequest.
* Bugfix use parsing lock when loading form data.

0.9.0 2021-11-13
----------------

* Support Python 3.10
* Update to the Quart 0.16.0 including the latest Quart APIs.

0.8.1 2021-09-12
----------------

* Bugfix form data parsing, fixing no running event loop errors.
* Bugfix save the results of the form parsing.

0.8.0 2021-05-11
----------------

* Bugfix add missing is_set method.
* Support Quart 0.15 as minimum version.

0.7.0 2020-12-06
----------------

* Officially support Python 3.9.
* Support Quart 0.14.0 or greater.

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
