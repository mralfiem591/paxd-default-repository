# IssueDetector: This module is responsible for detecting issues in the PaxD package management system.
# Packages are located in packages/ relative to this file.

import os
import yaml
package_dir = os.path.join(os.path.dirname(__file__), 'packages')

issues = {}
package_names = set()  # Track package names for duplicate detection

# Iterate through each package dir in this dir, and check if it has a package.yaml or paxd.yaml
for package_name in os.listdir(package_dir):
    
    if package_name ==  "metapackages" or not os.path.isdir(os.path.join(package_dir, package_name)):
        continue
    
    package_path = os.path.join(package_dir, package_name)
    package_yaml_path = os.path.join(package_path, 'package.yaml')
    paxd_yaml_path = os.path.join(package_path, 'paxd.yaml')
    
    # Load the package metadata
    metadata = {}
    if os.path.isfile(package_yaml_path):
        with open(package_yaml_path, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f)
    elif os.path.isfile(paxd_yaml_path):
        with open(paxd_yaml_path, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f)
    else:
        print(f"[IssueDetector] Package '{package_name}' is missing package.yaml or paxd.yaml. This package will not be shown as a valid package, and scanning cannot continue.")
        issues[package_name] = ["Missing package.yaml or paxd.yaml"]
        continue
    
    # Check for required fields in metadata
    required_fields = ['name', 'version', 'author', 'description']
    for field in required_fields:
        if field not in metadata:
            print(f"[IssueDetector] Package '{package_name}' is missing required field: '{field}'")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Missing required field: '{field}'")
    
    # Check for license field (recommended)
    if 'license' not in metadata:
        print(f"[IssueDetector] Package '{package_name}' is missing license field")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Missing license field")
    
    # Check version format (should be semantic versioning like 1.0.0)
    version = metadata.get('version', '')
    if version:
        version_parts = version.split('.')
        if len(version_parts) != 3 or not all(part.isdigit() for part in version_parts):
            print(f"[IssueDetector] Package '{package_name}' has invalid version format: '{version}' (should be X.Y.Z)")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Invalid version format: '{version}' (should be X.Y.Z)")
    
    # Check for placeholder or generic values
    author = metadata.get('author', '')
    if author.lower() in ['author', 'your name', 'todo', 'tbd', 'placeholder', '']:
        print(f"[IssueDetector] Package '{package_name}' has placeholder author field: '{author}'")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append(f"Placeholder author field: '{author}'")
    
    description = metadata.get('description', '')
    if len(description) < 10 or description.lower() in ['description', 'todo', 'tbd', 'placeholder']:
        print(f"[IssueDetector] Package '{package_name}' has inadequate description: '{description}'")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Inadequate or placeholder description")
    
    # Check if src directory exists
    src_path = os.path.join(package_path, 'src')
    if not os.path.isdir(src_path):
        print(f"[IssueDetector] Package '{package_name}' is missing 'src' directory")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Missing 'src' directory")
    elif not os.listdir(src_path):
        print(f"[IssueDetector] Package '{package_name}' has empty 'src' directory")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Empty 'src' directory")
    
    # Check if files listed in install->files actually exist
    install_files = metadata.get('install', {}).get('files', [])
    for file_name in install_files:
        file_path = os.path.join(package_path, 'src', file_name)
        if not os.path.exists(file_path):
            print(f"[IssueDetector] Package '{package_name}' lists file '{file_name}' that doesn't exist")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Listed file '{file_name}' doesn't exist in src/")
            
    # Check if package contains its own id as a dependency (id = folder name)
    dependencies = metadata.get('install', {}).get('dependencies', {}).get('paxd', [])
    if package_name in dependencies:
        print(f"[IssueDetector] Package '{package_name}' lists itself as a dependency. This will make the package pretty much uninstallable, as it will infinitely install itself.")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Lists itself as a dependency.")
        
    # Check [install][dependencies][paxd] actually exist in the repository (if that section exists, if it doesnt it's ok)
    paxd_dependencies = metadata.get('install', {}).get('dependencies', {}).get('paxd', [])
    for paxd_dep in paxd_dependencies:
        paxd_dep_path = os.path.join(package_dir, paxd_dep)
        if not os.path.isdir(paxd_dep_path):
            print(f"[IssueDetector] Package '{package_name}' has a PaxD dependency '{paxd_dep}' which does not exist in the packages repository.")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"PaxD dependency '{paxd_dep}' does not exist in repository.")
        
    # Check that [install][main_executable] exists relative to package_dir/src
    main_executable = metadata.get('install', {}).get('main_executable', None)
    if main_executable:
        main_executable_path = os.path.join(package_path, 'src', main_executable)
        if not os.path.isfile(main_executable_path):
            print(f"[IssueDetector] Package '{package_name}' main_executable '{main_executable}' does not exist at expected path: {main_executable_path}")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Mainfile '{main_executable}' does not exist at expected path: {main_executable_path}")
        else:
            # Check if main_executable has appropriate extension
            if not main_executable.endswith(('.py', '.exe', '.bat', '.cmd', '.ps1')):
                print(f"[IssueDetector] Package '{package_name}' main_executable '{main_executable}' has unusual extension")
                if package_name not in issues:
                    issues[package_name] = []
                issues[package_name].append(f"Mainfile '{main_executable}' has unusual extension")
    
    # Check for invalid characters in package name (folder name)
    if not package_name.replace('.', '').replace('-', '').replace('_', '').isalnum():
        print(f"[IssueDetector] Package '{package_name}' contains invalid characters in name")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Package name contains invalid characters")
    
    # Check if command alias is reasonable if main_executable exists
    command_alias = metadata.get('install', {}).get('command_alias', None)
    if main_executable and not command_alias:
        print(f"[IssueDetector] Package '{package_name}' has main_executable but no command_alias")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Has main_executable but missing command_alias")
    elif command_alias and not main_executable:
        print(f"[IssueDetector] Package '{package_name}' has command_alias but no main_executable")
        if package_name not in issues:
            issues[package_name] = []
        issues[package_name].append("Has command_alias but missing main_executable")

