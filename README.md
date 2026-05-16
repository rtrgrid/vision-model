# DrillDown Explainer: Infinite Visual Discovery

DrillDown is an AI-powered "Infinite Canvas" application designed for contextual visual exploration. It allows users to upload any image and "drill down" into its specific sub-components using advanced computer vision and generative AI.

## 🚀 Key Features

- **Dual Grounding Modes**:
    - **SAM2 (Segment Anything Model 2)**: Pixel-perfect object isolation using local inference.
    - **Red Ring (Visual Prompting)**: Guided attention using dynamic, resolution-aware markers.
- **Advanced Vision Intelligence**: Powered by **Gemini 2.5 Pro** and **Qwen2-VL** for deep 10-point semantic analysis (Materials, Aesthetic, Design Details, etc.).
- **Generative Continuity**: Uses **Google Imagen 4.0** to generate hyper-detailed macro close-ups based on identified sub-topics.
- **Vision Inspection UI**: Real-time transparency with a 3-tab inspector showing detected results, exact vision prompts, and raw JSON outputs.
- **Local + Cloud Hybrid**: Local object segmentation combined with world-class cloud reasoning.

## 🛠 Tech Stack

- **Frontend**: React (Vite), Vanilla CSS.
- **Backend**: Python (FastAPI), Pillow (Image Processing).
- **AI Models**:
    - **Vision**: Google Gemini 2.5 Pro, Qwen2-VL, InternVL-2.
    - **Segmentation**: SAM2 (Local).
    - **Generation**: Google Imagen 4.0, Stability AI SDXL (Fallback).

## 🏃 How to Run

### 1. Prerequisites
- Python 3.10+
- Node.js & npm
- Google AI (Gemini) API Key

### 2. Setup Backend
```bash
cd server
pip install -r requirements.txt
# Create a .env file with:
# GOOGLE_API_KEY=your_key
# HF_TOKEN=your_huggingface_token
python -m app.main
```

### 3. Setup Frontend
```bash
cd client
npm install
npm run dev
```

## 📂 Documentation
- [Technical Implementation Report](./DRILLDOWN_TECHNICAL_REPORT.md)
- [System Flow Architecture](./SYSTEM_FLOW_ARCHITECTURE.md)
- [Red Marker Workflow](./RED_MARKER_WORKFLOW.md)
- [Dual Grounding Deep-Dive](./DUAL_GROUNDING_ARCHITECTURE.md)

---
Developed as a high-fidelity prototype for AI-powered illustrated explainers.
