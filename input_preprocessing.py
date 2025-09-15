import os
import fitz  # PyMuPDF for PDF handling
import docx2txt
from docx2pdf import convert as docx_to_pdf
import fitz  # PyMuPDF for PDF handling
from pathlib import Path
import shutil
import tempfile
import pytesseract
from PIL import Image

INPUT_DIR = "input"
OUTPUT_DIR = "preprocessed"


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def correct_orientation(image: Image.Image) -> Image.Image:
    """Use pytesseract to detect and correct orientation of an image"""
    try:
        osd = pytesseract.image_to_osd(image)
        rotation = 0
        for line in osd.split("\n"):
            if "Rotate:" in line:
                rotation = int(line.split(":")[-1].strip())
                break
        if rotation and rotation != 0:
            return image.rotate(-rotation, expand=True)
        pass
    except Exception as e:
        print(f"Orientation detection failed: {e}")
    return image


def process_pdf(file_path, output_folder, base_name):
    """Convert PDF to images at 200dpi and save per page with orientation corrected"""
    ensure_dir(output_folder)
    doc = fitz.open(file_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)
    doc.close()
    for i, page in enumerate(pages, start=1):
        page = correct_orientation(page)
        out_path = os.path.join(output_folder, f"{base_name}_page{i}.png")
        page.save(out_path, "PNG")
        print(out_path)


def process_docx(file_path, output_folder, base_name):
    """Convert DOCX to PDF then to images"""
    ensure_dir(output_folder)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = os.path.join(tmpdir, "temp.pdf")
        try:
            # Convert docx to pdf
            docx_to_pdf(file_path, tmp_pdf)
            # Convert PDF to images
            process_pdf(tmp_pdf, output_folder, base_name)
        except Exception as e:
            print(f"Failed to convert {file_path}: {e}")

def process_file(file_path):
    file_name = Path(file_path).stem
    output_folder = os.path.join(OUTPUT_DIR, file_name)
    ext = Path(file_path).suffix.lower()
    
    if ext == ".pdf":
        process_pdf(file_path, output_folder, file_name)
    elif ext == ".docx":
        process_docx(file_path, output_folder, file_name)
    else:
        print(f"Skipping unsupported file: {file_path}")


def walk_and_process(input_dir=INPUT_DIR):
    for root, _, files in os.walk(input_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            process_file(fpath)


if __name__ == "__main__":
    ensure_dir(OUTPUT_DIR)
    walk_and_process()
    print("Preprocessing completed. Images stored in", OUTPUT_DIR)