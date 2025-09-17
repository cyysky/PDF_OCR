import os
import base64
import requests
import concurrent.futures
from tqdm import tqdm
import re
import time

# Config
INPUT_DIR = "preprocessed"
OUTPUT_DIR = "ocr_output"
API_URL = "http://localhost:4419/v1/chat/completions"
MODEL_NAME = "vision_model"

os.makedirs(OUTPUT_DIR, exist_ok=True)



def call_ocr_api(image_b64: str, max_retries: int = 3, delay: int = 5) -> str | None:
    """Send one image (base64) to OCR API, with retries. Returns None if all attempts fail."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                API_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                '''Extract all visible text and meaningful labels from the image as plain, structured prose suitable for ingestion into a knowledge graph or RAG system.
Convert textual content into coherent, semantically rich sentences grouped by logical themes (e.g., project details, annotations, equipment list, spatial layout).
Preserve contextual relationships by explicitly stating connections between entities (e.g., "The air handler unit (AHU-3) is located in the mechanical room and supplies conditioned air to Zone B via ductwork labeled DB-04").
Describe diagrams, arrows, airflow paths, equipment placements, seating arrangements, or architectural features as factual, spatially aware statements (e.g., "An arrow originating from the northwest corner flows toward the central control panel, indicating signal transmission from sensor S1 to PLC-2").
Include positional context only when it contributes to semantic meaning (e.g., "Label 'Main Inlet' is positioned adjacent to a circular valve symbol near the bottom-left quadrant of the diagram").
Avoid markdown formatting, bullet points, or section headers; instead, use natural transitions to separate ideas.
Output fluent, concise, and graph-friendly narrative text optimized for entity extraction, relationship mapping, and retrieval-augmented generation.'''
                            )
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                                }
                            ],
                        },
                    ],
                    "chat_template_kwargs": {"enable_thinking": False}
                },
                timeout=300,
                
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OCR API error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(delay)
    return None


def process_document(folder_name: str):
    """Process one document folder (multiple page images)."""
    folder_path = os.path.join(INPUT_DIR, folder_name)
    if not os.path.isdir(folder_path):
        return

    output_file = os.path.join(OUTPUT_DIR, f"{folder_name}.txt")
    # Skip if already processed
    if os.path.exists(output_file):
        print(f"Skipping {folder_name}, already processed.")
        return


    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s)]

    images = [f for f in os.listdir(folder_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    images.sort(key=natural_sort_key)
    texts = [""] * len(images)

    def ocr_page(idx_img):
        idx, img_name = idx_img
        img_path = os.path.join(folder_path, img_name)
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        text = call_ocr_api(img_b64)
        if text is None:
            raise RuntimeError(f"OCR failed for {img_name}")
        texts[idx] = text
        return img_name

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            list(tqdm(executor.map(ocr_page, enumerate(images)), total=len(images), desc=f"OCR {folder_name}", unit="page"))
    except Exception as e:
        print(f"Skipping {folder_name} due to OCR failure: {e}")
        return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(texts))
    print(f"OCR completed: {output_file}")


def main():
    for folder in os.listdir(INPUT_DIR):
        process_document(folder)


if __name__ == "__main__":
    main()
