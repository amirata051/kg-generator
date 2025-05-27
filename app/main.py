from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.graph import router as graph_router

app = FastAPI(title="Knowledge Graph Generator API")
app.include_router(upload_router, prefix="/api")
app.include_router(graph_router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": "Hello, Knowledge Graph Generator!"}
