# Run a package, given the full path is provided as an argument

import os

if os.name != "nt":
    print(f"PaxD is a Windows only tool.")
    print(f"Please run PaxD on a Windows device!")
    exit(1)

# Step 1: create a hook, so other packages can import paxd-sdk, and it becomes the paxd sdk package

import sys, importlib.abc, importlib.util

if not os.path.exists(os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD', 'com.mralfiem591.paxd-sdk', 'main.py')):
    print("PaxD SDK is not installed. Please install PaxD SDK to run this package, via 'paxd install paxd-sdk'.")
    exit(1)

SDK_PATH = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD', 'com.mralfiem591.paxd-sdk', 'main.py')

class PaxDSDKLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None  # Use default module creation semantics

    def exec_module(self, module):
        with open(SDK_PATH, 'r', encoding='utf-8') as f:
            code = f.read()
        exec(compile(code, SDK_PATH, 'exec'), module.__dict__)
    
class PaxDSDKFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'paxd_sdk':
            return importlib.util.spec_from_loader(fullname, PaxDSDKLoader())
        return None

sys.meta_path.insert(0, PaxDSDKFinder())

# Step 2: run the package, with adjusted sys.argv (remove the first argument, which is the run_pkg.py path)
sys.argv = sys.argv[1:]
with open(sys.argv[0], 'r', encoding='utf-8') as f:
    exec(f.read())