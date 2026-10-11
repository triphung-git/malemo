"""Configuration loader for TikTok Data Pipeline."""

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
    except Exception:
        pass

# Load .env file automatically
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"

_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_config(config_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file, with environment variable overrides."""
    global _CONFIG_CACHE
    path = Path(config_path or os.getenv("CONFIG_PATH") or DEFAULT_CONFIG_PATH)

    if not path.is_file():
        path = DEFAULT_CONFIG_PATH

    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config.setdefault("paths", {})
    config.setdefault("crawler", {})
    config.setdefault("media", {})
    config.setdefault("media", {}).setdefault("download", {})
    config.setdefault("media", {}).setdefault("models", {})

    if os.getenv("FFMPEG_PATH"):
        config["paths"]["ffmpeg_path"] = os.environ["FFMPEG_PATH"]
    if os.getenv("FFPROBE_PATH"):
        config["paths"]["ffprobe_path"] = os.environ["FFPROBE_PATH"]

    if os.getenv("YTDLP_DOWNLOAD_ATTEMPTS"):
        config["media"]["download"]["attempts"] = int(os.environ["YTDLP_DOWNLOAD_ATTEMPTS"])
    if os.getenv("YTDLP_PROXY"):
        config["media"]["download"]["proxy"] = os.environ["YTDLP_PROXY"]
    if os.getenv("YTDLP_COOKIEFILE"):
        config["media"]["download"]["cookiefile"] = os.environ["YTDLP_COOKIEFILE"]
    if os.getenv("YTDLP_COOKIES_FROM_BROWSER"):
        config["media"]["download"]["cookies_from_browser"] = os.environ["YTDLP_COOKIES_FROM_BROWSER"]

    if os.getenv("UVR_NUM_THREADS"):
        config["media"]["models"]["uvr_num_threads"] = int(os.environ["UVR_NUM_THREADS"])
    if os.getenv("DPDFNET_NUM_THREADS"):
        config["media"]["models"]["dpdfnet_num_threads"] = int(os.environ["DPDFNET_NUM_THREADS"])
    if os.getenv("SHERPA_ONNX_PROVIDER"):
        config["media"]["models"]["sherpa_provider"] = os.environ["SHERPA_ONNX_PROVIDER"]

    _CONFIG_CACHE = config
    return config


def get_config() -> Dict[str, Any]:
    """Return cached configuration or load default."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE


def get_project_root() -> Path:
    """Return the absolute Path to project root."""
    return PROJECT_ROOT


def resolve_path(rel_or_abs: str | Path) -> Path:
    """Resolve a relative path against PROJECT_ROOT, or return absolute path."""
    path = Path(rel_or_abs)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def resolve_binary(binary_name: str | Path) -> Path:
    """
    Resolve a binary executable across platforms (Windows / Linux / macOS).

    Handles:
    1. System binaries installed in PATH (e.g. via apt / brew / chocolatey).
    2. Project-local executables (e.g. ffmpeg.exe on Windows in project root).
    3. Cross-platform name discrepancies (.exe on Windows vs extension-less on POSIX).
    4. Avoiding accidental execution of Windows .exe files when running on POSIX environments.
    """
    name_str = str(binary_name).strip()
    is_windows = sys.platform == "win32"

    candidate = Path(name_str)
    if candidate.is_absolute():
        if candidate.is_file() and (is_windows or os.access(candidate, os.X_OK)):
            return candidate
        if not is_windows and name_str.lower().endswith(".exe"):
            stripped = Path(name_str[:-4])
            if stripped.is_file() and os.access(stripped, os.X_OK):
                return stripped
        return candidate

    if name_str.lower().endswith(".exe"):
        base_name = name_str[:-4]
        win_name = name_str
    else:
        base_name = name_str
        win_name = f"{name_str}.exe"

    if is_windows:
        local_exe = (PROJECT_ROOT / win_name).resolve()
        if local_exe.is_file():
            return local_exe
        local_base = (PROJECT_ROOT / base_name).resolve()
        if local_base.is_file():
            return local_base
        which_path = shutil.which(win_name) or shutil.which(base_name)
        if which_path:
            return Path(which_path)
        return local_exe
    else:
        # On POSIX (Linux/macOS):
        # Prefer system PATH (e.g. /usr/bin/ffmpeg or /usr/bin/ffprobe)
        which_path = shutil.which(base_name)
        if which_path:
            return Path(which_path)
        # Look for a native POSIX binary in PROJECT_ROOT (without .exe)
        local_posix = (PROJECT_ROOT / base_name).resolve()
        if local_posix.is_file() and os.access(local_posix, os.X_OK):
            return local_posix
        which_raw = shutil.which(name_str)
        if which_raw:
            return Path(which_raw)
        return local_posix

