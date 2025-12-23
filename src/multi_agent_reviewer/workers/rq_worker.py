from rq import Worker, Queue
from src.multi_agent_reviewer.config import settings
from redis import Redis
import signal
import logging
import os;

redis_conn = Redis.from_url(settings.redis_url)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_worker():
    queue = Queue(connection=redis_conn)
    worker = Worker([queue])

    def _graceful(signum, frame):
        logger.info("Received signal %s, shutting down gracefully...", signum)
        worker.request_stop(signum, frame)

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    worker.work(with_scheduler=True)


if __name__ ==  "__main__":
    run_worker()