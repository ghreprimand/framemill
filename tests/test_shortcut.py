"""Desktop launcher helpers: .desktop body, PATH lookup, Linux install isolation."""
from pathlib import Path

import pytest

from framemill import cli, shortcut


def test_linux_desktop_entry_fields_and_quoting():
    body = shortcut.linux_desktop_entry("/opt/framemill-gui")
    assert body.startswith("[Desktop Entry]\n")
    assert "Type=Application\n" in body
    assert "Name=framemill\n" in body
    assert "Exec=/opt/framemill-gui\n" in body
    assert "Icon=framemill\n" in body
    assert "Terminal=false\n" in body
    assert "Categories=Graphics;Development;2DGraphics;\n" in body
    quoted = shortcut.linux_desktop_entry("/home/me/My Apps/framemill")
    assert 'Exec="/home/me/My Apps/framemill"\n' in quoted


def test_resolve_gui_target_prefers_gui_then_cli(monkeypatch):
    monkeypatch.setattr(
        shortcut.shutil, "which",
        lambda name: {"framemill-gui": "/bin/framemill-gui", "framemill": "/bin/framemill"}.get(name),
    )
    assert shortcut.resolve_gui_target() == Path("/bin/framemill-gui")
    monkeypatch.setattr(
        shortcut.shutil, "which",
        lambda name: "/bin/framemill" if name == "framemill" else None,
    )
    assert shortcut.resolve_gui_target() == Path("/bin/framemill")


def test_resolve_gui_target_missing_is_clear(monkeypatch):
    monkeypatch.setattr(shortcut.shutil, "which", lambda name: None)
    with pytest.raises(shortcut.ShortcutError, match="framemill-gui"):
        shortcut.resolve_gui_target()


def test_linux_install_and_uninstall_use_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(shortcut.sys, "platform", "linux")
    monkeypatch.setattr(
        shortcut.shutil, "which",
        lambda name: "/opt/bin/framemill-gui" if name == "framemill-gui" else None,
    )
    monkeypatch.setattr(shortcut, "_refresh_linux_database", lambda *_a, **_k: None)
    created = shortcut.install_shortcut()
    desktop = tmp_path / ".local" / "share" / "applications" / "framemill.desktop"
    icon = tmp_path / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "framemill.svg"
    assert created == desktop
    assert desktop.is_file()
    assert "Exec=/opt/bin/framemill-gui" in desktop.read_text(encoding="utf-8")
    assert icon.is_file()
    removed = shortcut.uninstall_shortcut()
    assert desktop in removed
    assert icon in removed
    assert not desktop.exists()
    assert not icon.exists()


def test_cli_install_shortcut_missing_target(monkeypatch):
    monkeypatch.setattr(shortcut.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as exited:
        cli.main(["install-shortcut"])
    assert exited.value.code not in (0, None)
    assert "framemill-gui" in str(exited.value)


def test_packaged_icons_exist():
    svg = shortcut.asset_file("icon.svg")
    png = shortcut.asset_file("icon.png")
    assert svg.is_file()
    assert png.is_file()
