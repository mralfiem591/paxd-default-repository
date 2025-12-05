#!/usr/bin/env python3
"""
PaxD GUI - A graphical user interface for PaxD package management
Combined single-file version with all components included.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import subprocess
import sys
import os
import requests
import csv
import io
from typing import List, Dict, Optional, Callable
import atexit
import shutil

atexit.register(lambda: print("PaxD GUI has exited.\nSo long and thanks for all the fish!"))

try:
    import paxd_sdk as sdk  # type: ignore
except ImportError:
    print("PaxD SDK not found. Please install it using 'paxd install com.mralfiem591.paxd-sdk'")
    sys.exit(1)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def fetch_search_index() -> str:
    """Fetch search index CSV from repository"""
    try:
        repo_url = sdk.Repository.GetRepositoryUrl()
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
        return sdk.Package.IsInstalled(package_id)
    except Exception:
        return False


def get_repository_url() -> str:
    """Get repository URL using SDK"""
    try:
        return sdk.Repository.GetRepositoryUrl()
    except Exception:
        return "https://github.com/mralfiem/paxd-packages"  # Default fallback


def validate_package_data(package: Dict) -> bool:
    """Validate package data structure"""
    required_fields = ['package_id', 'package_name', 'version', 'author']
    
    for field in required_fields:
        if field not in package or not package[field]:
            return False
    
    return True


def get_package_identifier(package: Dict) -> str:
    """Get the best identifier for package operations (alias > package_id)"""
    aliases = package.get('aliases', [])
    if aliases:
        return aliases[0]  # Use first alias
    
    main_alias = package.get('alias', '').strip()
    if main_alias:
        return main_alias
    
    return package.get('package_id', '')


# ============================================================================
# PACKAGE MANAGER
# ============================================================================

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
                    timeout=5,
                    shell=True,  # Use shell to inherit PATH on Windows
                    env=os.environ  # Explicitly pass environment variables
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
                cwd=os.getcwd(),
                shell=True,  # Use shell to inherit PATH on Windows
                env=os.environ  # Explicitly pass environment variables
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
        package_identifier = get_package_identifier(package)
        
        try:
            # Special handling for GUI uninstall
            if (action == 'uninstall' and 
                (package.get('package_id') == 'com.mralfiem591.paxd-gui' or
                 'paxd-gui' in package.get('aliases', []))):
                
                # Use SDK messaging to queue GUI uninstall after exit
                try:
                    sdk.Messaging.SendMessage(
                        'com.mralfiem591.paxd-gui',
                        'com.mralfiem591.paxd',
                        {'queue_gui_uninstall': True}
                    )
                    return {
                        'success': True,
                        'message': 'GUI queued for uninstall after exit',
                        'output': 'Uninstall message sent to main PaxD package',
                        'error': ''
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Failed to queue GUI uninstall: {str(e)}',
                        'output': '',
                        'error': str(e)
                    }
            
            if action == 'install':
                result = self.install_package(package_identifier)
            elif action == 'update':
                result = self.update_package(package_identifier)
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
    
    def install_package(self, identifier: str) -> Dict:
        """Install package"""
        result = self.execute_command(['install', identifier])
        return result
    
    def update_package(self, identifier: str) -> Dict:
        """Update package"""
        result = self.execute_command(['update', identifier])
        return result
    
    def uninstall_package(self, identifier: str) -> Dict:
        """Uninstall package"""
        result = self.execute_command(['uninstall', identifier])
        return result
    
    def export_packages(self, export_file_path: str) -> Dict:
        """Export packages to .paxd file"""
        try:
            # Run paxd export
            result = self.execute_command(['export'])
            
            if result['success']:
                # Get package directory from SDK
                package_dir = sdk.PackageDir
                export_source = os.path.join(package_dir, "export.paxd")
                
                # Check if export.paxd was created
                if os.path.exists(export_source):
                    # Copy to target location
                    shutil.copy2(export_source, export_file_path)
                    
                    # Clean up the original export.paxd
                    try:
                        os.remove(export_source)
                    except Exception:
                        pass  # Ignore cleanup errors
                else:
                    return {
                        'success': False,
                        'return_code': -1,
                        'output': result.get('output', ''),
                        'error': 'Export file was not created'
                    }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'return_code': -1,
                'output': '',
                'error': f'Export error: {str(e)}'
            }


# ============================================================================
# GUI COMPONENTS
# ============================================================================

class PackageListFrame(ttk.Frame):
    def __init__(self, parent, on_package_select: Callable):
        super().__init__(parent)
        self.on_package_select = on_package_select
        self.packages = []
        self.filtered_packages = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup package list UI"""
        # Search frame
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Filter frame
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.filter_var,
            values=["all", "installed", "not installed", "updates available"],
            state="readonly"
        )
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind('<<ComboboxSelected>>', self.on_filter_changed)
        
        ttk.Label(filter_frame, text="packages").pack(side=tk.LEFT, padx=(5, 0))
        
        # Package list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for package list
        columns = ('name', 'version', 'author', 'status')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)
        
        # Configure columns
        self.tree.heading('#0', text='', anchor=tk.W)
        self.tree.heading('name', text='Name', anchor=tk.W)
        self.tree.heading('version', text='Version', anchor=tk.W)
        self.tree.heading('author', text='Author', anchor=tk.W)
        self.tree.heading('status', text='Status', anchor=tk.W)
        
        self.tree.column('#0', width=30, minwidth=30, stretch=False)
        self.tree.column('name', width=150, minwidth=100, stretch=True)
        self.tree.column('version', width=60, minwidth=50, stretch=False)
        self.tree.column('author', width=80, minwidth=60, stretch=True)
        self.tree.column('status', width=80, minwidth=60, stretch=False)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_changed)
    
    def update_packages(self, packages: List[Dict]):
        """Update package list"""
        self.packages = packages
        self.filter_packages()
    
    def filter_packages(self):
        """Filter and display packages"""
        search_term = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        
        # Filter packages
        filtered = []
        for package in self.packages:
            # Search filter
            if search_term and search_term not in package['package_name'].lower() and \
               search_term not in package['description'].lower() and \
               search_term not in package['author'].lower():
                continue
            
            # Status filter
            if filter_type == "installed" and not package.get('installed', False):
                continue
            elif filter_type == "not installed" and package.get('installed', False):
                continue
            elif filter_type == "updates available" and not package.get('update_available', False):
                continue
            
            filtered.append(package)
        
        self.filtered_packages = filtered
        self.display_packages()
    
    def display_packages(self):
        """Display filtered packages in treeview"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add packages
        for package in self.filtered_packages:
            installed = package.get('installed', False)
            update_available = package.get('update_available', False)
            
            if installed and update_available:
                status = f"✓ Installed - Update available! {package.get('installed_version', 'Unknown')} > {package['version']}"
                icon = "⚠"
                tag = 'update_available'
            elif installed:
                status = "✓ Installed"
                icon = "✓"
                tag = 'installed'
            else:
                status = "Not installed"
                icon = ""
                tag = 'not_installed'
            
            self.tree.insert('', 'end', 
                text=icon,
                values=(
                    package['package_name'],
                    package['version'],
                    package['author'],
                    status
                ),
                tags=(tag,)
            )
        
        # Configure tags
        self.tree.tag_configure('installed', foreground='green')
        self.tree.tag_configure('not_installed', foreground='black')
        self.tree.tag_configure('update_available', foreground='orange', font=('TkDefaultFont', 9, 'bold'))
    
    def on_search_changed(self, *args):
        """Handle search change"""
        self.filter_packages()
    
    def on_filter_changed(self, event=None):
        """Handle filter change"""
        self.filter_packages()
    
    def on_selection_changed(self, event):
        """Handle selection change"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            package_name = item['values'][0]
            
            # Find package by name
            for package in self.filtered_packages:
                if package['package_name'] == package_name:
                    self.on_package_select(package)
                    break
        else:
            # No selection, show placeholder in details frame
            # We'll handle this by checking if a details frame method exists
            pass


