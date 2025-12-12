# AutoPackage - Automated Extension Packager

import os

# 1: Iterate over folders in 'src' dir
src_dir = os.path.join(os.path.dirname(__file__), 'src')
for folder_name in os.listdir(src_dir):
    # Run `python extension_packager.py src/<folder_name> -o build/<folder_name>.zip`
    folder_path = os.path.join(src_dir, folder_name)
    if os.path.isdir(folder_path):
        output_path = os.path.join(os.path.dirname(__file__), 'build', f"{folder_name}.zip")
        os.system(f'python "{os.path.join(os.path.dirname(__file__), "extension_packager.py")}" "{folder_path}" -o "{output_path}"')