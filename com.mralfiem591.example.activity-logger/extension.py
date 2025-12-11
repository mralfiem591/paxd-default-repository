#!/usr/bin/env python3
"""
PaxD Activity Logger Extension

This extension demonstrates the core concepts of PaxD extensions by:
- Logging all PaxD operations to a file
- Showing package installation statistics
- Providing helpful notifications

Author: PaxD Extension Developer
Version: 1.0.0
"""

import os
import datetime
import json


def on_trigger(trigger_name, *args, **kwargs):
    """
    Handle extension triggers from PaxD.
    
    This function is called whenever a registered trigger is fired.
    
    Args:
        trigger_name (str): The name of the trigger being fired
        *args: Positional arguments passed with the trigger
        **kwargs: Keyword arguments passed with the trigger
    """
    
    # Get the PaxD data directory
    paxd_data_dir = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
    log_dir = os.path.join(paxd_data_dir, "extensions", "activity_logger")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path
    log_file = os.path.join(log_dir, "activity.log")
    stats_file = os.path.join(log_dir, "stats.json")
    
    # Prepare log entry
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "trigger": trigger_name,
        "args": list(args),
        "kwargs": dict(kwargs)
    }
    
    # Write to activity log
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"[Activity Logger] Failed to write log: {e}")
        return
    
    # Handle specific triggers with user-friendly messages
    try:
        if trigger_name == "pre_install":
            package = kwargs.get('package', 'unknown')
            user_requested = kwargs.get('user_requested', False)
            action = "Installing" if user_requested else "Installing dependency"
            print(f"🔄 [Activity Logger] {action}: {package}")
            
        elif trigger_name == "post_install":
            package = kwargs.get('package', 'unknown')
            version = kwargs.get('version', 'unknown')
            user_requested = kwargs.get('user_requested', False)
            
            if user_requested:
                print(f"✅ [Activity Logger] Successfully installed {package} v{version}")
                update_stats(stats_file, "installations", package)
            else:
                print(f"📦 [Activity Logger] Dependency {package} installed")
            
        elif trigger_name == "pre_uninstall":
            package = kwargs.get('package', 'unknown')
            print(f"🗑️ [Activity Logger] Uninstalling: {package}")
            
        elif trigger_name == "post_uninstall":
            package = kwargs.get('package', 'unknown')
            print(f"🧹 [Activity Logger] Cleanup completed for {package}")
            update_stats(stats_file, "uninstalls", package)
            
        elif trigger_name == "pre_update":
            package = kwargs.get('package', 'unknown')
            print(f"⬆️ [Activity Logger] Updating: {package}")
            
        elif trigger_name == "post_update":
            package = kwargs.get('package', 'unknown')
            version = kwargs.get('version', 'unknown')
            files = kwargs.get('files', [])
            print(f"🔄 [Activity Logger] Updated {package} to v{version} ({len(files)} files)")
            update_stats(stats_file, "updates", package)
            
        elif trigger_name == "pre_search":
            term = kwargs.get('term', 'unknown')
            print(f"🔍 [Activity Logger] Searching for: {term}")
            
        elif trigger_name == "post_search":
            term = kwargs.get('term', 'unknown')
            results = kwargs.get('results', [])
            print(f"📋 [Activity Logger] Found {len(results)} results for '{term}'")
            
        elif trigger_name == "listall.start":
            print(f"📦 [Activity Logger] Listing installed packages...")
            
        elif trigger_name == "listall.end":
            packages = kwargs.get('packages', [])
            user_packages = [pkg for pkg, ver, user in packages if user]
            dep_packages = [pkg for pkg, ver, user in packages if not user]
            print(f"📊 [Activity Logger] Found {len(user_packages)} user packages, {len(dep_packages)} dependencies")
            
    except Exception as e:
        print(f"[Activity Logger] Error handling trigger {trigger_name}: {e}")


def update_stats(stats_file, action_type, package):
    """Update the statistics file with package action counts."""
    try:
        # Load existing stats
        stats = {}
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
        
        # Initialize structure if needed
        if action_type not in stats:
            stats[action_type] = {}
        
        # Update count for this package
        if package in stats[action_type]:
            stats[action_type][package] += 1
        else:
            stats[action_type][package] = 1
        
        # Update last action timestamp
        stats['last_updated'] = datetime.datetime.now().isoformat()
        
        # Save updated stats
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
            
    except Exception as e:
        print(f"[Activity Logger] Failed to update stats: {e}")


# Extension metadata - REQUIRED for all PaxD extensions
EXTENSION_INFO = {
    "name": "com.mralfiem591.example.activity-logger",
    "version": "1.0.0",
    "description": "Logs all PaxD operations and provides activity statistics. Used as an example extension.",
    "author": "mralfiem591",
    "triggers": [
        "pre_install",
        "post_install", 
        "pre_update",
        "post_update",
        "pre_uninstall", 
        "post_uninstall",
        "pre_search",
        "post_search",
        "listall.start",
        "listall.end"
    ],
    "source_url": "https://github.com/mralfiem591/paxd/raw/refs/heads/extensions/[ZIP_NAME]"
}