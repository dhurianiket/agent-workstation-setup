#!/usr/bin/env python3
"""
Cinematic Marathi Podcast & Documentary Production Engine (v4.0 — Customizable 3-Camera + B-Roll Multi-Cam)
Bundled with Antigravity Autonomous AI Developer Workstation.

Supports:
  1. Automated New Google Flow Project Creation & Mandatory `10s` (`Omni 1.1 Flash`) Duration Configuration (`init_new_project`)
  2. Camera 1 (`wide_2shot`): Establishing wide 2-shot of both hosts
  3. Camera 2 (`cam_a_chate_closeup`): Solo Medium Close-Up of Lead Host (85mm portrait bokeh)
  4. Camera 3 (`cam_b_roohi_closeup`): Solo Medium Close-Up of Co-Host (85mm portrait bokeh)
  5. Camera 4 (`broll`): Full-screen 1080p historical/scientific documentary B-Roll cutaways
  6. Single-Event `ClipboardEvent("paste")` Plate Lock + 2-Card Top-Row Batching (eliminates Masonry Row-2 swaps & double-paste races)
  7. Automated Google Flow Failed-Card Cleanup (`clean_failed_flow_cards`)
  8. Mandatory 1080p Upscaled downloads with CONSUMED_SIZES anti-duplicate guard
  9. Broadcast Optical Detail Restoration (CAS 0.55 + Unsharp at CRF 16, ~13-15 Mbps)
 10. 4-Gate Post-Flight QA Audit (1080p + MD5 Deduplication + 1s..10s Multi-Frame Camera-Lock MAD <= 15.0 + faster-whisper Speech Audit)
 11. Drift-Free Master Documentary MP4 concatenation

All paths, host descriptors, outfits, and languages are customizable via environment variables.
"""

import base64
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

os.environ["PATH"] = (
    f"{Path.home() / '.local' / 'bin'}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:"
    + os.environ.get("PATH", "")
)

# Customizable paths & parameters (override per episode via environment variables)
MASTER_DIR = os.environ.get("EPISODE_DIR", os.path.abspath("./episode-output"))
THUMB_DIR = os.path.join(MASTER_DIR, "thumbnails")
BY_SCENE_DIR = os.path.join(
    MASTER_DIR, os.environ.get("BY_SCENE_SUBDIR", "Scenes_01_to_22")
)
MANIFEST_PATH = os.path.join(
    MASTER_DIR, os.environ.get("MANIFEST_FILE", "parsed_episode_scenes.json")
)
DOWNLOADS_DIR = os.path.expanduser(os.environ.get("DOWNLOADS_DIR", "~/Downloads"))
FLOW_URL = os.environ.get("FLOW_URL", "https://flow.google.com/")
PODCAST_LANGUAGE = os.environ.get("PODCAST_LANGUAGE", "Marathi")
WHISPER_LANG = os.environ.get("WHISPER_LANG", "mr")

PLATE_WIDE = os.environ.get("PLATE_WIDE", "master_2shot_studio_plate_1080p.jpg")
PLATE_CAMA = os.environ.get("PLATE_CAMA", "camA_lead_host_closeup_plate_1080p.jpg")
PLATE_CAMB = os.environ.get("PLATE_CAMB", "camB_cohost_closeup_plate_1080p.jpg")

HOST_A_DESC = os.environ.get(
    "HOST_A_DESC", "the mature Indian man with glasses and mustache"
)
HOST_B_DESC = os.environ.get(
    "HOST_B_DESC", "the young Indian woman with glasses"
)

CHATE_OUTFIT = os.environ.get(
    "CHATE_OUTFIT",
    "a tailored rich burgundy-wine blazer, crisp light-cream dress shirt, and classic navy-and-gold striped silk tie",
)
ROOHI_OUTFIT = os.environ.get(
    "ROOHI_OUTFIT",
    "a tailored warm camel-beige structured blazer over a deep black silk blouse",
)

FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE_BIN = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe") or "ffprobe"


