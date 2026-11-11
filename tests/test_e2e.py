"""端到端自动化测试集 (End-to-End Tests)。

验证系统在真实外部工具 ffmpeg/ffprobe 存在下的全链路执行：
1. 图像按 1/2、1/3、1/4 比例分割并上下拼接，检验输出分辨率与有效性。
2. 视频（含音轨）分割拼接，检验输出音画完整性、规格与时长。
3. 奇数宽高素材容错与偶数对齐机制验证。
4. MainWindow GUI 拖拽入队、设置自定义输出目录、多任务顺序处理到完成状态的全流程验证。
"""

from pathlib import Path
import subprocess

import pytest

from app.core.pipeline import PipelineBuilder
from app.core.probe import MediaProbe
from app.ui.main_window import MainWindow

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
FFMPEG_BIN = str(TOOLS_DIR / "ffmpeg.exe")
FFPROBE_BIN = str(TOOLS_DIR / "ffprobe.exe")


def test_e2e_image_ratios(tmp_path: Path) -> None:
    """测试 1920x1080 图像在 1/2、1/3、1/4 分割拼接下的端到端流程。"""
    probe = MediaProbe(ffprobe_bin=FFPROBE_BIN)
    img_in = tmp_path / "source_1920x1080.png"

    # 动态生成 1920x1080 测试图片
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1920x1080:d=1",
            "-frames:v",
            "1",
            str(img_in),
        ],
        check=True,
        capture_output=True,
    )

    in_info = probe.probe(img_in)
    assert in_info is not None
    assert in_info.width == 1920
    assert in_info.height == 1080
    assert in_info.is_video is False

    expected_resolutions = {
        2: (960, 2160),
        3: (640, 3240),
        4: (480, 4320),
    }

    for ratio, (expected_w, expected_h) in expected_resolutions.items():
        out_img = PipelineBuilder.generate_output_path(img_in, ratio, output_dir=tmp_path)
        cmd = PipelineBuilder.build_command(
            ffmpeg_bin=FFMPEG_BIN,
            input_path=str(img_in),
            output_path=str(out_img),
            orig_w=in_info.width,
            orig_h=in_info.height,
            n=ratio,
            is_video=in_info.is_video,
            has_audio=in_info.has_audio,
        )

        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"FFmpeg failed with: {res.stderr}"
        assert out_img.exists()
        assert out_img.stat().st_size > 0

        out_info = probe.probe(out_img)
        assert out_info is not None
        assert out_info.width == expected_w
        assert out_info.height == expected_h
        assert out_info.is_video is False


def test_e2e_video_split_stitch_with_audio(tmp_path: Path) -> None:
    """测试 1920x1080 含真实音频（aac 44100Hz）视频在 1/2 分割拼接下的端到端流程。"""
    probe = MediaProbe(ffprobe_bin=FFPROBE_BIN)
    vid_in = tmp_path / "source_audio_2s.mp4"

    # 动态生成一段含真实音轨（aac 44100Hz）的 1920x1080 视频（时长 2s）
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1920x1080:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=44100",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            str(vid_in),
        ],
        check=True,
        capture_output=True,
    )

    in_info = probe.probe(vid_in)
    assert in_info is not None
    assert in_info.width == 1920
    assert in_info.height == 1080
    assert in_info.is_video is True
    assert in_info.has_audio is True
    assert in_info.duration >= 1.9

    out_vid = PipelineBuilder.generate_output_path(vid_in, 2, output_dir=tmp_path)
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin=FFMPEG_BIN,
        input_path=str(vid_in),
        output_path=str(out_vid),
        orig_w=in_info.width,
        orig_h=in_info.height,
        n=2,
        is_video=in_info.is_video,
        has_audio=in_info.has_audio,
    )

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"FFmpeg failed with: {res.stderr}"
    assert out_vid.exists()
    assert out_vid.stat().st_size > 0

    out_info = probe.probe(out_vid)
    assert out_info is not None
    assert out_info.width == 960
    assert out_info.height == 2160
    assert out_info.duration >= 1.9
    assert out_info.has_audio is True
    assert out_info.is_video is True


