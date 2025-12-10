# A quick script to hash a directory in PaxD format.
# It should iterate all files in chosen-dir/src, and output it in YAML format.

# example output:
"""
  checksums:
      path/to/file/1/excluding/src/and/dirs/before.txt: sha256:abcdef1234567890
      path/to/file/2/excluding/src/and/dirs/before.txt: sha256:1234567890abcdef
"""

import os
import hashlib
import sys

if len(sys.argv) != 2:
    print("Usage: python hasher.py <directory_name>")
    sys.exit(1)
    
directory_name = sys.argv[1]
base_path = os.path.join(directory_name, "src")

if not os.path.exists(base_path):
    print(f"Directory {base_path} does not exist.")
    sys.exit(1)
    
checksums = {}
for root, _, files in os.walk(base_path):
    for file in files:
        file_path = os.path.join(root, file)
        relative_path = os.path.relpath(file_path, base_path)
        
        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksums[relative_path] = f"sha256:{sha256_hash.hexdigest()}"
        
# Output in YAML format (indented by one extra, so it can be pasted into paxd yaml file)
print("Place the following in the 'install' section of your paxd yaml file, overwriting any existing checksums:\n\n")
print("  checksums:")
for path, checksum in checksums.items():
    print(f"    {path}: {checksum}")