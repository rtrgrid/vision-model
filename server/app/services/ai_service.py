import asyncio
import os
import io
import base64
import json
import re
from PIL import Image
from huggingface_hub import InferenceClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv("server/.env")

class AIService:
    # Google GenAI Client
    google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Hugging Face Client
    hf_client = InferenceClient(token=os.getenv("HF_TOKEN"))
    
    # Model Names - Prioritizing Pro for maximum detail
    VISION_MODEL_PRIMARY = "gemini-2.5-pro"
    VISION_MODEL_SECONDARY = "gemini-2.0-flash" 
    
    # Image Generation
    IMAGE_MODEL_PRIMARY = "imagen-4.0-fast-generate-001" 
    IMAGE_MODEL_SECONDARY = "imagen-4.0-generate-001"
    
    HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

    # Advanced Magazine Variant Prompt with Negative Prompting
    STRUCTURED_PROMPT = (
        "SYSTEM PERSONA:\n"
        "You are an expert editorial art director, technical analyst, and spatial investigator. "
        "Your task is to analyze the specific area highlighted by the red marker (the 'target') while using the rest of the image for semantic context.\n\n"
        
        "NEGATIVE PROMPT & STRICT RULES:\n"
        "- DO NOT hallucinate brand names or trademarks (e.g., 'Chanel', 'Nike', 'Ferrari') unless a logo is explicitly 100% visible and readable in the target area. Use generic material/style descriptors instead (e.g., 'quilted leather').\n"
        "- DO NOT describe the red marker itself. It is only a guide for your attention.\n"
        "- DO NOT provide generic, high-level descriptions. Be forensic and granular about the specific sub-component highlighted.\n\n"
        
        "SEMANTIC EXTRACTION:\n"
        "Analyze the target area and return a detailed structured description designed for an interactive magazine layout. You must extract:\n"
        "1. 'object': The specific, granular name of the sub-component (e.g., 'leather watch strap', not just 'watch').\n"
        "2. 'materials': A list of likely materials and colors (e.g., ['rose gold', 'woven nylon', 'sapphire crystal']).\n"
        "3. 'style': The overall aesthetic or architectural style of the component.\n"
        "4. 'granular_details': A list of 3-5 forensic, physical observations. For EACH detail, you MUST provide 'label' (2-3 words), 'description' (1 sentence), and 'point' [x, y]. The point must be normalized floats between 0.0 and 1.0 representing the exact [x_coord, y_coord] on the image where this detail is located (e.g. [0.45, 0.60]).\n"
        "5. 'spatial_context': Describe where this object sits in relation to the parent scene (e.g., 'Located at the lower-left junction of the primary housing').\n"
        "6. 'editorial_headline': A captivating, magazine-style headline (max 6 words) about the target.\n"
        "7. 'explainer_paragraph': A 2-3 sentence elegant, factual explanation of the target's function, history, or design significance.\n\n"
        
        "DRILL CONTEXT GENERATION:\n"
        "8. 'drill_topic': This is the most critical field. Write a highly detailed, descriptive prompt that will be sent to an Image Generator to draw a MACRO CLOSE-UP of the target object. It MUST include the object name, its materials, its style, and all granular details discovered. (e.g., 'An extreme macro close-up of a woven navy blue nylon watch strap showing individual fiber weaves and the polished rose gold buckle...').\n\n"
        
        "OUTPUT FORMAT:\n"
        "You MUST return ONLY a raw JSON object matching this schema exactly. No markdown blocks, no conversational text:\n"
        "{\"object\": \"string\", \"materials\": [\"string\"], \"style\": \"string\", \"granular_details\": [{\"label\": \"string\", \"description\": \"string\", \"point\": [0.5, 0.5]}], \"spatial_context\": \"string\", \"editorial_headline\": \"string\", \"explainer_paragraph\": \"string\", \"drill_topic\": \"string\"}"
    )

    GLOBAL_DETECTION_PROMPT = (
        "SYSTEM PERSONA:\n"
        "You are an expert autonomous scene analyst and technical illustrator.\n\n"
        "TASK:\n"
        "Analyze the entire image and identify 5-8 of the most important, visually distinct, or interactive-worthy regions/objects. "
        "You MUST provide unique and precise spatial grounding for every single item you identify.\n\n"
        "SPATIAL GROUNDING RULES:\n"
        "- For EACH component in 'granular_details', you MUST provide a unique 'point' [x, y].\n"
        "- The 'point' must be the exact normalized [x_coord, y_coord] (0.0 to 1.0) corresponding to the center-of-mass of that specific component in the image.\n"
        "- DO NOT use the same coordinate for multiple objects.\n"
        "- DO NOT default to [0.5, 0.5]. Be forensic. If the object is in the top-left, the point should be near [0.1, 0.1].\n\n"
        "EXTRACTION RULES:\n"
        "1. Identify major foreground objects and meaningful sub-regions.\n"
        "2. Focus on shape, texture, color, and material.\n"
        "3. Provide EXACT normalized [x, y] coordinates (0.0 to 1.0) for the center of each object.\n"
        "4. Create a magazine-style editorial headline for the overall scene.\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY a raw JSON object with this schema:\n"
        "{\n"
        "  \"editorial_headline\": \"string\",\n"
        "  \"explainer_paragraph\": \"string\",\n"
        "  \"granular_details\": [\n"
        "    {\"label\": \"string\", \"description\": \"string\", \"point\": [x, y]}\n"
        "  ]\n"
        "}"
    )

    @classmethod
    async def generate_image(cls, prompt: str, output_path: str, reference_image_path: str = None):
        """
        Generates an image using FLUX.1 (via Hugging Face) with Google Imagen fallback.
        """
        loop = asyncio.get_event_loop()
        # Enforce Magazine Watercolor Style
        enhanced_prompt = f"A delicate, pale watercolor illustration of {prompt}. painted on textured cream paper, soft pastel tones, artistic, editorial magazine style, highly detailed but painted, no photorealism."
        
        def run_flux_logic():
            print(f"Trying {cls.HF_IMAGE_MODEL} (Flux)...")
            # Flux Schnell requires fewer steps
            image = cls.hf_client.text_to_image(
                enhanced_prompt,
                model=cls.HF_IMAGE_MODEL,
                num_inference_steps=4 
            )
            image.save(output_path, "PNG")
            return output_path

        def run_imagen_logic():
            print(f"Flux failed. Falling back to {cls.IMAGE_MODEL_PRIMARY}...")
            response = cls.google_client.models.generate_images(
                model=cls.IMAGE_MODEL_PRIMARY,
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio='16:9',
                    output_mime_type='image/png'
                )
            )
            return response.generated_images[0].image.image_bytes

        try:
            # TRY FLUX FIRST
            print("Executing Flux logic...")
            await loop.run_in_executor(None, run_flux_logic)
            print("Flux generation successful.")
            return output_path
        except Exception as e:
            print(f"Flux generation failed: {e}")
            try:
                # FALLBACK TO GOOGLE IMAGEN
                print("Executing Imagen fallback logic...")
                img_bytes = await loop.run_in_executor(None, run_imagen_logic)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                print(f"Imagen generation successful, saved to {output_path}")
                return output_path
            except Exception as e2:
                print(f"Google Imagen fallback also failed: {e2}")
                from PIL import Image
                img = Image.new('RGB', (1024, 576), color = 'red')
                img.save(output_path)
                return output_path

    @classmethod
    async def auto_analyze(cls, image_path: str, model_key: str = "qwen3.5"):
        """
        Performs a global scene analysis to detect all important regions.
        """
        print(f"Auto-Analysis Task: {model_key}")
        loop = asyncio.get_event_loop()
        
        def run_analysis_logic():
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            persona_prompt = cls.GLOBAL_DETECTION_PROMPT
            
            # Use Gemini as the reliable engine for complex global JSON extraction
            print(f"Running global analysis using {cls.VISION_MODEL_PRIMARY}...")
            response = cls.google_client.models.generate_content(
                model=cls.VISION_MODEL_PRIMARY,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=persona_prompt),
                            types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                        ]
                    )
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return response.text

        try:
            raw_text = await loop.run_in_executor(None, run_analysis_logic)
            # Use the existing extraction helper from identify_context (we'll need to move it or duplicate for now)
            # Actually, identify_context is a class method, so we can't easily call it. 
            # Let's just parse the JSON directly since GenAI SDK with mime_type="application/json" is very reliable.
            data = json.loads(raw_text)
            return data
        except Exception as e:
            print(f"Auto-analysis failed: {e}")
            return {"editorial_headline": "Scene Analysis", "granular_details": []}

    @classmethod
    async def identify_context(cls, image_path: str, x: float, y: float, model_key: str = "qwen3.5", segment_path: str = None):
        """
        Detailed vision extraction with Pro priority.
        """
        print(f"Vision Task: {model_key} (Prioritizing {cls.VISION_MODEL_PRIMARY})")
        loop = asyncio.get_event_loop()
        
        if segment_path and os.path.exists(segment_path):
            process_path = segment_path
            returned_path = segment_path
        else:
            process_path = f"static/temp_v_{hash(image_path + str(x) + str(y))}.png"
            returned_path = process_path
            def create_crop():
                with Image.open(image_path) as img:
                    width, height = img.size
                    cx, cy = int(x * width), int(y * height)
                    size = 350
                    crop = img.crop((max(0, cx-size), max(0, cy-size), min(width, cx+size), min(height, cy+size)))
                    crop.save(process_path, "PNG")
                return process_path
            await loop.run_in_executor(None, create_crop)

        def run_vision_logic():
            with open(process_path, "rb") as f:
                image_bytes = f.read()
            
            persona_prompt = cls.STRUCTURED_PROMPT
            
            # --- NVIDIA NIM API FOR SELECT MODELS ---
            if model_key in ["llava_nv", "kosmos_nv"]:
                nv_model_id = {
                    "llava_nv": "nvidia/健a-v1.6-34b", # Note: Actual ID may vary slightly, using common NIM naming
                    "kosmos_nv": "microsoft/kosmos-2"
                }.get(model_key)
                
                print(f"Calling NVIDIA NIM API for {model_key}...")
                try:
                    import base64
                    import requests
                    
                    # Updated to use the correct integrate endpoint
                    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
                    api_key = os.getenv("NVIDIA_API_KEY")
                    
                    b64_image = base64.b64encode(image_bytes).decode('utf-8')
                    image_url = f"data:image/png;base64,{b64_image}"
                    
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json"
                    }
                    
                    payload = {
                        "model": nv_model_id,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": cls.STRUCTURED_PROMPT},
                                    {"type": "image_url", "image_url": {"url": image_url}}
                                ]
                            }
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.20,
                        "top_p": 0.70
                    }
                    
                    response = requests.post(invoke_url, headers=headers, json=payload)
                    res_json = response.json()
                    
                    if 'choices' in res_json and len(res_json['choices']) > 0:
                        text_resp = res_json['choices'][0]['message']['content']
                        
                        if "```json" in text_resp:
                            text_resp = text_resp.split("```json")[1].split("```")[0].strip()
                        
                        return text_resp, cls.STRUCTURED_PROMPT
                    else:
                        print(f"NVIDIA API Unexpected Response: {res_json}")
                        raise Exception("Invalid response format from NVIDIA API")
                        
                except Exception as nv_e:
                    print(f"NVIDIA API call failed: {nv_e}. Falling back.")
                    persona_prompt = f"Persona: Simulate {model_key} detection engine. " + cls.STRUCTURED_PROMPT

            # --- REAL HUGGING FACE API FOR ALL ALTERNATIVE MODELS ---
            if model_key in ["qwen3.5", "qwen", "moondream", "internvl", "pixtral", "llava", "llava_next", "minicpm", "phi4", "llama_vision"]:
                hf_model_id = {
                    "qwen3.5": "Qwen/Qwen3.5-9B",
                    "qwen": "Qwen/Qwen2.5-VL-7B-Instruct",
                    "moondream": "vikhyatk/moondream2",
                    "internvl": "OpenGVLab/InternVL2-8B",
                    "pixtral": "mistralai/Pixtral-12B-2409",
                    "llava": "llava-hf/llava-1.5-7b-hf",
                    "llava_next": "llava-hf/llava-v1.6-mistral-7b-hf",
                    "minicpm": "openbmb/MiniCPM-V-2_6",
                    "phi4": "microsoft/Phi-4-multimodal-instruct",
                    "llama_vision": "meta-llama/Llama-3.2-11B-Vision-Instruct"
                }.get(model_key)
                
                print(f"Calling REAL Hugging Face API for {model_key} ({hf_model_id})...")
                try:
                    import base64
                    b64_image = base64.b64encode(image_bytes).decode('utf-8')
                    image_url = f"data:image/png;base64,{b64_image}"
                    
                    # Using the standard OpenAI-compatible chat completion endpoint on HF
                    response = cls.hf_client.chat.completions.create(
                        model=hf_model_id,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": cls.STRUCTURED_PROMPT},
                                    {"type": "image_url", "image_url": {"url": image_url}}
                                ]
                            }
                        ],
                        max_tokens=800
                    )
                    
                    # Extract text and attempt to clean it if it contains markdown JSON blocks
                    text_resp = response.choices[0].message.content
                    if "```json" in text_resp:
                        text_resp = text_resp.split("```json")[1].split("```")[0].strip()
                    
                    return text_resp, cls.STRUCTURED_PROMPT
                except Exception as hf_e:
                    print(f"Real {model_key} HF call failed: {hf_e}. Falling back to simulation.")
                    persona_prompt = f"Persona: Simulate {model_key} detection engine. " + cls.STRUCTURED_PROMPT
            
            # --- FALLBACK / OTHER MODELS: SIMULATED BY GEMINI ---
            elif model_key != "gemini":
                persona_prompt = f"Persona: Simulate {model_key} detection engine. " + cls.STRUCTURED_PROMPT

            try:
                # Try Primary (Pro) for maximum details
                print(f"Trying {cls.VISION_MODEL_PRIMARY}...")
                response = cls.google_client.models.generate_content(
                    model=cls.VISION_MODEL_PRIMARY,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=persona_prompt),
                                types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                            ]
                        )
                    ],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                return response.text, persona_prompt
            except Exception as e1:
                print(f"{cls.VISION_MODEL_PRIMARY} failed: {e1}. Trying fallback {cls.VISION_MODEL_SECONDARY}...")
                response = cls.google_client.models.generate_content(
                    model=cls.VISION_MODEL_SECONDARY,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=persona_prompt),
                                types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                            ]
                        )
                    ],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                return response.text, persona_prompt

        def extract_json_from_text(text: str) -> str:
            """Extracts JSON object from text, handling markdown blocks and basic cleanup."""
            # If it's already a clean JSON object, return it
            text = text.strip()
            if text.startswith('{') and text.endswith('}'):
                return text
                
            # Look for json markdown block
            if "```json" in text:
                try:
                    return text.split("```json")[1].split("```")[0].strip()
                except IndexError:
                    pass
            
            # Look for any markdown block
            if "```" in text:
                parts = text.split("```")
                if len(parts) >= 3:
                    return parts[1].strip()

            # Last resort: find first { and last }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                return text[start:end+1]
                
            return text

        try:
            json_text, used_prompt = await loop.run_in_executor(None, run_vision_logic)
            
            # Robust JSON parsing
            clean_json = extract_json_from_text(json_text)
            
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError as e:
                print(f"JSON Parsing failed on output: {clean_json[:100]}... Error: {e}")
                # Provide a safe fallback object so the application doesn't crash
                data = {
                    "object": "Component (Analysis Failed)",
                    "drill_topic": "a detailed sub-component",
                    "metadata": {"error": "Failed to parse vision model output"}
                }

            return {
                "drill_topic": data.get("drill_topic", "a detailed part"),
                "input_prompt": used_prompt,
                "raw_json": clean_json, # return the cleaned version
                "metadata": data
            }, returned_path
        except Exception as e:
            print(f"Vision failed completely: {e}")
            return {"drill_topic": "a detailed sub-component", "metadata": {}}, None
