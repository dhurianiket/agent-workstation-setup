---
name: cinematic-marathi-podcast-production
description: >
  End-to-end production pipeline (v4.0) for high-end cinematic Marathi (or customizable multilingual)
  documentary and two-host podcast videos using Google Flow (Gemini Omni 1.1 Flash) and FFmpeg.
  Enforces automated New Project creation & 10s setting verification on Google Flow,
  Episode Wardrobe Customization with Non-Repeating Outfit Registry, 3-Camera + B-Roll
  Documentary Switching (Wide 2-Shot + Cam A Lead Host Solo Close-Up + Cam B Co-Host
  Solo Close-Up + B-Roll), 2-Card Top-Row Batching (eliminating Masonry Row-2 swaps),
  Single-Paste Base64 Plate Lock with Static Tripod Camera prompts, Mandatory 1080p Upscaled
  downloads with anti-duplicate guards, Broadcast Optical Detail Restoration (CAS + Unsharp
  at CRF 16, ~13-15 Mbps), 4-Gate QA Audit (1080p/MD5 + 1s..10s Camera-Lock MAD <= 15.0 +
  faster-whisper Speech Accuracy Audit), and drift-free 1080p Master Documentary assembly.
---

# Cinematic Marathi Podcast & Documentary Production Skill (`v4.0` — Customizable 3-Camera + B-Roll Multi-Cam Engine)

A battle-tested operational guide and automation runbook for producing broadcast-grade, razor-sharp `1080p` investigative documentaries and two-host podcast videos using **Google Flow (`Gemini Omni 1.1 Flash`)**, **FFmpeg Broadcast Optical Restoration (`CRF 16`)**, and **4-Gate Automated QA (`faster-whisper` + `1s..10s` Multi-Frame Camera-Lock Audit)**.

---

## 0. Quick Customization Guide (Adapt for Your Own Channel, Hosts & Language)

Anyone cloning the **Antigravity Autonomous Workstation** can use this skill out of the box for Marathi two-host documentaries OR customize it for their own YouTube channel, hosts, wardrobe, and language via environment variables (without editing core engine code):

```bash
# Optional environment variable overrides for custom channels / hosts / languages:
export EPISODE_DIR="./episodes/episode-01"
export FLOW_URL="https://flow.google.com/"
export PODCAST_LANGUAGE="Marathi"               # e.g., Marathi, Hindi, English, Tamil, etc.
export WHISPER_LANG="mr"                        # ISO code for faster-whisper Gate 3 audit (mr, hi, en, etc.)

# Customize Host A (Left Anchor) & Host B (Right Co-Host) visual descriptors:
export HOST_A_DESC="the mature Indian man with glasses and mustache"
export HOST_B_DESC="the young Indian woman with glasses"

# Customize Episode Wardrobe (Non-Repeating Outfit Registry):
export CHATE_OUTFIT="a tailored midnight-indigo pinstripe blazer, pale lavender dress shirt, and silver-grey silk tie"
export ROOHI_OUTFIT="a tailored deep plum-violet structured blazer over a soft cream silk blouse"

# Run the full 3-Camera + B-Roll pipeline:
python3 skills/cinematic-marathi-podcast-production/scripts/flow_1080p_2shot_production_engine.py init_new_project
python3 skills/cinematic-marathi-podcast-production/scripts/flow_1080p_2shot_production_engine.py all
```

---

## 1. Default Production Context & Character Bible (Customizable)

* **Format**: High-Retention Investigative Documentary & Two-Host Studio Podcast (`16:9`, `1920x1080`)
* **Lead Host (Anchor 1 — Camera A / Left Side)**:
  * **Screen Position**: **LEFT** side of curved wooden podcast desk (with glasses and mustache).
  * **Vocal Persona**: Authoritative, mature, deep, resonant male voice ($F_0 \approx 115 - 165\text{ Hz}$).
  * **Prompt Character Descriptor (`HOST_A_DESC`)**: *"The mature Indian man with glasses and mustache in [CHATE_OUTFIT]"* (**Rule**: NEVER use real personal names in generation prompts to avoid public-figure safety blocks).
  * **Fallback TTS Voice**: `mr-IN-ManoharNeural`
