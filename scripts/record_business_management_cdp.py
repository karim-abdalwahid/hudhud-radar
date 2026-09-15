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


def record_business_management():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/business_management.mp4")

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

        # Step 1: Settings - Managed Meta Business Assets & Diagnostics
        print("1. Navigating to Settings - Business Asset Diagnostics...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/settings?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        f1 = temp_dir / "biz_step1_settings_assets.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(4.0)

        # Step 2: Scroll to Facebook & Instagram One-Click Connect & Token Generator
        print("2. Showing Business Account Connection & Token Architecture...", flush=True)
        token_section = hudhd_page.locator(".panel-section").nth(1)
        if token_section.is_visible():
            token_section.scroll_into_view_if_needed()
            time.sleep(1.5)

        f2 = temp_dir / "biz_step2_connect_flow.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # Step 3: Navigate to Executive Overview Dashboard
        print("3. Navigating to Executive Overview Dashboard...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/dashboard?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        # Frame 3: Executive Metrics Strip
        f3 = temp_dir / "biz_step3_dashboard_kpis.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.0)

        # Step 4: Scroll down to Multi-Asset Activity (Recent Leads & Cross-Platform Content)
        print("4. Showing Cross-Asset Activity (Leads & Content)...", flush=True)
        leads_panel = hudhd_page.locator(".panel-section").first
        if leads_panel.is_visible():
            leads_panel.scroll_into_view_if_needed()
            time.sleep(1.5)

        f4 = temp_dir / "biz_step4_cross_asset_activity.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(5.0)

    # Render MP4
    print("5. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_business_management()
