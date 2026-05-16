# DrillDown: Full System Architecture & Model Flow
**Technical Deep-Dive: From Click to Generation**

---

## 1. The Entry Point: Interactive Canvas
Every interaction starts on the React frontend.
1.  **Normalization**: When a user clicks, the browser captures the pixel position $(X, Y)$ within the image element. 
2.  **Conversion**: These are converted to **normalized coordinates** $(x, y)$ between $0.0$ and $1.0$. 
    *   *Why?* This ensures that regardless of whether the image is displayed at 500px or 2000px, the server receives the same "percentage-based" location.

---

## 2. Path A: SAM2 Segmentation Flow (Isolation-Based)
This path is designed for **maximum precision** by removing all visual distractions.

### Step-by-Step Logic:
1.  **NumPy Conversion**: The server loads the image and converts it into a high-dimensional mathematical matrix (NumPy array).
2.  **Inference (Hiera Tiny)**: The click coordinates are fed into the **SAM2 Predictor**. 
    *   The model looks at the pixel you clicked and "expands" outwards, identifying edges where colors or textures change abruptly.
3.  **Mask Generation**: SAM2 outputs a **Binary Mask** (a 1-bit map where 1 is "Object" and 0 is "Background").
4.  **The Cutout**: 
    *   The system uses the mask to perform a **Bitwise AND** operation.
    *   *Result:* A new image where the object is perfectly preserved, but everything else is pure black.
5.  **Vision Prompting**: The black-background image is sent to the Vision Model.
    *   *AI Logic:* "I see an object floating in a void. There is nothing else to describe, so I will focus 100% on its specific materials and details."

---

## 3. Path B: Red Marker Flow (Attention-Based)
This path is designed to guide the AI's "internal eyes" while keeping the full image context intact.

### Step-by-Step Logic:
1.  **Dynamic Radius Calculation**:
    *   `radius = min(100, max(15, width // 50))`
    *   This ensures the marker size is always relative to the photo's quality.
2.  **Marker Branching**: Depending on the strategy, the system draws:
    *   **The Ring**: A geometric "fence" around the object. Good for general identification.
    *   **Crosshairs**: Precise horizontal/vertical lines. This forces the AI to look at the **center intersection**.
    *   **The Glow**: A soft red gradient. This mimics human **Foveal Vision** (how our eyes see details sharp in the center and blurry on edges).
3.  **Vision Prompting**: The full, marked image is sent to the Vision Model.
    *   **The "Spatial Anchor" Prompt**: *"Focus only on the area marked in RED."*
    *   *AI Logic:* "I see a full scene (a man, a library), but there is a red signal at these coordinates. I will anchor my high-level reasoning to that signal while using the surrounding scene for context (e.g., 'the watch belongs to the man')."

---

## 4. The Shared Convergence: Semantic JSON Extraction
Both Path A and Path B end at the same "Brain" (Gemini 2.5 Pro).

1.  **JSON Schema Enforcement**: The model is forced to output a structured JSON object.
2.  **10-Point Analysis**: It fills fields like `materials`, `style`, `design_details`, and `drill_topic`.
3.  **Cache Save**: The system saves this metadata to a `.json` file. If you click that spot again, the system loads this data in milliseconds instead of calling the AI again.

---

## 5. Final Execution: Generative Continuation
The last step turns words back into a new image.
1.  **Topic Bridge**: The system takes the `drill_topic` (e.g., "The inner gear mechanism of a watch").
2.  **Prompt Engineering**: It wraps the topic in high-quality photography keywords: *"Professional macro photography of [drill_topic], hyper-detailed, 8k."*
3.  **Imagen 4.0 Inference**: The generator creates the next level of the infinite canvas.
4.  **History Append**: The new image is added to your navigation strip at the bottom.

---

## Summary Comparison

| Metric | SAM2 Path | Red Marker Path |
| :--- | :--- | :--- |
| **Logic** | **Isolate** the pixels | **Point** at the pixels |
| **Input** | Clean Cutout | Annotated Scene |
| **AI Focus** | 100% Force | 80% Guidance |
| **Best Result** | Accuracy of materials | Storytelling context |

---
**Document generated for Project DrillDown Architectural Review.**
