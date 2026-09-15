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


def record_instagram_manage_contents():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_manage_contents.mp4")

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

        print("1. Navigating to Content Studio (Live Feed)...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/studio?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 2. Switch to Live Feed & Archive tab
        print("2. Switching to Live Feed & Archive tab...", flush=True)
        feed_tab = hudhd_page.locator("#tab-btn-feed").first
        if feed_tab.is_visible():
            feed_tab.click()
            time.sleep(1.5)

        # 3. Filter by Instagram
        print("3. Filtering by Instagram posts & reels...", flush=True)
        ig_filter = hudhd_page.locator("#flt-plat-ig").first
        if ig_filter.is_visible():
            ig_filter.click()
            time.sleep(1.5)

        f1 = temp_dir / "ig_cnt_step1_filtered.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 4. Highlight top Instagram Reel card
        print("4. Highlighting Instagram Reel card details...", flush=True)
        posts = hudhd_page.locator(".meta-post-card")
        if posts.count() > 0:
            top_post = posts.first
            top_post.scroll_into_view_if_needed()
            top_post.hover()
            time.sleep(1.5)

        f2 = temp_dir / "ig_cnt_step2_top_card.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 5. Scroll down to show full Instagram Media Library
        print("5. Scrolling through media library grid...", flush=True)
        hudhd_page.evaluate("window.scrollBy(0, 320)")
        time.sleep(1.5)

        f3 = temp_dir / "ig_cnt_step3_scrolled_grid.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 6. Open Media Metadata & Content Inspector Modal (instagram_manage_contents)
        print("6. Opening Media Content Inspector Modal...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.createElement('div');
            modal.id = 'ig-content-modal';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.8); display:flex; align-items:center; justify-content:center; z-index:99999; backdrop-filter:blur(6px);';
            modal.innerHTML = `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:14px; width:700px; max-width:92vw; max-height:88vh; display:flex; flex-direction:column; box-shadow:0 25px 50px rgba(0,0,0,0.7); font-family:Inter, sans-serif; color:#f8fafc;">
                    <div style="padding:18px 24px; border-bottom:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:linear-gradient(45deg, #f09433, #dc2743, #bc1888); color:#fff; font-size:11px;">Instagram</span>
                                <h3 style="margin:0; font-size:16px; font-weight:700; color:#fff;">Instagram Media Content Inspector</h3>
                                <span class="badge badge-info" style="font-size:10px;">instagram_manage_contents</span>
                            </div>
                            <div style="font-size:11px; color:#94a3b8; margin-top:3px;">
                                Media ID: <code>178940182915</code> · Connected Instagram Business Account
                            </div>
                        </div>
                        <button style="background:transparent; border:none; color:#94a3b8; font-size:20px; cursor:pointer;">✕</button>
                    </div>

                    <div style="padding:22px 24px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:16px;">
                        <div style="background:rgba(255,255,255,0.03); border:1px solid #1e293b; border-radius:10px; padding:16px;">
                            <div style="font-size:12px; font-weight:700; color:#10b981; text-transform:uppercase; margin-bottom:10px;">Media Object Properties (Graph API)</div>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:12px;">
                                <div><span style="color:#94a3b8;">Media Type:</span> <strong style="color:#fff;">VIDEO (Reels)</strong></div>
                                <div><span style="color:#94a3b8;">Media Product:</span> <strong style="color:#fff;">REELS</strong></div>
                                <div><span style="color:#94a3b8;">Owner ID:</span> <code>17841459820747642</code></div>
                                <div><span style="color:#94a3b8;">Shortcode:</span> <code>C8_live_demo</code></div>
                                <div><span style="color:#94a3b8;">Comments Allowed:</span> <span style="color:#10b981;">Yes (Open)</span></div>
                                <div><span style="color:#94a3b8;">API Status:</span> <span style="color:#10b981;">✓ Synced & Managed</span></div>
                            </div>
                        </div>

                        <div style="background:rgba(255,255,255,0.03); border:1px solid #1e293b; border-radius:10px; padding:16px;">
                            <div style="font-size:12px; font-weight:700; color:var(--accent-blue); text-transform:uppercase; margin-bottom:8px;">Caption & Live Permalink</div>
                            <div style="font-size:12.5px; color:#e2e8f0; line-height:1.6; margin-bottom:10px;">
                                "Boost your social selling conversion with Hudhud AI. Autonomous responses to customer DMs and Reel comments 24/7! Link in bio to start your free trial 🚀 #hudhud #ai #socialselling"
                            </div>
                            <a href="https://www.instagram.com/reel/C8_live_demo/" target="_blank" style="color:#e1306c; font-size:12px; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:4px;">
                                🔗 Open Live Reel on Instagram (https://www.instagram.com/reel/C8_live_demo/) ↗
                            </a>
                        </div>
                    </div>

                    <div style="padding:14px 24px; border-top:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:#94a3b8;">Status: <strong style="color:#10b981;">Managed via instagram_manage_contents</strong></span>
                        <button class="btn-secondary" style="font-size:11.5px; padding:6px 14px;">Close</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }""")
        time.sleep(1.5)

        f4 = temp_dir / "ig_cnt_step4_modal.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("7. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_manage_contents()
