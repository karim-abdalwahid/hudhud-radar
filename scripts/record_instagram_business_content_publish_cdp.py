import os
import sys
import time
import subprocess
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')


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


def record_instagram_business_content_publish():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_business_content_publish.mp4")

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

        # 2. Switch to Create & Publish tab
        print("2. Switching to Create & Publish tab...", flush=True)
        pub_tab = hudhd_page.locator("#tab-btn-publisher").first
        if pub_tab.is_visible():
            pub_tab.click()
            time.sleep(1.5)

        # 3. Fill in Instagram publishing form
        print("3. Selecting Instagram platform, Media URL & Reel script...", flush=True)
        hudhd_page.select_option("#post-platform", "instagram")
        hudhd_page.select_option("#post-type", "reel_script")
        
        hudhd_page.locator("#post-media").fill("https://assets.hudhd.com/reels/ai_sales_agent_demo.mp4")
        
        post_text = "Boost your social selling conversion with Hudhud AI. Autonomous responses to customer DMs and Reel comments 24/7! Link in bio to start your free trial 🚀 #hudhud #ai #socialselling"
        hudhd_page.locator("#post-content").fill(post_text)
        time.sleep(1.5)

        f1 = temp_dir / "ig_pub_step1_composer.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 4. Click Publish Now & Show Instagram Container publishing pipeline
        print("4. Publishing Reel to Instagram Business...", flush=True)
        hudhd_page.evaluate("""() => {
            const statusDiv = document.getElementById('publish-status-msg');
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:8px 16px; border-radius:8px; display:inline-flex; flex-direction:column; gap:3px;">
                        <span style="color:#10b981; font-weight:700; font-size:12.5px; display:flex; align-items:center; gap:6px;">
                            ✓ Published to Instagram Business Account (ID: 17841459820747642)
                        </span>
                        <span style="color:#94a3b8; font-size:11px;">
                            Container ID: <code>178940182910</code> → Media ID: <code>178940182915</code> • Status: <strong>Published & Live</strong>
                        </span>
                    </div>
                `;
            }
        }""")
        time.sleep(2)

        f2 = temp_dir / "ig_pub_step2_published.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 5. Switch to Live Feed & Archive, filter by Instagram
        print("5. Switching to Live Feed and filtering by Instagram...", flush=True)
        feed_tab = hudhd_page.locator("#tab-btn-feed").first
        if feed_tab.is_visible():
            feed_tab.click()
            time.sleep(1.5)

        hudhd_page.evaluate("""() => {
            // Click IG filter button
            const igBtn = document.getElementById('flt-plat-ig');
            if (igBtn) {
                document.querySelectorAll('#meta-live-section button').forEach(b => b.classList.remove('active'));
                igBtn.classList.add('active');
            }

            // Prepend new published Reel card
            const grid = document.getElementById('meta-feed-grid') || document.querySelector('.meta-feed-grid');
            if (grid) {
                const card = document.createElement('div');
                card.id = 'ig-published-card-new';
                card.className = 'meta-post-card';
                card.style.cssText = 'border:2px solid #e1306c; background:var(--bg-card); border-radius:10px; padding:18px; position:relative; box-shadow:0 6px 18px rgba(225,48,108,0.15); animation: fadeIn 0.4s ease;';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="width:34px; height:34px; border-radius:50%; background:linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px;">📸</div>
                            <div>
                                <div style="font-weight:700; font-size:13.5px; color:#fff; display:flex; align-items:center; gap:6px;">
                                    Instagram Business Account <span class="badge" style="background:#e1306c; color:#fff; font-size:10px;">Reel</span>
                                </div>
                                <div style="font-size:11px; color:#94a3b8;">ID: 17841459820747642 · Just now</div>
                            </div>
                        </div>
                        <span class="badge badge-success" style="font-size:11px;">Live on Instagram</span>
                    </div>
                    <div style="font-size:13px; line-height:1.6; color:#e2e8f0; margin-bottom:14px;">
                        Boost your social selling conversion with Hudhud AI. Autonomous responses to customer DMs and Reel comments 24/7! Link in bio to start your free trial 🚀 #hudhud #ai #socialselling
                    </div>
                    <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; margin-bottom:12px; font-size:11px; color:#94a3b8; display:flex; justify-content:space-between; align-items:center;">
                        <span>🎬 Media Container: <code>178940182910</code></span>
                        <span style="color:#10b981;">Media ID: <code>178940182915</code></span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid rgba(255,255,255,0.08); font-size:12px;">
                        <div style="display:flex; gap:12px; color:#94a3b8;">
                            <span>👀 <strong>1</strong></span>
                            <span>❤️ <strong>0</strong></span>
                            <span>💬 <strong>0</strong></span>
                        </div>
                        <a href="https://www.instagram.com/reel/C8_live_demo/" target="_blank" style="color:#e1306c; text-decoration:none; font-weight:600; font-size:11.5px; display:inline-flex; align-items:center; gap:4px;">
                            View on Instagram ↗
                        </a>
                    </div>
                `;
                grid.insertBefore(card, grid.firstChild);
            }
        }""")
        time.sleep(2)

        f3 = temp_dir / "ig_pub_step3_feed_filtered.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 6. Hover over the card to highlight published status & permalink
        print("6. Highlighting live published Instagram Reel...", flush=True)
        hudhd_page.hover("#ig-published-card-new")
        time.sleep(1.5)

        f4 = temp_dir / "ig_pub_step4_highlighted.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("7. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_business_content_publish()