class PackageDetailsFrame(ttk.Frame):
    def __init__(self, parent, on_action: Callable):
        super().__init__(parent)
        self.on_action = on_action
        self.current_package = None
        self.current_action = 'none'
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup package details UI"""
        # Title
        self.title_label = ttk.Label(self, text="Select a package", font=('TkDefaultFont', 12, 'bold'))
        self.title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Package info frame
        info_frame = ttk.LabelFrame(self, text="Package Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Info labels
        self.version_label = ttk.Label(info_frame, text="")
        self.version_label.pack(anchor=tk.W)
        
        self.author_label = ttk.Label(info_frame, text="")
        self.author_label.pack(anchor=tk.W)
        
        self.id_label = ttk.Label(info_frame, text="")
        self.id_label.pack(anchor=tk.W)
        
        self.alias_label = ttk.Label(info_frame, text="")
        self.alias_label.pack(anchor=tk.W)
        
        self.status_label = ttk.Label(info_frame, text="")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Description frame
        desc_frame = ttk.LabelFrame(self, text="Description", padding="10")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.description_text = tk.Text(desc_frame, wrap=tk.WORD, height=4, state=tk.DISABLED)
        self.description_text.pack(fill=tk.BOTH, expand=True)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(self, text="Actions", padding="10")
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.action_var = tk.StringVar(value="none")
        
        # Action radio buttons
        self.none_radio = ttk.Radiobutton(
            actions_frame, text="No action", 
            variable=self.action_var, value="none",
            command=self.on_action_changed
        )
        self.none_radio.pack(anchor=tk.W)
        
        self.install_radio = ttk.Radiobutton(
            actions_frame, text="Install", 
            variable=self.action_var, value="install",
            command=self.on_action_changed
        )
        self.install_radio.pack(anchor=tk.W)
        
        self.update_radio = ttk.Radiobutton(
            actions_frame, text="Update", 
            variable=self.action_var, value="update",
            command=self.on_action_changed
        )
        self.update_radio.pack(anchor=tk.W)
        
        self.uninstall_radio = ttk.Radiobutton(
            actions_frame, text="Uninstall", 
            variable=self.action_var, value="uninstall",
            command=self.on_action_changed
        )
        self.uninstall_radio.pack(anchor=tk.W)
        
        # Label for GUI package uninstall instruction
        self.uninstall_note_label = ttk.Label(
            actions_frame, text="", 
            foreground="gray", font=('TkDefaultFont', 8)
        )
        self.uninstall_note_label.pack(anchor=tk.W, padx=(20, 0))
        
        # Queue status
        self.queue_status_label = ttk.Label(actions_frame, text="", foreground="blue")
        self.queue_status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Show placeholder content instead of hiding initially
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder content when no package is selected"""
        # Update labels with placeholder content
        self.title_label.config(text="")
        self.version_label.config(text="")
        self.author_label.config(text="")
        self.id_label.config(text="")
        self.alias_label.config(text="")
        self.status_label.config(text="")
        
        # Update description with placeholder text
        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, "Select a package from the side to start!")
        self.description_text.config(state=tk.DISABLED)
        
        # Set action to none and disable all options
        self.action_var.set("none")
        self.none_radio.config(state=tk.NORMAL)
        self.install_radio.config(state=tk.DISABLED)
        self.update_radio.config(state=tk.DISABLED)
        self.uninstall_radio.config(state=tk.DISABLED)
        self.uninstall_note_label.config(text="")
        self.queue_status_label.config(text="")
        
        # Show all widgets (they're already configured above)
        self.show_details()
    
    def show_package(self, package: Dict, queued_action: str = 'none'):
        """Show package details"""
        self.current_package = package
        self.current_action = queued_action
        
        # Update labels
        self.title_label.config(text=package['package_name'])
        self.version_label.config(text=f"Version: {package['version']}")
        self.author_label.config(text=f"Author: {package['author']}")
        self.id_label.config(text=f"ID: {package['package_id']}")
        
        aliases = package.get('aliases', [])
        if aliases:
            alias_text = f"Aliases: {', '.join(aliases)}"
        else:
            alias_text = "No aliases"
        self.alias_label.config(text=alias_text)
        
        installed = package.get('installed', False)
        update_available = package.get('update_available', False)
        installed_version = package.get('installed_version')
        
        if installed and update_available and installed_version:
            status_text = f"✓ Installed ({installed_version}) - Update available to {package['version']}!"
            status_color = "orange"
        elif installed:
            status_text = f"✓ Installed" + (f" ({installed_version})" if installed_version else "")
            status_color = "green"
        else:
            status_text = "Not installed"
            status_color = "red"
            
        self.status_label.config(
            text=f"Status: {status_text}",
            foreground=status_color
        )
        
        # Update description
        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, package['description'])
        self.description_text.config(state=tk.DISABLED)
        
        # Update action buttons
        self.update_action_buttons(installed)
        
        # Set queued action
        self.action_var.set(queued_action)
        self.update_queue_status()
        
        # Show all widgets
        self.show_details()
    
    def update_action_buttons(self, installed: bool):
        """Update action button states"""
        # Check if this is a protected package (prevent uninstallation)
        is_gui_package = (self.current_package and 
                         (self.current_package.get('package_id') == 'com.mralfiem591.paxd-gui' or
                          'paxd-gui' in self.current_package.get('aliases', [])))
        
        is_main_paxd = (self.current_package and 
                       (self.current_package.get('package_id') == 'com.mralfiem591.paxd' or
                        'paxd' in self.current_package.get('aliases', [])))
        
        is_paxd_sdk = (self.current_package and 
                      (self.current_package.get('package_id') == 'com.mralfiem591.paxd-sdk' or
                       'paxd-sdk' in self.current_package.get('aliases', [])))
        
        # Only main PaxD and SDK cannot be uninstalled (GUI can now be uninstalled via messaging)
        is_protected = is_main_paxd or is_paxd_sdk
        
        if installed:
            self.install_radio.config(state=tk.DISABLED)
            self.update_radio.config(state=tk.NORMAL)
            # Disable uninstall for protected packages only (not GUI)
            self.uninstall_radio.config(state=tk.DISABLED if is_protected else tk.NORMAL)
            
            # Show appropriate uninstall instruction/warning for protected packages
            if is_gui_package:
                self.uninstall_note_label.config(
                    text="(will queue GUI for uninstall after exit)"
                )
            elif is_main_paxd:
                self.uninstall_note_label.config(
                    text="(cannot be uninstalled; is main PaxD core and needed for commands)"
                )
            elif is_paxd_sdk:
                self.uninstall_note_label.config(
                    text="(cannot be uninstalled; is dependency of this GUI, and is required for proper functionality)"
                )
            else:
                self.uninstall_note_label.config(text="")
        else:
            self.install_radio.config(state=tk.NORMAL)
            self.update_radio.config(state=tk.DISABLED)
            self.uninstall_radio.config(state=tk.DISABLED)
            self.uninstall_note_label.config(text="")
    
    def update_queue_status(self):
        """Update queue status display"""
        action = self.action_var.get()
        if action == 'none':
            self.queue_status_label.config(text="")
        else:
            self.queue_status_label.config(text=f"Queued: {action.title()}")
    
    def on_action_changed(self):
        """Handle action change"""
        if self.current_package:
            action = self.action_var.get()
            
            # Check for vulnerability scanner uninstall warning
            if (action == 'uninstall' and 
                self.current_package and
                (self.current_package.get('package_id') == 'com.mralfiem591.vulnerability' or
                 'vulnerability' in self.current_package.get('aliases', []))):
                
                # Show warning dialog
                result = messagebox.askyesno(
                    "Security Warning",
                    "You are about to uninstall the PaxD vulnerability scanner.\n\n"
                    "This package protects your system by scanning for exploits and vulnerabilities in packages. "
                    "Without it, your system may be vulnerable to security threats from malicious packages.\n\n"
                    "Are you sure you want to uninstall the vulnerability scanner?",
                    icon="warning"
                )
                
                # If user cancels, reset to no action
                if not result:
                    self.action_var.set('none')
                    self.current_action = 'none'
                    self.update_queue_status()
                    self.on_action(self.current_package, 'none')
                    return
            
            self.current_action = action
            self.update_queue_status()
            self.on_action(self.current_package, action)
    
    def hide_details(self):
        """Hide package details"""
        for widget in self.winfo_children():
            # Only call pack_forget on widgets that support it
            if hasattr(widget, 'pack_forget'):
                widget.pack_forget() # type: ignore
    
    def show_details(self):
        """Show package details"""
        self.title_label.pack(anchor=tk.W, pady=(0, 10))
        
        for widget in self.winfo_children():
            if widget != self.title_label:
                if isinstance(widget, ttk.LabelFrame):
                    if "Description" in widget.cget('text'):
                        widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
                    else:
                        widget.pack(fill=tk.X, pady=(0, 10))


