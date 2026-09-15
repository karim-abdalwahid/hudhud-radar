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


def record_pages_messaging():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_messaging.mp4")

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

        print("1. Navigating to Live Inbox...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/inbox?lang=en")
        hudhd_page.wait_for_selector("#threads-list", timeout=15000)
        time.sleep(2)

        # Frame 1: Inbox loaded
        f1 = temp_dir / "msg_step1_inbox.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.0)

        # 2. Click Messenger Filter
        print("2. Filtering for Messenger conversations...", flush=True)
        msg_filter = hudhd_page.locator(".filter-chip").filter(has_text="Messenger").first
        if msg_filter.is_visible():
            msg_filter.click()
            time.sleep(1)

        f2 = temp_dir / "msg_step2_filtered.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(3.0)

        # 3. Select Conversation
        print("3. Selecting active customer conversation...", flush=True)
        first_thread = hudhd_page.locator("#threads-list .conv-item").first
        if first_thread.is_visible():
            first_thread.click()
            time.sleep(1.5)

        f3 = temp_dir / "msg_step3_chat_open.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(3.5)

        # 4. Type Page response
        print("4. Typing Facebook Page response message...", flush=True)
        input_box = hudhd_page.locator(".chat-input-row input, .chat-input-row textarea, input.chat-text-input").last
        if input_box.is_visible():
            input_box.click()
            input_box.fill("Hello! Thanks for contacting us on Messenger. Our team is available 24/7 to assist you. How can we help you today?")
            time.sleep(1)

        f4 = temp_dir / "msg_step4_typed.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(3.5)

        # 5. Send message
        print("5. Sending message on Messenger...", flush=True)
        send_btn = hudhd_page.locator("button.send-btn, .chat-input-row button").first
        if send_btn.is_visible():
            send_btn.click()
            time.sleep(2)
        else:
            input_box.press("Enter")
            time.sleep(2)

        # Frame 6: Final delivered message state
        f5 = temp_dir / "msg_step5_delivered.png"
        hudhd_page.screenshot(path=str(f5))
        frames.append(f5)
        durations.append(5.0)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_messaging()
