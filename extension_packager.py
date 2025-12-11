#!/usr/bin/env python3
"""
PaxD Extension Packager
Converts a folder containing extension files into a PaxD-compatible zip extension.
"""

import sys
import zipfile
import argparse
from pathlib import Path


def validate_extension_folder(folder_path: str) -> tuple[bool, str, dict]:
    """
    Validate that a folder contains a valid PaxD extension.
    Returns (is_valid, error_message, extension_info)
    """
    folder_path_obj = Path(folder_path)
    
    if not folder_path_obj.exists():
        return False, f"Folder does not exist: {folder_path_obj}", {}
    
    if not folder_path_obj.is_dir():
        return False, f"Path is not a directory: {folder_path_obj}", {}
    
    # Check for required extension.py file
    extension_py = folder_path_obj / "extension.py"
    if not extension_py.exists():
        return False, "Missing required 'extension.py' file", {}
    
    # Try to load and validate the extension
    try:
        # Read the extension file
        with open(extension_py, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a temporary namespace to execute the extension
        namespace = {}
        exec(content, namespace)
        
        # Check for required components
        if 'on_trigger' not in namespace:
            return False, "Extension missing required 'on_trigger' function", {}
        
        if not callable(namespace['on_trigger']):
            return False, "'on_trigger' must be a callable function", {}
        
        if 'EXTENSION_INFO' not in namespace:
            return False, "Extension missing required 'EXTENSION_INFO' dictionary", {}
        
        extension_info = namespace['EXTENSION_INFO']
        
        if not isinstance(extension_info, dict):
            return False, "'EXTENSION_INFO' must be a dictionary", {}
        
        # Validate required fields in EXTENSION_INFO
        required_fields = ['name', 'version', 'description', 'author']
        for field in required_fields:
            if field not in extension_info:
                return False, f"EXTENSION_INFO missing required field: {field}", {}
            if not isinstance(extension_info[field], str) or not extension_info[field].strip():
                return False, f"EXTENSION_INFO field '{field}' must be a non-empty string", {}
        
        # Validate triggers field if present
        if 'triggers' in extension_info:
            triggers = extension_info['triggers']
            if not isinstance(triggers, list):
                return False, "'triggers' in EXTENSION_INFO must be a list", {}
            
            valid_triggers = [
                'pre_install', 'post_install', 'pre_update', 'post_update',
                'pre_uninstall', 'post_uninstall', 'pre_search', 'post_search',
                'listall.start', 'listall.end'
            ]
            
            for trigger in triggers:
                if not isinstance(trigger, str):
                    return False, f"All triggers must be strings, got: {type(trigger)}", {}
                if trigger not in valid_triggers:
                    print(f"Warning: Unknown trigger '{trigger}' (will still be registered)")
        
        return True, "", extension_info
        
    except SyntaxError as e:
        return False, f"Syntax error in extension.py: {e}", {}
    except Exception as e:
        return False, f"Error loading extension.py: {e}", {}


from typing import Optional

def create_extension_zip(folder_path: str, output_path: Optional[str] = None) -> bool:
    """
    Create a PaxD extension zip file from a folder.
    """
    folder_path_obj = Path(folder_path)
    
    # Validate the extension folder
    is_valid, error_msg, extension_info = validate_extension_folder(folder_path)
    if not is_valid:
        print(f"❌ Validation failed: {error_msg}")
        return False
    
    # Determine output path
    if output_path is None:
        extension_name = extension_info.get('name', folder_path_obj.name)
        # Sanitize extension name for filename
        safe_name = "".join(c for c in extension_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        output_path_obj = folder_path_obj.parent / f"{safe_name}.zip"
    else:
        output_path_obj = Path(output_path)
    
    # Create the zip file
    try:
        with zipfile.ZipFile(output_path_obj, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from the folder
            for file_path in folder_path_obj.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path within the extension
                    relative_path = file_path.relative_to(folder_path_obj)
                    zipf.write(file_path, relative_path)
                    print(f"  Added: {relative_path}")
        
        print(f"✅ Successfully created extension: {output_path_obj}")
        print(f"📦 Extension: {extension_info['name']} v{extension_info['version']}")
        print(f"👤 Author: {extension_info['author']}")
        print(f"📝 Description: {extension_info['description']}")
        
        if 'triggers' in extension_info:
            print(f"🔗 Triggers: {', '.join(extension_info['triggers'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create zip file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Package a folder into a PaxD extension zip file",
        epilog="""
Examples:
  python extension_packager.py my_extension_folder
  python extension_packager.py my_extension_folder -o my_extension.zip
  python extension_packager.py ./example_extension --output ~/Desktop/my_extension.zip
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the folder containing the extension files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output zip file path (defaults to extension_name.zip in parent directory)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate the extension, do not create zip file'
    )
    
    args = parser.parse_args()
    
    print("🔧 PaxD Extension Packager")
    print("=" * 40)
    
    # Validate the extension
    print(f"📁 Validating extension folder: {args.folder_path}")
    is_valid, error_msg, extension_info = validate_extension_folder(args.folder_path)
    
    if not is_valid:
        print(f"❌ Validation failed: {error_msg}")
        sys.exit(1)
    
    print("✅ Extension validation passed!")
    print(f"📦 Extension: {extension_info['name']} v{extension_info['version']}")
    
    if args.validate_only:
        print("🔍 Validation-only mode - not creating zip file")
        return
    
    # Create the zip file
    print(f"\n📦 Creating extension zip file...")
    success = create_extension_zip(args.folder_path, args.output)
    
    if success:
        print("\n🎉 Extension packaged successfully!")
        print("\n💡 To install this extension in PaxD:")
        output_file = args.output or f"{extension_info['name']}.zip"
        print(f"   paxd extension install \"{output_file}\"")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()