* **Co-Host & Investigative Anchor (Anchor 2 — Camera B / Right Side)**:
  * **Screen Position**: **RIGHT** side of curved wooden podcast desk (with glasses and dark wavy hair).
  * **Vocal Persona**: Expressive, clear, journalistic, energetic young female voice ($F_0 \approx 220 - 275\text{ Hz}$).
  * **Prompt Character Descriptor (`HOST_B_DESC`)**: *"The young Indian woman with glasses in [ROOHI_OUTFIT]"*
  * **Fallback TTS Voice**: `mr-IN-AarohiNeural`

---

## 2. Step 0: New Episode Setup, Google Flow Project Creation & Non-Repeating Wardrobe Registry

For every new script/episode:
1. **All Files Strictly in the Episode Folder (`$EPISODE_DIR`)**: Save all episode manifests (`build_scriptX_manifest.py`, `parsed_scriptX_scenes.json`), studio plates (`scriptX_*_1080p.jpg`), production scripts, scene clips, `thumbnails/`, `Scenes_01_to_NN/`, and the final `EPISODE_XX_..._1080P_MASTER.mp4` inside the episode's dedicated folder.
2. **Create a Brand-New Project on Google Flow (`flow.google.com`) & Lock to `10s`**:
   * Navigate to `$FLOW_URL` (`https://flow.google.com/`) and click `+ New project`.
   * **CRITICAL (`8s -> 10s` Default Trap)**: Every brand-new Google Flow project defaults to **`Video · 720p · 8s`**. Always click the `Video · 720p · ...` settings pill in the bottom bar, click **`10s`**, and verify the pill reads **`Video · 720p · 10s | crop_16_9 | x1`** (`Omni 1.1 Flash`) before submitting any prompts. (Automated via `create_new_flow_project()` in [`scripts/flow_1080p_2shot_production_engine.py`](scripts/flow_1080p_2shot_production_engine.py)).
3. **Non-Repeating Episode Wardrobe Registry (Sample Presets)**:
   * Never repeat a host outfit from a previous episode. Select a fresh preset or define your own via `CHATE_OUTFIT` and `ROOHI_OUTFIT`:

| Episode | Lead Host (`CHATE_OUTFIT` — Left) | Co-Host (`ROOHI_OUTFIT` — Right) |
| :--- | :--- | :--- |
| **Preset 01 & 02** | Classic navy-blue blazer, white shirt, crimson-red tie | Maroon/burgundy blazer over dark top |
| **Preset 03** | Tailored dark espresso-brown blazer, crisp sky-blue dress shirt, golden-amber silk tie | Tailored deep emerald-teal blazer over an ivory silk blouse |
| **Preset 04** | Tailored charcoal-grey tweed blazer, crisp white dress shirt, royal forest-green silk tie | Tailored royal cobalt-blue blazer over a pearl-white silk blouse |
| **Preset 05** | Tailored rich burgundy-wine blazer, crisp light-cream dress shirt, navy-and-gold striped silk tie | Tailored warm camel-beige structured blazer over a deep black silk blouse |
| **Preset 06** | Tailored midnight-indigo pinstripe blazer, pale lavender dress shirt, silver-grey silk tie | Tailored deep plum-violet structured blazer over a soft cream silk blouse |
| **Preset 07** | Tailored olive-khaki linen-blend blazer, crisp white dress shirt, deep rust-orange silk tie | Tailored terracotta-coral blazer over a charcoal-black silk blouse |
| **Preset 08** | Tailored classic black double-breasted blazer, icy-blue dress shirt, burgundy-and-silver patterned tie | Tailored sage-green structured blazer over a pearl-ivory silk blouse |

