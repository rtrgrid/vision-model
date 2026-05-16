import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing all models and their supported methods:")

try:
    for m in genai.list_models():
        print(f"Name: {m.name}")
        print(f"Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"FAILED: {e}")
