#!/usr/bin/env python3
"""
PaxD Package Compiler
Bidirectional converter between user-friendly YAML format and JSONC manifest format.
Usage: python run_pkg.py main.py <input_file> [options]
       
Supports:
- YAML to JSONC conversion (default)
- JSONC/JSON to YAML conversion (auto-detected)
"""

import yaml
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any

def parse_arguments() -> tuple:
    """Parse command line arguments manually (since we're called via run_pkg.py)."""
    
    # run_pkg.py calls us as: python run_pkg.py main.py <actual_args>
    # Note that in the new PaxD update, run_pkg.py adjusts sys.argv to remove itself (basically trimming argv by 1)
    # So sys.argv = [main.py, actual_arg1, actual_arg2, ...]
    # We need to skip the first argument
    args = sys.argv[1:]  # Skip main.py
    
    if not args:
        print("Usage: paxd-compile <input_file> [-o output_file]")
        print("       Supports bidirectional conversion:")
        print("       - YAML to JSONC (default)")
        print("       - JSONC/JSON to YAML (auto-detected)")
        sys.exit(1)
    
    input_file = args[0]
    output_file = None
    
    # Look for -o flag
    for i, arg in enumerate(args):
        if arg == "-o" and i + 1 < len(args):
            output_file = args[i + 1]
            break
    
    return input_file, output_file

def strip_jsonc_comments(jsonc_content: str) -> str:
    """Remove comments from JSONC content to make it valid JSON."""
    # Remove single-line comments (// ...)
    jsonc_content = re.sub(r'//.*?$', '', jsonc_content, flags=re.MULTILINE)
    
    # Remove multi-line comments (/* ... */)
    jsonc_content = re.sub(r'/\*.*?\*/', '', jsonc_content, flags=re.DOTALL)
    
    return jsonc_content

def parse_json_manifest(json_content: str) -> Dict[str, Any]:
    """Parse JSON/JSONC manifest content."""
    # Strip comments if it's JSONC
    clean_json = strip_jsonc_comments(json_content)
    
    try:
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")

