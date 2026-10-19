from huey.contrib.djhuey import db_task

from . import jobs
from .models import Job


@db_task()
def run_job(job_id: int):
    jobs.execute(job_id)


def enqueue(kind: str, payload: dict) -> Job:
    job = Job.objects.create(kind=kind, payload=payload)
    run_job(job.id)
    return job


def retry(job: Job) -> Job:
    job.status, job.error, job.result = "pending", "", None
    job.save()
    run_job(job.id)
    return job
