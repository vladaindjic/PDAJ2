from celery import Celery
from celery.signals import worker_ready

# TODO: pendulum -> pendulum
# zameniti sa imenom projekta, zameniti
app = Celery('pendulum')
# citanje konfiguracije
app.config_from_object('pendulum.celeryconfig')

# da li je docker server i treba da pokrene stvari i da ih sacuva
if app.conf.AM_I_SERVER:
    # kada je worker na serveru spreman i kada se poveze kako treba,
    # izvrsi dolepomenutu funkciju
    @worker_ready.connect
    def bootstrap(**kwargs):
        from .tasks.server import seed_computations

        delay_time = 10 # seconds
        print "Getting ready to automatically seed computations in %d seconds..." % delay_time
        # spoljna petlja koja krece
        seed_computations.apply_async(countdown=delay_time)


if __name__ == '__main__':
    app.start()
