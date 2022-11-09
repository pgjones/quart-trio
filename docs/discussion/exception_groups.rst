.. _exception_groups:

Exception groups
================

Exception groups raised during the handling of a request or websocket are
caught and the exceptions contianed are checked against the handlers,
the first handled exception will be returned. This may lead to
non-deterministic code in that it will depend on which error is raised
first (in the case that exception groups can be handled).
