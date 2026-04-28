# Release v0.2 - Media

Theme: Briefly accepts media inputs. The chapter starts with YouTube captions.

## v0.2.0 - YouTube Captions

User-facing:

- `briefly <youtube-url>` produces a brief from the video's captions.
- `briefly <youtube-url> --extract` prints the transcript.
- `briefly <youtube-url> --json` returns structured output.
- Supports `watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`, `/live/` URLs.

Internal:

- New `briefly_core/youtube.py` module.
- Android-first InnerTube flow; watch-page fallback only when needed.
- Separate cache slot from HTML article extraction.
- Clean transcript text after entity decoding and `fmt=srv3` normalization.

Deferred to later v0.2.x slices:

- yt-dlp + audio transcription for videos without captions.
- `--timestamps`, `--language`, `--youtube` mode flag.
- Media file cache.
