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
CACHE_FOLDER = Path.home() / ".cache" / "nvim" / "vimpack-manual-downloader"
SECONDS_TO_CHECK_FOR_DOWNLOAD_FILES = 1


def is_version_at_least_0_12(version_str: str) -> bool:
    """Checks if the given Neovim version string is at least 0.12.
    Args:
        version_str (str): The Neovim version string (e.g., "NVIM v0.12.0").
    Returns:
        bool: True if the version is >= 0.12, False otherwise.
    Raises:
        ValueError: If the version format is invalid.
    """
    match: Match[str] | None = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")

    major, minor = map(int, match.groups()[:2])
    return major > 0 or (major == 0 and minor >= 12)


def get_open_cmd() -> str:
    """Gets the OS-specific command to open a URL.
    Checks for the availability of 'xdg-open' or 'open'. Exits if neither is found.
    Returns:
        str: The command used to open URLs ('xdg-open' or 'open').
    """
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


def run_process(commands: list[str]) -> str:
    """Runs a system command and returns its first line of output.
    Args:
        commands (list[str]): The command and its arguments as a list of strings.
    Returns:
        str: The first line of the command's stdout or stderr. Defaults to an empty string.
    """
    result = subprocess.run(commands, capture_output=True, text=True)
    result_msg: str = result.stderr or result.stdout
    return result_msg.splitlines()[0] if len(result_msg) > 0 else ""


def run_nvim_cmd(lua_command: str) -> str:
    """Runs a Lua command in headless Neovim and returns the output.
    Args:
        lua_command (str): The Lua command to run in Neovim.
    Returns:
        str: The first line of the output from the Neovim command.
    """
    full_cmd: list[str] = ["nvim", "-u", "NONE", "-c", lua_command, "--headless", "+q"]
    return run_process(full_cmd)


def create_URI(src: str, rev: str) -> str:
    """Generates the download URI for a GitHub repository archive.
    Args:
        src (str): The base URL of the repository.
        rev (str): The commit hash, tag, or branch name.
    Returns:
        str: The generated URI for the zip archive.
    """
    return f"{src}/archive/{rev}.zip"


def ask_for_remove_path(path: Path, prompt: str) -> bool:
    """Prompts the user to remove an existing file or directory.
    If the path exists, asks the user whether to remove it. If the user
    agrees, deletes the path.
    Args:
        path (Path): The file or directory path to check and potentially remove.
        prompt (str): The prompt message to show to the user.
    Returns:
        bool: True if the path did not exist or was successfully removed.
        False if the user chose to keep it.
    """
    if path.exists():
        if input(prompt).strip().lower() in ("", "y", "yes"):
            (path.unlink() if path.is_file() else shutil.rmtree(path))
            print(f"Removed {path}")
        else:
            return False
    return True


def unzip_with_retry(
    file_path: Path, output_dir: Path, sleep_seconds_if_bad_zip=2
) -> None:
    """Extracts a zip file with a retry mechanism for bad zip errors.
    Useful when a file might still be actively downloading.
    Args:
        file_path (Path): Path to the zip file.
        output_dir (Path): Directory where contents should be extracted.
        sleep_seconds_if_bad_zip (int, optional): Seconds to wait before retrying. Defaults to 2.
    """
    for _ in range(2):
        try:
            zipfile.ZipFile(file_path).extractall(output_dir)
            return
        except zipfile.BadZipFile:
            time.sleep(sleep_seconds_if_bad_zip) if _ == 0 else None


def main() -> None:
    if not DOWNLOAD_FOLDER.exists():
        print(f"Expecting Downloads folder on: {DOWNLOAD_FOLDER}")
        sys.exit(1)

    if not CACHE_FOLDER.exists():
        CACHE_FOLDER.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(
        description="Download vim plugin packs from lock file."
    )
    parser.add_argument(
        "-u",
        "--upgrade",
        action="store_true",
        help="Do not use the cache in CACHE_FOLDER",
    )
    parser.add_argument(
        "lockfile",
        nargs="?",
        default="nvim-pack-lock.json",
        help="Path to nvim-pack-lock JSON file",
    )

    args = parser.parse_args()

    json_lock_path: Path = Path(args.lockfile)

    with json_lock_path.open("r", encoding="utf-8") as f:
        json_plugins = json.load(f)

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

    if not CACHE_FOLDER.exists():
        CACHE_FOLDER.mkdir(parents=True)

    open_cmd: str = get_open_cmd()

    plugins_dict = json_plugins["plugins"]
    if not isinstance(plugins_dict, dict):
        print(f"Failure to parse lock-file: {json_lock_path}")
        sys.exit(1)

    existing_plugins_count = sum(
        1
        for p in plugins_dict.values()
        if (NVIM_PACK_PLUGINS_PATH / p["src"].split("/")[-1]).exists()
    )

    delete_all = False
    if existing_plugins_count > 0:
        ans = (
            input(
                f"\nFound {existing_plugins_count} existing plugin folder(s). "
                "Do you want to replace (updating) them all or be asked for each one? [all/each] "
            )
            .strip()
            .lower()
        )
        if ans in ("all", "a"):
            delete_all = True

    for plugin_name, plugin_spec in plugins_dict.items():
        print(f"\n### Plugin name: {plugin_name}")
        src, rev = plugin_spec["src"], plugin_spec["rev"]
        repo_name = src.split("/")[-1]
        uri: str = create_URI(src, rev)

        destination_folder = NVIM_PACK_PLUGINS_PATH / repo_name
        if destination_folder.exists():
            if delete_all:
                (
                    destination_folder.unlink()
                    if destination_folder.is_file()
                    else shutil.rmtree(destination_folder)
                )
                print(f"Removed {destination_folder}")
            else:
                ask_for_remove_path(
                    destination_folder,
                    prompt=f"\nFound the {plugin_name} already in nvim plugins path: {NVIM_PACK_PLUGINS_PATH}, should remove it? [Y/n]",
                )
            if destination_folder.exists():
                continue  # if it still exists skip this plugin download

        filepath: Path = DOWNLOAD_FOLDER / f"{repo_name}-{rev}.zip"
        cache_filepath: Path = CACHE_FOLDER / f"{repo_name}-{rev}.zip"
        if not cache_filepath.exists() and ask_for_remove_path(
            filepath,
            prompt=f"\nFound the {plugin_name} in {DOWNLOAD_FOLDER}, should remove it? [Y/n] ",
        ):
            run_process([open_cmd, uri])
            print(
                f"\nDownloading {plugin_name} waiting for it under {DOWNLOAD_FOLDER} with filename: {filepath}"
            )

        while True:
            if filepath.is_file():
                shutil.move(filepath, cache_filepath)
            if cache_filepath.exists():
                unzip_with_retry(cache_filepath, NVIM_PACK_PLUGINS_PATH)
                extracted_plugin_folder_path: Path = (
                    NVIM_PACK_PLUGINS_PATH / filepath.stem
                )
                if extracted_plugin_folder_path.exists():
                    shutil.move(
                        extracted_plugin_folder_path, NVIM_PACK_PLUGINS_PATH / repo_name
                    )
                break
            time.sleep(SECONDS_TO_CHECK_FOR_DOWNLOAD_FILES)


if __name__ == "__main__":
    main()