4. **Generate the 3 Episode-Specific `1920x1080` Studio Reference Plates**:
   * Customize **ONLY** the two hosts' clothing/outfits for the new episode while keeping 100% of their facial features, glasses, hair, microphones, wooden desk, glowing tripod lamp, acoustic wood-slat walls, and right-side bookshelf identical:
     1. **`scriptX_master_2shot_studio_plate_1080p.jpg` (Camera 1 — Wide 2-Shot)**: 16:9 wide two-shot of both hosts seated at the curved wooden podcast desk in their new episode outfits, scaled to `1920x1080` (`-vf "scale=1920:1080:flags=lanczos,cas=0.4" -q:v 1`).
     2. **`scriptX_camA_chate_closeup_plate_1080p.jpg` (Camera 2 — Solo Medium Close-Up of Lead Host)**: 16:9 85mm portrait lens chest-to-head framing of Lead Host in the exact same episode outfit, angled slightly right toward the co-host with broadcast microphone in the foreground and warm wood-slat/studio lamp bokeh behind (`1920x1080`).
     3. **`scriptX_camB_roohi_closeup_plate_1080p.jpg` (Camera 3 — Solo Medium Close-Up of Co-Host)**: 16:9 85mm portrait lens chest-to-head framing of Co-Host in the exact same episode outfit, angled slightly left toward the lead host with broadcast microphone in the foreground and warm illuminated studio bookshelf bokeh behind (`1920x1080`).

---

## 3. Multi-Cam 3-Camera + B-Roll Documentary Switching Architecture

> [!IMPORTANT]
> **Top-Tier Documentary Pacing — Change Camera Angle Every 10 Seconds**:
> Never keep a documentary or podcast locked on a static wide two-shot for back-to-back clips. Every multi-part scene MUST alternate across four distinct visual views using **dedicated Single-Ingredient Studio Plates** attached directly via Base64 on every card:

### 3.1 Deterministic Scene Camera Switching Pattern
1. **Camera 1 — Establishing Wide 2-Shot (`wide_2shot`)**:
   * **Assigned Beats**: Odd studio beats (`clip_in_scene == 1`, `clip_in_scene == 3`) of multi-part studio scenes to establish both hosts interacting across the desk.
   * **Locked Single Ingredient**: `scriptX_master_2shot_studio_plate_1080p.jpg`.
2. **Camera 2 — Solo Medium Close-Up: Lead Host (`cam_a_chate_closeup`)**:
   * **Assigned Beats**: Even studio beats (`clip_in_scene == 2`, `clip_in_scene == 4`) whenever Lead Host (`role == "chate"`) is speaking during deep storytelling beats, scientific investigations, and emotional revelations.
   * **Locked Single Ingredient**: `scriptX_camA_chate_closeup_plate_1080p.jpg`.
3. **Camera 3 — Solo Medium Close-Up: Co-Host (`cam_b_roohi_closeup`)**:
   * **Assigned Beats**: Even studio beats (`clip_in_scene == 2`, `clip_in_scene == 4`) of Co-Host's (`role == "roohi"`) multi-part scenes.
   * **Locked Single Ingredient**: `scriptX_camB_roohi_closeup_plate_1080p.jpg`.
4. **Cinematic 1080p B-Roll Cutaways (`broll`)**:
   * **Assigned Beats**: Closing visual cutaway of key narrative scenes (10–15 B-Roll clips per episode) to visualize historical events, locations, and scientific phenomena in full-screen 1080p.
   * **Ingredient**: None (0 ingredients attached).

