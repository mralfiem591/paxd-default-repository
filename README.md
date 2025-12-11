# PaxD Extensions System

PaxD supports a powerful extension system that allows developers to create custom plugins that can hook into various operations throughout the package manager's lifecycle. Extensions are packaged as zip files and can be easily installed, updated, and managed.

## Table of Contents

1. [Overview](#overview)
2. [Extension Structure](#extension-structure)
3. [Available Triggers](#available-triggers)
4. [Creating an Extension](#creating-an-extension)
5. [Extension Packaging](#extension-packaging)
6. [Managing Extensions](#managing-extensions)
7. [Extension Examples](#extension-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The PaxD extension system is built around a trigger-based architecture. Extensions register for specific triggers that fire during various PaxD operations. When a trigger fires, all registered extension callbacks are executed with relevant context data.

### Key Features

- **Event-driven architecture**: Extensions respond to triggers throughout PaxD operations
- **Safe execution environment**: Extensions run in isolated namespaces with limited module access
- **Easy installation**: Extensions are distributed as zip files for simple installation
- **Automatic updates**: Extensions can define source URLs for automatic updates
- **Rich context data**: Triggers provide detailed information about the current operation

## Extension Structure

Every PaxD extension must follow this file structure:

```
your-extension/
├── extension.py          # Main extension file (required)
├── README.md            # Documentation (recommended)
└── other-files/         # Additional resources (optional)
    ├── config.json
    ├── templates/
    └── assets/
```

### Required Files

#### `extension.py`

This is the main extension file that must contain:

1. **`EXTENSION_INFO`** dictionary with metadata
2. **`on_trigger(trigger_name, *args, **kwargs)`** function to handle trigger events

```python
#!/usr/bin/env python3
"""
Example PaxD Extension
"""

import os
import datetime

def on_trigger(trigger_name, *args, **kwargs):
    """
    Handle extension triggers from PaxD.
    
    Args:
        trigger_name (str): The name of the trigger being fired
        *args: Positional arguments passed with the trigger
        **kwargs: Keyword arguments passed with the trigger
    """
    if trigger_name == "post_install":
        package = kwargs.get("package", "unknown")
        print(f"📦 Extension: Package {package} was just installed!")
    
    elif trigger_name == "pre_search":
        term = kwargs.get("term", "unknown")
        print(f"🔍 Extension: About to search for '{term}'...")

# Extension metadata - REQUIRED for all PaxD extensions
EXTENSION_INFO = {
    "name": "example-extension",
    "version": "1.0.0", 
    "description": "An example PaxD extension",
    "author": "Your Name",
    "source_url": "https://example.com/extensions/example-extension.zip",  # Optional
    "triggers": [
        "post_install",
        "pre_search"
    ]
}
```

### Extension Metadata

The `EXTENSION_INFO` dictionary must contain:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✅ | string | Extension identifier (use lowercase with hyphens) |
| `version` | ✅ | string | Version string (e.g., "1.0.0") |
| `description` | ✅ | string | Brief description of the extension |
| `author` | ✅ | string | Extension author name |
| `triggers` | ✅ | list | List of trigger names to register for |
| `source_url` | ❌ | string | URL to zip file for automatic updates |

## Available Triggers

PaxD provides numerous trigger points throughout its operation lifecycle:

### Package Management Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_install` | Before package installation begins | `package`, `user_requested` |
| `post_install` | After successful package installation | `package`, `user_requested`, `version` |
| `pre_update` | Before package update begins | `package`, `force` |
| `post_update` | After successful package update | `package`, `version`, `files` |
| `pre_uninstall` | Before package removal begins | `package` |
| `post_uninstall` | After successful package removal | `package` |

### Dependency Management Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_dependency_check` | Before resolving dependencies | `package`, `dependencies` |
| `post_dependency_check` | After dependency resolution | `package`, `dependencies` |

### File Operation Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_file_download` | Before downloading package files | `package`, `files` |
| `post_file_download` | After downloading package files | `package`, `files`, `downloaded_files` |
| `checksum_failed` | When file checksum verification fails | `package`, `file`, `attempt`, `max_attempts` |

### Search and Information Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_search` | Before package search begins | `term` |
| `post_search` | After search results are found | `term`, `results` |
| `pre_info` | Before getting package information | `package`, `fullsize` |
| `post_info` | After package information retrieved | `package`, `fullsize`, `found` |

### Repository and System Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_repo_info` | Before showing repository info | |
| `post_repo_info` | After repository info displayed | `repo_url` |
| `pre_update_all` | Before bulk package update | |
| `post_update_all` | After bulk package update | `successful_updates`, `failed_updates`, `updated_packages`, `failed_packages` |

### List Operation Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `listall.start` | Before listing packages begins | |
| `listall.end` | After package listing completes | `packages` |

### Protocol and URL Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `pre_url_handle` | Before handling paxd:// URL | `url` |
| `post_url_handle` | After URL handling complete | `url`, `success` |
| `pre_protocol_register` | Before registering paxd:// protocol | |
| `post_protocol_register` | After protocol registration | `success` |
| `pre_protocol_check` | Before checking protocol status | |
| `post_protocol_check` | After protocol status check | `registered` |

### Application Lifecycle Triggers

| Trigger | When Fired | Context Data |
|---------|------------|--------------|
| `app_start` | When PaxD application starts | `command`, `verbose` |
| `app_exit` | When PaxD application exits normally | `command`, `success` |
| `app_cancelled` | When operation is cancelled by user | `command` |

## Creating an Extension

### Step 1: Create Extension Directory

```bash
mkdir my-awesome-extension
cd my-awesome-extension
```

### Step 2: Write Extension Code

Create `extension.py`:

```python
#!/usr/bin/env python3
"""
My Awesome PaxD Extension

This extension provides notifications and logging for PaxD operations.
"""

import os
import datetime
import json

def on_trigger(trigger_name, *args, **kwargs):
    """Handle all PaxD triggers"""
    
    # Get extension data directory
    data_dir = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD", "extensions", "my-awesome-extension")
    os.makedirs(data_dir, exist_ok=True)
    
    # Log all activities
    log_file = os.path.join(data_dir, "activity.log")
    timestamp = datetime.datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "trigger": trigger_name,
        "args": list(args),
        "kwargs": dict(kwargs)
    }
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + 'n')
    except Exception as e:
        print(f"Extension logging error: {e}")
    
    # Handle specific triggers
    if trigger_name == "post_install":
        package = kwargs.get("package", "unknown")
        print(f"🎉 Extension: Successfully installed {package}!")
    
    elif trigger_name == "checksum_failed":
        package = kwargs.get("package", "unknown")
        attempt = kwargs.get("attempt", 0)
        print(f"⚠️ Extension: Checksum failed for {package} (attempt {attempt})")

# Extension metadata
EXTENSION_INFO = {
    "name": "my-awesome-extension",
    "version": "1.0.0",
    "description": "Provides notifications and activity logging for PaxD operations",
    "author": "Your Name",
    "source_url": "https://github.com/yourname/my-awesome-extension/releases/latest/download/my-awesome-extension.zip",
    "triggers": [
        "post_install",
        "post_uninstall",
        "post_search",
        "checksum_failed",
        "app_start",
        "app_exit"
    ]
}
```

### Step 3: Add Documentation

Create `README.md`:

```markdown
# My Awesome Extension

This extension enhances PaxD with notifications and activity logging.

## Features

- Logs all PaxD operations to a file
- Provides user-friendly notifications
- Tracks package installation statistics

## Installation

Download the latest release and install:

```bash
paxd extension install my-awesome-extension.zip
```

## Configuration

The extension stores logs in:
`%LOCALAPPDATA%PaxDextensionsmy-awesome-extensionactivity.log`
```

## Extension Packaging

PaxD provides the `extension_packager.py` tool to package extensions into zip files:

### Basic Usage

```bash
# Package extension from folder
python extension_packager.py my-awesome-extension

# Specify custom output location
python extension_packager.py my-awesome-extension -o ~/Desktop/my-extension.zip

# Validate extension without packaging
python extension_packager.py my-awesome-extension --validate-only
```

### Placeholders in Files

The packager supports placeholders that are replaced during packaging:

- `[ZIP_NAME]` - Replaced with the zip file name (without .zip extension)

Example usage in README.md:
```markdown
To install this extension:
```bash
paxd extension install [ZIP_NAME].zip
```
```

### Supported File Types

The packager processes placeholders in these text file types:
- `.py` `.txt` `.md` `.json` `.yaml` `.yml`
- `.xml` `.html` `.js` `.css` `.ini` `.cfg` `.conf`

Binary files are included without modification.

## Managing Extensions

### Installation

```bash
# Install from zip file
paxd extension install my-extension.zip

# Install from URL (if supported by extension)
paxd extension install https://example.com/extension.zip
```

### Updating

```bash
# Update from source URL (if defined in extension)
paxd extension update my-extension

# Update from specific zip file
paxd extension update my-extension --zip-path new-version.zip
```

### Listing

```bash
# List all installed extensions
paxd extension list
```

### Removal

```bash
# Uninstall extension
paxd extension uninstall my-extension
```

## Extension Examples

### 1. Simple Activity Logger

```python
def on_trigger(trigger_name, *args, **kwargs):
    if trigger_name == "post_install":
        package = kwargs.get("package", "unknown")
        print(f"📦 Installed: {package}")

EXTENSION_INFO = {
    "name": "activity-logger",
    "version": "1.0.0",
    "description": "Logs package activities", 
    "author": "PaxD Team",
    "triggers": ["post_install", "post_uninstall"]
}
```

### 2. Package Statistics Tracker

```python
import json
import os

def on_trigger(trigger_name, *args, **kwargs):
    stats_file = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD", "extensions", "stats", "package_stats.json")
    os.makedirs(os.path.dirname(stats_file), exist_ok=True)
    
    # Load existing stats
    try:
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {"installs": 0, "updates": 0, "uninstalls": 0}
    
    # Update stats based on trigger
    if trigger_name == "post_install":
        stats["installs"] += 1
    elif trigger_name == "post_update":
        stats["updates"] += 1
    elif trigger_name == "post_uninstall":
        stats["uninstalls"] += 1
    
    # Save updated stats
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    if trigger_name == "app_exit":
        print(f"📊 Session stats: {stats['installs']} installs, {stats['updates']} updates, {stats['uninstalls']} uninstalls")

EXTENSION_INFO = {
    "name": "package-stats",
    "version": "1.0.0", 
    "description": "Track package management statistics",
    "author": "Community",
    "triggers": ["post_install", "post_update", "post_uninstall", "app_exit"]
}
```

### 3. Notification Extension

```python
def on_trigger(trigger_name, *args, **kwargs):
    if trigger_name == "post_install":
        package = kwargs.get("package", "unknown")
        version = kwargs.get("version", "unknown")
        # Show system notification (Windows)
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            toaster.show_toast("PaxD", f"Successfully installed {package} v{version}", duration=3)
        except ImportError:
            print(f"✅ Notification: {package} v{version} installed!")
    
    elif trigger_name == "checksum_failed":
        package = kwargs.get("package", "unknown")
        attempt = kwargs.get("attempt", 0)
        print(f"❌ Warning: Checksum verification failed for {package} (attempt {attempt})")

EXTENSION_INFO = {
    "name": "Notifications",
    "version": "1.0.0",
    "description": "Shows system notifications for PaxD operations",
    "author": "Community", 
    "triggers": ["post_install", "post_update", "checksum_failed", "app_cancelled"]
}
```

## Best Practices

### Extension Development

1. **Keep it Simple**: Extensions should be focused on specific functionality
2. **Handle Errors Gracefully**: Always wrap risky operations in try-catch blocks
3. **Respect User Privacy**: Only collect necessary data and store it securely
4. **Use Descriptive Names**: Extension names should clearly indicate their purpose
5. **Version Appropriately**: Use semantic versioning (major.minor.patch)

### Performance Considerations

1. **Minimal Processing**: Keep trigger handlers lightweight and fast
2. **Avoid Blocking Operations**: Don't perform long-running tasks in trigger handlers
3. **Cache When Possible**: Store frequently accessed data to avoid repeated calculations
4. **Cleanup Resources**: Properly close files and release resources

### Security Guidelines

1. **Limited Module Access**: Extensions run in a restricted namespace
2. **Validate Inputs**: Always validate data received through triggers
3. **Safe File Operations**: Use absolute paths and validate file access
4. **No Network Access**: Extensions should not make unauthorized network requests

### Code Organization

```python
#!/usr/bin/env python3
"""
Extension Template

Always include a clear docstring describing your extension's purpose.
"""

# Standard library imports only (no external dependencies)
import os
import json
import datetime

def on_trigger(trigger_name, *args, **kwargs):
    """
    Main trigger handler.
    
    Keep this function clean and delegate to helper functions for complex logic.
    """
    try:
        if trigger_name == "post_install":
            handle_install(kwargs)
        elif trigger_name == "pre_search":
            handle_search(kwargs)
        # Add more trigger handlers as needed
    except Exception as e:
        print(f"Extension error in {trigger_name}: {e}")

def handle_install(context):
    """Handle post-install trigger"""
    package = context.get("package", "unknown")
    # Implementation here

def handle_search(context):
    """Handle pre-search trigger"""
    term = context.get("term", "")
    # Implementation here

# Always place EXTENSION_INFO at the end
EXTENSION_INFO = {
    "name": "template-extension",
    "version": "1.0.0",
    "description": "Template for creating PaxD extensions",
    "author": "Your Name",
    "triggers": [
        "post_install",
        "pre_search"
    ]
}
```

## Troubleshooting

### Common Issues

#### Extension Not Loading

**Symptoms**: Extension doesn't appear in `paxd extension list` or triggers don't fire

**Solutions**:
1. Check extension.py syntax with `python -m py_compile extension.py`
2. Verify EXTENSION_INFO contains all required fields
3. Ensure on_trigger function is defined and callable
4. Check PaxD logs with `paxd --verbose` for error messages

#### Trigger Not Firing

**Symptoms**: Extension loads but on_trigger isn't called for expected operations

**Solutions**:
1. Verify trigger name is spelled correctly in EXTENSION_INFO['triggers']
2. Check if trigger is supported (see Available Triggers section)
3. Use `paxd --verbose` to see trigger execution logs
4. Test with a simple print statement in on_trigger

#### Permission Errors

**Symptoms**: Extension can't write files or access directories

**Solutions**:
1. Use `os.path.expandvars(r"%LOCALAPPDATA%")` for user data directory
2. Create directories with `os.makedirs(path, exist_ok=True)`
3. Handle permission errors gracefully with try-except blocks
4. Don't write to PaxD installation directory

#### Extension Update Fails

**Symptoms**: `paxd extension update` command fails

**Solutions**:
1. Verify source_url is accessible and returns valid zip file
2. Check network connectivity and firewall settings
3. Manually download and update with `--zip-path` option
4. Ensure new version has valid extension structure

### Debug Mode

Enable verbose logging to see detailed extension activity:

```bash
paxd --verbose install package-name
```

This shows:
- Extension loading process
- Trigger execution details  
- Extension callback failures
- Performance timing information

### Getting Help

1. **Documentation**: Check this file and extension examples
2. **Community**: Join PaxD discussions for extension development help
3. **Issues**: Report bugs in the PaxD repository
4. **Examples**: Study existing extensions for reference implementations

## Conclusion

The PaxD extension system provides powerful hooks throughout the package management lifecycle. Extensions can enhance user experience, provide custom functionality, and integrate PaxD with other tools and systems.

Start with simple extensions focusing on specific triggers, then gradually expand functionality as needed. Follow best practices for security, performance, and user experience to create valuable extensions for the PaxD community.

Happy extending! 🚀