#!/usr/bin/env python3
"""
PaxD SDK Examples
This file shows examples of using the PaxD SDK for package management operations.
"""

import paxd_sdk as sdk # type: ignore # Calls to the SDK may raise issues in vscode parsers, but it is available and works at runtime. If a function from the SDK is called and doesnt exist, a SDKException is raised (note, its not recommended to catch this)

def example_basic_usage():
    """Basic PaxD SDK usage examples"""
    # Get repository URL
    repo_url = sdk.GetRepositoryUrl()
    print(f"Repository URL: {repo_url}")
    
    # Get search index URL
    searchindex_url = f"{repo_url}/searchindex.csv"
    print(f"Search Index URL: {searchindex_url}")
    
    # Check if a package is installed
    is_installed = lambda package_name: sdk.IsInstalled(package_name)
    
    # Example: Check if PaxD itself is installed
    paxd_installed = is_installed("com.mralfiem591.paxd")
    print(f"PaxD installed: {paxd_installed}")

def example_package_checks():
    """Examples of checking package installation status"""
    packages_to_check = [
        "com.mralfiem591.paxd",
        "com.mralfiem591.paxd-sdk",
        "com.mralfiem591.paxd-imageview",
        "com.mralfiem591.test"
    ]
    
    print("Package Installation Status:")
    for package_id in packages_to_check:
        try:
            installed = sdk.IsInstalled(package_id)
            status = "✓ Installed" if installed else "✗ Not installed"
            print(f"  {package_id}: {status}")
        except Exception as e:
            print(f"  {package_id}: Error checking - {e}")

if __name__ == "__main__":
    print("PaxD SDK Examples")
    print("=" * 50)
    
    try:
        example_basic_usage()
        print()
        example_package_checks()
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure PaxD SDK is installed: paxd install com.mralfiem591.paxd-sdk")