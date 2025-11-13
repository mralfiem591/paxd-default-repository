#!/usr/bin/env python3
"""
Generate searchindex.csv for PaxD repository to enable fast package searching.

This script scans all packages in the repository and creates a CSV index file
containing package metadata for efficient searching without fetching individual
package files.

Usage:
    python generate_searchindex.py
    
Output:
    searchindex.csv - CSV file with package search metadata
"""

import os
import json
import csv
import yaml
from pathlib import Path

def parse_jsonc(jsonc_text: str) -> dict:
    """Parse JSONC (JSON with comments) by removing comments."""
    import re
    
    # Remove single-line comments (// ...)
    jsonc_text = re.sub(r'//.*?$', '', jsonc_text, flags=re.MULTILINE)
    
    # Remove multi-line comments (/* ... */)
    jsonc_text = re.sub(r'/\*.*?\*/', '', jsonc_text, flags=re.DOTALL)
    
    return json.loads(jsonc_text)

def compile_paxd_manifest(yaml_data: dict) -> dict:
    """Convert YAML data to PaxD manifest format."""
    
    manifest = {
        "pkg_info": {
            "pkg_name": yaml_data.get("name", "Unknown"),
            "pkg_author": yaml_data.get("author", "Unknown"),
            "pkg_version": yaml_data.get("version", "Unknown"),
            "pkg_description": yaml_data.get("description", "No description"),
            "pkg_license": yaml_data.get("license", "Unknown"),
            "tags": yaml_data.get("tags", [])
        },
        "install": {}
    }
    
    install_config = yaml_data.get("install", {})
    
    # Handle main executable and alias
    if "main_executable" in install_config:
        manifest["install"]["mainfile"] = install_config["main_executable"]
    
    if "command_alias" in install_config:
        manifest["install"]["alias"] = install_config["command_alias"]
    
    return manifest

def get_package_metadata(package_path: Path):
    """Extract metadata from a package directory."""
    package_id = package_path.name
    
    # Try different manifest files in order
    manifest_files = [
        ('paxd', 'json'),
        ('paxd.yaml', 'yaml'),
        ('package.yaml', 'yaml')
    ]
    
    for manifest_file, file_type in manifest_files:
        manifest_path = package_path / manifest_file
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if file_type == 'json':
                    package_data = parse_jsonc(content)
                else:  # yaml
                    yaml_data = yaml.safe_load(content)
                    package_data = compile_paxd_manifest(yaml_data)
                
                # Extract package info
                pkg_info = package_data.get('pkg_info', {})
                install_info = package_data.get('install', {})
                
                return {
                    'package_id': package_id,
                    'package_name': pkg_info.get('pkg_name', 'Unknown'),
                    'description': pkg_info.get('pkg_description', 'No description'),
                    'author': pkg_info.get('pkg_author', 'Unknown'),
                    'version': pkg_info.get('pkg_version', 'Unknown'),
                    'alias': install_info.get('alias', '')
                }
            except Exception as e:
                print(f"Warning: Error parsing {manifest_file} for {package_id}: {e}")
                continue
    
    return None

def load_resolution_data():
    """Load the resolution file to get package aliases."""
    resolution_path = Path('resolution')
    
    if not resolution_path.exists():
        print("Warning: resolution file not found")
        return {}
    
    try:
        with open(resolution_path, 'r', encoding='utf-8') as f:
            return parse_jsonc(f.read())
    except Exception as e:
        print(f"Warning: Error parsing resolution file: {e}")
        return {}

def generate_searchindex():
    """Generate searchindex.csv from all packages in the repository."""
    
    # Get packages directory
    packages_dir = Path('packages')
    
    if not packages_dir.exists():
        print("Error: packages directory not found!")
        return False
    
    # Load resolution data for aliases
    resolution_data = load_resolution_data()
    
    # Collect package data
    packages = []
    
    for package_path in sorted(packages_dir.iterdir()):
        if not package_path.is_dir():
            continue
        
        print(f"Processing {package_path.name}...")
        
        metadata = get_package_metadata(package_path)
        
        if metadata:
            # Get aliases from resolution
            package_id = metadata['package_id']
            aliases = resolution_data.get(package_id, [])
            
            # Convert aliases list to pipe-separated string
            metadata['aliases'] = '|'.join(aliases) if aliases else ''
            
            packages.append(metadata)
        else:
            print(f"Warning: Could not extract metadata from {package_path.name}")
    
    # Write CSV file
    csv_path = Path('searchindex.csv')
    
    if not packages:
        print("Error: No packages found!")
        print("Creating blank search index...")
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['package_id', 'package_name', 'description', 'author', 'version', 'alias', 'aliases']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        return True
    
    fieldnames = ['package_id', 'package_name', 'description', 'author', 'version', 'alias', 'aliases']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for package in packages:
            writer.writerow(package)
    
    print(f"\n✓ Successfully generated searchindex.csv with {len(packages)} packages")
    print(f"  Location: {csv_path.absolute()}")
    
    return True

if __name__ == '__main__':
    import sys
    
    print("PaxD Search Index Generator")
    print("=" * 60)
    
    success = generate_searchindex()
    
    if not success:
        sys.exit(1)
