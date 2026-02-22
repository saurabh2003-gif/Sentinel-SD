import re
import os

def bump_version():
    target_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setup.py")
    
    if not os.path.exists(target_file):
        print(f"Error: Could not find setup.py at {target_file}")
        return

    with open(target_file, "r") as f:
        content = f.read()
    
    # Simple regex to find the version="X.Y.Z" pattern
    match = re.search(r'version="(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("Error: Could not find version format in setup.py")
        return
        
    major, minor, patch = match.groups()
    new_patch = int(patch) + 1
    new_version = f'{major}.{minor}.{new_patch}'
    
    old_version_str = f'version="{major}.{minor}.{patch}"'
    new_version_str = f'version="{new_version}"'
    
    new_content = content.replace(old_version_str, new_version_str)
    
    with open(target_file, "w") as f:
        f.write(new_content)
        
    print(f"Successfully bumped version from {major}.{minor}.{patch} to {new_version}")

if __name__ == "__main__":
    bump_version()
