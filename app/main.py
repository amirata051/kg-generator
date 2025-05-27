from fastapi import FastAPI
from app.api.upload import router as upload_router

app = FastAPI(title="Knowledge Graph Generator API")
app.include_router(upload_router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": "Hello, Knowledge Graph Generator!"}
