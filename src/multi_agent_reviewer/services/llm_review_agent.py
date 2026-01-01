from rq.job import Job
from langchain_groq import ChatGroq


def run_llm_review(payload: dict, static_job_id: str):
    static_job = Job.fetch(static_job_id)
    static_results = static_job.result
