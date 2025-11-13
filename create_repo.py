from colorama import Fore, Style, init

init(autoreset=True)  # Initialize colorama with autoreset

print(Fore.CYAN + Style.BRIGHT + "\n=== PaxD Custom Repository Creation Script ===\n")

import os
directory = os.path.dirname(os.path.abspath(__file__))

if input(Fore.YELLOW + "This will initialise the directory of this script as a custom PaxD repository. " + Fore.RED + Style.BRIGHT + f"This can delete and overwrite files in this directory. PLEASE HAVE A BACKUP IF NEEDED! The directory is: {directory}\n\nType 'YES' in full capitals to continue: ") != "YES":
    print(Fore.RED + "Aborting repository creation.")
    exit(1)
    
# Step 1: if /packages, or /repoasset exist, delete them
def permission_error_handler(func, path, exc_info):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)
    
import shutil
for folder in ['packages', 'repoasset']:
    folder_path = os.path.join(directory, folder)
    if os.path.exists(folder_path):
        print(Fore.YELLOW + f"Removing existing '{folder}' directory...")
        shutil.rmtree(folder_path, onerror=permission_error_handler)
        
# Step 2: create /packages and /repoasset directories
os.makedirs(os.path.join(directory, 'packages'), exist_ok=True)
os.makedirs(os.path.join(directory, 'repoasset'), exist_ok=True)

# Step 3: start pulling some files from the default repository
default_repo = 'https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main'

import requests
required = [
    'SECURITY.md',
    'LICENSE',
    'README.md',
    'SEARCHINDEX.md',
    'generate_searchindex.py',
    'paxd',
    'certified',
    '.gitignore',
    'fastxd.py',
    'repoasset/certified.png',
    'repoasset/logo.png'
]

for entry in required:
    print(Fore.CYAN + f"Downloading '{entry}' from default repository...")
    url = f"{default_repo}/{entry}"
    response = requests.get(url)
    if response.status_code == 200:
        dest_path = os.path.join(directory, entry)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        print(Fore.GREEN + f"Successfully downloaded '{entry}'.")
    else:
        print(Fore.RED + f"Failed to download '{entry}'. HTTP Status Code: {response.status_code}")
        
# Step 4: small extras

# Create vulnerabilities and resolution with blank json dicts
with open(os.path.join(directory, 'vulnerabilities'), 'w', encoding='utf-8') as f:
    f.write("{}")
print(Fore.GREEN + "Created blank 'vulnerabilities' file.")
    
with open(os.path.join(directory, 'resolution'), 'w', encoding='utf-8') as f:
    f.write("{}")
print(Fore.GREEN + "Created blank 'resolution' file.")
    
# Create certified with blank json list
with open(os.path.join(directory, 'certified'), 'w', encoding='utf-8') as f:
    f.write("[]")
print(Fore.GREEN + "Created blank 'certified' file.")
    
# Generate initial searchindex.csv
print(Fore.CYAN + "Generating initial searchindex.csv...")
with open(os.path.join(directory, 'generate_searchindex.py'), 'r', encoding='utf-8') as f:
    exec(f.read())
print(Fore.GREEN + "searchindex.csv generated successfully.")
    
# Final message
print(Fore.GREEN + Style.BRIGHT + "\nRepository initialized successfully!\nYou can now add packages to the 'packages' directory and run 'generate_searchindex.py' to update the search index.\n")
print(Fore.YELLOW + "Remember to review and update the README.md and other documentation files to reflect your custom repository details.\n")
print(Fore.CYAN + "Thank you for using PaxD Repository Creator!\n")

# Self-delete
print(Fore.RED + "Cleanup success - self-deleted this script.")
os.remove(os.path.abspath(__file__))