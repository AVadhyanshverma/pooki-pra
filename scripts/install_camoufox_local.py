#!/usr/bin/env python3
"""
Unpacks and registers /tmp/camoufox.zip into the official Camoufox cache directory.
"""
import os
import sys
import zipfile
import orjson
import shlex
from pathlib import Path

def main():
    zip_path = Path("/tmp/camoufox.zip")
    if not zip_path.exists():
        print(f"Error: {zip_path} not found.")
        sys.exit(1)
        
    import camoufox.multiversion as mv
    import camoufox.pkgman as pm
    
    fetcher = pm.CamoufoxFetcher()
    repo_name = mv.get_repo_name(fetcher.github_repo)
    if fetcher._selected_version and fetcher._selected_version.sha256:
        sha8 = fetcher._selected_version.sha8
    else:
        sha8 = getattr(fetcher, "installed_sha8", "")
        
    version_folder = mv.version_folder_name(fetcher.version, fetcher.build, sha8)
    install_path = mv.BROWSERS_DIR / repo_name / version_folder
    
    print(f"Target Camoufox install path: {install_path}")
    install_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MB)...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(install_path)
    print("Extraction complete.")
    
    if fetcher._selected_version:
        metadata = fetcher._selected_version.to_metadata()
    else:
        metadata = {
            'version': fetcher.version,
            'build': fetcher.build,
            'prerelease': fetcher.is_prerelease,
            'sha256': getattr(fetcher, "installed_sha256", None),
            'created_at': getattr(fetcher, "installed_created_at", None),
            'interface': getattr(fetcher, "installed_interface", 1),
        }
        
    with open(install_path / 'version.json', 'wb') as f:
        f.write(orjson.dumps(metadata))
        
    if pm.OS_NAME != 'win':
        os.system(f'chmod -R 755 {shlex.quote(str(install_path))}')
        
    mv.set_active(f"browsers/{repo_name}/{version_folder}")
    mv.COMPAT_FLAG.touch()
    pm.ensure_browser_profile_dir()
    
    print("\nCamoufox browser successfully registered and activated!")
    print(f"Executable path: {pm.camoufox_path()}")

if __name__ == "__main__":
    main()
