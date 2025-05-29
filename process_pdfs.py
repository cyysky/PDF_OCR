from openai import OpenAI
import base64
import os
import shutil
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io

client = OpenAI(api_key="123", base_url="http://localhost:5551/v1")
model = "rolmocr"

def encode_image_from_bytes(image_bytes):
    """Encode image bytes to base64"""
    return base64.b64encode(image_bytes).decode("utf-8")

def ocr_page_with_rolm(img_base64):
    """OCR a single page using ROLM model"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                    },
                    {
                        "type": "text",
                        "text": "Return the plain text representation of this document as if you were reading it naturally.\n",
                    },
                ],
            }
        ],
        temperature=0.2,
        max_tokens=4096
    )
    return response.choices[0].message.content

def pdf_to_images_and_ocr(pdf_path):
    """Convert PDF pages to images and OCR them"""
    doc = fitz.open(pdf_path)
    all_text = []
    
    for page_num in range(len(doc)):
        print(f"  Processing page {page_num + 1}/{len(doc)}")
        
        # Get page
        page = doc.load_page(page_num)
        
        # Convert to image (300 DPI for good quality)
        mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")
        
        # Encode to base64
        img_base64 = encode_image_from_bytes(img_bytes)
        
        # OCR the page
        try:
            page_text = ocr_page_with_rolm(img_base64)
            all_text.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
        except Exception as e:
            print(f"    Error processing page {page_num + 1}: {e}")
            all_text.append(f"--- Page {page_num + 1} ---\n[ERROR: Could not process this page]\n")
    
    doc.close()
    return "\n".join(all_text)

def process_all_pdfs():
    """Process all PDFs in input_docs folder"""
    input_folder = Path("input_docs")
    output_folder = Path("output")
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(input_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input_docs folder")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\nProcessing {i}/{len(pdf_files)}: {pdf_path.name}")
        
        try:
            # OCR the PDF
            extracted_text = pdf_to_images_and_ocr(pdf_path)
            
            # Save text file
            txt_filename = pdf_path.stem + ".txt"
            txt_path = output_folder / txt_filename
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            
            # Move PDF to output folder
            output_pdf_path = output_folder / pdf_path.name
            shutil.move(str(pdf_path), str(output_pdf_path))
            
            print(f"  ✓ Completed: {txt_filename} and {pdf_path.name} moved to output folder")
            
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path.name}: {e}")
            continue

if __name__ == "__main__":
    process_all_pdfs()
    print("\n🎉 All PDFs processed!")