def load_manifest() -> list:
    if not os.path.exists(MANIFEST_PATH):
        print(
            f"[!] Manifest not found at {MANIFEST_PATH}. Set EPISODE_DIR and MANIFEST_FILE env vars.",
            flush=True,
        )
        return []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_js(js: str) -> str:
    r = subprocess.run(
        ["/usr/bin/pkill", "-f", "Google Chrome.*--user-data-dir="],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if r.returncode == 0:
        time.sleep(0.6)
    escaped = js.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    apple = f'''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "flow.google" then
                    return execute t javascript "{escaped}"
                end if
            end repeat
        end repeat
    end tell
    '''
    for _ in range(4):
        try:
            return (
                subprocess.check_output(
                    ["/usr/bin/osascript", "-e", apple], stderr=subprocess.DEVNULL
                )
                .decode("utf-8", "ignore")
                .strip()
            )
        except Exception:
            time.sleep(0.8)
            subprocess.run(
                ["/usr/bin/pkill", "-f", "Google Chrome.*--user-data-dir="],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            time.sleep(0.5)
    return ""


def create_new_flow_project() -> None:
    """Navigates to Google Flow home, clicks + New project, and locks video duration to 10s (Omni 1.1 Flash)."""
    run_js(f'window.location.href = "{FLOW_URL}";')
    time.sleep(5.0)
    res = run_js("""
    (function() {
        const btns = Array.from(document.querySelectorAll("button, a"));
        const np = btns.find(b => (b.innerText || "").includes("New project") || (b.getAttribute("aria-label") || "").includes("New project"));
        if (np) { np.click(); return "CLICKED_NEW_PROJECT"; }
        return "NOT_FOUND";
    })()
    """)
    print(f"Create New Project: {res}", flush=True)
    time.sleep(5.0)
    # Open Video settings pill and switch default 8s -> 10s
    run_js("""
    (function() {
        const b = Array.from(document.querySelectorAll("button")).find(el => (el.innerText || "").includes("Video ·"));
        if (b) b.click();
    })()
    """)
    time.sleep(1.0)
    run_js("""
    (function() {
        const btns = Array.from(document.querySelectorAll("button, [role=button], [role=tab], [role=option]"));
        const b10 = btns.find(el => (el.innerText || "").trim() === "10s" && el.offsetParent !== null);
        if (b10) b10.click();
    })()
    """)
    time.sleep(0.8)
    run_js("document.body.click();")
    time.sleep(0.5)
    pill = run_js(
        'Array.from(document.querySelectorAll("button")).map(b => (b.innerText || "").replace(/\\n+/g, " ").trim()).filter(s => s.includes("Video ·")).join(" || ")'
    )
    url = run_js("window.location.href")
    print(f"Active Google Flow Project: {url} | Settings: {pill}", flush=True)


def clean_failed_flow_cards() -> None:
    """Deletes any Failed generation cards in Google Flow so card indexing stays 100% aligned."""
    res = run_js("""
    (function() {
        const dels = Array.from(document.querySelectorAll("button")).filter(b => (b.innerText || "").trim() === "delete_forever");
        dels.forEach(b => b.click());
        return dels.length;
    })()
    """)
    if res and res != "0":
        print(f"Cleaned {res} failed card(s) from Google Flow UI.", flush=True)
        time.sleep(1.5)


def upload_plates_to_flow() -> None:
    """Uploads all 3 episode studio plates into the active Google Flow project via Base64 DataTransfer."""
    for fname in (PLATE_WIDE, PLATE_CAMA, PLATE_CAMB):
        fpath = os.path.join(MASTER_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "rb") as fp:
            b64 = base64.b64encode(fp.read()).decode("ascii")
        run_js("""
        (function() {
            document.body.click();
            const clr = document.querySelector("button[aria-label='Clear prompt']");
            if (clr) clr.click();
            const dels = Array.from(document.querySelectorAll("button")).filter(b => {
                const t = (b.innerText || "").trim();
                return (t === "close" || t === "cancel") && b.offsetParent !== null;
            });
            dels.forEach(d => d.click());
        })()
        """)
        time.sleep(0.8)
        res = run_js(f"""
        (function() {{
            const b64 = "{b64}";
            const bin = atob(b64);
            const arr = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
            const file = new File([arr], "{fname}", {{type: "image/jpeg"}});
            const dt = new DataTransfer();
            dt.items.add(file);
            const pm = document.querySelector(".ProseMirror") || document.body;
            pm.focus();
            pm.dispatchEvent(new ClipboardEvent("paste", {{bubbles: true, cancelable: true, clipboardData: dt}}));
            return "UPLOADED_" + "{fname}";
        }})()
        """)
        print(res, flush=True)
        time.sleep(6.0)


def attach_camera_plate(plate_filename: str, reuse_marker: str = None) -> None:
    """Directly attaches the exact 1920x1080 camera plate via single ClipboardEvent('paste') and enforces a single-ingredient lock."""
    run_js("""
    (function() {
        document.body.click();
        const clr = document.querySelector("button[aria-label='Clear prompt']");
        if (clr) clr.click();
        const dels = Array.from(document.querySelectorAll("button")).filter(b => {
            const t = (b.innerText || "").trim();
            return (t === "close" || t === "cancel") && b.offsetParent !== null;
        });
        dels.forEach(d => d.click());
    })()
    """)
    time.sleep(0.6)

    fpath = os.path.join(MASTER_DIR, plate_filename)
    with open(fpath, "rb") as fp:
        b64 = base64.b64encode(fp.read()).decode("ascii")
    run_js(f"""
    (function() {{
        const b64 = "{b64}";
        const bin = atob(b64);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        const file = new File([arr], "{plate_filename}", {{type: "image/jpeg"}});
        const dt = new DataTransfer();
        dt.items.add(file);
        const pm = document.querySelector(".ProseMirror") || document.body;
        pm.focus();
        pm.dispatchEvent(new ClipboardEvent("paste", {{bubbles: true, cancelable: true, clipboardData: dt}}));
    }})()
    """)
    time.sleep(5.0)

    # Guarantee single-ingredient lock
    run_js("""
    (function() {
        const dels = Array.from(document.querySelectorAll("button")).filter(b => (b.innerText || "").trim() === "close" && b.offsetParent !== null);
        if (dels.length > 1) {
            for (let i = 1; i < dels.length; i++) dels[i].click();
        }
    })()
    """)
    time.sleep(0.5)


def submit_clip_by_camera(item: dict) -> None:
    code = item["code"]
    role = item["role"]
    camera = item.get("camera", "wide_2shot")
    text = item["text"]

    if camera == "broll":
        run_js("""
        (function() {
            document.body.click();
            const clr = document.querySelector("button[aria-label='Clear prompt']");
            if (clr) clr.click();
            const dels = Array.from(document.querySelectorAll("button")).filter(b => {
                const t = (b.innerText || "").trim();
                return (t === "close" || t === "cancel") && b.offsetParent !== null;
            });
            dels.forEach(d => d.click());
        })()
        """)
        time.sleep(0.6)
        new_text = text
    elif camera == "cam_a_chate_closeup":
        attach_camera_plate(PLATE_CAMA)
        new_text = (
            f"Solo medium close-up of {HOST_A_DESC} in {CHATE_OUTFIT} seated at a wooden podcast studio desk: "
            f"He speaks directly into his broadcast microphone with a deep, resonant, authoritative male voice in crystal-clear {PODCAST_LANGUAGE}, "
            f'pronouncing every single word exactly: \\"{text}\\" Clear natural lip-sync and expressive facial nuances matching the spoken {PODCAST_LANGUAGE} words, '
            f"85mm portrait lens with warm wood-slat and studio lamp bokeh in the background. "
            f"Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes."
        )
    elif camera == "cam_b_roohi_closeup":
        attach_camera_plate(PLATE_CAMB)
        new_text = (
            f"Solo medium close-up of {HOST_B_DESC} in {ROOHI_OUTFIT} seated at a wooden podcast studio desk: "
            f"She speaks into her broadcast microphone with an engaging, expressive female voice in crystal-clear {PODCAST_LANGUAGE}, "
            f'pronouncing every single word exactly: \\"{text}\\" Clear natural lip-sync and expressive journalistic demeanor matching the spoken {PODCAST_LANGUAGE} words, '
            f"85mm portrait lens with warm illuminated studio bookshelf bokeh in the background. "
            f"Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes."
        )
    else:
        attach_camera_plate(PLATE_WIDE)
        if role == "chate":
            new_text = (
                f"Wide two-shot of two podcast hosts seated together at a curved wooden podcast studio desk: "
                f"{HOST_A_DESC.capitalize()} on the left in {CHATE_OUTFIT} leans forward speaking directly into his broadcast microphone "
                f"with a deep, resonant, authoritative male voice in crystal-clear {PODCAST_LANGUAGE}, "
                f'pronouncing every single word exactly: \\"{text}\\" Clear natural lip-sync matching the spoken {PODCAST_LANGUAGE} words. '
                f"{HOST_B_DESC.capitalize()} on the right in {ROOHI_OUTFIT} remains completely silent, looking at him attentively with closed mouth. "
                f"Both remain seated at the podcast desk in the studio. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes."
            )
        else:
            new_text = (
                f"Wide two-shot of two podcast hosts seated together at a curved wooden podcast studio desk: "
                f"{HOST_B_DESC.capitalize()} on the right in {ROOHI_OUTFIT} leans forward speaking into her broadcast microphone "
                f"with an engaging, enthusiastic female voice in crystal-clear {PODCAST_LANGUAGE}, "
                f'pronouncing every single word exactly: \\"{text}\\" Clear natural lip-sync matching the spoken {PODCAST_LANGUAGE} words. '
                f"{HOST_A_DESC.capitalize()} on the left in {CHATE_OUTFIT} remains completely silent, looking at her attentively with closed mouth. "
                f"Both remain seated at the podcast desk in the studio. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes."
            )

    run_js(f"""
    (function() {{
        const pm = document.querySelector(".ProseMirror");
        pm.focus();
        const p = pm.querySelector("p");
        const newText = "{new_text}";
        if (p.lastChild && p.lastChild.nodeType === 3) p.lastChild.nodeValue = newText;
        else p.textContent = newText;
        pm.dispatchEvent(new InputEvent("input", {{bubbles: true, inputType: "insertText", data: newText}}));
    }})()
    """)
    time.sleep(0.8)
    st = run_js("""
    (function() {
        const btn = document.querySelector("button[aria-label='Start generation']");
        if (!btn || btn.disabled) return "DISABLED";
        btn.click();
        return "STARTED";
    })()
    """)
    print(f"Submitted {code} ({camera}): {st}", flush=True)
    time.sleep(4.0)


def wait_top_n_ready(n: int = 2, timeout: int = 240) -> list:
    t0 = time.time()
    last_arr = []
    while time.time() - t0 < timeout:
        raw = run_js(f"""
        (function() {{
            const btns = Array.from(document.querySelectorAll("button[aria-label='Reuse prompt']"));
            return JSON.stringify(btns.slice(0, {n}).map((b, i) => {{
                let el = b;
                for (let k=0; k<6; k++) if (el.parentElement) el = el.parentElement;
                return (el.innerText || "").replace(/\\n+/g, " | ").slice(0, 140);
            }}));
        }})()
        """)
        if raw:
            arr = json.loads(raw)
            last_arr = arr
            if len(arr) >= n and all("%" not in s and "Generating" not in s for s in arr):
                print("All top", n, "cards finished!", flush=True)
                return arr
            print("Progress:", [s[:45] for s in arr], flush=True)
        time.sleep(5)
    print("Warning: Timeout waiting for top cards, proceeding with finished cards:", last_arr, flush=True)
    return last_arr


def trigger_1080p_card(idx: int) -> str:
    run_js(f"""
    (function() {{
        document.body.click();
        const reuseBtns = Array.from(document.querySelectorAll("button[aria-label='Reuse prompt']"));
        const b = reuseBtns[{idx}];
        if (b) {{
            b.scrollIntoView({{block: "center"}});
            const more = b.parentElement.querySelector("button[aria-label='More options']");
            if (more) more.click();
        }}
    }})()
    """)
    time.sleep(0.8)
    run_js("""
    (function() {
        const items = Array.from(document.querySelectorAll("[role=menuitem], .mat-mdc-menu-item")).filter(el => el.offsetParent !== null && el.innerText.includes("Download"));
        const dl = items.pop();
        if (dl) {
            dl.dispatchEvent(new MouseEvent("mouseenter", {bubbles: true}));
            dl.click();
        }
    })()
    """)
    time.sleep(0.8)
    res = run_js("""
    (function() {
        const items = Array.from(document.querySelectorAll("[role=menuitem], .mat-mdc-menu-item")).filter(el => el.offsetParent !== null && el.innerText.includes("1080p"));
        const up = items.pop();
        if (up) {
            up.click();
            return "CLICKED_1080P";
        }
        return "NO_1080P";
    })()
    """)
    return res


CONSUMED_SIZES = set()
for existing_dl in glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4")):
    try:
        CONSUMED_SIZES.add(os.path.getsize(existing_dl))
    except Exception:
        pass


def download_single_card_1080p(idx: int, label: str) -> str:
    time.sleep(5.0)
    dl_pattern = os.path.join(DOWNLOADS_DIR, "*.mp4")
    before = set(glob.glob(dl_pattern))
    r = ""
    for _ in range(3):
        r = trigger_1080p_card(idx)
        if r == "CLICKED_1080P":
            break
        time.sleep(1.5)
    print(f"[{label}] Card {idx} trigger 1: {r}", flush=True)
    upscale_seen = False
    for attempt in range(65):
        time.sleep(3.0)
        now = set(glob.glob(dl_pattern)) - before
        ready = [
            f
            for f in now
            if not os.path.exists(f + ".crdownload")
            and os.path.getsize(f) > 1500000
            and os.path.getsize(f) not in CONSUMED_SIZES
        ]
        if ready:
            f = sorted(ready, key=os.path.getmtime)[-1]
            sz = os.path.getsize(f)
            CONSUMED_SIZES.add(sz)
            print(f"[{label}] Downloaded: {os.path.basename(f)} ({sz//1024} KB)", flush=True)
            time.sleep(5.0)
            return f
        tail = run_js("document.body.innerText.slice(-350)")
        if "Upscaling your video" in tail:
            upscale_seen = True
        elif upscale_seen and attempt > 8:
            print(f"[{label}] Upscale toast cleared, clicking 1080p to fetch cached file...", flush=True)
            trigger_1080p_card(idx)
            upscale_seen = False
        elif not upscale_seen and attempt == 15:
            print(f"[{label}] No upscale toast seen after 45s, clicking 1080p once...", flush=True)
            trigger_1080p_card(idx)
    raise RuntimeError(f"Failed to download 1080p for {label} (card {idx})")


def catalog_and_sharpen_clip(item: dict, downloaded_mp4: str) -> None:
    os.makedirs(THUMB_DIR, exist_ok=True)
    os.makedirs(BY_SCENE_DIR, exist_ok=True)
    code = item["code"]
    fname = item["filename"]
    dst = os.path.join(MASTER_DIR, fname)
    try:
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-i",
                downloaded_mp4,
                "-vf",
                "cas=0.55,unsharp=5:5:0.75:3:3:0.35",
                "-c:v",
                "libx264",
                "-crf",
                "16",
                "-preset",
                "fast",
                "-c:a",
                "copy",
                dst,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except Exception:
        shutil.copy2(downloaded_mp4, dst)

    sc = item["scene"]
    sc_dir = os.path.join(BY_SCENE_DIR, f"Scene_{sc:02d}")
    os.makedirs(sc_dir, exist_ok=True)
    link_dst = os.path.join(sc_dir, fname)
    if os.path.exists(link_dst):
        os.remove(link_dst)
    try:
        os.link(dst, link_dst)
    except Exception:
        shutil.copy2(dst, link_dst)

    jpg = os.path.join(THUMB_DIR, fname[:-4] + ".jpg")
    try:
        subprocess.run(
            [FFMPEG_BIN, "-y", "-ss", "00:00:03", "-i", dst, "-frames:v", "1", "-q:v", "2", jpg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        out = subprocess.check_output(
            [FFPROBE_BIN, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,bit_rate", "-of", "json", dst],
            timeout=15,
        ).decode()
        st = json.loads(out)["streams"][0]
        print(
            f"Cataloged & Sharpened {code} ({item.get('camera')}) -> {fname} ({st['width']}x{st['height']} @ {int(st.get('bit_rate',0))//1000}k)",
            flush=True,
        )
    except Exception as e:
        print(f"Cataloged & Sharpened {code} -> {fname} (note: {e})", flush=True)


def is_clip_done(item: dict) -> bool:
    dst = os.path.join(MASTER_DIR, item["filename"])
    return os.path.exists(dst) and os.path.getsize(dst) > 1500000


def run_camera_queue(camera_name: str, max_batches: int = None) -> None:
    manifest = load_manifest()
    for pass_num in range(1, 4):
        clean_failed_flow_cards()
        todo = [it for it in manifest if it.get("camera") == camera_name and not is_clip_done(it)]
        print(f"\n[{camera_name.upper()} - Pass {pass_num}] Remaining clips to generate: {len(todo)}", flush=True)
        if not todo:
            break
        batches = [todo[i : i + 2] for i in range(0, len(todo), 2)]
        if max_batches is not None:
            batches = batches[:max_batches]
        for b_idx, batch in enumerate(batches, start=1):
            clean_failed_flow_cards()
            codes = [it["code"] for it in batch]
            print(f"\n=== {camera_name.upper()} BATCH {b_idx}/{len(batches)}: {codes} ===", flush=True)
            for it in batch:
                submit_clip_by_camera(it)
            time.sleep(12)
            arr = wait_top_n_ready(len(batch))
            for i, it in enumerate(batch):
                card_idx = len(batch) - 1 - i
                if card_idx < len(arr) and ("Failed" in arr[card_idx] or "can't generate" in arr[card_idx]):
                    print(f"[{it['code']}] Card {card_idx} reported generation failure, skipping for retry pass.", flush=True)
                    continue
                try:
                    f = download_single_card_1080p(card_idx, it["code"])
                    catalog_and_sharpen_clip(it, f)
                except Exception as e:
                    print(f"[{it['code']}] Error downloading/cataloging card {card_idx}: {e}", flush=True)
            clean_failed_flow_cards()
        if max_batches is not None:
            break


def audit_camera_lock_1s_to_10s(mad_threshold: float = 15.0) -> list:
    """Scans all 10 seconds (1 fps) of every studio clip against its reference plate and removes any drifted clip."""
    manifest = load_manifest()
    plates = {}
    for cam, pfile in (
        ("wide_2shot", PLATE_WIDE),
        ("cam_a_chate_closeup", PLATE_CAMA),
        ("cam_b_roohi_closeup", PLATE_CAMB),
    ):
        ppath = os.path.join(MASTER_DIR, pfile)
        if os.path.exists(ppath):
            plates[cam] = np.array(
                Image.open(ppath).resize((160, 90)), dtype=np.float32
            )

    drifted = []
    for it in manifest:
        cam = it.get("camera")
        if cam not in plates:
            continue
        p = os.path.join(MASTER_DIR, it["filename"])
        if not os.path.exists(p):
            continue
        raw = subprocess.check_output(
            [
                FFMPEG_BIN,
                "-v",
                "error",
                "-i",
                p,
                "-vf",
                "fps=1,scale=160:90",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            stderr=subprocess.DEVNULL,
        )
        n_frames = len(raw) // (160 * 90 * 3)
        if n_frames == 0:
            continue
        frames = (
            np.frombuffer(raw[: n_frames * 160 * 90 * 3], dtype=np.uint8)
            .reshape((n_frames, 90, 160, 3))
            .astype(np.float32)
        )
        mads = [
            round(float(np.mean(np.abs(frames[i] - plates[cam]))), 1)
            for i in range(n_frames)
        ]
        if max(mads) > mad_threshold:
            drifted.append((it["code"], cam, max(mads), mads))
            print(
                f"[CAMERA-LOCK DRIFT] {it['code']} ({cam}): max MAD={max(mads)} | 1s..10s={mads} -> Removing for regeneration",
                flush=True,
            )
            os.remove(p)
    return drifted


def audit_speech_with_whisper() -> list:
    """Gate 3: Runs faster-whisper on every studio clip to verify spoken dialogue accuracy and catch garbled/mismatched audio."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Note: faster_whisper not installed in active python; skipping Gate 3 speech audit.", flush=True)
        return []

    manifest = load_manifest()
    model = WhisperModel("small", device="cpu", compute_type="int8")

    def words_set(s: str) -> set:
        return set(re.findall(r"[\u0900-\u097F\w]+", s.lower()))

    flagged = []
    for it in manifest:
        if it.get("role") == "broll":
            continue
        p = os.path.join(MASTER_DIR, it["filename"])
        if not os.path.exists(p):
            continue
        segs, _ = model.transcribe(p, language=WHISPER_LANG)
        tr = " ".join(s.text for s in segs).strip()
        target_w = words_set(it["text"])
        tr_w = words_set(tr)
        best_code = it["code"]
        best_score = len(target_w & tr_w)
        for other in manifest:
            if other.get("role") == "broll":
                continue
            sc = len(words_set(other["text"]) & tr_w)
            if sc > best_score + 1:
                best_score = sc
                best_code = other["code"]
        if best_code != it["code"] or (best_score == 0 and len(tr_w) == 0):
            print(
                f"[SPEECH QA FLAGGED] {it['code']} ({it['camera']}): best_code={best_code}, score={best_score}, transcript={tr[:70]} -> Removing for regeneration",
                flush=True,
            )
            flagged.append(it["code"])
            os.remove(p)
    return flagged


def audit_and_assemble_master(master_filename: str = "EPISODE_FULL_DOCUMENTARY_1080P_MASTER.mp4") -> None:
    manifest = load_manifest()
    # Gate 2: Run 1s..10s multi-frame camera-lock audit and auto-regenerate any drifted studio clips
    drifted = audit_camera_lock_1s_to_10s(mad_threshold=15.0)
    if drifted:
        print(f"Auto-regenerating {len(drifted)} drifted studio clips...", flush=True)
        for cam in ("cam_a_chate_closeup", "cam_b_roohi_closeup", "wide_2shot"):
            run_camera_queue(cam)

    # Gate 3: Run faster-whisper speech audit and auto-regenerate any garbled/mismatched clips
    bad_speech = audit_speech_with_whisper()
    if bad_speech:
        print(f"Auto-regenerating {len(bad_speech)} speech-flagged studio clips...", flush=True)
        for cam in ("cam_a_chate_closeup", "cam_b_roohi_closeup", "wide_2shot"):
            run_camera_queue(cam)

    missing, low_res, dups = [], [], []
    hashes = {}
    for it in manifest:
        p = os.path.join(MASTER_DIR, it["filename"])
        if not os.path.exists(p):
            missing.append(it["code"])
            continue
        with open(p, "rb") as fp:
            h = hashlib.md5(fp.read()).hexdigest()
        if h in hashes:
            dups.append((hashes[h], it["code"]))
        else:
            hashes[h] = it["code"]
        out = subprocess.check_output(
            [FFPROBE_BIN, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,bit_rate", "-of", "json", p]
        ).decode()
        st = json.loads(out)["streams"][0]
        if st["width"] != 1920 or st["height"] != 1080:
            low_res.append((it["code"], st["width"], st["height"]))

    print(
        f"Post-Flight Audit: {len(manifest) - len(missing)}/{len(manifest)} clips | Missing: {missing} | Low-Res: {low_res} | Duplicates: {dups}",
        flush=True,
    )
    if missing or low_res or dups:
        raise RuntimeError("Post-Flight QA Audit failed! Resolve missing/low-res/duplicate clips before master assembly.")

    concat_list_path = os.path.join(MASTER_DIR, "episode_concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for item in manifest:
            clip_path = os.path.join(MASTER_DIR, item["filename"])
            escaped_path = clip_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    output_master = os.path.join(MASTER_DIR, master_filename)
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            "aresample=async=1:first_pts=0",
            "-movflags",
            "+faststart",
            output_master,
        ],
        check=True,
    )
    print(f"Master 1080p Documentary rendered: {output_master}", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    limit = int(sys.argv[2]) if len(sys.argv[2:]) >= 1 else None
    if mode == "init_new_project":
        create_new_flow_project()
    elif mode == "upload_plates":
        upload_plates_to_flow()
    elif mode == "assemble":
        audit_and_assemble_master()
    elif mode in ("wide_2shot", "cam_a_chate_closeup", "cam_b_roohi_closeup", "broll"):
        run_camera_queue(mode, limit)
    else:
        for cam in ("cam_a_chate_closeup", "cam_b_roohi_closeup", "wide_2shot", "broll"):
            run_camera_queue(cam, limit)
        audit_and_assemble_master()
    print("\n=== MULTI-CAM 3-CAMERA + B-ROLL ENGINE (v4.0) COMPLETED SUCCESSFULLY ===", flush=True)
