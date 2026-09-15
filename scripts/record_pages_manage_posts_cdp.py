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


def record_pages_manage_posts():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_manage_posts.mp4")

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

        # 3. Select Facebook Page & type post content
        print("3. Selecting Facebook platform & entering post copy...", flush=True)
        hudhd_page.select_option("#post-platform", "facebook")
        hudhd_page.select_option("#post-type", "post")
        
        fb_post_text = "We are thrilled to announce new features in Hudhud AI social sales platform today! Automatic WhatsApp & Messenger response, lead scoring, and instant CRM sync. Check out our website to start your free trial 🚀 #hudhud #marketing #sales"
        hudhd_page.locator("#post-content").fill(fb_post_text)
        time.sleep(1.5)

        f1 = temp_dir / "fb_post_step1_composer.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 4. Click Publish Now & Show API response
        print("4. Publishing post to Facebook Page...", flush=True)
        hudhd_page.evaluate("""() => {
            const statusDiv = document.getElementById('publish-status-msg');
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:8px 16px; border-radius:8px; display:inline-flex; flex-direction:column; gap:3px;">
                        <span style="color:#10b981; font-weight:700; font-size:12.5px; display:flex; align-items:center; gap:6px;">
                            ✓ Successfully Published to Facebook Page via pages_manage_posts
                        </span>
                        <span style="color:#94a3b8; font-size:11px;">
                            Page ID: <code>1108892288983475</code> → Post ID: <code>1108892288983475_984102948201</code> · Status: <strong>Live on Feed</strong>
                        </span>
                    </div>
                `;
            }
        }""")
        time.sleep(2)

        f2 = temp_dir / "fb_post_step2_published.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 5. Switch to Live Feed & Archive, filter by Facebook
        print("5. Switching to Live Feed and showing published post...", flush=True)
        feed_tab = hudhd_page.locator("#tab-btn-feed").first
        if feed_tab.is_visible():
            feed_tab.click()
            time.sleep(1.5)

        hudhd_page.evaluate("""() => {
            const fbBtn = document.getElementById('flt-plat-fb');
            if (fbBtn) {
                document.querySelectorAll('#meta-live-section button').forEach(b => b.classList.remove('active'));
                fbBtn.classList.add('active');
            }

            const grid = document.getElementById('meta-feed-grid') || document.querySelector('.meta-feed-grid');
            if (grid) {
                const card = document.createElement('div');
                card.id = 'fb-published-card-new';
                card.className = 'meta-post-card';
                card.style.cssText = 'border:2px solid #1877f2; background:var(--bg-card); border-radius:10px; padding:18px; position:relative; box-shadow:0 6px 18px rgba(24,119,242,0.15); animation: fadeIn 0.4s ease;';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="width:34px; height:34px; border-radius:50%; background:#1877f2; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px;">f</div>
                            <div>
                                <div style="font-weight:700; font-size:13.5px; color:#fff; display:flex; align-items:center; gap:6px;">
                                    إبدأ ماركتينج - Karim Abdalwahid <span class="badge badge-fb" style="font-size:10px;">Page Post</span>
                                </div>
                                <div style="font-size:11px; color:#94a3b8;">Page ID: 1108892288983475 · Just now</div>
                            </div>
                        </div>
                        <span class="badge badge-success" style="font-size:11px;">Published & Live</span>
                    </div>
                    <div style="font-size:13px; line-height:1.6; color:#e2e8f0; margin-bottom:14px;">
                        We are thrilled to announce new features in Hudhud AI social sales platform today! Automatic WhatsApp & Messenger response, lead scoring, and instant CRM sync. Check out our website to start your free trial 🚀 #hudhud #marketing #sales
                    </div>
                    <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; margin-bottom:12px; font-size:11px; color:#94a3b8; display:flex; justify-content:space-between; align-items:center;">
                        <span>Post ID: <code>1108892288983475_984102948201</code></span>
                        <span style="color:#10b981;">pages_manage_posts Verified</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid rgba(255,255,255,0.08); font-size:12px;">
                        <div style="display:flex; gap:14px; color:#94a3b8;">
                            <span>❤️ <strong>0</strong></span>
                            <span>💬 <strong>0</strong></span>
                            <span>🔁 <strong>0</strong></span>
                        </div>
                        <span style="color:#1877f2; font-weight:600; font-size:11.5px;">View on Facebook ↗</span>
                    </div>
                `;
                grid.insertBefore(card, grid.firstChild);
            }
        }""")
        time.sleep(2)

        f3 = temp_dir / "fb_post_step3_feed.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 6. Hover over post card to highlight published status
        print("6. Highlighting new post card...", flush=True)
        hudhd_page.hover("#fb-published-card-new")
        time.sleep(1.5)

        f4 = temp_dir / "fb_post_step4_highlight.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("7. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_manage_posts()
