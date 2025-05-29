#!/usr/bin/env python3
import argparse
import shutil
import os
import hashlib
from pathlib import Path

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error calculating MD5 for {file_path}: {e}")
        return None

def copy_files(input_folder, output_folder, recursive=False):
    """
    Copy all files from input_folder to output_folder root (flattened structure).
    Only add suffixes when files have different content (based on MD5 hash).
    
    Args:
        input_folder (str): Source directory path
        output_folder (str): Destination directory path
        recursive (bool): Whether to include files from subdirectories
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Check if input folder exists
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist.")
        return False
    
    if not input_path.is_dir():
        print(f"Error: '{input_folder}' is not a directory.")
        return False
    
    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    copied_count = 0
    conflicts_resolved = 0
    skipped_duplicates = 0
    
    try:
        if recursive:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(input_path):
                root_path = Path(root)
                for file in files:
                    src_file = root_path / file
                    dest_file = output_path / file
                    
                    # Handle filename conflicts with MD5 comparison
                    if dest_file.exists():
                        src_md5 = calculate_md5(src_file)
                        dest_md5 = calculate_md5(dest_file)
                        
                        if src_md5 and dest_md5 and src_md5 == dest_md5:
                            # Files are identical, skip copying
                            print(f"Skipped duplicate: {src_file.relative_to(input_path)} (identical to existing {dest_file.name})")
                            skipped_duplicates += 1
                            continue
                        
                        # Files are different, need to create unique name
                        conflicts_resolved += 1
                        base_name = dest_file.stem
                        extension = dest_file.suffix
                        counter = 1
                        while dest_file.exists():
                            # Check if this numbered version is also identical
                            existing_md5 = calculate_md5(dest_file)
                            if src_md5 and existing_md5 and src_md5 == existing_md5:
                                print(f"Skipped duplicate: {src_file.relative_to(input_path)} (identical to existing {dest_file.name})")
                                skipped_duplicates += 1
                                break
                            dest_file = output_path / f"{base_name}_{counter}{extension}"
                            counter += 1
                        else:
                            # No identical file found, copy with new name
                            shutil.copy2(src_file, dest_file)
                            print(f"Conflict resolved: {src_file.relative_to(input_path)} -> {dest_file.name}")
                            copied_count += 1
                    else:
                        # No conflict, copy normally
                        shutil.copy2(src_file, dest_file)
                        print(f"Copied: {src_file.relative_to(input_path)} -> {dest_file.name}")
                        copied_count += 1
        else:
            # Copy only files from the root directory
            for item in input_path.iterdir():
                if item.is_file():
                    dest_file = output_path / item.name
                    
                    # Handle filename conflicts with MD5 comparison
                    if dest_file.exists():
                        src_md5 = calculate_md5(item)
                        dest_md5 = calculate_md5(dest_file)
                        
                        if src_md5 and dest_md5 and src_md5 == dest_md5:
                            # Files are identical, skip copying
                            print(f"Skipped duplicate: {item.name} (identical to existing)")
                            skipped_duplicates += 1
                            continue
                        
                        # Files are different, need to create unique name
                        conflicts_resolved += 1
                        base_name = dest_file.stem
                        extension = dest_file.suffix
                        counter = 1
                        while dest_file.exists():
                            # Check if this numbered version is also identical
                            existing_md5 = calculate_md5(dest_file)
                            if src_md5 and existing_md5 and src_md5 == existing_md5:
                                print(f"Skipped duplicate: {item.name} (identical to existing {dest_file.name})")
                                skipped_duplicates += 1
                                break
                            dest_file = output_path / f"{base_name}_{counter}{extension}"
                            counter += 1
                        else:
                            # No identical file found, copy with new name
                            shutil.copy2(item, dest_file)
                            print(f"Conflict resolved: {item.name} -> {dest_file.name}")
                            copied_count += 1
                    else:
                        # No conflict, copy normally
                        shutil.copy2(item, dest_file)
                        print(f"Copied: {item.name}")
                        copied_count += 1
        
        print(f"\nSummary:")
        print(f"Successfully copied {copied_count} files to '{output_folder}'")
        if conflicts_resolved > 0:
            print(f"Resolved {conflicts_resolved} filename conflicts with different content")
        if skipped_duplicates > 0:
            print(f"Skipped {skipped_duplicates} duplicate files (identical content)")
        return True
        
    except Exception as e:
        print(f"Error during copying: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Copy all files to output folder root (flattened structure)")
    parser.add_argument("input_folder", help="Path to the input folder")
    parser.add_argument("output_folder", help="Path to the output folder")
    parser.add_argument("-r", "--recursive", action="store_true", 
                       help="Include files from subdirectories (all copied to output root)")
    
    args = parser.parse_args()
    
    copy_files(args.input_folder, args.output_folder, args.recursive)

if __name__ == "__main__":
    main()