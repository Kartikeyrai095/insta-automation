"""
Instagram Reel Automation — Main Pipeline Orchestrator

Flow:
  ControlAgent → TrendAgent → NewsAgent → ContentAgent
  → VideoAgent → AudioAgent → PostingAgent

Each step is wrapped in error handling with graceful degradation.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.control_agent import ControlAgent
from agents.trend_agent import TrendAgent
from agents.news_agent import NewsAgent
from agents.content_agent import ContentAgent
from agents.video_agent import VideoAgent
from agents.audio_agent import AudioAgent
from agents.posting_agent import PostingAgent
from agents.scheduler_agent import SchedulerAgent
from utils.logger import get_logger
from utils.dedup import record_topic
from utils.token_refresh import auto_refresh_if_needed

logger = get_logger("pipeline")


def run_pipeline():
    """Execute the full reel automation pipeline."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("🚀 Instagram Reel Automation Pipeline — Starting")
    logger.info(f"   Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # ── Step 0: Token Refresh ──────────────────────────────
    try:
        auto_refresh_if_needed()
    except Exception as e:
        logger.warning(f"Token refresh check failed (non-fatal): {e}")

    # ── Step 1: Control Check ──────────────────────────────
    logger.info("\n📋 Step 1/7: Control Check")
    try:
        control = ControlAgent()
        status = control.check()
        if not status.should_run:
            logger.info(f"Pipeline halted: {status.reason}")
            return {"status": "halted", "reason": status.reason}
    except Exception as e:
        logger.error(f"Control check error: {e}")
        # Proceed on control check failure (fail-open)

    # ── Step 1.5: Schedule Check ───────────────────────────
    try:
        scheduler = SchedulerAgent()
        if not scheduler.should_run():
            logger.info("Off-hours — skipping this run")
            return {"status": "skipped", "reason": "off-hours"}
    except Exception as e:
        logger.warning(f"Scheduler check failed (non-fatal): {e}")

    # ── Step 2: Fetch Trends ───────────────────────────────
    logger.info("\n📈 Step 2/7: Fetching Trends")
    try:
        trend_agent = TrendAgent()
        trends = trend_agent.run()

        if not trends:
            logger.error("No trends found — aborting pipeline")
            return {"status": "failed", "reason": "no_trends"}

        logger.info(f"Got {len(trends)} trending topics")
    except Exception as e:
        logger.error(f"TrendAgent failed: {e}")
        return {"status": "failed", "reason": f"trend_error: {e}"}

    # ── Step 3: Match News ─────────────────────────────────
    logger.info("\n📰 Step 3/7: Matching News")
    try:
        news_agent = NewsAgent()
        news = news_agent.run(trends)

        if not news:
            logger.warning("No news match found — aborting pipeline (fail-safe)")
            return {"status": "skipped", "reason": "no_news_match"}

        logger.info(f"Matched: '{news.topic}' → '{news.headline}'")
    except Exception as e:
        logger.error(f"NewsAgent failed: {e}")
        return {"status": "failed", "reason": f"news_error: {e}"}

    # ── Step 4: Generate Content ───────────────────────────
    logger.info("\n✍️ Step 4/7: Generating Content")
    try:
        content_agent = ContentAgent()
        content = content_agent.run(news)

        if not content:
            logger.error("Content generation failed — aborting")
            return {"status": "failed", "reason": "content_generation_failed"}

        logger.info(f"Content ready — Hook: {content.hook}")
    except Exception as e:
        logger.error(f"ContentAgent failed: {e}")
        return {"status": "failed", "reason": f"content_error: {e}"}

    # ── Step 5: Create Video ───────────────────────────────
    logger.info("\n🎬 Step 5/7: Creating Video")
    try:
        video_agent = VideoAgent()
        video_path = video_agent.run(content)

        if not video_path or not video_path.exists():
            logger.error("Video creation failed — aborting")
            return {"status": "failed", "reason": "video_creation_failed"}

        size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"Video created: {video_path.name} ({size_mb:.1f} MB)")
    except Exception as e:
        logger.error(f"VideoAgent failed: {e}")
        return {"status": "failed", "reason": f"video_error: {e}"}

    # ── Step 6: Add Audio ──────────────────────────────────
    logger.info("\n🎵 Step 6/7: Adding Audio")
    try:
        audio_agent = AudioAgent()
        final_video = audio_agent.run(video_path, content)
        logger.info(f"Final video: {final_video.name}")
    except Exception as e:
        logger.warning(f"AudioAgent failed (non-fatal): {e}")
        final_video = video_path  # Continue without audio

    # ── Step 7: Post to Instagram ──────────────────────────
    logger.info("\n📤 Step 7/7: Posting to Instagram")
    try:
        posting_agent = PostingAgent()
        result = posting_agent.run(final_video, content)

        if result.success:
            logger.info(f"🎉 Reel posted successfully! ID: {result.post_id}")
        else:
            logger.warning(f"Posting result: {result.error}")
            if result.fallback_path:
                logger.info(f"📦 Post package saved: {result.fallback_path}")
    except Exception as e:
        logger.error(f"PostingAgent failed: {e}")
        result = None

    # ── Record topic for dedup ─────────────────────────────
    try:
        record_topic(content.topic)
        logger.info(f"Recorded topic for dedup: '{content.topic}'")
    except Exception as e:
        logger.warning(f"Failed to record topic: {e}")

    # ── Summary ────────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("📊 Pipeline Summary")
    logger.info(f"   Topic:    {content.topic}")
    logger.info(f"   Hook:     {content.hook}")
    logger.info(f"   Video:    {final_video.name}")
    logger.info(f"   Posted:   {'✅ Yes' if result and result.success else '❌ No (package created)'}")
    logger.info(f"   Duration: {elapsed:.1f}s")
    logger.info("=" * 60)

    return {
        "status": "success" if result and result.success else "package_created",
        "topic": content.topic,
        "video": str(final_video),
        "duration_seconds": round(elapsed, 1),
    }


if __name__ == "__main__":
    try:
        result = run_pipeline()
        logger.info(f"Pipeline result: {result}")

        # Exit with appropriate code
        if result.get("status") in ("success", "package_created", "skipped", "halted"):
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled pipeline error: {e}", exc_info=True)
        sys.exit(1)
