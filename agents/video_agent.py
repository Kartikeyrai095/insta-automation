"""
VideoAgent — Generates Instagram Reel video using a 4-tier fallback strategy.
Tier 1: Google Veo AI video generation
Tier 2: Google Imagen AI image → FFmpeg video with Ken Burns effect
Tier 3: Pexels stock footage + FFmpeg text overlays
Tier 4: Pure FFmpeg animated gradient + text overlays
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from config.settings import (
    GEMINI_API_KEY,
    VEO_MODEL,
    VEO_ENABLED,
    IMAGEN_MODEL,
    IMAGEN_ENABLED,
    PEXELS_API_KEY,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    VIDEO_DURATION,
    OUTPUT_DIR,
)
from agents.content_agent import ReelContent
from utils.logger import get_logger

logger = get_logger("video")


class VideoAgent:
    """
    Creates a 9:16 vertical video for Instagram Reels.
    Uses a 4-tier fallback strategy for maximum reliability.
    """

    def __init__(self):
        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT
        self.fps = VIDEO_FPS
        self.duration = VIDEO_DURATION

    def run(self, content: ReelContent) -> Path | None:
        """
        Generate a reel video.

        Args:
            content: ReelContent from ContentAgent.

        Returns:
            Path to the generated video file, or None on failure.
        """
        logger.info(f"🎬 Generating video for: '{content.topic}'")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"reel_{timestamp}.mp4"

        # Tier 1: Veo AI Video
        if VEO_ENABLED and GEMINI_API_KEY:
            result = self._tier1_veo(content, output_path)
            if result:
                return result
            logger.warning("Tier 1 (Veo) failed, trying Tier 2")

        # Tier 2: Imagen AI Image → FFmpeg
        if IMAGEN_ENABLED and GEMINI_API_KEY:
            result = self._tier2_imagen_ffmpeg(content, output_path)
            if result:
                return result
            logger.warning("Tier 2 (Imagen+FFmpeg) failed, trying Tier 3")

        # Tier 3: Pexels stock footage + FFmpeg
        if PEXELS_API_KEY:
            result = self._tier3_pexels_ffmpeg(content, output_path)
            if result:
                return result
            logger.warning("Tier 3 (Pexels+FFmpeg) failed, trying Tier 4")

        # Tier 4: Pure FFmpeg (always works)
        result = self._tier4_pure_ffmpeg(content, output_path)
        if result:
            return result

        logger.error("❌ All video generation tiers failed")
        return None

    # ────────────────────────────────────────────────────────
    # Tier 1: Google Veo AI Video Generation
    # ────────────────────────────────────────────────────────
    def _tier1_veo(self, content: ReelContent, output_path: Path) -> Path | None:
        """Generate video using Google Veo API."""
        logger.info("🤖 Tier 1: Attempting Veo AI video generation...")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=GEMINI_API_KEY)

            config = types.GenerateVideosConfig(
                aspect_ratio="9:16",
            )

            operation = client.models.generate_videos(
                model=VEO_MODEL,
                prompt=content.video_prompt,
                config=config,
            )

            # Poll until complete (max 5 minutes)
            max_wait = 300
            elapsed = 0
            while not operation.done and elapsed < max_wait:
                logger.info(f"  Veo generating... ({elapsed}s elapsed)")
                time.sleep(15)
                elapsed += 15

            if not operation.done:
                logger.warning("Veo timed out after 5 minutes")
                return None

            result = operation.result
            if result and hasattr(result, 'generated_videos') and result.generated_videos:
                video_data = result.generated_videos[0]
                if hasattr(video_data, 'video') and hasattr(video_data.video, 'video_bytes'):
                    # Save the raw Veo video
                    raw_path = output_path.with_suffix('.veo.mp4')
                    with open(raw_path, 'wb') as f:
                        f.write(video_data.video.video_bytes)

                    # Add text overlays via FFmpeg
                    self._add_text_overlays(raw_path, output_path, content)

                    # Cleanup raw file
                    if raw_path.exists():
                        raw_path.unlink()

                    logger.info(f"✅ Tier 1 (Veo) succeeded: {output_path}")
                    return output_path

            logger.warning("Veo returned no video data")
            return None

        except ImportError:
            logger.warning("google-genai SDK not installed for Veo")
            return None
        except Exception as e:
            logger.error(f"Veo error: {e}")
            return None

    # ────────────────────────────────────────────────────────
    # Tier 2: Imagen AI Image → FFmpeg Video
    # ────────────────────────────────────────────────────────
    def _tier2_imagen_ffmpeg(self, content: ReelContent, output_path: Path) -> Path | None:
        """Generate image with Imagen, convert to video with FFmpeg Ken Burns effect."""
        logger.info("🖼️ Tier 2: Attempting Imagen + FFmpeg...")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=GEMINI_API_KEY)

            response = client.models.generate_images(
                model=IMAGEN_MODEL,
                prompt=content.image_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="9:16",
                ),
            )

            if not response.generated_images:
                logger.warning("Imagen returned no images")
                return None

            # Save the image
            img_data = response.generated_images[0]
            img_path = OUTPUT_DIR / "temp_imagen.png"

            if hasattr(img_data, 'image') and hasattr(img_data.image, 'image_bytes'):
                with open(img_path, 'wb') as f:
                    f.write(img_data.image.image_bytes)
            else:
                logger.warning("Imagen response format unexpected")
                return None

            # Convert image to video with Ken Burns zoom + text
            self._image_to_video_with_text(img_path, output_path, content)

            # Cleanup
            if img_path.exists():
                img_path.unlink()

            if output_path.exists():
                logger.info(f"✅ Tier 2 (Imagen+FFmpeg) succeeded: {output_path}")
                return output_path

            return None

        except ImportError:
            logger.warning("google-genai SDK not installed for Imagen")
            return None
        except Exception as e:
            logger.error(f"Imagen error: {e}")
            return None

    # ────────────────────────────────────────────────────────
    # Tier 3: Pexels Stock + FFmpeg
    # ────────────────────────────────────────────────────────
    def _tier3_pexels_ffmpeg(self, content: ReelContent, output_path: Path) -> Path | None:
        """Download Pexels stock footage and add overlays."""
        logger.info("📹 Tier 3: Attempting Pexels + FFmpeg...")
        try:
            import requests

            # Search for relevant video
            headers = {"Authorization": PEXELS_API_KEY}
            search_url = "https://api.pexels.com/videos/search"
            params = {
                "query": content.topic,
                "per_page": 3,
                "orientation": "portrait",
                "size": "medium",
            }

            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("videos"):
                logger.warning(f"No Pexels videos found for '{content.topic}'")
                return None

            # Find best video file (portrait, reasonable size)
            video_url = None
            for video in data["videos"]:
                for vf in video.get("video_files", []):
                    if (vf.get("width", 0) >= 720
                            and vf.get("height", 0) >= 1280
                            and vf.get("file_type") == "video/mp4"):
                        video_url = vf["link"]
                        break
                if video_url:
                    break

            if not video_url:
                # Try any available video
                video_url = data["videos"][0]["video_files"][0]["link"]

            # Download video
            stock_path = OUTPUT_DIR / "temp_pexels.mp4"
            vid_response = requests.get(video_url, timeout=60)
            vid_response.raise_for_status()
            with open(stock_path, 'wb') as f:
                f.write(vid_response.content)

            # Process with FFmpeg: resize, trim, add text
            self._process_stock_video(stock_path, output_path, content)

            # Cleanup
            if stock_path.exists():
                stock_path.unlink()

            if output_path.exists():
                logger.info(f"✅ Tier 3 (Pexels+FFmpeg) succeeded: {output_path}")
                return output_path

            return None

        except Exception as e:
            logger.error(f"Pexels error: {e}")
            return None

    # ────────────────────────────────────────────────────────
    # Tier 4: Pure FFmpeg (Animated Gradient + Text)
    # ────────────────────────────────────────────────────────
    def _tier4_pure_ffmpeg(self, content: ReelContent, output_path: Path) -> Path | None:
        """Generate video entirely with FFmpeg — animated gradient background + text."""
        logger.info("🎨 Tier 4: Generating pure FFmpeg video...")
        try:
            # Build subtitle text from script
            script_text = self._build_subtitle_text(content.script_lines)

            # Escape text for FFmpeg drawtext
            hook_escaped = self._escape_ffmpeg_text(content.hook)

            # FFmpeg command: animated gradient background + text overlays
            cmd = [
                "ffmpeg", "-y",
                # Generate animated gradient background
                "-f", "lavfi",
                "-i", (
                    f"color=c=#1a1a2e:s={self.width}x{self.height}:d={self.duration}:r={self.fps},"
                    f"drawbox=x=0:y=0:w={self.width}:h={self.height // 3}:color=#16213e@0.8:t=fill,"
                    f"drawbox=x=0:y={self.height * 2 // 3}:w={self.width}:h={self.height // 3}:color=#0f3460@0.7:t=fill"
                ),
                # Generate silent audio
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(self.duration),
                # Video filters: add text overlays
                "-vf", self._build_text_filter(content),
                # Output settings
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                str(output_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr[-500:]}")
                return None

            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Tier 4 (FFmpeg) succeeded: {output_path} ({size_mb:.1f} MB)")
                return output_path

            return None

        except Exception as e:
            logger.error(f"FFmpeg generation error: {e}")
            return None

    # ────────────────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────────────────
    def _build_text_filter(self, content: ReelContent) -> str:
        """Build FFmpeg drawtext filter chain for text overlays."""
        hook_escaped = self._escape_ffmpeg_text(content.hook)
        filters = []

        # Hook text at top (fade in)
        filters.append(
            f"drawtext=text='{hook_escaped}'"
            f":fontsize=52:fontcolor=white:borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=h*0.12"
            f":enable='between(t,0.5,{self.duration})'"
            f":alpha='if(lt(t,1.5),t-0.5,1)'"
        )

        # Script lines as subtitles (timed)
        lines = content.script_lines
        if lines:
            time_per_line = (self.duration - 2) / len(lines)
            for i, line in enumerate(lines):
                start = 1.5 + (i * time_per_line)
                end = start + time_per_line
                line_escaped = self._escape_ffmpeg_text(line)

                filters.append(
                    f"drawtext=text='{line_escaped}'"
                    f":fontsize=38:fontcolor=white:borderw=2:bordercolor=black"
                    f":x=(w-text_w)/2:y=h*0.75"
                    f":line_spacing=10"
                    f":enable='between(t,{start:.1f},{end:.1f})'"
                )

        # "Follow for more" CTA at bottom
        filters.append(
            f"drawtext=text='Follow for more! 🔔'"
            f":fontsize=32:fontcolor=#e94560:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=h*0.92"
            f":enable='between(t,{self.duration - 4},{self.duration})'"
        )

        return ",".join(filters)

    def _add_text_overlays(self, input_path: Path, output_path: Path, content: ReelContent):
        """Add text overlays to an existing video via FFmpeg."""
        text_filter = self._build_text_filter(content)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                   f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black,"
                   f"{text_filter}",
            "-t", str(self.duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"FFmpeg overlay error: {result.stderr[-500:]}")

    def _image_to_video_with_text(self, img_path: Path, output_path: Path, content: ReelContent):
        """Convert a static image to video with Ken Burns zoom effect + text."""
        text_filter = self._build_text_filter(content)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-vf", (
                f"scale=1200:{int(1200 * 16 / 9)},"
                f"zoompan=z='min(zoom+0.001,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={self.duration * self.fps}:s={self.width}x{self.height}:fps={self.fps},"
                f"{text_filter}"
            ),
            "-t", str(self.duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"FFmpeg image-to-video error: {result.stderr[-500:]}")

    def _process_stock_video(self, stock_path: Path, output_path: Path, content: ReelContent):
        """Process stock video: resize, trim, add overlays."""
        text_filter = self._build_text_filter(content)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(stock_path),
            "-vf", (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"{text_filter}"
            ),
            "-t", str(self.duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"FFmpeg stock processing error: {result.stderr[-500:]}")

    @staticmethod
    def _escape_ffmpeg_text(text: str) -> str:
        """Escape special characters for FFmpeg drawtext filter."""
        if not text:
            return ""
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "'\\''")
        text = text.replace(":", "\\:")
        text = text.replace("%", "%%")
        # Remove characters that break drawtext
        for char in [";", "[", "]", "{", "}"]:
            text = text.replace(char, "")
        return text

    @staticmethod
    def _build_subtitle_text(lines: list[str]) -> str:
        """Join script lines into subtitle text."""
        return "\n".join(lines)
