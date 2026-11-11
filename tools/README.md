# 内置工具目录 (Tools Directory)

本目录用于存放免安装运行所需的 FFmpeg 二进制可执行文件。

## 文件说明

| 文件名 | 说明 | 来源/建议版本 |
| :--- | :--- | :--- |
| `ffmpeg.exe` | 核心转码与滤镜处理工具 | FFmpeg 5.0+ 或 6.1+ 64位 Windows 版本 |
| `ffprobe.exe` | 媒体元数据解析与流检测工具 | 对应版本的 ffprobe |

## 注意事项

1. `*.exe` 文件已被 `.gitignore` 忽略，避免大体积二进制文件提交至 Git 仓库。
2. 开发与打包前，请确保将 `ffmpeg.exe` 和 `ffprobe.exe` 放置于本目录。
3. Nuitka 打包时会通过 `--include-data-dir=tools=tools` 参数将本目录下的二进制工具直接嵌入至分发包中。