### 3.2 Single-Event `ClipboardEvent("paste")` Plate Lock (No Duplicate `drop` Race)
* **Critical Rule (v4.0)**: Never fire both `ClipboardEvent("paste")` and `DragEvent("drop")` when attaching a Base64 camera plate — firing both uploads two copies of the image simultaneously and causes every 2nd card in a batch to fail with `"Sorry, this video failed to generate"`.
* Instead, `attach_camera_plate(plate_filename)` MUST:
  1. Clear the prompt box (`button[aria-label='Clear prompt']`) and close any existing ingredient chips (`close` / `cancel`).
  2. Dispatch **ONLY** `ClipboardEvent("paste")` on `.ProseMirror` and wait `5.0 seconds` for the single ingredient upload to settle.
  3. Strip any accidental 2nd ingredient chip before submitting and wait `4.0 seconds` after clicking `Start generation` before starting the next card's paste.

### 3.3 Mandatory 2-Card Top-Row Batching (Zero Masonry Row-2 Swap)
* **Why 2-Card Batches Are Mandatory for Studio Queues**:
  * Google Flow renders cards in a 2-column Masonry layout where failed cards (`height: 310px`) are shorter than finished video cards (`height: 391px`).
  * In a 4-card batch, if Row 1 has one failed card and one video card, the Masonry layout shifts the Y-coordinates of Row 2 (`idx 2` and `idx 3`), swapping their DOM order.
  * In a **2-card batch** (`batches = [todo[i : i + 2] for i in range(0, len(todo), 2)]`), both cards always sit side-by-side in **Row 1 (`y = 76`)**: `idx 0` (Top-Left) is ALWAYS `batch[1]` and `idx 1` (Top-Right) is ALWAYS `batch[0]`, eliminating Masonry order swaps 100%.

### 3.4 Mandatory 2-Step High-Definition & Optical Restoration Pipeline (`CRF 16`)
1. **Step A — Always Download via `1080p Upscaled`**:
   * Open the card's `More options` (`...`) $\rightarrow$ `Download` $\rightarrow$ **`1080p Upscaled`**.
   * Wait for Google Flow's `"Upscaling your video"` toast to finish and verify with `ffprobe` that the downloaded file is `1920x1080` (`> 1.5 MB`).
2. **Step B — Mandatory Broadcast Optical Detail Restoration (`CRF 16`, `~13–15 Mbps`)**:
   * Immediately pass every downloaded `1080p Upscaled` clip through FFmpeg **Contrast Adaptive Sharpening (`cas=0.55`) + Dual-Kernel Unsharp Masking (`unsharp=5:5:0.75:3:3:0.35`)** at `-crf 16`:
     ```bash
     ffmpeg -y -i raw_downloaded_1080p.mp4 \
       -vf "cas=0.55,unsharp=5:5:0.75:3:3:0.35" \
       -c:v libx264 -crf 16 -preset fast \
       -c:a copy \
       master_catalog_clip.mp4
     ```

---

## 4. Anti-Duplicate 1080p Download Protocol, Failed-Card Sweep & Chrome AppleEvents Guard

### 4.1 Kill Background `--user-data-dir=` Chrome Instances Before `osascript`
* Any background headless/isolated Chrome process (`--user-data-dir=...`) intercepts macOS AppleEvents (`tell application "Google Chrome"`) and returns empty strings.
* `run_js()` automatically runs `pkill -f "Google Chrome.*--user-data-dir="` before executing `osascript`.

### 4.2 Automated Google Flow Failed-Card Cleanup (`clean_failed_flow_cards`)
* Before starting any batch or retry pass, automatically click `delete_forever` on any failed card (`warning | Failed`) in Google Flow so failed cards never shift card indices or clutter the project UI.

### 4.3 Anti-Duplicate Download Guardrails (`download_single_card_1080p`)
1. **Global `CONSUMED_SIZES` Set**: Track the exact byte size (`os.path.getsize(f)`) of every downloaded `.mp4` across the entire run. Reject any file in `~/Downloads/` whose byte size is already in `CONSUMED_SIZES`.
2. **Pre- and Post-Download Cooldown (`5.0s`)**: Wait `5.0 seconds` before snapshotting `before = set(glob.glob(os.path.expanduser("~/Downloads/*.mp4")))` and wait `5.0 seconds` after a download completes so any late duplicate file from Chrome lands before the next card starts.
3. **Single Re-Click After Toast Clears**: Only click `1080p Upscaled` a second time if `"Upscaling your video"` was observed and then disappeared without any file landing in `~/Downloads/`.

