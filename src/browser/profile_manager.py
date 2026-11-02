import os
import shutil
import atexit
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.storage.db import DatabaseManager

DEFAULT_PROFILES_DIR = Path.home() / ".local" / "share" / "agent-browser" / "profiles"

class ProfileManager:
    """
    Manages persistent and ephemeral Firefox/Camoufox user profiles.
    Coordinates with DatabaseManager to persist profile metadata in SQLite.
    """

    def __init__(self, base_dir: Optional[Path] = None, db: Optional[DatabaseManager] = None):
        self.base_dir = base_dir or DEFAULT_PROFILES_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db = db or DatabaseManager()
        self._temp_dirs: List[Path] = []
        atexit.register(self.cleanup_temp_profiles)
        self._sweep_orphaned_temps()

    def _sweep_orphaned_temps(self):
        """Removes orphaned temp directories in /tmp starting with agent_browser_temp_."""
        tmp_base = Path(tempfile.gettempdir())
        try:
            for p in tmp_base.glob("agent_browser_temp_*"):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass

    def create_profile(self, name: str, copy_from: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
        """Creates a persistent profile directory and records it in SQLite."""
        # Sanitize profile name
        clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            raise ValueError(f"Invalid profile name: '{name}'")

        profile_dir = self.base_dir / clean_name
        if profile_dir.exists() and copy_from is None:
            # Re-register if exists
            return self.db.register_profile(clean_name, str(profile_dir), is_temp=False, notes=notes)

        profile_dir.mkdir(parents=True, exist_ok=True)

        if copy_from:
            source = self.get_profile_path(copy_from)
            if source and source.exists():
                shutil.copytree(source, profile_dir, dirs_exist_ok=True)

        return self.db.register_profile(clean_name, str(profile_dir), is_temp=False, notes=notes)

    def create_temp_profile(self) -> Dict[str, Any]:
        """Creates an isolated temporary profile that auto-cleans on exit."""
        temp_id = f"temp_{uuid.uuid4().hex[:8]}"
        temp_path = Path(tempfile.mkdtemp(prefix=f"agent_browser_{temp_id}_"))
        self._temp_dirs.append(temp_path)
        return self.db.register_profile(temp_id, str(temp_path), is_temp=True, notes="Ephemeral session")

    def get_profile_path(self, name: str) -> Optional[Path]:
        profile = self.db.get_profile(name)
        if profile:
            return Path(profile["path"])
        p = self.base_dir / name
        return p if p.exists() else None

    def list_profiles(self) -> List[Dict[str, Any]]:
        profiles = self.db.list_profiles()
        enriched = []
        for p in profiles:
            path = Path(p["path"])
            size_mb = 0.0
            if path.exists():
                total_bytes = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
                size_mb = round(total_bytes / (1024 * 1024), 2)
            item = dict(p)
            item["size_mb"] = size_mb
            enriched.append(item)
        return enriched

    def delete_profile(self, name: str, force: bool = False) -> bool:
        """Deletes a profile from disk and SQLite."""
        profile = self.db.get_profile(name)
        if not profile:
            return False

        if profile.get("is_active") and not force:
            raise ValueError(f"Cannot delete active profile '{name}' without force=True.")

        path = Path(profile["path"])
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

        return self.db.delete_profile(name)

    def switch_profile(self, name: str) -> Dict[str, Any]:
        """Sets the active profile in SQLite."""
        profile = self.db.get_profile(name)
        if not profile:
            raise ValueError(f"Profile '{name}' does not exist.")
        self.db.set_active_profile(name)
        return self.db.get_profile(name)

    def cleanup_temp_profiles(self):
        """Cleans up all tracked temporary profile folders."""
        for p in self._temp_dirs:
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
        self._temp_dirs.clear()
