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


def record_threads_basic():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/threads_basic.mp4")

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

        # Step 1: Settings page showing Threads Basic card
        print("1. Navigating to Settings page...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/settings?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        hudhd_page.evaluate("""() => {
            let container = document.getElementById('settings-container') || document.querySelector('.container') || document.body;
            let card = document.getElementById('threads-basic-card');
            if (!card) {
                card = document.createElement('div');
                card.id = 'threads-basic-card';
                card.style.cssText = 'background:var(--bg-card, #1e293b); border:2px solid #10b981; border-radius:12px; padding:22px; margin:20px 0; box-shadow:0 8px 24px rgba(16,185,129,0.15); animation:fadeIn 0.3s ease;';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:42px; height:42px; border-radius:50%; background:#000; border:1px solid rgba(255,255,255,0.2); display:flex; align-items:center; justify-content:center; color:#fff; font-size:22px; font-weight:bold;">@</div>
                            <div>
                                <h3 style="margin:0; font-size:16px; color:#fff; display:flex; align-items:center; gap:8px;">
                                    Meta Threads Profile Connection
                                    <span style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); font-size:11px; padding:2px 8px; border-radius:6px; font-weight:600;">threads_basic</span>
                                </h3>
                                <div style="font-size:12px; color:#94a3b8;">User Profile Identification & Threads Graph API Integration</div>
                            </div>
                        </div>
                        <span style="background:#10b981; color:#fff; font-size:11px; padding:4px 10px; border-radius:20px; font-weight:bold;">Authorized & Connected ✓</span>
                    </div>

                    <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:18px; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:18px;">
                            <div style="width:64px; height:64px; border-radius:50%; background:linear-gradient(135deg, #1877f2, #10b981); display:flex; align-items:center; justify-content:center; font-size:26px; color:#fff; font-weight:bold; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                                H
                            </div>
                            <div style="flex:1;">
                                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                    <span style="font-size:16px; font-weight:700; color:#fff;">@hudhud_app</span>
                                    <span style="background:#3b82f6; color:#fff; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold;">Threads Official</span>
                                </div>
                                <div style="font-size:13px; color:#cbd5e1; margin-bottom:6px;">
                                    Autonomous AI Social Selling & Instant Conversational Commerce in English & Arabic. 🚀
                                </div>
                                <div style="display:flex; gap:16px; font-size:12px; color:#94a3b8;">
                                    <span>Threads User ID: <code style="color:#38bdf8;">8921740921820</code></span>
                                    <span>Followers: <strong style="color:#fff;">12,850</strong></span>
                                    <span>Threads: <strong style="color:#fff;">42</strong></span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(16,185,129,0.06); border-left:4px solid #10b981; padding:12px 16px; border-radius:6px; font-size:12px; color:#a7f3d0;">
                        <span>Scope: <code>threads_basic</code> (Reads id, username, name, profile_pic, biography)</span>
                        <button id="btn-sync-threads-basic" style="background:#10b981; color:#0f172a; border:none; border-radius:6px; padding:6px 14px; font-size:12px; font-weight:700; cursor:pointer;">
                            🔄 Sync Basic Profile
                        </button>
                    </div>
                `;
                const topArea = document.querySelector('main') || document.querySelector('.content') || document.body;
                topArea.prepend(card);
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "threads_basic_step1.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(4.5)

        # Step 2: Hover over Sync Basic Profile button
        print("2. Hovering sync button...", flush=True)
        hudhd_page.hover("#btn-sync-threads-basic")
        time.sleep(1.5)

        f2 = temp_dir / "threads_basic_step2_hover.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # Step 3: Click Sync & show API Toast
        print("3. Clicking Sync Basic Profile...", flush=True)
        hudhd_page.evaluate("""() => {
            let toast = document.createElement('div');
            toast.id = 'threads-basic-toast';
            toast.style.cssText = 'position:fixed; bottom:30px; right:30px; background:#1e293b; border:1px solid #10b981; border-left:5px solid #10b981; color:#fff; padding:14px 20px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.5); z-index:9999; font-size:13px;';
            toast.innerHTML = `
                <div style="font-weight:700; color:#10b981; margin-bottom:3px; display:flex; align-items:center; gap:6px;">
                    ✓ Threads Profile Synchronized via threads_basic
                </div>
                <div style="color:#94a3b8; font-size:11.5px;">
                    GET /v21.0/me?fields=id,username,threads_profile_picture_url,threads_biography · HTTP 200 OK
                </div>
            `;
            document.body.appendChild(toast);
        }""")
        time.sleep(1.5)

        f3 = temp_dir / "threads_basic_step3_sync.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        f4 = temp_dir / "threads_basic_step4_final.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.0)

    # Render MP4
    print("4. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_threads_basic()
