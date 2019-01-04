About
=====

A distributed system for double pendulum simulation.
Sequential and multiprocessing implementation can be found at: https://github.com/vladaindjic/PDAJ

Installation
============

pendulum doesn't require system wide installation, just clone this
repository to get started.

In order to run whole simulation, run comman `docker-compose up`.
If you want to run more than one worker, run `docker-compose scale worker=<num_workers>`