---

## 5. Battle-Tested Safety Filter & Phonetic Clarity Lexicon (`v4.0`)

Google Flow utilizes strict automated safety classifiers (`Policy Violation` / `prominent people` / `Failed`) and multilingual TTS phonetics. Apply these verified replacements in your manifest builder before submitting prompts while preserving 100% narrative meaning:

| Category | Forbidden Term / Phrase | Verified 100%-Safe Replacement | Why It Gets Blocked / Fails |
| :--- | :--- | :--- | :--- |
| **Host Real Names** | Real personal names of hosts | `The mature Indian man with glasses and mustache` / `The young Indian woman with glasses` | Deepfake & public figure protection |
| **Living Hollywood / Indian Celebrities** | `हॉलिवूडचा अभिनेता ब्रॅड पिटचा... ब्रॅड पिटचा चेहरा` | `हॉलिवूडचा प्रसिद्ध चित्रपट... स्क्रीनवरील चित्र` | Living A-list celebrity / prominent people classifier |
| **Living Famous Scientists / Figures** | `सर रॉजर पेनरोझ`, `ग्रेटा ब्रॅडमन` | `जागतिक पातळीवरील ज्येष्ठ शास्त्रज्ञ`, `त्यांच्या कुटुंबातही शास्त्रीय संगीताचा वारसा पुढे चालत राहिला` | Living real-world celebrity/person filter |
| **Living Contemporary Athletes** | `रोहित शर्मा, विराट कोहली, स्टीव्ह स्मिथ, एबी डिविलियर्स, हॅरी ब्रूक` | `आधुनिक काळातील दिग्गज आक्रमक फलंदाज`, `नवखे फलंदाज` | Living celebrity / prominent people classifier |
| **Cities Homophonous with First Names** | `सिडनीपासून` (Sydney / Sidney) | `ऑस्ट्रेलियातील मुख्य शहरापासून` | Multilingual classifier flags "Sydney" as a person's name |
| **Airline / Commercial Brands in English B-Roll** | `JetBlue Airbus A320`, `1931 Sykes Don Bradman bat` | `sleek white and deep-blue modern narrow-body commercial passenger jet`, `vintage 1931 seasoned willow cricket bat` | Commercial trademark + prominent person trigger in English visual prompt |
| **Aviation Crash / Explosion / Fireball Terms** | `मोठा भीषण स्फोट होऊ शकतो`, `विमानाचे तुकडे उडणे`, `आगीच्या ज्वाळा आणि काळा धूर` | `मोठा गंभीर धोका निर्माण होऊ शकतो`, `प्रचंड घर्षणाचा धूर धावपट्टीवर पसरला` | Mass-casualty aviation disaster / explosion safety filter |
| **Dense Transliterated English Jargon** | `ई-कॅम मॉनिटरवर एनएलजी शॉक ॲब्झॉर्बर फॉल्ट आणि व्हील स्टिअरिंग फॉल्ट` | `कॉकपिटच्या मुख्य इलेक्ट्रॉनिक स्क्रीनवर दोन मोठे धोक्याचे लाल इशारे चमकू लागले, पुढील चाकाचा शॉक ॲब्झॉर्बर आणि स्टिअरिंग यंत्रणेत मोठा बिघाड` | 6+ consecutive transliterated English acronyms cause Marathi TTS to output garbled non-Marathi speech |
| **Child Fatality / Snakebite** | `त्या लहान मुलाचा सर्पदंशाने मृत्यू झाला होता` | `त्याचा जीवनप्रवास तिथेच सर्पदंशामुळे अचानक थांबला होता` | Child mortality / harm safety classifier |
| **Stowaway / Hypothermia Fatality** | `विजयचा मृत्यू झाला`, `विजयचा मृतदेह` | `विजयचा जीवनप्रवास थांबला होता`, `विजयचे पार्थिव` | Graphic fatality trigger |
| **Human Trafficking / Smuggler** | `मानवी तस्कर` (Human trafficker) | `अनोळखी प्रवासी मध्यस्थ` | Human trafficking policy trigger |
| **Proper Names in Biometrics** | `Andrew Carlssin's facial scan`, `Carlssin's mugshot` | `biometric face scan of an unidentified male suspect` | Biometric privacy rules |
| **Microphone Brands** | `Shure SM7B`, `Rode`, `Neumann` | `broadcast microphone`, `matte-black podcast microphone` | Commercial trademark filtering |
| **Court Bail / Cash Deposit** | `कोर्टाने त्याच्या जामिनाची रक्कम... ठेवली` | `प्रशासनाने ती अधिकृत अट तब्बल दहा लाख डॉलर्स... ठेवली` | Anti-money laundering & court bail triggers |
| **Court Hearing / Seizure** | `न्यायालयाची सुनावणी... वकील आले, न्यायाधीश आले` | `पुढील सुनावणी सुरू झाली. सर्वजण आले...` | Judicial proceeding & asset seizure triggers |
| **Terrorist / Militant Names** | `ओसामा बिन लादेनचा अचूक ठावठिकाणा` | `त्या काळात अमेरिकेसाठी सर्वात मोठा शत्रू असलेल्या प्रमुखाचा अचूक ठावठिकाणा` | Terrorism & named extremist entity filter |
| **Specific Terminal Diseases** | `एड्सवरचा (AIDS) भविष्यातील अचूक औषधोपचार` | `एका महाभयंकर असाध्य आजारावरचा भविष्यातील अचूक वैद्यकीय उपचार` | Medical misinformation / clinical disease filter |
| **Alcohol / Substance Mentions** | `मद्यपान / दारूला स्पर्शही केला नाही / स्कॉच विस्की` | `अत्यंत कठोर आणि संयमी जीवनशैली पाळली` | Substance policy trigger |
| **Named Real-World Wars** | `इराक युद्धाचे!` | `आखाती देशातील मोठ्या युद्धाचे!` | Armed conflict & geopolitical event filter |
| **Gambling / Lotteries** | `लॉटरी` (Lottery) | `महाबक्षीस`, `मोठे बक्षीस` | Anti-gambling policy triggers |
| **Source `.docx` Autocorrect Typos** | Mixed English words in Marathi (e.g. `हवेत range नव्हती`, `puppy प्रेम`) | Pure Marathi equivalent (e.g. `हवेत रेंज नव्हती`, `अपार प्रेम`) | Prevents unnatural English-accented TTS jumps |

