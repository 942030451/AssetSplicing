"""Nuitka 编译与便携包自动化构建测试。"""

import sys
from pathlib import Path
import pytest

from build.build_nuitka import (
    build_command,
    verify_no_source_leak,
    assemble_portable_package,
)


def test_build_command_generation():
    """验证 Nuitka 编译命令参数完整性与格式。"""
    entry_point = "app/main.py"
    output_dir = "dist"
    output_filename = "AssetSplitter.exe"

    cmd = build_command(entry_point, output_dir, output_filename)

    assert isinstance(cmd, list)
    assert all(isinstance(arg, str) for arg in cmd)
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "nuitka"]
    assert "--standalone" in cmd
    assert "--windows-disable-console" in cmd
    assert "--enable-plugin=pyside6" in cmd
    assert f"--output-dir={output_dir}" in cmd
    assert f"--output-filename={output_filename}" in cmd
    assert entry_point in cmd


def test_verify_no_source_leak_clean(tmp_path: Path):
    """验证全为二进制/资源文件时源码泄漏检查返回 True。"""
    clean_dir = tmp_path / "clean_package"
    clean_dir.mkdir()
    (clean_dir / "AssetSplitter.exe").write_bytes(b"MZ\x90\x00")
    (clean_dir / "python311.dll").write_bytes(b"\x00\x01\x02")
    sub_dir = clean_dir / "PySide6"
    sub_dir.mkdir()
    (sub_dir / "QtCore.pyd").write_bytes(b"\x00\x00")
    (sub_dir / "package.json").write_text("{}", encoding="utf-8")

    assert verify_no_source_leak(clean_dir) is True


def test_verify_no_source_leak_with_py(tmp_path: Path):
    """验证存在 .py 源代码时源码泄漏检查返回 False 或正确抛出异常。"""
    leak_dir = tmp_path / "leak_package"
    leak_dir.mkdir()
    (leak_dir / "AssetSplitter.exe").write_bytes(b"MZ\x90\x00")
    sub_dir = leak_dir / "app"
    sub_dir.mkdir()
    (sub_dir / "secret.py").write_text("print('secret')", encoding="utf-8")

    assert verify_no_source_leak(leak_dir) is False

    with pytest.raises(RuntimeError, match="源码泄漏"):
        verify_no_source_leak(leak_dir, raise_on_error=True)


def test_verify_no_source_leak_nonexistent(tmp_path: Path):
    """验证目录不存在时的安全处理。"""
    non_existent = tmp_path / "does_not_exist"
    assert verify_no_source_leak(non_existent) is False

    with pytest.raises(FileNotFoundError):
        verify_no_source_leak(non_existent, raise_on_error=True)


def test_assemble_portable_package(tmp_path: Path):
    """验证便携包重整逻辑及内置 tools 复制。"""
    dist_root = tmp_path / "dist"
    nuitka_out = dist_root / "main.dist"
    nuitka_out.mkdir(parents=True)
    (nuitka_out / "AssetSplitter.exe").write_bytes(b"EXE_BINARY")
    (nuitka_out / "PySide6.QtCore.pyd").write_bytes(b"PYD_BINARY")

    tools_src = tmp_path / "tools"
    tools_src.mkdir()
    (tools_src / "ffmpeg.exe").write_bytes(b"FFMPEG_BINARY")
    (tools_src / "ffprobe.exe").write_bytes(b"FFPROBE_BINARY")
    (tools_src / "README.md").write_text("tools readme", encoding="utf-8")

    portable_output = dist_root / "AssetSplitter_Portable"

    # 执行重组
    result_path = assemble_portable_package(
        dist_dir=nuitka_out,
        tools_dir=tools_src,
        output_dir=portable_output,
    )

    assert result_path == portable_output
    assert (portable_output / "AssetSplitter.exe").is_file()
    assert (portable_output / "PySide6.QtCore.pyd").is_file()
    assert (portable_output / "tools" / "ffmpeg.exe").is_file()
    assert (portable_output / "tools" / "ffprobe.exe").is_file()
    assert (portable_output / "tools" / "README.md").is_file()
    assert verify_no_source_leak(portable_output) is True
