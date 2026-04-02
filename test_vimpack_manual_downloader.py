import json
import sys
import importlib.util
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Dynamically import the script to avoid syntax issues with hyphens in the filename
script_path = Path(__file__).parent / "vimpack-manual-downloader.py"
spec = importlib.util.spec_from_file_location("vimpack_manual_downloader", script_path)
downloader = importlib.util.module_from_spec(spec)
sys.modules["vimpack_manual_downloader"] = downloader
spec.loader.exec_module(downloader)

def test_is_version_at_least_0_12():
    assert downloader.is_version_at_least_0_12("NVIM v0.12.0") is True
    assert downloader.is_version_at_least_0_12("NVIM v0.13.1") is True
    assert downloader.is_version_at_least_0_12("NVIM v1.0.0") is True
    assert downloader.is_version_at_least_0_12("NVIM v0.11.9") is False
    assert downloader.is_version_at_least_0_12("NVIM v0.9.0") is False

    with pytest.raises(ValueError):
        downloader.is_version_at_least_0_12("invalid version")

@patch("vimpack_manual_downloader.shutil.which")
def test_get_open_cmd_xdg_open(mock_which):
    mock_which.side_effect = lambda cmd: "/usr/bin/xdg-open" if cmd == "xdg-open" else None
    assert downloader.get_open_cmd() == "xdg-open"

@patch("vimpack_manual_downloader.shutil.which")
def test_get_open_cmd_open(mock_which):
    mock_which.side_effect = lambda cmd: "/usr/bin/open" if cmd == "open" else None
    assert downloader.get_open_cmd() == "open"

@patch("vimpack_manual_downloader.shutil.which")
def test_get_open_cmd_none(mock_which):
    mock_which.return_value = None
    with pytest.raises(SystemExit):
        downloader.get_open_cmd()

def test_create_URI():
    src = "https://github.com/folke/snacks.nvim"
    rev = "ad9ede6a9cddf16cedbd31b8932d6dcdee9b716e"
    expected = "https://github.com/folke/snacks.nvim/archive/ad9ede6a9cddf16cedbd31b8932d6dcdee9b716e.zip"
    assert downloader.create_URI(src, rev) == expected

@patch("vimpack_manual_downloader.subprocess.run")
def test_run_process(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "output\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    res = downloader.run_process(["echo", "test"])
    assert res == "output"
    mock_run.assert_called_once_with(["echo", "test"], capture_output=True, text=True)

@patch("vimpack_manual_downloader.subprocess.run")
def test_run_nvim_cmd(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "/my/nvim/data"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    res = downloader.run_nvim_cmd("lua print('foo')")
    assert res == "/my/nvim/data"
    mock_run.assert_called_once_with(["nvim", "-c", "lua print('foo')", "--headless", "+q"], capture_output=True, text=True)

@patch("vimpack_manual_downloader.input")
def test_ask_for_remove_path_yes(mock_input, tmp_path):
    mock_input.return_value = "yes"
    test_file = tmp_path / "test.txt"
    test_file.touch()
    
    assert downloader.ask_for_remove_path(test_file, "Remove?") is True
    assert not test_file.exists()

@patch("vimpack_manual_downloader.input")
def test_ask_for_remove_path_no(mock_input, tmp_path):
    mock_input.return_value = "n"
    test_file = tmp_path / "test.txt"
    test_file.touch()
    
    assert downloader.ask_for_remove_path(test_file, "Remove?") is False
    assert test_file.exists()

def test_ask_for_remove_path_not_exists(tmp_path):
    test_file = tmp_path / "nonexistent.txt"
    assert downloader.ask_for_remove_path(test_file, "Remove?") is True

@patch("vimpack_manual_downloader.zipfile.ZipFile")
def test_unzip_with_retry_success(mock_zipfile, tmp_path):
    mock_zip_instance = MagicMock()
    mock_zipfile.return_value = mock_zip_instance
    
    downloader.unzip_with_retry(Path("dummy.zip"), tmp_path)
    mock_zip_instance.extractall.assert_called_once_with(tmp_path)

@patch("vimpack_manual_downloader.time.sleep")
@patch("vimpack_manual_downloader.zipfile.ZipFile")
def test_unzip_with_retry_bad_zip_retry(mock_zipfile, mock_sleep, tmp_path):
    mock_zip_instance = MagicMock()
    mock_zipfile.side_effect = [downloader.zipfile.BadZipFile, mock_zip_instance]
    
    downloader.unzip_with_retry(Path("dummy.zip"), tmp_path, sleep_seconds_if_bad_zip=0)
    assert mock_zip_instance.extractall.call_count == 1
    mock_sleep.assert_called_once()

def test_read_lockfile_smoke_test():
    # Verify the lockfile structure can be parsed successfully.
    lockfile_path = Path(__file__).parent / "nvim-pack-lock.json"
    with lockfile_path.open("r", encoding="utf-8") as f:
        plugins_dict = json.load(f)
    assert "plugins" in plugins_dict
    assert "blink.cmp" in plugins_dict["plugins"]
    assert "src" in plugins_dict["plugins"]["blink.cmp"]
    assert "rev" in plugins_dict["plugins"]["blink.cmp"]
