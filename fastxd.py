# FastxD: A smaller version of PaxD, made to just download to a temp file, install one package, and delete itself.

import requests
import json
import os
import sys

# Store the script path early to avoid __file__ issues later
try:
    script_path = os.path.abspath(__file__)
except NameError:
    script_path = os.path.abspath(sys.argv[0])

repository = input("Enter the repository URL to use for FastxD (or leave empty for default repository): ").strip()
if not repository:
    repository = "https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main"
package = input("Enter the package name to install via FastxD: ").strip()

def parse_jsonc(jsonc_text: str) -> dict:
    """Parse JSONC (JSON with comments) by removing comments."""
    import re
    
    # Remove single-line comments (// ...)
    lines = jsonc_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Find // that's not inside a string
        in_string = False
        escaped = False
        comment_pos = None
        
        for i, char in enumerate(line):
            if escaped:
                escaped = False
                continue
                
            if char == '\\' and in_string:
                escaped = True
                continue
                
            if char == '"' and not escaped:
                in_string = not in_string
                continue
                
            if not in_string and char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                comment_pos = i
                break
        
        if comment_pos is not None:
            cleaned_lines.append(line[:comment_pos].rstrip())
        else:
            cleaned_lines.append(line)
    
    cleaned_json = '\n'.join(cleaned_lines)
    return json.loads(cleaned_json)


def _cleanup():
    """Delete the downloaded main file and this script file."""
    global main_file_path, script_path
    if 'main_file_path' in globals() and os.path.exists(main_file_path):
        try:
            os.remove(main_file_path)
            print(f"Package '{package}' main file cleaned up.")
        except Exception as e:
            print(f"Could not remove main file: {e}")
    else:
        print(f"Could not find main file for package '{package}'. It may have already been deleted.")
        
    if os.path.exists(script_path):
        try:
            os.remove(script_path)
            print("FastxD script file cleaned up.")
        except Exception as e:
            print(f"Could not remove FastxD script: {e}")
    else:
        print("Could not find FastxD script file. It may have already been deleted.")
        
import atexit
atexit.register(_cleanup)

def _resolve_repository_url(repo_url):
    """Resolve repository URL by following redirects and return the final URL."""
    try:
        # Make a HEAD request to check for redirects without downloading content
        response = requests.head(repo_url, headers={"User-Agent": "FastxD/1.0.0"}, allow_redirects=True, timeout=10)

        # If we were redirected, keep repeating the previous logic until we get to a point we arent redirected
        if response.url != repo_url:
            return _resolve_repository_url(response.url)
        
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]
        return repo_url
    except Exception as e:
        # If resolution fails, fall back to original URL
        print(f"Warning: Could not resolve repository URL ({e}), using original URL")
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]
        return repo_url
        
repository = _resolve_repository_url(repository)

# GET {repo_url}/resolution
resolution_url = f"{repository}/resolution"
resolution_response = requests.get(resolution_url, headers={"User-Agent": "FastxD/1.0.0"}, allow_redirects=True)  # type: ignore
resolution_response.raise_for_status()
resolution_data = parse_jsonc(resolution_response.text)

# Check if package name needs to be resolved from alias to actual package name
resolved_package = None
for actual_package, aliases in resolution_data.items():
    if package in aliases:
        resolved_package = actual_package
        print(f"Resolving alias '{package}' to '{resolved_package}'")
        package = resolved_package
        break

# Get the paxd file for the package
try:
    response = requests.get(f"{repository}/packages/{package}/paxd", headers={"User-Agent": "FastxD/1.0.0"}, timeout=15)
    response.raise_for_status()
except Exception as e:
    print(f"ERROR: Could not fetch package '{package}' from repository '{repository}' ({e}). Does this package maybe use YAML? If so, it is not supported by FastxD. Installation aborted.")
    exit(1)

# Debug: Check response content
if not response.text.strip():
    print(f"ERROR: Empty response when fetching package '{package}' from repository '{repository}'. Installation aborted.")
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    exit(1)

try:
    response_json = parse_jsonc(response.text)
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in package '{package}' paxd file. Installation aborted.")
    print(f"JSON error: {e}")
    print(f"Response content (first 500 chars): {response.text[:500]}")
    exit(1)
if response_json["install"]["depend"]:
    print(f"WARN: Package '{package}' has dependencies which FastxD cannot install. You may experience errors if the following dependencies arent present:")
    for dep in response_json["install"]["depend"]:
        print(f"{dep.split(':')[1:]} ({dep.split(':')[0]})")

# Check if this package supports FastxD
if not response_json["install"].get("supports-fastxd", True):
    print(f"ERROR: Package '{package}' does not support FastxD installation. Installation aborted.")
    exit(1)

# Get the main file URL from the paxd file
try:
    main_file_url = response_json["install"]["mainfile"]
    if not main_file_url.startswith("http"):
        # If it's a relative URL, make it absolute
        main_file_url = f"{repository}/packages/{package}/src/{main_file_url}"
except KeyError:
    print(f"ERROR: Package '{package}' does not specify a mainfile. Installation aborted.")
    exit(1)

# Download the main file
try:
    print(f"Downloading main file from: {main_file_url}")
    main_file_response = requests.get(main_file_url, headers={"User-Agent": "FastxD/1.0.0"}, timeout=30)
    main_file_response.raise_for_status()
except Exception as e:
    print(f"ERROR: Could not download main file for package '{package}' ({e}). Installation aborted.")
    exit(1)

# Save the main file to a temp location
import tempfile
import os

temp_dir = tempfile.gettempdir()
# Get the original filename from the URL or use a default
original_filename = main_file_url.split('/')[-1] if '/' in main_file_url else f"{package}"
main_file_path = os.path.join(temp_dir, f"fastxd_{package}_{original_filename}")

with open(main_file_path, "wb") as main_file:
    main_file.write(main_file_response.content)

# Make the file executable if it's a script
if main_file_path.endswith(('.py', '.sh', '.bat', '.cmd')):
    try:
        os.chmod(main_file_path, 0o755)
    except:
        pass  # Ignore chmod errors on Windows

print(f"Package '{package}' downloaded successfully!")
print(f"Main file location: {main_file_path}")
print(f"You can now use the package, with 'python {main_file_path}'. When you're done, press Enter to clean up.")

input("Press Enter to continue and clean up the package...")
# Allow atexit to handle cleanup
