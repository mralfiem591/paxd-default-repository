import os

import atexit

# Store the current file path for use in cleanup function
CURRENT_FILE_PATH = os.path.abspath(__file__)

SDK_BACKUP = False

def cleanup():
    # Check if the bat file exists and contains run_pkg.py (which is a bug)
    bat_file_path = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD", "bin", "paxd.bat")
    needs_rewrite = False
    if os.path.exists(bat_file_path):
        try:
            with open(bat_file_path, 'r') as f:
                content = f.read()
                if "run_pkg.py" in content:
                    needs_rewrite = True
        except (IOError, OSError):
            needs_rewrite = True
    else:
        needs_rewrite = True
    
    if needs_rewrite:
        # Ensure the bin directory exists
        os.makedirs(os.path.dirname(bat_file_path), exist_ok=True)
        with open(bat_file_path, 'w') as f:
            f.write("@echo off\n")
            f.write(f"python {CURRENT_FILE_PATH} %*\n")

atexit.register(cleanup)

import subprocess
import requests # type: ignore (requests is in paxd file dependencies)
import json
from pathlib import Path as PathLib
import hashlib
import shutil
import sys
import argparse # type: ignore (argparse is in paxd file dependencies)
from colorama import init, Fore, Style  # type: ignore (colorama is in paxd file dependencies)
import yaml # type: ignore (yaml is in paxd file dependencies)
import re

# Windows-specific imports with error handling
try:
    import ctypes
    import winreg
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    # Create mock objects to prevent attribute errors
    class MockModule:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    ctypes = MockModule()
    winreg = MockModule()

class DependencyError(Exception):
    """Custom exception for dependency resolution errors."""
    pass

class LexicographicConversionError(Exception):
    """Custom exception for lexicographic conversion errors."""
    pass

def find_sdk():
    import sys, importlib.abc, importlib.util

    if not os.path.exists(os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD', 'com.mralfiem591.paxd-sdk', 'main.py')):
        print("PaxD SDK is not installed. Please install PaxD SDK to run this package, via 'paxd install paxd-sdk'.")
        print("ALERT: PaxD SDK is required, but cannot be installed normally due to PaxD not being able to run. A forced installation will begin.")
        global SDK_BACKUP
        SDK_BACKUP = True

    SDK_PATH = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD', 'com.mralfiem591.paxd-sdk', 'main.py')

    class PaxDSDKLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None  # Use default module creation semantics

        def exec_module(self, module):
            with open(SDK_PATH, 'r') as f:
                code = f.read()
            exec(compile(code, SDK_PATH, 'exec'), module.__dict__)
        
    class PaxDSDKFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname == 'paxd_sdk':
                return importlib.util.spec_from_loader(fullname, PaxDSDKLoader())
            return None

    sys.meta_path.insert(0, PaxDSDKFinder())
    
try:
    find_sdk()
    import paxd_sdk  # type: ignore
    
    messages = paxd_sdk.Messaging.GetMessages("com.mralfiem591.paxd")
    
    if messages:
        print("New messages available!")
        for message in messages:
            print(f"{Fore.CYAN}--- MESSAGE START ---{Style.RESET_ALL}")
            print(f"FROM: {message['from']}")
            print(f"SENT: {message['timestamp']}")
            print("CONTENT:")
            for key, value in message['message'].items():
                print(f" - {key.title()}: {value}")
            print(f"{Fore.CYAN}--- MESSAGE END ---{Style.RESET_ALL}\n")
            
    paxd_sdk.Messaging.ClearMessages("com.mralfiem591.paxd")
except Exception:
    pass

lexicographic_max_default = 10000

def convert_to_lexicographic_position(n, max_range=lexicographic_max_default):
    """Convert a sequential number to its lexicographic position."""
    # Generate numbers as strings and sort them lexicographically
    string_numbers = [str(i) for i in range(max_range)]
    sorted_strings = sorted(string_numbers)
    
    # Return the number at position n
    if n < len(sorted_strings):
        return int(sorted_strings[n])
    else:
        # If n exceeds our range, raise a LexicographicConversionError
        raise LexicographicConversionError(f"Input {n} exceeds maximum range {max_range}")
    
LOGS_VERBOSE = {}

def parse_jsonc(jsonc_text: str) -> dict:
    """Parse JSONC (JSON with comments) by removing comments."""
    
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

def strip_jsonc_comments(jsonc_content: str) -> str:
    """Remove comments from JSONC content to make it valid JSON."""
    # Remove single-line comments (// ...)
    jsonc_content = re.sub(r'//.*?$', '', jsonc_content, flags=re.MULTILINE)
    
    # Remove multi-line comments (/* ... */)
    jsonc_content = re.sub(r'/\*.*?\*/', '', jsonc_content, flags=re.DOTALL)
    
    return jsonc_content

def parse_json_manifest(json_content: str) -> dict:
    """Parse JSON/JSONC manifest content."""
    # Strip comments if it's JSONC
    clean_json = strip_jsonc_comments(json_content)
    
    try:
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")

def compile_paxd_manifest(yaml_data: dict) -> dict:
    """Convert YAML data to PaxD manifest format."""
    
    # Validate required fields
    required_fields = ["name", "author", "version", "description", "license"]
    for field in required_fields:
        if field not in yaml_data:
            raise ValueError(f"Required field '{field}' missing from YAML")
    
    manifest = {
        "pkg_info": {
            "pkg_name": yaml_data["name"],
            "pkg_author": yaml_data["author"],
            "pkg_version": yaml_data["version"],
            "pkg_description": yaml_data["description"],
            "pkg_license": yaml_data["license"],
            "tags": yaml_data.get("tags", [])
        },
        "install": {}
    }
    
    install_config = yaml_data.get("install", {})
    
    # Handle files to include
    if "files" in install_config:
        manifest["install"]["include"] = install_config["files"]
    else:
        print("Warning: No 'files' specified in install section")
    
    # Handle dependencies
    if "dependencies" in install_config:
        deps = []
        dep_config = install_config["dependencies"]
        
        # Add pip dependencies
        if "pip" in dep_config:
            for pip_pkg in dep_config["pip"]:
                deps.append(f"pip:{pip_pkg}")
        
        # Add paxd dependencies
        if "paxd" in dep_config:
            for paxd_pkg in dep_config["paxd"]:
                deps.append(f"paxd:{paxd_pkg}")
        
        # Add other dependency types
        for dep_type, packages in dep_config.items():
            if dep_type not in ["pip", "paxd"] and isinstance(packages, list):
                for pkg in packages:
                    deps.append(f"{dep_type}:{pkg}")
        
        if deps:
            manifest["install"]["depend"] = deps
    
    # Handle checksums
    if "checksums" in install_config:
        manifest["install"]["checksum"] = install_config["checksums"]
    
    # Handle optional install settings
    optional_bool_settings = ["firstrun", "updaterun"]
    for setting in optional_bool_settings:
        if setting in install_config:
            manifest["install"][setting] = install_config[setting]
    
    # Handle exclude from updates
    if "exclude_from_updates" in install_config:
        manifest["install"]["update-ex"] = install_config["exclude_from_updates"]
    
    # Handle main executable and alias
    if "main_executable" in install_config:
        manifest["install"]["mainfile"] = install_config["main_executable"]
    
    if "command_alias" in install_config:
        manifest["install"]["alias"] = install_config["command_alias"]
    
    # Handle uninstall script
    if "uninstall_script" in yaml_data:
        manifest["uninstall"] = {
            "file": yaml_data["uninstall_script"]
        }
    
    return manifest

def permission_handler(func, path, exc_info):
    """Error handler for shutil.rmtree to handle permission errors."""
    import stat
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise

def is_admin() -> bool:
    """Check if the script is running with administrator privileges."""
    if not WINDOWS_AVAILABLE or ctypes is None:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False
    
def add_to_path(folder_path: str) -> bool:
    """Add folder to system PATH if not already present."""
    if not WINDOWS_AVAILABLE or winreg is None or ctypes is None:
        print("Windows registry access not available")
        return False
        
    folder_path = str(PathLib(folder_path).resolve())
    
    try:
        # Open the Environment registry key
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,  # type: ignore
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                           0, winreg.KEY_ALL_ACCESS) as key:  # type: ignore
            
            # Get current PATH value
            try:
                current_path, _ = winreg.QueryValueEx(key, "PATH")  # type: ignore
            except FileNotFoundError:
                current_path = ""
            
            # Check if folder is already in PATH
            path_entries = [p.strip() for p in current_path.split(os.pathsep)]
            if folder_path not in path_entries:
                # Add folder to PATH
                new_path = current_path + os.pathsep + folder_path
                try:
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)  # type: ignore
                    print(f"Added {folder_path} to system PATH")
                    print("Note the shell will need restarted before this takes effect!")
                    
                    # Try to notify system of environment change, but don't let it hang
                    try:
                        # Use SendMessageTimeout with a 5-second timeout to prevent hanging
                        import threading
                        
                        def notify_environment_change():
                            try:
                                # HWND_BROADCAST = 0xFFFF, WM_SETTINGCHANGE = 0x001A
                                ctypes.windll.user32.SendMessageTimeoutW( # type: ignore
                                    0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
                                )
                            except:
                                pass  # Ignore any errors during notification
                        
                        # Run notification in separate thread with timeout, due to an existing bug
                        notify_thread = threading.Thread(target=notify_environment_change, daemon=True)
                        notify_thread.start()
                        notify_thread.join(timeout=6.0)  # Wait max 6 seconds
                        
                    except Exception:
                        pass  # Ignore notification errors - the PATH change was successful
                    
                    return True
                except Exception as reg_error:
                    print(f"Failed to modify registry: {reg_error}")
                    return False
            else:
                print(f"{folder_path} is already in PATH")
                return True
                
    except Exception as e:
        print(f"Error modifying PATH: {e}")
        return False

