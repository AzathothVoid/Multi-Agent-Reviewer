def main():
    import uvicorn

    uvicorn.run(
        "multi_agent_reviewer.main:app", host="localhost", port=8000, reload=True
    )
