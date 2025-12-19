"""
Text Chunking Script for RAG Pipeline

Segments cleaned text into overlapping chunks with rich metadata.
Uses sliding window approach with sentence-boundary awareness.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm


class TextChunker:
    """Chunk text into overlapping segments with metadata."""
    
    def __init__(
        self,
        input_dir: str = "processed/raw_text",
        output_file: str = "processed/chunks/chunks.jsonl",
        chunk_size: int = 1400,  # Target size (range: 1200-1600)
        overlap: int = 200
    ):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Create output directory
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
    
    def find_sentence_boundary(self, text: str, target_pos: int, direction: str = "forward") -> int:
        """
        Find nearest sentence boundary from target position.
        
        Args:
            text: Full text
            target_pos: Starting search position
            direction: "forward" or "backward"
        
        Returns:
            Position of sentence boundary
        """
        sentence_endings = r'[.!?]\s+'
        
        if direction == "forward":
            # Search forward for sentence ending
            match = re.search(sentence_endings, text[target_pos:])
            if match:
                return target_pos + match.end()
            return min(target_pos + 100, len(text))  # Fallback
        
        elif direction == "backward":
            # Search backward for sentence ending
            text_before = text[:target_pos]
            matches = list(re.finditer(sentence_endings, text_before))
            if matches:
                return matches[-1].end()
            return max(0, target_pos - 100)  # Fallback
        
        return target_pos
    
    def chunk_text(self, text: str, source: str) -> List[Dict]:
        """
        Chunk a single document into overlapping segments.
        
        Args:
            text: Full document text
            source: Source filename
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        position = 0
        chunk_index = 0
        
        while position < len(text):
            # Calculate target chunk end
            target_end = position + self.chunk_size
            
            # Don't exceed text length
            if target_end >= len(text):
                chunk_end = len(text)
            else:
                # Find nearest sentence boundary
                chunk_end = self.find_sentence_boundary(text, target_end, direction="forward")
            
            # Extract chunk text
            chunk_text = text[position:chunk_end].strip()
            
            # Skip if too small (except last chunk)
            if len(chunk_text) < 300 and chunk_end < len(text):
                position = chunk_end
                continue
            
            # Generate stable chunk ID using hash
            source_prefix = Path(source).stem.replace(' ', '_').replace('-', '_')
            text_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            chunk_id = f"{source_prefix}_{text_hash}_{chunk_index:03d}"
            
            # Create chunk metadata
            chunk = {
                "chunk_id": chunk_id,
                "source": source,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "chunk_index": chunk_index,
                "position_start": position,
                "position_end": chunk_end
            }
            
            chunks.append(chunk)
            chunk_index += 1
            
            # Move to next chunk with overlap
            position = chunk_end - self.overlap
            
            # Ensure we make progress (avoid infinite loop)
            if position <= chunks[-2]["position_start"] if len(chunks) > 1 else -1:
                position = chunk_end
        
        return chunks
    
    def process_all(self):
        """Process all text files and generate chunks."""
        txt_files = list(self.input_dir.glob("*.txt"))
        
        if not txt_files:
            print(f"No text files found in {self.input_dir}")
            return
        
        print(f"Found {len(txt_files)} text files")
        print(f"Chunking parameters: size={self.chunk_size}, overlap={self.overlap}")
        print()
        
        all_chunks = []
        stats = {
            'total_files': len(txt_files),
            'total_chunks': 0,
            'total_chars': 0,
            'chunk_sizes': []
        }
        
        # Process each file
        for txt_file in tqdm(txt_files, desc="Chunking texts"):
            try:
                # Read source text
                with open(txt_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Create chunks
                chunks = self.chunk_text(text, txt_file.name)
                all_chunks.extend(chunks)
                
                # Update statistics
                stats['total_chunks'] += len(chunks)
                stats['total_chars'] += sum(c['char_count'] for c in chunks)
                stats['chunk_sizes'].extend([c['char_count'] for c in chunks])
                
                tqdm.write(f"  ✓ {txt_file.name}: {len(chunks)} chunks")
            
            except Exception as e:
                tqdm.write(f"  ✗ {txt_file.name}: Error - {e}")
        
        # Save chunks as JSONL
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        # Calculate statistics
        if stats['chunk_sizes']:
            avg_size = sum(stats['chunk_sizes']) / len(stats['chunk_sizes'])
            min_size = min(stats['chunk_sizes'])
            max_size = max(stats['chunk_sizes'])
        else:
            avg_size = min_size = max_size = 0
        
        # Print results
        print("\n" + "="*60)
        print("CHUNKING COMPLETE")
        print("="*60)
        print(f"Total files processed: {stats['total_files']}")
        print(f"Total chunks created: {stats['total_chunks']}")
        print(f"Total characters: {stats['total_chars']:,}")
        print(f"\nChunk size statistics:")
        print(f"  Average: {avg_size:.0f} chars")
        print(f"  Minimum: {min_size} chars")
        print(f"  Maximum: {max_size} chars")
        print(f"\nOutput: {self.output_file}")
        print(f"  ({self.output_file.stat().st_size / 1024:.1f} KB)")
        print("="*60)


def main():
    chunker = TextChunker(
        input_dir="processed/raw_text",
        output_file="processed/chunks/chunks.jsonl",
        chunk_size=1400,
        overlap=200
    )
    chunker.process_all()


if __name__ == "__main__":
    main()
