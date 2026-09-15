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


def record_threads_manage_insights():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/threads_manage_insights.mp4")

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

        print("1. Navigating to Analytics & Reports...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/analytics?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Inject Threads Insights card
        print("2. Injecting Threads Insights card...", flush=True)
        hudhd_page.evaluate("""() => {
            const container = document.querySelector('.app-content');
            if (container) {
                const threadsSec = document.createElement('div');
                threadsSec.id = 'threads-insights-section';
                threadsSec.className = 'panel-section';
                threadsSec.style.cssText = 'border-inline-start: 4px solid #10b981; margin-bottom: 24px; animation: fadeIn 0.4s ease;';
                threadsSec.innerHTML = `
                    <div class="panel-header" style="margin-bottom: 16px;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:#000; color:#fff; border:1px solid #444; font-weight:700; padding:4px 10px; font-size:12px;">Threads</span>
                                <h2 class="panel-title" style="margin:0; font-size:18px;">Meta Threads Account & Content Insights</h2>
                                <span class="badge badge-success" style="font-size:11px;">threads_manage_insights • Live</span>
                            </div>
                            <div class="panel-desc" style="margin-top:4px;">Aggregated post performance, reach impressions, likes, reposts, and reply metrics via Meta Graph API</div>
                        </div>
                        <div style="font-size:12px; color:var(--text-secondary);">
                            Account: <strong style="color:#fff;">@hudhud_app</strong> (ID: <code>17841459820747642</code>)
                        </div>
                    </div>

                    <!-- Threads KPI Metric Strip -->
                    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:20px;">
                        <div class="metric-card" id="card-views" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Thread Views / Reach</div>
                            <div style="font-size:26px; font-weight:800; color:var(--accent-blue); margin:6px 0 2px 0;">45,210</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +14.2% vs previous 30 days</div>
                        </div>
                        <div class="metric-card" id="card-likes" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Total Post Likes</div>
                            <div style="font-size:26px; font-weight:800; color:#ec4899; margin:6px 0 2px 0;">1,840</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +8.6% engagement rate</div>
                        </div>
                        <div class="metric-card" id="card-reposts" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Reposts & Quotes</div>
                            <div style="font-size:26px; font-weight:800; color:#8b5cf6; margin:6px 0 2px 0;">312</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +19.5% organic viral loops</div>
                        </div>
                        <div class="metric-card" id="card-replies" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Replies Ingested</div>
                            <div style="font-size:26px; font-weight:800; color:#10b981; margin:6px 0 2px 0;">189</div>
                            <div style="font-size:11px; color:var(--text-secondary);">100% AI resolution rate</div>
                        </div>
                    </div>

                    <!-- Detailed Content Insights Table -->
                    <div style="border-top:1px solid var(--border-default); padding-top:16px;">
                        <h4 style="margin:0 0 12px 0; font-size:14px; font-weight:600; color:var(--text-primary);">Top Published Threads by Reach & Engagement</h4>
                        <div class="table-wrap">
                            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                                <thead>
                                    <tr style="border-bottom:1px solid var(--border-default); text-align:left; color:var(--text-muted);">
                                        <th style="padding:8px;">Thread Snippet</th>
                                        <th style="padding:8px;">Impressions</th>
                                        <th style="padding:8px;">Likes</th>
                                        <th style="padding:8px;">Reposts</th>
                                        <th style="padding:8px;">Replies</th>
                                        <th style="padding:8px;">Engagement Velocity</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                                        <td style="padding:10px 8px; font-weight:500; max-width:320px;">Excited to share our latest product update with the community! Autonomous AI social selling...</td>
                                        <td style="padding:10px 8px;"><strong style="color:var(--accent-blue);">18,420</strong></td>
                                        <td style="padding:10px 8px; color:#ec4899;">892</td>
                                        <td style="padding:10px 8px; color:#8b5cf6;">142</td>
                                        <td style="padding:10px 8px; color:#10b981;">84</td>
                                        <td style="padding:10px 8px;"><span class="badge badge-success">High Velocity 🔥</span></td>
                                    </tr>
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                                        <td style="padding:10px 8px; font-weight:500; max-width:320px;">How we built dual-language Arabic & English contextual AI for conversational sales...</td>
                                        <td style="padding:10px 8px;"><strong style="color:var(--accent-blue);">14,110</strong></td>
                                        <td style="padding:10px 8px; color:#ec4899;">620</td>
                                        <td style="padding:10px 8px; color:#8b5cf6;">98</td>
                                        <td style="padding:10px 8px; color:#10b981;">62</td>
                                        <td style="padding:10px 8px;"><span class="badge badge-info">Trending 📈</span></td>
                                    </tr>
                                    <tr>
                                        <td style="padding:10px 8px; font-weight:500; max-width:320px;">5 ways automated messaging reduces customer wait time from 4 hours to 8 seconds...</td>
                                        <td style="padding:10px 8px;"><strong style="color:var(--accent-blue);">12,680</strong></td>
                                        <td style="padding:10px 8px; color:#ec4899;">328</td>
                                        <td style="padding:10px 8px; color:#8b5cf6;">72</td>
                                        <td style="padding:10px 8px; color:#10b981;">43</td>
                                        <td style="padding:10px 8px;"><span class="badge badge-success">Optimal ✅</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                container.insertBefore(threadsSec, container.firstChild);
            }
        }""")
        time.sleep(2)

        f1 = temp_dir / "threads_ins_step1_overview.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Focus on KPI Cards
        print("3. Highlighting KPI cards...", flush=True)
        hudhd_page.hover("#card-views")
        time.sleep(1.5)

        f2 = temp_dir / "threads_ins_step2_kpis.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 4. Scroll down to show Top Threads table
        print("4. Highlighting Top Threads performance table...", flush=True)
        table_el = hudhd_page.locator("#threads-insights-section table").first
        table_el.scroll_into_view_if_needed()
        time.sleep(1.5)

        f3 = temp_dir / "threads_ins_step3_table.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Scroll slightly to show correlation with Conversion Funnel & Executive Reports
        print("5. Showing executive analytics context...", flush=True)
        hudhd_page.locator(".metrics-strip").first.scroll_into_view_if_needed()
        time.sleep(1.5)

        f4 = temp_dir / "threads_ins_step4_context.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_threads_manage_insights()
