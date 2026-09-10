# Strikebot — Competitive Esports & MMR Management Bot

A custom Python Discord bot built to automate match tracking, skill rating (MMR) calculations, and administrative server moderation for online gaming leagues.

## Key Features

- **Dynamic Matchmaking Rating (MMR):**
  - Tracks rolling 10-match partner MMR averages (`^pavg10`).
  - Executes end-of-season rank squishing (`^seasonreset`) to reset skill distributions closer to the median.
  - Automatically exports seasonal player data into structured CSV files.
- **Automated Moderation & Strike System:**
  - Manages player penalties with dynamic strike limits (`^setlimit`, `^addstrike`, `^removestrike`).
  - Logs match summaries and triggers automated role notifications for player rank promotions/demotions (`^announce`).
- **Asynchronous Architecture:** Built using `discord.py` for real-time handling during high-traffic events.

## Tech Stack & Tools

- **Language:** Python
- **Libraries:** `discord.py`, `aiohttp`
- **Development Tools:** AI-Assisted Prototyping & Prompt Engineering (LLMs), CLI Local Deployment

## Command Overview

| Command | Description |
| :--- | :--- |
| `^addstrike` / `^removestrike` | Adds or removes player penalty strikes |
| `^setlimit` | Sets the maximum strike threshold before moderation action |
| `^pavg10` | Calculates rolling 10-match partner MMR average |
| `^seasonreset` | Compresses seasonal MMR toward median (Base: 1250, Squish: 0.5) and generates a CSV export |
| `^announce` | Pings players who earned a promotion or demotion |
| `^lowest` | Displays the lowest current MMR in the division |

## Setup & Local Execution

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/osmanyousef01-cell/Strikebot.git](https://github.com/osmanyousef01-cell/Strikebot.git)
   cd Strikebot
