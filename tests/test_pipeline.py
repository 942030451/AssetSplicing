import pytest
from pathlib import Path
from app.core.pipeline import PipelineBuilder

def test_calculate_part_width():
    # 1920 均分 2 份 -> 960 (偶数)
    assert PipelineBuilder.calculate_part_width(1920, 2) == 960
    # 1920 均分 3 份 -> 640 (偶数)
    assert PipelineBuilder.calculate_part_width(1920, 3) == 640
    # 1920 均分 4 份 -> 480 (偶数)
    assert PipelineBuilder.calculate_part_width(1920, 4) == 480
    # 奇数分辨率容错测试：1921 均分 2 份 -> 向下取偶得 960
    assert PipelineBuilder.calculate_part_width(1921, 2) == 960
    # 1083 均分 3 份 -> 1083/3 = 361 -> 向下取偶得 360
    assert PipelineBuilder.calculate_part_width(1083, 3) == 360

def test_calculate_part_width_invalid_n():
    with pytest.raises(ValueError, match="n must be greater than 0"):
        PipelineBuilder.calculate_part_width(1920, 0)
    with pytest.raises(ValueError, match="n must be greater than 0"):
        PipelineBuilder.calculate_part_width(1920, -1)

def test_calculate_part_width_invalid_w():
    with pytest.raises(ValueError, match="w must be greater than 0"):
        PipelineBuilder.calculate_part_width(0, 2)
    with pytest.raises(ValueError, match="w must be greater than 0"):
        PipelineBuilder.calculate_part_width(-10, 2)

def test_calculate_part_width_too_small():
    with pytest.raises(ValueError, match="too small"):
        PipelineBuilder.calculate_part_width(1, 2)
    with pytest.raises(ValueError, match="too small"):
        PipelineBuilder.calculate_part_width(3, 2)

def test_build_filtergraph_two_parts():
    fg = PipelineBuilder.build_filtergraph(w_part=960, h=1080, n=2)
    assert "[0:v]crop=960:1080:0:0[p0]" in fg
    assert "[0:v]crop=960:1080:960:0[p1]" in fg
    assert "[p0][p1]vstack=inputs=2[v]" in fg

def test_build_filtergraph_three_parts():
    fg = PipelineBuilder.build_filtergraph(w_part=640, h=1080, n=3)
    assert "[0:v]crop=640:1080:0:0[p0]" in fg
    assert "[0:v]crop=640:1080:640:0[p1]" in fg
    assert "[0:v]crop=640:1080:1280:0[p2]" in fg
    assert "[p0][p1][p2]vstack=inputs=3[v]" in fg

def test_build_filtergraph_four_parts():
    fg = PipelineBuilder.build_filtergraph(w_part=480, h=1080, n=4)
    assert "[0:v]crop=480:1080:0:0[p0]" in fg
    assert "[0:v]crop=480:1080:480:0[p1]" in fg
    assert "[0:v]crop=480:1080:960:0[p2]" in fg
    assert "[0:v]crop=480:1080:1440:0[p3]" in fg
    assert "[p0][p1][p2][p3]vstack=inputs=4[v]" in fg

def test_build_command_for_video(tmp_path):
    input_file = tmp_path / "test.mp4"
    output_file = tmp_path / "out.mp4"
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        output_path=str(output_file),
        orig_w=1920,
        orig_h=1080,
        n=2,
        is_video=True,
        has_audio=True
    )
    assert "ffmpeg.exe" in cmd[0]
    assert "-filter_complex" in cmd
    assert "-c:a" in cmd
    assert "copy" in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-progress" in cmd
    assert "pipe:1" in cmd

def test_build_command_for_video_no_audio(tmp_path):
    input_file = tmp_path / "test.mp4"
    output_file = tmp_path / "out.mp4"
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        output_path=str(output_file),
        orig_w=1920,
        orig_h=1080,
        n=2,
        is_video=True,
        has_audio=False
    )
    assert "ffmpeg.exe" in cmd[0]
    assert "-filter_complex" in cmd
    assert "-c:a" not in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd

def test_build_command_odd_height_video(tmp_path):
    input_file = tmp_path / "odd_height.mp4"
    output_file = tmp_path / "out.mp4"
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        output_path=str(output_file),
        orig_w=1920,
        orig_h=1081,
        n=3,
        is_video=True,
        has_audio=False
    )
    # 视频模式下 1081 向下取偶为 1080
    fg_idx = cmd.index("-filter_complex")
    fg = cmd[fg_idx + 1]
    assert "crop=640:1080:0:0" in fg
    assert "crop=640:1080:640:0" in fg
    assert "crop=640:1080:1280:0" in fg

def test_build_command_for_image(tmp_path):
    input_file = tmp_path / "test.png"
    output_file = tmp_path / "out.png"
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        output_path=str(output_file),
        orig_w=1200,
        orig_h=800,
        n=2,
        is_video=False,
        has_audio=False
    )
    assert "-c:a" not in cmd
    assert "-progress" not in cmd

def test_build_command_odd_height_image(tmp_path):
    input_file = tmp_path / "odd_height.png"
    output_file = tmp_path / "out.png"
    cmd = PipelineBuilder.build_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        output_path=str(output_file),
        orig_w=1200,
        orig_h=801,
        n=2,
        is_video=False,
        has_audio=False
    )
    # 图片模式保留原始高度 801
    fg_idx = cmd.index("-filter_complex")
    fg = cmd[fg_idx + 1]
    assert "crop=600:801:0:0" in fg

def test_generate_output_path():
    # 默认同目录生成
    res1 = PipelineBuilder.generate_output_path("video.mp4", 2)
    assert res1.name == "video_vsplit_1_2.mp4"
    assert res1.parent == Path(".")

    res2 = PipelineBuilder.generate_output_path(Path("/data/test.png"), 3)
    assert res2.name == "test_vsplit_1_3.png"
    assert res2.parent == Path("/data")

    # 指定输出目录
    res3 = PipelineBuilder.generate_output_path("video.mp4", 4, output_dir="D:/output")
    assert res3 == Path("D:/output/video_vsplit_1_4.mp4")

    # 非法分块比例异常
    with pytest.raises(ValueError, match="n must be greater than 0"):
        PipelineBuilder.generate_output_path("video.mp4", 0)

def test_build_preview_command_video(tmp_path):
    input_file = tmp_path / "test.mp4"
    preview_file = tmp_path / "preview.jpg"
    cmd = PipelineBuilder.build_preview_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        preview_output_path=str(preview_file),
        orig_w=1920,
        orig_h=1080,
        n=2,
        is_video=True,
        seek_sec=1.5
    )
    assert "-ss" in cmd
    assert "1.50" in cmd
    assert "-frames:v" in cmd
    assert "1" in cmd
    assert "-filter_complex" in cmd
    assert cmd[-1] == str(preview_file)

def test_build_preview_command_image(tmp_path):
    input_file = tmp_path / "test.png"
    preview_file = tmp_path / "preview.png"
    cmd = PipelineBuilder.build_preview_command(
        ffmpeg_bin="ffmpeg.exe",
        input_path=str(input_file),
        preview_output_path=str(preview_file),
        orig_w=1200,
        orig_h=800,
        n=3,
        is_video=False
    )
    assert "-ss" not in cmd
    assert "-frames:v" in cmd
    assert "1" in cmd
    assert "crop=400:800" in cmd[cmd.index("-filter_complex") + 1]

