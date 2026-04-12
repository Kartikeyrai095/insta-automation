"""
AudioAgent — Merges background audio into the generated reel video.
Uses royalty-free audio clips from the assets/audio/ directory.
"""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

from config.settings import AUDIO_DIR, BACKGROUND_AUDIO_VOLUME, OUTPUT_DIR
from agents.content_agent import ReelContent
from utils.logger import get_logger

logger = get_logger("audio")


class AudioAgent:
    """
    Merges background audio into a video file at low volume.
    If no audio files are available, returns the video as-is.
    """

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".ogg"}

    def __init__(self):
        self.audio_dir = AUDIO_DIR
        self.volume = BACKGROUND_AUDIO_VOLUME

    def run(self, video_path: Path, content: ReelContent) -> Path:
        """
        Merge background audio into the video.

        Args:
            video_path: Path to the video file.
            content: ReelContent (used for mood-based audio selection).

        Returns:
            Path to the final video (with or without audio).
        """
        logger.info("🎵 Processing audio...")

        # Find available audio files
        audio_files = self._get_audio_files()

        if not audio_files:
            logger.info("No audio files available — video will be silent/as-is")
            return video_path

        # Select an audio file
        audio_file = self._select_audio(audio_files, content)
        logger.info(f"Selected audio: {audio_file.name}")

        # Merge audio into video
        output_path = OUTPUT_DIR / f"final_{video_path.name}"
        success = self._merge_audio(video_path, audio_file, output_path)

        if success and output_path.exists():
            # Remove the intermediate video
            if video_path != output_path and video_path.exists():
                video_path.unlink()
            logger.info(f"✅ Audio merged: {output_path}")
            return output_path

        logger.warning("Audio merge failed — returning original video")
        return video_path

    def _get_audio_files(self) -> list[Path]:
        """Get all supported audio files from the audio directory."""
        if not self.audio_dir.exists():
            return []

        files = [
            f for f in self.audio_dir.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

        logger.info(f"Found {len(files)} audio files in {self.audio_dir}")
        return files

    def _select_audio(self, audio_files: list[Path], content: ReelContent) -> Path:
        """
        Select an audio file based on content mood/category.
        Currently random — can be enhanced with mood-to-file mapping.
        """
        # If filenames contain category hints, try to match
        category = content.category.lower()
        category_matches = [
            f for f in audio_files
            if category in f.stem.lower()
        ]

        if category_matches:
            return random.choice(category_matches)

        return random.choice(audio_files)

    def _merge_audio(self, video_path: Path, audio_path: Path, output_path: Path) -> bool:
        """
        Merge audio into video at low volume using FFmpeg.
        Keeps the original video audio (if any) and mixes in background audio.
        """
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex", (
                    f"[1:a]volume={self.volume},aloop=loop=-1:size=2e+09[bg];"
                    f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[out]"
                ),
                "-map", "0:v",
                "-map", "[out]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                str(output_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                # If the video has no audio stream, try simpler approach
                logger.debug(f"amix failed, trying direct audio add: {result.stderr[-200:]}")
                return self._add_audio_simple(video_path, audio_path, output_path)

            return True

        except Exception as e:
            logger.error(f"Audio merge error: {e}")
            return False

    def _add_audio_simple(self, video_path: Path, audio_path: Path, output_path: Path) -> bool:
        """Simpler audio add when video has no existing audio stream."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex",
                f"[1:a]volume={self.volume}[bg]",
                "-map", "0:v",
                "-map", "[bg]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                str(output_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                logger.error(f"Simple audio add failed: {result.stderr[-300:]}")
                return False

            return True

        except Exception as e:
            logger.error(f"Simple audio error: {e}")
            return False
