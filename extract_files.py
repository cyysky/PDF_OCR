import os
import pandas as pd
import fitz  # PyMuPDF
from pathlib import Path
import requests
import base64
from concurrent.futures import ThreadPoolExecutor
import time

# Configuration
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output_txt"
API_URL = "http://localhost:9501/v1/chat/completions"
MODEL_NAME = "llm_model"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return None

def extract_text_from_excel(excel_path):
    """Extract text from Excel file"""
    try:
        # Read all sheets
        excel_file = pd.read_excel(excel_path, sheet_name=None)
        text = ""
        for sheet_name, df in excel_file.items():
            text += f"\n--- Sheet: {sheet_name} ---\n"
            text += df.to_string(index=False)
        return text
    except Exception as e:
        print(f"Error extracting text from Excel {excel_path}: {e}")
        return None

def encode_image_from_bytes(image_bytes):
    """Encode image bytes to base64"""
    return base64.b64encode(image_bytes).decode("utf-8")

def convert_to_markdown(text_content, filename):
    """Convert extracted text to markdown using API"""
    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": "Convert the following document text to well-formatted Markdown. Preserve all information, structure headings appropriately, and format tables properly using Markdown syntax. Return only the Markdown content without any additional commentary."
                    },
                    {
                        "role": "user",
                        "content": text_content
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 4096
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error converting to markdown for {filename}: {e}")
        return None

def save_markdown(content, output_path):
    """Save markdown content to file"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error saving markdown file {output_path}: {e}")
        return False

def process_file(file_path):
    """Process a single file"""
    file_path = Path(file_path)
    print(f"Processing: {file_path.name}")
    
    # Extract text based on file type
    text_content = None
    if file_path.suffix.lower() == ".pdf":
        text_content = extract_text_from_pdf(file_path)
    elif file_path.suffix.lower() in [".xls", ".xlsx"]:
        text_content = extract_text_from_excel(file_path)
    
    if not text_content:
        return False
    
    # Convert to markdown
    markdown_content = convert_to_markdown(text_content, file_path.name)
    if not markdown_content:
        return False
    
    # Save markdown file
    output_path = Path(OUTPUT_FOLDER) / f"{file_path.stem}.md"
    success = save_markdown(markdown_content, output_path)
    
    if success:
        print(f"✓ Successfully processed: {file_path.name}")
    else:
        print(f"✗ Failed to save markdown for: {file_path.name}")
    
    return success

def main():
    """Main function to process all files"""
    # Create output folder
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    
    # Get all PDF and Excel files
    input_path = Path(INPUT_FOLDER)
    if not input_path.exists():
        print(f"Input folder '{INPUT_FOLDER}' not found!")
        return
    
    pdf_files = list(input_path.glob("*.pdf"))
    excel_files = list(input_path.glob("*.xls")) + list(input_path.glob("*.xlsx"))
    all_files = pdf_files + excel_files
    
    if not all_files:
        print(f"No PDF or Excel files found in '{INPUT_FOLDER}' folder!")
        return
    
    print(f"Found {len(all_files)} files to process")
    print(f"PDF files: {len(pdf_files)}")
    print(f"Excel files: {len(excel_files)}")
    
    # Process files
    successful = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(process_file, all_files)
        for result in results:
            if result:
                successful += 1
    
    print(f"\nProcessing completed!")
    print(f"Successfully processed: {successful}/{len(all_files)} files")
    print(f"Output saved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()