def decompile_paxd_manifest(manifest_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert PaxD manifest format back to user-friendly YAML format."""
    
    # Validate manifest structure
    if "pkg_info" not in manifest_data:
        raise ValueError("Invalid manifest: missing 'pkg_info' section")
    
    pkg_info = manifest_data["pkg_info"]
    install_data = manifest_data.get("install", {})
    
    # Required fields mapping
    yaml_data = {
        "name": pkg_info.get("pkg_name", ""),
        "author": pkg_info.get("pkg_author", ""),
        "version": pkg_info.get("pkg_version", ""),
        "description": pkg_info.get("pkg_description", ""),
        "license": pkg_info.get("pkg_license", "")
    }
    
    # Add tags if present
    if "tags" in pkg_info and pkg_info["tags"]:
        yaml_data["tags"] = pkg_info["tags"]
    
    # Build install section
    install_config = {}
    
    # Handle files
    if "include" in install_data:
        install_config["files"] = install_data["include"]
    
    # Handle dependencies - convert back to structured format
    if "depend" in install_data:
        dependencies = {}
        for dep in install_data["depend"]:
            if ":" in dep:
                dep_type, package = dep.split(":", 1)
                if dep_type not in dependencies:
                    dependencies[dep_type] = []
                dependencies[dep_type].append(package)
            else:
                # Handle malformed dependencies
                if "unknown" not in dependencies:
                    dependencies["unknown"] = []
                dependencies["unknown"].append(dep)
        
        if dependencies:
            install_config["dependencies"] = dependencies
    
    # Handle checksums
    if "checksum" in install_data:
        install_config["checksums"] = install_data["checksum"]
    
    # Handle boolean settings
    for yaml_key, manifest_key in [("firstrun", "firstrun"), ("updaterun", "updaterun")]:
        if manifest_key in install_data:
            install_config[yaml_key] = install_data[manifest_key]
    
    # Handle exclude from updates
    if "update-ex" in install_data:
        install_config["exclude_from_updates"] = install_data["update-ex"]
    
    # Handle main executable and alias
    if "mainfile" in install_data:
        install_config["main_executable"] = install_data["mainfile"]
    
    if "alias" in install_data:
        install_config["command_alias"] = install_data["alias"]
    
    # Add install section if not empty
    if install_config:
        yaml_data["install"] = install_config
    
    # Handle uninstall script
    if "uninstall" in manifest_data and "file" in manifest_data["uninstall"]:
        yaml_data["uninstall_script"] = manifest_data["uninstall"]["file"]
    
    return yaml_data

def compile_paxd_manifest(yaml_data: Dict[str, Any]) -> Dict[str, Any]:
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

def format_jsonc(data: Dict[str, Any]) -> str:
    """Format the manifest as JSONC with minimal comments."""
    
    lines = []
    lines.append("// PaxD package - auto-generated from YAML source")
    lines.append("")
    lines.append("{")
    
    # pkg_info section
    lines.append("    \"pkg_info\": {")
    pkg_info = data["pkg_info"]
    
    pkg_info_items = list(pkg_info.items())
    for i, (key, value) in enumerate(pkg_info_items):
        comma = "," if i < len(pkg_info_items) - 1 else ""
        lines.append(f"        \"{key}\": {json.dumps(value)}{comma}")
    
    lines.append("    },")
    
    # install section
    install_comma = "," if "uninstall" in data else ""
    lines.append("    \"install\": {")
    install = data["install"]
    install_items = list(install.items())
    
    for i, (key, value) in enumerate(install_items):
        comma = "," if i < len(install_items) - 1 else ""
        
        if key == "include":
            lines.append("        \"include\": [")
            for j, file in enumerate(value):
                file_comma = "," if j < len(value) - 1 else ""
                lines.append(f"            {json.dumps(file)}{file_comma}")
            lines.append(f"        ]{comma}")
        elif key == "depend":
            lines.append("        \"depend\": [")
            for j, dep in enumerate(value):
                dep_comma = "," if j < len(value) - 1 else ""
                lines.append(f"            {json.dumps(dep)}{dep_comma}")
            lines.append(f"        ]{comma}")
        elif key == "checksum":
            lines.append("        \"checksum\": {")
            checksum_items = list(value.items())
            for j, (file, hash_val) in enumerate(checksum_items):
                checksum_comma = "," if j < len(checksum_items) - 1 else ""
                lines.append(f"            {json.dumps(file)}: {json.dumps(hash_val)}{checksum_comma}")
            lines.append(f"        }}{comma}")
        elif key == "update-ex":
            lines.append("        \"update-ex\": [")
            for j, file in enumerate(value):
                file_comma = "," if j < len(value) - 1 else ""
                lines.append(f"            {json.dumps(file)}{file_comma}")
            lines.append(f"        ]{comma}")
        else:
            lines.append(f"        \"{key}\": {json.dumps(value)}{comma}")
    
    lines.append(f"    }}{install_comma}")
    
    # uninstall section (only if present and not commented out)
    if "uninstall" in data:
        lines.append("    \"uninstall\": {")
        lines.append(f"        \"file\": {json.dumps(data['uninstall']['file'])}")
        lines.append("    }")
    
    lines.append("}")
    
    return "\n".join(lines)

def detect_input_format(file_path: Path) -> str:
    """Detect whether the input file is YAML or JSON/JSONC based on extension and content."""
    
    # Check file extension first
    suffix = file_path.suffix.lower()
    
    # Python files are definitely not supported
    if suffix in ['.py', '.pyc']:
        raise ValueError(f"Python files are not supported: {file_path}")
    
    # Clear YAML extensions
    if suffix in ['.yaml', '.yml']:
        return 'yaml'
    
    # Clear JSON extensions
    if suffix in ['.json', '.jsonc']:
        return 'json'
    
    # For files named "paxd" or other ambiguous cases, check content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Check if it starts with JSON-like structure
        if content.startswith('{') or content.startswith('//'):
            return 'json'
        
        # Otherwise assume YAML
        return 'yaml'
        
    except Exception:
        # If we can't read the file, guess based on name
        if file_path.name == 'paxd':
            return 'json'  # paxd files are usually JSON manifests
        
        return 'yaml'  # Default assumption

def main():
    """Main function - handles bidirectional compilation between YAML and JSONC."""
    try:
        input_file, output_file = parse_arguments()
        
        # Convert to absolute path and resolve any path issues
        input_path = Path(input_file).resolve()
        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found")
            sys.exit(1)
        
        # Detect input format
        input_format = detect_input_format(input_path)
        print(f"Detected input format: {input_format.upper()}")
        
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        if not file_content.strip():
            print("Error: Input file appears to be empty")
            sys.exit(1)
        
        if input_format == 'yaml':
            # YAML to JSONC conversion
            print("Converting YAML to JSONC...")
            
            # Parse YAML
            yaml_data = yaml.safe_load(file_content)
            if not yaml_data:
                print("Error: YAML file appears to be empty or invalid")
                sys.exit(1)
            
            # Compile to manifest format
            manifest = compile_paxd_manifest(yaml_data)
            
            # Format as JSONC
            output_content = format_jsonc(manifest)
            
            # Determine output path
            if output_file:
                output_path = Path(output_file)
            else:
                # Output as the file name "paxd": thats what the package handler looks for
                output_path = input_path.parent / "paxd"
            
            # Show package info
            print(f"[OK] Package: {manifest['pkg_info']['pkg_name']} v{manifest['pkg_info']['pkg_version']}")
            
            # Show some stats
            file_count = len(manifest['install'].get('include', []))
            dep_count = len(manifest['install'].get('depend', []))
            print(f"[OK] Files to install: {file_count}")
            print(f"[OK] Dependencies: {dep_count}")
            
        else:
            # JSON/JSONC to YAML conversion
            print("Converting JSONC/JSON to YAML...")
            
            # Parse JSON/JSONC
            manifest = parse_json_manifest(file_content)
            
            # Decompile to YAML format
            yaml_data = decompile_paxd_manifest(manifest)
            
            # Format as YAML
            output_content = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False, indent=2)
            
            # Add header comment
            output_content = f"# PaxD package configuration - converted from manifest\n# Original file: {input_path.name}\n\n{output_content}"
            
            # Determine output path
            if output_file:
                output_path = Path(output_file)
            else:
                # Output as .yaml file
                if input_path.name == 'paxd':
                    output_path = input_path.parent / "package.yaml"
                else:
                    output_path = input_path.with_suffix('.yaml')
            
            # Show package info
            print(f"[OK] Package: {yaml_data.get('name', 'Unknown')} v{yaml_data.get('version', 'Unknown')}")
            
            # Show some stats
            install_config = yaml_data.get('install', {})
            file_count = len(install_config.get('files', []))
            deps = install_config.get('dependencies', {})
            dep_count = sum(len(packages) for packages in deps.values()) if isinstance(deps, dict) else 0
            print(f"[OK] Files to install: {file_count}")
            print(f"[OK] Dependencies: {dep_count}")
        
        # Write output
        print(f"Writing output to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"[OK] Successfully converted '{input_path}' to '{output_path}'")
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()