import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageSequence


def webp_to_mp4(webp_path: str, mp4_path: str, fps: int = 15):
    webp_p = Path(webp_path)
    mp4_p = Path(mp4_path)
    mp4_p.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(webp_p)
    n_frames = getattr(img, 'n_frames', 1)
    
    # Calculate duration
    duration = img.info.get('duration', 100)
    actual_fps = max(1, round(1000 / duration)) if duration > 0 else fps
    # Limit fps between 5 and 30 for smooth playback
    actual_fps = min(max(actual_fps, 5), 30)

    width, height = img.size
    out_width = width if width % 2 == 0 else width - 1
    out_height = height if height % 2 == 0 else height - 1

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{out_width}x{out_height}',
        '-pix_fmt', 'rgb24',
        '-r', str(actual_fps),
        '-i', '-',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        str(mp4_p)
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for frame in ImageSequence.Iterator(img):
        frame_rgb = frame.convert('RGB')
        if frame_rgb.size != (out_width, out_height):
            frame_rgb = frame_rgb.resize((out_width, out_height), Image.Resampling.LANCZOS)
        proc.stdin.write(frame_rgb.tobytes())
    proc.stdin.close()
    stdout, stderr = proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode('utf-8', errors='ignore')}")
    
    print(f"Successfully converted: {mp4_p.name} ({n_frames} frames at {actual_fps} fps, size: {mp4_p.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_webp_to_mp4.py <input.webp> <output.mp4>")
        sys.exit(1)
    webp_to_mp4(sys.argv[1], sys.argv[2])
