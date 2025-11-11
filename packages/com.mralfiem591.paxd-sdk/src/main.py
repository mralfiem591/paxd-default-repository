# PaxD SDK - the main SDK for use by PaxD packages

import os

# Part 1: utilities that can be accessed by other packages based specifically on the SDK (eg. version)
class SDKDetails:
    Version = "1.2.2"

    @staticmethod
    def AssertVersion(min_version: str) -> bool:
        # Simple version assertion (major.minor.patch)
        min_parts = list(map(int, min_version.split('.')))
        curr_parts = list(map(int, SDKDetails.Version.split('.')))
        for i in range(3):
            if curr_parts[i] > min_parts[i]:
                return True
            elif curr_parts[i] < min_parts[i]:
                return False
        return True
    
    @staticmethod
    def AssertVersionNoExit(min_version: str) -> bool:
        print("[PaxD SDK] AssertVersionNoExit() is deprecated and will be removed in a future update, to be replaced by AssertVersion(). Please update your code accordingly. This function will now behave like AssertVersion().\nRandom person using this code, and have no idea what this means? Please report it to the package developers, to help improve their package. Thank you!")
        return SDKDetails.AssertVersion(min_version)
    
    @staticmethod
    def PrintInfo() -> None:
        print(f"PaxD SDK v{SDKDetails.Version}")
        print("Created for the developers of PaxD, by mralfiem591.")
        print("Made to reduce the boredom of decoding how the messiest codebase in the world works.")

# Part 2: constants for use by other packages
PackageDir = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD')

# Part 3: package management
class Package:
    @staticmethod
    def Install(package_name: str):
        # Remove dangerous characters from package name
        package_name = package_name.replace('/', '').replace('\\', '').replace('..', '').replace('&', '').replace(';', '').replace('|', '')
        
        # Install a package by calling PaxD
        os.system(f"start cmd /c paxd install --skip-checksum {package_name}")

    @staticmethod
    def Uninstall(package_name: str):
        # Remove dangerous characters from package name
        package_name = package_name.replace('/', '').replace('\\', '').replace('..', '').replace('&', '').replace(';', '').replace('|', '')
        
        
        # Uninstall a package by calling PaxD
        os.system(f"start cmd /c paxd uninstall {package_name}")
        
    @staticmethod
    def Update(package_name: str):
        # Remove dangerous characters from package name
        package_name = package_name.replace('/', '').replace('\\', '').replace('..', '').replace('&', '').replace(';', '').replace('|', '')
        
        
        # Update a package by calling PaxD
        os.system(f"start cmd /c paxd update -f --skip-checksum {package_name}")

    @staticmethod
    def IsInstalled(package_name: str) -> bool:
        """Check if a package is installed."""
        package_path = os.path.join(PackageDir, package_name)
        return os.path.exists(package_path)
    
    @staticmethod
    def GetInstalledVersion(package_name: str) -> str:
        """Get the installed version of a package."""
        version_file = os.path.join(PackageDir, package_name, ".VERSION")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        return "Unknown"
    
    @staticmethod
    def ListInstalled() -> list:
        """Get a list of all installed packages."""
        if not os.path.exists(PackageDir):
            return []
        
        packages = []
        for item in os.listdir(PackageDir):
            package_path = os.path.join(PackageDir, item)
            if os.path.isdir(package_path):
                version = Package.GetInstalledVersion(item)
                is_user_installed = os.path.exists(os.path.join(package_path, ".USER_INSTALLED"))
                packages.append({
                    'name': item,
                    'version': version,
                    'user_installed': is_user_installed,
                    'path': package_path
                })
        return packages
    
    @staticmethod
    def GetPackageInfo(package_name: str) -> dict:
        """Get information about an installed package."""
        package_path = os.path.join(PackageDir, package_name)
        if not os.path.exists(package_path):
            return {}
        
        info = {
            'name': package_name,
            'path': package_path,
            'installed': True,
            'version': Package.GetInstalledVersion(package_name),
            'user_installed': os.path.exists(os.path.join(package_path, ".USER_INSTALLED")),
            'has_firstrun': os.path.exists(os.path.join(package_path, ".FIRSTRUN")),
            'has_updaterun': os.path.exists(os.path.join(package_path, ".UPDATERUN"))
        }
        
        # Get dependencies if available
        deps_file = os.path.join(package_path, ".DEPENDENCIES")
        if os.path.exists(deps_file):
            with open(deps_file, 'r') as f:
                info['dependencies'] = [line.strip() for line in f if line.strip()]
        
        return info

