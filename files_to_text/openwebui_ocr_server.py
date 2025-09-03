import time
import os
import io
import logging
import base64
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor, as_completed
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="File to Text API Server")

# Config
API_URL = "http://localhost:7601/v1/chat/completions"
MODEL_NAME = "vision_model"
MAX_PAGES = 500
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
OCR_MAX_RETRIES = 3
OCR_RETRY_DELAY = 5

def setup_poppler():
    """Set up Poppler path for Windows if needed."""
    if os.name == 'nt':  # Windows
        poppler_path = os.path.join(os.path.dirname(__file__), "poppler", "Library", "bin")
        if os.path.exists(poppler_path):
            os.environ["PATH"] += os.pathsep + poppler_path

setup_poppler()

def validate_file_size(content: bytes, max_size: int = MAX_FILE_SIZE) -> None:
    """Validate file size does not exceed limit."""
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file content")
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {max_size / (1024*1024):.0f}MB")

def extract_filename(request: Request) -> str:
    """Extract filename from headers or generate one."""
    filename = request.headers.get("X-Filename")
    if filename:
        return filename
    
    content_type = request.headers.get("Content-Type", "")
    if "pdf" in content_type:
        return "document.pdf"
    elif "png" in content_type:
        return "image.png"
    elif "jpeg" in content_type or "jpg" in content_type:
        return "image.jpg"
    else:
        return "file"

def call_ocr_api(image_b64: str) -> Optional[str]:
    """Send one image (base64) to OCR API, with retries."""
    for attempt in range(1, OCR_MAX_RETRIES + 1):
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
                    "chat_template_kwargs": {"enable_thinking": False}
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OCR API error (attempt {attempt}/{OCR_MAX_RETRIES}): {e}")
            if attempt < OCR_MAX_RETRIES:
                time.sleep(OCR_RETRY_DELAY)
    return None

def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def process_image(image: Image.Image, page_num: int, filename: str, total_pages: int) -> Dict[str, Any]:
    """Process a single image and return document format."""
    try:
        # Convert image to base64
        image_b64 = image_to_base64(image)
        
        # Call OCR API
        text = call_ocr_api(image_b64)
        if text is None:
            raise RuntimeError(f"OCR failed for page {page_num}")
        
        # Return document format
        return {
            "page_content": text,
            "metadata": {
                "page": page_num,
                "filename": filename,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error processing page {page_num}: {e}")
        raise

def process_pdf(pdf_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Process PDF file by converting to images and extracting text."""
    try:
        # Convert PDF to images
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,
            fmt='png',
            thread_count=5,
            userpw=None
        )
        
        if not images:
            raise HTTPException(status_code=422, detail="No pages extracted from PDF")
            
        if len(images) > MAX_PAGES:
            raise HTTPException(status_code=400, detail=f"PDF has {len(images)} pages, maximum allowed is {MAX_PAGES}")
        
        logger.info(f"Processing PDF '{filename}' with {len(images)} pages")
        
        # Process images concurrently
        documents = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(process_image, image, i + 1, filename, len(images)): i + 1 
                for i, image in enumerate(images)
            }
            
            # Collect results
            for future in as_completed(future_to_page):
                try:
                    doc = future.result()
                    documents.append(doc)
                except Exception as e:
                    page_num = future_to_page[future]
                    logger.error(f"Failed to process page {page_num}: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to process page {page_num}")
        
        # Sort documents by page number to ensure order
        documents.sort(key=lambda x: x["metadata"]["page"])
        return documents
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        elif "password" in str(e).lower() or "encrypted" in str(e).lower():
            raise HTTPException(status_code=422, detail="Password-protected PDFs are not supported")
        else:
            logger.error(f"Error processing PDF: {e}")
            raise HTTPException(status_code=422, detail=f"Failed to process PDF: {str(e)}")

def process_image_file(image_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Process a single image file."""
    try:
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to base64
        image_b64 = image_to_base64(image)
        
        # Call OCR API
        text = call_ocr_api(image_b64)
        if text is None:
            raise RuntimeError("OCR failed for image")
        
        # Return document format
        return [{
            "page_content": text,
            "metadata": {
                "page": 1,
                "filename": filename,
                "total_pages": 1
            }
        }]
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to process image: {str(e)}")

@app.put("/process")
async def process_file(request: Request) -> JSONResponse:
    """
    Process uploaded file (PDF or image) and return extracted text.
    
    Expects raw file bytes in request body with appropriate Content-Type header.
    Returns JSON array of document objects with page_content and metadata.
    """
    try:
        # Read request body
        content = await request.body()
        
        # Validate file size
        validate_file_size(content)
        
        # Extract filename
        filename = extract_filename(request)
        content_type = request.headers.get("Content-Type", "").lower()
        
        logger.info(f"Processing file: {filename} ({len(content)} bytes, {content_type})")
        
        # Process based on content type
        if "pdf" in content_type:
            documents = process_pdf(content, filename)
        elif any(img_type in content_type for img_type in ["png", "jpeg", "jpg"]):
            documents = process_image_file(content, filename)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload PDF or image files (PNG, JPG, JPEG)."
            )
        
        logger.info(f"Successfully processed {filename} with {len(documents)} pages")
        return JSONResponse(content=documents)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "File to Text API Server is running"}

if __name__ == "__main__":
    # Run with: python api_server.py
    uvicorn.run(app, host="0.0.0.0", port=7600)