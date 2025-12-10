#!/usr/bin/env python3
"""
PaxD Package Hasher Tool

This script iterates through each package folder in the packages/ directory,
calculates SHA256 hashes for all files in each package's src/ directory,
and updates the checksum section in the package's YAML file.

Usage: python hasher.py
"""

import os
import hashlib
import yaml
import sys

def calculate_file_hash(file_path):
    """Calculate SHA256 hash for a file using the same method as PaxD."""
    # Read the file and strip leading/trailing blank lines
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Strip leading and trailing whitespace/newlines
    content = content.strip()
    
    # Calculate hash of the stripped content
    return f"sha256:{hashlib.sha256(content).hexdigest()}"

def get_package_yaml_path(package_dir):
    """Find the package YAML file (package.yaml or paxd.yaml)."""
    yaml_files = ['package.yaml', 'paxd.yaml']
    for yaml_file in yaml_files:
        yaml_path = os.path.join(package_dir, yaml_file)
        if os.path.exists(yaml_path):
            return yaml_path
    return None

def hash_package_files(package_dir):
    """Hash all files in the src/ directory of a package."""
    src_dir = os.path.join(package_dir, "src")
    if not os.path.exists(src_dir):
        print(f"  Warning: No src/ directory found in {package_dir}")
        return {}
    
    checksums = {}
    for root, _, files in os.walk(src_dir):
        for file in files:
            file_path = os.path.join(root, file)
            # Get relative path from src/ directory
            relative_path = os.path.relpath(file_path, src_dir)
            # Normalize path separators to forward slashes (Unix-style)
            relative_path = relative_path.replace(os.sep, '/')
            
            try:
                checksum = calculate_file_hash(file_path)
                checksums[relative_path] = checksum
                print(f"    Hashed: {relative_path}")
            except Exception as e:
                print(f"    Error hashing {relative_path}: {e}")
    
    return checksums

def update_package_yaml(yaml_path, checksums):
    """Update the checksum section in the package YAML file."""
    try:
        # Read existing YAML
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # Ensure install section exists
        if 'install' not in data:
            data['install'] = {}
        
        # Remove old 'checksums' section if it exists
        if 'checksums' in data['install']:
            data['install'].pop('checksums', None)
            print(f"    Removed old 'checksums' section")
        
        # Update checksum section (singular)
        if checksums:
            data['install']['checksum'] = checksums
            print(f"    Updated checksum section with {len(checksums)} entries")
        else:
            # Remove checksum section if no files were found
            data['install'].pop('checksum', None)
            print(f"    Removed checksum section (no files found)")
        
        # Write updated YAML
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
        
        return True
    except Exception as e:
        print(f"    Error updating YAML file: {e}")
        return False

def main():
    """Main function to process all packages."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    packages_dir = script_dir
    
    print("PaxD Package Hasher Tool")
    print("=" * 40)
    print(f"Scanning packages in: {packages_dir}")
    print()
    
    processed_count = 0
    error_count = 0
    
    # Iterate through all directories in packages/
    for item in os.listdir(packages_dir):
        item_path = os.path.join(packages_dir, item)
        
        # Skip files and special directories
        if not os.path.isdir(item_path) or item.startswith('.') or item == '__pycache__':
            continue
        
        # Skip the script itself and other non-package directories
        if item in ['hasher.py', 'metapackages']:
            continue
        
        print(f"Processing package: {item}")
        
        # Find package YAML file
        yaml_path = get_package_yaml_path(item_path)
        if not yaml_path:
            print(f"  Warning: No package.yaml or paxd.yaml found in {item}")
            error_count += 1
            continue
        
        # Hash files in src/ directory
        checksums = hash_package_files(item_path)
        
        # Update YAML file
        if update_package_yaml(yaml_path, checksums):
            processed_count += 1
            print(f"  ✓ Successfully updated {os.path.basename(yaml_path)}")
        else:
            error_count += 1
            print(f"  ✗ Failed to update {os.path.basename(yaml_path)}")
        
        print()
    
    print("=" * 40)
    print(f"Processing complete!")
    print(f"Packages processed: {processed_count}")
    if error_count > 0:
        print(f"Errors encountered: {error_count}")
        sys.exit(1)
    else:
        print("All packages processed successfully!")

if __name__ == "__main__":
    main()