# Part 4: File and directory utilities
class Files:
    @staticmethod
    def GetPackageDataDir(package_name: str) -> str:
        """Get the data directory for a specific package."""
        return os.path.join(PackageDir, package_name)
    
    @staticmethod
    def GetPackageTempDir(package_name: str) -> str:
        """Get/create a temporary directory for a package."""
        temp_dir = os.path.join(PackageDir, package_name, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    @staticmethod
    def GetPackageConfigDir(package_name: str) -> str:
        """Get/create a config directory for a package."""
        config_dir = os.path.join(PackageDir, package_name, "config")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    @staticmethod
    def CleanupTempFiles(package_name: str):
        """Clean up temporary files for a package."""
        temp_dir = os.path.join(PackageDir, package_name, "temp")
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

# Part 5: Configuration management
class Config:
    @staticmethod
    def Get(package_name: str, key: str, default=None):
        """Get a configuration value."""
        import json
        config_file = os.path.join(Files.GetPackageConfigDir(package_name), "config.json")
        if not os.path.exists(config_file):
            return default
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get(key, default)
        except (json.JSONDecodeError, IOError):
            return default
    
    @staticmethod
    def Set(package_name: str, key: str, value):
        """Set a configuration value."""
        import json
        config_file = os.path.join(Files.GetPackageConfigDir(package_name), "config.json")
        config = {}
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        config[key] = value
        
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    @staticmethod
    def Delete(package_name: str, key: str):
        """Delete a configuration value."""
        import json
        config_file = os.path.join(Files.GetPackageConfigDir(package_name), "config.json")
        if not os.path.exists(config_file):
            return
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if key in config:
                del config[key]
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
        except (json.JSONDecodeError, IOError):
            pass

# Part 6: Inter-package communication
class Messaging:
    @staticmethod
    def SendMessage(from_package: str, to_package: str, message: dict):
        """Send a message from one package to another."""
        import json
        import datetime
        
        if not os.path.exists(os.path.join(PackageDir, to_package)):
            raise ValueError(f"Package '{to_package}' is not installed.")
        
        message_dir = os.path.join(PackageDir, to_package, "messages")
        os.makedirs(message_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().isoformat()
        # Replace colons with hyphens to make filename Windows-compatible
        safe_timestamp = timestamp.replace(':', '-')
        message_file = os.path.join(message_dir, f"{from_package}_{safe_timestamp}.json")
        
        message_data = {
            'from': from_package,
            'to': to_package,
            'timestamp': timestamp,
            'message': message
        }
        
        with open(message_file, 'w') as f:
            json.dump(message_data, f, indent=2)
    
    @staticmethod
    def GetMessages(package_name: str) -> list:
        """Get all messages for a package."""
        import json
        
        message_dir = os.path.join(PackageDir, package_name, "messages")
        if not os.path.exists(message_dir):
            return []
        
        messages = []
        for file in os.listdir(message_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(message_dir, file), 'r') as f:
                        messages.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass
        
        return sorted(messages, key=lambda x: x.get('timestamp', ''))
    
    @staticmethod
    def ClearMessages(package_name: str):
        """Clear all messages for a package."""
        import shutil
        message_dir = os.path.join(PackageDir, package_name, "messages")
        if os.path.exists(message_dir):
            shutil.rmtree(message_dir)

# Part 7: Repository utilities
class Repository:
    @staticmethod
    def GetRepositoryUrl() -> str:
        """Get the configured repository URL."""
        repository_file = os.path.join(PackageDir, 'com.mralfiem591.paxd', 'repository')
        if os.path.exists(repository_file):
            with open(repository_file, 'r') as f:
                url = f.read().strip()
                if url.startswith("optimised::"):
                    return url[len("optimised::"):]
                return url
        return ""

# Part 8: System integration
class System:    
    @staticmethod
    def GetEnvironmentVar(var_name: str, default: str = "") -> str:
        """Get an environment variable."""
        return os.environ.get(var_name, default)
    
    @staticmethod
    def IsAdmin() -> bool:
        """Check if running with administrator privileges."""
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin()) # type: ignore # Package runner already enforces Windows only, can be ignored
        except Exception:
            return False

# Part 9: Helper functions for common tasks
class Helpers:
    @staticmethod
    def DownloadFile(url: str, destination: str) -> bool:
        """Download a file from a URL."""
        try:
            import urllib.request
            urllib.request.urlretrieve(url, destination)
            return True
        except Exception:
            return False
    
    @staticmethod
    def ExtractArchive(archive_path: str, extract_to: str) -> bool:
        """Extract a zip archive."""
        try:
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            return True
        except Exception:
            return False
    
    @staticmethod
    def GetFileHash(file_path: str, algorithm: str = "sha256") -> str:
        """Get the hash of a file."""
        import hashlib
        
        if algorithm.lower() == "sha256":
            hash_obj = hashlib.sha256()
        elif algorithm.lower() == "md5":
            hash_obj = hashlib.md5()
        else:
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            return ""
    
    @staticmethod
    def ParseJsonc(jsonc_text: str) -> dict:
        # Parse JSONC (JSON with comments) by removing comments.
        # This mainly exists because the paxd file in packages on a repository is formatted in JSONC, containing comments.
        # This makes it not function with pythons built in "json" module. This parser will replace the "json" module.
        
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
        import json
        return json.loads(cleaned_json)
    
    @staticmethod
    def AssertVersion(min_version_1: str, min_version_2: str) -> bool:
        # Simple version assertion (major.minor.patch)
        # Return True if min_version_1 >= min_version_2
        min_parts_1 = list(map(int, min_version_1.split('.')))
        min_parts_2 = list(map(int, min_version_2.split('.')))
        for i in range(3):
            if min_parts_1[i] > min_parts_2[i]:
                return True
            elif min_parts_1[i] < min_parts_2[i]:
                return False
        return True

        
if __name__ == "__main__":
    SDKDetails.PrintInfo()
    print("\nPlease do not run this SDK directly.")
    print("Instead, import it into another file.")
    exit(1)
