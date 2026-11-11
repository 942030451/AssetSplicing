import subprocess
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication

from app.core.probe import MediaInfo
from app.core.worker import BatchTask, BatchProcessorThread, parse_progress_line

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
FFMPEG_BIN = str(TOOLS_DIR / "ffmpeg.exe")


def test_parse_progress_line():
    assert parse_progress_line("out_time_ms=5000000") == ("out_time_ms", 5000000)
    assert parse_progress_line("out_time_us=5000000") == ("out_time_us", 5000000)
    assert parse_progress_line("progress=continue") == ("progress", "continue")
    assert parse_progress_line("progress=end") == ("progress", "end")
    assert parse_progress_line("invalid_line") == (None, None)
    assert parse_progress_line("") == (None, None)
    assert parse_progress_line("   ") == (None, None)
    assert parse_progress_line("=value") == (None, None)
    assert parse_progress_line("key=") == ("key", "")
    assert parse_progress_line("  frame= 10  ") == ("frame", 10)


def test_batch_task_init():
    info = MediaInfo(width=1920, height=1080, duration=10.0, is_video=True, has_audio=True)
    task = BatchTask(
        task_id="t1",
        input_path=Path("input.mp4"),
        output_path=Path("output.mp4"),
        media_info=info,
        split_ratio=2,
    )
    assert task.task_id == "t1"
    assert task.input_path == Path("input.mp4")
    assert task.output_path == Path("output.mp4")
    assert task.media_info == info
    assert task.split_ratio == 2

    # 路径支持字符串自动转换
    task_str = BatchTask(
        task_id="t2",
        input_path="input.png",  # type: ignore
        output_path="output.png",  # type: ignore
        media_info=info,
        split_ratio=3,
    )
    assert isinstance(task_str.input_path, Path)
    assert isinstance(task_str.output_path, Path)


def test_worker_image_task(tmp_path, qtbot):
    # 生成测试图片 200x100
    in_img = tmp_path / "test_in.png"
    out_img = tmp_path / "test_out.png"
    subprocess.run(
        [FFMPEG_BIN, "-y", "-f", "lavfi", "-i", "color=c=blue:s=200x100:d=1", "-frames:v", "1", str(in_img)],
        check=True,
        capture_output=True,
    )

    info = MediaInfo(width=200, height=100, duration=0.0, is_video=False, has_audio=False)
    task = BatchTask(
        task_id="img_1",
        input_path=in_img,
        output_path=out_img,
        media_info=info,
        split_ratio=2,
    )

    started_ids = []
    completed_ids = []
    progress_records = []

    worker = BatchProcessorThread(ffmpeg_bin=FFMPEG_BIN, tasks=[task])
    worker.sig_task_started.connect(started_ids.append)
    worker.sig_task_completed.connect(lambda tid, path: completed_ids.append((tid, path)))
    worker.sig_task_progress.connect(lambda tid, pct: progress_records.append((tid, pct)))

    with qtbot.waitSignal(worker.sig_all_finished, timeout=10000):
        worker.start()

    assert started_ids == ["img_1"]
    assert len(completed_ids) == 1
    assert completed_ids[0][0] == "img_1"
    assert completed_ids[0][1] == str(out_img)
    assert out_img.exists()
    assert (
        ("img_1", 0.0) in progress_records and ("img_1", 100.0) in progress_records
    )


def test_worker_video_task(tmp_path, qtbot):
    # 生成 1 秒测试视频 320x240
    in_vid = tmp_path / "test_in.mp4"
    out_vid = tmp_path / "test_out.mp4"
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(in_vid),
        ],
        check=True,
        capture_output=True,
    )

    info = MediaInfo(width=320, height=240, duration=1.0, is_video=True, has_audio=False)
    task = BatchTask(
        task_id="vid_1",
        input_path=in_vid,
        output_path=out_vid,
        media_info=info,
        split_ratio=2,
    )

    started_ids = []
    completed_ids = []
    progress_values = []

    worker = BatchProcessorThread(ffmpeg_bin=FFMPEG_BIN, tasks=[task])
    worker.sig_task_started.connect(started_ids.append)
    worker.sig_task_completed.connect(lambda tid, path: completed_ids.append((tid, path)))
    worker.sig_task_progress.connect(lambda tid, pct: progress_values.append(pct))

    with qtbot.waitSignal(worker.sig_all_finished, timeout=15000):
        worker.start()

    assert started_ids == ["vid_1"]
    assert len(completed_ids) == 1
    assert out_vid.exists()
    assert 0.0 in progress_values
    assert 100.0 in progress_values
    assert any(0.0 < p < 100.0 for p in progress_values)


def test_worker_task_failure(tmp_path, qtbot):
    # 非法任务（输入文件不存在）
    non_existent = tmp_path / "non_existent.mp4"
    out_vid = tmp_path / "out_failed.mp4"
    info = MediaInfo(width=320, height=240, duration=1.0, is_video=True, has_audio=False)
    task = BatchTask(
        task_id="fail_1",
        input_path=non_existent,
        output_path=out_vid,
        media_info=info,
        split_ratio=2,
    )

    failed_records = []
    worker = BatchProcessorThread(ffmpeg_bin=FFMPEG_BIN, tasks=[task])
    worker.sig_task_failed.connect(lambda tid, err: failed_records.append((tid, err)))

    with qtbot.waitSignal(worker.sig_all_finished, timeout=10000):
        worker.start()

    assert len(failed_records) == 1
    assert failed_records[0][0] == "fail_1"
    assert len(failed_records[0][1]) > 0
    # 失败时不应产生或残留目标文件
    assert not out_vid.exists()


