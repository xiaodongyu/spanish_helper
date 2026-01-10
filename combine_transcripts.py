#!/usr/bin/env python3
"""
Combine all transcript files in radios/transcript folder into a single file.
Each episode is separated by a clear separator.
"""

import os
from pathlib import Path
import re

def combine_transcripts(transcript_dir, output_filename="transcript_combined.txt"):
    """
    Combine all transcript files in the transcript directory into a single file.
    
    Args:
        transcript_dir: Path to the transcript directory
        output_filename: Name of the output combined file
    """
    transcript_dir = Path(transcript_dir)
    
    if not transcript_dir.exists():
        print(f"❌ Directory not found: {transcript_dir}")
        return False
    
    # Find all transcript files (excluding combined files)
    transcript_files = sorted([
        f for f in transcript_dir.glob("*.txt")
        if "combined" not in f.name.lower()
    ])
    
    if not transcript_files:
        print(f"❌ No transcript files found in {transcript_dir}")
        return False
    
    print(f"📁 Found {len(transcript_files)} transcript file(s)")
    
    # Separator for episodes
    separator = "=" * 80
    
    # Combine all transcripts
    combined_content = []
    combined_content.append(f"Complete Transcript\n")
    combined_content.append(f"Total Episodes: {len(transcript_files)}\n")
    combined_content.append(separator + "\n\n")
    
    for i, transcript_file in enumerate(transcript_files, 1):
        print(f"   Reading: {transcript_file.name}")
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Remove any existing headers/metadata from individual files
            # Look for lines like "Story X from: ..." and remove them
            lines = content.split('\n')
            cleaned_lines = []
            skip_header = True
            
            for line in lines:
                # Skip header lines
                if skip_header and (line.startswith("Story ") or line.startswith("=" * 60) or not line.strip()):
                    if line.startswith("=" * 60):
                        skip_header = False  # After separator, start including content
                    continue
                skip_header = False
                cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines).strip()
            
            # Add episode separator and content
            episode_header = f"\n\n{separator}\nEPISODE {i}\n{separator}\n\n"
            combined_content.append(episode_header)
            combined_content.append(cleaned_content)
            
        except Exception as e:
            print(f"   ⚠️  Error reading {transcript_file.name}: {str(e)}")
            continue
    
    # Write combined file
    output_path = transcript_dir / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(combined_content))
        f.write(f"\n\n{separator}\nEND OF TRANSCRIPT\n{separator}\n")
    
    print(f"\n✅ Combined transcript saved: {output_path.name}")
    print(f"   Total size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return True

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    transcript_dir = script_dir / "Duolinguo" / "radios" / "transcript"
    
    # Check if there's a subdirectory with transcripts
    subdirs = ["splitted results", "transcript"]
    found_dir = None
    
    # First check main directory
    if transcript_dir.exists() and list(transcript_dir.glob("*.txt")):
        found_dir = transcript_dir
    else:
        # Check subdirectories
        for subdir in subdirs:
            subdir_path = transcript_dir / subdir
            if subdir_path.exists() and list(subdir_path.glob("*.txt")):
                found_dir = subdir_path
                break
    
    if not found_dir:
        # Try main transcript directory
        found_dir = transcript_dir
    
    # Combine transcripts
    combine_transcripts(found_dir)

if __name__ == "__main__":
    main()
