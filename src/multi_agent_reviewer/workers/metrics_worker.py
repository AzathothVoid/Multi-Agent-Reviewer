from rq import Queue, Worker
from multi_agent_reviewer import metrics
from rq.job import Job
import time


class MetricsWorker(Worker):
    def execute_job(self, job: Job, queue: Queue):
        metrics.MAR_RQ_STARTED.labels("rq_worker", queue.name).inc()
        start = time.time()
        try:
            result = super().execute_job(job, queue)
            metrics.MAR_RQ_SUCCEEDED.labels("rq_worker", queue.name).inc()
            return result
        except Exception as e:
            metrics.MAR_RQ_FAILED.labels(
                "rq_worker", queue.name, type(e).__name__
            ).inc()
            raise
        finally:
            metrics.MAR_RQ_JOB_DURATION.labels("rq_worker", queue.name).observe(
                time.time() - start
            )
