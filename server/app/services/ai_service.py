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

load_dotenv()

class AIService:
    # Google GenAI Client
    google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Hugging Face Client
    hf_client = InferenceClient(token=os.getenv("HF_TOKEN"))
    
    # Model Names - Prioritizing Pro for maximum detail
    VISION_MODEL_PRIMARY = "gemini-2.5-pro"
    VISION_MODEL_SECONDARY = "gemini-2.0-flash" 
    
    # Image Generation
    IMAGE_MODEL_PRIMARY = "imagen-3.0-generate-001" 
    IMAGE_MODEL_SECONDARY = "imagen-4.0-generate-001"
    
    HF_IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

    # Magazine Variant Prompt
    STRUCTURED_PROMPT = (
        "You are an expert editorial art director and technical analyst.\n\n"
        "Analyze the area highlighted by the red marker carefully. Keep the surrounding scene in mind for context.\n\n"
        "Return a detailed structured description designed for a magazine layout including:\n\n"
        "1. Primary object category\n"
        "2. Materials and Colors\n"
        "3. Style/aesthetic\n"
        "4. A short, captivating 'editorial_headline' (max 6 words)\n"
        "5. An 'explainer_paragraph' (2-3 sentences, elegantly written, explaining the function or history of the specific detail highlighted)\n"
        "6. A highly descriptive 'drill_topic' (used as an image generation prompt for a macro-zoom into the object)\n\n"
        "Output MUST be in raw JSON format matching this schema exactly:\n"
        "{\"object\": \"string\", \"materials\": [\"string\"], \"style\": \"string\", \"editorial_headline\": \"string\", \"explainer_paragraph\": \"string\", \"drill_topic\": \"string\"}"
    )

    @classmethod
    async def generate_image(cls, prompt: str, output_path: str, reference_image_path: str = None):
        """
        Generates an image using Google Imagen with HF fallback.
        """
        loop = asyncio.get_event_loop()
        # Enforce Magazine Watercolor Style
        enhanced_prompt = f"A delicate, pale watercolor illustration of {prompt}. 16:9 aspect ratio, painted on textured cream paper, soft pastel tones, artistic, editorial magazine style, highly detailed but painted, no photorealism."
        
        def run_imagen_logic():
            # Try Primary
            try:
                print(f"Trying {cls.IMAGE_MODEL_PRIMARY}...")
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
            except Exception as e1:
                print(f"{cls.IMAGE_MODEL_PRIMARY} failed: {e1}. Trying {cls.IMAGE_MODEL_SECONDARY}...")
                try:
                    response = cls.google_client.models.generate_images(
                        model=cls.IMAGE_MODEL_SECONDARY,
                        prompt=enhanced_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio='16:9',
                            output_mime_type='image/png'
                        )
                    )
                    return response.generated_images[0].image.image_bytes
                except Exception as e2:
                    raise e2

        try:
            img_bytes = await loop.run_in_executor(None, run_imagen_logic)
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            return output_path
        except Exception as e:
            print(f"Google Gen failed: {e}. Falling back to HF.")
            try:
                image = await loop.run_in_executor(
                    None, 
                    lambda: cls.hf_client.text_to_image(
                        enhanced_prompt,
                        model=cls.HF_IMAGE_MODEL,
                        num_inference_steps=30
                    )
                )
                image.save(output_path, "PNG")
                return output_path
            except:
                img = Image.new('RGB', (1024, 576), (60, 60, 60))
                img.save(output_path, "PNG")
                return output_path

    @classmethod
    async def identify_context(cls, image_path: str, x: float, y: float, model_key: str = "gemini", segment_path: str = None):
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
            if model_key != "gemini":
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

        try:
            json_text, used_prompt = await loop.run_in_executor(None, run_vision_logic)
            data = json.loads(json_text)
            return {
                "drill_topic": data.get("drill_topic", "a detailed part"),
                "input_prompt": used_prompt,
                "raw_json": json_text,
                "metadata": data
            }, returned_path
        except Exception as e:
            print(f"Vision failed completely: {e}")
            return {"drill_topic": "a detailed sub-component", "metadata": {}}, None
