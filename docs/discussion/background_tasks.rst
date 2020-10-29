.. _discuss_background_tasks:

Background Tasks
================

The background task nursery (placed on the app) exists thanks to the
ASGI lifespan protocol, with the nursery being opened and persisting
for the duration of the server lifespan task. This allows for
background tasks, but possibly goes against Trio's design principles.

Cancellation
------------

Task cancellation is still not clear, nor is graceful
shutdowns. Although this goes beyond Quart-Trio alone.
