"""
PDF Extraction Script for RAG Pipeline

Extracts and cleans text from all PDFs in RAG2/ folder.
Uses pypdf as primary extractor, falls back to pdfminer.six on failures.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Disable problematic parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("Warning: pypdf not available, using pdfminer.six only")

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False
    print("Warning: pdfminer.six not available")

from tqdm import tqdm


class PDFExtractor:
    """Extract and clean text from PDF files."""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.errors = []
    
    def find_pdfs(self) -> List[Path]:
        """Find all PDF files in source directory."""
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
        
        pdfs = list(self.source_dir.glob("*.pdf")) + list(self.source_dir.glob("*.PDF"))
        print(f"Found {len(pdfs)} PDF files in {self.source_dir}")
        return pdfs
    
    def extract_with_pypdf(self, pdf_path: Path) -> Tuple[str, bool]:
        """Extract text using pypdf library."""
        if not PYPDF_AVAILABLE:
            return "", False
        
        try:
            reader = PdfReader(str(pdf_path))
            text_parts = []
            
            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    print(f"  Warning: Failed to extract page in {pdf_path.name}: {e}")
            
            full_text = "\n\n".join(text_parts)
            return full_text, True
        
        except Exception as e:
            return "", False
    
    def extract_with_pdfminer(self, pdf_path: Path) -> Tuple[str, bool]:
        """Fallback extraction using pdfminer.six."""
        if not PDFMINER_AVAILABLE:
            return "", False
        
        try:
            text = pdfminer_extract(str(pdf_path))
            return text, True
        except Exception as e:
            return "", False
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted PDF text.
        
        Steps:
        1. Remove multiple spaces
        2. Join broken sentences (line breaks mid-sentence)
        3. Remove page numbers
        4. Remove headers/footers (repeated patterns)
        5. Preserve section headings
        """
        if not text:
            return ""
        
        # Step 1: Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Step 2: Join broken sentences
        # If a line ends without punctuation and next starts lowercase, join them
        text = re.sub(r'(?<=[a-z,])\n(?=[a-z])', ' ', text)
        
        # Step 3: Remove standalone page numbers
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d+\s+of\s+\d+\b', '', text, flags=re.IGNORECASE)
        
        # Step 4: Remove common header/footer patterns
        # This is simplified - you may want to customize based on your PDFs
        text = re.sub(r'©\s*\d{4}.*?All rights reserved\.?', '', text, flags=re.IGNORECASE)
        
        # Step 5: Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Final whitespace cleanup
        text = text.strip()
        
        return text
    
    def extract_pdf(self, pdf_path: Path) -> Dict:
        """
        Extract and clean text from a single PDF.
        
        Returns:
            dict with 'success', 'text', 'method', 'error'
        """
        result = {
            'pdf': pdf_path.name,
            'success': False,
            'text': '',
            'method': None,
            'error': None
        }
        
        # Try pypdf first
        text, success = self.extract_with_pypdf(pdf_path)
        if success and text:
            result['success'] = True
            result['text'] = self.clean_text(text)
            result['method'] = 'pypdf'
            return result
        
        # Fallback to pdfminer
        text, success = self.extract_with_pdfminer(pdf_path)
        if success and text:
            result['success'] = True
            result['text'] = self.clean_text(text)
            result['method'] = 'pdfminer'
            return result
        
        # Both failed
        result['error'] = "Both pypdf and pdfminer failed to extract text"
        return result
    
    def process_all(self):
        """Process all PDFs in source directory."""
        pdfs = self.find_pdfs()
        
        if not pdfs:
            print("No PDF files found to process.")
            return
        
        print("\nExtracting and cleaning PDF text...")
        
        stats = {
            'total': len(pdfs),
            'success': 0,
            'failed': 0,
            'pypdf': 0,
            'pdfminer': 0
        }
        
        for pdf_path in tqdm(pdfs, desc="Processing PDFs"):
            result = self.extract_pdf(pdf_path)
            
            if result['success']:
                stats['success'] += 1
                stats[result['method']] += 1
                
                # Save cleaned text
                output_path = self.output_dir / f"{pdf_path.stem}.txt"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result['text'])
                
                tqdm.write(f"  ✓ {pdf_path.name} → {output_path.name} ({len(result['text'])} chars)")
            else:
                stats['failed'] += 1
                self.errors.append({
                    'pdf': pdf_path.name,
                    'error': result['error']
                })
                tqdm.write(f"  ✗ {pdf_path.name}: {result['error']}")
        
        # Save error log
        if self.errors:
            error_log = Path('processed/extraction_errors.json')
            with open(error_log, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2)
            print(f"\n⚠ Errors logged to: {error_log}")
        
        # Print statistics
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total PDFs: {stats['total']}")
        print(f"Successful: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        print(f"  - pypdf: {stats['pypdf']}")
        print(f"  - pdfminer: {stats['pdfminer']}")
        print(f"\nOutput directory: {self.output_dir}")
        print("="*60)


def main():
    source_dir = "RAG2"
    output_dir = "processed/raw_text"
    
    extractor = PDFExtractor(source_dir, output_dir)
    extractor.process_all()


if __name__ == "__main__":
    main()
