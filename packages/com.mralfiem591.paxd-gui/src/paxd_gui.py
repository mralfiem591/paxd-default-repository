#!/usr/bin/env python3
"""
PaxD GUI - A graphical user interface for PaxD package management
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import sys
import os
from typing import List, Dict, Optional
import csv
import requests

try:
    import paxd_sdk as sdk  # type: ignore
except ImportError:
    print("PaxD SDK not found. Please install it using 'paxd install com.mralfiem591.paxd-sdk'")
    sys.exit(1)

from package_manager import PackageManager
from gui_components import PackageListFrame, PackageDetailsFrame, QueueFrame
from utils import fetch_search_index, parse_search_index


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
        
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Configure grid weights
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Top frame with apply button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
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
        
        # Queue info label
        self.queue_label = ttk.Label(top_frame, text="Queue: 0 actions")
        self.queue_label.pack(side=tk.LEFT)
        
        # Main content area
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
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
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        
    def load_packages(self):
        """Load packages from search index"""
        def load_in_thread():
            try:
                self.status_var.set("Loading packages...")
                search_index = fetch_search_index()
                self.packages = parse_search_index(search_index)
                
                # Update installed status
                for package in self.packages:
                    package['installed'] = sdk.IsInstalled(package['package_id'])
                
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
        queue_window = QueueWindow(self.root, self.queue, self.package_manager)
        queue_window.start_processing()
        
        # Clear queue after processing starts
        self.queue = []
        self.update_queue_display()
        
        # Refresh packages after processing
        queue_window.window.protocol("WM_DELETE_WINDOW", lambda: [
            queue_window.window.destroy(),
            self.refresh_packages()
        ])
    
    def refresh_packages(self):
        """Refresh package list"""
        self.load_packages()
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)
    
    def run(self):
        """Run the GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


class QueueWindow:
    def __init__(self, parent, queue, package_manager):
        self.queue = queue
        self.package_manager = package_manager
        
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
                        if result.get('success'):
                            self.log(f"✓ Success: {result.get('message', 'Operation completed')}")
                        else:
                            self.log(f"✗ Error: {result.get('message', 'Unknown error')}")
                            
                            # Handle update retry option
                            if action == 'update' and 'already the latest version' in result.get('output', ''):
                                if messagebox.askyesno(
                                    "Force Update", 
                                    f"{package['package_name']} is already up to date. Force update anyway?",
                                    parent=self.window
                                ):
                                    self.log(f"Forcing update for {package['package_name']}...")
                                    force_result = self.package_manager.execute_action(package, 'force_update')
                                    if force_result.get('success'):
                                        self.log(f"✓ Force update successful")
                                    else:
                                        self.log(f"✗ Force update failed: {force_result.get('message')}")
                    
                    except Exception as e:
                        self.log(f"✗ Exception: {str(e)}")
                    
                    self.log("")  # Empty line for readability
                
                self.progress_bar['value'] = len(self.queue)
                self.progress_label.config(text="Processing complete!")
                self.close_button.config(state=tk.NORMAL)
                
            except Exception as e:
                self.log(f"Critical error: {str(e)}")
                self.close_button.config(state=tk.NORMAL)
        
        threading.Thread(target=process, daemon=True).start()


if __name__ == "__main__":
    try:
        app = PaxDGUI()
        app.run()
    except Exception as e:
        print(f"Error starting PaxD GUI: {e}")
        sys.exit(1)