"""Nuitka 机器码编译与便携包绿色分发自动化脚本。

将 PySide6 应用程序编译为机器码二进制文件，
防止明文源码泄露，并组装内置 tools/ 工具链至绿色发布包。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union


def build_command(
    entry_point: Union[str, Path] = "app/main.py",
    output_dir: Union[str, Path] = "dist",
    output_filename: str = "AssetSplitter.exe",
    assume_yes: bool = True,
) -> List[str]:
    """组装 Nuitka 编译命令行参数列表。

    严格使用 List[str] 传参，避免 shell 注入风险。
    """
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--windows-disable-console",
        "--enable-plugin=pyside6",
    ]
    if assume_yes:
        cmd.append("--assume-yes-for-downloads")

    cmd.extend([
        f"--output-dir={output_dir}",
        f"--output-filename={output_filename}",
        str(entry_point),
    ])
    return cmd


def verify_no_source_leak(
    package_dir: Union[str, Path],
    raise_on_error: bool = False,
) -> bool:
    """递归扫描目标分发包目录，确保绝不包含任何 .py 或 .pyw 源码明文文件。"""
    pkg_path = Path(package_dir).resolve()
    if not pkg_path.is_dir():
        if raise_on_error:
            raise FileNotFoundError(f"发布包目录不存在或不是目录: {pkg_path}")
        return False

    leaks: List[Path] = []
    for pattern in ("*.py", "*.pyw"):
        for item in pkg_path.rglob(pattern):
            if item.is_file():
                leaks.append(item)

    if leaks:
        leak_files_str = ", ".join(str(p.relative_to(pkg_path)) for p in leaks[:10])
        err_msg = (
            f"安全合规校验失败：检测到源码泄漏！发布包中残留 {len(leaks)} 个 Python 源码文件！\n"
            f"残留文件示例: {leak_files_str}"
        )
        if raise_on_error:
            raise RuntimeError(err_msg)
        return False

    return True


def assemble_portable_package(
    dist_dir: Union[str, Path],
    tools_dir: Union[str, Path],
    output_dir: Union[str, Path],
) -> Path:
    """将 Nuitka 编译产物目录规范化重组为绿色免安装发布包，并集成 tools/ 工具链。

    Args:
        dist_dir: Nuitka 产物目录（例如 dist/main.dist 或 dist）
        tools_dir: 内置外部工具链目录（包含 ffmpeg.exe, ffprobe.exe）
        output_dir: 目标便携包输出目录（例如 dist/AssetSplitter_Portable）

    Returns:
        Path: 规范化后的便携包目录
    """
    src_dist = Path(dist_dir).resolve()
    if not src_dist.exists():
        raise FileNotFoundError(f"编译产物目录不存在: {src_dist}")

    # 如果传入的是外层目录且自身不是 .dist 目录，自动搜寻内部最新的 .dist 目录
    if not src_dist.name.endswith(".dist") and not (src_dist / "AssetSplitter.exe").is_file():
        candidates = sorted(src_dist.glob("*.dist"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError(f"在 {src_dist} 中未找到任何 Nuitka 产物目录 (*.dist)！")
        src_dist = candidates[0]

    target_portable = Path(output_dir).resolve()
    target_portable.parent.mkdir(parents=True, exist_ok=True)

    # 若目标便携包目录已存在且非源目录，清理以保证干净的打包环境
    if target_portable.exists() and target_portable != src_dist:
        shutil.rmtree(target_portable)

    # 复制 Nuitka 编译产物
    if target_portable != src_dist:
        shutil.copytree(src_dist, target_portable)

    # 规范化可执行文件名称
    expected_exe = target_portable / "AssetSplitter.exe"
    if not expected_exe.is_file():
        # 如果 Nuitka 输出的是 main.exe，自动重命名为 AssetSplitter.exe
        fallback_exe = target_portable / "main.exe"
        if fallback_exe.is_file():
            fallback_exe.rename(expected_exe)

    # 集成 tools/ 工具链
    src_tools = Path(tools_dir).resolve()
    if not src_tools.is_dir():
        raise FileNotFoundError(f"内置外部工具目录不存在: {src_tools}")

    target_tools = target_portable / "tools"
    if target_tools.exists():
        shutil.rmtree(target_tools)
    shutil.copytree(src_tools, target_tools)

    return target_portable


def run_compilation(
    entry_point: Union[str, Path],
    dist_dir: Union[str, Path],
    output_filename: str = "AssetSplitter.exe",
) -> None:
    """执行 Nuitka 独立编译。使用 List[str] 避免 shell 注入风险，显式锁定工作目录 cwd。"""
    project_root = Path(__file__).resolve().parent.parent
    cmd = build_command(entry_point, dist_dir, output_filename, assume_yes=True)
    print(f"[*] 执行编译命令: {' '.join(cmd)}")

    # 传递环境变量并设置项目根目录 PYTHONPATH，完全遵从系统现有环境变量
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{project_root};{existing_pp}" if existing_pp else str(project_root)

    result = subprocess.run(cmd, env=env, cwd=str(project_root), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Nuitka 编译失败，退出码: {result.returncode}")


def main() -> int:
    """编译与绿色打包主入口。"""
    project_root = Path(__file__).resolve().parent.parent
    entry_point = project_root / "app" / "main.py"
    dist_dir = project_root / "dist"
    tools_dir = project_root / "tools"
    portable_dir = dist_dir / "AssetSplitter_Portable"

    print("==================================================")
    print("AssetSplitter - Nuitka 机器码编译与便携包生成")
    print("==================================================")

    # 1. 执行 Nuitka 机器码编译
    run_compilation(entry_point, dist_dir, "AssetSplitter.exe")

    # 2. 组装绿色便携发布包
    print(f"[*] 组装绿色便携发布包至: {portable_dir}")
    assemble_portable_package(dist_dir, tools_dir, portable_dir)

    # 3. 安全扫描：防止明文源码泄露
    print("[*] 正在扫描源码泄露风险...")
    verify_no_source_leak(portable_dir, raise_on_error=True)
    print("[+] 源码安全扫描通过，未检测到任何 .py 明文源代码。")

    # 4. 验证内置工具完整性与可用性
    ffmpeg_exe = portable_dir / "tools" / "ffmpeg.exe"
    ffprobe_exe = portable_dir / "tools" / "ffprobe.exe"
    if not ffmpeg_exe.is_file() or not ffprobe_exe.is_file():
        raise FileNotFoundError("便携包内 tools/ 工具不完整！")

    proc_ffmpeg = subprocess.run([str(ffmpeg_exe), "-version"], capture_output=True, check=False)
    if proc_ffmpeg.returncode != 0:
        raise RuntimeError(f"内置 ffmpeg.exe 运行验证失败: {proc_ffmpeg.stderr.decode('utf-8', errors='ignore')}")

    proc_ffprobe = subprocess.run([str(ffprobe_exe), "-version"], capture_output=True, check=False)
    if proc_ffprobe.returncode != 0:
        raise RuntimeError(f"内置 ffprobe.exe 运行验证失败: {proc_ffprobe.stderr.decode('utf-8', errors='ignore')}")

    print("[+] 内置 ffmpeg.exe 与 ffprobe.exe 验证通过。")

    print(f"[SUCCESS] 绿色便携发布包构建成功: {portable_dir}")
    return 0


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    # 若在非虚拟环境被调用，自动转发至虚拟环境的 python
    if venv_python.is_file() and Path(sys.executable).resolve() != venv_python.resolve():
        print(f"[*] 切换至虚拟环境 Python 执行: {venv_python}")
        proc = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(proc.returncode)
    sys.exit(main())
