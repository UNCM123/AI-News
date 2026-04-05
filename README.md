# AI News Aggregator

A web dashboard that scrapes AI news from Reddit, company blogs, RSS feeds, and Twitter/X every 6 hours, then uses Claude to summarize and categorize stories into a clean digest.

## Sources

- **Reddit:** r/artificial, r/MachineLearning, r/ChatGPT, r/OpenAI, r/LocalLLaMA, r/singularity, r/ClaudeAI, and more
- **Company blogs:** Anthropic, OpenAI, Google DeepMind, Google Gemini, Meta AI, Hugging Face, Mistral, xAI, Microsoft AI, NVIDIA, Cohere, ElevenLabs, Perplexity, Cursor, Lovable, and more
- **News sites:** VentureBeat, TechCrunch, The Verge, MIT Tech Review, Wired, Ars Technica
- **Twitter/X:** Key AI researchers and company accounts via Nitter RSS

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Fill in:
   - `ANTHROPIC_API_KEY` — get from https://console.anthropic.com
   - `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — create app at https://www.reddit.com/prefs/apps

3. **Run**
   ```bash
   python run.py
   ```
   Visit http://localhost:8000

## Features

- Scrapes all sources every 6 hours automatically
- Claude AI summarizes each article in 2-3 sentences
- Stories categorized into: Models & Research, Products & Tools, Industry News, Community
- Daily digest with AI-generated overview
- Browse past digests by date
- Manual refresh button on dashboard
- JSON API at `/api/digest/latest`
