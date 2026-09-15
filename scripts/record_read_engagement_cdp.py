import os
import sys
import time
import subprocess
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright


def render_frames_to_mp4(frames, durations, out_path, fps=10):
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    first = Image.open(frames[0])
    w, h = first.size
    w = w if w % 2 == 0 else w - 1
    h = h if h % 2 == 0 else h - 1

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_p)
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for f_path, dur in zip(frames, durations):
        img = Image.open(f_path).convert("RGB")
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        raw = img.tobytes()
        for _ in range(int(dur * fps)):
            proc.stdin.write(raw)
    proc.stdin.close()
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode('utf-8', errors='ignore')}")
    print(f"Rendered: {out_p.name} ({out_p.stat().st_size / 1024 / 1024:.2f} MB)")


def record_pages_read_engagement():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_read_engagement.mp4")

    frames = []
    durations = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        hudhd_page = None
        for pg in context.pages:
            if "hudhd.com" in pg.url:
                hudhd_page = pg
                break
        
        if not hudhd_page:
            hudhd_page = context.new_page()

        print("1. Navigating to Content Studio...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/studio?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 2. Switch to Live Feed & Archive tab
        print("2. Switching to Live Feed & Archive view...", flush=True)
        feed_tab = hudhd_page.locator("#tab-btn-feed").first
        if feed_tab.is_visible():
            feed_tab.click()
            time.sleep(2)

        f1 = temp_dir / "eng_step1_live_feed.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Click Facebook filter button
        print("3. Filtering for Facebook Page posts...", flush=True)
        fb_filter = hudhd_page.locator("#flt-plat-fb").first
        if fb_filter.is_visible():
            fb_filter.click()
            time.sleep(2)

        f2 = temp_dir / "eng_step2_fb_filtered.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # 4. Scroll to highlight post engagement metrics (Likes, Comments, Shares)
        print("4. Highlighting Facebook post engagement metrics...", flush=True)
        posts = hudhd_page.locator(".meta-post-card")
        if posts.count() > 0:
            first_post = posts.first
            first_post.scroll_into_view_if_needed()
            first_post.hover()
            time.sleep(1.5)

        f3 = temp_dir / "eng_step3_post_metrics.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Navigate to Analytics & Reports
        print("5. Navigating to Analytics & Reports...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/analytics?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        f4 = temp_dir / "eng_step4_analytics_kpis.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(5.0)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_read_engagement()
