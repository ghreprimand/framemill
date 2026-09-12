"""Static checks on the packaging scripts and release workflow.

The AppImage build itself needs network access (it fetches a manylinux Python
base and pip dependencies), so it runs in CI rather than here. These tests keep
the script and workflow honest without a network: valid shell syntax and the
expected build steps and outputs.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_appimage_script_has_valid_bash_syntax():
    script = ROOT / "packaging/build_appimage.sh"
    assert script.exists()
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_appimage_script_uses_python_appimage_and_names_output():
    text = (ROOT / "packaging/build_appimage.sh").read_text()
    assert "python-appimage build app" in text
    assert "requirements.txt" in text
    assert 'OUT_DIR="dist"' in text
    assert "framemill-x86_64.AppImage" in text
    # The bundled entrypoint must launch the GUI module.
    assert "framemill.app" in text


def test_release_workflow_publishes_pypi_and_appimage():
    wf = (ROOT / ".github/workflows/release.yml").read_text()
    # Trusted Publishing to PyPI (OIDC), no stored token.
    assert "pypa/gh-action-pypi-publish" in wf
    assert "id-token: write" in wf
    assert "environment: pypi" in wf
    # Wheel + sdist attached to the GitHub release.
    assert "softprops/action-gh-release" in wf
    # Best-effort AppImage.
    assert "build_appimage.sh" in wf


def test_test_workflow_builds_distributions():
    wf = (ROOT / ".github/workflows/build.yml").read_text()
    assert "python -m build" in wf
    assert "pytest" in wf
