# IssueDetector: This module is responsible for detecting issues in the PaxD package management system.
# Packages are located in packages/ relative to this file.

import os
import yaml
package_dir = os.path.join(os.path.dirname(__file__), 'packages')

issues = {}

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
            
    # Check if package contains its own id as a dependency (id = folder name)
    # Dependencies are at [install][dependencies]
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
        
    # Check that [install][mainfile] exists relative to package_dir/src
    mainfile = metadata.get('install', {}).get('mainfile', None)
    if mainfile:
        mainfile_path = os.path.join(package_path, 'src', mainfile)
        if not os.path.isfile(mainfile_path):
            print(f"[IssueDetector] Package '{package_name}' mainfile '{mainfile}' does not exist at expected path: {mainfile_path}")
            if package_name not in issues:
                issues[package_name] = []
            issues[package_name].append(f"Mainfile '{mainfile}' does not exist at expected path: {mainfile_path}")
            
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
    f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
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