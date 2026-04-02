#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from re import Match

DOWNLOAD_FOLDER = Path.home() / "Downloads"
SECONDS_TO_CHECK_FOR_DOWNLOAD_FILES = 1

if not DOWNLOAD_FOLDER.exists():
    print(f"Expecting Downloads folder on: {DOWNLOAD_FOLDER}")
    sys.exit(1)


def is_version_at_least_0_12(version_str: str) -> bool:
    # Extract version like "0.12.0" from "NVIM v0.12.0"
    match: Match[str] | None = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")

    major, minor = map(int, match.groups()[:2])
    return major > 0 or (major == 0 and minor >= 12)


parser = argparse.ArgumentParser(
    description="Download vim plugin packs from lock file."
)
parser.add_argument(
    "lockfile",
    nargs="?",
    default="nvim-pack-lock.json",
    help="Path to nvim-pack-lock JSON file",
)

args = parser.parse_args()

json_lock_path: Path = Path(args.lockfile)


def get_open_cmd() -> str:
    if shutil.which("xdg-open"):
        print("Using program `xdg-open` to open links")
        open_cmd = "xdg-open"
    elif shutil.which("open"):
        print("Using program `open` to open links")
        open_cmd = "open"
    else:
        print("Expecting xdg-open or open to open links")
        sys.exit(1)
    return open_cmd


with json_lock_path.open("r", encoding="utf-8") as f:
    plugins_dict = json.load(f)


def run_process(commands: list[str]) -> str:
    result = subprocess.run(commands, capture_output=True, text=True)
    result_msg: str = result.stderr or result.stdout
    return result_msg.splitlines()[0] if len(result_msg) > 0 else ""


def run_nvim_cmd(lua_command: str) -> str:
    full_cmd: list[str] = ["nvim", "-c", lua_command, "--headless", "+q"]
    return run_process(full_cmd)


def create_URI(src: str, rev: str) -> str:
    return f"{src}/archive/{rev}.zip"


def ask_for_remove_path(path: Path, prompt: str) -> bool:
    if path.exists():
        if input(prompt).strip().lower() in ("", "y", "yes"):
            (path.unlink() if path.is_file() else shutil.rmtree(path))
            print(f"Removed {path}")
        else:
            return False  # False means should use the downloaded file
    return True


def unzip_with_retry(
    file_path: Path, output_dir: Path, sleep_seconds_if_bad_zip=2
) -> None:
    for _ in range(2):
        try:
            zipfile.ZipFile(file_path).extractall(output_dir)
            return
        except zipfile.BadZipFile:
            time.sleep(sleep_seconds_if_bad_zip) if _ == 0 else None


nvim_version_txt: str = run_process(["nvim", "--version"])
if not is_version_at_least_0_12(nvim_version_txt):
    print("Nvim should be at least above 0.12")

cmd = "lua print(vim.fn.stdpath('data'))"
NVIM_DATA_PATH = Path(run_nvim_cmd(cmd))
print(f"Found value of vim.fn.stdpath('data'): {NVIM_DATA_PATH}")

NVIM_PACK_PLUGINS_PATH: Path = NVIM_DATA_PATH / "site" / "pack" / "core" / "opt"
print(f"VIM PACK PATH: {NVIM_PACK_PLUGINS_PATH}")

# it should exists but creates if not
if not NVIM_PACK_PLUGINS_PATH.exists():
    NVIM_PACK_PLUGINS_PATH.mkdir(parents=True)

open_cmd: str = get_open_cmd()

for plugin_name, plugin_spec in plugins_dict["plugins"].items():
    print(f"\n### Plugin name: {plugin_name}")
    src, rev = plugin_spec["src"], plugin_spec["rev"]
    repo_name = src.split("/")[-1]
    uri: str = create_URI(src, rev)

    destination_folder = NVIM_PACK_PLUGINS_PATH / repo_name
    if destination_folder.exists():
        ask_for_remove_path(
            destination_folder,
            prompt=f"\nFound the {plugin_name} already in nvim plugins path: {NVIM_PACK_PLUGINS_PATH}, should remove it? [Y/n]",
        )
        if destination_folder.exists():
            continue  # if it still exists skip this plugin download

    filepath: Path = DOWNLOAD_FOLDER / f"{repo_name}-{rev}.zip"
    if ask_for_remove_path(
        filepath,
        prompt=f"\nFound the {plugin_name} in {DOWNLOAD_FOLDER}, should remove it? [Y/n] ",
    ):
        res: str = run_process([open_cmd, uri])
        print(
            f"\nDownloading {plugin_name} waiting for it under {DOWNLOAD_FOLDER} with filename: {filepath}"
        )
    while True:
        if filepath.is_file():
            unzip_with_retry(filepath, NVIM_PACK_PLUGINS_PATH)
            extracted_plugin_folder_path: Path = NVIM_PACK_PLUGINS_PATH / filepath.stem
            if extracted_plugin_folder_path.exists():
                shutil.move(
                    extracted_plugin_folder_path, NVIM_PACK_PLUGINS_PATH / repo_name
                )
            break
        time.sleep(SECONDS_TO_CHECK_FOR_DOWNLOAD_FILES)
