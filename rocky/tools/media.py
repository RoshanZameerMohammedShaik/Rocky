"""Media processing tools for Rocky.Ai."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.platform import is_command_available
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class DescribeImageTool(Tool):
    """Describe an image — returns base64 for the model to process."""

    def __init__(self):
        super().__init__(
            name="describe_image",
            description="Read and encode an image file for analysis.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the image file",
                    required=True
                ),
                ToolParameter(
                    name="question",
                    type="string",
                    description="Specific question about the image",
                    required=False,
                    default=None
                ),
            ]
        )

    def execute(self, path: str, question: Optional[str] = None) -> ToolResult:
        image_path = Path(path).expanduser().resolve()

        if not image_path.exists():
            return ToolResult.fail(f"Image not found: {path}")

        valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        if image_path.suffix.lower() not in valid_extensions:
            return ToolResult.fail(f"Unsupported image format: {image_path.suffix}")

        try:
            size = image_path.stat().st_size
            return ToolResult.ok(
                f"Image loaded: {image_path.name} ({size} bytes). "
                "Vision model support coming in a future release.",
                data={"path": str(image_path), "size": size}
            )
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return ToolResult.fail(f"Failed to process image: {e}")


class TranscribeAudioTool(Tool):
    """Transcribe audio using Whisper."""

    def __init__(self):
        super().__init__(
            name="transcribe_audio",
            description="Transcribe audio file to text using AI.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the audio file",
                    required=True
                ),
            ]
        )

    def execute(self, path: str) -> ToolResult:
        audio_path = Path(path).expanduser().resolve()

        if not audio_path.exists():
            return ToolResult.fail(f"Audio file not found: {path}")

        valid_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"}
        if audio_path.suffix.lower() not in valid_extensions:
            return ToolResult.fail(f"Unsupported audio format: {audio_path.suffix}")

        try:
            # Try faster-whisper if installed
            from faster_whisper import WhisperModel
            model = WhisperModel("base", compute_type="int8")
            segments, _ = model.transcribe(str(audio_path))
            transcript = " ".join(seg.text for seg in segments)
            return ToolResult.ok(transcript, data={"path": str(audio_path)})
        except ImportError:
            size = audio_path.stat().st_size
            return ToolResult.ok(
                f"Audio file loaded: {audio_path.name} ({size} bytes). "
                "Install faster-whisper for transcription: pip install faster-whisper",
                data={"path": str(audio_path)}
            )
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return ToolResult.fail(f"Failed to transcribe audio: {e}")


class ProcessVideoTool(Tool):
    """Process video: extract audio and frames for analysis."""

    def __init__(self):
        super().__init__(
            name="process_video",
            description="Process a video file: extract and transcribe audio, analyze key frames.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the video file",
                    required=True
                ),
                ToolParameter(
                    name="extract_frames",
                    type="integer",
                    description="Number of frames to extract for analysis",
                    required=False,
                    default=5
                ),
            ]
        )

    def execute(self, path: str, extract_frames: int = 5) -> ToolResult:
        video_path = Path(path).expanduser().resolve()

        if not video_path.exists():
            return ToolResult.fail(f"Video file not found: {path}")

        valid_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
        if video_path.suffix.lower() not in valid_extensions:
            return ToolResult.fail(f"Unsupported video format: {video_path.suffix}")

        if not is_command_available("ffmpeg"):
            return ToolResult.fail(
                "FFmpeg not installed. Install FFmpeg to process videos."
            )

        try:
            output_parts = [f"Processing video: {video_path.name}\n"]

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract audio
                audio_path = temp_path / "audio.wav"
                audio_result = self._extract_audio(video_path, audio_path)

                if audio_result:
                    output_parts.append(f"Audio extracted: {audio_result}")

                    # Try transcription
                    try:
                        from faster_whisper import WhisperModel
                        model = WhisperModel("base", compute_type="int8")
                        segments, _ = model.transcribe(str(audio_path))
                        transcript = " ".join(seg.text for seg in segments)
                        output_parts.append(f"\nTranscript:\n{transcript}")
                    except ImportError:
                        output_parts.append("\nInstall faster-whisper for transcription.")

                # Extract frames
                frames = self._extract_frames(video_path, temp_path, extract_frames)
                if frames:
                    output_parts.append(f"\nExtracted {len(frames)} frames to {temp_dir}")

            return ToolResult.ok(
                "\n".join(output_parts),
                data={"path": str(video_path)}
            )

        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return ToolResult.fail(f"Failed to process video: {e}")

    def _extract_audio(self, video_path: Path, output_path: Path) -> Optional[str]:
        """Extract audio from video using FFmpeg."""
        try:
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                "-y", str(output_path)
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)

            if output_path.exists() and output_path.stat().st_size > 0:
                return f"{output_path.stat().st_size} bytes"
            return None
        except Exception as e:
            logger.warning(f"Audio extraction failed: {e}")
            return None

    def _extract_frames(self, video_path: Path, output_dir: Path, count: int) -> list[Path]:
        """Extract frames from video using FFmpeg."""
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip() or "10")

            interval = duration / (count + 1)
            frames = []

            for i in range(count):
                timestamp = interval * (i + 1)
                output_path = output_dir / f"frame_{i:03d}.jpg"

                cmd = [
                    "ffmpeg", "-ss", str(timestamp),
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-y", str(output_path)
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)

                if output_path.exists():
                    frames.append(output_path)

            return frames
        except Exception as e:
            logger.warning(f"Frame extraction failed: {e}")
            return []
