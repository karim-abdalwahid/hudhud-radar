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


def record_pages_utility_messaging():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_utility_messaging.mp4")

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

        print("1. Navigating to Automations...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/automations?lang=en")
        hudhd_page.wait_for_selector(".wf-card", timeout=15000)
        time.sleep(1.5)

        # Frame 1: Overview
        f1 = temp_dir / "step1_overview.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.0)

        # 2. Focus on Facebook Messenger card
        print("2. Focusing on Facebook Messenger card...", flush=True)
        fb_card = hudhd_page.locator(".wf-card").nth(1)
        fb_card.scroll_into_view_if_needed()
        time.sleep(1)
        
        f2 = temp_dir / "step2_fb_card_focus.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(3.5)

        # 3. Open Rules Modal
        print("3. Opening Workflow Rules Modal...", flush=True)
        rules_btn = fb_card.locator("button").filter(has_text="Rules").first
        rules_btn.click()
        time.sleep(2)
        
        f3 = temp_dir / "step3_rules_modal.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(5.0)

        # Close rules modal via JS
        hudhd_page.evaluate("if(typeof closeWorkflowConfigModal==='function')closeWorkflowConfigModal();")
        time.sleep(1.5)

        # 4. Open Visual Canvas
        print("4. Opening Visual Canvas...", flush=True)
        canvas_btn = fb_card.locator("button").filter(has_text="Canvas").first
        canvas_btn.click()
        time.sleep(2.5)
        
        f4 = temp_dir / "step4_canvas_view.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(5.0)

        # Exit canvas back to list
        hudhd_page.evaluate("if(typeof exitCanvasToList==='function')exitCanvasToList();")
        time.sleep(1.5)

        f5 = temp_dir / "step5_final.png"
        hudhd_page.screenshot(path=str(f5))
        frames.append(f5)
        durations.append(2.5)

    # Render MP4
    print("5. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_utility_messaging()
