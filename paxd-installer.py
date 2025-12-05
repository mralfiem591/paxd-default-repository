# PaxD Installer
# A basic script to run when installing PaxD for the first time (as you would normally need PaxD to access the PaxD repo, where PaxD is located)
import ctypes
import os
try:
    import requests
except ImportError:
    print("ERROR: requests module is required but not found. Please install requests via 'pip install requests' and re-run the installer.")
    exit(1)

WINDOWS_AVAILABLE = os.name == "nt"

def is_admin() -> bool:
    """Check if the script is running with administrator privileges."""
    if not WINDOWS_AVAILABLE or ctypes is None:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False
    
if not is_admin():
    print("This installer requires administrator privileges to run.")
    print("Please re-run this script as an administrator.")
    print("\nHINT: If you are using the one-liner, make sure you run it in an administrator Command Prompt.")
    exit(1)

os.system("cls")

def _resolve_repository_url(repo_url):
    """Resolve repository URL by following redirects and return the final URL."""
    try:
        # Make a HEAD request to check for redirects without downloading content
        response = requests.head(repo_url, headers={"User-Agent": "PaxdInstaller/1.0.0"}, allow_redirects=True, timeout=10)

        # If we were redirected, keep repeating the previous logic until we get to a point we arent redirected
        if response.url != repo_url:
            return _resolve_repository_url(response.url)
        
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]
        return repo_url
    except Exception as e:
        # If resolution fails, fall back to original URL
        print(f"{Fore.YELLOW}Warning: Could not resolve repository URL ({e}), using original URL")
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]
        return repo_url

try:
    import subprocess
except ImportError:
    print("ERROR: subprocess module is required but not found. Installation cannot continue.")
    exit(1)

try:
    from colorama import Fore, init # type: ignore
    init(autoreset=True)
except ImportError:
    # Fallback when colorama is not available
    class Fore:
        RED = ""
        GREEN = ""
        YELLOW = ""
        LIGHTYELLOW_EX = ""
        LIGHTGREEN_EX = ""
        CYAN = ""
    
    class Style:
        BRIGHT = ""
    
    def init(autoreset=True):
        # Set _ to autoreset so that pylance doesn't complain about unused variable
        _ = autoreset
        pass
    
    print("WARNING: colorama module not found. Continuing without colored output.\nFor a better experience, consider installing colorama via 'pip install colorama'.")
    
try:
    from rich import traceback
    traceback.install()
except ImportError:
    print(f"{Fore.YELLOW}WARNING: rich module not found. Continuing without enhanced tracebacks.\nFor a better experience, consider installing rich via 'pip install rich'.")
    pass  # rich is not available, continue without it

def one_liner_cleanup():
    """Simply delete %TEMP%\\paxd_installer.py."""
    print(Fore.YELLOW + "Cleaning up installer file...")
    if os.path.exists(os.path.join(os.path.expandvars(r"%TEMP%"), "paxd_installer.py")):
        os.remove(os.path.join(os.path.expandvars(r"%TEMP%"), "paxd_installer.py"))

if os.path.join(os.path.expandvars(r"%TEMP%"), "paxd_installer.py") == os.path.abspath(__file__):
    print(Fore.GREEN + "One-liner detected, automatic cleanup enabled!")
    import atexit
    atexit.register(one_liner_cleanup)

print(Fore.CYAN + "Welcome to the PaxD Installer!")
print(Fore.CYAN + "This will install PaxD and set it up for first use.")
print()
print(Fore.YELLOW + "First, a quick question:")
repo = input(f"{Fore.YELLOW}Which repository would you like to set up PaxD with, and install it from? {Fore.LIGHTYELLOW_EX}(Note: The repository must be PaxD-ready, meaning it contains com.mralfiem591.paxd in it's repository) (default: https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main){Fore.YELLOW}: ").strip().lower()
if not repo:
    repo = "https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main"

repo = _resolve_repository_url(repo)
print(f"{Fore.GREEN}Repository URL resolved to: {Fore.CYAN}{repo}{Fore.GREEN}.")

paxd_ready = requests.get(f"{repo}/packages/com.mralfiem591.paxd/src/paxd.py", headers={"User-Agent": "PaxdInstaller/1.0.0"}, allow_redirects=True) # Some repositories always return 404 when looking for a folder - check for main.py instead
if paxd_ready.status_code != 200:
    print(Fore.RED + f"ERROR: The provided repository does not appear to be PaxD-ready (missing com.mralfiem591.paxd package) (checked: {repo}/packages/com.mralfiem591.paxd/src/paxd.py). Installation aborted.")
    print(Fore.RED + "HELP: Please ensure you provide a valid PaxD-ready repository URL. You can find such repositories on the PaxD website!")
    exit(1)
else:
    print(Fore.GREEN + "Repository verified as PaxD-ready.")

print(Fore.GREEN + "0- Pre-checks...")

print(Fore.GREEN + "   - Checking internet connection...")
if not os.system("ping -n 1 google.com >nul 2>&1") == 0:
    print(Fore.RED + "ERROR: No internet connection.")
    exit(1)
print(Fore.GREEN + "   - Internet connection is active.")

