#!/usr/bin/env python3
"""
Minecraft Bedrock Addon Development Tool
Unified CLI for creating, building, and transferring addons from Linux to iPad via Dropbox
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

# Configuration
HOME = Path.home()
ADDONS_DIR = HOME / "minecraft-addons"
BUILDS_DIR = ADDONS_DIR / "builds"
DROPBOX_DIR = HOME / "Dropbox" / "Minecraft"

# Constants
PACK_TYPE_BEHAVIOR = "behavior"
PACK_TYPE_RESOURCE = "resource"
MODULE_TYPE_DATA = "data"
MODULE_TYPE_RESOURCES = "resources"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_msg(msg: str, msg_type: str = "info"):
    """Print formatted message based on type"""
    formats = {
        "success": (f"{Colors.GREEN}✓{Colors.RESET} {msg}", None),
        "error": (f"{Colors.RED}✗{Colors.RESET} {msg}", sys.stderr),
        "info": (f"{Colors.BLUE}ℹ{Colors.RESET} {msg}", None),
        "header": (f"\n{Colors.BOLD}{msg}{Colors.RESET}", None),
    }
    text, file = formats[msg_type]
    print(text, file=file)

def run_command(cmd: list, check: bool = True, capture: bool = False) -> Optional[str]:
    """Run a shell command"""
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            print_msg(f"Command failed: {' '.join(cmd)}", "error")
            sys.exit(1)
        return None

def validate_json_files(addon_path: Path) -> bool:
    """Validate all JSON files in addon directory"""
    json_files = list(addon_path.rglob("*.json"))

    if not json_files:
        print_msg("No JSON files found")
        return True

    all_valid = True
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            print_msg(f"Invalid JSON in {json_file.relative_to(addon_path)}: {e}", "error")
            all_valid = False

    if all_valid:
        print_msg("All JSON files valid", "success")

    return all_valid

def package_addon(addon_path: Path, output_dir: Path, addon_name: str) -> Path:
    """Package addon into .mcaddon and .mcpack files using zip command"""
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Copy packs to temp directory
        bp_path = addon_path / "behavior_pack"
        rp_path = addon_path / "resource_pack"

        if bp_path.exists():
            shutil.copytree(bp_path, tmppath / "behavior_pack")
        if rp_path.exists():
            shutil.copytree(rp_path, tmppath / "resource_pack")

        # Create .mcaddon (both packs)
        mcaddon_file = output_dir / f"{addon_name}.mcaddon"
        subprocess.run(["zip", "-qr", str(mcaddon_file), "."], cwd=tmppath, check=True)

        # Create individual .mcpack files
        if bp_path.exists():
            bp_mcpack = output_dir / f"{addon_name}_BP.mcpack"
            subprocess.run(["zip", "-qr", str(bp_mcpack), "."],
                         cwd=tmppath / "behavior_pack", check=True)

        if rp_path.exists():
            rp_mcpack = output_dir / f"{addon_name}_RP.mcpack"
            subprocess.run(["zip", "-qr", str(rp_mcpack), "."],
                         cwd=tmppath / "resource_pack", check=True)

    return mcaddon_file

def generate_uuid() -> str:
    """Generate a lowercase UUID"""
    return str(uuid.uuid4())

def resolve_addon_path(name: str, custom_path: Optional[str] = None) -> Path:
    """Resolve addon path from name or custom path"""
    if custom_path:
        addon_path = Path(custom_path)
    else:
        addon_path = ADDONS_DIR / name

    if not addon_path.exists():
        print_msg(f"Addon not found: {addon_path}", "error")
        sys.exit(1)

    return addon_path

def create_manifest(pack_type: str, addon_name: str) -> dict:
    """Create a manifest.json structure"""
    is_behavior = pack_type == PACK_TYPE_BEHAVIOR
    return {
        "format_version": 2,
        "header": {
            "name": f"{addon_name} {'Behavior' if is_behavior else 'Resources'}",
            "description": f"{'Behavior' if is_behavior else 'Resource'} pack for {addon_name}",
            "uuid": generate_uuid(),
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [
            {
                "type": MODULE_TYPE_DATA if is_behavior else MODULE_TYPE_RESOURCES,
                "uuid": generate_uuid(),
                "version": [1, 0, 0]
            }
        ]
    }

def init_addon(args):
    """Initialize a new addon project"""
    addon_name = args.name
    addon_path = ADDONS_DIR / addon_name

    if addon_path.exists():
        print_msg(f"Addon '{addon_name}' already exists at {addon_path}", "error")
        sys.exit(1)

    print_msg(f"Initializing addon: {addon_name}", "header")

    # Create directory structure
    bp_path = addon_path / "behavior_pack"
    rp_path = addon_path / "resource_pack"

    bp_path.mkdir(parents=True)
    rp_path.mkdir(parents=True)

    # Create subdirectories
    for subdir in ["entities", "items", "blocks", "recipes", "functions"]:
        (bp_path / subdir).mkdir()

    for subdir in ["textures", "models", "sounds", "animations"]:
        (rp_path / subdir).mkdir()

    # Create manifests
    bp_manifest = create_manifest(PACK_TYPE_BEHAVIOR, addon_name)
    rp_manifest = create_manifest(PACK_TYPE_RESOURCE, addon_name)

    with open(bp_path / "manifest.json", 'w') as f:
        json.dump(bp_manifest, f, indent=2)

    with open(rp_path / "manifest.json", 'w') as f:
        json.dump(rp_manifest, f, indent=2)

    print_msg(f"Addon initialized at {addon_path}", "success")
    print_msg(f"Behavior Pack UUID: {bp_manifest['header']['uuid']}")
    print_msg(f"Resource Pack UUID: {rp_manifest['header']['uuid']}")
    print(f"\nNext steps:")
    print(f"  1. Edit files in {addon_path}")
    print(f"  2. Build to Dropbox: mcaddon build {addon_name}")
    print(f"  3. Load on iPad from Files → Dropbox → Minecraft")

def build_addon(args):
    """Build addon into .mcaddon and .mcpack files"""
    addon_path = resolve_addon_path(args.name, args.path)
    addon_name = addon_path.name
    print_msg(f"Building addon: {addon_name}", "header")

    # Validate JSON files
    print_msg("Validating JSON files...")
    if not validate_json_files(addon_path):
        sys.exit(1)

    # Determine output directory
    if args.local:
        output_dir = BUILDS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = DROPBOX_DIR
        if not output_dir.exists():
            print_msg(f"Creating Dropbox Minecraft folder: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

    # Package addon
    print_msg(f"Packaging addon to {'Dropbox' if not args.local else 'local builds'}...")
    mcaddon_file = package_addon(addon_path, output_dir, addon_name)

    print_msg(f"Build complete: {mcaddon_file}", "success")

    # List generated files
    print("\nGenerated files:")
    for ext in [".mcaddon", "_BP.mcpack", "_RP.mcpack"]:
        file = output_dir / f"{addon_name}{ext}"
        if file.exists():
            size = file.stat().st_size / 1024
            print(f"  • {file.name} ({size:.1f} KB)")

    # Check Dropbox sync status if building to Dropbox
    if not args.local:
        check_dropbox_sync()
        print(f"\n{Colors.BOLD}On iPad:{Colors.RESET}")
        print("  1. Open Files app → Browse → Dropbox")
        print("  2. Navigate to Minecraft folder")
        print(f"  3. Tap '{addon_name}.mcaddon'")
        print("  4. Select 'Open in Minecraft'")

    return mcaddon_file

def check_dropbox_sync(timeout: int = 20) -> None:
    """Check Dropbox sync status and wait for completion"""
    dropbox_cli = subprocess.run(["which", "dropbox"], capture_output=True)
    if dropbox_cli.returncode != 0:
        return

    print_msg("Checking Dropbox sync status...")
    status = run_command(["dropbox", "status"], capture=True, check=False)

    if status and "Up to date" in status:
        print_msg("Dropbox sync complete!", "success")
        return

    if status and "Syncing" in status:
        print_msg("Syncing to Dropbox...")
        for _ in range(timeout // 2):
            time.sleep(2)
            status = run_command(["dropbox", "status"], capture=True, check=False)
            if status and "Up to date" in status:
                print_msg("Dropbox sync complete!", "success")
                return

def get_file_mtimes(addon_path: Path) -> str:
    """Get a string of all file modification times for change detection"""
    mtimes = []
    for file_path in sorted(addon_path.rglob("*")):
        if file_path.is_file():
            mtimes.append(f"{file_path.stat().st_mtime} {file_path}")
    return "\n".join(mtimes)

def watch_addon(args):
    """Watch addon directory and auto-rebuild on changes"""
    addon_path = resolve_addon_path(args.name, args.path)
    addon_name = addon_path.name

    print_msg(f"Watching addon: {addon_name}", "header")
    print_msg(f"Path: {addon_path}")
    print_msg("Press Ctrl+C to stop\n")

    # Initial build
    build_addon(args)

    # Track file modification times
    mtimes = get_file_mtimes(addon_path)

    try:
        while True:
            time.sleep(2)  # Check every 2 seconds

            # Get current modification times
            current_mtimes = get_file_mtimes(addon_path)

            # Check for changes
            if current_mtimes != mtimes:
                print(f"\n{Colors.YELLOW}Change detected, rebuilding...{Colors.RESET}")
                build_addon(args)
                mtimes = current_mtimes

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped watching{Colors.RESET}")

def list_addons(args):
    """List all addons"""
    print_msg("Available Addons", "header")

    if not ADDONS_DIR.exists():
        print_msg("No addons directory found")
        return

    addons = [d for d in ADDONS_DIR.iterdir() if d.is_dir() and d.name not in ['tools', 'builds']]

    if not addons:
        print_msg("No addons found")
        print(f"\nCreate one with: mcaddon init <name>")
        return

    for addon_dir in sorted(addons):
        has_bp = (addon_dir / "behavior_pack").exists()
        has_rp = (addon_dir / "resource_pack").exists()
        packs = []
        if has_bp:
            packs.append("BP")
        if has_rp:
            packs.append("RP")

        # Check if built
        mcaddon_file = BUILDS_DIR / f"{addon_dir.name}.mcaddon"
        built = "✓ built" if mcaddon_file.exists() else "not built"

        print(f"  • {addon_dir.name:20} [{', '.join(packs):5}] {built}")

def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Bedrock Addon Development Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mcaddon init my_addon              Create new addon
  mcaddon build my_addon             Build to Dropbox (auto-syncs to iPad)
  mcaddon build my_addon --local     Build to local folder only
  mcaddon watch my_addon             Auto-rebuild to Dropbox on changes
  mcaddon list                       List all addons
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize new addon')
    init_parser.add_argument('name', help='Addon name')
    init_parser.set_defaults(func=init_addon)

    # Build command
    build_parser = subparsers.add_parser('build', help='Build addon to Dropbox')
    build_parser.add_argument('name', help='Addon name')
    build_parser.add_argument('--path', help='Custom addon path')
    build_parser.add_argument('--local', action='store_true', help='Build to local folder instead of Dropbox')
    build_parser.set_defaults(func=build_addon)

    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch and auto-rebuild to Dropbox')
    watch_parser.add_argument('name', help='Addon name')
    watch_parser.add_argument('--path', help='Custom addon path')
    watch_parser.add_argument('--local', action='store_true', help='Build to local folder instead of Dropbox')
    watch_parser.set_defaults(func=watch_addon)

    # List command
    list_parser = subparsers.add_parser('list', help='List all addons')
    list_parser.set_defaults(func=list_addons)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Ensure directories exist
    ADDONS_DIR.mkdir(parents=True, exist_ok=True)

    args.func(args)

if __name__ == "__main__":
    main()
