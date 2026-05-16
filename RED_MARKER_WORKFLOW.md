# DrillDown: Red Marker (Red Ring) Workflow
**Technical Specification & Flow Analysis**

---

## 1. Concept: The "Visual Proxy"
The **Red Marker** (or "Red Ring") method is a visual prompting technique designed to communicate spatial intent to a Vision-Language Model (VLM) without requiring pixel-perfect segmentation. Instead of cutting the object out, we "show" the AI where to look by modifying the image itself.

---

## 2. Dynamic Radius Logic (Resolution-Aware)
A professional marker must scale with the image to ensure consistent AI performance.

*   **The Problem:** A static 20px radius is too large on mobile thumbnails and too small on 4k professional photos.
*   **The Solution:** Dynamic Radius calculation.
    *   **Formula:** `Radius = Image_Width / 50` (approx. 2% of horizontal span).
    *   **Minimum Clip:** 15px (ensures visibility on tiny assets).
    *   **Maximum Clip:** 100px (prevents covering too much context on massive assets).

---

## 3. Advanced Marking Techniques

### A. The "Red Ring" (Current Default)
*   **Visual:** A red hollow circle with a center dot.
*   **Strength:** Excellent for general-purpose VLMs (Gemini, LLaVA). It creates a "boundary" without obscuring the texture inside.
*   **Best For:** Clearly defined objects like watches, buttons, or flowers.

### B. The "Crosshairs" (Coordinate Anchor)
*   **Visual:** Two thin, high-contrast red lines (horizontal and vertical) intersecting at $(x, y)$.
*   **Strength:** Models like **Qwen2-VL** are trained on datasets with coordinate boxes. Crosshairs help the model's internal geometry engine "pin" the exact pixel of interest.
*   **Best For:** Tiny details (e.g., a specific screw, a line of text, or a distant pixel).

### C. The "Semi-Transparent Glow" (Foveal Focus)
*   **Visual:** A soft, radial red gradient that is brightest at $(x, y)$ and fades out.
*   **Strength:** Modern VLMs are trained on **natural images**. Hard geometric lines (rings/crosshairs) are "noise" that can confuse the model's feature extractor. A soft glow guides the model's **Attention Mechanism** more naturally, mimicking how human eyes focus (Foveal Vision).
*   **Best For:** Textures, materials, and "vibes" where hard edges would break the semantic flow.

---

## 4. Detailed Execution Flow

### Stage A: The Server-Side Handshake
1.  **Coordinate Capture**: User clicks at normalized `(x, y)`.
2.  **Resolution Assessment**: Server checks `image.size`.
3.  **Marker Selection**: Logic chooses between Ring, Crosshair, or Glow.
4.  **Compositing**: Pillow draws the selected marker onto a temporary copy of the image.

### Stage B: Visual Prompting
1.  **Vision Brain**: The marked image is sent to **Gemini 2.5 Pro**.
2.  **Contextual Logic**: The prompt is adjusted: *"Analyze the area highlighted by the [marker type]."*
3.  **JSON Extraction**: VLM performs the 10-point analysis and returns structured data.

---

## 5. Comparison: Red Ring vs. SAM2

| Feature | Red Ring Method | SAM2 (Segmentation) |
| :--- | :--- | :--- |
| **Speed** | **Instant** (PIL) | **Slow** (Model Inference) |
| **Precision** | Medium (Attention-based) | **Ultra** (Pixel-perfect) |
| **Context** | **High** (AI sees environment) | Low (AI is isolated) |
| **Implementation** | Pure Logic | Machine Learning |

---
**Report updated with Advanced Marking Logic (v2.1).**
