"""
PostingAgent — Uploads Reels to Instagram via Graph API (Resumable Upload).
Falls back to saving a post package for manual upload.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import requests

from config.settings import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_USER_ID,
    INSTAGRAM_BASE_URL,
    INSTAGRAM_POLL_INTERVAL,
    INSTAGRAM_POLL_TIMEOUT,
    OUTPUT_DIR,
)
from agents.content_agent import ReelContent
from utils.logger import get_logger

logger = get_logger("posting")


class PostResult:
    def __init__(self, success: bool, post_id: str = "", error: str = "", fallback_path: str = ""):
        self.success = success
        self.post_id = post_id
        self.error = error
        self.fallback_path = fallback_path

    def __repr__(self):
        if self.success:
            return f"PostResult(✅ posted, id={self.post_id})"
        return f"PostResult(❌ failed: {self.error})"


class PostingAgent:
    """
    Posts Reels to Instagram using the Graph API Resumable Upload flow.
    Falls back to saving a post package for manual upload.
    """

    def __init__(self):
        self.access_token = INSTAGRAM_ACCESS_TOKEN
        self.user_id = INSTAGRAM_USER_ID
        self.base_url = INSTAGRAM_BASE_URL

    def run(self, video_path: Path, content: ReelContent) -> PostResult:
        """
        Post a reel to Instagram.

        Args:
            video_path: Path to the final video file.
            content: ReelContent with caption and hashtags.

        Returns:
            PostResult indicating success or failure.
        """
        logger.info(f"📤 Attempting to post reel: {video_path.name}")

        # Check credentials
        if not self.access_token or not self.user_id:
            logger.warning("Instagram credentials not configured — creating post package")
            return self._create_post_package(video_path, content)

        # Try Instagram Graph API
        try:
            result = self._post_via_graph_api(video_path, content)
            return result
        except Exception as e:
            logger.error(f"Instagram API error: {e}")
            logger.info("Falling back to post package")
            return self._create_post_package(video_path, content)

    def _post_via_graph_api(self, video_path: Path, content: ReelContent) -> PostResult:
        """Post using Instagram Graph API Resumable Upload."""
        logger.info("Step 1/4: Creating resumable upload session...")

        # Step 1: Create resumable upload container
        create_url = f"{self.base_url}/{self.user_id}/media"
        create_params = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": content.full_caption,
            "access_token": self.access_token,
        }

        create_response = requests.post(create_url, data=create_params, timeout=30)
        create_response.raise_for_status()
        create_data = create_response.json()

        container_id = create_data.get("id")
        upload_url = create_data.get("uri")

        if not container_id:
            return PostResult(False, error=f"No container ID returned: {create_data}")

        logger.info(f"Step 2/4: Uploading video ({video_path.stat().st_size / 1024 / 1024:.1f} MB)...")

        # Step 2: Upload the video file
        file_size = video_path.stat().st_size
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size),
        }

        with open(video_path, "rb") as f:
            upload_response = requests.post(
                upload_url or f"https://rupload.facebook.com/video-upload/{container_id}",
                headers=headers,
                data=f,
                timeout=120,
            )

        if upload_response.status_code not in (200, 201):
            return PostResult(
                False,
                error=f"Upload failed ({upload_response.status_code}): {upload_response.text[:200]}",
            )

        logger.info("Step 3/4: Waiting for processing...")

        # Step 3: Poll container status until FINISHED
        status = self._poll_status(container_id)
        if status != "FINISHED":
            return PostResult(False, error=f"Container status: {status} (expected FINISHED)")

        logger.info("Step 4/4: Publishing reel...")

        # Step 4: Publish
        publish_url = f"{self.base_url}/{self.user_id}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }

        publish_response = requests.post(publish_url, data=publish_params, timeout=30)
        publish_response.raise_for_status()
        publish_data = publish_response.json()

        post_id = publish_data.get("id", "")
        logger.info(f"✅ Reel published successfully! Post ID: {post_id}")
        return PostResult(True, post_id=post_id)

    def _poll_status(self, container_id: str) -> str:
        """Poll the container status until it's FINISHED or times out."""
        status_url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }

        elapsed = 0
        while elapsed < INSTAGRAM_POLL_TIMEOUT:
            try:
                response = requests.get(status_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                status = data.get("status_code", data.get("status", "UNKNOWN"))
                logger.info(f"  Container status: {status} ({elapsed}s)")

                if status == "FINISHED":
                    return "FINISHED"
                elif status in ("ERROR", "EXPIRED"):
                    logger.error(f"Container error: {data}")
                    return status

            except Exception as e:
                logger.warning(f"Status poll error: {e}")

            time.sleep(INSTAGRAM_POLL_INTERVAL)
            elapsed += INSTAGRAM_POLL_INTERVAL

        logger.error(f"Container polling timed out after {INSTAGRAM_POLL_TIMEOUT}s")
        return "TIMEOUT"

    def _create_post_package(self, video_path: Path, content: ReelContent) -> PostResult:
        """Create a post package for manual upload."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_dir = OUTPUT_DIR / f"post_package_{timestamp}"
        package_dir.mkdir(exist_ok=True)

        # Copy video
        import shutil
        dest_video = package_dir / video_path.name
        shutil.copy2(video_path, dest_video)

        # Write metadata
        metadata = {
            "topic": content.topic,
            "caption": content.full_caption,
            "hashtags": content.hashtags,
            "hook": content.hook,
            "script": content.script_lines,
            "category": content.category,
            "video_file": video_path.name,
            "created_at": datetime.now().isoformat(),
        }

        meta_path = package_dir / "post_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Write caption as plain text (easy to copy-paste)
        caption_path = package_dir / "caption.txt"
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(content.full_caption)

        logger.info(f"📦 Post package created: {package_dir}")
        return PostResult(
            success=False,
            error="No Instagram credentials — post package created for manual upload",
            fallback_path=str(package_dir),
        )