# Check for duplicate package names across different directories
for package_name in os.listdir(package_dir):
    if package_name == "metapackages" or not os.path.isdir(os.path.join(package_dir, package_name)):
        continue
    
    package_path = os.path.join(package_dir, package_name)
    package_yaml_path = os.path.join(package_path, 'package.yaml')
    paxd_yaml_path = os.path.join(package_path, 'paxd.yaml')
    
    metadata = {}
    if os.path.isfile(package_yaml_path):
        with open(package_yaml_path, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f)
    elif os.path.isfile(paxd_yaml_path):
        with open(paxd_yaml_path, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f)
    
    if 'name' in metadata:
        pkg_name = metadata['name']
        if pkg_name in package_names:
            print(f"[IssueDetector] Duplicate package name '{pkg_name}' found in package '{package_name}'")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Duplicate package name '{pkg_name}'")
        else:
            package_names.add(pkg_name)
            
if issues:
    print("\n[IssueDetector] Summary of detected issues:")
    for pkg, issue_list in issues.items():
        print(f" - Package '{pkg}':")
        for issue in issue_list:
            print(f"    * {issue}")
else:
    print("[IssueDetector] No issues detected in packages.")

# Generate issue report file
import datetime

report_file = "ISSUE_REPORT.txt"
with open(report_file, 'w', encoding='utf-8') as f:
    f.write("PaxD Package Issue Report\n")
    f.write("=" * 50 + "\n")
    f.write(f"Generated: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    f.write("NOTE: The above time will only change if the report content changes, to avoid unnecessary commits.\n\n")
    
    if issues:
        f.write(f"ISSUES DETECTED ({len(issues)} packages affected):\n")
        f.write("-" * 40 + "\n\n")
        
        for pkg, issue_list in issues.items():
            f.write(f"Package: {pkg}\n")
            for issue in issue_list:
                f.write(f"  - {issue}\n")
            f.write("\n")
            
        f.write(f"\nSUMMARY:\n")
        f.write(f"- Total packages with issues: {len(issues)}\n")
        total_issue_count = sum(len(issue_list) for issue_list in issues.values())
        f.write(f"- Total issues found: {total_issue_count}\n")
        
    else:
        f.write("STATUS: ALL PACKAGES OK\n")
        f.write("No issues detected in any packages.\n")

print(f"[IssueDetector] Report saved to: {report_file}")