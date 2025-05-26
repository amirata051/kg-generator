from fastapi import FastAPI

app = FastAPI(title="Knowledge Graph Generator API")

@app.get("/")
async def read_root():
    return {"message": "Hello, Knowledge Graph Generator!"}
