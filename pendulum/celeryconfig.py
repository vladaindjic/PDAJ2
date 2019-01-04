from multiprocessing import cpu_count
import os

from kombu import Queue


## Environment based settings

MAX_CPU_CORES = os.getenv('MAX_CPU_CORES', cpu_count())
SERVER_NAME = os.getenv('SERVER_NAME', 'localhost')
AM_I_SERVER = (os.getenv('COMPUTER_TYPE') == 'server')

THETA_RESOLUTION = int(os.getenv('THETA_RESOLUTION', '10'))
L1 = float(os.getenv('L1', '1.0'))
L2 = float(os.getenv('L2', '1.0'))
M1 = float(os.getenv('M1', '1.0'))
M2 = float(os.getenv('M2', '1.0'))
TMAX = float(os.getenv('TMAX', '30.0'))
DT = float(os.getenv('DT', '0.01'))
RESULTS_PATH = os.getenv('RESULTS_PATH', "results.csv")


if AM_I_SERVER:
    MONITORING_IS_ACTIVE = bool(int(os.getenv('MONITORING_IS_ACTIVE', '0')))
    if MONITORING_IS_ACTIVE:
        MONITORING_SERVER_NAME = os.getenv('MONITORING_SERVER_NAME', 'localhost')
        MONITORING_SERVER_PORT = int(os.getenv('MONITORING_SERVER_PORT', 2003))
        MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 30))
        MONITORING_METRIC_PREFIX = os.getenv('MONITORING_METRIC_PREFIX', 'experiments.pendulum')

    HDF5_COMPLIB = os.getenv('HDF5_COMPLIB', 'zlib')
    HDF5_COMPLEVEL = int(os.getenv('HDF5_COMPLEVEL', 1))

    RESULTS_DIR = os.getenv('RESULTS_DIR', '/tmp/results')
    STATUS_DIR = os.path.join(RESULTS_DIR, 'status')


## Concurrency settings

CELERYD_CONCURRENCY = MAX_CPU_CORES

# This ensures that each worker will only take one task at a time, when combined
# with late acks. This is the recommended configuration for long-running tasks.
# References:
#   * http://celery.readthedocs.org/en/latest/userguide/optimizing.html#prefetch-limits
#   * http://celery.readthedocs.org/en/latest/userguide/optimizing.html#reserve-one-task-at-a-time
#   * http://celery.readthedocs.org/en/latest/configuration.html#celeryd-prefetch-multiplier
#   * http://stackoverflow.com/questions/16040039/understanding-celery-task-prefetching
#   * https://bugs.launchpad.net/openquake-old/+bug/1092050
#   * https://wiredcraft.com/blog/3-gotchas-for-celery/
#   * http://www.lshift.net/blog/2015/04/30/making-celery-play-nice-with-rabbitmq-and-bigwig/

# Ostaviti ovako ako se rade proracuni, jedino za kroler povecati
CELERYD_PREFETCH_MULTIPLIER = 1

## Task result backend settings

# medjurezultati rada se cuvaju u redisu
CELERY_RESULT_BACKEND = "redis://%s" % SERVER_NAME


## Message Routing

CELERY_DEFAULT_QUEUE = 'worker'
CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_DEFAULT_ROUTING_KEY = 'worker'

if AM_I_SERVER:
    CELERY_QUEUES = (
        Queue('server',  routing_key='server'),
    )
else:
    CELERY_QUEUES = (
        Queue('worker', routing_key='worker'),
    )

class ServerTasksRouter(object):
    def route_for_task(self, task, args=None, kwargs=None):
        if task.startswith('pendulum.tasks.server.'):
            return {'queue': 'server'}
        
        return None

CELERY_ROUTES = (
    ServerTasksRouter(),
)


## Broker Settings

BROKER_URL = "amqp://%s" % SERVER_NAME
# zbog efikasnosti
CELERY_ACCEPT_CONTENT = ['pickle', 'json']


## Task execution settings

# kompresija
CELERY_MESSAGE_COMPRESSION = 'bzip2'
# ne isticu nam medjurezultati
CELERY_TASK_RESULT_EXPIRES = None
# koliko cesto sme da se izvrsava task
CELERY_DISABLE_RATE_LIMITS = True
# da moze monitoring da se ukljuci
CELERY_TRACK_STARTED = True

# This ensures that the worker acks the task *after* it's completed.
# If the worker crashes or gets killed mid-execution, the task will be returned
# to the broker and restarted on another worker.
# References:
#   * https://wiredcraft.com/blog/3-gotchas-for-celery/
#   * http://celery.readthedocs.org/en/latest/configuration.html#celery-acks-late
#   * http://celery.readthedocs.org/en/latest/faq.html#faq-acks-late-vs-retry

# uglavnom task javi da neocekivano zavrsva sa radom, pa javi serveru
# ali ako pukne memorija ili nesto gore, onda ne moze da stigne da javi
CELERY_ACKS_LATE = True


## Worker settings

if AM_I_SERVER:
    CELERY_IMPORTS = ['pendulum.tasks.server']
else:
    CELERY_IMPORTS = ['pendulum.tasks.worker']

# HACK: Prevents weird SymPy related memory leaks
# CELERYD_MAX_TASKS_PER_CHILD = 10
CELERYD_MAX_TASKS_PER_CHILD = 100


## Periodic Task Server (celery beat)

if AM_I_SERVER and MONITORING_IS_ACTIVE:
    CELERYBEAT_SCHEDULE = {
        'monitor-queues': {
            'task': 'pendulum.tasks.server.monitor_queues',
            'schedule': MONITORING_INTERVAL,
        },
    }