def test_worker_cancellation(tmp_path, qtbot):
    # 生成 3 秒测试视频以便能中途取消
    in_vid = tmp_path / "long_in.mp4"
    out_vid = tmp_path / "long_out.mp4"
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=640x480:rate=30",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(in_vid),
        ],
        check=True,
        capture_output=True,
    )

    info = MediaInfo(width=640, height=480, duration=3.0, is_video=True, has_audio=False)
    task1 = BatchTask(task_id="cancel_1", input_path=in_vid, output_path=out_vid, media_info=info, split_ratio=2)
    task2 = BatchTask(
        task_id="cancel_2",
        input_path=in_vid,
        output_path=tmp_path / "never_run.mp4",
        media_info=info,
        split_ratio=2,
    )

    started_ids = []
    failed_ids = []

    worker = BatchProcessorThread(ffmpeg_bin=FFMPEG_BIN, tasks=[task1, task2])
    worker.sig_task_started.connect(started_ids.append)
    worker.sig_task_failed.connect(lambda tid, err: failed_ids.append(tid))

    # 在收到进度信号后立即取消
    def on_progress(tid, pct):
        if pct > 0:
            worker.cancel()

    worker.sig_task_progress.connect(on_progress)

    with qtbot.waitSignal(worker.sig_all_finished, timeout=15000):
        worker.start()

    # task1 应该被 cancel 并且 task2 不应该运行
    assert "cancel_1" in started_ids
    assert "cancel_2" not in started_ids
    # 脏文件必须被清理
    assert not out_vid.exists()
    assert not (tmp_path / "never_run.mp4").exists()


def test_worker_cancel_before_start(tmp_path, qtbot):
    info = MediaInfo(width=100, height=100, duration=0.0, is_video=False, has_audio=False)
    task = BatchTask(
        task_id="t_pre_cancel",
        input_path=tmp_path / "img.png",
        output_path=tmp_path / "out.png",
        media_info=info,
        split_ratio=2,
    )

    started_ids = []
    worker = BatchProcessorThread(ffmpeg_bin=FFMPEG_BIN, tasks=[task])
    worker.sig_task_started.connect(started_ids.append)
    worker.cancel()
    worker.cancel()  # 验证多次调用 cancel 幂等安全

    with qtbot.waitSignal(worker.sig_all_finished, timeout=5000):
        worker.start()

    assert len(started_ids) == 0


def test_worker_multi_task_sequential(tmp_path, qtbot):
    # 生成 2 张图片，测试多任务队列顺序执行与信号发射
    img1_in = tmp_path / "in1.png"
    img1_out = tmp_path / "out1.png"
    img2_in = tmp_path / "in2.png"
    img2_out = tmp_path / "out2.png"
    for p in (img1_in, img2_in):
        subprocess.run(
            [FFMPEG_BIN, "-y", "-f", "lavfi", "-i", "color=c=red:s=100x100:d=1", "-frames:v", "1", str(p)],
            check=True,
            capture_output=True,
        )

    info = MediaInfo(width=100, height=100, duration=0.0, is_video=False, has_audio=False)
    t1 = BatchTask(task_id="multi_1", input_path=img1_in, output_path=img1_out, media_info=info, split_ratio=2)
    t2 = BatchTask(task_id="multi_2", input_path=img2_in, output_path=img2_out, media_info=info, split_ratio=2)

    events = []
    # 测试通过任务列表在前参数构建 BatchProcessorThread([t1, t2], FFMPEG_BIN)
    worker = BatchProcessorThread([t1, t2], FFMPEG_BIN)
    worker.sig_task_started.connect(lambda tid: events.append(("start", tid)))
    worker.sig_task_completed.connect(lambda tid, path: events.append(("done", tid)))

    with qtbot.waitSignal(worker.sig_all_finished, timeout=10000):
        worker.start()

    assert events == [
        ("start", "multi_1"),
        ("done", "multi_1"),
        ("start", "multi_2"),
        ("done", "multi_2"),
    ]
    assert img1_out.exists()
    assert img2_out.exists()


def test_worker_invalid_split_ratio_continues_next_task(tmp_path, qtbot):
    # 任务 1 包含非法 split_ratio=0 导致 PipelineBuilder.build_command 抛错
    # 任务 2 为合法任务，验证任务 1 报错后不崩溃并能继续执行任务 2
    img1_in = tmp_path / "in_err.png"
    img1_out = tmp_path / "out_err.png"
    img2_in = tmp_path / "in_ok.png"
    img2_out = tmp_path / "out_ok.png"
    for p in (img1_in, img2_in):
        subprocess.run(
            [FFMPEG_BIN, "-y", "-f", "lavfi", "-i", "color=c=green:s=100x100:d=1", "-frames:v", "1", str(p)],
            check=True,
            capture_output=True,
        )

    info = MediaInfo(width=100, height=100, duration=0.0, is_video=False, has_audio=False)
    t_err = BatchTask(task_id="t_err", input_path=img1_in, output_path=img1_out, media_info=info, split_ratio=0)
    t_ok = BatchTask(task_id="t_ok", input_path=img2_in, output_path=img2_out, media_info=info, split_ratio=2)

    failed_events = []
    completed_events = []
    worker = BatchProcessorThread(FFMPEG_BIN, [t_err, t_ok])
    worker.sig_task_failed.connect(lambda tid, err: failed_events.append((tid, err)))
    worker.sig_task_completed.connect(lambda tid, path: completed_events.append((tid, path)))

    with qtbot.waitSignal(worker.sig_all_finished, timeout=10000):
        worker.start()

    assert len(failed_events) == 1
    assert failed_events[0][0] == "t_err"
    assert "n must be greater than 0" in failed_events[0][1]

    assert len(completed_events) == 1
    assert completed_events[0][0] == "t_ok"
    assert img2_out.exists()

