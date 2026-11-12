import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget

from app.core.probe import MediaInfo
from app.ui.drop_zone import DropZone
from app.ui.main_window import MainWindow
from app.ui.task_table import TaskTable
from app.ui.theme import apply_theme, DARK_THEME


@pytest.fixture
def sample_video_info():
    return MediaInfo(
        width=1920,
        height=1080,
        duration=10.0,
        is_video=True,
        has_audio=True,
    )


@pytest.fixture
def sample_image_info():
    return MediaInfo(
        width=1200,
        height=800,
        duration=0.0,
        is_video=False,
        has_audio=False,
    )


def test_theme_application(qtbot):
    button = QPushButton("Test Button")
    qtbot.addWidget(button)
    apply_theme(button)
    assert button.styleSheet() != ""
    assert "#18181b" in DARK_THEME or "#27272a" in DARK_THEME


def test_main_window_instantiation(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert hasattr(window, "drop_zone")
    assert isinstance(window.drop_zone, DropZone)

    assert hasattr(window, "task_table")
    assert isinstance(window.task_table, TaskTable)

    assert hasattr(window, "btn_start")
    assert isinstance(window.btn_start, QPushButton)

    assert hasattr(window, "btn_cancel")
    assert isinstance(window.btn_cancel, QPushButton)

    assert hasattr(window, "btn_clear")
    assert isinstance(window.btn_clear, QPushButton)

    assert hasattr(window, "btn_open_dir")
    assert isinstance(window.btn_open_dir, QPushButton)

    # 初始状态检查
    assert window.windowTitle() == "Asset Splicer-分割拼接工具"
    assert window.radio_ratio_2.text() == "1/2"
    assert window.radio_ratio_3.text() == "1/3"
    assert window.radio_ratio_4.text() == "1/4"
    assert not window.windowIcon().isNull()
    assert not window.btn_start.isEnabled()
    assert not window.btn_cancel.isEnabled()


def test_drop_zone_drag_and_drop(qtbot, tmp_path):
    zone = DropZone()
    qtbot.addWidget(zone)

    valid_file = tmp_path / "sample.mp4"
    valid_file.write_text("dummy")
    invalid_file = tmp_path / "sample.txt"
    invalid_file.write_text("dummy")

    # 模拟有效文件的 DragEnter
    mime_valid = QMimeData()
    mime_valid.setUrls([QUrl.fromLocalFile(str(valid_file))])
    event_valid = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime_valid,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    zone.dragEnterEvent(event_valid)
    assert event_valid.isAccepted()

    # 模拟无效文件的 DragEnter
    mime_invalid = QMimeData()
    mime_invalid.setUrls([QUrl.fromLocalFile(str(invalid_file))])
    event_invalid = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime_invalid,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    zone.dragEnterEvent(event_invalid)
    assert not event_invalid.isAccepted()

    # 模拟 Drop 事件发射信号
    with qtbot.waitSignal(zone.sig_files_dropped, timeout=1000) as blocker:
        drop_event = QDropEvent(
            QPointF(10.0, 10.0),
            Qt.DropAction.CopyAction,
            mime_valid,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        zone.dropEvent(drop_event)
        assert drop_event.isAccepted()

    dropped_paths = blocker.args[0]
    assert len(dropped_paths) == 1
    assert dropped_paths[0] == valid_file.resolve()


def test_ratio_switching_updates_task_table(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    fake_file = tmp_path / "test.mp4"
    fake_file.write_text("video")

    # 添加模拟任务 (1920x1080)
    task_id = window.task_table.add_task_item(fake_file, sample_video_info, split_ratio=2)
    assert task_id is not None
    assert window.task_table.rowCount() == 1

    # 比例 1/2: 1920/2 = 960, 高度 1080 * 2 = 2160
    assert "960 × 2160" in window.task_table.get_target_resolution_text(0)

    # 切换为 1/3: 1920/3 = 640, 高度 1080 * 3 = 3240
    window.radio_ratio_3.setChecked(True)
    assert "640 × 3240" in window.task_table.get_target_resolution_text(0)

    # 切换为 1/4: 1920/4 = 480, 高度 1080 * 4 = 4320
    window.radio_ratio_4.setChecked(True)
    assert "480 × 4320" in window.task_table.get_target_resolution_text(0)


def test_add_files_via_probe(qtbot, tmp_path, sample_video_info, sample_image_info):
    window = MainWindow()
    qtbot.addWidget(window)

    v_file = tmp_path / "clip.mp4"
    v_file.write_text("video")
    i_file = tmp_path / "pic.png"
    i_file.write_text("image")
    bad_file = tmp_path / "corrupt.mp4"
    bad_file.write_text("bad")

    def mock_probe(path):
        p = Path(path)
        if p.name == "clip.mp4":
            return sample_video_info
        elif p.name == "pic.png":
            return sample_image_info
        return None

    with patch.object(window.probe, "probe", side_effect=mock_probe):
        window.on_files_dropped([v_file, i_file, bad_file])

    # 成功添加 2 个合法媒体任务，坏文件被过滤
    assert window.task_table.rowCount() == 2
    assert window.btn_start.isEnabled()
    assert "跳过 1 个无法解析的文件" in window.statusBar().currentMessage()

    # 重复添加 clip.mp4 不应重复入队，并提示跳过重复文件而不是无法解析
    with patch.object(window.probe, "probe", side_effect=mock_probe):
        window.on_files_dropped([v_file])
    assert window.task_table.rowCount() == 2
    assert "跳过 1 个重复文件" in window.lbl_status.text()
    assert "已添加 2 个任务" in window.lbl_status.text()


def test_task_table_item_removal_and_clear(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "f1.mp4"
    f1.write_text("1")
    f2 = tmp_path / "f2.mp4"
    f2.write_text("2")

    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)
    window.task_table.add_task_item(f2, sample_video_info, split_ratio=2)
    assert window.task_table.rowCount() == 2

    # 移除第一行
    window.task_table.remove_row_by_index(0)
    assert window.task_table.rowCount() == 1
    assert window.task_table.item(0, 0).text() == "f2.mp4"

    # 清空列表
    window.btn_clear.click()
    assert window.task_table.rowCount() == 0
    assert not window.btn_start.isEnabled()


def test_start_and_cancel_button_state_toggle(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)
    window.update_ui_state()
    assert window.btn_start.isEnabled()
    assert not window.btn_cancel.isEnabled()

    # 模拟启动处理（mock BatchProcessorThread 避免真正执行 ffmpeg）
    with patch("app.ui.main_window.BatchProcessorThread") as MockThread:
        mock_thread_instance = MagicMock()
        mock_thread_instance._is_cancelled = False
        def fake_cancel():
            mock_thread_instance._is_cancelled = True
        mock_thread_instance.cancel.side_effect = fake_cancel
        MockThread.return_value = mock_thread_instance

        window.btn_start.click()

        # 启动后，开始按钮禁用，中止按钮启用，拖拽区和行移除锁定
        assert not window.btn_start.isEnabled()
        assert window.btn_cancel.isEnabled()
        assert not window.btn_clear.isEnabled()
        assert not window.drop_zone.isEnabled()
        assert not window.task_table._actions_enabled

        # 启动后各项选择保持选中显示但处于禁用状态，无法被修改
        assert window.radio_ratio_2.isChecked()
        assert not window.radio_ratio_2.isEnabled()
        assert window.radio_out_source.isChecked()
        assert not window.radio_out_source.isEnabled()
        assert window.radio_bitrate_original.isChecked()
        assert not window.radio_bitrate_original.isEnabled()

        # 表格内操作按钮（预览/移除）处于禁用状态
        action_widget = window.task_table.cellWidget(0, window.task_table.COL_ACTION)
        assert action_widget is not None
        for btn in action_widget.findChildren(QPushButton):
            assert not btn.isEnabled()

        # 模拟点击中止
        window.btn_cancel.click()
        mock_thread_instance.cancel.assert_called_once()

        # 模拟处理完成信号
        window.on_processing_finished()
        assert window.btn_start.isEnabled()
        assert not window.btn_cancel.isEnabled()
        assert window.btn_clear.isEnabled()
        assert window.drop_zone.isEnabled()
        assert window.task_table._actions_enabled
        assert window.lbl_status.text() == "处理已中止"
        assert window.statusBar().currentMessage() == "用户已中止批量处理"


def test_custom_output_dir_selection(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    # 默认原目录
    tasks_default = window.task_table.get_pending_tasks(
        split_ratio=window.current_ratio,
        output_dir=window.custom_output_dir,
    )
    assert len(tasks_default) == 1
    assert tasks_default[0].output_path.parent == tmp_path

    # 选择自定义输出目录
    custom_dir = tmp_path / "custom_out"
    custom_dir.mkdir()
    window.radio_out_custom.setChecked(True)
    window.edit_custom_dir.setText(str(custom_dir))

    tasks_custom = window.task_table.get_pending_tasks(
        split_ratio=window.current_ratio,
        output_dir=window.custom_output_dir,
    )
    assert len(tasks_custom) == 1
    assert tasks_custom[0].output_path.parent == custom_dir


def test_bitrate_mode_selection(qtbot, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)

    vid_info = MediaInfo(
        width=1920,
        height=1080,
        duration=10.0,
        is_video=True,
        has_audio=True,
        bitrate=11_000_000,
    )
    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    window.task_table.add_task_item(f1, vid_info, split_ratio=2)

    # 1. 默认保持原片码率 (11 Mbps -> 11000k)
    assert window.radio_bitrate_original.isChecked()
    assert window.current_bitrate_mode == "original"
    tasks_orig = window.task_table.get_pending_tasks(
        split_ratio=window.current_ratio,
        output_dir=window.custom_output_dir,
        bitrate_mode=window.current_bitrate_mode,
        custom_bitrate=window.custom_bitrate_val,
    )
    assert tasks_orig[0].bitrate == "11000k"

    # 2. 切换为自定义码率 15 Mbps -> 15000k
    window.radio_bitrate_custom.setChecked(True)
    assert window.edit_custom_bitrate.isEnabled()
    window.edit_custom_bitrate.setText("15")
    assert window.current_bitrate_mode == "custom"
    assert window.custom_bitrate_val == "15000k"
    tasks_custom = window.task_table.get_pending_tasks(
        split_ratio=window.current_ratio,
        output_dir=window.custom_output_dir,
        bitrate_mode=window.current_bitrate_mode,
        custom_bitrate=window.custom_bitrate_val,
    )
    assert tasks_custom[0].bitrate == "15000k"

    # 3. 切换为智能画质 (CRF 18) -> None
    window.radio_bitrate_crf.setChecked(True)
    assert not window.edit_custom_bitrate.isEnabled()
    assert window.current_bitrate_mode == "crf"
    tasks_crf = window.task_table.get_pending_tasks(
        split_ratio=window.current_ratio,
        output_dir=window.custom_output_dir,
        bitrate_mode=window.current_bitrate_mode,
        custom_bitrate=window.custom_bitrate_val,
    )
    assert tasks_crf[0].bitrate is None


def test_task_table_status_updates(qtbot, tmp_path, sample_video_info):
    table = TaskTable()
    qtbot.addWidget(table)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    task_id = table.add_task_item(f1, sample_video_info, split_ratio=2)

    table.set_task_started(task_id)
    assert "处理中" in table.get_task_status_text(task_id)

    table.set_task_progress(task_id, 45.5)
    assert "45.5%" in table.get_task_status_text(task_id)

    table.set_task_completed(task_id, str(tmp_path / "out.mp4"))
    assert "已完成" in table.get_task_status_text(task_id)

    table.set_task_failed(task_id, "FFmpeg error message")
    assert "失败" in table.get_task_status_text(task_id)


def test_main_window_open_output_dir(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
        window.open_output_dir()
        mock_open.assert_called_once()
        called_url = mock_open.call_args[0][0]
        assert tmp_path.name in called_url.toString()


def test_check_tools_missing(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.ffmpeg_bin = "non_existent_ffmpeg.exe"
    window.ffprobe_bin = "non_existent_ffprobe.exe"
    assert not window.check_tools_exist(show_dialog=False)
    assert "警告" in window.statusBar().currentMessage()


def test_app_main_creation():
    from app.main import create_app
    app = create_app([])
    assert app is not None
    assert app.applicationName() == "Asset Splicer"
    assert app.applicationDisplayName() == "Asset Splicer-分割拼接工具"
    assert not app.windowIcon().isNull()


def test_preview_dialog_trigger(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    task_id = window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    with patch("app.ui.preview_dialog.PreviewDialog.generate_and_show") as mock_preview:
        window.task_table.sig_preview_requested.emit(task_id)
        mock_preview.assert_called_once()
        kwargs = mock_preview.call_args[1]
        assert kwargs["file_path"] == f1.resolve()
        assert kwargs["media_info"] == sample_video_info
        assert kwargs["split_ratio"] == 2


def test_preview_dialog_fit_mode_and_cleanup(qtbot, tmp_path, sample_image_info):
    from app.ui.preview_dialog import PreviewDialog
    from PySide6.QtGui import QImage

    # 创建一个测试图片
    img_file = tmp_path / "test_preview.jpg"
    qimg = QImage(200, 400, QImage.Format.Format_RGB32)
    qimg.fill(Qt.GlobalColor.blue)
    qimg.save(str(img_file))

    dlg = PreviewDialog(
        image_path=img_file,
        file_name="test_preview.jpg",
        media_info=sample_image_info,
        split_ratio=2,
    )
    qtbot.addWidget(dlg)

    # 默认适应窗口整体预览模式
    assert dlg.is_fit_mode is True
    assert dlg.temp_image_path.is_file()

    # 切换到 1:1 模式
    dlg.toggle_view_mode()
    assert dlg.is_fit_mode is False

    # 切换回整体预览
    dlg.toggle_view_mode()
    assert dlg.is_fit_mode is True

    # 测试清理临时文件
    dlg.cleanup_temp_file()
    assert not img_file.exists()


def test_close_event_cancels_running_worker(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("video")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    window.worker = mock_worker
    window._is_processing = True

    from PySide6.QtGui import QCloseEvent
    event = QCloseEvent()
    window.closeEvent(event)

    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_with(2000)
    assert event.isAccepted()


def test_ratio_switching_locks_completed_task(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task1.mp4"
    f1.write_text("v1")
    f2 = tmp_path / "task2.mp4"
    f2.write_text("v2")

    t1 = window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)
    t2 = window.task_table.add_task_item(f2, sample_video_info, split_ratio=2)

    # 标记任务 1 已完成
    window.task_table.set_task_completed(t1, str(tmp_path / "out1.mp4"))
    assert "960 × 2160" in window.task_table.get_target_resolution_text(0)

    # 切换比例为 1/3
    window.radio_ratio_3.setChecked(True)

    # 任务 1 已完成，保持原比例规格锁定；任务 2 未完成，更新为新比例规格
    assert "960 × 2160" in window.task_table.get_target_resolution_text(0)
    assert "640 × 3240" in window.task_table.get_target_resolution_text(1)


def test_start_processing_aborts_when_tools_missing(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("v1")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    window.ffmpeg_bin = "non_existent_ffmpeg.exe"
    window.ffprobe_bin = "non_existent_ffprobe.exe"

    with patch("PySide6.QtWidgets.QMessageBox.warning"):
        window.start_processing()

    assert not window._is_processing
    assert window.worker is None


def test_start_processing_waits_for_previous_worker(qtbot, tmp_path, sample_video_info):
    window = MainWindow()
    qtbot.addWidget(window)

    f1 = tmp_path / "task.mp4"
    f1.write_text("v1")
    window.task_table.add_task_item(f1, sample_video_info, split_ratio=2)

    old_worker = MagicMock()
    old_worker.isRunning.return_value = True
    window.worker = old_worker

    with patch.object(window, "check_tools_exist", return_value=True), \
         patch("app.ui.main_window.BatchProcessorThread") as MockThread:
        new_worker = MagicMock()
        MockThread.return_value = new_worker
        window.start_processing()

        old_worker.wait.assert_called_with(1000)
        assert window._is_processing is True
        assert window.worker is new_worker

