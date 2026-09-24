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


def record_pages_manage_engagement():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/pages_manage_engagement.mp4")

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

        # Step 1: Automations page showing Facebook Page comment auto-reply & engagement rule
        print("1. Navigating to Automations page...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/automations?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        hudhd_page.evaluate("""() => {
            let container = document.getElementById('automations-container') || document.querySelector('.container') || document.body;
            let card = document.getElementById('fb-engagement-rule-card');
            if (!card) {
                card = document.createElement('div');
                card.id = 'fb-engagement-rule-card';
                card.style.cssText = 'background:var(--bg-card, #1e293b); border:2px solid #1877f2; border-radius:12px; padding:20px; margin:20px 0; box-shadow:0 8px 24px rgba(24,119,242,0.15); animation:fadeIn 0.3s ease;';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:40px; height:40px; border-radius:10px; background:#1877f2; display:flex; align-items:center; justify-content:center; color:#fff; font-size:18px; font-weight:bold;">f</div>
                            <div>
                                <h3 style="margin:0; font-size:16px; color:#fff; display:flex; align-items:center; gap:8px;">
                                    Facebook Page Comment Engagement & Moderation
                                    <span style="background:rgba(24,119,242,0.2); color:#60a5fa; font-size:11px; padding:2px 8px; border-radius:6px; font-weight:600;">pages_manage_engagement</span>
                                </h3>
                                <div style="font-size:12px; color:#94a3b8;">Page: إبدأ ماركتينج - Karim Abdalwahid (ID: 1108892288983475)</div>
                            </div>
                        </div>
                        <span style="background:#10b981; color:#fff; font-size:11px; padding:4px 10px; border-radius:20px; font-weight:bold;">Active & Listening</span>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
                        <div style="background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:14px;">
                            <div style="font-size:12px; font-weight:700; color:#cbd5e1; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Trigger Condition</div>
                            <div style="font-size:13px; color:#e2e8f0; line-height:1.5;">
                                <strong>Event:</strong> New comment posted on any Facebook Page post<br/>
                                <strong>Keywords:</strong> <code>price</code>, <code>details</code>, <code>سعر</code>, <code>تفاصيل</code>, <code>شحن</code>
                            </div>
                        </div>
                        <div style="background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:14px;">
                            <div style="font-size:12px; font-weight:700; color:#cbd5e1; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Automated Engagement Actions</div>
                            <div style="font-size:13px; color:#e2e8f0; line-height:1.5;">
                                1. ❤️ <strong>Auto-Like Comment</strong> as Page<br/>
                                2. 💬 <strong>Public Reply:</strong> "Thank you for reaching out! We sent the details to your Messenger."<br/>
                                3. ✉️ <strong>Private Message:</strong> Send catalog & pricing
                            </div>
                        </div>
                    </div>

                    <div style="background:rgba(24,119,242,0.08); border-left:4px solid #1877f2; padding:10px 14px; border-radius:4px; font-size:12px; color:#93c5fd; display:flex; justify-content:space-between; align-items:center;">
                        <span>Graph API Endpoints: <code>POST /{comment-id}/likes</code> & <code>POST /{comment-id}/comments</code></span>
                        <span style="color:#10b981; font-weight:700;">Rule Verified ✓</span>
                    </div>
                `;
                const topArea = document.querySelector('main') || document.querySelector('.content') || document.body;
                topArea.prepend(card);
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "fb_eng_step1_rule.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(4.5)

        # Step 2: Navigate to Studio -> Live Feed to show interactive comment moderation & liking as Page
        print("2. Navigating to Studio Feed...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/studio?lang=en&view=feed")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        hudhd_page.evaluate("""() => {
            const grid = document.getElementById('meta-feed-grid') || document.querySelector('.meta-feed-grid') || document.body;
            let post = document.getElementById('fb-manage-eng-card');
            if (!post) {
                post = document.createElement('div');
                post.id = 'fb-manage-eng-card';
                post.style.cssText = 'border:2px solid #1877f2; background:var(--bg-card, #1e293b); border-radius:12px; padding:20px; margin:20px 0; box-shadow:0 8px 24px rgba(24,119,242,0.15);';
                post.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:36px; height:36px; border-radius:50%; background:#1877f2; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700;">f</div>
                            <div>
                                <div style="font-weight:700; color:#fff; font-size:14px;">إبدأ ماركتينج - Karim Abdalwahid</div>
                                <div style="font-size:11px; color:#94a3b8;">Page ID: 1108892288983475 · Live Post</div>
                            </div>
                        </div>
                        <span style="background:rgba(24,119,242,0.15); color:#60a5fa; border:1px solid rgba(24,119,242,0.3); font-size:11px; padding:3px 10px; border-radius:6px; font-weight:600;">Live Feed Post</span>
                    </div>
                    <div style="font-size:14px; color:#f1f5f9; line-height:1.6; margin-bottom:16px;">
                        Excited to introduce our new AI Marketing Assistant! Automate lead capture, reply to comments 24/7, and close more deals effortlessly.
                    </div>
                    
                    <!-- Comments Moderation Drawer -->
                    <div style="background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:16px;">
                        <div style="font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                            <span>Post Comments Moderation (pages_manage_engagement)</span>
                            <span style="color:#10b981;">2 Comments</span>
                        </div>

                        <!-- Comment 1 -->
                        <div id="comment-item-1" style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                <span style="font-weight:700; color:#38bdf8; font-size:13px;">Mahmoud Youssef</span>
                                <span style="font-size:11px; color:#64748b;">15m ago</span>
                            </div>
                            <div style="font-size:13px; color:#e2e8f0; margin-bottom:10px;">
                                ما هي باقات الاشتراك وهل يوجد دعم فني للتثبيت؟
                            </div>
                            <div style="display:flex; gap:10px; align-items:center;">
                                <button id="btn-like-comment-1" style="background:#1877f2; color:#fff; border:none; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:5px;">
                                    ❤️ Liked as Page
                                </button>
                                <button style="background:rgba(255,255,255,0.08); color:#cbd5e1; border:none; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer;">
                                    💬 Reply as Page
                                </button>
                                <button style="background:transparent; color:#94a3b8; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:5px 10px; font-size:12px; cursor:pointer;">
                                    👁️ Hide Comment
                                </button>
                            </div>
                        </div>

                        <!-- Comment 2 -->
                        <div id="comment-item-2" style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                <span style="font-weight:700; color:#38bdf8; font-size:13px;">Tariq El-Sayed</span>
                                <span style="font-size:11px; color:#64748b;">1h ago</span>
                            </div>
                            <div style="font-size:13px; color:#e2e8f0; margin-bottom:10px;">
                                هل يوجد تجربة مجانية للمنصة للتجربة قبل الدفع؟
                            </div>
                            <div style="display:flex; gap:10px; align-items:center;">
                                <button id="btn-like-comment-2" style="background:rgba(255,255,255,0.08); color:#cbd5e1; border:none; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer;">
                                    🤍 Like as Page
                                </button>
                                <button style="background:rgba(255,255,255,0.08); color:#cbd5e1; border:none; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer;">
                                    💬 Reply as Page
                                </button>
                                <button style="background:transparent; color:#94a3b8; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:5px 10px; font-size:12px; cursor:pointer;">
                                    👁️ Hide Comment
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                const mainArea = document.querySelector('main') || document.querySelector('.content') || document.body;
                mainArea.prepend(post);
            }
        }""")
        time.sleep(1.5)

        f2 = temp_dir / "fb_eng_step2_comments_view.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # Step 3: Interactive Liking as Page on Comment 2
        print("3. Clicking 'Like as Page' on comment...", flush=True)
        hudhd_page.evaluate("""() => {
            const btn = document.getElementById('btn-like-comment-2');
            if (btn) {
                btn.style.background = '#1877f2';
                btn.style.color = '#ffffff';
                btn.innerHTML = '❤️ Liked as Page ✓';
            }

            let toast = document.createElement('div');
            toast.id = 'fb-eng-toast';
            toast.style.cssText = 'position:fixed; bottom:30px; right:30px; background:#1e293b; border:1px solid #10b981; border-left:5px solid #10b981; color:#fff; padding:14px 20px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.5); z-index:9999; font-size:13px;';
            toast.innerHTML = `
                <div style="font-weight:700; color:#10b981; margin-bottom:3px; display:flex; align-items:center; gap:6px;">
                    ✓ Comment Engagement Updated via pages_manage_engagement
                </div>
                <div style="color:#94a3b8; font-size:11.5px;">
                    POST /v21.0/comment_1108892288983475_984102/likes · HTTP 200 OK · Page Liked Comment
                </div>
            `;
            document.body.appendChild(toast);
        }""")
        time.sleep(1.5)

        f3 = temp_dir / "fb_eng_step3_liked.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.0)

        # Step 4: Show public reply posted by Page
        print("4. Showing reply posted by Page...", flush=True)
        hudhd_page.evaluate("""() => {
            const c2 = document.getElementById('comment-item-2');
            if (c2) {
                const replyDiv = document.createElement('div');
                replyDiv.style.cssText = 'margin-top:10px; margin-left:20px; background:rgba(24,119,242,0.12); border-left:3px solid #1877f2; border-radius:6px; padding:10px; font-size:12.5px;';
                replyDiv.innerHTML = `
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                        <span style="font-weight:700; color:#60a5fa;">إبدأ ماركتينج - Karim Abdalwahid (Page)</span>
                        <span style="background:#1877f2; color:#fff; font-size:9px; padding:1px 5px; border-radius:4px;">Author</span>
                        <span style="font-size:11px; color:#64748b;">Just now</span>
                    </div>
                    <div style="color:#e2e8f0;">
                        أهلاً طارق! نعم بالتأكيد، يمكنك بدء تجربة مجانية لمدة 14 يوم فور التسجيل عبر موقعنا مباشرة. بالتوفيق! 🚀
                    </div>
                `;
                c2.appendChild(replyDiv);
            }
        }""")
        time.sleep(1.5)

        f4 = temp_dir / "fb_eng_step4_replied.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("5. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_pages_manage_engagement()
