#!/usr/bin/env python3
"""
Minecraft Bedrock Addon Development Tool
Unified CLI for creating, building, and transferring addons from Linux to iPad via Dropbox
"""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# Configuration
HOME = Path.home()
ADDONS_DIR = HOME / "minecraft-addons"
TOOLS_DIR = ADDONS_DIR / "tools"
BUILDS_DIR = ADDONS_DIR / "builds"
DROPBOX_DIR = HOME / "Dropbox" / "Minecraft"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}", file=sys.stderr)

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{msg}{Colors.RESET}")

def run_command(cmd: list, check=True, capture=False) -> Optional[str]:
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
            print_error(f"Command failed: {' '.join(cmd)}")
            sys.exit(1)
        return None

def generate_uuid() -> str:
    """Generate a lowercase UUID"""
    return str(uuid.uuid4())

def create_manifest(pack_type: str, addon_name: str) -> dict:
    """Create a manifest.json structure"""
    is_behavior = pack_type == "behavior"
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
                "type": "data" if is_behavior else "resources",
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
        print_error(f"Addon '{addon_name}' already exists at {addon_path}")
        sys.exit(1)

    print_header(f"Initializing addon: {addon_name}")

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
    bp_manifest = create_manifest("behavior", addon_name)
    rp_manifest = create_manifest("resource", addon_name)

    with open(bp_path / "manifest.json", 'w') as f:
        json.dump(bp_manifest, f, indent=2)

    with open(rp_path / "manifest.json", 'w') as f:
        json.dump(rp_manifest, f, indent=2)

    print_success(f"Addon initialized at {addon_path}")
    print_info(f"Behavior Pack UUID: {bp_manifest['header']['uuid']}")
    print_info(f"Resource Pack UUID: {rp_manifest['header']['uuid']}")
    print(f"\nNext steps:")
    print(f"  1. Edit files in {addon_path}")
    print(f"  2. Build to Dropbox: mcaddon build {addon_name}")
    print(f"  3. Load on iPad from Files → Dropbox → Minecraft")

def build_addon(args):
    """Build addon into .mcaddon and .mcpack files"""
    addon_path = Path(args.path) if args.path else ADDONS_DIR / args.name

    if not addon_path.exists():
        print_error(f"Addon not found: {addon_path}")
        sys.exit(1)

    addon_name = addon_path.name
    print_header(f"Building addon: {addon_name}")

    # Validate JSON files
    print_info("Validating JSON files...")
    validate_script = TOOLS_DIR / "validate-json.sh"
    run_command([str(validate_script), str(addon_path)])

    # Determine output directory
    if args.local:
        output_dir = BUILDS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = DROPBOX_DIR
        if not output_dir.exists():
            print_info(f"Creating Dropbox Minecraft folder: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

    # Package addon
    print_info(f"Packaging addon to {'Dropbox' if not args.local else 'local builds'}...")
    package_script = TOOLS_DIR / "package-addon.sh"
    output_file = run_command(
        [str(package_script), str(addon_path), str(output_dir)],
        capture=True
    )

    print_success(f"Build complete: {output_file}")

    # List generated files
    print("\nGenerated files:")
    for ext in [".mcaddon", "_BP.mcpack", "_RP.mcpack"]:
        file = output_dir / f"{addon_name}{ext}"
        if file.exists():
            size = file.stat().st_size / 1024
            print(f"  • {file.name} ({size:.1f} KB)")

    # Check Dropbox sync status if building to Dropbox
    if not args.local:
        dropbox_cli = subprocess.run(["which", "dropbox"], capture_output=True)
        if dropbox_cli.returncode == 0:
            print_info("Checking Dropbox sync status...")
            status = run_command(["dropbox", "status"], capture=True, check=False)
            if status and "Up to date" in status:
                print_success("Dropbox sync complete!")
            elif status and "Syncing" in status:
                print_info("Syncing to Dropbox...")
                # Wait for sync
                for _ in range(10):
                    time.sleep(2)
                    status = run_command(["dropbox", "status"], capture=True, check=False)
                    if status and "Up to date" in status:
                        print_success("Dropbox sync complete!")
                        break

        print(f"\n{Colors.BOLD}On iPad:{Colors.RESET}")
        print("  1. Open Files app → Browse → Dropbox")
        print("  2. Navigate to Minecraft folder")
        print(f"  3. Tap '{addon_name}.mcaddon'")
        print("  4. Select 'Open in Minecraft'")

    return output_file

def watch_addon(args):
    """Watch addon directory and auto-rebuild on changes"""
    addon_path = Path(args.path) if args.path else ADDONS_DIR / args.name

    if not addon_path.exists():
        print_error(f"Addon not found: {addon_path}")
        sys.exit(1)

    addon_name = addon_path.name
    print_header(f"Watching addon: {addon_name}")
    print_info(f"Path: {addon_path}")
    print_info("Press Ctrl+C to stop\n")

    # Initial build
    build_addon(argparse.Namespace(name=addon_name, path=str(addon_path), local=args.local))

    # Watch for changes using inotifywait
    try:
        while True:
            cmd = [
                "inotifywait",
                "-r",
                "-e", "modify,create,delete,move",
                str(addon_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            print(f"\n{Colors.YELLOW}Change detected, rebuilding...{Colors.RESET}")
            time.sleep(1)  # Debounce
            build_addon(argparse.Namespace(name=addon_name, path=str(addon_path), local=args.local))

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped watching{Colors.RESET}")

def list_addons(args):
    """List all addons"""
    print_header("Available Addons")

    if not ADDONS_DIR.exists():
        print_info("No addons directory found")
        return

    addons = [d for d in ADDONS_DIR.iterdir() if d.is_dir() and d.name not in ['tools', 'builds']]

    if not addons:
        print_info("No addons found")
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
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    args.func(args)

if __name__ == "__main__":
    main()
