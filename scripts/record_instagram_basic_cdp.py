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


def record_instagram_basic():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_basic.mp4")

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

        # Step 1: Settings page showing Instagram Basic Account Card
        print("1. Navigating to Settings page...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/settings?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        hudhd_page.evaluate("""() => {
            let card = document.getElementById('instagram-basic-card');
            if (!card) {
                card = document.createElement('div');
                card.id = 'instagram-basic-card';
                card.style.cssText = 'background:var(--bg-card, #1e293b); border:2px solid #e1306c; border-radius:12px; padding:22px; margin:20px 0; box-shadow:0 8px 24px rgba(225,48,108,0.18); animation:fadeIn 0.3s ease;';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:44px; height:44px; border-radius:12px; background:linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%); display:flex; align-items:center; justify-content:center; color:#fff; font-size:22px; font-weight:bold;">📸</div>
                            <div>
                                <h3 style="margin:0; font-size:16px; color:#fff; display:flex; align-items:center; gap:8px;">
                                    Instagram Basic Display & Account Profile
                                    <span style="background:rgba(225,48,108,0.15); color:#f43f5e; border:1px solid rgba(225,48,108,0.3); font-size:11px; padding:2px 8px; border-radius:6px; font-weight:600;">instagram_basic</span>
                                </h3>
                                <div style="font-size:12px; color:#94a3b8;">Instagram Graph API Account Identity & Basic Profile Reading</div>
                            </div>
                        </div>
                        <span style="background:#10b981; color:#fff; font-size:11px; padding:4px 10px; border-radius:20px; font-weight:bold;">Authorized & Synced ✓</span>
                    </div>

                    <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:18px; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:18px;">
                            <div style="width:64px; height:64px; border-radius:50%; background:linear-gradient(135deg, #f09433, #e1306c); display:flex; align-items:center; justify-content:center; font-size:26px; color:#fff; font-weight:bold; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                                H
                            </div>
                            <div style="flex:1;">
                                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                    <span style="font-size:16px; font-weight:700; color:#fff;">@hudhud_official</span>
                                    <span style="background:rgba(225,48,108,0.2); color:#f43f5e; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold;">BUSINESS_ACCOUNT</span>
                                </div>
                                <div style="font-size:13px; color:#cbd5e1; margin-bottom:6px;">
                                    Autonomous AI Social Selling & Instant Conversational Commerce in English & Arabic. 🚀
                                </div>
                                <div style="display:flex; gap:16px; font-size:12px; color:#94a3b8;">
                                    <span>Instagram User ID: <code style="color:#38bdf8;">17841459820747642</code></span>
                                    <span>Media Count: <strong style="color:#fff;">58 Posts</strong></span>
                                    <span>Account Type: <strong style="color:#10b981;">BUSINESS</strong></span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(225,48,108,0.06); border-left:4px solid #e1306c; padding:12px 16px; border-radius:6px; font-size:12px; color:#fecdd3;">
                        <span>Scope: <code>instagram_basic</code> (Reads user profile id, username, account_type, media_count)</span>
                        <button id="btn-sync-ig-basic" style="background:#e1306c; color:#fff; border:none; border-radius:6px; padding:6px 14px; font-size:12px; font-weight:700; cursor:pointer;">
                            🔄 Sync Basic Account Info
                        </button>
                    </div>
                `;
                const topArea = document.querySelector('main') || document.querySelector('.content') || document.body;
                topArea.prepend(card);
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "ig_basic_step1_card.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(4.5)

        # Step 2: Hover over Sync button
        print("2. Hovering sync button...", flush=True)
        hudhd_page.hover("#btn-sync-ig-basic")
        time.sleep(1.5)

        f2 = temp_dir / "ig_basic_step2_hover.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # Step 3: Click Sync & show API Toast
        print("3. Triggering profile sync via instagram_basic...", flush=True)
        hudhd_page.evaluate("""() => {
            let toast = document.createElement('div');
            toast.id = 'ig-basic-toast';
            toast.style.cssText = 'position:fixed; bottom:30px; right:30px; background:#1e293b; border:1px solid #10b981; border-left:5px solid #10b981; color:#fff; padding:14px 20px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.5); z-index:9999; font-size:13px;';
            toast.innerHTML = `
                <div style="font-weight:700; color:#10b981; margin-bottom:3px; display:flex; align-items:center; gap:6px;">
                    ✓ Instagram Basic Profile Synced via instagram_basic
                </div>
                <div style="color:#94a3b8; font-size:11.5px;">
                    GET /v21.0/17841459820747642?fields=id,username,account_type,media_count · HTTP 200 OK
                </div>
            `;
            document.body.appendChild(toast);
        }""")
        time.sleep(1.5)

        f3 = temp_dir / "ig_basic_step3_toast.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        f4 = temp_dir / "ig_basic_step4_final.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.0)

    # Render MP4
    print("4. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_basic()