print(Fore.GREEN + "   - Checking OS...")
if os.name != "nt":
    print(Fore.RED + "ERROR: This installer only works on Windows.")
    exit(1)
print(Fore.GREEN + "   - OS is Windows.")

print(Fore.GREEN + "   - Ensuring LOCALAPPDATA directory exists...")
if not os.path.exists(os.path.expandvars(r"%LOCALAPPDATA%")):
    print(Fore.RED + "ERROR: LOCALAPPDATA directory does not exist. This installer only works on Windows.")
    print(Fore.RED + "Please create the LOCALAPPDATA directory and try again.")
    exit(1)
print(Fore.GREEN + "   - LOCALAPPDATA directory exists.")

print(Fore.GREEN + "   - Checking pip and python exist...")
if not os.system("uv self version >nul 2>&1") == 0:
    print(Fore.RED + "ERROR: uv is not installed or not in PATH. Please install uv (you can easily do this with 'pip install pipx && pipx install uv' for cmd.exe, 'pip install pipx; pipx install uv' for PowerShell) and ensure it is in PATH.")
    exit(1)
if not os.system("python --version >nul 2>&1") == 0:
    print(Fore.RED + "ERROR: python is not installed or not in PATH. Please install python and ensure it is in PATH.")
    exit(1)
    
print(Fore.GREEN + "   - uv and python are installed and in PATH.")
print()
print(Fore.GREEN + "All pre-checks passed.")
print()
if input(Fore.GREEN + f"Your system is ready for installation/repair! Proceed? (y/n): ").strip().lower() != "y":
    print(Fore.RED + "Installation/repair aborted by user.")
    exit(1)
    
if os.path.exists(os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")):
    import shutil
    shutil.rmtree(os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD"))

print(Fore.GREEN + "1- Writing repository file...")
local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
os.makedirs(os.path.join(local_app_data, "com.mralfiem591.paxd"), exist_ok=True)
with open(os.path.join(local_app_data, "com.mralfiem591.paxd", "repository"), "w") as repo_file:
    repo_file.write(repo + "\n")
    
print(Fore.GREEN + "2- Installing PaxD...")
file_response = requests.get(f"{repo}/packages/com.mralfiem591.paxd/src/paxd.py", headers={"User-Agent": "PaxdInstaller/1.0.0"}, allow_redirects=True)
file_response.raise_for_status()
file_data = file_response.text
with open(os.path.join(local_app_data, "com.mralfiem591.paxd", "paxd.py"), "w", encoding="utf-8") as paxd_file:
    paxd_file.write(file_data)
    
print(Fore.GREEN + "3- Writing .FIRSTRUN file...")
with open(os.path.join(local_app_data, "com.mralfiem591.paxd", ".FIRSTRUN"), "w") as firstrun_file:
    firstrun_file.write("This file indicates that the package has been run for the first time.")
    
print(Fore.GREEN + "4- Installing dependencies of PaxD...")
import sys
result = subprocess.run(["uv", "pip", "install", "--system", "--python", sys.executable, "requests", "colorama", "rich", "argparse", "sentry-sdk"])
if result.returncode != 0:
    print(Fore.RED + "ERROR: Failed to install dependencies via uv. Please ensure you have an active internet connection and try again.")

# install paxd-sdk
print(Fore.GREEN + "5- Installing PaxD SDK...")
sdk_response = requests.get(f"{repo}/packages/com.mralfiem591.paxd-sdk/src/main.py", headers={"User-Agent": "PaxdInstaller/1.0.0"}, allow_redirects=True)
sdk_response.raise_for_status()
sdk_data = sdk_response.text
os.makedirs(os.path.join(local_app_data, "com.mralfiem591.paxd-sdk"), exist_ok=True)
with open(os.path.join(local_app_data, "com.mralfiem591.paxd-sdk", "main.py"), "w", encoding="utf-8") as sdk_file:
    sdk_file.write(sdk_data)

print(Fore.LIGHTGREEN_EX + "NOTE: Dependencies that PaxD requires from the PaxD repository will be installed automatically when you first run PaxD, as they are not essential for the initialization.")

print(Fore.GREEN + "Success! PaxD has been installed.")
import time
time.sleep(0.7)
paxd_py_path = os.path.join(local_app_data, "com.mralfiem591.paxd", "paxd.py")
result = subprocess.run([sys.executable, paxd_py_path, "init", "-y"])
result2 = subprocess.run([sys.executable, paxd_py_path, "update", "paxd"])
if result.returncode == 0 and result2.returncode == 0:
    print(Fore.GREEN + "PaxD has been installed successfully and added to Path! Enjoy using PaxD. Simply run 'paxd' in a new Command Prompt to get started.")
    print(Fore.YELLOW + f'HINT: If \'paxd\' is not recognized, please restart your Command Prompt or computer to refresh environment variables. If it still isnt working, try \'"{sys.executable}" "{paxd_py_path}" init -y\' directly.')
else:
    print(Fore.YELLOW + f'WARNING: Could not fully complete installation of PaxD. You can retry the installation by running \'"{sys.executable}" "{paxd_py_path}" init -y\' in a Command Prompt.')
