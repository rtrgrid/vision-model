# Vision Engine to Magazine UI: Integration Spec
**Bridging the Backend AI with the "Infinite Canvas" Magazine Frontend**

---

## 1. Executive Summary
This document outlines how our existing Python/FastAPI Vision Engine (SAM2, Red Marker, Gemini 2.5 Pro) directly powers the specific UI components and aesthetic requirements defined in the `drilldown-magazine.html` design specification.

We have built a highly capable "brain" that analyzes images. The HTML spec defines a beautiful "body" to display that analysis. Here is how they fit together.

---

## 2. What We Built: The Vision Engine
Our current backend operates on a "Dual Grounding" architecture:

1.  **The Input (The Click):** The user clicks an $(x, y)$ coordinate on an image.
2.  **Visual Grounding (Two Paths):**
    *   **SAM2 (Precision Mode):** We use `segment-anything-2` to perfectly cut out the object, placing it on a pure black background.
    *   **Red Marker (Context Mode):** We use `Pillow` to draw a dynamic red ring, crosshair, or glow directly onto the image at the click coordinate.
3.  **Semantic Extraction:** The grounded image is sent to **Gemini 2.5 Pro**.
4.  **The Output (Structured JSON):** Gemini is forced to return a precise 10-point analysis.

**Example Current Output:**
```json
{
  "object": "mechanical watch escapement wheel",
  "materials": ["brass", "synthetic ruby"],
  "style": "precision engineering",
  "drill_topic": "how escapement wheels regulate time"
}
```

---

## 3. How the Engine Fits the Magazine HTML

The `drilldown-magazine.html` spec envisions an "editorial" layout where every click results in a polished, multi-faceted page, not just a single raw image.

### A. The "Demo Canvas" & Red Ring Compositing
*   **HTML Spec:** The HTML features a `.demo-canvas` where a `.red-ring` appears on click.
*   **Backend Fit:** This is exactly our **Path B (Red Marker Workflow)**. When the frontend registers a click, it can immediately render a CSS `.red-ring`. Simultaneously, it sends the coordinates to the server, where our `Pillow` logic replicates that exact ring on the server-side image before sending it to Gemini. This ensures the AI sees exactly what the user selected.

### B. Populating the "Magazine Page" (The Next Layer)
When a user clicks, the HTML spec describes moving to a "child layer" (e.g., `#layer1: Inside the Magma Chamber`).

Our Gemini JSON output directly populates these HTML elements:
*   **`.demo-title` / `<h1 class="font-playfair">`:** We will map the Gemini `drill_topic` (or a newly prompted `editorial_headline`) to this large serif header.
*   **The Main Illustration:** The `drill_topic` is sent to **Imagen 4.0** to generate the new background image for that layer.
*   **The Body Text:** *Gap Identified.* Currently, our JSON is highly technical. To fit the magazine vibe, we must update the Gemini prompt to generate an `editorial_paragraph` (2-3 sentences explaining the object elegantly) to render alongside the image.

### C. The "Ecommerce Expansion" (The Product Panel)
*   **HTML Spec:** The HTML includes a `.product-panel` that slides out, showing items with `brand`, `price`, and `product-search-tag`.
*   **Backend Fit:** This utilizes the raw data points from our 10-point analysis.
    *   Gemini's `object` extraction (e.g., "leather aviator jacket") becomes the query for a Shopping API.
    *   Gemini's `materials` and `style` extractions become the `.product-search-tag` badges on the frontend.

### D. The "Style Coherence" Requirement
*   **HTML Spec:** The architecture notes mandate a "watercolor style preserved across every page."
*   **Backend Fit:** Our image generation pipeline (using Imagen 4.0) must be updated. We will prepend a strict style enforcement string to every generated prompt: *"In the style of a delicate, pale watercolor illustration..."* ensuring the output matches the HTML's `--watercolor-cream` and `--watercolor-green` aesthetic.

---

## 4. The Action Plan (Next Steps)

To fully realize the Magazine Variant, we need to adapt our backend output to feed the specific CSS/HTML structure of the spec:

1.  **Prompt Engineering Update:** Modify `page_service.py` to instruct Gemini to generate an `editorial_headline` and an `explainer_paragraph` in addition to the raw technical data.
2.  **Style Enforcer:** Hardcode the "watercolor style" into the Imagen 4.0 prompt builder in the backend so all child images match the magazine's vibe.
3.  **Frontend Layout:** Build a new React component that consumes this updated JSON and renders the large serif titles, the explainer text, and the watercolor image in the layout defined by the HTML spec.

---
*Prepared by Gemini CLI based on the DrillDown Magazine Specification.*
