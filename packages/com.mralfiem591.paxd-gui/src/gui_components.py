"""
GUI Components for PaxD GUI
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Optional


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
        self.search_var.trace('w', self.on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Filter frame
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.filter_var,
            values=["all", "installed", "not installed"],
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
        self.tree.column('name', width=200, minwidth=150)
        self.tree.column('version', width=80, minwidth=60)
        self.tree.column('author', width=120, minwidth=100)
        self.tree.column('status', width=100, minwidth=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
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
            status = "✓ Installed" if package.get('installed', False) else "Not installed"
            icon = "✓" if package.get('installed', False) else ""
            
            self.tree.insert('', 'end', 
                text=icon,
                values=(
                    package['package_name'],
                    package['version'],
                    package['author'],
                    status
                ),
                tags=('installed' if package.get('installed', False) else 'not_installed',)
            )
        
        # Configure tags
        self.tree.tag_configure('installed', foreground='green')
        self.tree.tag_configure('not_installed', foreground='black')
    
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
        
        # Queue status
        self.queue_status_label = ttk.Label(actions_frame, text="", foreground="blue")
        self.queue_status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Initially hide all widgets
        self.hide_details()
    
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
        status_text = "✓ Installed" if installed else "Not installed"
        self.status_label.config(
            text=f"Status: {status_text}",
            foreground="green" if installed else "red"
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
        if installed:
            self.install_radio.config(state=tk.DISABLED)
            self.update_radio.config(state=tk.NORMAL)
            self.uninstall_radio.config(state=tk.NORMAL)
        else:
            self.install_radio.config(state=tk.NORMAL)
            self.update_radio.config(state=tk.DISABLED)
            self.uninstall_radio.config(state=tk.DISABLED)
    
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
            self.current_action = action
            self.update_queue_status()
            self.on_action(self.current_package, action)
    
    def hide_details(self):
        """Hide package details"""
        for widget in self.winfo_children():
            widget.pack_forget()
    
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


class QueueFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup queue UI"""
        # Title
        title_label = ttk.Label(self, text="Action Queue", font=('TkDefaultFont', 10, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Queue list
        self.queue_listbox = tk.Listbox(self, height=8)
        self.queue_listbox.pack(fill=tk.BOTH, expand=True)
    
    def update_queue(self, queue: List[Dict]):
        """Update queue display"""
        self.queue_listbox.delete(0, tk.END)
        for item in queue:
            package_name = item['package']['package_name']
            action = item['action'].title()
            self.queue_listbox.insert(tk.END, f"{action}: {package_name}")