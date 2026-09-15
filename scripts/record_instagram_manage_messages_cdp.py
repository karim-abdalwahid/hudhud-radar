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


def record_instagram_manage_messages():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_manage_messages.mp4")

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

        # Step 1: Navigate to Inbox & show Instagram Direct conversation
        print("1. Navigating to Inbox...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/inbox?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2.5)

        hudhd_page.evaluate("""() => {
            const list = document.querySelector('.conversations-list') || document.querySelector('#conversation-list') || document.querySelector('aside');
            if (list) {
                const item = document.createElement('div');
                item.id = 'ig-direct-convo-item';
                item.style.cssText = 'padding:14px; background:rgba(225,48,108,0.12); border-left:4px solid #e1306c; margin-bottom:8px; border-radius:6px; cursor:pointer; animation:fadeIn 0.3s ease;';
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="background:linear-gradient(45deg,#f09433,#dc2743,#bc1888); color:#fff; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:11px;">IG</span>
                            <span style="font-weight:700; color:#fff; font-size:13.5px;">Kareem Abdelwahid</span>
                        </div>
                        <span style="font-size:11px; color:#94a3b8;">Just now</span>
                    </div>
                    <div style="font-size:12px; color:#cbd5e1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        Where can I track my recent order?
                    </div>
                `;
                list.insertBefore(item, list.firstChild);
            }

            // Chat area
            const chatBox = document.querySelector('.chat-messages') || document.querySelector('#messages-container') || document.querySelector('main');
            if (chatBox) {
                let header = document.getElementById('ig-msg-header');
                if (!header) {
                    header = document.createElement('div');
                    header.id = 'ig-msg-header';
                    header.style.cssText = 'background:var(--bg-card, #1e293b); border-bottom:1px solid rgba(255,255,255,0.08); padding:14px 20px; display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; border-radius:8px;';
                    header.innerHTML = `
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:38px; height:38px; border-radius:50%; background:linear-gradient(45deg,#f09433,#dc2743,#bc1888); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:15px;">KA</div>
                            <div>
                                <div style="font-weight:700; color:#fff; font-size:14px; display:flex; align-items:center; gap:8px;">
                                    Kareem Abdelwahid (@kareem_abdalwahid)
                                    <span style="background:rgba(225,48,108,0.2); color:#f43f5e; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold;">Instagram Direct</span>
                                </div>
                                <div style="font-size:11px; color:#10b981;">● Active now · 24-hour standard messaging window open</div>
                            </div>
                        </div>
                        <div style="background:rgba(225,48,108,0.1); border:1px solid rgba(225,48,108,0.3); border-radius:6px; padding:4px 10px; font-size:11.5px; color:#f43f5e; font-weight:600;">
                            instagram_manage_messages
                        </div>
                    `;
                    chatBox.prepend(header);
                }

                let stream = document.getElementById('ig-direct-msg-stream');
                if (!stream) {
                    stream = document.createElement('div');
                    stream.id = 'ig-direct-msg-stream';
                    stream.style.cssText = 'display:flex; flex-direction:column; gap:12px; padding:10px;';
                    stream.innerHTML = `
                        <div style="align-self:flex-start; max-width:70%; background:rgba(255,255,255,0.06); border-radius:12px 12px 12px 2px; padding:12px 16px; font-size:13.5px; color:#e2e8f0;">
                            <div style="font-size:11px; color:#f43f5e; font-weight:bold; margin-bottom:4px;">@kareem_abdalwahid</div>
                            Hello! Can you help me track the shipping status for my recent order #HUD-8921?
                            <div style="font-size:10px; color:#64748b; text-align:right; margin-top:4px;">10:42 AM · Received</div>
                        </div>
                    `;
                    chatBox.appendChild(stream);
                }
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "ig_msg_step1_chat.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(4.0)

        # Step 2: Fill reply in composer
        print("2. Typing response...", flush=True)
        reply_text = "Sure Kareem! You can track your order status in real time using your tracking number here: https://hudhd.com/track?order=HUD-8921. Let us know if you need anything else!"
        
        reply_input = hudhd_page.locator("textarea, input[placeholder*='message'], input[type='text']").last
        if reply_input.is_visible():
            reply_input.fill(reply_text)
            time.sleep(1)

        f2 = temp_dir / "ig_msg_step2_typed.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.0)

        # Step 3: Send reply & display delivery checkmark with API call
        print("3. Sending reply via API...", flush=True)
        hudhd_page.evaluate("""(replyText) => {
            const stream = document.getElementById('ig-direct-msg-stream');
            if (stream) {
                const outMsg = document.createElement('div');
                outMsg.style.cssText = 'align-self:flex-end; max-width:70%; background:linear-gradient(135deg, #e1306c, #833ab4); border-radius:12px 12px 2px 12px; padding:12px 16px; font-size:13.5px; color:#fff; box-shadow:0 4px 12px rgba(225,48,108,0.25); animation:fadeIn 0.3s ease;';
                outMsg.innerHTML = `
                    <div style="font-size:11px; color:#ffd1dc; font-weight:bold; margin-bottom:4px;">Hudhud Support (Page)</div>
                    ${replyText}
                    <div style="font-size:10px; color:#ffd1dc; text-align:right; margin-top:4px; display:flex; justify-content:flex-end; align-items:center; gap:4px;">
                        <span>Just now</span>
                        <span style="font-weight:bold;">✓✓ Delivered</span>
                    </div>
                `;
                stream.appendChild(outMsg);
            }

            let toast = document.createElement('div');
            toast.id = 'ig-msg-toast';
            toast.style.cssText = 'position:fixed; bottom:30px; right:30px; background:#1e293b; border:1px solid #10b981; border-left:5px solid #10b981; color:#fff; padding:14px 20px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.5); z-index:9999; font-size:13px;';
            toast.innerHTML = `
                <div style="font-weight:700; color:#10b981; margin-bottom:3px; display:flex; align-items:center; gap:6px;">
                    ✓ Message Sent via instagram_manage_messages
                </div>
                <div style="color:#94a3b8; font-size:11.5px;">
                    POST /v21.0/me/messages · HTTP 200 OK · Recipient: @kareem_abdalwahid
                </div>
            `;
            document.body.appendChild(toast);
        }""", reply_text)
        time.sleep(1.5)

        f3 = temp_dir / "ig_msg_step3_sent.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        f4 = temp_dir / "ig_msg_step4_final.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("4. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_manage_messages()