def test_e2e_odd_resolution_tolerance(tmp_path: Path) -> None:
    """测试奇数分辨率（1921x1081）视频素材在 1/3 比例下的偶数对齐与编码容错。"""
    probe = MediaProbe(ffprobe_bin=FFPROBE_BIN)
    vid_odd = tmp_path / "source_odd_1921x1081.mp4"

    # 生成具有奇数分辨率的素材 (使用 yuv444p 以便 libx264 编码支持奇数原始尺寸)
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1921x1081:rate=25",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv444p",
            str(vid_odd),
        ],
        check=True,
        capture_output=True,
    )

    in_info = probe.probe(vid_odd)
    assert in_info is not None
    assert in_info.width == 1921
    assert in_info.height == 1081
    assert in_info.is_video is True

    # 执行 1/3 比例视频分割拼接
    out_vid = PipelineBuilder.generate_output_path(vid_odd, 3, output_dir=tmp_path)
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin=FFMPEG_BIN,
        input_path=str(vid_odd),
        output_path=str(out_vid),
        orig_w=in_info.width,
        orig_h=in_info.height,
        n=3,
        is_video=in_info.is_video,
        has_audio=in_info.has_audio,
    )

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"FFmpeg failed with: {res.stderr}"
    assert out_vid.exists()
    assert out_vid.stat().st_size > 0

    out_info = probe.probe(out_vid)
    assert out_info is not None
    # 1921 // 3 // 2 * 2 = 640
    assert out_info.width == 640
    # 1081 // 2 * 2 * 3 = 1080 * 3 = 3240
    assert out_info.height == 3240
    assert out_info.width % 2 == 0
    assert out_info.height % 2 == 0
    assert out_info.is_video is True


def test_e2e_full_gui_flow(qtbot, tmp_path: Path) -> None:
    """测试完整 GUI 交互链路：添加图片与视频任务、设置自定义目录、启动并等待完成。"""
    win = MainWindow()
    qtbot.addWidget(win)

    src_dir = tmp_path / "inputs"
    out_dir = tmp_path / "outputs"
    src_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    img_path = src_dir / "gui_image.png"
    vid_path = src_dir / "gui_video.mp4"

    # 生成真实测试图片
    subprocess.run(
        [
            win.ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=1920x1080:d=1",
            "-frames:v",
            "1",
            str(img_path),
        ],
        check=True,
        capture_output=True,
    )

    # 生成真实测试视频 (1s 时长以保证执行迅速且指标真实)
    subprocess.run(
        [
            win.ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1920x1080:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            str(vid_path),
        ],
        check=True,
        capture_output=True,
    )

    # 设置自定义输出目录
    win.radio_out_custom.setChecked(True)
    win.edit_custom_dir.setText(str(out_dir))

    # 模拟文件拖拽添加
    win.on_files_dropped([img_path, vid_path])

    # 验证表格正确列出 2 个任务，初始状态正常
    assert win.task_table.rowCount() == 2
    task_id_0 = win.task_table.get_task_id_by_row(0)
    task_id_1 = win.task_table.get_task_id_by_row(1)
    assert task_id_0 is not None
    assert task_id_1 is not None

    status_0 = win.task_table.get_task_status_text(task_id_0)
    status_1 = win.task_table.get_task_status_text(task_id_1)
    assert status_0 == "等待中"
    assert status_1 == "等待中"
    assert win.btn_start.isEnabled()

    # 模拟点击开始处理
    win.btn_start.click()

    # 使用 qtbot.waitUntil 等待批处理全部完成
    qtbot.waitUntil(lambda: not win._is_processing, timeout=15000)
    if win.worker and win.worker.isRunning():
        win.worker.wait(5000)

    # 预期输出文件路径 (默认 1/2 分割)
    expected_img_out = out_dir / f"{img_path.stem}_vsplit_1_2.png"
    expected_vid_out = out_dir / f"{vid_path.stem}_vsplit_1_2.mp4"

    # 断言磁盘上生成的 2 个输出文件均存在且大小有效
    assert expected_img_out.exists(), f"未生成输出图片: {expected_img_out}"
    assert expected_img_out.stat().st_size > 0
    assert expected_vid_out.exists(), f"未生成输出视频: {expected_vid_out}"
    assert expected_vid_out.stat().st_size > 0

    # 断言表格中 2 个任务状态全部为已完成
    status_0_done = win.task_table.get_task_status_text(task_id_0)
    status_1_done = win.task_table.get_task_status_text(task_id_1)
    assert "已完成" in status_0_done or "100%" in status_0_done
    assert "已完成" in status_1_done or "100%" in status_1_done

    item_0 = win.task_table.item(0, win.task_table.COL_STATUS)
    item_1 = win.task_table.item(1, win.task_table.COL_STATUS)
    assert item_0 is not None and ("已完成" in item_0.text() or "100%" in item_0.text())
    assert item_1 is not None and ("已完成" in item_1.text() or "100%" in item_1.text())

    # 校验产物规格完整性
    probe = MediaProbe(ffprobe_bin=win.ffprobe_bin)
    img_info = probe.probe(expected_img_out)
    assert img_info is not None
    assert img_info.width == 960
    assert img_info.height == 2160
    assert img_info.is_video is False

    vid_info = probe.probe(expected_vid_out)
    assert vid_info is not None
    assert vid_info.width == 960
    assert vid_info.height == 2160
    assert vid_info.is_video is True
    assert vid_info.has_audio is True

    win.close()
