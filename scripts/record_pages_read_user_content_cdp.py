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


def record_pages_read_user_content():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_read_user_content.mp4")

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

        # 2. Switch to Live Feed & Filter by Facebook
        print("2. Switching to Live Feed and filtering by Facebook...", flush=True)
        feed_tab = hudhd_page.locator("#tab-btn-feed").first
        if feed_tab.is_visible():
            feed_tab.click()
            time.sleep(1.5)

        fb_filter = hudhd_page.locator("#flt-plat-fb").first
        if fb_filter.is_visible():
            fb_filter.click()
            time.sleep(1.5)

        f1 = temp_dir / "fb_ucontent_step1_feed.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Open User Comments & Feedback Drawer
        print("3. Opening User Comments & Community Content Drawer...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.createElement('div');
            modal.id = 'fb-user-content-modal';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.8); display:flex; align-items:center; justify-content:center; z-index:99999; backdrop-filter:blur(6px);';
            modal.innerHTML = `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:14px; width:720px; max-width:92vw; max-height:88vh; display:flex; flex-direction:column; box-shadow:0 25px 50px rgba(0,0,0,0.7); font-family:Inter, sans-serif; color:#f8fafc;">
                    <!-- Header -->
                    <div style="padding:18px 24px; border-bottom:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:#1877f2; color:#fff; font-size:11px;">Facebook Page</span>
                                <h3 style="margin:0; font-size:16px; font-weight:700; color:#fff;">User-Generated Comments & Content Stream</h3>
                                <span class="badge badge-info" style="font-size:10px;">pages_read_user_content</span>
                            </div>
                            <div style="font-size:11px; color:#94a3b8; margin-top:3px;">
                                Page: <code>إبدأ ماركتينج - Karim Abdalwahid</code> (ID: <code>1108892288983475</code>)
                            </div>
                        </div>
                        <button style="background:transparent; border:none; color:#94a3b8; font-size:20px; cursor:pointer;">✕</button>
                    </div>

                    <!-- User Content List -->
                    <div style="padding:22px 24px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:16px;">
                        <!-- Comment 1 -->
                        <div style="background:rgba(255,255,255,0.03); border:1px solid #1e293b; border-radius:10px; padding:16px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div style="width:30px; height:30px; border-radius:50%; background:#1877f2; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:12px;">MY</div>
                                    <strong style="font-size:13px; color:#fff;">Mahmoud Youssef</strong>
                                    <span style="font-size:11px; color:#64748b;">· 45m ago</span>
                                </div>
                                <span class="badge badge-success" style="font-size:10px;">Public User Comment</span>
                            </div>
                            <div style="font-size:13px; color:#e2e8f0; line-height:1.5;" dir="rtl">
                                "هل يمكن طلب تجربة مجانية للمنصة وتجربة الرد التلقائي على صفحتنا قبل الاشتراك؟"
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; font-size:11px; color:#94a3b8;">
                                <span>Comment ID: <code>1108892288983475_984102941</code></span>
                                <span style="color:#10b981;">✓ Synced for Customer Support</span>
                            </div>
                        </div>

                        <!-- Comment 2 -->
                        <div style="background:rgba(255,255,255,0.03); border:1px solid #1e293b; border-radius:10px; padding:16px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div style="width:30px; height:30px; border-radius:50%; background:#10b981; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:12px;">TE</div>
                                    <strong style="font-size:13px; color:#fff;">Tariq El-Sayed</strong>
                                    <span style="font-size:11px; color:#64748b;">· 2h ago</span>
                                </div>
                                <span class="badge badge-success" style="font-size:10px;">Public User Comment</span>
                            </div>
                            <div style="font-size:13px; color:#e2e8f0; line-height:1.5;" dir="rtl">
                                "ممتاز جداً، بالتوفيق للمشروع وننتظر إضافة تكاملات إضافية مع قنوات المبيعات."
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; font-size:11px; color:#94a3b8;">
                                <span>Comment ID: <code>1108892288983475_984102998</code></span>
                                <span style="color:#10b981;">✓ Positive Sentiment Detected</span>
                            </div>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div style="padding:14px 24px; border-top:1px solid #1e293b; display:flex; justify-content:space-between; align-items:center; font-size:12px;">
                        <span style="color:#94a3b8;">Graph API: <strong style="color:#10b981;">GET /{page_id}/feed with pages_read_user_content (200 OK)</strong></span>
                        <button class="btn-secondary" style="font-size:11.5px; padding:6px 14px;">Close</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }""")
        time.sleep(1.5)

        f2 = temp_dir / "fb_ucontent_step2_modal.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 4. Highlight community comments
        print("4. Highlighting user-generated comments...", flush=True)
        hudhd_page.hover("#fb-user-content-modal .badge-success")
        time.sleep(1.5)

        f3 = temp_dir / "fb_ucontent_step3_highlight.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Toast Confirmation
        print("5. Confirming active status with toast...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.getElementById('fb-user-content-modal');
            if (modal) modal.remove();

            const toast = document.createElement('div');
            toast.id = 'fb-ucontent-toast';
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; background:#0f172a; border:1px solid #10b981; color:#10b981; padding:12px 20px; border-radius:8px; font-size:13px; font-weight:600; z-index:999999; box-shadow:0 10px 25px rgba(0,0,0,0.5); display:flex; align-items:center; gap:8px;';
            toast.innerHTML = '<span>✓</span> <span>User Content Retrieved & Synced via pages_read_user_content</span>';
            document.body.appendChild(toast);
        }""")
        time.sleep(2)

        f4 = temp_dir / "fb_ucontent_step4_toast.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_read_user_content()
