"""
Package Manager for PaxD GUI
Handles PaxD command execution and package operations
"""

import subprocess
import threading
import sys
import os
from typing import Dict, List, Optional


class PackageManager:
    def __init__(self):
        self.paxd_executable = self.find_paxd_executable()
    
    def find_paxd_executable(self) -> str:
        """Find PaxD executable"""
        # Try common locations
        possible_paths = [
            "paxd",  # In PATH
            "paxd.exe",  # Windows with extension
            os.path.join(os.path.expanduser("~"), ".local", "bin", "paxd"),  # Local install
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        # Default to "paxd" and hope it's in PATH
        return "paxd"
    
    def execute_command(self, args: List[str], timeout: int = 60) -> Dict:
        """Execute PaxD command"""
        full_args = [self.paxd_executable] + args
        
        try:
            result = subprocess.run(
                full_args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'output': result.stdout,
                'error': result.stderr,
                'args': full_args
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'return_code': -1,
                'output': '',
                'error': f'Command timed out after {timeout} seconds',
                'args': full_args
            }
        except FileNotFoundError:
            return {
                'success': False,
                'return_code': -1,
                'output': '',
                'error': f'PaxD executable not found: {self.paxd_executable}',
                'args': full_args
            }
        except Exception as e:
            return {
                'success': False,
                'return_code': -1,
                'output': '',
                'error': f'Unexpected error: {str(e)}',
                'args': full_args
            }
    
    def execute_action(self, package: Dict, action: str) -> Dict:
        """Execute action on package"""
        package_identifier = self.get_package_identifier(package)
        
        try:
            if action == 'install':
                result = self.install_package(package_identifier)
            elif action == 'update':
                result = self.update_package(package_identifier)
            elif action == 'force_update':
                result = self.force_update_package(package_identifier)
            elif action == 'uninstall':
                result = self.uninstall_package(package_identifier)
            else:
                return {
                    'success': False,
                    'message': f'Unknown action: {action}',
                    'output': '',
                    'error': f'Action "{action}" is not supported'
                }
            
            # Add user-friendly message
            if result['success']:
                action_past = {
                    'install': 'installed',
                    'update': 'updated',
                    'force_update': 'force updated',
                    'uninstall': 'uninstalled'
                }.get(action, action)
                result['message'] = f'{package["package_name"]} {action_past} successfully'
            else:
                result['message'] = f'Failed to {action} {package["package_name"]}: {result.get("error", "Unknown error")}'
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error during {action}: {str(e)}',
                'output': '',
                'error': str(e)
            }
    
    def get_package_identifier(self, package: Dict) -> str:
        """Get the best identifier for a package"""
        # Prefer alias if available, otherwise use package ID
        aliases = package.get('aliases', [])
        if aliases:
            # Use the first alias (usually the main one)
            return aliases[0]
        else:
            return package['package_id']
    
    def install_package(self, identifier: str) -> Dict:
        """Install package"""
        result = self.execute_command(['install', identifier])
        return result
    
    def update_package(self, identifier: str) -> Dict:
        """Update package"""
        result = self.execute_command(['update', identifier])
        return result
    
    def force_update_package(self, identifier: str) -> Dict:
        """Force update package"""
        result = self.execute_command(['update', '-f', identifier])
        return result
    
    def uninstall_package(self, identifier: str) -> Dict:
        """Uninstall package"""
        result = self.execute_command(['uninstall', identifier])
        return result
    
    def get_installed_packages(self) -> List[str]:
        """Get list of installed packages"""
        result = self.execute_command(['list', '--installed'])
        if result['success']:
            # Parse output to get package names/IDs
            lines = result['output'].strip().split('\n')
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package identifier from line
                    # This depends on the actual format of 'paxd list --installed'
                    parts = line.split()
                    if parts:
                        packages.append(parts[0])
            return packages
        return []
    
    def search_packages(self, query: str = '') -> List[Dict]:
        """Search for packages"""
        args = ['search']
        if query:
            args.append(query)
        
        result = self.execute_command(args)
        if result['success']:
            # Parse search results
            # This would need to be implemented based on PaxD's search output format
            return self.parse_search_results(result['output'])
        return []
    
    def parse_search_results(self, output: str) -> List[Dict]:
        """Parse search results from PaxD output"""
        # This is a placeholder - implement based on actual PaxD search output format
        packages = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # This is a very basic parser - adjust based on actual format
                parts = line.split('\t')  # Assuming tab-separated
                if len(parts) >= 3:
                    packages.append({
                        'package_id': parts[0],
                        'package_name': parts[1],
                        'description': parts[2] if len(parts) > 2 else '',
                        'version': parts[3] if len(parts) > 3 else 'Unknown',
                        'author': parts[4] if len(parts) > 4 else 'Unknown',
                        'installed': False  # Would need to check separately
                    })
        
        return packages
    
    def get_package_info(self, identifier: str) -> Optional[Dict]:
        """Get detailed information about a package"""
        result = self.execute_command(['info', identifier])
        if result['success']:
            # Parse package info
            return self.parse_package_info(result['output'])
        return None
    
    def parse_package_info(self, output: str) -> Dict:
        """Parse package info from PaxD output"""
        # Placeholder implementation
        info = {
            'package_id': 'unknown',
            'package_name': 'Unknown',
            'description': 'No description available',
            'version': 'Unknown',
            'author': 'Unknown',
            'installed': False
        }
        
        # Parse the output to extract package information
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key in info:
                    info[key] = value
        
        return info