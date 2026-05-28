from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import hashlib
import shutil
from app.services.page_service import PageService
from app.services.ai_service import AIService

router = APIRouter()
page_service = PageService()
STATIC_DIR = "static"

class PageRequest(BaseModel):
    query: Optional[str] = None
    parentId: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    customTopic: Optional[str] = None
    visionModel: Optional[str] = "qwen3.5"
    groundingMode: Optional[str] = "sam2" # Default to SAM2 Segmentation Workflow

class AnalyzeRequest(BaseModel):
    pageId: str
    visionModel: Optional[str] = "qwen3.5"

@router.post("/stream-page")
async def stream_page(req: PageRequest):
    return StreamingResponse(
        page_service.stream_page(
            query=req.query,
            parent_id=req.parentId,
            x=req.x,
            y=req.y,
            vision_model=req.visionModel,
            grounding_mode=req.groundingMode,
            custom_topic=req.customTopic
        ),
        media_type="text/event-stream"
    )

@router.post("/analyze")
async def analyze_page(req: AnalyzeRequest):
    try:
        image_path = os.path.join(STATIC_DIR, f"{req.pageId}.png")
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        analysis = await AIService.auto_analyze(image_path, model_key=req.visionModel)
        return analysis
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/page")
async def get_page(req: PageRequest):
    try:
        print(f"Requesting page: {req}")
        result = await page_service.get_or_create_page(
            query=req.query,
            parent_id=req.parentId,
            x=req.x,
            y=req.y,
            vision_model=req.visionModel,
            grounding_mode=req.groundingMode
        )
        # Result now includes 'id', 'imageUrl', and we'll add 'confidence'
        return result
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in /page: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Read file content to create hash
        content = await file.read()
        page_id = hashlib.sha256(content).hexdigest()
        
        # Save to static directory
        file_path = os.path.join(STATIC_DIR, f"{page_id}.png")
        
        # Always save as PNG for consistency with compositor
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(file_path, "PNG")
        
        return {"id": page_id, "imageUrl": f"/static/{page_id}.png", "metadata": {}, "rawJson": "", "inputPrompt": "", "samConfidence": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