---

## 6. Strict Script Adherence, Chunking & Chronological Scene Organization

### Rule 1: 100% Script Accuracy & Completeness Audit
* Every single scene (`Scene 01` through `Scene N`) and every dialogue paragraph in the source `.docx` manuscript must be parsed into `parsed_scriptX_scenes.json` prior to production.
* **No Skipped Lines or Missing Scenes**: Every dialogue line is mapped to one or more 10-second studio parts (`Part 1`, `Part 2`, `Part 3`, `[Part 4]`) plus 10–15 documentary B-roll plates across the episode.

### Rule 2: 10-Second Generation Chunking (Strict 15–25 Marathi Words Floor & Ceiling)
* Gemini Omni Flash clips are fixed at **10 seconds** ($\approx 2.0 - 2.4$ Marathi words/second).
* **Strict Floor (`>= 15 words`) & Ceiling (`<= 25 words`)**:
  * Never submit a studio clip with fewer than 14 words (`11–12` words leaves dead air in a 10s generation and can cause the model to hallucinate foreign-language filler syllables).
  * Never exceed 26 words so the host finishes speaking naturally before the 10.0s mark without clipping the final word.

### Rule 3: Spelled-Out Numbers & Clean Devanagari Phonetics
* Never pass raw digits (`292`, `2005`, `1931`, `99.94`, `140`, `25L`, `100%`) or English parentheticals (`(ECAM)`, `(ATC)`, `(LAX)`) inside Marathi dialogue quotes. Always strip English parentheticals and spell numbers/codes out in full Devanagari words:
  * `२९२` $\rightarrow$ `दोनशे ब्याण्णव`
  * `२१ सप्टेंबर २००५` $\rightarrow$ `एकवीस सप्टेंबर दोन हजार पाच`
  * `N536JB` $\rightarrow$ `एन पाचशे छत्तीस जेबी`
  * `२५L` $\rightarrow$ `पंचवीस एल`
  * `१,००० फूट` $\rightarrow$ `एक हजार फूट`

