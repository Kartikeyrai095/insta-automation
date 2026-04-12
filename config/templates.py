"""
Rule-based content templates — fallback when no LLM API is available.
Uses keyword substitution for variety.
"""

from __future__ import annotations

import random

# ─────────────────────────────────────────────
# Hook Templates (attention-grabbing openers)
# ─────────────────────────────────────────────
HOOK_TEMPLATES = [
    "🚨 Breaking: {topic} just changed everything!",
    "You won't believe what happened with {topic}!",
    "⚡ {topic} is trending — here's why!",
    "Everyone's talking about {topic} right now 🔥",
    "🧵 {topic}: What you NEED to know",
    "This {topic} update will shock you 😱",
    "📢 Major update on {topic}!",
    "Stop scrolling! {topic} is HUGE right now",
    "🔴 LIVE: {topic} breaks the internet",
    "Wait… did {topic} really just happen?!",
    "📌 {topic} explained in 15 seconds",
    "💡 The truth about {topic} no one tells you",
    "🎯 {topic}: The story everyone's missing",
    "⚠️ {topic} alert! Here's the full story",
    "Why {topic} matters more than you think 🤔",
]

# ─────────────────────────────────────────────
# Script Templates (10-20 second narration)
# ─────────────────────────────────────────────
SCRIPT_TEMPLATES = [
    [
        "So {topic} is making headlines everywhere.",
        "{headline}",
        "This could change everything we know.",
        "Stay tuned for more updates!",
    ],
    [
        "Here's the deal with {topic}.",
        "{headline}",
        "Experts are saying this is just the beginning.",
        "Follow for the latest updates!",
    ],
    [
        "Breaking news about {topic}!",
        "According to {source}, {headline}",
        "The impact could be massive.",
        "What do you think? Comment below!",
    ],
    [
        "Let's talk about {topic}.",
        "{headline}",
        "People are divided on this one.",
        "Drop your opinion in the comments!",
    ],
    [
        "{topic} is the number one trend right now.",
        "Here's why: {headline}",
        "This is developing fast.",
        "Turn on notifications so you don't miss updates!",
    ],
]

# ─────────────────────────────────────────────
# Caption Templates
# ─────────────────────────────────────────────
CAPTION_TEMPLATES = [
    "🔥 {topic} is trending! {headline} 👀 What are your thoughts? Drop a comment! 👇",
    "📰 Breaking: {headline} | Stay informed, follow for more! 🔔",
    "⚡ {topic} update you can't miss! {headline} Share this with someone who needs to see it! 🔁",
    "🚀 {topic} just went viral! Here's what's happening: {headline} 💬",
    "📢 {headline} — The {topic} story everyone's talking about! Follow for daily updates 🗓️",
    "🎯 Everything you need to know about {topic}: {headline} Save this for later! 🔖",
    "💡 Did you know? {headline} The {topic} saga continues... 🧵",
]

# ─────────────────────────────────────────────
# Hashtag Collections
# ─────────────────────────────────────────────
GENERAL_HASHTAGS = [
    "#trending", "#viral", "#news", "#breakingnews",
    "#update", "#today", "#dailynews", "#mustknow",
    "#fyp", "#foryou", "#explore", "#reels",
    "#instagram", "#instagood", "#share",
]

CATEGORY_HASHTAGS = {
    "tech": ["#tech", "#technology", "#ai", "#innovation", "#digital", "#gadgets"],
    "sports": ["#sports", "#cricket", "#ipl", "#football", "#fitness", "#game"],
    "entertainment": ["#bollywood", "#hollywood", "#movies", "#celebrity", "#entertainment"],
    "business": ["#business", "#economy", "#stocks", "#market", "#startup"],
    "india": ["#india", "#indianews", "#bharatiya", "#desi", "#hindustani"],
    "general": ["#world", "#global", "#international", "#breaking", "#latestnews"],
}


def generate_hook(topic: str) -> str:
    """Generate a hook using templates."""
    template = random.choice(HOOK_TEMPLATES)
    return template.format(topic=topic)


def generate_script(topic: str, headline: str, source: str = "reports") -> list[str]:
    """Generate a script using templates."""
    template = random.choice(SCRIPT_TEMPLATES)
    return [
        line.format(topic=topic, headline=headline, source=source)
        for line in template
    ]


def generate_caption(topic: str, headline: str) -> str:
    """Generate a caption using templates."""
    template = random.choice(CAPTION_TEMPLATES)
    return template.format(topic=topic, headline=headline)


def generate_hashtags(category: str = "general", count: int = 12) -> list[str]:
    """Generate a mix of general and category-specific hashtags."""
    category_tags = CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["general"])
    all_tags = list(set(GENERAL_HASHTAGS + category_tags))
    random.shuffle(all_tags)
    return all_tags[:count]
