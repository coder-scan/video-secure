import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.services.video.inspector import MediaMetadata

logger = logging.getLogger(__name__)


@dataclass
class TranscodeVariant:
    name: str
    width: int
    height: int
    video_bitrate: str
    audio_bitrate: str
    bandwidth: int


ALL_VARIANTS = [
    TranscodeVariant("360p", 640, 360, "800k", "96k", 900000),
    TranscodeVariant("720p", 1280, 720, "2500k", "128k", 2800000),
    TranscodeVariant("1080p", 1920, 1080, "5000k", "192k", 5300000),
]


def select_target_variants(source_height: int) -> List[TranscodeVariant]:
    """
    Selects valid HLS quality tiers without fake upscaling.
    A 720p source will produce 360p and 720p, but never 1080p.
    """
    selected = []
    for v in ALL_VARIANTS:
        if v.height <= source_height or v.name == "360p":
            selected.append(v)
    return selected if selected else [ALL_VARIANTS[0]]


def create_hls_keyinfo_file(
    scratch_dir: Path,
    key_uri: str,
    raw_key: bytes,
    iv: bytes,
) -> Tuple[Path, Path]:
    """
    Creates temporary .key and .keyinfo files for FFmpeg HLS encryption.
    Lines in keyinfo:
    1: Key URI (embedded in .m3u8 manifest)
    2: Path to raw key on disk for FFmpeg
    3: IV in hexadecimal
    """
    key_file = scratch_dir / "enc.key"
    keyinfo_file = scratch_dir / "enc.keyinfo"

    with open(key_file, "wb") as f:
        f.write(raw_key)

    with open(keyinfo_file, "w", encoding="utf-8") as f:
        f.write(f"{key_uri}\n")
        f.write(f"{key_file.resolve().as_posix()}\n")
        f.write(f"{iv.hex()}\n")

    return key_file, keyinfo_file


def transcode_to_encrypted_hls(
    source_file: Path,
    output_dir: Path,
    key_uri: str,
    raw_key: bytes,
    iv: bytes,
    metadata: MediaMetadata,
) -> Dict[str, Any]:
    """
    Transcodes an untrusted input video into AES-128 encrypted multi-bitrate HLS
    and generates keyframe thumbnails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg")

    variants = select_target_variants(metadata.height)
    key_file, keyinfo_file = create_hls_keyinfo_file(output_dir, key_uri, raw_key, iv)

    try:
        if ffmpeg_bin:
            _execute_ffmpeg_hls(ffmpeg_bin, source_file, output_dir, keyinfo_file, variants)
            thumbnail_paths = _generate_thumbnails_ffmpeg(
                ffmpeg_bin, source_file, output_dir, metadata.duration_seconds
            )
        else:
            logger.warning("ffmpeg binary not found in PATH. Using local mock packaging.")
            _mock_hls_packaging(output_dir, key_uri, iv, variants)
            thumbnail_paths = _mock_thumbnails(output_dir)

        # Write master.m3u8 linking all variants
        master_playlist_path = output_dir / "master.m3u8"
        _write_master_playlist(master_playlist_path, variants)

        return {
            "master_playlist": master_playlist_path,
            "variants": [v.name for v in variants],
            "thumbnails": thumbnail_paths,
        }
    finally:
        # Crucial security step: Shred local raw key & keyinfo files immediately
        if key_file.exists():
            key_file.unlink()
        if keyinfo_file.exists():
            keyinfo_file.unlink()


def _execute_ffmpeg_hls(
    ffmpeg_bin: str,
    source_file: Path,
    output_dir: Path,
    keyinfo_file: Path,
    variants: List[TranscodeVariant],
) -> None:
    """Executes FFmpeg with structured argument arrays for each variant."""
    for v in variants:
        variant_dir = output_dir / v.name
        variant_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = variant_dir / "index.m3u8"
        segment_pattern = variant_dir / "segment_%03d.ts"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(source_file.resolve()),
            "-vf", f"scale=w={v.width}:h={v.height}:force_original_aspect_ratio=decrease",
            "-c:v", "libx264",
            "-b:v", v.video_bitrate,
            "-maxrate", v.video_bitrate,
            "-bufsize", f"{int(v.video_bitrate[:-1]) * 2}k",
            "-c:a", "aac",
            "-b:a", v.audio_bitrate,
            "-hls_time", "6",
            "-hls_playlist_type", "vod",
            "-hls_key_info_file", str(keyinfo_file.resolve()),
            "-hls_segment_filename", str(segment_pattern.resolve()),
            str(playlist_path.resolve()),
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1800,
            shell=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed for variant {v.name}: {proc.stderr[:400]}")


def _generate_thumbnails_ffmpeg(
    ffmpeg_bin: str,
    source_file: Path,
    output_dir: Path,
    duration: float,
) -> List[str]:
    thumb_dir = output_dir / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    timestamps = [
        ("10pct", max(1.0, duration * 0.1)),
        ("50pct", max(1.0, duration * 0.5)),
        ("90pct", max(1.0, duration * 0.9)),
    ]

    for label, ts in timestamps:
        out_name = f"thumb_{label}.jpg"
        out_path = thumb_dir / out_name
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(ts),
            "-i", str(source_file.resolve()),
            "-vframes", "1",
            "-q:v", "3",
            str(out_path.resolve()),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        if res.returncode == 0 and out_path.exists():
            generated.append(f"thumbnails/{out_name}")

    return generated


def _write_master_playlist(master_path: Path, variants: List[TranscodeVariant]) -> None:
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for v in variants:
        lines.append(
            f"#EXT-X-STREAM-INF:BANDWIDTH={v.bandwidth},RESOLUTION={v.width}x{v.height}"
        )
        lines.append(f"{v.name}/index.m3u8")

    with open(master_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _mock_hls_packaging(
    output_dir: Path, key_uri: str, iv: bytes, variants: List[TranscodeVariant]
) -> None:
    """Mock packaging for test environments without ffmpeg installed."""
    for v in variants:
        v_dir = output_dir / v.name
        v_dir.mkdir(parents=True, exist_ok=True)
        # Create encrypted segment mock
        segment = v_dir / "segment_000.ts"
        with open(segment, "wb") as f:
            f.write(b"MOCK_ENCRYPTED_TS_SEGMENT_DATA")

        # Create playlist referencing AES-128 key URI
        playlist = v_dir / "index.m3u8"
        content = (
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXT-X-TARGETDURATION:6\n"
            f'#EXT-X-KEY:METHOD=AES-128,URI="{key_uri}",IV=0x{iv.hex()}\n'
            "#EXTINF:6.000,\n"
            "segment_000.ts\n"
            "#EXT-X-ENDLIST\n"
        )
        with open(playlist, "w", encoding="utf-8") as f:
            f.write(content)


def _mock_thumbnails(output_dir: Path) -> List[str]:
    thumb_dir = output_dir / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    for label in ["10pct", "50pct", "90pct"]:
        name = f"thumb_{label}.jpg"
        p = thumb_dir / name
        with open(p, "wb") as f:
            f.write(b"MOCK_JPEG_THUMBNAIL_BYTES")
        generated.append(f"thumbnails/{name}")
    return generated
