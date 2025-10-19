# test_server.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/status/test")
async def status_test():
    return {"status": "ok"}