# ============================================================================
# QUEUE WINDOW
# ============================================================================

class QueueWindow:
    def __init__(self, parent, queue, package_manager, refresh_callback=None):
        self.queue = queue
        self.package_manager = package_manager
        self.parent_refresh_callback = refresh_callback
        self.gui_was_updated = False  # Track if GUI was updated
        
        self.window = tk.Toplevel(parent)
        self.window.title("Processing Queue")
        self.window.geometry("600x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.window.winfo_screenheight() // 2) - (400 // 2)
        self.window.geometry(f"600x400+{x}+{y}")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup queue window UI"""
        # Progress info
        info_frame = ttk.Frame(self.window, padding="10")
        info_frame.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(info_frame, text="Preparing...")
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(info_frame, mode='determinate', maximum=len(self.queue))
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(self.window, text="Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Close button (initially disabled)
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill=tk.X)
        
        self.close_button = ttk.Button(
            button_frame, 
            text="Close", 
            command=self.window.destroy,
            state=tk.DISABLED
        )
        self.close_button.pack(side=tk.RIGHT)
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.window.update()
        
        # Also print
        print(message)
    
    def start_processing(self):
        """Start processing queue"""
        def process():
            try:
                for i, item in enumerate(self.queue):
                    package = item['package']
                    action = item['action']
                    
                    self.progress_label.config(text=f"Processing {package['package_name']} ({action})...")
                    self.progress_bar['value'] = i
                    
                    self.log(f"Processing: {package['package_name']} - {action}")
                    
                    try:
                        result = self.package_manager.execute_action(package, action)
                        
                        # Check if this is a GUI package update (trigger restart after any update attempt)
                        is_gui_update = (action == 'update' and 
                                       (package.get('package_id') == 'com.mralfiem591.paxd-gui' or
                                        'paxd-gui' in package.get('aliases', [])))
                        
                        # Always show as attempted, regardless of actual outcome
                        if action == 'update':
                            self.log(f"✓ Update attempted of {package['package_name']}!")
                            # Mark GUI as updated if this was a GUI update attempt
                            if is_gui_update:
                                self.gui_was_updated = True
                        elif action == 'uninstall' and (package.get('package_id') == 'com.mralfiem591.paxd-gui' or
                                                       'paxd-gui' in package.get('aliases', [])):
                            # Special handling for GUI uninstall messaging
                            if result.get('success'):
                                self.log(f"✓ {result.get('message', 'GUI queued for uninstall')}")
                                # Show popup about GUI uninstall queue
                                self.window.after(100, lambda: messagebox.showinfo(
                                    "GUI Uninstall Queued",
                                    "The PaxD GUI has been queued for uninstall.\n\n"
                                    "When you exit this application, PaxD package will "
                                    "automatically uninstall the GUI for you.\n\n"
                                    "Thank you for using PaxD GUI, and we hope to see you again soon.\n\n    - mralfiem591 :)"
                                ))
                            else:
                                self.log(f"✗ Failed to queue GUI uninstall: {result.get('message', 'Unknown error')}")
                        elif result.get('success'):
                            self.log(f"✓ Success: {result.get('message', 'Operation completed')}")
                        else:
                            self.log(f"✗ Error: {result.get('message', 'Unknown error')}")
                    
                    except Exception as e:
                        self.log(f"✗ Exception: {str(e)}")
                    
                    self.log("")  # Empty line for readability
                
                self.progress_bar['value'] = len(self.queue)
                self.progress_label.config(text="Processing complete!")
                self.close_button.config(state=tk.NORMAL)
                
                # Trigger refresh in parent window
                if hasattr(self, 'parent_refresh_callback') and self.parent_refresh_callback:
                    self.parent_refresh_callback()
                
                # Check if GUI was updated and restart if needed
                if hasattr(self, 'gui_was_updated') and self.gui_was_updated:
                    self.log("GUI was updated - restarting application...")
                    self.window.after(2000, self._restart_application)  # Wait 2 seconds before restart
                
            except Exception as e:
                self.log(f"Critical error: {str(e)}")
                self.close_button.config(state=tk.NORMAL)
        
        threading.Thread(target=process, daemon=True).start()
    
    def _restart_application(self):
        """Restart the application after GUI update"""
        try:
            # Start new instance
            os.system("start cmd /c paxd gui")
            self.log("Handoff to new GUI instance was a success! This instance will now exit.")
            # Exit current instance
            os._exit(0)
        except Exception as e:
            self.log(f"Failed to restart application: {e}")
            self.close_button.config(state=tk.NORMAL)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class PaxDGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PaxD Package Manager")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Initialize package manager
        self.package_manager = PackageManager()
        
        # Data
        self.packages = []
        self.queue = []
        
        # Setup GUI
        self.setup_gui()
        self.load_packages()
    
    def setup_menu(self):
        """Setup the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import from file", command=self.import_from_file)
        file_menu.add_command(label="Export to file", command=self.export_to_file)
    
    def import_from_file(self):
        """Import packages from a .paxd file"""
        file_path = filedialog.askopenfilename(
            title="Import from .paxd file",
            filetypes=[("PaxD files", "*.paxd"), ("All files", "*.*")],
            defaultextension=".paxd"
        )
        
        if file_path:
            # Validate file extension
            if not file_path.lower().endswith('.paxd'):
                messagebox.showerror("Invalid File", "Please select a .paxd file.")
                return
            
            # Check if file exists
            if not os.path.exists(file_path):
                messagebox.showerror("File Not Found", "The selected file does not exist.")
                return
            
            def import_in_thread():
                try:
                    self.status_var.set("Parsing package file...")
                    
                    # Read and parse the .paxd file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Parse package names (one per line, strip whitespace)
                    package_names = []
                    for line in lines:
                        package_name = line.strip()
                        if package_name and not package_name.startswith('#'):  # Skip empty lines and comments
                            package_names.append(package_name)
                    
                    if not package_names:
                        self.root.after(0, lambda: messagebox.showwarning("No Packages", "No package names found in the file."))
                        self.root.after(0, lambda: self.status_var.set("Ready"))
                        return
                    
                    # Find packages to queue for installation
                    packages_to_install = []
                    already_installed = []
                    not_found = []
                    
                    for package_name in package_names:
                        # Find the package in our loaded packages list
                        found_package = None
                        for package in self.packages:
                            # Check if package name matches package_name, package_id, or any alias
                            if (package['package_name'].lower() == package_name.lower() or
                                package['package_id'].lower() == package_name.lower() or
                                package_name.lower() in [alias.lower() for alias in package.get('aliases', [])]):
                                found_package = package
                                break
                        
                        if found_package:
                            if found_package.get('installed', False):
                                already_installed.append(package_name)
                            else:
                                packages_to_install.append(found_package)
                        else:
                            not_found.append(package_name)
                    
                    # Queue packages for installation
                    queued_count = 0
                    for package in packages_to_install:
                        # Remove any existing action for this package
                        self.queue = [item for item in self.queue if item['package']['package_id'] != package['package_id']]
                        
                        # Add install action
                        self.queue.append({
                            'package': package,
                            'action': 'install'
                        })
                        queued_count += 1
                    
                    # Update queue display and show results
                    self.root.after(0, self.update_queue_display)
                    
                    # Build result message
                    message_parts = []
                    if queued_count > 0:
                        message_parts.append(f"Queued {queued_count} packages for installation.")
                    if already_installed:
                        message_parts.append(f"Already installed ({len(already_installed)}): {', '.join(already_installed)}")
                    if not_found:
                        message_parts.append(f"Not found ({len(not_found)}): {', '.join(not_found)}")
                    
                    result_message = "\n\n".join(message_parts)
                    
                    if queued_count > 0:
                        result_message += "\n\nClick 'Apply Changes' to install the queued packages."
                        self.root.after(0, lambda: messagebox.showinfo("Import Complete", result_message))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("Import Complete", result_message))
                    
                    self.root.after(0, lambda: self.status_var.set("Ready"))
                    
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Import Error", f"Error parsing file: {str(e)}"))
                    self.root.after(0, lambda: self.status_var.set("Ready"))
            
            threading.Thread(target=import_in_thread, daemon=True).start()
    
    def export_to_file(self):
        """Export packages to a .paxd file"""
        file_path = filedialog.asksaveasfilename(
            title="Export to .paxd file",
            filetypes=[("PaxD files", "*.paxd"), ("All files", "*.*")],
            defaultextension=".paxd"
        )
        
        if file_path:
            # Ensure .paxd extension
            if not file_path.lower().endswith('.paxd'):
                file_path += '.paxd'
            
            def export_in_thread():
                try:
                    self.status_var.set("Exporting packages...")
                    result = self.package_manager.export_packages(file_path)
                    
                    if result['success']:
                        self.root.after(0, lambda: messagebox.showinfo("Export Successful", f"Packages exported to:\n{file_path}"))
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        self.root.after(0, lambda: messagebox.showerror("Export Failed", f"Failed to export packages:\n{error_msg}"))
                    
                    self.root.after(0, lambda: self.status_var.set("Ready"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Export Error", f"Error during export: {str(e)}"))
                    self.root.after(0, lambda: self.status_var.set("Ready"))
            
            threading.Thread(target=export_in_thread, daemon=True).start()
        
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Configure grid weights
        self.root.grid_rowconfigure(2, weight=1)  # Adjusted for menu bar
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create menu bar
        self.setup_menu()
        
        # Top frame with apply button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        # Apply button
        self.apply_button = ttk.Button(
            top_frame, 
            text="Apply Changes", 
            command=self.apply_changes,
            style="Accent.TButton"
        )
        self.apply_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Refresh button
        refresh_button = ttk.Button(
            top_frame, 
            text="Refresh", 
            command=self.refresh_packages
        )
        refresh_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Update All button
        update_all_button = ttk.Button(
            top_frame, 
            text="Update All", 
            command=self.update_all_packages
        )
        update_all_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Queue info label
        self.queue_label = ttk.Label(top_frame, text="Queue: 0 actions")
        self.queue_label.pack(side=tk.LEFT)
        
        # Main content area
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Package list frame
        self.package_list_frame = PackageListFrame(
            main_frame, 
            on_package_select=self.on_package_select
        )
        self.package_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Package details frame
        self.package_details_frame = PackageDetailsFrame(
            main_frame,
            on_action=self.on_package_action
        )
        self.package_details_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        
    def load_packages(self):
        """Load packages from search index"""
        def load_in_thread():
            try:
                self.status_var.set("Loading packages...")
                search_index = fetch_search_index()
                self.packages = parse_search_index(search_index)
                
                # Update installed status and check for updates
                for package in self.packages:
                    package['installed'] = sdk.Package.IsInstalled(package['package_id'])
                    
                    # Check for updates if package is installed
                    if package['installed']:
                        try:
                            installed_version = sdk.Package.GetInstalledVersion(package['package_id'])
                            latest_version = package['version']
                            
                            # Check if installed version is latest using AssertVersion
                            is_latest = sdk.Helpers.AssertVersion(installed_version, latest_version)
                            package['update_available'] = not is_latest
                            package['installed_version'] = installed_version
                            
                            # Check if this is the GUI package and needs update
                            if (package['package_id'] == 'com.mralfiem591.paxd-gui' or 
                                'paxd-gui' in package.get('aliases', [])) and not is_latest:
                                print(f"PaxD GUI has an update! {installed_version} > {latest_version}")
                        except Exception as e:
                            # If we can't get version info, assume no update available
                            package['update_available'] = False
                            package['installed_version'] = 'Unknown'
                    else:
                        package['update_available'] = False
                        package['installed_version'] = None
                
                # Update GUI in main thread
                self.root.after(0, lambda: self.update_package_list())
                self.root.after(0, lambda: self.status_var.set(f"Loaded {len(self.packages)} packages"))
            except Exception as e:
                self.root.after(0, lambda: self.show_error("Error loading packages", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error loading packages"))
        
        threading.Thread(target=load_in_thread, daemon=True).start()
    
    def update_package_list(self):
        """Update the package list display"""
        self.package_list_frame.update_packages(self.packages)
    
    def on_package_select(self, package):
        """Handle package selection"""
        self.package_details_frame.show_package(package, self.get_package_queue_action(package))
    
    def on_package_action(self, package, action):
        """Handle package action from details frame"""
        self.add_to_queue(package, action)
    
    def add_to_queue(self, package, action):
        """Add action to queue"""
        # Remove any existing action for this package
        self.queue = [item for item in self.queue if item['package']['package_id'] != package['package_id']]
        
        if action != 'none':
            self.queue.append({
                'package': package,
                'action': action
            })
        
        self.update_queue_display()
        
        # Update package details if it's currently showing
        current_package = self.package_details_frame.current_package
        if current_package and current_package['package_id'] == package['package_id']:
            self.package_details_frame.show_package(package, action)
    
    def get_package_queue_action(self, package):
        """Get the queued action for a package"""
        for item in self.queue:
            if item['package']['package_id'] == package['package_id']:
                return item['action']
        return 'none'
    
    def update_queue_display(self):
        """Update queue display"""
        count = len(self.queue)
        self.queue_label.config(text=f"Queue: {count} action{'s' if count != 1 else ''}")
    
    def apply_changes(self):
        """Apply all queued changes"""
        if not self.queue:
            messagebox.showinfo("No Changes", "No changes to apply.")
            return
        
        # Show queue window
        queue_window = QueueWindow(self.root, self.queue, self.package_manager, self.refresh_packages)
        queue_window.start_processing()
        
        # Clear queue after processing starts
        self.queue = []
        self.update_queue_display()
        
        # Handle window close
        queue_window.window.protocol("WM_DELETE_WINDOW", queue_window.window.destroy)
    
    def refresh_packages(self):
        """Refresh package list"""
        self.load_packages()
    
    def update_all_packages(self):
        """Queue update action for all installed packages"""
        updated_count = 0
        
        for package in self.packages:
            if package.get('installed', False):
                # Remove any existing action for this package
                self.queue = [item for item in self.queue if item['package']['package_id'] != package['package_id']]
                
                # Add update action
                self.queue.append({
                    'package': package,
                    'action': 'update'
                })
                updated_count += 1
        
        if updated_count > 0:
            self.update_queue_display()
            messagebox.showinfo("Update All", f"Queued {updated_count} packages for update.")
            
            # If the currently selected package is in the queue, update its display
            current_package = self.package_details_frame.current_package
            if current_package and current_package.get('installed', False):
                self.package_details_frame.show_package(current_package, 'update')
        else:
            messagebox.showinfo("Update All", "No installed packages found to update.")
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)
    
    def run(self):
        """Run the GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        app = PaxDGUI()
        app.run()
    except Exception as e:
        print(f"Error starting PaxD GUI: {e}")
        sys.exit(1)
