import os
import socket
import subprocess
import time
from datetime import datetime

import numpy as np
from celery import chord
from celery.exceptions import Reject

from .worker import solve
from ..app import app


## Monitoring tasks

@app.task
def monitor_queues(ignore_result=True):
    server_name = app.conf.MONITORING_SERVER_NAME
    server_port = app.conf.MONITORING_SERVER_PORT
    metric_prefix = app.conf.MONITORING_METRIC_PREFIX

    queues_to_monitor = ('server', 'worker')

    output = subprocess.check_output('rabbitmqctl -q list_queues name messages consumers', shell=True)
    lines = (line.split() for line in output.splitlines())
    data = ((queue, int(tasks), int(consumers)) for queue, tasks, consumers in lines if queue in queues_to_monitor)

    timestamp = int(time.time())
    metrics = []
    for queue, tasks, consumers in data:
        metric_base_name = "%s.queue.%s." % (metric_prefix, queue)

        metrics.append("%s %d %d\n" % (metric_base_name + 'tasks', tasks, timestamp))
        metrics.append("%s %d %d\n" % (metric_base_name + 'consumers', consumers, timestamp))

    sock = socket.create_connection((server_name, server_port), timeout=10)
    sock.sendall(''.join(metrics))
    sock.close()


## Recording the experiment status

def get_experiment_status_filename(status):
    return os.path.join(app.conf.STATUS_DIR, status)


def get_experiment_status_time():
    """Get the current local date and time, in ISO 8601 format (microseconds and TZ removed)"""
    return datetime.now().replace(microsecond=0).isoformat()


@app.task
def record_experiment_status(status):
    # ako su rezultati vec sracunati, onda nece pokrenuti, jer je iskesirano
    with open(get_experiment_status_filename(status), 'w') as fp:
        fp.write(get_experiment_status_time() + '\n')


## Seeding the computations

def y0_gen(theta_resolution):
    for theta1_init in np.linspace(0, 2 * np.pi, theta_resolution):
        for theta2_init in np.linspace(0, 2 * np.pi, theta_resolution):
            # Initial conditions: theta1, dtheta1/dt, theta2, dtheta2/dt.
            y0 = np.array([
                theta1_init,
                0.0,
                theta2_init,
                0.0
            ])
            yield y0


@app.task
def seed_computations(ignore_result=True):
    # da li su eksperimenti zapoceti, bacamo izuzetak
    # seed-ovani smo ranije

    # omogucava sleep-resume mehanizam (samo ako ne ubijemo RabitMq i REdis)
    # if os.path.exists(get_experiment_status_filename('started')):
    #     raise Reject('Computations have already been seeded!')
    # snimanje statusa
    record_experiment_status.si('started').delay()

    theta_resolution = app.conf.THETA_RESOLUTION
    L1 = app.conf.L1
    L2 = app.conf.L2
    m1 = app.conf.M1
    m2 = app.conf.M2
    tmax = app.conf.TMAX
    dt = app.conf.DT

    import logging
    logging.warn('\nL1 %s\nL2 %s\nm1 %s\nm2 %s\ntmax %s\ndt %s\ntheta_resolution %s',
                 L1, L2, m1, m2, tmax, dt, theta_resolution)
    # distribuirani map reduce
    chord(
        (
            solve.s(L1, L2, m1, m2, tmax, dt, y0)
            for y0 in y0_gen(theta_resolution)
        ),
        store_results.s()
    ).delay()


@app.task
def store_results(results):
    import logging
    import csv

    results_path = os.path.join(app.conf.RESULTS_DIR, "results.csv")
    logging.info('RESULTS PATH <- %s', results_path)

    with open(results_path, 'w') as csvfile:
        fieldnames = ['theta1_init', 'theta2_init', 'theta1', 'theta2', 'x1', 'y1', 'x2', 'y2']
        csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csvwriter.writeheader()

        for theta1_init, theta2_init, theta1, theta2, x1, y1, x2, y2 in results:
            csvwriter.writerow({'theta1_init': theta1_init,
                                'theta2_init': theta2_init,
                                'theta1': theta1[-1],
                                'theta2': theta2[-1],
                                'x1': x1[-1],
                                'y1': y1[-1],
                                'x2': x2[-1],
                                'y2': y2[-1]
                                })
