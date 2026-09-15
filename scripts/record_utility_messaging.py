import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright


def record_pages_utility_messaging():
    video_dir = Path("docs/APP_REVIEW/videos/raw")
    video_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_utility_messaging.mp4")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1920, "height": 1080},
            locale="en-US"
        )
        page = context.new_page()

        print("Navigating to automations page...", flush=True)
        page.goto("https://www.hudhd.com/automations?lang=en", wait_until="domcontentloaded")
        time.sleep(3)

        # 1. Look for the Facebook Messenger workflow card
        print("Finding Facebook Messenger workflow card...", flush=True)
        fb_card = page.locator(".wf-card").filter(has_text="Facebook").first
        if not fb_card.is_visible():
            fb_card = page.locator(".wf-card").first
        
        fb_card.scroll_into_view_if_needed()
        time.sleep(1.5)
        
        # Hover over the card to highlight it
        fb_card.hover()
        time.sleep(2)

        # 2. Click to open in canvas / view workflow details
        edit_btn = fb_card.locator("button, a").filter(has_text="Edit").first
        if edit_btn.is_visible():
            print("Opening visual canvas...", flush=True)
            edit_btn.click()
            time.sleep(3)
            
            # If canvas opened, show nodes
            nodes = page.locator(".canvas-node")
            if nodes.count() > 0:
                print(f"Showing {nodes.count()} canvas automation nodes...", flush=True)
                nodes.first.hover()
                time.sleep(2)
        else:
            fb_card.click()
            time.sleep(2)

        # 3. Trigger test run if visible
        test_btn = page.locator("button").filter(has_text="Test").first
        if test_btn.is_visible():
            print("Triggering test execution...", flush=True)
            test_btn.click()
            time.sleep(2)

        # 4. Hold screen for reviewer
        print("Holding final state for review...", flush=True)
        time.sleep(4)

        # Capture final screenshot
        screenshot_path = Path("docs/APP_REVIEW/videos/pages_utility_messaging.png")
        page.screenshot(path=str(screenshot_path), full_page=False)

        # Close context to flush video
        context.close()
        browser.close()

    # Find the newly recorded video in raw dir
    raw_videos = sorted(video_dir.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not raw_videos:
        raise RuntimeError("No recorded video found in raw directory!")
    
    raw_video = raw_videos[0]
    print(f"Recorded raw video: {raw_video.name}", flush=True)

    # Convert to standard MP4 with ffmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_mp4)
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Successfully generated: {out_mp4} ({out_mp4.stat().st_size / 1024 / 1024:.2f} MB)", flush=True)


if __name__ == "__main__":
    record_pages_utility_messaging()
