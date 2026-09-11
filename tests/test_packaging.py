"""Check the AppImage wrapper using a local tool stub, without network access."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_appimage_wraps_actual_nested_bundle_and_preserves_arguments(tmp_path):
    shutil.copytree(ROOT / "packaging", tmp_path / "packaging")
    (tmp_path / "framemill/assets").mkdir(parents=True)
    shutil.copy(ROOT / "framemill/assets/icon.svg", tmp_path / "framemill/assets/icon.svg")
    bundle = tmp_path / "build/linux/x64/release/bundle"
    bundle.mkdir(parents=True)
    binary = bundle / "framemill"
    binary.write_text('#!/bin/sh\nprintf "%s" "$1"\n')
    binary.chmod(0o755)
    tool = tmp_path / "tool"
    tool.write_text(
        '#!/bin/sh\nset -eu\n'
        'test -s "$1/framemill.svg"\n'
        'test "$("$1/AppRun" "argument with spaces")" = "argument with spaces"\n'
        'touch "$2"\n'
    )
    tool.chmod(0o755)
    result = subprocess.run(
        ["bash", "packaging/build_appimage.sh"], cwd=tmp_path,
        env={**os.environ, "APPIMAGETOOL": str(tool), "BUNDLE_DIR": str(bundle)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "dist/framemill-x86_64.AppImage").exists()


def test_appimage_rejects_non_bundle_directory(tmp_path):
    bundle = tmp_path / "not-a-bundle"
    bundle.mkdir()
    result = subprocess.run(
        ["bash", str(ROOT / "packaging/build_appimage.sh")], cwd=tmp_path,
        env={**os.environ, "BUNDLE_DIR": str(bundle)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "must contain an executable named framemill" in result.stderr
