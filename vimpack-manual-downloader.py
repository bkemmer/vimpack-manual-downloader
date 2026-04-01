import json
from pathlib import Path

json_path: Path = Path("nvim-pack-lock.json")
with json_path.open("r", encoding="utf-8") as f:
    plugins_dict = json.load(f)


def create_URI(src: str, rev: str) -> str:
    return f"{src}/archive/{rev}.zip"


for plugin_name, plugin_spec in plugins_dict["plugins"].items():
    print(f"Plugin name: {plugin_name}")
    print(create_URI(plugin_spec["src"], plugin_spec["rev"]))
    print()
    # print(plugin["src"])
    # print(plugin_spec)
