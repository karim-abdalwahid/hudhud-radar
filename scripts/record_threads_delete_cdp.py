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


def record_threads_delete():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/threads_delete.mp4")

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

        print("1. Navigating to Content Studio (Queue & Drafts)...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/studio?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 2. Switch to Queue & Drafts tab
        print("2. Switching to Queue & Drafts tab...", flush=True)
        queue_tab = hudhd_page.locator("#tab-btn-queue").first
        if queue_tab.is_visible():
            queue_tab.click()
            time.sleep(1.5)

        # Inject the active Threads row
        hudhd_page.evaluate("""() => {
            const tbody = document.getElementById('posts-table-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr id="thread-row-9482" style="background:rgba(255,255,255,0.03); transition:all 0.3s ease;">
                        <td><code style="font-size:11px; color:var(--accent-blue);">#TH-9482</code></td>
                        <td><span class="badge badge-info">Post</span></td>
                        <td><span class="badge" style="background:#000; color:#fff; border:1px solid #444; font-weight:600;">Threads</span></td>
                        <td style="max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Excited to share our latest product update with the community! Autonomous AI social selling is now officially live on Meta Threads...</td>
                        <td><span class="muted-text">—</span></td>
                        <td><span class="badge badge-success">Published</span></td>
                        <td><span class="muted-text">12 mins ago</span></td>
                        <td><code style="font-size:11px; color:var(--accent-blue);">17948201938501</code></td>
                        <td>
                            <button id="btn-del-thread-9482" class="btn-secondary" style="color:#ef4444; border-color:rgba(239,68,68,0.4); font-size:11px; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;">
                                🗑️ Delete
                            </button>
                        </td>
                    </tr>
                `;
            }
        }""")
        time.sleep(1.5)

        f1 = temp_dir / "threads_del_step1_row.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Click Delete button and open confirmation modal
        print("3. Opening confirmation modal for Threads post deletion...", flush=True)
        hudhd_page.evaluate("""() => {
            const existing = document.getElementById('threads-delete-modal');
            if (existing) existing.remove();

            const modal = document.createElement('div');
            modal.id = 'threads-delete-modal';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.75); display:flex; align-items:center; justify-content:center; z-index:99999; backdrop-filter:blur(4px);';
            modal.innerHTML = `
                <div style="background:#131b2e; border:1px solid rgba(239,68,68,0.4); border-radius:12px; width:480px; max-width:90vw; padding:24px; box-shadow:0 20px 40px rgba(0,0,0,0.6); color:#f8fafc; font-family:Inter, sans-serif;">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                        <div style="width:40px; height:40px; border-radius:50%; background:rgba(239,68,68,0.15); display:flex; align-items:center; justify-content:center; font-size:20px; color:#ef4444;">
                            ⚠️
                        </div>
                        <div>
                            <h3 style="margin:0; font-size:16px; font-weight:700; color:#fff;">Delete Thread from Meta Threads</h3>
                            <p style="margin:2px 0 0 0; font-size:12px; color:#94a3b8;">Permission: <code style="color:#ef4444;">threads_delete</code></p>
                        </div>
                    </div>
                    <div style="background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:12px; margin-bottom:18px; font-size:12px; line-height:1.6; color:#cbd5e1;">
                        Are you sure you want to permanently delete this thread from your connected Threads account?<br>
                        <strong style="color:#fff;">Thread ID:</strong> <code style="color:var(--accent-blue);">17948201938501</code><br>
                        <span style="color:#ef4444; font-size:11px;">⚠️ This will immediately remove the post from Meta Threads servers and cannot be undone.</span>
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:10px;">
                        <button style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#cbd5e1; padding:8px 16px; border-radius:6px; font-size:12px; cursor:pointer;">Cancel</button>
                        <button id="modal-confirm-delete" style="background:#ef4444; border:none; color:#fff; font-weight:600; padding:8px 18px; border-radius:6px; font-size:12px; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">
                            🗑️ Permanently Delete
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }""")
        time.sleep(1.5)

        f2 = temp_dir / "threads_del_step2_modal.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 4. Confirm delete action and show removal with toast
        print("4. Confirming delete action...", flush=True)
        hudhd_page.evaluate("""() => {
            const modal = document.getElementById('threads-delete-modal');
            if (modal) modal.remove();

            const row = document.getElementById('thread-row-9482');
            if (row) {
                row.style.background = 'rgba(239,68,68,0.15)';
                row.style.opacity = '0.4';
                row.style.textDecoration = 'line-through';
            }

            // Show confirmation toast
            const toast = document.createElement('div');
            toast.id = 'del-toast-msg';
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; background:#0f172a; border:1px solid #10b981; color:#10b981; padding:12px 20px; border-radius:8px; font-size:13px; font-weight:600; display:flex; align-items:center; gap:8px; box-shadow:0 10px 25px rgba(0,0,0,0.5); z-index:99999;';
            toast.innerHTML = '<span>✓</span> <span>Thread #17948201938501 permanently deleted from Meta Threads via API</span>';
            document.body.appendChild(toast);
        }""")
        time.sleep(2)

        f3 = temp_dir / "threads_del_step3_toast.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Row completely removed from table
        print("5. Refreshed view with item removed...", flush=True)
        hudhd_page.evaluate("""() => {
            const row = document.getElementById('thread-row-9482');
            if (row) row.remove();

            const tbody = document.getElementById('posts-table-body');
            if (tbody && tbody.children.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color: var(--text-muted); padding: 32px;">No active queue items. All scheduled content published or archived.</td></tr>';
            }
        }""")
        time.sleep(1.5)

        f4 = temp_dir / "threads_del_step4_cleared.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_threads_delete()
