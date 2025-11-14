# Run a package, given the full path is provided as an argument

import os

if os.name != "nt":
    print(f"PaxD is a Windows only tool.")
    print(f"Please run PaxD on a Windows device!")
    print("(This also applies to tools and apps installed via PaxD)")
    exit(1)

# Step 1: create a hook, so other packages can import paxd-sdk, and it becomes the paxd sdk package

import sys, importlib.abc, importlib.util

class SDKException(Exception):
    """Custom exception raised when trying to use PaxD SDK without it being installed."""
    pass

SDK_PATH = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'PaxD', 'com.mralfiem591.paxd-sdk', 'main.py')
SDK_INSTALLED = os.path.exists(SDK_PATH)

class MockSDKModule:
    """Mock module that raises SDKException when any attribute is accessed."""
    
    def __getattr__(self, name):
        raise SDKException(
            f"PaxD SDK is not installed. Cannot access '{name}'. "
            "Please install PaxD SDK via 'paxd install paxd-sdk' to use SDK functionality."
        )
    
    def __call__(self, *args, **kwargs):
        raise SDKException(
            "PaxD SDK is not installed. "
            "Please install PaxD SDK via 'paxd install paxd-sdk' to use SDK functionality."
        )

class PaxDSDKLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None  # Use default module creation semantics

    def exec_module(self, module):
        if SDK_INSTALLED:
            # Load the actual SDK
            with open(SDK_PATH, 'r', encoding='utf-8') as f:
                code = f.read()
            exec(compile(code, SDK_PATH, 'exec'), module.__dict__)
        else:
            # Create a mock SDK that raises exceptions on use
            # Add common SDK attributes/functions that might be accessed
            # Set these to safe default values to avoid triggering SDKException during setup
            setattr(module, '__name__', 'paxd_sdk')
            setattr(module, '__file__', '<mock_paxd_sdk>')
            setattr(module, '__package__', None)
            setattr(module, '__all__', [])  # Empty list for __all__
            setattr(module, '__version__', '0.0.0-mock')  # Mock version string
            
            # Set a custom __getattr__ on the module to handle dynamic attribute access
            def mock_getattr(name):
                raise SDKException(
                    f"PaxD SDK is not installed. Cannot access '{name}'. "
                    "Please install PaxD SDK via 'paxd install paxd-sdk' to use SDK functionality."
                )
            
            module.__getattr__ = mock_getattr
    
class PaxDSDKFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'paxd_sdk':
            return importlib.util.spec_from_loader(fullname, PaxDSDKLoader())
        return None

sys.meta_path.insert(0, PaxDSDKFinder())

# Step 2: run the package, with adjusted sys.argv (remove the first argument, which is the run_pkg.py path, to prevent issues with modules like argparse thinking the main script is named run_pkg.py and not the actual package script)
sys.argv = sys.argv[1:]
with open(sys.argv[1], "r", encoding="utf-8") as f:
    exec(f.read())
