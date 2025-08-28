# PDF and Document OCR Processing Pipeline

This repository contains a comprehensive suite of tools for processing PDF and DOCX documents through an OCR (Optical Character Recognition) pipeline. The system converts documents to images, applies preprocessing, and extracts text using vision models, with support for batch processing and file management.

## Overview

The pipeline consists of multiple stages:
1. **Document Preprocessing**: Convert PDF and DOCX files to standardized images
2. **OCR Processing**: Extract text from images using vision models
3. **File Management**: Organize and manage processed files

The system supports two OCR workflows with different model endpoints and provides utilities for file copying with duplicate detection.

## Core Components

### `input_preprocessing.py`
Preprocesses input documents by converting them to high-resolution images with automatic orientation correction.

**Key Features:**
- Converts PDF files to PNG images at 200dpi
- Converts DOCX files to PDF, then to PNG images
- Applies automatic orientation correction using Tesseract OSD
- Organizes output by source document in the `preprocessed/` directory

**Usage:**
```bash
python input_preprocessing.py
```

**Input/Output Structure:**
- Input: Documents placed in `input/` directory
- Output: Images organized in `preprocessed/{document_name}/` with naming pattern `{document_name}_page{number}.png`

### `ocr_vision.py`
Performs OCR on preprocessed images using a local vision model API.

**Key Features:**
- Sends images to vision API at `http://localhost:7601/v1/chat/completions`
- Uses concurrent processing for improved performance (5 threads)
- Preserves document structure with page separation
- Skips already processed documents
- Provides progress indication with tqdm

**Usage:**
```bash
python ocr_vision.py
```

**Input/Output Structure:**
- Input: Image folders in `preprocessed/` directory
- Output: Text files in `ocr_output/` directory with one file per document

### `process_pdfs.py`
Alternative OCR workflow that processes PDFs directly using a different local model.

**Key Features:**
- Uses OpenAI-compatible API at `http://localhost:5551/v1`
- Processes PDFs at 300dpi for higher quality
- Extracts text using the "rolmocr" model
- Moves processed PDFs to output folder
- Provides detailed progress reporting

**Usage:**
```bash
python process_pdfs.py
```

**Input/Output Structure:**
- Input: PDF files in `input_docs/` directory
- Output: Text files and original PDFs in `output/` directory

### `copy_files.py`
Utility for copying files with intelligent conflict resolution and duplicate detection.

**Key Features:**
- Copies files to output folder with flattened structure
- Uses MD5 hashing to detect identical files
- Skips duplicates with identical content
- Appends counters to filenames when content differs
- Supports recursive copying from subdirectories

**Usage:**
```bash
python copy_files.py input_folder output_folder
python copy_files.py input_folder output_folder -r  # recursive mode
```

## Dependencies

Install required packages:
```bash
pip install PyMuPDF docx2txt docx2pdf pdf2image pillow pytesseract requests tqdm openai
```

**Additional System Requirements:**
- Poppler (required by pdf2image)
- Tesseract OCR (required by pytesseract)
- Local vision model services running on ports 7601 and 5551

## Workflow

### Standard OCR Pipeline
1. Place PDF or DOCX files in the `input/` directory
2. Run preprocessing: `python input_preprocessing.py`
3. Run OCR: `python ocr_vision.py`
4. Find results in `ocr_output/` directory

### Alternative Direct PDF Processing
1. Place PDF files in the `input_docs/` directory
2. Run: `python process_pdfs.py`
3. Find results in `output/` directory

### File Organization
Use `copy_files.py` to organize files:
```bash
# Copy files non-recursively
python copy_files.py source_folder destination_folder

# Copy files recursively (including subdirectories)
python copy_files.py source_folder destination_folder -r
```

## Directory Structure
```
PDF_OCR/
├── input/                  # Input documents (PDF, DOCX)
├── input_docs/             # Input PDFs for direct processing
├── preprocessed/           # Output from input_preprocessing.py
├── ocr_output/             # Text output from ocr_vision.py
├── output/                 # Output from process_pdfs.py
├── input_preprocessing.py  # Document to image converter
├── ocr_vision.py           # Vision model OCR processor
├── process_pdfs.py         # Direct PDF OCR processor
├── copy_files.py           # File copying utility
└── README.md               # This documentation
```

## Configuration

### OCR API Endpoints
- `ocr_vision.py`: Modify `API_URL` and `MODEL_NAME` variables
- `process_pdfs.py`: Modify `client` initialization and model settings

### Processing Parameters
- Image resolution: Adjust DPI in preprocessing scripts
- Concurrent workers: Modify `max_workers` in `ocr_vision.py`
- OCR timeout: Adjust `timeout` parameter in API requests

## Error Handling
The system includes comprehensive error handling:
- Skips unsupported file types
- Continues processing after individual page failures
- Provides detailed error messages
- Implements retry logic for API calls
- Preserves original files during processing

## Best Practices
1. Ensure local OCR services are running before processing
2. Verify Poppler and Tesseract installations
3. Monitor system resources during batch processing
4. Backup original documents before large-scale processing
5. Check output quality for critical documents