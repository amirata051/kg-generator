from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from app.workers.worker import get_global_kg  # import function to get KG instance

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_graph(request: ChatRequest):
    """
    # Use the global KnowledgeGraph instance built in Worker
    # If not initialized, return an error
    """
    kg = get_global_kg()
    if not kg:
        logger.error("KnowledgeGraph instance not initialized yet.")
        raise HTTPException(status_code=400, detail="Knowledge Graph not initialized. Please upload files first.")

    try:
        chat = kg.chat_session()
        response = chat.send_message(request.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat processing failed")
