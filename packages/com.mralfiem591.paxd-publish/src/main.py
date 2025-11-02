#!/usr/bin/env python3
"""
PaxD Package Publisher

This tool validates and publishes PaxD packages to the repository via GitHub Pull Request.
"""

import os
import sys
import json
import yaml
import shutil
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import requests
    from github import Github, Auth
    import git
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install required packages:")
    print("pip install requests PyGithub gitpython pyyaml")
    sys.exit(1)


class PaxDPackagePublisher:
    def __init__(self, github_token: str, repo_owner: str = "mralfiem591", repo_name: str = "paxd"):
        """Initialize the package publisher."""
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        
        # Use the new authentication method to avoid deprecation warning
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")

    def validate_package_structure(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate the local package structure.
        
        Returns:
            Dict containing validation results and package metadata
        """
        print("🔍 Validating package structure...")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'package_info': {}
        }
        
        # Check for manifest file (package.yaml or paxd.yaml)
        manifest_file = None
        for filename in ['package.yaml', 'paxd.yaml']:
            manifest_path = package_dir / filename
            if manifest_path.exists():
                manifest_file = manifest_path
                break
        
        if not manifest_file:
            results['errors'].append("No package manifest found (package.yaml or paxd.yaml)")
            results['valid'] = False
            return results
        
        # Parse manifest
        try:
            with open(manifest_file, 'r', encoding='utf-8', errors='replace') as f:
                manifest = yaml.safe_load(f)
            
            results['package_info'] = manifest
            print(f"  ✅ Found manifest: {manifest_file.name}")
            
        except yaml.YAMLError as e:
            results['errors'].append(f"Invalid YAML in manifest: {e}")
            results['valid'] = False
            return results
        except UnicodeDecodeError as e:
            results['errors'].append(f"Manifest file contains invalid characters: {e}")
            results['valid'] = False
            return results
        
        # Validate required manifest fields
        required_fields = ['name', 'author', 'version', 'description']
        for field in required_fields:
            if field not in manifest:
                results['errors'].append(f"Missing required field '{field}' in manifest")
                results['valid'] = False
        
        # Check for src/ directory
        src_dir = package_dir / 'src'
        if not src_dir.exists() or not src_dir.is_dir():
            results['errors'].append("Missing src/ directory")
            results['valid'] = False
        else:
            print(f"  ✅ Found src/ directory")
            
            # Check if src/ has any files
            src_files = list(src_dir.glob('*'))
            if not src_files:
                results['warnings'].append("src/ directory is empty")
            else:
                print(f"  📁 Found {len(src_files)} files in src/")
        
        # Check for paxd executable (optional)
        paxd_file = package_dir / 'paxd'
        if paxd_file.exists():
            print(f"  ✅ Found paxd executable")
        
        # Validate package name format
        author = manifest.get('author', '')
        if not author:
            results['errors'].append("Package author is required but not specified in manifest")
            results['valid'] = False
            return results
            
        package_name = manifest.get('name', '')
        if not package_name:
            results['errors'].append("Package name is required but not specified in manifest")
            results['valid'] = False
            return results
            
        # Generate package ID - use author as publisher
        package_id = f"com.{author}.{package_name.lower().replace(' ', '-')}"
        
        if package_dir.name != package_id:
            results['warnings'].append(f"Directory name '{package_dir.name}' doesn't match expected '{package_id}'")
        
        results['package_info']['package_id'] = package_id
        
        return results

    def check_file_encodings(self, package_dir: Path) -> List[str]:
        """
        Check all files in the package directory for encoding issues.
        
        Returns:
            List of files with encoding problems
        """
        problematic_files = []
        
        def check_file(file_path: Path):
            """Check a single file for encoding issues."""
            try:
                # Try to read as text first
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError:
                # Check if it's a binary file or just bad encoding
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        # Try to decode as utf-8
                        content.decode('utf-8')
                except UnicodeDecodeError:
                    problematic_files.append(str(file_path.relative_to(package_dir)))
            except Exception:
                # Skip files we can't read for other reasons
                pass
        
        # Check all files recursively
        for item in package_dir.rglob('*'):
            if item.is_file() and not item.name.startswith('.'):
                check_file(item)
        
        return problematic_files

    def create_package_structure(self, package_dir: Path, target_dir: Path, package_info: Dict[str, Any]) -> bool:
        """
        Create the proper package structure in the target directory.
        
        Args:
            package_dir: Source package directory
            target_dir: Target directory for the package
            package_info: Package metadata from manifest
            
        Returns:
            True if successful, False otherwise
        """
        print(f"📦 Creating package structure...")
        
        try:
            package_id = package_info['package_id']
            target_package_dir = target_dir / "packages" / package_id
            
            # Create target directory
            target_package_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files from source to target
            for item in package_dir.iterdir():
                if item.name.startswith('.'):
                    continue
                    
                target_item = target_package_dir / item.name
                
                try:
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                except (UnicodeDecodeError, UnicodeError) as e:
                    print(f"  ⚠️  Warning: Skipping file with encoding issues: {item.name} ({e})")
                    continue
            
            print(f"  ✅ Package structure created at: packages/{package_id}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error creating package structure: {e}")
            return False

    def create_pull_request(self, package_info: Dict[str, Any], temp_dir: Path, custom_message: Optional[str] = None) -> Optional[str]:
        """
        Create a pull request with the package.
        
        Args:
            package_info: Package metadata
            temp_dir: Temporary directory containing the repo
            custom_message: Optional custom message to include in the PR body
            
        Returns:
            URL of the created PR or None if failed
        """
        print("🚀 Creating pull request...")
        
        try:
            # Initialize git repo with explicit encoding
            repo_path = temp_dir / "repo"
            
            # Set git config to handle encoding properly
            os.environ['GIT_CONFIG_GLOBAL'] = '/dev/null'  # Avoid user git config interference
            os.environ['LC_ALL'] = 'C.UTF-8'  # Set UTF-8 locale
            
            repo = git.Repo.clone_from(
                f"https://{self.github_token}@github.com/{self.repo_owner}/{self.repo_name}.git",
                repo_path
            )
            
            # Configure git user for this repository
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", "paxd-publish")
                git_config.set_value("user", "email", "paxd-publish@github.com")
            
            # Create new branch
            package_id = package_info['package_id']
            branch_name = f"add-package-{package_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            repo.git.checkout('HEAD', b=branch_name)
            
            # Copy package files to repo
            success = self.create_package_structure(
                Path.cwd(),  # Current directory (where user ran the command)
                repo_path,
                package_info
            )
            
            if not success:
                return None
            
            # Add files to git
            repo.git.add('packages/')
            
            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.index.diff("HEAD"):
                print("  ⚠️  No changes detected - package may already exist")
                return None
            
            # Commit changes
            commit_message = f"Add package {package_id} v{package_info.get('version', 'unknown')}\n\nAutomatically published via paxd-publish"
            repo.git.commit('-m', commit_message)
            
            # Push branch
            origin = repo.remote('origin')
            origin.push(branch_name)
            
            # Create PR
            pr_title = f"Add package: {package_info.get('name', package_id)} v{package_info.get('version', 'unknown')}"
            
            # Build PR body with optional custom message
            pr_body_parts = []
            
            # Add custom message if provided
            if custom_message:
                pr_body_parts.append(f"## Changes & Updates\n\n{custom_message}\n")
            
            # Add standard package information
            pr_body_parts.append(f"""## Package Submission

**Package ID:** `{package_id}`
**Name:** {package_info.get('name', 'Unknown')}
**Version:** {package_info.get('version', 'unknown')}
**Author:** {package_info.get('author', 'Unknown')}
**Description:** {package_info.get('description', 'No description provided')}

### Package Details
- **License:** {package_info.get('license', 'Not specified')}
- **Tags:** {', '.join(package_info.get('tags', []))}

### Files Included
- Package manifest (`package.yaml` or `paxd.yaml`)
- Source files in `src/` directory
{('- PaxD executable (`paxd`)' if Path('paxd').exists() else '')}

---
*This PR was created automatically by paxd-publish*""")
            
            pr_body = '\n'.join(pr_body_parts)

            pr = self.repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            print(f"  ✅ Pull request created: {pr.html_url}")
            return pr.html_url
            
        except Exception as e:
            print(f"  ❌ Error creating pull request: {e}")
            return None

    def publish_package(self, package_dir: Optional[Path] = None, custom_message: Optional[str] = None) -> bool:
        """
        Main method to publish a package.
        
        Args:
            package_dir: Directory containing the package (defaults to current directory)
            custom_message: Optional custom message to include in the PR body
            
        Returns:
            True if successful, False otherwise
        """
        if package_dir is None:
            package_dir = Path.cwd()
        
        print(f"🎯 Publishing package from: {package_dir}")
        
        # Check for encoding issues first
        print("🔍 Checking file encodings...")
        problematic_files = self.check_file_encodings(package_dir)
        
        if problematic_files:
            print(f"\n⚠️  Found {len(problematic_files)} files with encoding issues:")
            for file_name in problematic_files:
                print(f"  - {file_name}")
            print(f"\n💡 These files contain non-UTF-8 characters or are binary files.")
            print(f"   Consider converting text files to UTF-8 or excluding binary files.")
            print(f"   Proceeding with caution - some files may be skipped.")
        
        # Validate package
        validation = self.validate_package_structure(package_dir)
        
        # Report validation results
        if validation['errors']:
            print("\n❌ Validation errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        if not validation['valid']:
            print("\n💥 Package validation failed. Please fix the errors above.")
            return False
        
        print(f"\n✅ Package validation successful!")
        package_info = validation['package_info']
        
        print(f"📋 Package Info:")
        print(f"  - Name: {package_info.get('name')}")
        print(f"  - Author: {package_info.get('author')}")
        print(f"  - Version: {package_info.get('version')}")
        print(f"  - Package ID: {package_info['package_id']}")
        
        # Create temporary directory for git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create PR
            pr_url = self.create_pull_request(package_info, temp_path, custom_message)
            
            if pr_url:
                print(f"\n🎉 Package published successfully!")
                print(f"📄 Pull Request: {pr_url}")
                print(f"⏳ Your package will be available after the PR is reviewed and merged.")
                return True
            else:
                print(f"\n💥 Failed to create pull request.")
                return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Publish PaxD packages to the repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Publish package from current directory
  paxd-publish
  
  # Publish package from specific directory
  paxd-publish --dir ./my-package
  
  # Include a custom message about changes
  paxd-publish --message "Fixed critical bug in authentication module"
  
  # Use custom repository
  paxd-publish --owner myuser --repo myrepo

Environment Variables:
  PAXD_GH_TOKEN: GitHub personal access token (required)
        """
    )
    
    parser.add_argument(
        '--dir',
        type=Path,
        default=Path.cwd(),
        help='Directory containing the package to publish (default: current directory)'
    )
    parser.add_argument(
        '--owner',
        default='mralfiem591',
        help='GitHub repository owner (default: mralfiem591 - this is where the PaxD repository is located)'
    )
    parser.add_argument(
        '--repo',
        default='paxd',
        help='GitHub repository name (default: paxd)'
    )
    parser.add_argument(
        '--token',
        help='GitHub token (or set PAXD_GH_TOKEN env var)'
    )
    parser.add_argument(
        '--message',
        help='Custom message to include in the pull request describing changes and updates'
    )
    
    args = parser.parse_args()
    
    # Get GitHub token
    github_token = args.token or os.getenv('PAXD_GH_TOKEN')
    if not github_token:
        print("❌ Error: GitHub token is required.")
        print("Set the PAXD_GH_TOKEN environment variable or use --token option.")
        print("Get a token from: https://github.com/settings/tokens")
        sys.exit(1)
    
    # Validate directory
    if not args.dir.exists():
        print(f"❌ Error: Directory does not exist: {args.dir}")
        sys.exit(1)
    
    if not args.dir.is_dir():
        print(f"❌ Error: Path is not a directory: {args.dir}")
        sys.exit(1)
    
    # Create publisher and publish package
    try:
        publisher = PaxDPackagePublisher(
            github_token=github_token,
            repo_owner=args.owner,
            repo_name=args.repo
        )
        
        success = publisher.publish_package(args.dir, args.message)
        sys.exit(0 if success else 1)
        
    except UnicodeDecodeError as e:
        print(f"💥 Unicode/Encoding Error: {e}")
        print(f"📄 This usually means there's a file with non-UTF-8 characters.")
        print(f"🔧 Try saving all files with UTF-8 encoding and remove any binary files from the package.")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()