from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
import hashlib
import shutil
from app.services.page_service import PageService

router = APIRouter()
page_service = PageService()
STATIC_DIR = "static"

class PageRequest(BaseModel):
    query: Optional[str] = None
    parentId: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    visionModel: Optional[str] = "gemini"
    groundingMode: Optional[str] = "sam2" # "sam2" or "red_ring"

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
        
        return {"id": page_id, "imageUrl": f"/static/{page_id}.png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
