from __future__ import annotations

import asyncio
from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import httpx

from briefly_core.content import ExtractedContent

_DEFAULT_TIMEOUT_SECONDS = 15.0
_ANDROID_CLIENT_VERSION = "20.10.38"
_DEFAULT_ANDROID_INNERTUBE_API_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
_YOUTUBE_HOST_PATTERN = re.compile(
    r"(?:^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com)$",
    re.IGNORECASE,
)
_VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}")
_INNERTUBE_API_KEY_PATTERN = re.compile(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"')
_FMT_QUERY_PATTERN = re.compile(r"([?&])fmt=[^&]*(&|$)")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_DEFAULT_GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
_GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


@dataclass(frozen=True)
class CaptionSegment:
    start_ms: int
    duration_ms: int
    text: str


@dataclass(frozen=True)
class YoutubeTranscript:
    video_id: str
    title: str | None
    language_code: str | None
    is_auto_generated: bool
    text: str
    segments: tuple[CaptionSegment, ...]


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return bool(host and _YOUTUBE_HOST_PATTERN.search(host))


def parse_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host or not _YOUTUBE_HOST_PATTERN.search(host):
        return None

    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/", 1)[0]
        return candidate if _VIDEO_ID_PATTERN.fullmatch(candidate) else None

    if parsed.path == "/watch":
        values = parse_qs(parsed.query).get("v")
        if values and _VIDEO_ID_PATTERN.fullmatch(values[0]):
            return values[0]
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live", "v"}:
        candidate = parts[1]
        return candidate if _VIDEO_ID_PATTERN.fullmatch(candidate) else None

    return None


def extract_innertube_api_key(html: str) -> str | None:
    match = _INNERTUBE_API_KEY_PATTERN.search(html)
    return match.group(1) if match else None


def extract_initial_player_response(html: str) -> dict[str, Any] | None:
    needle = "ytInitialPlayerResponse"
    cursor = html.find(needle)
    while cursor != -1:
        brace_start = html.find("{", cursor + len(needle))
        if brace_start == -1:
            return None
        brace_end = _find_matching_brace(html, brace_start)
        if brace_end is None:
            return None
        try:
            parsed = json.loads(html[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            cursor = html.find(needle, brace_end + 1)
            continue
        return parsed if isinstance(parsed, dict) else None
    return None


def pick_caption_track(
    player_response: dict[str, Any],
    *,
    skip_auto_generated: bool = False,
) -> dict[str, Any] | None:
    captions = player_response.get("captions")
    renderer: Any = None
    if isinstance(captions, dict):
        renderer = captions.get("playerCaptionsTracklistRenderer")
    if renderer is None:
        renderer = player_response.get("playerCaptionsTracklistRenderer")
    if not isinstance(renderer, dict):
        return None

    manual = renderer.get("captionTracks") or []
    automatic = renderer.get("automaticCaptions") or []

    candidates: list[dict[str, Any]] = []
    for track in manual:
        if isinstance(track, dict):
            candidates.append(track)
    if not skip_auto_generated:
        for track in automatic:
            if isinstance(track, dict):
                candidates.append(track)

    if not candidates:
        return None

    def sort_key(track: dict[str, Any]) -> tuple[int, int]:
        kind_value = track.get("kind")
        kind = kind_value if isinstance(kind_value, str) else ""
        is_asr = 1 if kind == "asr" else 0
        lang_value = track.get("languageCode")
        lang = lang_value if isinstance(lang_value, str) else ""
        is_english = 0 if lang == "en" or lang.startswith("en-") else 1
        return (is_asr, is_english)

    sorted_tracks = sorted(candidates, key=sort_key)
    seen: set[str] = set()
    for track in sorted_tracks:
        lang_value = track.get("languageCode")
        lang = lang_value.lower() if isinstance(lang_value, str) else ""
        if lang and lang in seen:
            continue
        if lang:
            seen.add(lang)
        return track
    return None


def parse_caption_xml(xml: str) -> tuple[CaptionSegment, ...]:
    text = xml.strip()
    if not text:
        return ()
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return ()

    segments: list[CaptionSegment] = []
    for element in root.iter("text"):
        raw = "".join(element.itertext()) or ""
        cleaned = _decode_caption_text(raw)
        if not cleaned:
            continue
        start_ms = _parse_time_attr(element.get("start"))
        duration_ms = _parse_time_attr(element.get("dur"))
        segments.append(CaptionSegment(start_ms=start_ms, duration_ms=duration_ms, text=cleaned))
    return tuple(segments)


async def fetch_player_response_android(
    *,
    client: httpx.AsyncClient,
    api_key: str,
    video_id: str,
) -> dict[str, Any] | None:
    response = await client.post(
        "https://www.youtube.com/youtubei/v1/player",
        params={"key": api_key},
        headers={
            "Content-Type": "application/json",
            "User-Agent": _DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json",
        },
        json={
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": _ANDROID_CLIENT_VERSION,
                },
            },
            "videoId": video_id,
        },
    )
    if response.status_code != 200:
        return None
    try:
        parsed = response.json()
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def fetch_youtube_transcript(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> YoutubeTranscript:
    video_id = parse_video_id(url)
    if video_id is None:
        raise ValueError(f"Unsupported YouTube URL: {url}")

    owns_client = client is None
    active_client = client or httpx.AsyncClient(
        follow_redirects=True,
        timeout=_DEFAULT_TIMEOUT_SECONDS,
        headers={
            "User-Agent": _DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        player_response: dict[str, Any] | None = await fetch_player_response_android(
            client=active_client,
            api_key=_DEFAULT_ANDROID_INNERTUBE_API_KEY,
            video_id=video_id,
        )
        track = (
            pick_caption_track(player_response) if isinstance(player_response, dict) else None
        )

        if track is None:
            scraped_key = await _scrape_innertube_api_key(active_client, video_id)
            if scraped_key is not None and scraped_key != _DEFAULT_ANDROID_INNERTUBE_API_KEY:
                fallback_response = await fetch_player_response_android(
                    client=active_client,
                    api_key=scraped_key,
                    video_id=video_id,
                )
                if fallback_response is not None:
                    track = pick_caption_track(fallback_response)
                    if track is not None:
                        player_response = fallback_response

        if track is None:
            title = (
                _extract_video_title(player_response) if isinstance(player_response, dict) else None
            )
            try:
                groq_transcript = await _fetch_groq_whisper_transcript(
                    url,
                    video_id=video_id,
                    title=title,
                    client=active_client,
                )
            except Exception as error:
                raise ValueError(
                    f"No captions available for this video: {video_id}. "
                    f"Groq Whisper fallback failed: {error}"
                ) from error
            if groq_transcript is not None:
                return groq_transcript
            raise ValueError(f"No captions available for this video: {video_id}")

        base_url = track.get("baseUrl")
        if not isinstance(base_url, str) or not base_url:
            raise ValueError(f"Caption track missing URL for video: {video_id}")

        caption_response = await active_client.get(_normalize_caption_url(base_url))
        if caption_response.status_code != 200:
            raise ValueError(
                f"Failed to fetch caption track for {video_id}: "
                f"HTTP {caption_response.status_code}"
            )

        segments = parse_caption_xml(caption_response.text)
        if not segments:
            raise ValueError(f"Caption track was empty for {video_id}")

        title = (
            _extract_video_title(player_response) if isinstance(player_response, dict) else None
        )
        language_code = (
            track.get("languageCode") if isinstance(track.get("languageCode"), str) else None
        )
        is_asr = track.get("kind") == "asr"
        joined = " ".join(segment.text for segment in segments)

        return YoutubeTranscript(
            video_id=video_id,
            title=title,
            language_code=language_code,
            is_auto_generated=is_asr,
            text=joined,
            segments=segments,
        )
    finally:
        if owns_client:
            await active_client.aclose()


def transcript_to_extracted_content(
    transcript: YoutubeTranscript,
    *,
    source_url: str,
    timestamps: bool = False,
) -> ExtractedContent:
    return ExtractedContent(
        source=source_url,
        title=transcript.title,
        text=transcript_to_text(transcript, timestamps=timestamps),
    )


def transcript_to_text(transcript: YoutubeTranscript, *, timestamps: bool = False) -> str:
    if not timestamps:
        return transcript.text

    return "\n".join(
        f"{_format_timestamp(segment.start_ms)} {segment.text}"
        for segment in transcript.segments
    )


async def _fetch_groq_whisper_transcript(
    url: str,
    *,
    video_id: str,
    title: str | None,
    client: httpx.AsyncClient,
) -> YoutubeTranscript | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    with tempfile.TemporaryDirectory(prefix="briefly-youtube-") as temp_dir:
        audio_path = await _download_youtube_audio(url, Path(temp_dir))
        return await _transcribe_audio_with_groq(
            audio_path,
            video_id=video_id,
            title=title,
            api_key=api_key,
            client=client,
        )


async def _download_youtube_audio(url: str, output_dir: Path) -> Path:
    ytdlp = os.environ.get("YT_DLP_PATH") or "yt-dlp"
    output_template = str(output_dir / "%(id)s.%(ext)s")
    try:
        process = await asyncio.create_subprocess_exec(
            ytdlp,
            "--no-playlist",
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            output_template,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise RuntimeError("yt-dlp was not found. Set YT_DLP_PATH or install yt-dlp.") from error
    _, stderr = await process.communicate()
    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "yt-dlp failed to download audio.")

    audio_files = sorted(path for path in output_dir.iterdir() if path.is_file())
    if not audio_files:
        raise RuntimeError("yt-dlp did not produce an audio file.")
    return audio_files[0]


async def _transcribe_audio_with_groq(
    audio_path: Path,
    *,
    video_id: str,
    title: str | None,
    api_key: str,
    client: httpx.AsyncClient,
) -> YoutubeTranscript:
    model = os.environ.get("BRIEFLY_GROQ_WHISPER_MODEL") or _DEFAULT_GROQ_WHISPER_MODEL
    files = {
        "file": (
            audio_path.name,
            audio_path.read_bytes(),
            _audio_content_type(audio_path),
        )
    }
    response = await client.post(
        _GROQ_TRANSCRIPTIONS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        data={
            "model": model,
            "response_format": "verbose_json",
            "temperature": "0",
        },
        files=files,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Groq transcription failed: HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Groq transcription returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Groq transcription returned an invalid response.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Groq transcription returned empty text.")

    segments = _groq_segments_to_caption_segments(payload)
    if not segments:
        segments = (CaptionSegment(start_ms=0, duration_ms=0, text=text.strip()),)

    return YoutubeTranscript(
        video_id=video_id,
        title=title,
        language_code=None,
        is_auto_generated=True,
        text=text.strip(),
        segments=segments,
    )


def _groq_segments_to_caption_segments(payload: dict[str, Any]) -> tuple[CaptionSegment, ...]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        return ()

    segments: list[CaptionSegment] = []
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        start_ms = _seconds_to_ms(segment.get("start"))
        end_ms = _seconds_to_ms(segment.get("end"))
        segments.append(
            CaptionSegment(
                start_ms=start_ms,
                duration_ms=max(0, end_ms - start_ms),
                text=text.strip(),
            )
        )
    return tuple(segments)


def _seconds_to_ms(raw: object) -> int:
    if not isinstance(raw, int | float) or isinstance(raw, bool):
        return 0
    return max(0, int(raw * 1000))


def _audio_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".ogg":
        return "audio/ogg"
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".webm":
        return "audio/webm"
    return "application/octet-stream"


def _normalize_caption_url(url: str) -> str:
    cleaned = _FMT_QUERY_PATTERN.sub(lambda match: match.group(1) if match.group(2) else "", url)
    return cleaned.rstrip("?&")


async def _scrape_innertube_api_key(client: httpx.AsyncClient, video_id: str) -> str | None:
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        response = await client.get(watch_url)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    return extract_innertube_api_key(response.text)


def _find_matching_brace(text: str, open_index: int) -> int | None:
    depth = 0
    in_string = False
    escape = False
    for index in range(open_index, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if in_string:
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _decode_caption_text(raw: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", html.unescape(raw)).strip()


def _parse_time_attr(raw: str | None) -> int:
    if raw is None:
        return 0
    try:
        return int(float(raw) * 1000)
    except ValueError:
        return 0


def _extract_video_title(player_response: dict[str, Any]) -> str | None:
    details = player_response.get("videoDetails")
    if isinstance(details, dict):
        title = details.get("title")
        if isinstance(title, str):
            cleaned = title.strip()
            return cleaned or None
    return None


def _format_timestamp(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"[{hours}:{minutes:02}:{seconds:02}]"
    return f"[{minutes}:{seconds:02}]"
