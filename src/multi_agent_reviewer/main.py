from fastapi import FastAPI


app = FastAPI()


@app.post("/review")
async def review():
    return {"message": "Review endpoint"}
