import os
import base64
import requests
import concurrent.futures
from tqdm import tqdm

# Config
INPUT_DIR = "preprocessed"
OUTPUT_DIR = "ocr_output"
API_URL = "http://localhost:7601/v1/chat/completions"
MODEL_NAME = "vision_model"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def call_ocr_api(image_b64: str) -> str:
    """Send one image (base64) to OCR API."""
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
                            "Extract all visible text and meaningful labels from the image into clean Markdown. "
                            "Preserve structure by grouping textual information into logical sections (e.g., project details, notes, labels). "
                            "If the image contains diagrams, arrows, airflow lines, equipment, or seating layouts, describe them concisely "
                            "in Markdown as bullet points or short paragraphs. "
                            "Maintain clear separation between textual metadata and diagram descriptions. "
                            "If location is relevant (e.g., 'top-right corner', 'inside dome'), include it briefly. "
                            "Do not include any preambles, explanations, code fences, or adornments. "
                            "Only return direct Markdown content."
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
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OCR API error: {e}")
        return ""


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
    images = [f for f in os.listdir(folder_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    images.sort()
    texts = [""] * len(images)

    def ocr_page(idx_img):
        idx, img_name = idx_img
        img_path = os.path.join(folder_path, img_name)
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        text = call_ocr_api(img_b64)
        texts[idx] = text
        return img_name

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(ocr_page, enumerate(images)), total=len(images), desc=f"OCR {folder_name}", unit="page"))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(texts))
    print(f"OCR completed: {output_file}")


def main():
    for folder in os.listdir(INPUT_DIR):
        process_document(folder)


if __name__ == "__main__":
    main()
