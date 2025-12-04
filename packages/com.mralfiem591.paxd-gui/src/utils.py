"""
Utility functions for PaxD GUI
"""

import requests
import csv
import io
from typing import List, Dict, Optional
import paxd_sdk as sdk  # type: ignore


def fetch_search_index() -> str:
    """Fetch search index CSV from repository"""
    try:
        repo_url = sdk.GetRepositoryUrl()
        searchindex_url = f"{repo_url}/searchindex.csv"
        
        response = requests.get(searchindex_url, timeout=10)
        response.raise_for_status()
        
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch search index: {str(e)}")
    except Exception as e:
        raise Exception(f"Error accessing repository: {str(e)}")


def parse_search_index(csv_content: str) -> List[Dict]:
    """Parse search index CSV content into package list"""
    packages = []
    
    try:
        # Use StringIO to treat string as file-like object
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            # Parse aliases
            aliases_str = row.get('aliases', '').strip()
            aliases = []
            if aliases_str:
                aliases = [alias.strip() for alias in aliases_str.split('|') if alias.strip()]
            
            package = {
                'package_id': row.get('package_id', '').strip(),
                'package_name': row.get('package_name', '').strip(),
                'description': row.get('description', '').strip(),
                'author': row.get('author', '').strip(),
                'version': row.get('version', '').strip(),
                'alias': row.get('alias', '').strip(),  # Main alias
                'aliases': aliases,  # All aliases as list
                'installed': False  # Will be updated later
            }
            
            # Skip empty entries
            if package['package_id'] and package['package_name']:
                packages.append(package)
    
    except csv.Error as e:
        raise Exception(f"Failed to parse CSV: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing search index: {str(e)}")
    
    return packages


def is_package_installed(package_id: str) -> bool:
    """Check if package is installed using SDK"""
    try:
        return sdk.IsInstalled(package_id)
    except Exception:
        return False


def get_repository_url() -> str:
    """Get repository URL using SDK"""
    try:
        return sdk.GetRepositoryUrl()
    except Exception:
        return "https://github.com/mralfiem/paxd-packages"  # Default fallback


def format_package_size(size_bytes: Optional[int]) -> str:
    """Format package size in human readable format"""
    if size_bytes is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def validate_package_data(package: Dict) -> bool:
    """Validate package data structure"""
    required_fields = ['package_id', 'package_name', 'version', 'author']
    
    for field in required_fields:
        if field not in package or not package[field]:
            return False
    
    return True


def search_packages(packages: List[Dict], query: str, search_fields: Optional[List[str]] = None) -> List[Dict]:
    """Search packages by query in specified fields"""
    if not query:
        return packages
    
    if search_fields is None:
        search_fields = ['package_name', 'description', 'author', 'package_id']
    
    query_lower = query.lower()
    results = []
    
    for package in packages:
        for field in search_fields:
            if field in package and package[field]:
                if query_lower in package[field].lower():
                    results.append(package)
                    break  # Don't add the same package multiple times
    
    return results


def filter_packages_by_status(packages: List[Dict], status: str) -> List[Dict]:
    """Filter packages by installation status"""
    if status == "all":
        return packages
    elif status == "installed":
        return [pkg for pkg in packages if pkg.get('installed', False)]
    elif status == "not installed":
        return [pkg for pkg in packages if not pkg.get('installed', False)]
    else:
        return packages


def sort_packages(packages: List[Dict], sort_by: str = 'package_name', reverse: bool = False) -> List[Dict]:
    """Sort packages by specified field"""
    valid_fields = ['package_name', 'version', 'author', 'package_id', 'description']
    
    if sort_by not in valid_fields:
        sort_by = 'package_name'
    
    try:
        return sorted(packages, key=lambda x: x.get(sort_by, '').lower(), reverse=reverse)
    except Exception:
        return packages


def get_package_display_name(package: Dict) -> str:
    """Get display name for package (prefers package_name over package_id)"""
    return package.get('package_name', package.get('package_id', 'Unknown Package'))


def get_package_identifier(package: Dict) -> str:
    """Get the best identifier for package operations (alias > package_id)"""
    aliases = package.get('aliases', [])
    if aliases:
        return aliases[0]  # Use first alias
    
    main_alias = package.get('alias', '').strip()
    if main_alias:
        return main_alias
    
    return package.get('package_id', '')


def extract_error_message(error_output: str) -> str:
    """Extract meaningful error message from command output"""
    if not error_output:
        return "Unknown error occurred"
    
    # Split into lines and look for error patterns
    lines = error_output.strip().split('\n')
    
    # Common error patterns to look for
    error_patterns = [
        'Error:',
        'ERROR:',
        'error:',
        'Failed:',
        'FAILED:',
        'failed:',
        'Exception:',
        'EXCEPTION:'
    ]
    
    for line in lines:
        line = line.strip()
        for pattern in error_patterns:
            if pattern in line:
                # Return the line after removing the pattern
                return line.replace(pattern, '').strip()
    
    # If no specific error pattern found, return the first non-empty line
    for line in lines:
        line = line.strip()
        if line:
            return line
    
    return error_output.strip()


def create_backup_package_list(packages: List[Dict]) -> str:
    """Create a backup string of installed packages"""
    installed = [pkg for pkg in packages if pkg.get('installed', False)]
    
    backup_lines = []
    backup_lines.append("# PaxD Package Backup")
    backup_lines.append(f"# Generated on {__import__('datetime').datetime.now().isoformat()}")
    backup_lines.append("")
    
    for package in installed:
        backup_lines.append(f"{package['package_id']} # {package['package_name']} v{package['version']}")
    
    return '\n'.join(backup_lines)


def parse_backup_package_list(backup_content: str) -> List[str]:
    """Parse backup content to extract package IDs"""
    package_ids = []
    
    lines = backup_content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract package ID (everything before the first space or #)
            parts = line.split()
            if parts:
                package_id = parts[0]
                if package_id:
                    package_ids.append(package_id)
    
    return package_ids