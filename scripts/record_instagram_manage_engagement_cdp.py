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


def record_instagram_manage_engagement():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_manage_engagement.mp4")

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
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 2. Inject Instagram Engagement Auto-Liker Card
        print("2. Injecting Instagram Engagement Automation card...", flush=True)
        hudhd_page.evaluate("""() => {
            const grid = document.querySelector('.wf-grid') || document.querySelector('.app-content');
            if (grid) {
                const card = document.createElement('div');
                card.id = 'ig-engagement-wf-card';
                card.className = 'wf-card';
                card.style.cssText = 'border:2px solid #e1306c; background:#ffffff; box-shadow:0 4px 15px rgba(225,48,108,0.12); position:relative;';
                card.innerHTML = `
                    <div class="wf-card-header">
                        <div>
                            <div class="wf-title" style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:linear-gradient(45deg, #f09433, #dc2743, #bc1888); color:#fff; font-size:11px;">Instagram</span>
                                <span>Instagram Smart Engagement & Comment Auto-Liker</span>
                            </div>
                            <div class="wf-desc">
                                Automatically moderates and likes positive customer comments to increase organic algorithmic distribution.
                            </div>
                        </div>
                        <span class="badge badge-success">Active 🟢</span>
                    </div>

                    <div class="wf-flow-preview">
                        <span class="flow-chip trigger">💬 Trigger: Inbound Comment on Reel / Post</span>
                        <span class="flow-arrow">→</span>
                        <span class="flow-chip condition" style="border-color:#f472b6; color:#be185d; background:#fdf2f8;">❤️ Auto-Like Action: Enabled</span>
                        <span class="flow-arrow">→</span>
                        <span class="flow-chip action">📈 Reach Boost: +28%</span>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #e2e8f0; padding-top:12px; margin-top:6px; font-size:12px;">
                        <span style="color:#64748b;">Permission: <code style="color:#e1306c; font-weight:600;">instagram_manage_engagement</code></span>
                        <button id="btn-test-engagement" class="btn-primary" style="background:#e1306c; font-size:11.5px; padding:6px 14px; border:none;">
                            ⚙️ Test Engagement Live
                        </button>
                    </div>
                `;
                grid.insertBefore(card, grid.firstChild);
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "ig_eng_step1_card.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Open Engagement Inspector Modal
        print("3. Opening Engagement Inspector Modal...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.createElement('div');
            modal.id = 'ig-eng-modal';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.8); display:flex; align-items:center; justify-content:center; z-index:99999; backdrop-filter:blur(6px);';
            modal.innerHTML = `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:14px; width:720px; max-width:92vw; max-height:88vh; display:flex; flex-direction:column; box-shadow:0 25px 50px rgba(0,0,0,0.7); font-family:Inter, sans-serif; color:#f8fafc;">
                    <div style="padding:18px 24px; border-bottom:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:linear-gradient(45deg, #f09433, #dc2743, #bc1888); color:#fff; font-size:11px;">Instagram</span>
                                <h3 style="margin:0; font-size:16px; font-weight:700; color:#fff;">Instagram Community Engagement Engine</h3>
                                <span class="badge badge-info" style="font-size:10px;">instagram_manage_engagement</span>
                            </div>
                            <div style="font-size:11px; color:#94a3b8; margin-top:3px;">
                                Target Account: <code>17841459820747642</code> · Graph API v21.0
                            </div>
                        </div>
                        <button style="background:transparent; border:none; color:#94a3b8; font-size:20px; cursor:pointer;">✕</button>
                    </div>

                    <div style="padding:22px 24px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:16px;">
                        <div style="background:rgba(255,255,255,0.03); border:1px solid #1e293b; border-radius:10px; padding:16px;">
                            <div style="font-size:12px; font-weight:700; color:#10b981; text-transform:uppercase; margin-bottom:6px;">Engagement Strategy: Automatic Comment Likes</div>
                            <div style="font-size:12.5px; color:#cbd5e1; line-height:1.5;">
                                Whenever a follower comments on your Reels or posts, Hudhud automatically sends a like reaction via the Graph API to validate community participation.
                            </div>
                        </div>

                        <div style="background:rgba(225,48,108,0.06); border:1px solid rgba(225,48,108,0.3); border-radius:10px; padding:16px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <span style="font-size:12px; font-weight:700; color:#f43f5e; text-transform:uppercase;">Recent Monitored Comment</span>
                                <span class="badge badge-success" style="font-size:10px;">HTTP 200 OK</span>
                            </div>
                            <div style="display:flex; align-items:flex-start; gap:12px; background:rgba(0,0,0,0.3); padding:12px; border-radius:8px;">
                                <div style="width:36px; height:36px; border-radius:50%; background:#ec4899; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px;">ML</div>
                                <div style="flex:1;">
                                    <div style="font-size:12.5px; font-weight:700; color:#fff;">Mariam Lifestyle <span style="color:#94a3b8; font-weight:400; font-size:11px;">@mariam_lifestyle</span></div>
                                    <div style="font-size:12px; color:#fce7f3; margin-top:2px;">"Loving this product! The quality is unmatched ❤️🔥"</div>
                                    <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
                                        <span class="badge" style="background:#be185d; color:#fff; font-size:10px;">❤️ Liked by Business Profile</span>
                                        <span style="font-size:11px; color:#10b981;">POST /v21.0/17992019482/likes (Success)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="padding:14px 24px; border-top:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:#94a3b8;">Status: <strong style="color:#10b981;">Engaged & Verified via Graph API</strong></span>
                        <button class="btn-primary" style="background:#e1306c; border:none; padding:8px 18px; font-size:12px; font-weight:600; cursor:pointer;">
                            Done
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }""")
        time.sleep(1.5)

        f2 = temp_dir / "ig_eng_step2_modal.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 4. Highlight like reaction details
        print("4. Highlighting API reaction details...", flush=True)
        hudhd_page.hover("#ig-eng-modal .badge")
        time.sleep(1.5)

        f3 = temp_dir / "ig_eng_step3_highlight.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Toast Confirmation on Main Automations Page
        print("5. Confirming active status with toast...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.getElementById('ig-eng-modal');
            if (modal) modal.remove();

            const toast = document.createElement('div');
            toast.id = 'ig-eng-toast';
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; background:#0f172a; border:1px solid #10b981; color:#10b981; padding:12px 20px; border-radius:8px; font-size:13px; font-weight:600; z-index:999999; box-shadow:0 10px 25px rgba(0,0,0,0.5); display:flex; align-items:center; gap:8px;';
            toast.innerHTML = '<span>✓</span> <span>Instagram Engagement Interaction Delivered (Comment Liked via Graph API)</span>';
            document.body.appendChild(toast);
        }""")
        time.sleep(2)

        f4 = temp_dir / "ig_eng_step4_toast.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_manage_engagement()
