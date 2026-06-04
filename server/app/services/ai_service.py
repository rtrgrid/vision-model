import asyncio
import os
import io
import base64
import json
import requests
import re
import traceback
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv("server/.env")

class AIService:
    # --- GOOGLE CONFIGURATION (For Image Gen) ---
    google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    IMAGE_MODEL_GOOGLE = "imagen-4.0-fast-generate-001"

    # --- LOCAL OLLAMA CONFIGURATION (For Vision) ---
    OLLAMA_URL = "http://localhost:11434/api"
    VISION_MODEL_LOCAL = "qwen3.5:9b"

    # --- PROMPTS (Upgraded with Forensic Illustrative Logic) ---
    STRUCTURED_PROMPT = (
        "SYSTEM PERSONA: You are an expert Technical Forensic Analyst and Master Illustrator. "
        "You specialize in identifying complex internal structures for educational textbooks.\n\n"
        "TASK: Analyze the technical sub-component at the specified location. Identify its material composition, "
        "mechanical function, and internal layers. Keep the surrounding scene in mind for context.\n\n"
        "FIELDS TO FILL:\n"
        "1. 'object': Specific, granular technical name of the part.\n"
        "2. 'materials': List specific technical materials and textures (e.g., 'brushed aerospace aluminum', 'translucent polymer').\n"
        "3. 'style': The design aesthetic (e.g., 'Bauhaus functionalism', 'Organic bionics').\n"
        "4. 'editorial_headline': A short, captivating technical title (max 6 words).\n"
        "5. 'explainer_paragraph': 2-3 elegantly written sentences of deep technical context explaining the function or history of this detail.\n"
        "6. 'drill_topic': A MASTER IMAGE PROMPT for the next layer. It MUST describe an EXTREME MACRO CLOSE-UP or CROSS-SECTION CUTAWAY. "
        "Describe forensic textures, soft cinematic lighting, and internal mechanical/biological details in great depth. "
        "Aesthetic: 'clean technical illustration, muted watercolor palette on cream paper, architectural diagram style'. "
        "CRITICAL: Explicitly forbid text. The prompt must produce a PURELY VISUAL image with ZERO labels or annotations.\n\n"
        "OUTPUT: Return ONLY a raw JSON object matching this schema exactly. No conversation."
    )

    GLOBAL_DETECTION_PROMPT = (
        "TASK: Forensic Scene Analysis.\n"
        "1. Create a technical 'editorial_headline' for the scene.\n"
        "2. Write a 2-sentence 'explainer_paragraph' summarizing the technology shown.\n"
        "3. Identify 8-10 major sub-components in 'granular_details'. Each MUST have: 'label' (name), 'description' (technical purpose), and 'point' [x, y].\n"
        "OUTPUT: Return ONLY a raw JSON object with these 3 root keys."
    )

    @classmethod
    def _extract_json(cls, text: str):
        """Advanced JSON repair and extraction."""
        if not text: return "{}"
        text = text.strip()
        print(f"\n--- [AI RAW START] ---\n{text[:1000]}...\n--- [AI RAW END] ---\n")
        
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match: text = json_match.group(1).strip()
            
        start = text.find('{')
        if start == -1: return "{}"
        
        extracted = text[start:]
        bracket_count = 0
        end_index = -1
        in_string = False
        escape = False
        
        for i, char in enumerate(extracted):
            if char == '"' and not escape: in_string = not in_string
            if not in_string:
                if char == '{': bracket_count += 1
                elif char == '}': 
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_index = i + 1; break
            if char == '\\': escape = True
            else: escape = False
            
        if end_index != -1: return extracted[:end_index]
        
        if extracted.count('"') % 2 != 0: extracted += '"'
        open_braces = extracted.count('{')
        close_braces = extracted.count('}')
        if open_braces > close_braces: extracted += '}' * (open_braces - close_braces)
        return extracted

    @classmethod
    def _sanitize_coordinates(cls, data):
        """
        Total Metadata Normalizer:
        Ensures arrows and tabs are perfectly synced.
        """
        if isinstance(data, list):
            data = {"granular_details": data}

        if not isinstance(data, dict): return {"granular_details": []}
        
        # 1. Normalize Root Metadata
        for k_h in ["headline", "title", "subject", "topic"]:
            if k_h in data and "editorial_headline" not in data: data["editorial_headline"] = data[k_h]
        for k_e in ["description", "explainer", "summary", "context"]:
            if k_e in data and "explainer_paragraph" not in data: data["explainer_paragraph"] = data[k_e]
        if "name" in data and "object" not in data: data["object"] = data["name"]

        if "editorial_headline" not in data: data["editorial_headline"] = "Technical Component Analysis"
        if "explainer_paragraph" not in data: data["explainer_paragraph"] = "System-level forensic scan of the region."

        # 2. Support Keyed Objects
        details = []
        if not any(k in data for k in ["granular_details", "details", "objects", "components", "items"]):
            potential_details = []
            for k, v in data.items():
                if isinstance(v, dict) and any(pk in v for pk in ["label", "point", "center_point", "bbox_2d", "component"]):
                    potential_details.append(v)
            if potential_details: details = potential_details

        if not details:
            for key in ["granular_details", "details", "objects", "components", "items"]:
                if key in data and isinstance(data[key], list):
                    details = data[key]; break
        
        if not details: details = data.get("granular_details", [])
        data["granular_details"] = details

        # 3. Process each Point
        for detail in details:
            if not isinstance(detail, dict): continue
            
            # Map Label (Fixing the "Technical Detail" name bug)
            if "label" not in detail:
                detail["label"] = detail.get("component", detail.get("name", detail.get("object", "Technical Detail")))
            
            # Map Description
            if "description" not in detail:
                detail["description"] = detail.get("text", detail.get("explainer", detail.get("purpose", "")))

            # Coordinate normalization
            if "bbox_2d" in detail and isinstance(detail["bbox_2d"], list) and len(detail["bbox_2d"]) == 4:
                y1, x1, y2, x2 = detail["bbox_2d"]
                detail["point"] = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
            if "point" not in detail:
                for k_p in ["centerPoint", "center_point", "center", "location"]:
                    if k_p in detail: detail["point"] = detail[k_p]; break
            
            point = detail.get("point")
            if isinstance(point, list) and len(point) >= 2:
                normalized = []
                for val in [float(point[0]), float(point[1])]:
                    if val > 2.0: normalized.append(round(val / 1000.0, 4))
                    else: normalized.append(round(val, 4))
                detail["point"] = normalized
            else:
                detail["point"] = [0.5, 0.5]
        return data

    @classmethod
    def _prepare_vision_image(cls, image_path: str, max_size: int = 768):
        """Shrink image for faster local Ollama processing."""
        with Image.open(image_path) as img:
            if img.mode != "RGB": img = img.convert("RGB")
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

    @classmethod
    async def generate_image(cls, prompt: str, output_path: str, reference_image_path: str = None):
        """Fast image generation via Google Imagen."""
        print(f"DRAWING: Google Imagen...")
        enhanced_prompt = f"A delicate illustration of {prompt}. technical editorial style."
        try:
            def run():
                res = cls.google_client.models.generate_images(
                    model=cls.IMAGE_MODEL_GOOGLE, prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio='16:9', output_mime_type='image/png')
                )
                return res.generated_images[0].image.image_bytes
            img_bytes = await asyncio.get_event_loop().run_in_executor(None, run)
            with open(output_path, "wb") as f: f.write(img_bytes)
            return output_path
        except:
            Image.new('RGB', (1024, 576), color='gray').save(output_path)
            return output_path

    @classmethod
    async def auto_analyze(cls, image_path: str, model_key: str = "qwen3.5"):
        """FREE Local Scene Analysis."""
        print(f"SCANNING: Local Qwen3.5 (Consistency Mode)...")
        loop = asyncio.get_event_loop()
        for attempt in range(2):
            try:
                img_b64 = cls._prepare_vision_image(image_path)
                payload = {"model": cls.VISION_MODEL_LOCAL, "prompt": cls.GLOBAL_DETECTION_PROMPT, "images": [img_b64], "stream": False, "options": {"temperature": 0.0}}
                
                def run(): return requests.post(f"{cls.OLLAMA_URL}/generate", json=payload, timeout=300).json().get("response", "")
                raw_text = await loop.run_in_executor(None, run)
                
                json_text = cls._extract_json(raw_text)
                data = json.loads(json_text)
                result = cls._sanitize_coordinates(data)
                
                if result.get("granular_details"):
                    return {"metadata": result, "rawJson": json.dumps(result, indent=2)}
                print(f"Attempt {attempt+1} empty. Retrying...")
            except Exception as e:
                traceback.print_exc()
                if attempt == 1: return {"metadata": {"editorial_headline": "Error", "granular_details": []}, "rawJson": str(e)}
        return {"metadata": {"editorial_headline": "Empty Scan", "granular_details": []}, "rawJson": "{}"}

    @classmethod
    async def identify_context(cls, image_path: str, x: float, y: float, model_key: str = "qwen3.5", segment_path: str = None):
        """FREE Local Detail Identification."""
        print(f"IDENTIFYING: Local Qwen3.5 at [{x}, {y}]...")
        loop = asyncio.get_event_loop()
        process_path = segment_path if segment_path and os.path.exists(segment_path) else image_path
        try:
            img_b64 = cls._prepare_vision_image(process_path, max_size=800)
            payload = {"model": cls.VISION_MODEL_LOCAL, "prompt": cls.STRUCTURED_PROMPT, "images": [img_b64], "stream": False, "options": {"temperature": 0.0}}
            def run(): return requests.post(f"{cls.OLLAMA_URL}/generate", json=payload, timeout=300).json().get("response", "")
            raw_text = await loop.run_in_executor(None, run)
            
            json_text = cls._extract_json(raw_text)
            data = json.loads(json_text)
            result = cls._sanitize_coordinates(data)
            
            drill_topic = result.get("drill_topic")
            if not drill_topic:
                drill_topic = f"An extreme macro close-up of {result.get('object', 'detail')}, technical style."
            
            return {
                "drill_topic": drill_topic, 
                "raw_json": json.dumps(result, indent=2),
                "rawJson": json.dumps(result, indent=2),
                "metadata": result
            }, process_path
        except Exception as e:
            traceback.print_exc()
            return {"drill_topic": "detail", "metadata": {"object": "Error"}, "rawJson": str(e)}, process_path
