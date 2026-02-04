# DiverSSe

Diverse Spanish Speech

## Setup environment

Install dependencies:

```bash
pip install yt-dlp
```

You also need [Deno](https://deno.land/) for yt-dlp to work properly with YouTube:

```bash
curl -fsSL https://deno.land/install.sh | sh
```

After installing, restart your terminal or run:

```bash
export PATH="$HOME/.deno/bin:$PATH"
```

## Download audio

The script reads a TSV file with YouTube links and timestamps, downloads the audio, and extracts the segments.

```bash
python src/download_audio.py --tsv_file data/diversse.tsv
```

Output files are saved to `data/audio/` organized by disease folder (e.g., `data/audio/ALS/`).