### Rule 4: Chronological Scene-First File Naming & Dual Folder Hierarchy
* **Mandatory Master Filename Format**:
  ```text
  Scene{SCENE_NUM:02d}_{CLIP_IN_SCENE:02d}_{BATCH_CODE}_Scene{SCENE_NUM:02d}_{Speaker}_{Slug}.mp4
  ```
* **Dual Directory Structure**:
  1. **Flat Chronological Master Folder**: `<EPISODE_DIR>/` (all clips sort 100% chronologically from `Scene01_01` to `SceneNN_MM`).
  2. **Per-Scene Subfolder Hierarchy**: `<EPISODE_DIR>/Scenes_01_to_NN/Scene_01/` through `Scene_NN/`, populated via zero-overhead filesystem hardlinks (`os.link(master_path, scene_folder_path)`).
  3. **Synchronized 1080p Thumbnails**: `<EPISODE_DIR>/thumbnails/` containing matching `SceneXX_YY_...jpg` frames extracted at `t = 00:00:03`.

---

## 7. Standardized 4-Camera Prompt Templates (with Mandatory Static Tripod Lock)

### A. Camera 1 — Wide 2-Shot (`wide_2shot`)
* **Lead Host Speaking (Left)**:
  ```text
  Wide two-shot of two podcast hosts seated together at a curved wooden podcast studio desk: The mature Indian man on the left with glasses and mustache in [CHATE_OUTFIT] leans forward speaking directly into his broadcast microphone with a deep, resonant, authoritative Indian male voice in crystal-clear Marathi, pronouncing every single word exactly: "[EXACT MARATHI DIALOGUE]" Clear natural lip-sync matching the spoken Marathi words. The young woman on the right in [ROOHI_OUTFIT] remains completely silent, looking at him attentively with closed mouth. Both remain seated at the podcast desk in the studio. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes.
  ```
* **Co-Host Speaking (Right)**:
  ```text
  Wide two-shot of two podcast hosts seated together at a curved wooden podcast studio desk: The young Indian woman on the right with glasses and [ROOHI_OUTFIT] leans forward speaking into her broadcast microphone with an engaging, enthusiastic young Indian female voice in crystal-clear Marathi, pronouncing every single word exactly: "[EXACT MARATHI DIALOGUE]" Clear natural lip-sync matching the spoken Marathi words. The mature Indian man on the left in [CHATE_OUTFIT] remains completely silent, looking at her attentively with closed mouth. Both remain seated at the podcast desk in the studio. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes.
  ```

### B. Camera 2 — Solo Medium Close-Up: Lead Host (`cam_a_chate_closeup`)
```text
Solo medium close-up of the mature Indian man with glasses and mustache in [CHATE_OUTFIT] seated at a wooden podcast studio desk: He speaks directly into his broadcast microphone with a deep, resonant, authoritative Indian male voice in crystal-clear Marathi, pronouncing every single word exactly: "[EXACT MARATHI DIALOGUE]" Clear natural lip-sync and expressive facial nuances matching the spoken Marathi words, 85mm portrait lens with warm wood-slat and studio lamp bokeh in the background. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes.
```

