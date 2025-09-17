#!/usr/bin/env python3
"""
Script to extract all original images from PDF files in the input1 directory and its subdirectories.
Uses PyMuPDF (fitz) to extract embedded images without rasterization.
"""

import fitz  # PyMuPDF
import os
from pathlib import Path
import shutil
from PIL import Image
import io

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extract all images from a single PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save extracted images
    """
    try:
        # Create output directory for this PDF
        pdf_name = Path(pdf_path).stem
        pdf_output_dir = Path(output_dir) / pdf_name
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        image_count = 0
        
        # Iterate through each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Get list of images on the page
            image_list = page.get_images(full=True)
            
            # Extract each image
            for img_index, img in enumerate(image_list):
                if img_index == 1:
                    try:
                        # Get the XREF of the image
                        xref = img[0]
                        
                        # Extract image bytes
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Create image file name
                        image_filename = f"page_{page_num+1:03d}_img_{img_index+1:03d}.{image_ext}"
                        image_path = pdf_output_dir / image_filename
                        
                        # Save the image
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        
                        image_count += 1
                        
                    except Exception as e:
                        print(f"Error extracting image {img_index+1} from page {page_num+1} in {pdf_path}: {e}")
                        continue
        
        doc.close()
        print(f"Extracted {image_count} images from {pdf_path} to {pdf_output_dir}")
        return image_count
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return 0

def extract_all_pdf_images(input_dir="input", output_dir="extracted_images"):
    """
    Extract images from all PDF files in the input directory and subdirectories.
    
    Args:
        input_dir (str): Directory containing PDF files
        output_dir (str): Directory to save all extracted images
    """
    # Convert to Path objects
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files recursively
    pdf_files = list(input_path.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_path}")
        return
    
    print(f"Found {len(pdf_files)} PDF files. Starting extraction...")
    
    total_images = 0
    
    # Process each PDF file
    for pdf_file in pdf_files:
        image_count = extract_images_from_pdf(str(pdf_file), str(output_path))
        total_images += image_count
    
    print(f"Extraction completed. Total images extracted: {total_images}")

if __name__ == "__main__":
    extract_all_pdf_images()