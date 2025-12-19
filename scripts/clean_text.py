import json
import re
from pathlib import Path

def clean_text(text):
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Basic header/footer removal heuristics (can be tuned based on specific PDF)
    # Example: Remove page numbers if they appear alone
    # This is a simple cleaner; for PDR specifically, we might want to strip common headers if known.
    
    # Fix hyphenated words at end of lines (e.g. "medi-\ncine" -> "medicine")
    # Since we already joined lines with space, we look for "- " pattern that might have been a split.
    # However, pdfplumber usually handles extraction well. 
    # If the raw text had newlines, the regex above replaced them with spaces.
    # We might want to fix "word- word" -> "wordword" if it was a hyphenation.
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    return text

def process_file(input_path, output_path):
    print(f"Cleaning text from {input_path}...")
    count = 0
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            try:
                data = json.loads(line)
                raw_text = data.get("text", "")
                cleaned = clean_text(raw_text)
                
                if cleaned:
                    data["text"] = cleaned
                    fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                    count += 1
            except json.JSONDecodeError:
                continue
                
    print(f"Cleaned {count} pages. Saved to {output_path}")

if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    INPUT_FILE = SCRIPT_DIR / "raw_text.jsonl"
    OUTPUT_FILE = SCRIPT_DIR / "cleaned_text.jsonl"
    
    process_file(INPUT_FILE, OUTPUT_FILE)
