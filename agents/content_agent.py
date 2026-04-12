"""
ContentAgent — Generates reel content using Google Gemini API.
Falls back to rule-based templates if API is unavailable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from config.templates import (
    generate_hook,
    generate_script,
    generate_caption,
    generate_hashtags,
)
from agents.news_agent import NewsMatch
from utils.logger import get_logger

logger = get_logger("content")


@dataclass
class ReelContent:
    """Complete content package for one Instagram Reel."""
    topic: str
    hook: str
    script_lines: list[str]
    caption: str
    hashtags: list[str]
    video_prompt: str = ""
    image_prompt: str = ""
    category: str = "general"

    @property
    def full_caption(self) -> str:
        """Caption with hashtags appended."""
        tags = " ".join(self.hashtags)
        return f"{self.caption}\n\n{tags}"

    @property
    def full_script(self) -> str:
        """All script lines joined."""
        return " ".join(self.script_lines)


class ContentAgent:
    """
    Generates all content for an Instagram Reel:
    - Hook (attention-grabbing opener)
    - Script (10-20 second narration, 4-5 lines)
    - Caption (engaging, with emoji)
    - Hashtags (10-15 relevant tags)
    - Video prompt (for Veo AI video generation)
    - Image prompt (for Imagen AI image generation)
    """

    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Gemini client."""
        if self._client is None and self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        return self._client

    def run(self, news: NewsMatch) -> ReelContent | None:
        """
        Generate content for a reel based on a news match.

        Args:
            news: NewsMatch from NewsAgent.

        Returns:
            ReelContent object, or None on failure.
        """
        logger.info(f"✍️ Generating content for: '{news.topic}'")

        # Try Gemini API first
        if self.api_key:
            content = self._generate_with_gemini(news)
            if content:
                return content
            logger.warning("Gemini generation failed, falling back to templates")

        # Fallback to templates
        return self._generate_with_templates(news)

    def _generate_with_gemini(self, news: NewsMatch) -> ReelContent | None:
        """Generate content using Google Gemini API."""
        client = self._get_client()
        if not client:
            return None

        prompt = self._build_prompt(news)

        try:
            from tenacity import retry, stop_after_attempt, wait_exponential

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=2, min=4, max=30),
            )
            def call_gemini():
                response = client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.8,
                        "top_p": 0.9,
                        "max_output_tokens": 1024,
                        "response_mime_type": "application/json",
                    },
                )
                return response.text

            raw_response = call_gemini()
            logger.debug(f"Gemini raw response: {raw_response[:500]}")

            # Parse JSON response
            content_data = json.loads(raw_response)

            content = ReelContent(
                topic=news.topic,
                hook=content_data.get("hook", generate_hook(news.topic)),
                script_lines=content_data.get("script_lines", []),
                caption=content_data.get("caption", ""),
                hashtags=content_data.get("hashtags", []),
                video_prompt=content_data.get("video_prompt", ""),
                image_prompt=content_data.get("image_prompt", ""),
                category=news.category,
            )

            # Validate and fix
            if not content.script_lines:
                content.script_lines = generate_script(news.topic, news.headline)
            if not content.caption:
                content.caption = generate_caption(news.topic, news.headline)
            if len(content.hashtags) < 5:
                content.hashtags = generate_hashtags(news.category)
            if not content.video_prompt:
                content.video_prompt = self._default_video_prompt(news)
            if not content.image_prompt:
                content.image_prompt = self._default_image_prompt(news)

            logger.info(f"✅ Gemini content generated successfully")
            logger.info(f"  Hook: {content.hook}")
            logger.info(f"  Script lines: {len(content.script_lines)}")
            logger.info(f"  Hashtags: {len(content.hashtags)}")
            return content

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None

    def _generate_with_templates(self, news: NewsMatch) -> ReelContent:
        """Generate content using rule-based templates."""
        logger.info("Using template-based content generation")

        content = ReelContent(
            topic=news.topic,
            hook=generate_hook(news.topic),
            script_lines=generate_script(news.topic, news.headline, news.source_name),
            caption=generate_caption(news.topic, news.headline),
            hashtags=generate_hashtags(news.category),
            video_prompt=self._default_video_prompt(news),
            image_prompt=self._default_image_prompt(news),
            category=news.category,
        )

        logger.info(f"✅ Template content generated")
        return content

    def _build_prompt(self, news: NewsMatch) -> str:
        """Build the Gemini prompt for content generation."""
        return f"""You are an expert Instagram Reels content creator specializing in news and trending topics.
Create viral, engaging content for an Instagram Reel about the following:

TRENDING TOPIC: {news.topic}
NEWS HEADLINE: {news.headline}
NEWS SUMMARY: {news.summary}
SOURCE: {news.source_name}
CATEGORY: {news.category}

Generate the following in JSON format:

{{
    "hook": "A 5-8 word attention-grabbing opener with emoji. Must create curiosity.",
    "script_lines": [
        "Line 1: Shocking opener about the topic (3-5 seconds)",
        "Line 2: The key fact from the headline (3-5 seconds)",
        "Line 3: The impact or significance (3-5 seconds)",
        "Line 4: Call-to-action (2-3 seconds)"
    ],
    "caption": "An engaging Instagram caption (150-200 chars) with emojis. Include a call-to-action (comment, share, follow). Do NOT include hashtags here.",
    "hashtags": ["#hashtag1", "#hashtag2", "...up to 12-15 relevant hashtags"],
    "video_prompt": "A detailed prompt for AI video generation: describe a cinematic, visually stunning 9:16 vertical video scene (15 seconds) that represents this topic. Include mood, lighting, camera movement, and visual elements. No text overlays in the video itself.",
    "image_prompt": "A detailed prompt for AI image generation: describe a striking, high-quality 9:16 vertical image that represents this topic. Cinematic style, vibrant colors, dramatic lighting."
}}

RULES:
- Hook must be EXTREMELY attention-grabbing (think: would you stop scrolling?)
- Script must be speakable in 12-15 seconds total
- Each script line should be 1-2 sentences max
- Caption should feel authentic and human
- Hashtags: mix of high-volume (#trending, #viral) and niche-specific tags
- Video prompt: cinematic, abstract/symbolic representation — NOT news footage
- Image prompt: visually stunning, Instagram-worthy aesthetic
- Use Indian English where appropriate (the audience is Indian)
- Respond ONLY with valid JSON, no markdown or explanation"""

    @staticmethod
    def _default_video_prompt(news: NewsMatch) -> str:
        """Default video prompt if Gemini doesn't generate one."""
        return (
            f"A cinematic, dramatic 9:16 vertical video representing the concept of "
            f"'{news.topic}'. Moody lighting, slow camera push-in, abstract visuals "
            f"with vibrant colors. News-style urgency. 15 seconds, no text overlays."
        )

    @staticmethod
    def _default_image_prompt(news: NewsMatch) -> str:
        """Default image prompt if Gemini doesn't generate one."""
        return (
            f"A striking, cinematic 9:16 vertical image representing '{news.topic}'. "
            f"Dramatic lighting, deep colors, modern minimalist composition. "
            f"Professional photography style, Instagram-worthy aesthetic."
        )