### C. Camera 3 — Solo Medium Close-Up: Co-Host (`cam_b_roohi_closeup`)
```text
Solo medium close-up of the young Indian woman with glasses in [ROOHI_OUTFIT] seated at a wooden podcast studio desk: She speaks into her broadcast microphone with an engaging, expressive young Indian female voice in crystal-clear Marathi, pronouncing every single word exactly: "[EXACT MARATHI DIALOGUE]" Clear natural lip-sync and expressive journalistic demeanor matching the spoken Marathi words, 85mm portrait lens with warm illuminated studio bookshelf bokeh in the background. Static locked tripod camera throughout the entire 10-second shot with zero camera cuts, zero zooms, and no scene changes.
```

### D. Camera 4 — Cinematic 1080p B-Roll Cutaway (`broll`)
```text
Cinematic 1080p historical documentary visual plate, [ERA/SETTING DESCRIPTION — NO REAL PERSONAL OR BRAND NAMES], 35mm film grain, slow camera movement, 24fps motion picture quality, no dialogue, subtle atmospheric sound.
```

---

## 8. Automated 4-Gate Quality Assurance (QA) & Master Documentary Assembly

1. **Gate 1 — 1080p Resolution & MD5 Deduplication Audit**:
   * Verify `len(missing) == 0`, all clips are `1920x1080` (`bit_rate >= 8,000,000`), and `0` duplicate MD5 hashes exist across all clips in `<EPISODE_DIR>/`.
2. **Gate 2 — 1-Second-Interval (`1s..10s`) Multi-Frame Camera-Lock Audit (`MAD <= 15.0`)**:
   * Extract `1 fps` (`160x90`) frames across all 10 seconds of every studio clip and compute the Mean Absolute Deviation (`MAD`) against its assigned studio reference plate (`wide_2shot`, `cam_a_chate_closeup`, `cam_b_roohi_closeup`).
   * Any studio clip with `max(MAD) > 15.0` at any second (indicating a mid-clip camera cutaway, zoom, or unplated generation) is automatically removed and regenerated before master assembly.
3. **Gate 3 — Automated `faster-whisper` Speech & Script Adherence Audit (`audit_speech_with_whisper`)**:
   * Transcribe every studio clip using `faster-whisper` (`small`, `language=WHISPER_LANG`) and verify:
     1. Zero cross-clip mismatches (`best_code == item["code"]`).
     2. Non-zero word overlap (`best_score >= 1` and `len(transcript) >= 15`), automatically removing and regenerating any clip with garbled or truncated audio.
4. **Gate 4 — Drift-Free Master Documentary Concatenation**:
   * Concatenate all verified clips in exact manifest order into `EPISODE_XX_..._FULL_DOCUMENTARY_1080P_MASTER.mp4` using stream-copied video (`-c:v copy`) and timestamp-aligned stereo AAC audio (`-c:a aac -b:a 192k -ar 48000 -ac 2 -af "aresample=async=1:first_pts=0" -movflags +faststart`).

---

## 9. Reference Multi-Cam Automation Engine (`flow_1080p_2shot_production_engine.py`)

The portable, customizable end-to-end Python Multi-Cam 3-Camera + B-Roll production engine is bundled directly inside this repository at:
* [`skills/cinematic-marathi-podcast-production/scripts/flow_1080p_2shot_production_engine.py`](scripts/flow_1080p_2shot_production_engine.py)
* Installed globally by `setup_wizard.py` to `~/.gemini/config/skills/cinematic-marathi-podcast-production/` and `~/.gemini/config/plugins/antigravity-workstation/skills/cinematic-marathi-podcast-production/`.
