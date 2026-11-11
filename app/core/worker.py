import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import QObject, QThread, Signal

from app.core.pipeline import PipelineBuilder
from app.core.probe import MediaInfo


def parse_progress_line(line: str) -> Tuple[Optional[str], Optional[Union[str, int]]]:
    line = line.strip()
    if not line or "=" not in line:
        return None, None
    key, val = line.split("=", 1)
    key = key.strip()
    val = val.strip()
    if not key:
        return None, None
    try:
        return key, int(val)
    except ValueError:
        return key, val


@dataclass
class BatchTask:
    task_id: str
    input_path: Path
    output_path: Path
    media_info: MediaInfo
    split_ratio: int

    def __post_init__(self):
        if not isinstance(self.input_path, Path):
            self.input_path = Path(self.input_path)
        if not isinstance(self.output_path, Path):
            self.output_path = Path(self.output_path)


class BatchProcessorThread(QThread):
    sig_task_started = Signal(str)           # task_id
    sig_task_progress = Signal(str, float)   # task_id, percent (0.0 - 100.0)
    sig_task_completed = Signal(str, str)    # task_id, output_path
    sig_task_failed = Signal(str, str)       # task_id, error_message
    sig_all_finished = Signal()

    def __init__(
        self,
        ffmpeg_bin: Union[str, Path, Sequence[BatchTask]] = "ffmpeg",
        tasks: Optional[Union[Sequence[BatchTask], str, Path]] = None,
        parent: Optional[QObject] = None,
    ):
        # 安全兼容 (tasks, ffmpeg_bin) 的调用形式与标准 (ffmpeg_bin, tasks) 形式
        if isinstance(ffmpeg_bin, (list, tuple)):
            actual_tasks = list(ffmpeg_bin)
            actual_ffmpeg_bin = str(tasks) if isinstance(tasks, (str, Path)) else "ffmpeg"
            actual_parent = parent
        else:
            actual_ffmpeg_bin = str(ffmpeg_bin)
            actual_tasks = list(tasks) if isinstance(tasks, (list, tuple)) else []
            actual_parent = parent

        super().__init__(actual_parent)
        self.ffmpeg_bin: str = actual_ffmpeg_bin
        self.tasks: List[BatchTask] = actual_tasks

        self._is_cancelled: bool = False
        self._current_process: Optional[subprocess.Popen] = None
        self._current_output_file: Optional[Path] = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        self._is_cancelled = True
        with self._lock:
            proc = self._current_process
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        if proc.poll() is None:
                            proc.kill()
                            proc.wait(timeout=2.0)
                except Exception:
                    pass
            self._cleanup_output_file()

    def _cleanup_output_file(self) -> None:
        if self._current_output_file:
            try:
                if self._current_output_file.is_file():
                    self._current_output_file.unlink()
            except Exception:
                pass

    def run(self) -> None:
        try:
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                if sys.platform == "win32"
                else 0
            )

            for task in self.tasks:
                if self._is_cancelled:
                    break

                self.sig_task_started.emit(task.task_id)
                self.sig_task_progress.emit(task.task_id, 0.0)

                with self._lock:
                    if self._is_cancelled:
                        self.sig_task_failed.emit(task.task_id, "用户已取消任务")
                        break

                try:
                    task.output_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.sig_task_failed.emit(task.task_id, f"创建目标目录失败: {e}")
                    continue

                try:
                    cmd = PipelineBuilder.build_command(
                        ffmpeg_bin=self.ffmpeg_bin,
                        input_path=str(task.input_path),
                        output_path=str(task.output_path),
                        orig_w=task.media_info.width,
                        orig_h=task.media_info.height,
                        n=task.split_ratio,
                        is_video=task.media_info.is_video,
                        has_audio=task.media_info.has_audio,
                    )
                except Exception as e:
                    self.sig_task_failed.emit(task.task_id, f"构建命令失败: {e}")
                    continue

                with self._lock:
                    if self._is_cancelled:
                        self.sig_task_failed.emit(task.task_id, "用户已取消任务")
                        break
                    self._current_output_file = task.output_path

                stderr_lines: deque = deque(maxlen=50)

                def collect_stderr(p: subprocess.Popen):
                    try:
                        if p.stderr:
                            for err_line in p.stderr:
                                stderr_lines.append(err_line)
                    except Exception:
                        pass

                proc: Optional[subprocess.Popen] = None
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        creationflags=creationflags,
                    )
                    with self._lock:
                        self._current_process = proc

                    stderr_thread = threading.Thread(
                        target=collect_stderr, args=(proc,), daemon=True
                    )
                    stderr_thread.start()

                    if task.media_info.is_video and task.media_info.duration > 0:
                        total_us = task.media_info.duration * 1_000_000.0
                        last_pct = 0.0
                        if proc.stdout:
                            for line in proc.stdout:
                                if self._is_cancelled:
                                    break
                                k, v = parse_progress_line(line)
                                if k == "out_time_us" and isinstance(v, (int, float)):
                                    pct = min(99.9, max(0.0, (float(v) / total_us) * 100.0))
                                    if pct - last_pct >= 0.1 or pct == 0.0:
                                        last_pct = pct
                                        self.sig_task_progress.emit(task.task_id, round(pct, 1))
                    else:
                        if proc.stdout:
                            for _ in proc.stdout:
                                if self._is_cancelled:
                                    break

                    if self._is_cancelled:
                        try:
                            if proc.poll() is None:
                                proc.terminate()
                                proc.wait(timeout=2.0)
                        except Exception:
                            try:
                                if proc.poll() is None:
                                    proc.kill()
                                    proc.wait(timeout=2.0)
                            except Exception:
                                pass
                    else:
                        proc.wait()

                    stderr_thread.join(timeout=1.0)

                    with self._lock:
                        if self._is_cancelled:
                            self._cleanup_output_file()
                            self.sig_task_failed.emit(task.task_id, "用户已取消任务")
                            break

                    if proc.returncode == 0:
                        self.sig_task_progress.emit(task.task_id, 100.0)
                        self.sig_task_completed.emit(task.task_id, str(task.output_path))
                    else:
                        err_text = "".join(stderr_lines).strip()
                        err_msg = (
                            err_text[-500:]
                            if err_text
                            else f"FFmpeg 进程退出，错误码: {proc.returncode}"
                        )
                        self._cleanup_output_file()
                        self.sig_task_failed.emit(task.task_id, err_msg)

                except Exception as e:
                    self._cleanup_output_file()
                    self.sig_task_failed.emit(task.task_id, str(e))
                finally:
                    if proc:
                        if proc.stdout:
                            try:
                                proc.stdout.close()
                            except Exception:
                                pass
                        if proc.stderr:
                            try:
                                proc.stderr.close()
                            except Exception:
                                pass
                    with self._lock:
                        self._current_process = None
                        self._current_output_file = None

        finally:
            self.sig_all_finished.emit()
