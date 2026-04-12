# 🎬 Instagram Reel Automation

Fully automated multi-agent system for generating and posting Instagram Reels — powered by **Google AI** (Gemini + Veo + Imagen), orchestrated via **GitHub Actions**.

---

## 🏗️ Architecture

```
ControlAgent → TrendAgent → NewsAgent → ContentAgent → VideoAgent → AudioAgent → PostingAgent
```

| Agent | Role | Powered By |
|---|---|---|
| **ControlAgent** | STOP/START/PAUSE mechanism | `stop.txt` flag |
| **TrendAgent** | Scrape trending topics | Google Trends RSS |
| **NewsAgent** | Match trends to verified news | RSS feeds (9 sources) |
| **ContentAgent** | Generate hook, script, caption, hashtags, prompts | Gemini 2.5 Flash |
| **VideoAgent** | Create 9:16 reel video (4-tier fallback) | Veo 3.1 → Imagen 4 → Pexels → FFmpeg |
| **AudioAgent** | Merge background music | FFmpeg |
| **PostingAgent** | Upload to Instagram | Graph API (Resumable Upload) |
| **SchedulerAgent** | Time-slot awareness (IST) | Built-in |

### Video Generation (4-Tier Fallback)

1. **Tier 1**: Veo 3.1 — AI-generated cinematic video
2. **Tier 2**: Imagen 4 — AI image → FFmpeg Ken Burns video
3. **Tier 3**: Pexels — Stock footage + FFmpeg text overlays
4. **Tier 4**: FFmpeg — Animated gradient + text (always works)

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- FFmpeg (`sudo apt install ffmpeg` / `brew install ffmpeg`)
- [Google AI Studio API Key](https://aistudio.google.com/) (Gemini + Veo + Imagen)
- Instagram Business/Creator account with Meta Developer App

### 2. Clone & Install

```bash
git clone https://github.com/Kartikeyrai095/insta-automation.git
cd insta-automation
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
# Required — Google AI
export GEMINI_API_KEY="your-gemini-api-key"

# Required — Instagram Graph API
export INSTAGRAM_ACCESS_TOKEN="your-long-lived-token"
export INSTAGRAM_USER_ID="your-instagram-user-id"

# Optional — Pexels fallback
export PEXELS_API_KEY="your-pexels-api-key"

# Optional — GitHub secret auto-refresh
export GH_TOKEN="your-github-pat"
export INSTAGRAM_APP_SECRET="your-meta-app-secret"
```

### 4. Run

```bash
python main.py
```

---

## 📅 GitHub Actions Schedule

The system runs **3 times daily** via GitHub Actions cron:

| Slot | IST | UTC | Cron |
|---|---|---|---|
| Morning | 9:00 AM | 3:30 AM | `30 3 * * *` |
| Afternoon | 2:00 PM | 8:30 AM | `30 8 * * *` |
| Evening | 7:00 PM | 1:30 PM | `30 13 * * *` |

You can also trigger manually: **Actions → Instagram Reel Automation → Run workflow**

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram long-lived user access token |
| `INSTAGRAM_USER_ID` | Instagram Business account numeric ID |
| `PEXELS_API_KEY` | (Optional) Pexels API key for stock footage |
| `GH_TOKEN` | (Optional) GitHub PAT for auto-refreshing IG token |
| `INSTAGRAM_APP_SECRET` | (Optional) Meta app secret for token refresh |

---

## 🛑 STOP/START/PAUSE Mechanism

Control the pipeline by editing `stop.txt`:

| Flag | Effect |
|---|---|
| `START` | Normal operation |
| `STOP` | Halt all runs until changed |
| `PAUSE` | Skip the current run only |

```bash
echo "STOP" > stop.txt    # Emergency stop
echo "START" > stop.txt   # Resume
echo "PAUSE" > stop.txt   # Skip one run
```

---

## 📁 Folder Structure

```
├── .github/workflows/reel_automation.yml   # GitHub Actions cron
├── agents/                                 # All agent modules
│   ├── control_agent.py
│   ├── trend_agent.py
│   ├── news_agent.py
│   ├── content_agent.py
│   ├── video_agent.py
│   ├── audio_agent.py
│   ├── posting_agent.py
│   └── scheduler_agent.py
├── config/                                 # Configuration
│   ├── settings.py
│   ├── rss_feeds.py
│   └── templates.py
├── utils/                                  # Utilities
│   ├── logger.py
│   ├── dedup.py
│   └── token_refresh.py
├── assets/audio/                           # Royalty-free audio clips
├── assets/fonts/                           # Custom fonts (optional)
├── output/                                 # Generated videos (gitignored)
├── logs/                                   # Run logs (gitignored)
├── main.py                                 # Pipeline orchestrator
├── stop.txt                                # STOP/START control flag
├── topic_history.json                      # Deduplication history
└── requirements.txt                        # Python dependencies
```

---

## 🔧 Configuration

All settings are in `config/settings.py`. Key options:

| Setting | Default | Description |
|---|---|---|
| `MAX_POSTS_PER_DAY` | 3 | Daily post limit |
| `DEDUP_WINDOW_DAYS` | 7 | Days to remember used topics |
| `VIDEO_DURATION` | 15s | Reel length |
| `BACKGROUND_AUDIO_VOLUME` | 8% | Background music volume |
| `VEO_ENABLED` | true | Enable Veo AI video |
| `IMAGEN_ENABLED` | true | Enable Imagen AI images |

---

## 🔑 Instagram Graph API Setup

1. Create a **Meta Developer App** at [developers.facebook.com](https://developers.facebook.com)
2. Add the **Instagram Graph API** product
3. Link your **Instagram Business/Creator** account to a **Facebook Page**
4. Request permissions: `instagram_basic`, `instagram_content_publish`
5. Generate a **long-lived user access token** (valid 60 days)
6. The system auto-refreshes the token at day 50 (requires `INSTAGRAM_APP_SECRET`)

---

## 📊 Free Tier Limits

| Resource | Limit | Our Usage |
|---|---|---|
| GitHub Actions (public repo) | Unlimited | ~30 min/day ✅ |
| GitHub Actions (private repo) | 2,000 min/month | ~900 min/month ✅ |
| Gemini API | Generous free tier | ~3 calls/day ✅ |
| Instagram API | 25 calls/day | ~3 posts/day ✅ |

> **Tip**: Make the repo **public** for unlimited free GitHub Actions minutes. Secrets remain secure.

---

## 🐛 Troubleshooting

| Issue | Solution |
|---|---|
| `No trends found` | Google Trends RSS may be rate-limited. Wait and retry. |
| `No news match` | Topics are too niche. Reduce `min_match_score` in `news_agent.py`. |
| `FFmpeg not found` | Install FFmpeg: `sudo apt install ffmpeg` / `brew install ffmpeg` |
| `Token expired` | Generate new long-lived token and update GitHub secret. |
| `Daily limit reached` | Wait for next day. Adjust `MAX_POSTS_PER_DAY` in settings. |

---

## 📄 License

MIT License. Audio/video assets must be royalty-free.
