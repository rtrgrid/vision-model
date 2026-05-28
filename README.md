# DrillDown: The Infinite Technical Canvas
DrillDown is an advanced visual exploration system that combines Vision AI, Object Segmentation, and Generative AI to allow users to "drill into" images. By identifying specific sub-components and generating high-detail macro close-ups, it creates an interactive, infinite technical diagram experience.

## 🚀 Key Features
- **Autonomous Scene Analysis:** Automatically detects and annotates key regions (objects, materials, textures) in any image using a high-tech scanning animation.
- **Infinite Zoom:** Generate endless layers of technical detail by clicking objects directly or clicking technical labels.
- **Multimodal AI Stack:** Orchestrates **Qwen 3.5 VL**, **Gemini 2.5 Pro**, and **Meta SAM2** for high-precision grounding and reasoning.
- **Technical Diagram UI:** Custom-built overlay system with SVG arrows and 3-tier staggered labels to prevent overlap and maximize readability.
- **Semantic Grounding:** Intelligent drill-down that understands "what" you click (e.g., "Cappuccino Cup") for guaranteed accuracy.

## 🛠 Technology Stack
- **Frontend:** React (Vite), Tailwind/Vanilla CSS, SVG Graphics.
- **Backend:** FastAPI (Python), Server-Sent Events (SSE) for real-time AI updates.
- **AI Models:**
  - **Vision:** Qwen3.5-VL (9B), Gemini 2.5 Pro.
  - **Segmentation:** SAM2 (Segment Anything Model 2).
  - **Generation:** FLUX.1 [schnell], Google Imagen 4.0.

## 📦 Setup & Installation

### 1. Backend
```bash
cd server
pip install -r requirements.txt
# Ensure you have a .env file in server/ with:
# GOOGLE_API_KEY=...
# HF_TOKEN=...
# NVIDIA_API_KEY=...
PYTHONPATH=. python3 app/main.py
```

### 2. Frontend
```bash
cd client
npm install
npm run dev
```

## 📂 Project Structure
- `/client`: React source code and API integration.
- `/server`: FastAPI routes and AI service implementations (`SAM2`, `AIService`).
- `/notes`: In-depth documentation, architectural reports, and project history.
- `/static`: Generated image assets and metadata (ignored by git).

---
**Developed for the DrillDown Capstone Project.**