class PaxD:
    def __init__(self, verbose=False):
        self.repository_file = os.path.join(os.path.dirname(__file__), "repository")
        self.paxd_version = "1.6.5"
        self.paxd_version_phrase = "The Authentication Update"
        # Check if a PAXD_GH_TOKEN environment variable is set for authentication
        self.paxd_auth_token = os.getenv("PAXD_GH_TOKEN", None)
        if self.paxd_auth_token:
            self.paxd_version_phrase += " (Authenticated)"
            self.headers = {"User-Agent": f"PaxdClient/{self.paxd_version}", "Authorization": f"token {self.paxd_auth_token}"}
        else:
            self.headers = {"User-Agent": f"PaxdClient/{self.paxd_version}"}
        self.verbose = verbose
    
    def _verbose_print(self, message, color=Fore.LIGHTBLACK_EX, mode=0):
        """Print message only in verbose mode with timestamp. (still log incase of exception, for Sentry, to provide more context)"""
        
        if mode == 0 or mode == 1:
            # Normal mode
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Get the lexicographic position BEFORE adding to the dict
            current_count = len(LOGS_VERBOSE)
            lexicographic_number = convert_to_lexicographic_position(current_count)
            
            LOGS_VERBOSE[f"({lexicographic_number}) {timestamp}"] = message # Also include the len of LOGS_VERBOSE so logs made at the exact same time are still valid and shown, instead of just the most recent one
            if self.verbose:
                print(f"{color}[{timestamp}] VERBOSE: {message}{Style.RESET_ALL}")
    
    def _verbose_timing_start(self, operation):
        """Start timing an operation in verbose mode."""
        if self.verbose:
            import time
            self._timing_start = time.time()
            self._verbose_print(f"Starting operation: {operation}", Fore.CYAN)
    
    def _verbose_timing_end(self, operation):
        """End timing an operation in verbose mode."""
        if self.verbose:
            import time
            if hasattr(self, '_timing_start'):
                elapsed = time.time() - self._timing_start
                self._verbose_print(f"Completed operation: {operation} (took {elapsed:.3f}s)", Fore.GREEN)

    def get_latest_version(self):
        """Fetch the latest version of PaxD from the repository."""
        self._verbose_timing_start("get_latest_version")
        self._verbose_print("Reading repository URL from file")
        repo_url = self._read_repository_url()
        self._verbose_print(f"Repository URL from file: {repo_url}")
        
        self._verbose_print("Resolving repository URL redirects")
        repo_url = self._resolve_repository_url(repo_url)
        self._verbose_print(f"Resolved repository URL: {repo_url}")
        
        self._verbose_print("Fetching latest PaxD version metadata")
        
        try:
            package_data, source_file = self._fetch_package_metadata(repo_url, "com.mralfiem591.paxd")
            self._verbose_print(f"Successfully fetched PaxD metadata from {source_file}")
            latest_version = package_data.get('pkg_info', {}).get('pkg_version', None)
            self._verbose_print(f"Latest version found: {latest_version}")
            self._verbose_timing_end("get_latest_version")
            return latest_version
        except Exception as e:
            self._verbose_print(f"Error fetching latest version: {e}")
            print(f"Error fetching latest version: {e}")
            self._verbose_timing_end("get_latest_version")
            return None

    def _read_repository_url(self):
        """Read the repository URL from the repository file."""
        self._verbose_print(f"Checking repository file exists: {self.repository_file}")
        if not os.path.exists(self.repository_file):
            self._verbose_print(f"Repository file not found at: {self.repository_file}")
            raise FileNotFoundError(f"Repository file not found: {self.repository_file}")
        
        self._verbose_print("Reading repository URL from file")
        with open(self.repository_file, 'r') as f:
            url = f.read().strip()
        self._verbose_print(f"Repository URL read: {url}")
        return url
    
    def _resolve_repository_url(self, repo_url):
        """Resolve repository URL by following redirects and return the final URL."""
        self._verbose_print(f"Resolving repository URL: {repo_url}")
        if repo_url.startswith("optimised::"):
            self._verbose_print("Repository URL is optimised - no resolution needed!")
            # Remove optimised:: from the URL, and return
            repo_url = repo_url[len("optimised::"):]
            if repo_url.endswith("/"):
                self._verbose_print("Removing trailing slash from URL")
                repo_url = repo_url[:-1]
            self._verbose_print(f"Trimmed optimised::, the url 'optimised::{repo_url}' has became '{repo_url}' and is being returned.")
            return repo_url
        try:
            # Make a HEAD request to check for redirects without downloading content
            self._verbose_print("Making HEAD request to check for redirects")
            response = requests.head(repo_url, headers=self.headers, allow_redirects=True, timeout=10) # type: ignore
            self._verbose_print(f"HEAD {repo_url}: {response.status_code}")
            self._verbose_print(f"HEAD request completed, final URL: {response.url}")

            # If we were redirected, keep repeating the previous logic until we get to a point we arent redirected
            if response.url != repo_url:
                self._verbose_print(f"Redirect detected: {repo_url} -> {response.url}, starting new iteration...")
                return self._resolve_repository_url(response.url)
            
            if repo_url.endswith("/"):
                self._verbose_print("Removing trailing slash from URL")
                repo_url = repo_url[:-1]
            self._verbose_print(f"Final resolved URL (for this iteration): {repo_url}")
            return repo_url
        except Exception as e:
            # If resolution fails, fall back to original URL
            self._verbose_print(f"URL resolution failed: {e}, falling back to original URL")
            print(f"{Fore.YELLOW}Warning: Could not resolve repository URL ({e}), using original URL")
            if repo_url.endswith("/"):
                self._verbose_print("Removing trailing slash from URL")
                repo_url = repo_url[:-1]
            return repo_url
    
    def _fetch_package_metadata(self, repo_url, package_name):
        """Fetch package metadata, trying both paxd and paxd.yaml files."""
        self._verbose_print(f"Fetching package metadata for: {package_name}")
        
        # First try the traditional paxd file
        package_url = f"{repo_url}/packages/{package_name}/paxd"
        self._verbose_print(f"Trying paxd file at: {package_url}")
        
        try:
            package_response = requests.get(package_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {package_url}: {package_response.status_code}")
            
            if package_response.status_code == 200:
                self._verbose_print("Found paxd file, parsing as JSONC")
                package_data = parse_jsonc(package_response.text)
                self._verbose_print("Successfully parsed paxd file")
                return package_data, "paxd"
        except Exception as e:
            self._verbose_print(f"Failed to fetch or parse paxd file: {e}")
        
        # If paxd file not found or failed, try paxd.yaml
        yaml_url = f"{repo_url}/packages/{package_name}/paxd.yaml"
        self._verbose_print(f"Trying paxd.yaml file at: {yaml_url}")
        
        try:
            yaml_response = requests.get(yaml_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {yaml_url}: {yaml_response.status_code}")
            
            if yaml_response.status_code == 200:
                self._verbose_print("Found paxd.yaml file, parsing as YAML")
                yaml_data = yaml.safe_load(yaml_response.text)
                if not yaml_data:
                    raise ValueError("YAML file appears to be empty or invalid")
                
                # Convert YAML to paxd manifest format using compiler code
                self._verbose_print("Converting YAML to paxd manifest format")
                package_data = compile_paxd_manifest(yaml_data)
                self._verbose_print("Successfully converted YAML to paxd format")
                return package_data, "paxd.yaml"
        except Exception as e:
            self._verbose_print(f"Failed to fetch or parse paxd.yaml file: {e}")

        yaml_url2 = f"{repo_url}/packages/{package_name}/package.yaml"
        self._verbose_print(f"Trying package.yaml file at: {yaml_url2}")

        try:
            yaml_response = requests.get(yaml_url2, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {yaml_url2}: {yaml_response.status_code}")

            if yaml_response.status_code == 200:
                self._verbose_print("Found package.yaml file, parsing as YAML")
                yaml_data = yaml.safe_load(yaml_response.text)
                if not yaml_data:
                    raise ValueError("YAML file appears to be empty or invalid")
                
                # Convert YAML to paxd manifest format using compiler code
                self._verbose_print("Converting YAML to paxd manifest format")
                package_data = compile_paxd_manifest(yaml_data)
                self._verbose_print("Successfully converted YAML to paxd format")
                return package_data, "package.yaml"
        except Exception as e:
            self._verbose_print(f"Failed to fetch or parse package.yaml file: {e}")

        # If neither are found, try package.yaml
        
        # If all 3 files failed, check if it's a 404 and provide a friendly error
        self._verbose_print("paxd, package.yaml and paxd.yaml files failed, checking error type")
        package_response = requests.get(package_url, headers=self.headers, allow_redirects=True)  # type: ignore
        
        if package_response.status_code == 404:
            # Package not found - provide a user-friendly error
            raise FileNotFoundError(f"Package '{package_name}' not found in repository")
        else:
            # Other HTTP error - raise the original error for debugging
            package_response.raise_for_status()
        
        # This shouldn't be reached, but just in case
        raise FileNotFoundError(f"Could not find package metadata for {package_name}")

    def install(self, package_name, user_requested=False, skip_checksum=False): # type: ignore
        """Install a package using the PaxD repository.
        
        Args:
            package_name: Name of the package to install
            user_requested: True if installed directly by user, False if installed as dependency
        """
        self._verbose_timing_start(f"install {package_name}")
        self._verbose_print(f"Installing package: {package_name} (user_requested={user_requested})")
        
        try:
            # Read and resolve repository URL
            self._verbose_print("Reading and resolving repository URL")
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            self._verbose_print(f"Local app data directory: {local_app_data}")
            
            # GET {repo_url}/paxd - this validates that the URL is a valid paxd repo
            paxd_url = f"{repo_url}/paxd"
            self._verbose_print(f"Validating repository at: {paxd_url}")
            response = requests.get(paxd_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {paxd_url}: {response.status_code}")
            self._verbose_print(f"Repository validation response: {response.status_code}")
            
            # if the response contains a repo_info dict, it's a valid repo, otherwise, invalid
            if response.status_code == 200:
                try:
                    self._verbose_print("Parsing repository info")
                    repo_data = parse_jsonc(response.text)
                    if "repo_info" in repo_data:
                        repo_name = repo_data.get('repo_info', {}).get('repo_name', 'Unknown')
                        self._verbose_print(f"Valid repository found: {repo_name}")
                        print(f"{Fore.GREEN}Valid PaxD repository found at {Fore.CYAN}{repo_url}")
                    else:
                        self._verbose_print("Invalid repository: no repo_info found")
                        print(f"{Fore.RED}Invalid PaxD repository at {Fore.CYAN}{repo_url}")
                        raise ValueError("Invalid PaxD repository")
                except json.JSONDecodeError as e:
                    self._verbose_print(f"JSON decode error validating repository: {e}")
                    print(f"Invalid JSON response from repository: {e}")
                    raise ValueError("Invalid PaxD repository")
            else:
                self._verbose_print(f"Repository validation failed with status {response.status_code}")
                print(f"Invalid PaxD repository at {repo_url}")
                raise ValueError("Invalid PaxD repository")

            # GET {repo_url}/resolution
            resolution_url = f"{repo_url}/resolution"
            self._verbose_print(f"Fetching resolution data from: {resolution_url}")
            resolution_response = requests.get(resolution_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {resolution_url}: {resolution_response.status_code}")
            self._verbose_print(f"Resolution response status: {resolution_response.status_code}")
            resolution_response.raise_for_status()
            resolution_data = parse_jsonc(resolution_response.text)
            self._verbose_print(f"Resolution data contains {len(resolution_data)} packages")
            
            # Check if package name needs to be resolved from alias to actual package name
            self._verbose_print(f"Checking if '{package_name}' is an alias")
            resolved_package = None
            for actual_package, aliases in resolution_data.items():
                if package_name in aliases:
                    resolved_package = actual_package
                    self._verbose_print(f"Alias '{package_name}' resolved to '{resolved_package}'")
                    print(f"Resolving alias '{package_name}' to '{resolved_package}'")
                    package_name = resolved_package
                    break
            
            if resolved_package is None:
                self._verbose_print(f"'{package_name}' is not an alias, using as direct package name")
                
            # Check if package is already installed
            package_install_path = os.path.join(local_app_data, package_name)
            self._verbose_print(f"Checking if package already installed at: {package_install_path}")
            if os.path.exists(package_install_path):
                self._verbose_print("Package directory already exists")
                if user_requested:
                    # User is manually installing a package that already exists
                    user_installed_file = os.path.join(package_install_path, ".USER_INSTALLED")
                    self._verbose_print(f"Checking user-installed marker: {user_installed_file}")
                    if os.path.exists(user_installed_file):
                        self._verbose_print("Package is already user-installed")
                        print(f"{Fore.YELLOW}Package '{Fore.CYAN}{package_name}{Fore.YELLOW}' is already installed by user at {package_install_path}")
                        return
                    else:
                        # Package exists as dependency, convert to user-installed
                        self._verbose_print("Package exists as dependency, converting to user-installed")
                        print(f"{Fore.BLUE}Package '{Fore.CYAN}{package_name}{Fore.BLUE}' exists as dependency, converting to user-installed")
                        self._mark_as_user_installed(package_name)
                        return
                else:
                    # Installing as dependency, package already exists - that's fine
                    self._verbose_print("Package already exists, installing as dependency - nothing to do")
                    print(f"Package '{package_name}' is already installed at {package_install_path}")
                    return
            else:
                self._verbose_print("Package is not currently installed, proceeding with installation")
                
            # Check if package has an IMPORTANT file, if so, print it
            important_file_url = f"{repo_url}/packages/{package_name}/IMPORTANT"
            self._verbose_print(f"Checking for IMPORTANT file at: {important_file_url}")
            important_response = requests.get(important_file_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {important_file_url}: {important_response.status_code}")
            if important_response.status_code == 200:
                self._verbose_print("IMPORTANT file found, displaying to user")
                print(f"{Fore.YELLOW}Important information regarding package '{Fore.CYAN}{package_name}{Fore.YELLOW}':\n")
                print(f"{Fore.LIGHTMAGENTA_EX}{important_response.text}{Style.RESET_ALL}\n")
            
            # Fetch package metadata
            self._verbose_print(f"Fetching package metadata for: {package_name}")
            print(f"{Fore.CYAN}Fetching metadata for package {Fore.YELLOW}{package_name}{Fore.CYAN}...")
            package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
            self._verbose_print(f"Successfully fetched metadata from {source_file}")
            if source_file == "paxd.yaml":
                print(f"{Fore.GREEN}Found YAML package configuration, converted to paxd format")

            pkg_name_friendly = f"{Fore.GREEN}{package_data.get('pkg_info', {}).get('pkg_name', package_name)}{Style.RESET_ALL}, by {Fore.MAGENTA}{package_data.get('pkg_info', {}).get('pkg_author', 'Unknown Author')}{Style.RESET_ALL} ({Fore.BLUE}{package_data.get('pkg_info', {}).get('pkg_version', 'Unknown Version')}{Style.RESET_ALL})"
            self._verbose_print(f"Package info: {package_data.get('pkg_info', {})}")
            print(f"{Fore.GREEN}Retrieved package metadata for '{pkg_name_friendly}'")

            # Install dependencies and track them
            dependencies = set()
            dep_list = package_data.get("install", {}).get("depend", [])
            self._verbose_print(f"Package has {len(dep_list)} dependencies: {dep_list}")
            
            for dep in dep_list:
                dependencies.add(dep)
                self._verbose_print(f"Processing dependency: {dep}")
                try:
                    # Dependency begins with "pip:": use pip to install
                    if dep.startswith("pip:"):
                        pip_package = dep[len("pip:"):]
                        self._verbose_print(f"Installing pip package: {pip_package}")
                        print(f"{Fore.CYAN}Installing Python package '{Fore.YELLOW}{pip_package}{Fore.CYAN}' via pip")
                        result = os.system(f"pip install {pip_package}")
                        self._verbose_print(f"Pip install result code: {result}")
                    # Dependency begins with "winget": use winget to install
                    elif dep.startswith("winget:"):
                        winget_package = dep[len("winget:"):]
                        self._verbose_print(f"Installing winget package: {winget_package}")
                        print(f"{Fore.CYAN}Installing Windows package '{Fore.YELLOW}{winget_package}{Fore.CYAN}' via winget")
                        result = os.system(f"winget install {winget_package}")
                        self._verbose_print(f"Winget install result code: {result}")
                    # Dependency begins with "choco:": use choco to install
                    elif dep.startswith("choco:"):
                        choco_package = dep[len("choco:"):]
                        self._verbose_print(f"Installing choco package: {choco_package}")
                        print(f"{Fore.CYAN}Installing Chocolatey package '{Fore.YELLOW}{choco_package}{Fore.CYAN}' via choco")
                        result = os.system(f"choco install {choco_package}")
                        self._verbose_print(f"Choco install result code: {result}")
                    # Dependency begins with "npm:": use npm to install
                    elif dep.startswith("npm:"):
                        npm_package = dep[len("npm:"):]
                        self._verbose_print(f"Installing npm package: {npm_package}")
                        print(f"{Fore.CYAN}Installing Node.js package '{Fore.YELLOW}{npm_package}{Fore.CYAN}' via npm")
                        result = os.system(f"npm install {npm_package}")
                        self._verbose_print(f"NPM install result code: {result}")
                    # Dependency begins with "paxd:": call self.install on the package
                    elif dep.startswith("paxd:"):
                        paxd_package = dep[len("paxd:"):]
                        self._verbose_print(f"Installing PaxD dependency package: {paxd_package}")
                        print(f"{Fore.CYAN}Installing PaxD package '{Fore.YELLOW}{paxd_package}{Fore.CYAN}' via PaxD")
                        self.install(paxd_package, user_requested=False)
                        # Mark this package as a dependency
                        self._mark_as_dependency(paxd_package, package_name)
                        self._verbose_print(f"Marked {paxd_package} as dependency of {package_name}")
                    else:
                        self._verbose_print(f"Unknown dependency type: {dep}")
                        print(f"Unknown dependency type for '{dep}'")
                except Exception as e:
                    self._verbose_print(f"Failed to install dependency {dep}: {e}")
                    raise DependencyError(f"Failed to install dependency '{dep}': {e}")

            # For each file in package_data[install][include], GET that file and install (supporting relative paths like folder1/file2)
            include_files = package_data.get("install", {}).get("include", [])
            self._verbose_print(f"Installing {len(include_files)} files: {include_files}")
            
            for file in include_files:
                self._verbose_print(f"Processing file: {file}")
                if file == "README.html":
                    self._verbose_print("Skipping auto-generated README.html file")
                    print(f"{Fore.RED}File is an auto-generated README.html file - skipping...")
                    continue
                    
                file_url = f"{repo_url}/packages/{package_name}/src/{file}"
                self._verbose_print(f"Downloading file from: {file_url}")
                file_response = requests.get(file_url, headers=self.headers, allow_redirects=True)  # type: ignore
                self._verbose_print(f"GET {file_url}: {file_response.status_code}")
                self._verbose_print(f"File download response: {file_response.status_code}")
                file_response.raise_for_status()
                file_data = file_response.content
                self._verbose_print(f"Downloaded {len(file_data)} bytes")
                
                # Actually install this file to %LOCALAPPDATA%/<package_name>/{file}
                install_path = os.path.join(local_app_data, package_name, file)
                self._verbose_print(f"Installing file to: {install_path}")
                os.makedirs(os.path.dirname(install_path), exist_ok=True)
                with open(install_path, 'wb') as f:
                    f.write(file_data)
                self._verbose_print(f"Successfully wrote file to disk")
                
                # Check if this file has a checksum at package_data[install][checksum], if so, verify it
                expected_checksum = package_data.get("install", {}).get("checksum", {}).get(file)
                if expected_checksum and not skip_checksum:
                    self._verbose_print(f"Verifying checksum for {file}: expected {expected_checksum}")
                    # Also calculate checksum of the raw downloaded data for debugging
                    raw_checksum = f"sha256:{hashlib.sha256(file_data).hexdigest()}"
                    self._verbose_print(f"Raw downloaded data checksum: {raw_checksum}")
                    self._verbose_print(f"Downloaded data length: {len(file_data)} bytes")
                    # Verify the checksum
                    sha256 = hashlib.sha256()
                    with open(install_path, "rb") as f:
                        while True:
                            chunk: bytes = f.read(4096)
                            if not chunk:
                                break
                            sha256.update(chunk)
                    calculated_checksum = f"sha256:{sha256.hexdigest()}"
                    self._verbose_print(f"Calculated checksum: {calculated_checksum}")
                    if calculated_checksum == expected_checksum:
                        self._verbose_print("Checksum verification passed")
                        print(f"Checksum verified for {install_path}")
                    else:
                        self._verbose_print(f"Checksum verification failed: {calculated_checksum} != {expected_checksum}")
                        print(f"Checksum mismatch for {install_path}: {calculated_checksum} != {expected_checksum}")
                        # Delete the file if checksum verification fails
                        os.remove(install_path)
                        self._verbose_print(f"Deleted invalid file: {install_path}")
                        print(f"Deleted invalid file {install_path}")
                else:
                    self._verbose_print("No checksum verification required for this file")

            # If package_data[install][firstrun], create a .FIRSTRUN file. If this value is false or non-existent, ignore and continue
            firstrun_flag = package_data.get("install", {}).get("firstrun")
            self._verbose_print(f"Firstrun flag: {firstrun_flag}")
            if firstrun_flag:
                firstrun_path = os.path.join(local_app_data, package_name, ".FIRSTRUN")
                self._verbose_print(f"Creating .FIRSTRUN file at: {firstrun_path}")
                with open(firstrun_path, 'w') as f:
                    f.write("This file indicates that the package has been run for the first time.")
                print(f"Created .FIRSTRUN file at {firstrun_path}")
                
            # If package_data[install][mainfile] exists and has a value, run some code to make a bat file in a predefined directory that exists in PATH
            mainfile = package_data.get("install", {}).get("mainfile")
            self._verbose_print(f"Mainfile: {mainfile}")
            if mainfile:
                alias = package_data.get("install", {}).get("alias", mainfile.split(".")[0])
                self._verbose_print(f"Creating batch file with alias: {alias}")
                bat_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{alias}.bat")
                self._verbose_print(f"Batch file path: {bat_file_path}")
                if not os.path.exists(bat_file_path):
                    self._verbose_print("Creating new batch file")
                    with open(bat_file_path, 'w') as f:
                        f.write(f"@echo off\n")
                        f.write(f"python {os.path.join(local_app_data, 'com.mralfiem591.paxd', 'run_pkg.py')} {os.path.join(local_app_data, package_name, mainfile)} %*\n")
                    print(f"Created batch file at {bat_file_path}")
                else:
                    self._verbose_print("Batch file already exists, skipping creation")
            
            # Create version file for tracking updates
            version_file = os.path.join(local_app_data, package_name, ".VERSION")
            installed_version = package_data.get('pkg_info', {}).get('pkg_version', 'Unknown')
            self._verbose_print(f"Creating version file: {version_file} with version: {installed_version}")
            with open(version_file, 'w') as f:
                f.write(installed_version)
            
            # Save dependencies for future cleanup tracking
            deps_file = os.path.join(local_app_data, package_name, ".DEPENDENCIES")
            self._verbose_print(f"Saving {len(dependencies)} dependencies to: {deps_file}")
            with open(deps_file, 'w') as f:
                for dep in sorted(dependencies):
                    f.write(f"{dep}\n")
            
            # Mark as user-installed if requested by user (not as dependency)
            if user_requested:
                self._verbose_print("Marking package as user-installed")
                self._mark_as_user_installed(package_name)
            else:
                self._verbose_print("Package installed as dependency, not marking as user-installed")
            
            self._verbose_timing_end(f"install {package_name}")
            print(f"{Fore.GREEN}✓ Installed version {Fore.CYAN}{installed_version}{Fore.GREEN} of '{pkg_name_friendly}'{Style.RESET_ALL}")
            if mainfile:
                print(f"{Fore.YELLOW}Easily run it with '{Fore.GREEN}{alias if alias else mainfile.split('.')[0]}{Fore.YELLOW}' in your shell.")

        except FileNotFoundError as e:
            self._verbose_print(f"FileNotFoundError: {e}")
            self._verbose_timing_end(f"install {package_name}")
            error_msg = str(e)
            if "not found in repository" in error_msg:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.CYAN}Try searching for similar packages with: {Fore.GREEN}paxd search {package_name}")
            else:
                print(f"{Fore.RED}Error: {error_msg}")
        except requests.HTTPError as e:
            self._verbose_print(f"HTTPError: {e}")
            self._verbose_timing_end(f"install {package_name}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.CYAN}Try searching for similar packages with: {Fore.GREEN}paxd search {package_name}")
            else:
                print(f"{Fore.RED}HTTP error: {e}")
        except requests.RequestException as e:
            self._verbose_print(f"RequestException: {e}")
            self._verbose_timing_end(f"install {package_name}")
            print(f"{Fore.RED}Network error: {e}")
        except json.JSONDecodeError as e:
            self._verbose_print(f"JSONDecodeError: {e}")
            self._verbose_timing_end(f"install {package_name}")
            print(f"JSON parsing error: {e}")
        except DependencyError as e:
            self._verbose_print(f"DependencyError: {e}")
            self._verbose_timing_end(f"install {package_name}")
            print(f"Dependency error: {e}")
        except Exception as e:
            self._verbose_print(f"Unexpected error: {e}")
            self._verbose_timing_end(f"install {package_name}")
            print(f"Unexpected error: {e}")
    
    def uninstall(self, package_name):
        """Uninstall a package."""
        self._verbose_timing_start(f"uninstall {package_name}")
        self._verbose_print(f"Uninstalling package: {package_name}")
        print(f"{Fore.RED}Uninstalling {Fore.CYAN}{package_name}{Fore.RED}...")
        
        try:
            # Read and resolve repository URL
            self._verbose_print("Reading and resolving repository URL for uninstall")
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            self._verbose_print(f"Local app data directory: {local_app_data}")
            
            # GET {repo_url}/resolution
            resolution_url = f"{repo_url}/resolution"
            self._verbose_print(f"Fetching resolution data from: {resolution_url}")
            resolution_response = requests.get(resolution_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {resolution_url}: {resolution_response.status_code}")
            self._verbose_print(f"Resolution response status: {resolution_response.status_code}")
            resolution_response.raise_for_status()
            resolution_data = parse_jsonc(resolution_response.text)
            self._verbose_print(f"Resolution data contains {len(resolution_data)} packages")
            
            # Check if package name needs to be resolved from alias to actual package name
            self._verbose_print(f"Checking if '{package_name}' is an alias")
            resolved_package = None
            for actual_package, aliases in resolution_data.items():
                if package_name in aliases:
                    resolved_package = actual_package
                    print(f"{Fore.BLUE}Resolving alias '{Fore.YELLOW}{package_name}{Fore.BLUE}' to '{Fore.CYAN}{resolved_package}{Fore.BLUE}'")
                    package_name = resolved_package
                    break
                
            if package_name == "com.mralfiem591.paxd":
                print(f"{Fore.RED}Cannot uninstall PaxD itself using PaxD. Please uninstall manually.")
                return

            # Fetch package metadata
            self._verbose_print(f"Fetching package metadata for uninstall: {package_name}")
            package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
            self._verbose_print(f"Successfully fetched metadata from {source_file}")
            
            # Check if package is actually installed
            package_install_path = os.path.join(local_app_data, package_name)
            if not os.path.exists(package_install_path):
                if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{package_data.get('install', {}).get('alias', package_name)}.bat")):
                    print(f"{Fore.YELLOW}Package '{Fore.CYAN}{package_name}{Fore.YELLOW}' is already not installed, but found leftover files. Cleaning up...")
                    os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{package_data.get('install', {}).get('alias', package_name)}.bat"))
                print(f"{Fore.YELLOW}Package '{Fore.CYAN}{package_name}{Fore.YELLOW}' is already not installed.")
                return
            
            pkg_name_friendly = f"{Fore.GREEN}{package_data.get('pkg_info', {}).get('pkg_name', package_name)}{Style.RESET_ALL}, by {Fore.MAGENTA}{package_data.get('pkg_info', {}).get('pkg_author', 'Unknown Author')}{Style.RESET_ALL} ({Fore.BLUE}{package_data.get('pkg_info', {}).get('pkg_version', 'Unknown Version')}{Style.RESET_ALL})"
            print(f"{Fore.CYAN}Retrieved package metadata for '{pkg_name_friendly}'")
            
            # Remove the bat file from bin, if it exists
            bat_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{package_data.get('install', {}).get('alias', package_name)}.bat")
            if os.path.exists(bat_file_path):
                os.remove(bat_file_path)
                print(f"{Fore.RED}Deleted {bat_file_path}")

            # If package_data[uninstall][file] exists and has a value, run that file in a new shell window, closing it once it's done
            uninstall_file = package_data.get("uninstall", {}).get("file")
            if uninstall_file:
                uninstall_file_path = os.path.join(local_app_data, package_name, uninstall_file)
                if os.path.exists(uninstall_file_path) and uninstall_file.endswith(".py"):
                    print(f"{Fore.YELLOW}Running uninstall script {Fore.CYAN}{uninstall_file_path}{Fore.YELLOW}... Note that you may need to take action in another terminal window.")
                    self._verbose_print(f"Running uninstall script: {uninstall_file_path} in new cmd window")
                    subprocess.run(f"start cmd /c python {uninstall_file_path}", shell=True)
                    # Wait until the uninstall script is completed
                    input(f"{Fore.YELLOW}Press Enter once the uninstall script has completed (other window will close)...")
                    self._verbose_print("Uninstall script completed")
            
            # Clean up dependencies before deleting the package
            deps_file = os.path.join(local_app_data, package_name, ".DEPENDENCIES")
            if os.path.exists(deps_file):
                with open(deps_file, 'r') as f:
                    for line in f:
                        dep = line.strip()
                        if dep and dep.startswith("paxd:"):
                            paxd_package = dep[len("paxd:"):]
                            self._remove_dependency_reference(paxd_package, package_name)
                    
            # Now for the fun part - deleting the package folder from %LOCALAPPDATA%/<package_name>
            self._verbose_print(f"Deleting package folder: {package_name} at {package_install_path}")
            package_folder = os.path.join(local_app_data, package_name)
            if os.path.exists(package_folder):
                shutil.rmtree(package_folder, onerror=permission_handler)
                # Check package folder is deleted
                if not os.path.exists(package_folder):
                    print(f"{Fore.GREEN}✓ Successfully uninstalled '{Fore.CYAN}{package_name}{Fore.GREEN}' - deleted package folder {package_folder}")
                    self._verbose_print(f"Successfully uninstalled package: {package_name}")
                else:
                    print(f"{Fore.RED}Failed to delete package folder {package_folder}")
                    self._verbose_print(f"Failed to delete package folder: {package_folder}")
                    
        except FileNotFoundError as e:
            self._verbose_print(f"FileNotFoundError in uninstall: {e}")
            self._verbose_timing_end(f"uninstall {package_name}")
            error_msg = str(e)
            if "not found in repository" in error_msg:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.YELLOW}Note: This might mean the package was removed from the repository.")
                print(f"{Fore.CYAN}You can still try to uninstall locally installed files if they exist.")
                # Try to uninstall local files even if not in repository
                local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
                package_folder = os.path.join(local_app_data, package_name)
                if os.path.exists(package_folder):
                    print(f"{Fore.YELLOW}Found local installation, attempting cleanup...")
                    try:
                        shutil.rmtree(package_folder, onerror=permission_handler)
                        if not os.path.exists(package_folder):
                            print(f"{Fore.GREEN}✓ Successfully removed local files for '{Fore.CYAN}{package_name}{Fore.GREEN}'")
                        else:
                            print(f"{Fore.RED}Failed to remove local files for '{package_name}'")
                    except Exception as cleanup_error:
                        print(f"{Fore.RED}Error during cleanup: {cleanup_error}")
                else:
                    print(f"{Fore.YELLOW}Package '{Fore.CYAN}{package_name}{Fore.YELLOW}' is not installed locally.")
            else:
                print(f"{Fore.RED}Error: {error_msg}")
        except requests.HTTPError as e:
            self._verbose_print(f"HTTPError in uninstall: {e}")
            self._verbose_timing_end(f"uninstall {package_name}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.YELLOW}Note: This might mean the package was removed from the repository.")
                print(f"{Fore.CYAN}You can still try to uninstall locally installed files if they exist.")
                # Try to uninstall local files even if not in repository
                local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
                package_folder = os.path.join(local_app_data, package_name)
                if os.path.exists(package_folder):
                    print(f"{Fore.YELLOW}Found local installation, attempting cleanup...")
                    try:
                        shutil.rmtree(package_folder, onerror=permission_handler)
                        if not os.path.exists(package_folder):
                            print(f"{Fore.GREEN}✓ Successfully removed local files for '{Fore.CYAN}{package_name}{Fore.GREEN}'")
                        else:
                            print(f"{Fore.RED}Failed to remove local files for '{package_name}'")
                    except Exception as cleanup_error:
                        print(f"{Fore.RED}Error during cleanup: {cleanup_error}")
                else:
                    print(f"{Fore.YELLOW}Package '{Fore.CYAN}{package_name}{Fore.YELLOW}' is not installed locally.")
            else:
                print(f"{Fore.RED}HTTP error: {e}")
        except requests.RequestException as e:
            self._verbose_print(f"RequestException in uninstall: {e}")
            self._verbose_timing_end(f"uninstall {package_name}")
            print(f"{Fore.RED}Network error: {e}")
        except Exception as e:
            self._verbose_print(f"Unexpected error in uninstall: {e}")
            self._verbose_timing_end(f"uninstall {package_name}")
            print(f"{Fore.RED}Unexpected error: {e}")

    def update(self, package_name=None, force=False, skip_checksum=False): # type: ignore
        """Update a package to the latest version."""
        self._verbose_timing_start(f"update {package_name}")
        self._verbose_print(f"Updating package: {package_name} (force={force})")
        
        if not package_name:
            self._verbose_print("No package name provided for update")
            self._verbose_timing_end(f"update {package_name}")
            print(f"{Fore.RED}No package specified for update.")
            return
            
        print(f"{Fore.BLUE}Updating {Fore.CYAN}{package_name}{Fore.BLUE}...")
        
        backup_files = []  # Track backup files for cleanup on success or failure
        try:
            # Read and resolve repository URL
            self._verbose_print("Reading and resolving repository URL for update")
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            self._verbose_print(f"Local app data directory: {local_app_data}")
            
            # GET {repo_url}/resolution to resolve aliases
            resolution_url = f"{repo_url}/resolution"
            resolution_response = requests.get(resolution_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {resolution_url}: {resolution_response.status_code}")
            resolution_response.raise_for_status()
            resolution_data = parse_jsonc(resolution_response.text)
            
            # Check if package name needs to be resolved from alias to actual package name
            original_package_name = package_name
            for actual_package, aliases in resolution_data.items():
                if package_name in aliases:
                    print(f"{Fore.BLUE}Resolving alias '{Fore.YELLOW}{package_name}{Fore.BLUE}' to '{Fore.CYAN}{actual_package}{Fore.BLUE}'")
                    package_name = actual_package
                    break
            
            # Check if package is currently installed
            package_install_path = os.path.join(local_app_data, package_name)
            if not os.path.exists(package_install_path):
                print(f"{Fore.RED}Package '{Fore.CYAN}{original_package_name}{Fore.RED}' is not installed. Use '{Fore.GREEN}paxd install {original_package_name}{Fore.RED}' to install it.")
                return
            
            # Special handling for updating PaxD itself
            if package_name == "com.mralfiem591.paxd":
                print(f"{Fore.YELLOW}Warning: Self-updating PaxD requires careful handling.")
                print(f"{Fore.YELLOW}The update will download new files and may require a restart of PaxD.")
                print(f"{Fore.GREEN}Although, you can normally ignore this. Careful measures are taken to prevent corruption, and there is only a miniscule chance of failure.")
                print(f"{Fore.LIGHTYELLOW_EX}In the event of failure, try running the installer via the one-liner on the PaxD website, as it can detect, flag, and repair most problems.")
                
            # Get current installed version (if available)
            current_version = None
            version_file = os.path.join(package_install_path, ".VERSION")
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    current_version = f.read().strip()
            
            # Fetch latest package metadata
            self._verbose_print(f"Fetching latest package metadata for: {package_name}")
            package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
            self._verbose_print(f"Successfully fetched metadata from {source_file}")
            if source_file == "paxd.yaml":
                print(f"{Fore.GREEN}Using YAML package configuration")
            
            # Get latest version from repository
            latest_version = package_data.get('pkg_info', {}).get('pkg_version', 'Unknown')
            pkg_name_friendly = f"{package_data.get('pkg_info', {}).get('pkg_name', package_name)}, by {package_data.get('pkg_info', {}).get('pkg_author', 'Unknown Author')}"
            
            print(f"{Fore.WHITE}Current version: {Fore.RED}{current_version or 'Unknown'}")
            print(f"{Fore.WHITE}Latest version: {Fore.GREEN}{latest_version}")
            
            # Check if update is needed
            if current_version == latest_version and not force:
                print(f"{Fore.GREEN}Package '{pkg_name_friendly}' is already up to date.")
                return
            
            print(f"{Fore.BLUE}Updating '{pkg_name_friendly}' from {Fore.RED}{current_version or 'Unknown'}{Fore.BLUE} to {Fore.GREEN}{latest_version}")
            
            # Handle dependencies (both new and existing)
            current_dependencies = set()
            for dep in package_data.get("install", {}).get("depend", []):
                current_dependencies.add(dep)
                try:
                    # Dependency begins with "pip:": use pip to install
                    if dep.startswith("pip:"):
                        pip_package = dep[len("pip:"):]
                        print(f"{Fore.CYAN}Installing/updating Python package '{Fore.YELLOW}{pip_package}{Fore.CYAN}' via pip")
                        os.system(f"pip install --upgrade {pip_package}")
                    # Dependency begins with "winget": use winget to install
                    elif dep.startswith("winget:"):
                        winget_package = dep[len("winget:"):]
                        print(f"Installing/updating Windows package '{winget_package}' via winget")
                        os.system(f"winget install {winget_package}")
                    # Dependency begins with "choco:": use choco to install
                    elif dep.startswith("choco:"):
                        choco_package = dep[len("choco:"):]
                        print(f"Installing/updating Chocolatey package '{choco_package}' via choco")
                        os.system(f"choco upgrade {choco_package}")
                    # Dependency begins with "npm:": use npm to install
                    elif dep.startswith("npm:"):
                        npm_package = dep[len("npm:"):]
                        print(f"Installing/updating Node.js package '{npm_package}' via npm")
                        os.system(f"npm install {npm_package}")
                    # Dependency begins with "paxd:": check if installed, then install or update
                    elif dep.startswith("paxd:"):
                        paxd_package = dep[len("paxd:"):]
                        paxd_dep_path = os.path.join(local_app_data, paxd_package)
                        if os.path.exists(paxd_dep_path):
                            print(f"Updating PaxD dependency '{paxd_package}'")
                            self.update(paxd_package)
                        else:
                            print(f"Installing new PaxD dependency '{paxd_package}'")
                            self.install(paxd_package, user_requested=False)
                            # Mark this package as a dependency
                            self._mark_as_dependency(paxd_package, package_name)
                    else:
                        print(f"Unknown dependency type for '{dep}'")
                except Exception as e:
                    print(f"Warning: Failed to handle dependency '{dep}': {e}")
            
            # Check for orphaned dependencies (packages that were dependencies but are no longer needed)
            self._cleanup_orphaned_dependencies(package_name, current_dependencies)
            
            # Update files from the include list
            # update-ex: array of filenames from include list to skip during updates
            # Useful for config files or user-modified files that shouldn't be overwritten
            updated_files = []
            excluded_files = package_data.get("install", {}).get("update-ex", [])
            
            for file in package_data.get("install", {}).get("include", []):
                # Check if this file is excluded from updates
                if file in excluded_files:
                    print(f"Skipping update of '{file}' (excluded by update-ex)")
                    continue
                    
                file_url = f"{repo_url}/packages/{package_name}/src/{file}"
                file_response = requests.get(file_url, headers=self.headers, allow_redirects=True)  # type: ignore
                self._verbose_print(f"GET {file_url}: {file_response.status_code}")
                file_response.raise_for_status()
                file_data = file_response.content
                
                # Update the file
                install_path = os.path.join(local_app_data, package_name, file)
                os.makedirs(os.path.dirname(install_path), exist_ok=True)
                
                # Backup existing file if it exists
                backup_path = f"{install_path}.backup"
                if os.path.exists(install_path):
                    shutil.copy2(install_path, backup_path)
                    backup_files.append(backup_path)
                
                with open(install_path, 'wb') as f:
                    f.write(file_data)
                    
                updated_files.append(file)
                
                # Verify checksum if provided
                expected_checksum = package_data.get("install", {}).get("checksum", {}).get(file)
                if expected_checksum and not skip_checksum:
                    # Also calculate checksum of the raw downloaded data for debugging
                    raw_checksum = f"sha256:{hashlib.sha256(file_data).hexdigest()}"
                    # Verify the checksum
                    sha256 = hashlib.sha256()
                    with open(install_path, "rb") as f:
                        while True:
                            chunk: bytes = f.read(4096)
                            if not chunk:
                                break
                            sha256.update(chunk)
                    calculated_checksum = f"sha256:{sha256.hexdigest()}"
                    
                    if calculated_checksum == expected_checksum:
                        print(f"Checksum verified for {file}")
                        # Remove backup if checksum is correct
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                            backup_files.remove(backup_path) if backup_path in backup_files else None
                    else:
                        print(f"Checksum mismatch for {file}: {calculated_checksum} != {expected_checksum}")
                        self._verbose_print(f"Checksum verification failed for {file}: {calculated_checksum} != {expected_checksum}")
                        # Restore from backup
                        if os.path.exists(backup_path):
                            shutil.copy2(backup_path, install_path)
                            os.remove(backup_path)
                            backup_files.remove(backup_path) if backup_path in backup_files else None
                            print(f"Restored {file} from backup due to checksum failure")
                            # Remove from updated_files since it was restored
                            updated_files.remove(file) if file in updated_files else None
                        else:
                            os.remove(install_path)
                            print(f"Deleted invalid file {file}")
                            # Remove from updated_files since it was deleted
                            updated_files.remove(file) if file in updated_files else None
                else:
                    print(f"No checksum verification required for {file}")
            
            # Clean up any remaining backup files (for files without checksums or after successful updates)
            cleaned_backups = self._cleanup_backup_files(backup_files, "successful update")
            
            if cleaned_backups > 0:
                print(f"Removed {cleaned_backups} backup file(s)")
            
            # Update the version file
            version_file = os.path.join(package_install_path, ".VERSION")
            with open(version_file, 'w') as f:
                f.write(latest_version)
            
            # Handle updaterun flag
            if package_data.get("install", {}).get("updaterun"):
                updaterun_path = os.path.join(local_app_data, package_name, ".UPDATERUN")
                with open(updaterun_path, 'w') as f:
                    f.write("This file indicates that the package has been updated and may need special handling.")
                print(f"Created .UPDATERUN file at {updaterun_path}")
            
            # Update batch file if mainfile exists (in case alias or mainfile changed)
            mainfile = package_data.get("install", {}).get("mainfile")
            if mainfile:
                alias = package_data.get("install", {}).get("alias", mainfile.split(".")[0])
                bat_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{alias}.bat")
                
                # Update the batch file content
                with open(bat_file_path, 'w') as f:
                    f.write(f"@echo off\n")
                    f.write(f"python {os.path.join(local_app_data, 'com.mralfiem591.paxd', 'run_pkg.py')} {os.path.join(local_app_data, package_name, mainfile)} %*\n")
                print(f"Updated batch file at {bat_file_path}")
            
            print(f"{Fore.GREEN}✓ Successfully updated '{pkg_name_friendly}' to version {Fore.CYAN}{latest_version}{Style.RESET_ALL}")
            if updated_files:
                print(f"{Fore.BLUE}Updated files: {Fore.WHITE}{', '.join(updated_files)}")
            if excluded_files:
                print(f"{Fore.YELLOW}Excluded from update: {Fore.WHITE}{', '.join(excluded_files)}")
                
        except FileNotFoundError as e:
            self._verbose_print(f"FileNotFoundError in update: {e}")
            self._verbose_timing_end(f"update {package_name}")
            error_msg = str(e)
            if "not found in repository" in error_msg:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.YELLOW}The package might have been removed from the repository or renamed.")
                print(f"{Fore.CYAN}Try searching for similar packages with: {Fore.GREEN}paxd search {package_name}")
            else:
                print(f"{Fore.RED}Error: {error_msg}")
            # Clean up backup files on error
            self._cleanup_backup_files(backup_files, "error cleanup")
        except requests.HTTPError as e:
            self._verbose_print(f"HTTPError in update: {e}")
            self._verbose_timing_end(f"update {package_name}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                print(f"{Fore.RED}Package '{Fore.YELLOW}{package_name}{Fore.RED}' was not found in the repository.")
                print(f"{Fore.YELLOW}The package might have been removed from the repository or renamed.")
                print(f"{Fore.CYAN}Try searching for similar packages with: {Fore.GREEN}paxd search {package_name}")
            else:
                print(f"{Fore.RED}HTTP error: {e}")
            # Clean up backup files on error
            self._cleanup_backup_files(backup_files, "error cleanup")
        except requests.RequestException as e:
            self._verbose_print(f"RequestException in update: {e}")
            self._verbose_timing_end(f"update {package_name}")
            print(f"{Fore.RED}Network error: {e}")
            # Clean up backup files on error
            self._cleanup_backup_files(backup_files, "error cleanup")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Clean up backup files on error
            self._cleanup_backup_files(backup_files, "error cleanup")
        except Exception as e:
            print(f"Unexpected error during update: {e}")
            # Clean up backup files on error
            self._cleanup_backup_files(backup_files, "error cleanup")
            
    def list_installed(self):
        """List all installed packages with their versions."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        if not os.path.exists(local_app_data):
            print(f"{Fore.YELLOW}No packages installed.")
            return
        
        packages = []
        for item in os.listdir(local_app_data):
            package_path = os.path.join(local_app_data, item)
            if os.path.isdir(package_path):
                version_file = os.path.join(package_path, ".VERSION")
                version = "Unknown"
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        version = f.read().strip()
                
                user_installed = os.path.exists(os.path.join(package_path, ".USER_INSTALLED"))
                packages.append((item, version, user_installed))
        
        if not packages:
            print(f"{Fore.YELLOW}No packages installed.")
            return
        
        print(f"{Fore.BLUE}Installed Packages:")
        for pkg, ver, user in sorted(packages):
            status = f"{Fore.GREEN}[USER]" if user else f"{Fore.YELLOW}[DEP]"
            print(f"  {status} {Fore.CYAN}{pkg} {Fore.WHITE}({ver})")

    def is_installed(self, package_name):
        """Check if a package is installed."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        package_install_path = os.path.join(local_app_data, package_name)
        return os.path.exists(package_install_path)

    def info(self, package_name, fullsize=False):
        """Display detailed information about a package."""
        self._verbose_timing_start(f"info {package_name}")
        self._verbose_print(f"Getting info for package: {package_name}")
        
        try:
            # Read and resolve repository URL
            self._verbose_print("Reading and resolving repository URL for info")
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            self._verbose_print(f"Local app data directory: {local_app_data}")
            
            # GET {repo_url}/resolution to resolve aliases
            resolution_url = f"{repo_url}/resolution"
            self._verbose_print(f"Fetching resolution data from: {resolution_url}")
            resolution_response = requests.get(resolution_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {resolution_url}: {resolution_response.status_code}")
            self._verbose_print(f"Resolution response status: {resolution_response.status_code}")
            resolution_response.raise_for_status()
            resolution_data = parse_jsonc(resolution_response.text)
            self._verbose_print(f"Resolution data contains {len(resolution_data)} packages")
            
            # Check if package name needs to be resolved from alias to actual package name
            original_package_name = package_name
            resolved_from_alias = False
            for actual_package, aliases in resolution_data.items():
                if package_name in aliases:
                    package_name = actual_package
                    resolved_from_alias = True
                    break
            
            # Fetch package metadata (try both paxd and paxd.yaml)
            self._verbose_print(f"Fetching package metadata for info: {package_name}")
            package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
            self._verbose_print(f"Successfully fetched metadata from {source_file}")
            if source_file == "paxd.yaml":
                print(f"{Fore.GREEN}Package uses YAML configuration format")
            
            # Check if package is installed
            package_install_path = os.path.join(local_app_data, package_name)
            is_installed = os.path.exists(package_install_path)
            installed_version = None
            is_user_installed = False
            
            if is_installed:
                # Get installed version
                version_file = os.path.join(package_install_path, ".VERSION")
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        installed_version = f.read().strip()
                
                # Check if user-installed
                user_installed_file = os.path.join(package_install_path, ".USER_INSTALLED")
                is_user_installed = os.path.exists(user_installed_file)
            
            # Display package information
            print(f"{Fore.BLUE}{'=' * 60}")
            pkg_info = package_data.get('pkg_info', {})
            
            # Package name and version
            pkg_name = pkg_info.get('pkg_name', package_name)
            pkg_version = pkg_info.get('pkg_version', 'Unknown')
            print(f"{Fore.CYAN}Package: {Fore.GREEN}{pkg_name}")
            print(f"{Fore.WHITE}ID: {Fore.YELLOW}{package_name}")
            
            if resolved_from_alias:
                print(f"{Fore.YELLOW}Alias: {Fore.MAGENTA}{original_package_name}")
            
            print(f"{Fore.BLUE}Version: {Fore.WHITE}{pkg_version}")
            
            # Author and description
            if 'pkg_author' in pkg_info:
                print(f"{Fore.MAGENTA}Author: {Style.RESET_ALL}{pkg_info['pkg_author']}")
            
            if 'pkg_description' in pkg_info:
                print(f"{Fore.WHITE}Description: {Style.RESET_ALL}{pkg_info['pkg_description']}")
            
            # Installation status
            print(f"\n{Fore.YELLOW}Installation Status:")
            if is_installed:
                print(f"  {Fore.GREEN}[+] Installed (version {Fore.CYAN}{installed_version or 'Unknown'}{Fore.GREEN})")
                if is_user_installed:
                    print(f"  {Fore.GREEN}[+] User-installed (won't be auto-removed)")
                else:
                    print(f"  {Fore.YELLOW}[!] Dependency (may be auto-removed)")
                
                # Check if update is available
                if installed_version and installed_version != pkg_version:
                    print(f"  {Fore.BLUE}[*] Update available: {Fore.RED}{installed_version}{Fore.BLUE} -> {Fore.GREEN}{pkg_version}")
                elif installed_version == pkg_version:
                    print(f"  {Fore.GREEN}[+] Up to date")
            else:
                print(f"  {Fore.RED}[-] Not installed")
                
            if is_installed and not fullsize:
                try:
                    package_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                    for dirpath, dirnames, filenames in os.walk(package_install_path)
                                    for filename in filenames)
                    print(f"  {Fore.BLUE}Size: {Fore.WHITE}{package_size / 1024:.1f} KB")
                except:
                    pass
            elif is_installed and fullsize:
                try:
                    for file in os.walk(package_install_path):
                        for filename in file[2]:
                            if filename in [".VERSION", ".USER_INSTALLED", ".DEPENDENCIES", ".FIRSTRUN", ".UPDATERUN"]:
                                continue
                            filepath = os.path.join(file[0], filename)
                            filesize = os.path.getsize(filepath)
                            print(f"  {Fore.WHITE}{os.path.relpath(filepath, package_install_path)}: {filesize / 1024:.1f} KB")
                except:
                    pass
            
            # Dependencies
            install_info = package_data.get('install', {})
            dependencies = install_info.get('depend', [])
            if dependencies:
                print(f"\n{Fore.YELLOW}Dependencies:")
                for dep in dependencies:
                    if dep.startswith("paxd:"):
                        paxd_dep = dep[len("paxd:"):]
                        dep_path = os.path.join(local_app_data, paxd_dep)
                        status = f"{Fore.GREEN}[+] installed" if os.path.exists(dep_path) else f"{Fore.RED}[-] not installed"
                        print(f"  - {Fore.CYAN}{paxd_dep}{Style.RESET_ALL} (PaxD) - {status}")
                    else:
                        dep_type = dep.split(":")[0] if ":" in dep else "unknown"
                        dep_name = dep.split(":", 1)[1] if ":" in dep else dep
                        print(f"  - {Fore.WHITE}{dep_name}{Style.RESET_ALL} ({Fore.MAGENTA}{dep_type}{Style.RESET_ALL})")
            
            # Files included
            included_files = install_info.get('include', [])
            if included_files:
                print(f"\n{Fore.BLUE}Included Files:")
                excluded_files = install_info.get('update-ex', [])
                for file in included_files:
                    if file in excluded_files:
                        print(f"  - {Fore.WHITE}{file}{Style.RESET_ALL} {Fore.YELLOW}(excluded from updates)")
                    else:
                        print(f"  - {Fore.WHITE}{file}")
            
            # Main executable
            mainfile = install_info.get('mainfile')
            if mainfile:
                alias = install_info.get('alias', mainfile.split(".")[0])
                print(f"\n{Fore.GREEN}Executable:")
                print(f"  {Fore.WHITE}Main file: {Fore.CYAN}{mainfile}")
                print(f"  {Fore.WHITE}Command: {Fore.GREEN}{alias}")
            
            # Special flags
            special_flags = []
            if install_info.get('firstrun'):
                special_flags.append("Creates .FIRSTRUN marker")
            if install_info.get('updaterun'):
                special_flags.append("Creates .UPDATERUN marker on updates")
            
            if special_flags:
                print(f"\nSpecial Features:")
                for flag in special_flags:
                    print(f"  - {flag}")
            
            # Uninstall info
            uninstall_info = package_data.get('uninstall', {})
            if uninstall_info.get('file'):
                print(f"\nUninstall:")
                print(f"  Custom uninstall script: {uninstall_info['file']}")
            
            print("=" * 60)
            self._verbose_timing_end(f"info {package_name}")
            
        except requests.HTTPError as e:
            self._verbose_print(f"HTTPError in info: {e}")
            self._verbose_timing_end(f"info {package_name}")
            if e.response.status_code == 404:
                print(f"Package '{original_package_name}' not found in repository")
            else:
                print(f"HTTP error: {e}")
        except FileNotFoundError as e:
            self._verbose_print(f"FileNotFoundError in info: {e}")
            self._verbose_timing_end(f"info {package_name}")
            print(f"Error: {e}")
        except requests.RequestException as e:
            self._verbose_print(f"RequestException in info: {e}")
            self._verbose_timing_end(f"info {package_name}")
            print(f"Network error: {e}")
        except json.JSONDecodeError as e:
            self._verbose_print(f"JSONDecodeError in info: {e}")
            self._verbose_timing_end(f"info {package_name}")
            print(f"JSON parsing error: {e}")
        except Exception as e:
            self._verbose_print(f"Unexpected error in info: {e}")
            self._verbose_timing_end(f"info {package_name}")
            print(f"Unexpected error: {e}")
            
    def show_repo_info(self):
        """Display information about the configured repository."""
        try:
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            repo_info_url = f"{repo_url}/paxd"
            repo_response = requests.get(repo_info_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {repo_info_url}: {repo_response.status_code}")
            repo_response.raise_for_status()
            repo_data = parse_jsonc(repo_response.text)
            
            print(f"{Fore.BLUE}{'=' * 60}")
            print(f"{Fore.CYAN}Repository Information:")
            print(f"{Fore.YELLOW}Name:{Style.RESET_ALL} {repo_data.get('repo_info', {}).get('repo_name', 'Unknown')}")
            print(f"{Fore.MAGENTA}Author:{Style.RESET_ALL} {repo_data.get('repo_info', {}).get('repo_author', 'Unknown')}")
            print(f"{Fore.WHITE}Description:{Style.RESET_ALL} {repo_data.get('repo_info', {}).get('repo_description', 'No description provided.')}")
                
            print(f"{Fore.BLUE}URL:{Style.RESET_ALL} {repo_url}")
            print(f"{Fore.BLUE}{'=' * 60}")
            for key, value in repo_data.get('credit', {}).items():
                print(f"{Fore.GREEN}- {key.title()}: {value}")
            if repo_data.get('credit', {}):
                print(f"{Fore.BLUE}{'=' * 60}")

            if repo_data.get('repo_info', {}).get('repo_logo'):
                if self.is_installed("com.mralfiem591.paxd-imageview"):
                    subprocess.Popen(f"start cmd /c paxd-imageview --sleep 5 {repo_url}/{repo_data['repo_info']['repo_logo']}", shell=True)
                else:
                    print(f"Logo URL: {repo_url}/{repo_data['repo_info']['repo_logo']} (Install 'paxd-imageview' to view images)")
            else:
                print("No logo provided.")

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print("Repository information not found.")
            else:
                print(f"HTTP error: {e}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
        except requests.RequestException as e:
            print(f"Network error: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def credit(self):
        repo_url = self._read_repository_url()
        repo_url = self._resolve_repository_url(repo_url)
        
        print(f"{Fore.CYAN}PaxD (Package xpress Delivery) - Package Manager for Developers")
        print(f"{Fore.WHITE}Developed by mralfiem591")
        print(f"{Fore.LIGHTBLUE_EX}Powered by Python")
        print(f"{Fore.LIGHTMAGENTA_EX}Inspired by package managers like pip, npm, winget, and apt-get")
        print(f"{Fore.YELLOW}View repository credits and info via the '{Fore.LIGHTYELLOW_EX}paxd repo-info{Fore.YELLOW}' command")
        if self.is_installed("com.mralfiem591.paxd-imageview"):
            subprocess.Popen(f"start cmd /c paxd-imageview --sleep 5 {repo_url}/packages/com.mralfiem591.paxd/src/asset/logo.png", shell=True)
    
    def search(self, search_term: str):
        """Search for packages by name, alias, or description."""
        self._verbose_timing_start(f"search {search_term}")
        self._verbose_print(f"Searching for packages matching: {search_term}")
        
        if not search_term:
            self._verbose_print("No search term provided")
            print(f"{Fore.RED}Please provide a search term.")
            self._verbose_timing_end(f"search {search_term}")
            return
            
        try:
            self._verbose_print("Reading and resolving repository URL for search")
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            
            # Get resolution data for aliases
            resolution_url = f"{repo_url}/resolution"
            self._verbose_print(f"Fetching resolution data from: {resolution_url}")
            resolution_response = requests.get(resolution_url, headers=self.headers, allow_redirects=True)  # type: ignore
            self._verbose_print(f"GET {resolution_url}: {resolution_response.status_code}")
            self._verbose_print(f"Resolution response status: {resolution_response.status_code}")
            resolution_response.raise_for_status()
            resolution_data = parse_jsonc(resolution_response.text)
            self._verbose_print(f"Found {len(resolution_data)} packages in resolution data")
            
            print(f"{Fore.CYAN}Searching for '{Fore.YELLOW}{search_term}{Fore.CYAN}'...")
            print(f"{Fore.BLUE}{'=' * 60}")
            
            found_packages = []
            search_term_lower = search_term.lower()
            
            # Search through all packages in resolution (this gives us all available packages)
            for package_name, aliases in resolution_data.items():
                try:
                    # Get package metadata (try both paxd and paxd.yaml)
                    package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
                    self._verbose_print(f"Successfully fetched metadata from {source_file} for search")
                    pkg_info = package_data.get('pkg_info', {})
                    install_info = package_data.get('install', {})
                    
                    # Extract searchable fields
                    display_name = pkg_info.get('pkg_name', 'Unknown')
                    description = pkg_info.get('pkg_description', 'No description')
                    author = pkg_info.get('pkg_author', 'Unknown')
                    version = pkg_info.get('pkg_version', 'Unknown')
                    alias = install_info.get('alias', '')
                    
                    # Check if search term matches
                    matches = []
                    matched_aliases = set()  # Track aliases to avoid duplicates
                    
                    # Check package name (exact and partial)
                    if search_term_lower in package_name.lower():
                        matches.append(f"package name: {package_name}")
                    
                    # Check display name
                    if search_term_lower in display_name.lower():
                        matches.append(f"display name: {display_name}")
                    
                    # Check all aliases (both from package info and resolution) but avoid duplicates
                    all_aliases = set()
                    if alias:
                        all_aliases.add(alias)
                    all_aliases.update(aliases)
                    
                    for alias_name in all_aliases:
                        if search_term_lower in alias_name.lower():
                            matched_aliases.add(alias_name)
                    
                    # Add matched aliases to results
                    for matched_alias in sorted(matched_aliases):
                        matches.append(f"alias: {matched_alias}")
                    
                    # Check description
                    if search_term_lower in description.lower():
                        matches.append("description")
                    
                    # Check author
                    if search_term_lower in author.lower():
                        matches.append(f"author: {author}")
                    
                    if matches:
                        found_packages.append({
                            'package_name': package_name,
                            'display_name': display_name,
                            'description': description,
                            'author': author,
                            'version': version,
                            'alias': alias,
                            'aliases': aliases,
                            'matches': matches,
                            'is_installed': self.is_installed(package_name)
                        })
                        
                except Exception as e:
                    # Skip packages that can't be processed
                    continue
            
            # Display results
            if not found_packages:
                print(f"{Fore.RED}No packages found matching '{Fore.YELLOW}{search_term}{Fore.RED}'")
                return
            
            print(f"{Fore.GREEN}Found {Fore.WHITE}{len(found_packages)}{Fore.GREEN} package(s):")
            print()
            
            for pkg in found_packages:
                if pkg['is_installed']:
                    status = f"{Fore.GREEN}[INSTALLED]{Style.RESET_ALL}"
                else:
                    status = f"{Fore.RED}[NOT INSTALLED]{Style.RESET_ALL}"
                print(f"{status} {Fore.CYAN}{pkg['display_name']}")
                print(f"  {Fore.WHITE}Package:{Style.RESET_ALL} {pkg['package_name']}")
                if pkg['alias']:
                    print(f"  {Fore.YELLOW}Alias:{Style.RESET_ALL} {pkg['alias']}")
                if pkg['aliases']:
                    other_aliases = [a for a in pkg['aliases'] if a != pkg['alias']]
                    if other_aliases:
                        print(f"  {Fore.YELLOW}Other aliases:{Style.RESET_ALL} {', '.join(other_aliases)}")
                print(f"  {Fore.MAGENTA}Author:{Style.RESET_ALL} {pkg['author']}")
                print(f"  {Fore.BLUE}Version:{Style.RESET_ALL} {pkg['version']}")
                print(f"  {Fore.WHITE}Description:{Style.RESET_ALL} {pkg['description']}")
                print(f"  {Fore.GREEN}Matches:{Style.RESET_ALL} {', '.join(pkg['matches'])}")
                print()
                
            print(f"{Fore.CYAN}To install a package, use: {Fore.GREEN}paxd install <package_name_or_alias>")
            self._verbose_timing_end(f"search {search_term}")
            
        except requests.HTTPError as e:
            self._verbose_print(f"HTTPError in search: {e}")
            self._verbose_timing_end(f"search {search_term}")
            print(f"{Fore.RED}HTTP error: {e}")
        except FileNotFoundError as e:
            self._verbose_print(f"FileNotFoundError in search: {e}")
            self._verbose_timing_end(f"search {search_term}")
            print(f"{Fore.RED}Error: {e}")
        except requests.RequestException as e:
            self._verbose_print(f"RequestException in search: {e}")
            self._verbose_timing_end(f"search {search_term}")
            print(f"{Fore.RED}Network error: {e}")
        except json.JSONDecodeError as e:
            self._verbose_print(f"JSONDecodeError in search: {e}")
            self._verbose_timing_end(f"search {search_term}")
            print(f"{Fore.RED}JSON parsing error: {e}")
        except Exception as e:
            self._verbose_print(f"Unexpected error in search: {e}")
            self._verbose_timing_end(f"search {search_term}")
            print(f"{Fore.RED}Unexpected error: {e}")
    
    def _mark_as_dependency(self, dependency_package: str, parent_package: str):
        """Mark a package as a dependency of another package."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        dependency_path = os.path.join(local_app_data, dependency_package)
        
        if not os.path.exists(dependency_path):
            return
        
        # Don't mark user-installed packages as dependencies
        user_installed_file = os.path.join(dependency_path, ".USER_INSTALLED")
        if os.path.exists(user_installed_file):
            print(f"'{dependency_package}' is user-installed, not marking as dependency")
            return
        
        # Create or update the .DEPENDENCY file
        dependency_file = os.path.join(dependency_path, ".DEPENDENCY")
        dependent_packages = set()
        
        if os.path.exists(dependency_file):
            with open(dependency_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        dependent_packages.add(line)
        
        dependent_packages.add(parent_package)
        
        with open(dependency_file, 'w') as f:
            for pkg in sorted(dependent_packages):
                f.write(f"{pkg}\n")
        
        print(f"Marked '{dependency_package}' as dependency of '{parent_package}'")
    
    def _cleanup_backup_files(self, backup_files: list, context: str = "update") -> int:
        """Clean up backup files and return count of files cleaned."""
        cleaned_count = 0
        for backup_path in backup_files[:]:  # Use slice copy to avoid modification during iteration
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    cleaned_count += 1
                    print(f"Cleaned up backup file: {os.path.basename(backup_path)} ({context})")
                except Exception as e:
                    print(f"Warning: Failed to remove backup file {backup_path}: {e}")
        return cleaned_count
    
    def _mark_as_user_installed(self, package_name: str):
        """Mark a package as user-installed (prevents auto-removal)."""
        self._verbose_print(f"Marking package as user-installed: {package_name}")
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        package_path = os.path.join(local_app_data, package_name)
        self._verbose_print(f"Package path: {package_path}")
        
        if not os.path.exists(package_path):
            self._verbose_print("Package path does not exist, cannot mark as user-installed")
            return
        
        # Create .USER_INSTALLED marker file
        user_installed_file = os.path.join(package_path, ".USER_INSTALLED")
        self._verbose_print(f"Creating user-installed marker: {user_installed_file}")
        with open(user_installed_file, 'w') as f:
            f.write(f"Package installed by user on {__import__('datetime').datetime.now().isoformat()}")
        
        # Remove from dependency tracking if it was previously a dependency
        dependency_file = os.path.join(package_path, ".DEPENDENCY")
        if os.path.exists(dependency_file):
            print(f"'{package_name}' was previously a dependency, converting to user-installed package")
            os.remove(dependency_file)
        
        print(f"Marked '{package_name}' as user-installed")
    
    def _cleanup_orphaned_dependencies(self, package_name: str, current_dependencies: set):
        """Remove dependencies that are no longer needed."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        
        # Get the old dependencies from a previous install/update
        old_deps_file = os.path.join(local_app_data, package_name, ".DEPENDENCIES")
        old_dependencies = set()
        
        if os.path.exists(old_deps_file):
            with open(old_deps_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        old_dependencies.add(line)
        
        # Find dependencies that are no longer needed
        removed_dependencies = old_dependencies - current_dependencies
        
        for old_dep in removed_dependencies:
            if old_dep.startswith("paxd:"):
                paxd_package = old_dep[len("paxd:"):]
                self._remove_dependency_reference(paxd_package, package_name)
        
        # Save current dependencies for future cleanup
        with open(old_deps_file, 'w') as f:
            for dep in sorted(current_dependencies):
                f.write(f"{dep}\n")
    
    def _remove_dependency_reference(self, dependency_package: str, parent_package: str):
        """Remove a parent package reference from a dependency and uninstall if orphaned."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        dependency_path = os.path.join(local_app_data, dependency_package)
        
        if not os.path.exists(dependency_path):
            return
        
        dependency_file = os.path.join(dependency_path, ".DEPENDENCY")
        if not os.path.exists(dependency_file):
            return
        
        # Read current dependent packages
        dependent_packages = set()
        with open(dependency_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line != parent_package:
                    dependent_packages.add(line)
        
        if dependent_packages:
            # Still has dependencies, update the file
            with open(dependency_file, 'w') as f:
                for pkg in sorted(dependent_packages):
                    f.write(f"{pkg}\n")
            print(f"Removed dependency reference from '{dependency_package}' to '{parent_package}'")
        else:
            # Check if this package is user-installed before removing
            user_installed_file = os.path.join(dependency_path, ".USER_INSTALLED")
            if os.path.exists(user_installed_file):
                print(f"'{dependency_package}' is user-installed, keeping despite no remaining dependencies")
                # Remove the .DEPENDENCY file since it's no longer needed
                os.remove(dependency_file)
            else:
                # No more dependencies and not user-installed, this package is orphaned
                print(f"Dependency '{dependency_package}' is no longer needed, removing...")
                try:
                    self.uninstall(dependency_package)
                except Exception as e:
                    print(f"Warning: Failed to remove orphaned dependency '{dependency_package}': {e}")
    
    def update_all(self):
        """Update all installed packages."""
        print(f"{Fore.BLUE}Updating all installed packages...")
        
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        if not os.path.exists(local_app_data):
            print(f"{Fore.YELLOW}No packages are installed.")
            return
        
        # Find all installed packages
        installed_packages = []
        for item in os.listdir(local_app_data):
            package_path = os.path.join(local_app_data, item)
            if os.path.isdir(package_path):
                installed_packages.append(item)
        
        if not installed_packages:
            print(f"{Fore.YELLOW}No packages are installed.")
            return
        
        print(f"{Fore.GREEN}Found {Fore.WHITE}{len(installed_packages)}{Fore.GREEN} installed packages: {Fore.CYAN}{', '.join(installed_packages)}")
        
        updated_count = 0
        failed_count = 0
        
        for package in installed_packages:
            try:
                print(f"\n{Fore.BLUE}--- Checking {Fore.CYAN}{package}{Fore.BLUE} for updates ---")
                # Save the current output state to track if update actually happened
                old_version_file = os.path.join(local_app_data, package, ".VERSION")
                old_version = None
                if os.path.exists(old_version_file):
                    with open(old_version_file, 'r') as f:
                        old_version = f.read().strip()
                
                self.update(package)
                
                # Check if version actually changed
                new_version = None
                if os.path.exists(old_version_file):
                    with open(old_version_file, 'r') as f:
                        new_version = f.read().strip()
                
                if old_version != new_version:
                    updated_count += 1
                    
            except Exception as e:
                print(f"Failed to update {package}: {e}")
                failed_count += 1
        
        print(f"\n{Fore.BLUE}--- Update Summary ---")
        print(f"{Fore.GREEN}Updated: {Fore.WHITE}{updated_count}{Fore.GREEN} packages")
        if failed_count > 0:
            print(f"{Fore.RED}Failed: {Fore.WHITE}{failed_count}{Fore.RED} packages")
        print(f"{Fore.GREEN}All package updates completed.")
        
    def export(self):
        """Export a list of all packages, to an export.paxd file."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        export_file = os.path.join(local_app_data, "export.paxd")

        with open(export_file, 'w') as f:
            for item in os.listdir(local_app_data):
                if item == "com.mralfiem591.paxd":
                    print(f"Skipping PaxD core package: {item}")
                    continue
                package_path = os.path.join(local_app_data, item)
                if os.path.isdir(package_path):
                    self._verbose_print(f"Exporting package: {item}")
                    f.write(f"{item}\n")

        print(f"Exported package list to {export_file}")
        
    def import_paxd(self): # used import_paxd() because import() is not usable (as it includes import, a python thing)
        """Import and install packages from an export.paxd file."""
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        import_file = os.path.join(local_app_data, "export.paxd")

        if not os.path.exists(import_file):
            print(f"{Fore.RED}Import file not found: {import_file}")
            return

        with open(import_file, 'r') as f:
            packages_to_install = [line.strip() for line in f if line.strip()]

        print(f"{Fore.BLUE}Importing and installing packages from {import_file}...")
        for package_name in packages_to_install:
            try:
                print(f"\n{Fore.BLUE}--- Installing {Fore.CYAN}{package_name}{Fore.BLUE} ---")
                self.install(package_name)
            except Exception as e:
                print(f"Failed to install {package_name}: {e}")

        print(f"\n{Fore.GREEN}All package imports completed.")
        
    def message_package(self):
        # Send a message to a compatible package. Requires the PaxD SDK.
        find_sdk()
        
        import paxd_sdk as sdk # type: ignore
        
        if not sdk.SDKDetails().AssertVersion("1.2.0"):
            print("Messaging another module is a feature only included in PaxD SDK 1.2.0 and later. Please update your SDK.")

        to = input("Enter the package name to message: ").strip()
        message = input("Enter the message to send: ").strip()

        try:
            sdk.Messaging.SendMessage("com.mralfiem591.paxd", to, {"message": message})
        except ValueError as e:
            print(f"Failed to send message: {e}")
            return
        print("Message sent!")

PaxD()._verbose_print("IMPORTANT: please ignore the numbers stated at the left side of each log key! They are purely to make sorting easier for our bug trackers systems. They are lexicographic for a reason! (because our bug tracker can only read lexicographic ordering for some reason lol)", mode=2)

import datetime
PaxD()._verbose_print(f"PaxD v{PaxD().paxd_version} initialized at {datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} :)")

PaxD()._verbose_print("if you are reading this, you just lost the game :D") # humour in a non-intrusive way :)... also sorry not sorry

def create_argument_parser():
    """Create and configure the argument parser for PaxD CLI."""
    parser = argparse.ArgumentParser(
        prog='paxd',
        description='PaxD - Modern Package Manager for Windows',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Fore.CYAN}Examples:{Style.RESET_ALL}
  paxd install package-name      Install a package
  paxd uninstall package-name    Uninstall a package  
  paxd update package-name       Update a specific package
  paxd search term               Search for packages
  paxd info package-name         Show package details
  paxd --verbose install pkg     Install with verbose output
        """
    )
    
    # Global options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'PaxD {PaxD().paxd_version}: {PaxD().paxd_version_phrase}'
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='<command>'
    )
    
    # Install command
    install_parser = subparsers.add_parser(
        'install',
        help='Install a package',
        description='Install a package from the repository'
    )
    install_parser.add_argument(
        'package_name',
        help='Name of the package to install'
    )
    install_parser.add_argument(
        '--skip-checksum', '-sk',
        action='store_true',
        help='Skip checksum verification during installation'
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser(
        'uninstall',
        help='Uninstall a package',
        description='Remove a package from the system'
    )
    uninstall_parser.add_argument(
        'package_name',
        help='Name of the package to uninstall'
    )
    
    # Update command
    update_parser = subparsers.add_parser(
        'update',
        help='Update a specific package',
        description='Update a package to the latest version'
    )
    update_parser.add_argument(
        'package_name',
        help='Name of the package to update'
    )
    update_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force update even if already up to date'
    )
    update_parser.add_argument(
        '--skip-checksum', '-sk',
        action='store_true',
        help='Skip checksum verification during update'
    )

    # Update-all command
    update_parser = subparsers.add_parser(
        'update-all',
        help='Update all installed packages',
        description='Update all installed packages to their latest versions'
    )
    
    # Reinstall command
    reinstall_parser = subparsers.add_parser(
        'reinstall',
        help='Uninstall then install a package',
        description='Remove and reinstall a package'
    )
    reinstall_parser.add_argument(
        'package_name',
        help='Name of the package to reinstall'
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Show detailed package information',
        description='Display comprehensive information about a package'
    )
    info_parser.add_argument(
        'package_name',
        help='Name of the package to show info for'
    )
    info_parser.add_argument(
        '--fullsize', '-fs',
        action='store_true',
        help='Show the size of each file, not just the entire package',
    )
    
    # Search command
    search_parser = subparsers.add_parser(
        'search',
        help='Search for packages',
        description='Search for packages by name, alias, or description'
    )
    search_parser.add_argument(
        'search_term',
        help='Term to search for'
    )
    search_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit number of search results'
    )

    # Repo-info command
    subparsers.add_parser(
        'repo-info',
        help='Show repository information',
        description='Display information about the configured repository'
    )
    
    # Credit command
    subparsers.add_parser(
        'credit',
        help='Show PaxD credits',
        description='Display PaxD credits and information'
    )
    
    # Packagedir command
    subparsers.add_parser(
        'packagedir',
        help='Show the package directory',
        description='Display the directory where the package is installed'
    )
    
    # Repository command
    subparsers.add_parser(
        'repo',
        help='Open the repository.',
        description='Open the repository in the default browser'
    )
    
    # Listall command
    subparsers.add_parser(
        'listall',
        help='List all installed packages',
        description='Display a list of all installed packages'
    )
    
    # Export command
    subparsers.add_parser(
        'export',
        help='Export installed packages to a file',
        description='Export a list of all installed packages to export.paxd'
    )
    
    # Import command
    subparsers.add_parser(
        'import',
        help='Import packages from a file',
        description='Import and install packages from export.paxd'
    )
    
    # Init command
    init_parser = subparsers.add_parser(
        'init',
        help="Reinitialize PaxD's first-time setup",
        description="Reinitialize PaxD's first-time setup process (not recommended!)"
    )
    init_parser.add_argument(
        '-y',
        action='store_true',
        help="Automatically confirm reinitialization without prompt"
    )
    
    # Message command
    subparsers.add_parser(
        'message',
        help="Send a message",
        description="Send a message to a compatible package for it to receive."
    )
    
    # Return parser, with all commands
    return parser

def main():
    # Initialize colorama for colored output
    init(autoreset=True) # type: ignore
    
    if os.name != "nt" or not WINDOWS_AVAILABLE:
        print(f"{Fore.RED}PaxD is a Windows only tool.")
        print(f"{Fore.RED}Please run PaxD on a Windows device!")
        exit(1)
        
    if not os.getenv("PAXD_GH_TOKEN", None):
        print(f"{Fore.YELLOW}Warning: No authentication token found. You may encounter rate limiting. It is highly recommended to set one up, and set PAXD_GH_TOKEN environment variable.{Style.RESET_ALL}")
        
    # If repository is unoptimised, optimise it
    with open(os.path.join(os.path.dirname(__file__), "repository"), 'r+') as repo_file:
        if repo_file.read().strip().startswith("optimised::"):
            # Repository is already optimised - continue like normal
            pass
        else:
            # Repository is unoptimised - optimise it by resolving it, and writing the resolved URL (lowers head requests needed during normal usage)
            print("Repository is unoptimised - optimising...")
            repo_optimised = f"optimised::{PaxD()._resolve_repository_url(PaxD()._read_repository_url())}"
            # Clear the repository file, and write the optimised repo to it
            repo_file.seek(0)
            repo_file.write(repo_optimised)
            repo_file.truncate()

    # Create and parse arguments first
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return

    # Create PaxD instance with verbose flag
    paxd = PaxD(verbose=args.verbose if hasattr(args, 'verbose') else False)
    
    if SDK_BACKUP:
        paxd._verbose_print("PaxD SDK missing - forcing install")
        paxd.install("com.mralfiem591.paxd-sdk", user_requested=False)
        exit(1)
    
    if os.path.exists(os.path.join(os.path.dirname(__file__), ".UPDATERUN")):
        print(f"{Fore.GREEN}PaxD was updated! Welcome to PaxD {Fore.CYAN}{paxd.paxd_version}{Fore.GREEN}: {paxd.paxd_version_phrase}...{Style.RESET_ALL}\n")
        os.remove(os.path.join(os.path.dirname(__file__), ".UPDATERUN"))
    
    if os.path.exists(os.path.join(os.path.dirname(__file__), ".FIRSTRUN")):
        print(f"{Fore.YELLOW}PaxD first time run, initializing...")
        # 1. Create bin directory
        if not os.path.exists(os.path.join(os.path.dirname(__file__), "bin")):
            os.makedirs(os.path.join(os.path.dirname(__file__), "bin"))
            
        # 2. Add bin directory to PATH permanently
        # Note that paxd is Windows only, so no need to check OS
        bin_path = os.path.join(os.path.dirname(__file__), "bin")
        if not os.path.exists(os.path.join(os.path.dirname(__file__), ".BINSKIP")) and os.path.exists(bin_path):
            # Check if we have administrator permission, if not, prompt the user to run as admin and exit
            if not is_admin():
                print("Please run this script as an administrator, for first time init only.")
                exit(1)
            # Add the bin folder to path
            if not add_to_path(bin_path):
                print(f"Failed to add bin folder to PATH. Try manually adding '{bin_path}' to your PATH, and make a .BINSKIP file alongside paxd.")
                exit(1)
                
        # 3. Create a paxd.bat in the bin path
        paxd_bin_path = os.path.join(bin_path, "paxd.bat")
        if not os.path.exists(paxd_bin_path):
            with open(paxd_bin_path, 'w') as f:
                f.write(f"@echo off\n")
                f.write(f"python {os.path.abspath(__file__)} %*\n")
            print(f"Created paxd.bat at {paxd_bin_path}")
        
        # 4. Register PaxD itself as user-installed and version PaxD
        print("Registering PaxD itself...")
        local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        paxd_package_path = os.path.join(local_app_data, "com.mralfiem591.paxd")
        
        # Create PaxD's package directory if it doesn't exist
        os.makedirs(paxd_package_path, exist_ok=True)
        
        # Create version file for PaxD if it doesn't exist
        version_file = os.path.join(paxd_package_path, ".VERSION")
        if not os.path.exists(version_file):
            with open(version_file, 'w') as f:
                f.write(paxd.paxd_version)
            print(f"Created version file for PaxD: {paxd.paxd_version}")
        
        # Mark PaxD as user-installed if not already marked
        user_installed_file = os.path.join(paxd_package_path, ".USER_INSTALLED")
        if not os.path.exists(user_installed_file):
            with open(user_installed_file, 'w') as f:
                f.write(f"PaxD installed by user on {__import__('datetime').datetime.now().isoformat()}")
            print(f"{Fore.GREEN}Marked PaxD as user-installed")
            
        # 5. Install dependencies of com.mralfiem591.paxd
        print("Installing PaxD dependencies...")
        # Fetch dependenices from the paxd file in the repository
        try:
            repo_url = paxd._read_repository_url()
            repo_url = paxd._resolve_repository_url(repo_url)
            package_data, source_file = paxd._fetch_package_metadata(repo_url, "com.mralfiem591.paxd")
            paxd._verbose_print(f"Successfully fetched PaxD metadata from {source_file}")
            install_info = package_data.get('install', {})
            dependencies = install_info.get('depend', [])
            for dep in dependencies:
                if dep.startswith("paxd:"):
                    paxd_package = dep[len("paxd:"):]
                    paxd.install(paxd_package, user_requested=False)
                elif dep.startswith("pip:"):
                    pip_package = dep[len("pip:"):]
                    os.system(f"pip install {pip_package}")
                # Add more dependency types as needed
                else:
                    print(f"Unknown dependency type for '{dep}'")
        except Exception as e:
            print(f"{Fore.RED}Failed to install PaxD dependencies: {e}")
        # 6. Delete the .FIRSTRUN file
        os.remove(os.path.join(os.path.dirname(__file__), ".FIRSTRUN"))
        print(f"{Fore.GREEN}PaxD first time run initialization complete.")
        print(f"\n{Fore.CYAN}Welcome to PaxD!{Style.RESET_ALL}\nIt is recommended you try out PaxD with our {Fore.YELLOW}paxd-test{Style.RESET_ALL} package - install it with {Fore.GREEN}`paxd install paxd-test`{Style.RESET_ALL}, and run paxd-test to see it in action!\n\nYou can uninstall it later with {Fore.RED}`paxd uninstall paxd-test`{Style.RESET_ALL}.\n")
        
    # Check version file and user-installed file in case they were removed by the user
    # Define PaxD package path
    local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
    paxd_package_path = os.path.join(local_app_data, "com.mralfiem591.paxd")
    os.makedirs(paxd_package_path, exist_ok=True)
    
    # Create version file for PaxD if it doesn't exist
    version_file = os.path.join(paxd_package_path, ".VERSION")
    if not os.path.exists(version_file):
        with open(version_file, 'w') as f:
            f.write(paxd.paxd_version)
        print(f"Created version file for PaxD: {paxd.paxd_version}")
    
    # Mark PaxD as user-installed if not already marked
    user_installed_file = os.path.join(paxd_package_path, ".USER_INSTALLED")
    if not os.path.exists(user_installed_file):
        with open(user_installed_file, 'w') as f:
            f.write(f"PaxD installed by user on {__import__('datetime').datetime.now().isoformat()}")
        print("Marked PaxD as user-installed")
    
    # Set verbose mode if requested
    if args.verbose:
        print(f"{Fore.BLUE}Verbose mode enabled")
        paxd._verbose_print(f"Verbose logging initialized with maximum default lexicographic value of {lexicographic_max_default}", mode=2)
        paxd._verbose_print("Verbose logging initialised", mode=1)
        paxd._verbose_print(f"PaxD version: {paxd.paxd_version}")
        paxd._verbose_print(f"Command to execute: {args.command}")
    
    # Execute commands based on parsed arguments
    try:
        paxd._verbose_print(f"Executing command: {args.command}")
        if args.command == "install":
            paxd._verbose_print(f"Installing package: {args.package_name}, skip_checksum={args.skip_checksum}")
            paxd.install(args.package_name, user_requested=True, skip_checksum=args.skip_checksum)
        elif args.command == "uninstall":
            paxd._verbose_print(f"Uninstalling package: {args.package_name}")
            paxd.uninstall(args.package_name)
        elif args.command == "update":
            force_flag = args.force if hasattr(args, 'force') else False
            paxd._verbose_print(f"Updating package: {args.package_name}, force={force_flag}, skip_checksum={args.skip_checksum}")
            paxd.update(args.package_name, force=force_flag, skip_checksum=args.skip_checksum)
        elif args.command == "update-all":
            paxd._verbose_print("Updating all packages")
            paxd._verbose_print("Updating all packages")
            paxd.update_all()
        elif args.command == "info":
            paxd._verbose_print(f"Getting info for package: {args.package_name}")
            paxd.info(args.package_name, args.fullsize)
        elif args.command == "search":
            paxd._verbose_print(f"Searching for: {args.search_term}")
            # Note: search_term is used instead of package_name for search
            paxd.search(args.search_term)
        elif args.command == "repo-info":
            paxd._verbose_print("Getting repository info")
            paxd.show_repo_info()
        elif args.command == "reinstall":
            if args.package_name == "deltarunedeltarune":
                # sneaky sneaky easter egg
                import random
                rand = random.randint(1, 5)
                if rand == 1:
                    print("Kris Get The Banana\n\nPotassium")
                elif rand == 2:
                    print("NOWS YOUR CHANCE TO BE A [[Big Shot]]")
                elif rand == 3:
                    print("WHAT GIVES PEOPLE FEELINGS OF POWER:\n\nMONEY: ██\nSTATUS: ███\nBEATING JEVIL FIRST TRY: ████████████████████")
                elif rand == 4:
                    print(f"{Fore.MAGENTA}██     {Fore.YELLOW}██{Style.RESET_ALL}\n\nTHE POWER OF PATTERN RECOGNITION")
                elif rand == 5:
                    print("* You said you were a GAMER!!!\n\n* I Only Play Mobile Games\n\n* NOOOOOOOOOOOO!!!")
                exit(0)
            paxd._verbose_print(f"Reinstalling package: {args.package_name}")
            if args.package_name == "com.mralfiem591.paxd":
                print(f"{Fore.RED}Cannot reinstall PaxD itself using PaxD. Please uninstall manually.")
                print(f"{Fore.YELLOW}Reinstalling PaxD itself requires manual uninstallation and reinstallation.")
                print(f"{Fore.YELLOW}Please uninstall PaxD manually, then download and install the latest version from the PaxD repository.")
                return
            paxd.install(args.package_name, user_requested=True)
        elif args.command == "credit":
            paxd._verbose_print("Showing credits")
            paxd.credit()
        elif args.command == "packagedir":
            paxd._verbose_print("Opening package directory")
            packages = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            os.system(f"explorer {packages}")
        elif args.command == "repo":
            paxd._verbose_print("Opening repository in browser")
            os.system(f"start {paxd._resolve_repository_url(paxd._read_repository_url())}")
        elif args.command == "listall":
            paxd._verbose_print("Listing all installed packages")
            paxd.list_installed()
        elif args.command == "export":
            paxd._verbose_print("Exporting installed packages")
            paxd.export()
        elif args.command == "import":
            paxd._verbose_print("Importing packages from export.paxd")
            paxd.import_paxd()
        elif args.command == "message":
            paxd._verbose_print("Sending message to package")
            paxd.message_package()
        elif args.command == "init":
            if not args.y:
                if input(Fore.RED + Style.BRIGHT + "Are you SURE you want to complete first time initialization? This should only ever be done ONCE! Type 'YES' in full capitals to continue.") != "YES":
                    print(f"{Fore.YELLOW}Initialization cancelled by user.")
                    return
            paxd._verbose_print("Performing first time initialization via init command")
            # 1. Create bin directory
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "bin")):
                os.makedirs(os.path.join(os.path.dirname(__file__), "bin"))
                
            # 2. Add bin directory to PATH permanently
            # Note that paxd is Windows only, so no need to check OS
            bin_path = os.path.join(os.path.dirname(__file__), "bin")
            if not os.path.exists(os.path.join(os.path.dirname(__file__), ".BINSKIP")) and os.path.exists(bin_path):
                # Check if we have administrator permission, if not, prompt the user to run as admin and exit
                if not is_admin():
                    print("Please run this script as an administrator, for first time init only.")
                    exit(1)
                # Add the bin folder to path
                if not add_to_path(bin_path):
                    print(f"Failed to add bin folder to PATH. Try manually adding '{bin_path}' to your PATH, and make a .BINSKIP file alongside paxd.")
                    exit(1)
                    
            # 3. Create a paxd.bat in the bin path
            paxd_bin_path = os.path.join(bin_path, "paxd.bat")
            if not os.path.exists(paxd_bin_path):
                with open(paxd_bin_path, 'w') as f:
                    f.write(f"@echo off\n")
                    f.write(f"python {os.path.abspath(__file__)} %*\n")
                print(f"Created paxd.bat at {paxd_bin_path}")
            
            # 4. Register PaxD itself as user-installed and version PaxD
            print("Registering PaxD itself...")
            local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
            paxd_package_path = os.path.join(local_app_data, "com.mralfiem591.paxd")
            
            # Create PaxD's package directory if it doesn't exist
            os.makedirs(paxd_package_path, exist_ok=True)
            
            # Create version file for PaxD if it doesn't exist
            version_file = os.path.join(paxd_package_path, ".VERSION")
            if not os.path.exists(version_file):
                with open(version_file, 'w') as f:
                    f.write(paxd.paxd_version)
                print(f"Created version file for PaxD: {paxd.paxd_version}")
            
            # Mark PaxD as user-installed if not already marked
            user_installed_file = os.path.join(paxd_package_path, ".USER_INSTALLED")
            if not os.path.exists(user_installed_file):
                with open(user_installed_file, 'w') as f:
                    f.write(f"PaxD installed by user on {__import__('datetime').datetime.now().isoformat()}")
                print(f"{Fore.GREEN}Marked PaxD as user-installed")
                
            # 5. Install dependencies of com.mralfiem591.paxd
            print("Installing PaxD dependencies...")
            # Fetch dependenices from the paxd file in the repository
            try:
                repo_url = paxd._read_repository_url()
                repo_url = paxd._resolve_repository_url(repo_url)
                package_data, source_file = paxd._fetch_package_metadata(repo_url, "com.mralfiem591.paxd")
                paxd._verbose_print(f"Successfully fetched PaxD metadata from {source_file}")
                install_info = package_data.get('install', {})
                dependencies = install_info.get('depend', [])
                for dep in dependencies:
                    if dep.startswith("paxd:"):
                        paxd_package = dep[len("paxd:"):]
                        paxd.install(paxd_package, user_requested=False)
                    elif dep.startswith("pip:"):
                        pip_package = dep[len("pip:"):]
                        os.system(f"pip install {pip_package}")
                    # Add more dependency types as needed
                    else:
                        print(f"Unknown dependency type for '{dep}'")
            except Exception as e:
                print(f"{Fore.RED}Failed to install PaxD dependencies: {e}")
            # 6. Delete the .FIRSTRUN file
            os.remove(os.path.join(os.path.dirname(__file__), ".FIRSTRUN"))
            print(f"{Fore.GREEN}PaxD first time run initialization complete.")
            print(f"\n{Fore.CYAN}Welcome to PaxD!{Style.RESET_ALL}\nIt is recommended you try out PaxD with our {Fore.YELLOW}paxd-test{Style.RESET_ALL} package - install it with {Fore.GREEN}`paxd install paxd-test`{Style.RESET_ALL}, and run paxd-test to see it in action!\n\nYou can uninstall it later with {Fore.RED}`paxd uninstall paxd-test`{Style.RESET_ALL}.\n")
            
        elif args.command == "deltarunedeltarunedeltarune":
            # sneaky sneaky easter egg
            import random
            rand = random.randint(1, 4)
            if rand == 1:
                print("Kris Get The Banana\n\nPotassium")
            elif rand == 2:
                print("NOWS YOUR CHANCE TO BE A [[Big Shot]]")
            elif rand == 3:
                print("WHAT GIVES PEOPLE FEELINGS OF POWER:\n\nMONEY: ██\nSTATUS: ███\n BEATING JEVIL FIRST TRY: ████████████████████")
            elif rand == 4:
                print(f"{Fore.MAGENTA}█ {Fore.YELLOW}█{Style.RESET_ALL}\n\nTHE POWER OF PATTERN RECOGNITION")
            
        else:
            paxd._verbose_print(f"Unknown command: {args.command}")
            print(f"{Fore.RED}Unknown command: {args.command}")
            parser.print_help()
            
    except KeyboardInterrupt:
        paxd._verbose_print("Operation cancelled by user (KeyboardInterrupt)")
        print(f"\n{Fore.YELLOW}Operation cancelled by user.")
        sys.exit(1)
    # Remove "except Exception": sentry now handles it

    # Fetch latest version of PaxD from the repository and notify if it has an update
    paxd._verbose_print("Checking for PaxD updates")
    latest_version = paxd.get_latest_version()
    if latest_version and latest_version != paxd.paxd_version and args.command not in ["update", "update-all"]:
        print(f"{Fore.YELLOW}New PaxD version available: {Fore.RED}{paxd.paxd_version}{Fore.YELLOW} -> {Fore.GREEN}{latest_version}\n{Fore.YELLOW}Get it with '{Fore.LIGHTYELLOW_EX}paxd update paxd{Fore.YELLOW}'.")
    # Remove "try"/"except Exception": sentry now handles it

if __name__ == "__main__":
    main()
    bat_file_path = os.path.join(os.path.dirname(__file__), 'bin', 'paxd.bat')