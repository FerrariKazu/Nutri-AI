# pip install pdfplumber

import pdfplumber
import json
import sys
from pathlib import Path

def extract_pdf(pdf_path, output_path):
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    
    if not pdf_path.exists():
        print(f"Error: File not found at {pdf_path}")
        return

    print(f"Extracting text from {pdf_path}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        with open(output_path, 'w', encoding='utf-8') as f:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    record = {
                        "page": i + 1,
                        "text": text
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{total_pages} pages...")
                    
    print(f"Extraction complete. Saved to {output_path}")

if __name__ == "__main__":
    # Default paths
    # Assuming herbal-pdrsmall.pdf is in the project root (one level up from scripts/)
    # or in the same directory. Adjust as needed.
    BASE_DIR = Path(__file__).parent.parent
    PDF_FILE = BASE_DIR / "herbal-pdrsmall.pdf"
    OUTPUT_FILE = Path(__file__).parent / "raw_text.jsonl"
    
    if len(sys.argv) > 1:
        PDF_FILE = sys.argv[1]
        
    extract_pdf(PDF_FILE, OUTPUT_FILE)
