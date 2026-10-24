"""Register this tested local adapter without rewriting unrelated Codex settings."""
from datetime import datetime
import argparse
import os
from pathlib import Path
import shutil
import sys
import tomllib


def install_skill(directory: Path):
    source = Path(__file__).resolve().parent / "skills" / "vista-computer-use"
    target = directory / "skills" / source.name
    def packaged_files(folder):
        return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}}

    source_files = packaged_files(source)
    if not source_files:
        raise SystemExit("Bundled vista-computer-use skill is missing")
    if target.exists():
        target_files = packaged_files(target)
        if source_files == target_files:
            print(f"Skill already installed: {target}")
            return
        backup = directory / "skill-backups" / (source.name + "-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        shutil.copytree(target, backup)
        print(f"Skill backup: {backup}")
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    print(f"Installed skill: {target}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-skill", action="store_true", help="Install the matching vista-computer-use skill")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Windows is required")
    # Fail before changing configuration if dependencies are unavailable.
    import mcp  # noqa: F401
    import pyautogui  # noqa: F401
    from PIL import Image  # noqa: F401

    directory = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = directory / "config.toml"
    directory.mkdir(parents=True, exist_ok=True)
    original = config.read_text(encoding="utf-8") if config.exists() else ""
    parsed = tomllib.loads(original)
    server = Path(__file__).resolve().with_name("server.py")
    interpreter = Path(sys.executable).resolve()
    entry = {
        "command": str(interpreter), "args": [str(server)],
        "enabled": True, "startup_timeout_sec": 30, "tool_timeout_sec": 60,
    }
    previous = parsed.get("mcp_servers", {}).get("vista_desktop")
    if previous is not None:
        if previous == entry:
            print("vista_desktop is already configured correctly")
            if args.with_skill:
                install_skill(directory)
            return
        raise SystemExit("Existing vista_desktop configuration differs; inspect it before changing it")
    addition = (
        "\n\n[mcp_servers.vista_desktop]\n"
        f"command = '{interpreter}'\n"
        f"args = ['{server}']\n"
        "enabled = true\nstartup_timeout_sec = 30\ntool_timeout_sec = 60\n"
    )
    updated = original + addition
    assert tomllib.loads(updated)["mcp_servers"]["vista_desktop"] == entry
    if config.exists():
        backup = config.with_name("config.toml.before-vista-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".bak")
        shutil.copy2(config, backup)
        print(f"Backup: {backup}")
    temporary = config.with_name("config.toml.vista-tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(config)
    print(f"Configured vista_desktop in {config}")
    if args.with_skill:
        install_skill(directory)
    print("Restart Codex to load the new MCP server.")


if __name__ == "__main__":
    main()
