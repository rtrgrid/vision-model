import hashlib
import os
import asyncio
import json
from app.services.ai_service import AIService
from app.utils.compositor import ImageCompositor
try:
    from app.services.sam2_service import SAM2Service
except Exception as e:
    print(f"WARNING: Could not import SAM2Service: {e}")
    SAM2Service = None


STATIC_DIR = "static"

class PageService:
    @staticmethod
    def get_hash(key: str):
        return hashlib.sha256(key.encode()).hexdigest()

    async def get_or_create_page(self, query: str = None, parent_id: str = None, x: float = None, y: float = None, vision_model: str = "qwen3.5", grounding_mode: str = "sam2"):
        if query:
            # ... existing initial page logic ...
            page_id = self.get_hash(f"initial_{query}")
            output_path = os.path.join(STATIC_DIR, f"{page_id}.png")
            if os.path.exists(output_path):
                return {"id": page_id, "imageUrl": f"/static/{page_id}.png"}
            
            prompt = f"A watercolor illustration of {query}, pale palette, serif title, 16:9"
            await AIService.generate_image(prompt, output_path)
            return {"id": page_id, "imageUrl": f"/static/{page_id}.png"}

        if parent_id and x is not None and y is not None:
            # Round coordinates to 2 decimal places to group nearby clicks
            rx = round(x, 2)
            ry = round(y, 2)
            # Hash now includes vision model AND grounding mode and rounded coords
            page_id = self.get_hash(f"drill_{parent_id}_{rx}_{ry}_{vision_model}_{grounding_mode}")
            output_path = os.path.join(STATIC_DIR, f"{page_id}.png")
            json_path = os.path.join(STATIC_DIR, f"{page_id}.json")
            
            # Cache Hit Logic
            if os.path.exists(output_path) and os.path.exists(json_path):
                print(f"Cache Hit for page: {page_id}")
                with open(json_path, "r") as f:
                    cached_data = json.load(f)
                return {
                    "id": page_id, 
                    "imageUrl": f"/static/{page_id}.png",
                    **cached_data
                }
            
            parent_path = os.path.join(STATIC_DIR, f"{parent_id}.png")
            if not os.path.exists(parent_path):
                raise FileNotFoundError(f"Parent image not found: {parent_path}")

            segment_path = None
            marked_path = None
            sam_confidence = None

            # 1. Grounding Phase
            if grounding_mode == "sam2":
                segment_path = os.path.join(STATIC_DIR, f"seg_{page_id}.png")
                loop = asyncio.get_event_loop()
                try:
                    sam_info = await loop.run_in_executor(
                        None, 
                        lambda: SAM2Service.segment_object(parent_path, x, y, segment_path)
                    )
                    sam_confidence = sam_info['confidence']
                except Exception as e:
                    print(f"SAM2 failed: {e}")
                    segment_path = None
            else:
                # Use Red Ring / Spotlight logic
                marked_path = os.path.join(STATIC_DIR, f"marked_{page_id}.png")
                ImageCompositor.draw_red_ring(parent_path, x, y, marked_path)
                print(f"Grounding with Red Ring: {marked_path}")

            # 2. Identify context
            grounding_path = segment_path if segment_path else marked_path
            
            if vision_model == "none":
                # Skip Vision AI entirely. Use generic prompt.
                print("Skipping Vision AI. Generating based on visual zoom only.")
                vision_result = {
                    "drill_topic": "a detailed macro-zoom into the textures and components of this specific area",
                    "metadata": {
                        "object": "Undefined Component",
                        "editorial_headline": "The Pure Detail",
                        "explainer_paragraph": "This is a direct visual drill-down without semantic analysis. The AI is interpreting the textures and shapes of the original image to generate a deeper layer.",
                        "style": "Visual continuity from previous page"
                    },
                    "input_prompt": "N/A - Vision Skipped",
                    "raw_json": "{}"
                }
                crop_path = None # Will rely on segment or marked path for ref
            elif vision_model == "all":
                models_to_test = ["gemini", "qwen3.5", "qwen", "internvl", "pixtral", "llava_next", "minicpm", "moondream", "llava", "phi4", "llama_vision"]
                
                async def run_model(m_key):
                    try:
                        res, c_path = await AIService.identify_context(
                            parent_path, x, y, 
                            model_key=m_key, 
                            segment_path=grounding_path
                        )
                        return {"model": m_key, "metadata": res.get("metadata", {}), "rawJson": res.get("raw_json", "")}
                    except Exception as e:
                        return {"model": m_key, "metadata": {"error": str(e)}, "rawJson": ""}

                tasks = [run_model(m) for m in models_to_test]
                results = await asyncio.gather(*tasks)
                
                result_meta = {
                    "isComparison": True,
                    "results": results,
                    "groundingMode": grounding_mode
                }
                
                # Cleanup grounding images
                if marked_path and os.path.exists(marked_path):
                    os.remove(marked_path)
                if segment_path and os.path.exists(segment_path):
                    os.remove(segment_path)
                    
                # Return immediately without generating a new image
                return {
                    "id": page_id, 
                    "imageUrl": f"/static/{parent_id}.png",
                    **result_meta
                }
            else:
                # Normal single model execution
                vision_result, crop_path = await AIService.identify_context(
                    parent_path, x, y, 
                    model_key=vision_model, 
                    segment_path=grounding_path
                )
            
            drill_topic = vision_result.get("drill_topic", "a detailed sub-component")
            metadata = vision_result.get("metadata", {})
            input_prompt = vision_result.get("input_prompt", "")
            raw_json = vision_result.get("raw_json", "")

            # 3. Generate child page
            # Reference for Img2Img is either the segment cutout or the zoomed crop
            ref_path = segment_path if segment_path else crop_path
            await AIService.generate_image(drill_topic, output_path, reference_image_path=ref_path)
            
            # Prepare result object
            result_meta = {
                "context": drill_topic,
                "metadata": metadata,
                "inputPrompt": input_prompt,
                "rawJson": raw_json,
                "samConfidence": sam_confidence,
                "groundingMode": grounding_mode
            }

            # Save metadata to cache
            with open(json_path, "w") as f:
                json.dump(result_meta, f)

            # Clean up temp files
            if segment_path and os.path.exists(segment_path):
                os.remove(segment_path)
            if marked_path and os.path.exists(marked_path):
                os.remove(marked_path)
            if crop_path and os.path.exists(crop_path):
                os.remove(crop_path)
                
            return {
                "id": page_id, 
                "imageUrl": f"/static/{page_id}.png",
                **result_meta
            }
        
        raise ValueError("Invalid parameters for page generation")

    async def stream_page(self, query: str = None, parent_id: str = None, x: float = None, y: float = None, vision_model: str = "qwen3.5", grounding_mode: str = "sam2", custom_topic: str = None):
        def sse(event: str, data: dict):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        if query:
            yield sse("generating", {"message": "Generating initial image..."})
            page_id = self.get_hash(f"initial_{query}")
            output_path = os.path.join(STATIC_DIR, f"{page_id}.png")
            if not os.path.exists(output_path):
                prompt = f"A watercolor illustration of {query}, pale palette, serif title, 16:9"
                await AIService.generate_image(prompt, output_path)
            yield sse("complete", {"id": page_id, "imageUrl": f"/static/{page_id}.png"})
            return

        if parent_id and x is not None and y is not None:
            print(f"Drill Request: parent={parent_id}, x={x}, y={y}, custom={custom_topic}")
            rx = round(x, 4)
            ry = round(y, 4)
            # Add custom_topic to hash if present to distinguish semantic drills
            hash_key = f"drill_{parent_id}_{rx}_{ry}_{vision_model}_{grounding_mode}"
            if custom_topic:
                hash_key += f"_{custom_topic}"
                
            page_id = self.get_hash(hash_key)
            output_path = os.path.join(STATIC_DIR, f"{page_id}.png")
            json_path = os.path.join(STATIC_DIR, f"{page_id}.json")

            if os.path.exists(output_path) and os.path.exists(json_path):
                with open(json_path, "r") as f:
                    cached_data = json.load(f)
                yield sse("complete", {"id": page_id, "imageUrl": f"/static/{page_id}.png", **cached_data})
                return

            parent_path = os.path.join(STATIC_DIR, f"{parent_id}.png")
            if not os.path.exists(parent_path):
                print(f"ERROR: Parent image not found: {parent_path}")
                yield sse("error", {"message": "Parent image not found. Please wait for the current image to finish loading."})
                return

            segment_path = None
            marked_path = None
            sam_confidence = None

            yield sse("grounding", {"message": "Isolating object..."})
            if grounding_mode == "sam2":
                segment_path = os.path.join(STATIC_DIR, f"seg_{page_id}.png")
                loop = asyncio.get_event_loop()
                try:
                    sam_info = await loop.run_in_executor(
                        None, 
                        lambda: SAM2Service.segment_object(parent_path, x, y, segment_path)
                    )
                    sam_confidence = sam_info['confidence']
                except Exception as e:
                    print(f"SAM2 failed: {e}")
                    segment_path = None
            else:
                marked_path = os.path.join(STATIC_DIR, f"marked_{page_id}.png")
                ImageCompositor.draw_red_ring(parent_path, x, y, marked_path)
            
            yield sse("vision", {"message": "Analyzing component...", "samConfidence": sam_confidence})
            grounding_path = segment_path if segment_path else marked_path
            
            if custom_topic:
                # SEMANTIC DRILL: Use the label text directly
                vision_result = {
                    "drill_topic": f"An extreme macro close-up of {custom_topic}, focusing on its specific textures, materials, and fine details.",
                    "metadata": {
                        "object": custom_topic,
                        "editorial_headline": f"Drilling into: {custom_topic}",
                        "explainer_paragraph": f"This layer explores the specific details of the {custom_topic} identified in the previous scene.",
                        "style": "Technical continuity"
                    },
                    "input_prompt": f"Detail zoom of {custom_topic}",
                    "raw_json": json.dumps({"object": custom_topic})
                }
                crop_path = grounding_path
            elif vision_model == "none":
                vision_result = {
                    "drill_topic": "a detailed macro-zoom into the textures and components of this specific area",
                    "metadata": {
                        "object": "Undefined Component",
                        "editorial_headline": "The Pure Detail",
                        "explainer_paragraph": "This is a direct visual drill-down without semantic analysis. The AI is interpreting the textures and shapes of the original image to generate a deeper layer.",
                        "style": "Visual continuity from previous page"
                    },
                    "input_prompt": "N/A - Vision Skipped",
                    "raw_json": "{}"
                }
                crop_path = None
            elif vision_model == "all":
                yield sse("error", {"message": "Compare mode not supported in stream yet."})
                return
            else:
                vision_result, crop_path = await AIService.identify_context(
                    parent_path, x, y, 
                    model_key=vision_model, 
                    segment_path=grounding_path
                )
            
            drill_topic = vision_result.get("drill_topic", "a detailed sub-component")
            metadata = vision_result.get("metadata", {})
            input_prompt = vision_result.get("input_prompt", "")
            raw_json = vision_result.get("raw_json", "")

            result_meta = {
                "context": drill_topic,
                "metadata": metadata,
                "inputPrompt": input_prompt,
                "rawJson": raw_json,
                "samConfidence": sam_confidence,
                "groundingMode": grounding_mode
            }
            # Yield metadata so UI can update instantly before image finishes
            yield sse("generating", {
                "message": "Illustrating detail...", 
                "metadata": metadata, 
                "samConfidence": sam_confidence,
                "rawJson": raw_json,
                "inputPrompt": input_prompt
            })

            ref_path = segment_path if segment_path else crop_path
            print(f"Generating image for topic: {drill_topic[:50]}...")
            await AIService.generate_image(drill_topic, output_path, reference_image_path=ref_path)
            print(f"Image generation finished: {output_path}")
            
            with open(json_path, "w") as f:
                json.dump(result_meta, f)
            print(f"Metadata saved to: {json_path}")

            if segment_path and os.path.exists(segment_path): os.remove(segment_path)
            if marked_path and os.path.exists(marked_path): os.remove(marked_path)
            if crop_path and os.path.exists(crop_path): os.remove(crop_path)
            
            print(f"Sending complete event for {page_id}")
            yield sse("complete", {"id": page_id, "imageUrl": f"/static/{page_id}.png", **result_meta})
            return

        yield sse("error", {"message": "Invalid parameters for page generation"})
