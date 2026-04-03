# Vimpack Manual Downloader

A python script to manually download and extract Neovim plugins from an `nvim-pack-lock.json` file. It reads the plugin details (source and revision) from the lock file, and then downloads the zip archives to your `Downloads` folder using your system's default browser (`open` or `xdg-open`). Finally, it automatically extracts these archives into Neovim's data path (`stdpath('data')/site/pack/core/opt`).

## Prerequisites

- Python 3
- Neovim `>= 0.12` installed and accessible from your PATH.
- `xdg-open` (for Linux) or `open` (for macOS) installed on your system.

## Usage

By default, the script looks for an `nvim-pack-lock.json` file in the current directory:

```bash
python3 vimpack-manual-downloader.py
```

You can also specify a custom path to a different lockfile:

```bash
python3 vimpack-manual-downloader.py /path/to/custom-lock.json
```

## How It Works

1. **Parses the Lockfile**: Reads the JSON lock file to extract plugin names, github sources, and revisions (commits).
2. **Validates Plugins**: Checks if the plugin is already present in your Neovim pack data folder (e.g., `~/.local/share/nvim/site/pack/core/opt`). If found, it will prompt you if you want to replace it.
3. **Downloads**: Triggers a download of the repository's `.zip` archive via `xdg-open` or `open`.
4. **Polls & Extracts**: Monitors your Downloads folder until the zip file is fully downloaded, then unzips it into the Neovim pack directory with retry mechanisms.
