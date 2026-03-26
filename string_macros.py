#!/usr/bin/env python3
"""
STRING MACROS - FEATURE LIST
===========================================================================

  Current version: v3.18.59
  File ratio (default 12): 2 Raw - 3 Inef - 7 Normal  (2:3:7)
  Time-sensitive ratio:    6 Raw - 0 Inef - 6 Normal  (1:1)

===========================================================================
                    GROUP 1: PAUSE BREAKS
===========================================================================

1. WITHIN-FILE PAUSES
   Files: Normal + Inef (Raw = 0%)
   Value: random % drawn fresh per file (decimal, never rounded):
     Normal: rng.uniform(2%, 5%)  e.g. 2.14%, 3.87%
     Inef:   rng.uniform(10%, 15%)  e.g. 11.6%, 13.2%
   e.g. 20s Normal file at 3.4% -> 0.68s pause
   One pause per file in middle 80%. Skips drags, rapid-clicks, pre-DragStart.

2. PRE-PLAY BUFFER
   Files: ALL (including between cycles in the outer loop)
   Value: rng.uniform(500, 800) ms * mult — applied before every file and
   between every cycle boundary (end of cycle N -> start of cycle N+1).
   Between-cycle buffer was added in v3.18.45 to prevent 0ms gap between
   the last DragEnd of one cycle and the cursor transition of the next,
   which caused drag-click at wrong position.

3. INEF BEFORE-FILE PAUSE
   Files: Inef only, only if current cycle >= 25s
   Value: rng.uniform(10000, 30000) ms flat (no mult)
   Added between each full cycle (F1->...->FN loop).
   Cursor drifts during this pause toward next file start position.

4. INEFFICIENT MASSIVE PAUSE
   Files: Inef only
   Value: rng.uniform(240000, 420000) ms flat (no mult) = 4-7 min
   One pause inserted at a safe random point after all cycles complete.
   Loop pre-samples pause so total file stays near target duration.
   Safe: no drag, no rapid-click, not pre-DragStart, not first/last 10%.

5. MULTIPLIER SYSTEM
   Continuous random range, 4 decimal places (never rounded):
     Raw:    rng.uniform(1.1, 1.2)  e.g. 1.13, 1.17
     Normal: rng.uniform(1.5, 1.7)  e.g. 1.53, 1.67
     Inef:   rng.uniform(2.0, 3.0)  e.g. 2.14, 2.87
   Multiplied (baked in at generation time):
     - Pre-play buffer: rng.uniform(500, 800) * mult
     - Cursor transition: rng.uniform(200, 400) * mult
     - Within-file % pause: file_duration * pct (pct not multiplied; the pause
       duration grows with larger files naturally)
     - Mid-event random pause (50% chance/cycle): rng.uniform(200, 800) * mult
   NOT multiplied (flat): inef before-file pause, massive pause, distraction files

===========================================================================
                    GROUP 2: PATTERN BREAKING
===========================================================================

6. CURSOR TRANSITION TO START POINT
   Files: ALL (SKIPPED for click-sensitive)
   Value: rng.uniform(200, 400) ms * mult — human path between files.
   Skipped entirely for click-sensitive folders.

7. IDLE CURSOR WANDERING
   Files: ALL (SKIPPED for click-sensitive)
   Fills existing recording gaps > 2000ms with cursor arcs/drifts.
   Does NOT add time — movements fit inside the existing gap.
   Not shown in manifest (zero time impact on total).

8. MOUSE JITTER
   Files: ALL (SKIPPED for click-sensitive)
   Value: 9-21% of mouse moves get +/-1-3px random offsets.
   Excluded near drags, rapid-click sequences, first/last 10% of file.

9. VIRTUAL QUEUE - SUBFOLDER FILES
   Each subfolder has its own shuffled queue. No file repeats until all
   others used. Boundary guard prevents same file at queue wrap.
   Same mechanism applies to distraction files (Feature 32).

===========================================================================
                    GROUP 3: SMOOTH OPERATION
===========================================================================

10. RAPID CLICK PROTECTION
    3+ clicks within 1500ms detected. Jitter exclusion extended to 1500ms.

11. DRAG OPERATION PROTECTION
    Hold+Move+Release detected. No jitter during entire drag sequence.

12. EVENT TIMING INTEGRITY
    No modifications inside drags, pre-DragStart, rapid-clicks, or first/
    last 10%. Prevents click-hold clamping (unintended long drags).

13. COMBINATION HISTORY
    Tracks used file combos per subfolder across cycles.
    Avoids repeating same combination. Persists via uploaded .txt files.

14. MANUAL HISTORY UPLOAD
    Upload COMBINATION_HISTORY_XX.txt to input_macros/combination_history/
    All .txt files read; those combos avoided in future runs.

15. ALPHABETICAL FILE NAMING
    Raw: ^XX_A  Inef: XX_C (not-sign prefix)  Normal: XX_E (no prefix)
    Output folder: (bundle_id) folder_name

16. FOLDER-NUMBER STRUCTURE
    F1, F2, F3.5 etc. F<N> prefix preferred; other numbers in name ignored.
    e.g. "F3- press 1 to bank" -> num=3, the "1" in name is ignored.

17. OPTIONAL TAG
    Default chance: rng.uniform(24%, 33%) per bundle (decimal, never rounded).
    Custom number: used as CENTRE of +/-2% random range (never rounded).
      e.g. "optional23" -> rng.uniform(21%, 25%)
           "optional50" -> rng.uniform(48%, 52%)
           "optional50.5" -> rng.uniform(48.5%, 52.5%)
    This adds variety so the same folder never hits the exact same threshold.
    Range clamped so it never goes below 1% or above 99%.
    Max-files/loops: "optional58-6-" = 58% centre, pick 1-6 files/loops.
    No optional: "F1-4-" = always included, pick 1-4 files.
    always_first/last wraps the entire picked group once (not per file).
    For nested folders: -N- means max N complete sub-cycles (loops), not files.

18. END TAG
    Uses word-boundary match (end) — "tend" does NOT match.
    Loop stops after this folder. Always included if reached.

19. OPTIONAL+END COMBO TAG
    Chosen = loop stops here. Skipped = loop continues.
    Renamed from "optional/end" in v3.18.42.

20. TIME SENSITIVE TAG
    Ratio: 1:1 (half raw, half normal, zero inef).
    Main folder tag propagates to ALL subfolders.

21. CLICK SENSITIVE TAG
    Disables ALL coordinate-changing features:
    cursor path, mouse jitter, idle wandering, distraction insertion.
    Main folder tag propagates to ALL subfolders.
    Accepted: "click sensitive" / "click/time sensitive" / "click+time sensitive"

22. CLICK/TIME SENSITIVE COMBO TAG
    Both tag rules active: 1:1 ratio + no cursor/jitter/idle/distraction.

23. DONT USE FEATURES ON ME TAG
    Exact folder name (case-insensitive). Files inserted completely unmodified.
    Marked [UNMODIFIED] in manifest.

24. ALWAYS FIRST / LAST FILES
    Tag in FILENAME (not folder name). Three modes:
    A) Root-level (next to F1/F2/F3 subfolders): fires ONCE per strung file,
       before all cycles start and after all cycles end.
    B) Inside a specific subfolder (e.g. F0): wraps ONLY that subfolder's files.
       Pattern: [AF] -> F0 files -> [AL] -> F1 -> F2 -> ...
    C) Flat/single-subfolder folder: fires ONCE at very start and very end.
    For nested folders (Feature 39): AF/AL wrap all loops together, not per loop.

25. COMPREHENSIVE MANIFEST
    !_MANIFEST_XX_!.txt in output folder. Shows per-version:
    - File type, multiplier, total pause added
    - Breakdown (x = mult applied, - = flat): PRE-Play Buffer, Within File Pauses,
      CURSOR to Start Point, POST-SNAP GAP, DISTRACTION File Pause,
      INEFFICIENT Before File Pause, INEFFICIENT MASSIVE PAUSE
    - Full file list with cumulative end times

26. SPECIFIC FOLDERS FILTERING
    --specific-folders <file>: process only folders (and optionally subfolders)
    listed in the file. Matching is case-insensitive, whitespace-stripped.

    File format (one entry per line):
      FolderName                   -> include folder, ALL its subfolders
      FolderName: F1, F3, F4       -> include folder, ONLY subfolders F1 F3 F4
      FolderName: F1, F3-F5        -> include folder, F1 and range F3 through F5

    Examples:
      22- Craft Dia- edge- lamp bank Z- S
      22- Craft Dia- edge- lamp bank Z- S: F1, F2, F4
      58- Smth R2H only: F1-F3

    - Subfolder numbers are case-insensitive (F1 = f1 = 1)
    - Decimal subfolders supported: F3.5
    - If a requested subfolder doesn't exist, it is skipped with a warning
    - Output folder: (bundle_id) folder_name

27. CHAT INSERTS
    --no-chat disables. One chat file spliced into one non-raw version
    per folder batch at a random point in the middle third.

28. PRE-PLAY BUFFER GUARANTEE
    files_added int counter (not list truthiness) ensures buffer fires before
    every file including always_first/last. Avoids Python nonlocal edge case.

29. FAIL-FAST ERROR HANDLING
    Fatal errors call sys.exit(1) so GitHub Actions fails at the right step.

30. FLAT FOLDER SUPPORT
    JSON files directly in main folder (no numbered subfolders) = single pool.
    All tags (always_first/last, time_sensitive, click_sensitive) still work.

31. DISTRACTION FILE GENERATION + INSERTION
    Trigger: DISTRACTIONS/ folder in input_macros/
    Generates 50 temp files (30s-2min), each using 3 of 6 features:
    wander, pause, right-click, typing, key-spam, shapes.
    Chance: Normal 3.5-5%, Inef 3.5-7%, Raw 0%, Click-sensitive 0%.
    NOT multiplied — flat pre-built durations. Shown in manifest.

32. VIRTUAL QUEUE - DISTRACTION FILES
    All 50 distraction files rotate before any repeat.
    Boundary guard prevents consecutive repeat at queue wrap.

33. 2:3:7 FILE RATIO DISTRIBUTION
    raw=round(v x 2/12), inef=round(v x 3/12), normal=remainder.
    12->2:3:7, 24->4:6:14, 20->3:5:12.
    Time-sensitive override: 1:1 raw:normal, zero inef.

34. FILE TRANSITION START GAP PROTECTION
    80-150ms gap (POST-SNAP GAP) between snap MouseMove and first event of
    next file. Prevents zero-gap DragStart = cursor clamp at transition.
    Tracked in manifest as flat (no mult).

35. INTRA-FILE ZERO-GAP PROTECTION
    On load: MouseMove->DragStart/Click gap < 15ms shifted to 20ms.
    Prevents recording-tool artifacts causing button clamp.
    Applied before any other features, to raw events only.

36. ORIGINAL FILES DEDUPLICATION
    Counts each unique filename once across all subfolders.
    Copied subfolders shown as "(N copied folder(s))" in manifest.

37. MAX-FILES TAG
    "-N-" in folder name = pick 1-N files (or loops for nested folders).
    "F3 optional58-6-" = 58% chance, 1-6 files.
    "F1-4-" = always included, 1-4 files.

38. PROBLEMATIC KEY FILTERING
    On load (before any features): strips keys that break macro playback.
    Filtered: HOME(36), END(35), PAGE_UP(33), PAGE_DOWN(34), PAUSE(19),
              PRINT_SCREEN(44)
    Kept: ESC(27) — valid in-game action (closing menus, cancelling dialogs).
    IMPORTANT: base_time captured BEFORE filtering so files whose only early
    event is a filtered key (e.g. END at t=90ms) keep their full duration.
    Without this, the 90ms anchor is lost and the file collapses to near-zero.

39. NESTED SUBFOLDER SUPPORT
    A numbered subfolder (e.g. F5) can contain its own F1/F2/F3/F4 instead
    of direct JSON files. Detected automatically during scanning.
    -N- on the outer folder = max N complete inner loops (not N files).
    always_first/last at F5's root level fire ONCE before all loops and
    ONCE after all loops (not per loop).
    Internal subfolders support all tags: optional, end, time/click sensitive.
    Separate ManualHistoryTracker maintained for nested folder's combos.

===========================================================================

CHANGELOG (recent):
- v3.18.46: ESC key (KeyCode 27) removed from filter_problematic_keys.
            ESC was being stripped from every source file on load because macro
            players use ESC to stop playback. However ESC is also a valid in-game
            action (e.g. closing menus, cancelling dialogs) and must be preserved.
            Remaining filtered keys: HOME(36), END(35), PAGE_UP(33), PAGE_DOWN(34),
            PAUSE(19), PRINT_SCREEN(44) — these have no in-game use and reliably
            break or freeze macro playback.
- v3.18.45: Pre-play buffer now also fires between cycles (all file types).
            ROOT CAUSE of click-through bug: add_file_to_cycle fires a 500-800ms
            buffer between files WITHIN a cycle (when files_added > 0). But at
            the boundary between cycle N and cycle N+1, files_added resets to 0
            for the first file of the new cycle — no buffer fires. This left the
            last DragEnd of cycle N and the cursor transition start of cycle N+1
            at the exact same timestamp (0ms gap). The game reads simultaneous
            DragEnd + MouseMove as cursor still held -> drag-click at wrong coords.
            Fix: in the outer loop, if stringed_events is non-empty (not first cycle),
            add a rng.uniform(500,800)ms gap to inter_cycle_pause for ALL file types
            before appending the next cycle. Tracked in total_pre_file.
- v3.18.44: Flat/single-subfolder always_first/last now wraps whole strung file.
            Previously string_cycle played always_first/last on EVERY cycle call,
            so a 50-cycle file had 50x [ALWAYS FIRST]...[ALWAYS LAST] pairs.
            Fix: outer loop passes play_always_first=True only on cycle 0, and
            suppresses play_always_last entirely. After the while loop, always_last
            is injected once directly into stringed_events with a pre-play buffer.
            Result: [ALWAYS FIRST] -> file_1 -> file_2 -> ... -> file_N -> [ALWAYS LAST]
- v3.18.43: CRITICAL — end tag now uses word-boundary matching.
            BUG: 'end' in folder_name was a substring check. Any folder name
            containing a word with "end" in it (e.g. "click tend", "blend",
            "extended") was being tagged as an END folder, causing the loop to
            stop there and skip all subsequent folders.
            Example: "F4- use log on fire OR click tend" matched because
            "t-END" contains "end" -> loop stopped at F4, F5 and F6 ignored.
            FIX: changed to re.search(r'\bend\b', ...) — whole-word match only.
            "tend" no longer matches. "end", "end-logout", "optional+end" still do.
- v3.18.42: Two fixes:
            1. optional+end tag renamed from "optional/end" everywhere in docs,
               comments, print output, and manifest. Tag detection unchanged
               (still looks for both "optional" AND "end" in folder name).
            2. All combination.append() calls now consistently wrap the file in
               a list [_f] — the optional+end branch, end branch, and fallback
               path were appending raw Path objects. string_cycle has an
               isinstance guard that handled it safely, but this makes the
               contract explicit and removes the inconsistency.
- v3.18.41: always_first/last in multi-subfolder mode now wraps ONLY the files
            of their own folder, then continues to remaining folders.
            Pattern: [ALWAYS FIRST] -> F0 files -> [ALWAYS LAST] -> F1 -> F2 -> ...
            Previously wrapped the entire cycle (all folders). Also fixed file
            corruption from emoji-stripping pass (ohno_pause variable, prefix docs).
- v3.18.39: click sensitive main-folder tag now propagates to all subfolders
- v3.18.38: click sensitive also skips distraction file insertion
- v3.18.37: click sensitive fully implemented (jitter + idle + transitions all skipped)
- v3.18.36: inef massive pause pre-sampled so total file stays near target duration
- v3.18.35: safety file-count limit raised 150->2000 (was cutting files short)
- v3.18.34: subfolder number extraction prefers F<N> prefix; optional-chance
            regex excludes dashes so -2- max-files marker not read as 2%
- v3.18.33: always_first/last wraps once per cycle; bundle ID moved to prefix;
            dedup by filename globally; subfolder counts in manifest
- v3.18.32: time-sensitive 1:1 ratio; click-sensitive tag; max-files tag;
            copied folder dedup; subfolder counts
- v3.18.31: virtual queue for all subfolder files; post-pause delay deleted;
            distraction in manifest; massive pause 4-7 min; within-file %
- v3.18.30: intra-file zero-gap protection (Feature 35)
- v3.18.29: virtual queue for distraction files; 2:3:7 ratio distribution
"""

import argparse, json, random, re, sys, os, math, shutil, itertools
from pathlib import Path

VERSION = "v3.18.65"

# ============================================================================
# FEATURE DOCUMENTATION - ORGANIZED BY PURPOSE
# ============================================================================

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_ms_precise(ms):
    """Format milliseconds as Xm Ys"""
    total_sec = int(ms / 1000)
    minutes = total_sec // 60
    seconds = total_sec % 60
    return f"{minutes}m {seconds}s"

def get_file_duration_ms(filepath):
    """Get file duration in milliseconds"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            events = json.load(f)
        if not events:
            return 0
        times = [e.get('Time', 0) for e in events]
        return max(times) - min(times)
    except:
        return 0

def filter_problematic_keys(events: list) -> list:
    """
    CRITICAL: Filter out keys that could stop macro playback.
    Removes: HOME(36), END(35), PAGE_UP(33), PAGE_DOWN(34), PAUSE(19), PRINT_SCREEN(44)
    NOTE: ESC(27) kept - it is a valid in-game key (e.g. closing menus).
    """
    problematic_codes = {19, 33, 34, 35, 36, 44}  # ESC(27) removed - valid in-game action
    filtered = []
    
    for event in events:
        keycode = event.get('KeyCode')
        if keycode in problematic_codes:
            continue
        filtered.append(event)
    
    return filtered

def parse_optional_chance(folder_name: str) -> float:
    """
    Parse the inclusion probability from an 'optional'-tagged folder name.

    Rules:
      - No number after 'optional'  -> random default 24.0-33.0% (float)
      - Number found (integer OR decimal) -> used as centre of +/-2% random range.
        e.g. optional23 -> rng.uniform(21.0, 25.0)%
        This adds variety so the same folder doesn't always hit the exact same
        threshold. Range is clamped so it never goes below 1% or above 99%.

    Accepted formats (all case-insensitive):
      "3 optional- bank/"           -> random 0.24-0.33
      "3 optional50- bank/"         -> random 0.48-0.52
      "3 optional50.5- bank/"       -> random 0.485-0.525
      "3 optional23-4- booth/"      -> random 0.21-0.25
      "3 optional33.3+end- logout/" -> random 0.313-0.353

    Returns a float in (0, 1).
    """
    import re
    # Capture integer OR decimal number after 'optional' (e.g. 50, 50.5, 33.3)
    match = re.search(r'optional[^-\d]*?(\d+(?:\.\d+)?)', folder_name, re.IGNORECASE)
    if match:
        centre = float(match.group(1))
        lo = max(1.0, centre - 2.0)
        hi = min(99.0, centre + 2.0)
        return random.uniform(lo, hi) / 100.0
    # No number -> default random range (float, never rounded)
    return random.uniform(0.24, 0.33)


def parse_max_files(folder_name: str) -> int:
    """
    Parse max-files count from folder name.
    Formats (case-insensitive, all combinations):
      "F3 optional58-6-"  -> max 6  (58% chance)
      "F3 optional-6-"    -> max 6  (default chance)
      "F1-4-"             -> max 4  (always included)
      "F3 optional58-"    -> max 1  (no max-files number = default 1)
      "F1- mine rock/"    -> max 1  (no number = default 1)

    The max-files number is the LAST standalone integer before a trailing dash,
    not the folder number or the optional-chance percentage.
    Returns int >= 1.
    """
    import re
    # Pattern: dash, then digits (the max-files count), then dash or end
    # We look for a bare integer surrounded by dashes that isn't the folder number
    # (folder number is at the very start) and isn't the optional-chance percentage
    # (which directly follows "optional").
    # Strategy: strip the leading folder number, strip optional-chance, then find
    # a remaining -N- or -N/ pattern.
    name = folder_name.strip('/').strip()
    # Remove folder number prefix (e.g. "3", "3.5", "F3")
    name = re.sub(r'^[Ff]?\d+(?:\.\d+)?\s*', '', name)
    # Remove optional-chance number (digits immediately after "optional")
    name = re.sub(r'optional\s*\d+(?:\.\d+)?', 'optional', name, flags=re.IGNORECASE)
    # Now look for -N- or -N/ or -N at end where N is 2-3 digits (1 digit would be ambiguous)
    # Actually look for any -digits- pattern remaining
    matches = re.findall(r'-(\d+)-', name)
    if matches:
        try:
            return max(1, int(matches[-1]))   # take the last one
        except ValueError:
            pass
    return 1   # default: 1 file


def fix_click_events(events: list) -> list:
    """
    Convert 'Click' events to LeftDown+LeftUp pairs.
    This prevents the mouse from clamping down and dragging.
    
    CRITICAL FIX from merge_macros.py!
    """
    fixed = []
    for event in events:
        if event.get('Type') == 'Click':
            # Replace Click with LeftDown + LeftUp pair
            time = event.get('Time', 0)
            x = event.get('X')
            y = event.get('Y')
            
            # LeftDown at same time
            left_down = {
                'Type': 'LeftDown',
                'Time': time,
            }
            if x is not None:
                left_down['X'] = x
            if y is not None:
                left_down['Y'] = y
            
            # LeftUp 10-20ms later (small random delay)
            left_up = {
                'Type': 'LeftUp',
                'Time': time + random.randint(10, 20),
            }
            if x is not None:
                left_up['X'] = x
            if y is not None:
                left_up['Y'] = y
            
            fixed.append(left_down)
            fixed.append(left_up)
        else:
            # Keep all other events as-is
            fixed.append(event)
    
    return fixed

def generate_human_path(start_x, start_y, end_x, end_y, duration_ms, rng):
    """
    Generate a human-like mouse path with variable speed, path styles, and wobbles.
    
    Path Styles:
    - Efficient: Direct path, few curves, faster
    - Meandering: Curved path, more wandering, varied speed
    - Hesitant: Slow start, acceleration, deceleration
    - Swift: Fast throughout, minimal curves
    
    Speed Variations:
    - Very fast: 100-200ms typical
    - Fast: 200-300ms typical
    - Normal: 300-500ms typical
    - Slow: 500-700ms typical
    - Very slow: 700-1000ms typical
    
    Returns: List of (time_ms, x, y) tuples.
    """
    if duration_ms < 100:
        return [(0, end_x, end_y)]
    
    path = []
    dx = end_x - start_x
    dy = end_y - start_y
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance < 5:
        return [(0, end_x, end_y)]
    
    # Choose path style (determines curvature and speed pattern)
    path_style = rng.choice(['efficient', 'meandering', 'hesitant', 'swift'])
    
    # Determine num_steps based on distance and path style
    if path_style == 'efficient':
        # Direct, fewer steps
        num_steps = max(3, min(int(distance / 20), int(duration_ms / 60)))
    elif path_style == 'swift':
        # Very fast, few steps
        num_steps = max(2, min(int(distance / 25), int(duration_ms / 80)))
    elif path_style == 'meandering':
        # More steps for smoother curves
        num_steps = max(5, min(int(distance / 10), int(duration_ms / 40)))
    else:  # hesitant
        # Medium steps
        num_steps = max(4, min(int(distance / 15), int(duration_ms / 50)))
    
    # Add control points based on path style
    if path_style == 'efficient':
        # Few or no control points (straighter path)
        num_control = rng.choice([0, 1])
        offset_range = 0.15  # Less curve
    elif path_style == 'swift':
        # No control points (direct)
        num_control = 0
        offset_range = 0.0
    elif path_style == 'meandering':
        # More control points (curvier path)
        num_control = rng.randint(2, 4)
        offset_range = 0.4  # More curve
    else:  # hesitant
        # Medium control points
        num_control = rng.randint(1, 2)
        offset_range = 0.25
    
    control_points = []
    for _ in range(num_control):
        offset = rng.uniform(-offset_range, offset_range) * distance
        t = rng.uniform(0.2, 0.8)
        ctrl_x = start_x + dx * t + (-dy / (distance + 1)) * offset
        ctrl_y = start_y + dy * t + (dx / (distance + 1)) * offset
        control_points.append((ctrl_x, ctrl_y, t))
    
    control_points.sort(key=lambda p: p[2])
    current_time = 0
    
    for step in range(num_steps + 1):
        t_raw = step / num_steps
        
        # Apply speed profile based on path style
        if path_style == 'efficient':
            # Smooth acceleration
            t = 1 - (1 - t_raw) ** 1.8
        elif path_style == 'swift':
            # Linear (constant speed)
            t = t_raw
        elif path_style == 'meandering':
            # Variable speed with slight deceleration at end
            t = 0.5 * (1 - math.cos(t_raw * math.pi))
        else:  # hesitant
            # Slow start, fast middle, slow end
            t = 0.5 * (1 - math.cos(t_raw * math.pi))
        
        # Calculate position
        if not control_points:
            x = start_x + dx * t
            y = start_y + dy * t
        else:
            x, y = start_x, start_y
            for i, (ctrl_x, ctrl_y, ctrl_t) in enumerate(control_points):
                if t <= ctrl_t:
                    segment_t = t / ctrl_t if ctrl_t > 0 else 0
                    x = start_x + (ctrl_x - start_x) * segment_t
                    y = start_y + (ctrl_y - start_y) * segment_t
                    break
                else:
                    if i == len(control_points) - 1:
                        segment_t = (t - ctrl_t) / (1 - ctrl_t) if (1 - ctrl_t) > 0 else 0
                        x = ctrl_x + (end_x - ctrl_x) * segment_t
                        y = ctrl_y + (end_y - ctrl_y) * segment_t
                    else:
                        start_x, start_y = ctrl_x, ctrl_y
        
        # Add wobble (less for swift, more for meandering)
        if path_style == 'swift':
            wobble = rng.uniform(0, 2) if step > 0 and step < num_steps else 0
        elif path_style == 'meandering':
            wobble = rng.uniform(1, 7) if step > 0 and step < num_steps else 0
        else:
            wobble = rng.uniform(1, 5) if step > 0 and step < num_steps else 0
        
        x += rng.uniform(-wobble, wobble)
        y += rng.uniform(-wobble, wobble)
        
        # Bounds
        x = max(100, min(1800, int(x)))
        y = max(100, min(1000, int(y)))
        
        step_time = int(t * duration_ms)
        current_time = max(current_time, step_time)
        path.append((current_time, x, y))
    
    return path

# ============================================================================
# COMBINATION TRACKER
# ============================================================================


def is_in_drag_sequence(events, index, drag_indices=None):
    """
    Check if the given index is inside a drag sequence (between DragStart and DragEnd).
    Returns True if we're in the middle of a drag.

    If drag_indices (a precomputed set from build_drag_index_set) is provided,
    the check is O(1). Otherwise falls back to the original O(n) scan.
    """
    if drag_indices is not None:
        return index in drag_indices

    drag_started = False
    for j in range(index, -1, -1):
        event_type = events[j].get("Type", "")
        if event_type == "DragEnd":
            return False
        elif event_type == "DragStart":
            drag_started = True
            break
    
    if not drag_started:
        return False
    
    for j in range(index + 1, len(events)):
        event_type = events[j].get("Type", "")
        if event_type == "DragEnd":
            return True
        elif event_type == "DragStart":
            return False
    
    return False


def build_drag_index_set(events) -> set:
    """
    Return the set of all event indices that are inside a drag sequence.
    O(n) single pass - call this once, then use the result for O(1) lookups.
    """
    drag_indices = set()
    in_drag = False
    for i, e in enumerate(events):
        t = e.get("Type", "")
        if t == "DragStart":
            in_drag = True
        elif t == "DragEnd":
            in_drag = False
        if in_drag:
            drag_indices.add(i)
    return drag_indices

def detect_rapid_click_sequences(events):
    """
    Detect sequences of rapid clicks at similar coordinates.
    
    Detects:
    - Double clicks (2 clicks within 500ms, +/-5 pixels)
    - Spam clicks (3+ clicks within 2 seconds, +/-10 pixels)
    
    Returns list of protected ranges: [(start_idx, end_idx), ...]
    These ranges should NOT have pauses/gaps inserted between them.
    """
    if not events or len(events) < 2:
        return []
    
    protected_ranges = []
    
    i = 0
    while i < len(events):
        event = events[i]
        
        # Check Click and DragStart events (both are click actions)
        event_type = event.get("Type")
        if event_type not in ("Click", "DragStart"):
            i += 1
            continue
        
        # Found a click, look for nearby clicks
        click_sequence = [i]
        first_time = event.get("Time", 0)
        first_x = event.get("X")
        first_y = event.get("Y")
        
        if first_x is None or first_y is None:
            i += 1
            continue
        
        # Look ahead for more clicks
        j = i + 1
        while j < len(events):
            next_event = events[j]
            next_time = next_event.get("Time", 0)
            
            # Stop looking if too far in time (2 seconds max)
            if next_time - first_time > 2000:
                break
            
            # Check if it's a click or drag
            next_type = next_event.get("Type")
            if next_type in ("Click", "DragStart"):
                next_x = next_event.get("X")
                next_y = next_event.get("Y")
                
                if next_x is not None and next_y is not None:
                    # Calculate distance from first click
                    dist = ((next_x - first_x) ** 2 + (next_y - first_y) ** 2) ** 0.5
                    
                    # If within 10 pixels, part of sequence
                    if dist <= 10:
                        click_sequence.append(j)
            
            j += 1
        
        # If found 2+ clicks, protect the sequence
        if len(click_sequence) >= 2:
            start_idx = click_sequence[0]
            end_idx = click_sequence[-1]
            protected_ranges.append((start_idx, end_idx))
            i = end_idx + 1
        else:
            i += 1
    
    return protected_ranges


def is_in_protected_range(index, protected_ranges):
    """Check if an index is within any protected range."""
    for start, end in protected_ranges:
        if start <= index <= end:
            return True
    return False


def add_pre_click_jitter(events: list, rng: random.Random) -> tuple:
    """
    SMART JITTER SYSTEM v3.9.0
    
    Add realistic micro-movements to 9-21% of TOTAL file movements.
    CRITICAL: NO jitter within 1 second before/after ANY click!
    
    Rules:
    1. Jitter percentage: 9-21% of total MouseMove events
    2. Exclusion zone: 1000ms before AND after any click
    3. Only jitter MouseMove events (never Click, DragStart, RightDown, etc.)
    4. Jitter = 2-3 micro-movements (+/-1-3px) + final snap to exact position
    
    Returns (events_with_jitter, jitter_count, total_moves, jitter_percentage).
    """
    if not events or len(events) < 2:
        return events, 0, 0, 0.0
    
    # Step 1: Find ALL click times (any click-like event)
    click_types = {'Click', 'LeftDown', 'RightDown', 'DragStart'}
    click_times_sorted = sorted(
        event.get('Time', 0) for event in events if event.get('Type') in click_types
    )

    import bisect
    exclusion_ms = 1000

    # Step 2: Find all MouseMove events that are SAFE to jitter
    # Safe = NOT within 1000ms before/after ANY click  (O(n log c) total)
    safe_movements = []
    total_moves = 0

    for i, event in enumerate(events):
        if event.get('Type') == 'MouseMove':
            total_moves += 1
            event_time = event.get('Time', 0)

            # Binary search: nearest click before and after
            pos = bisect.bisect_left(click_times_sorted, event_time)
            is_safe = True
            # Check click just before
            if pos > 0 and event_time - click_times_sorted[pos - 1] <= exclusion_ms:
                is_safe = False
            # Check click at or after
            if is_safe and pos < len(click_times_sorted) and click_times_sorted[pos] - event_time <= exclusion_ms:
                is_safe = False

            if is_safe:
                safe_movements.append((i, event))
    
    # Step 3: Calculate how many jitters to add (9-21% of TOTAL movements)
    jitter_percentage = rng.uniform(0.09, 0.21)
    target_jitters = int(total_moves * jitter_percentage)
    
    # Can't jitter more than safe movements available
    target_jitters = min(target_jitters, len(safe_movements))
    
    if target_jitters == 0:
        return events, 0, total_moves, jitter_percentage
    
    # Step 4: Randomly select which safe movements get jitter
    movements_to_jitter = rng.sample(safe_movements, target_jitters)
    
    # Sort by index (descending) so we insert from end to start
    # This prevents index shifting issues
    movements_to_jitter.sort(key=lambda x: x[0], reverse=True)
    
    # Step 5: Add jitter to selected movements
    jitter_count = 0
    
    for idx, event in movements_to_jitter:
        move_x = event.get('X')
        move_y = event.get('Y')
        move_time = event.get('Time')
        
        if move_x is None or move_y is None or move_time is None:
            continue
        
        # Generate 2-3 micro-movements
        num_jitters = rng.randint(2, 3)
        jitter_events = []
        
        # Time budget: 100-200ms total
        time_budget = rng.randint(100, 200)
        time_per_jitter = time_budget // (num_jitters + 1)
        
        # Cap time_budget so jitter events never go before t=0
        if move_time - time_budget < 0:
            time_budget = max(0, int(move_time) - 1)
        if time_budget == 0:
            continue  # Not enough room before this event - skip jitter
        current_time = move_time - time_budget
        
        # Add jitter movements (+/-1-3 pixels)
        for j in range(num_jitters):
            offset_x = rng.randint(-3, 3)
            offset_y = rng.randint(-3, 3)
            
            jitter_x = int(move_x) + offset_x
            jitter_y = int(move_y) + offset_y
            
            # Bounds check
            jitter_x = max(100, min(1800, jitter_x))
            jitter_y = max(100, min(1000, jitter_y))
            
            jitter_events.append({
                'Type': 'MouseMove',
                'Time': current_time,
                'X': jitter_x,
                'Y': jitter_y
            })
            
            current_time += time_per_jitter
        
        # Final movement: snap to EXACT target position
        jitter_events.append({
            'Type': 'MouseMove',
            'Time': current_time,
            'X': int(move_x),
            'Y': int(move_y)
        })
        
        # Insert jitter events BEFORE the original movement
        for jitter_idx, jitter_event in enumerate(jitter_events):
            events.insert(idx + jitter_idx, jitter_event)
        
        jitter_count += 1
    
    return events, jitter_count, total_moves, jitter_percentage

def insert_intra_file_pauses(events: list, rng: random.Random,
                              protected_ranges: list = None,
                              file_type: str = 'normal') -> tuple:
    """
    Insert a single within-file pause whose duration is a percentage of the
    individual file's own play time:
      Raw:         0%  - no pause inserted
      Normal:      5%  - e.g. 20s file -> 1s pause somewhere safe
      Inefficient: 15% - e.g. 20s file -> 3s pause somewhere safe

    The pause is inserted at a single randomly chosen safe point (not in a drag
    sequence, not in a rapid-click sequence, not in the first or last 10%).
    Returns (events_with_pause, total_pause_time_ms).
    """
    if not events or len(events) < 5:
        return events, 0

    # Raw = 0%, Normal = random in [2%, 5%], Inef = random in [10%, 15%]
    # Drawn fresh each call — decimal, never rounded (e.g. 2.14%, 3.87%, 11.6%)
    if file_type == 'raw':
        return events, 0
    elif file_type == 'inef':
        pct = rng.uniform(0.10, 0.15)
    else:  # normal
        pct = rng.uniform(0.02, 0.05)

    if protected_ranges is None:
        protected_ranges = []

    file_duration_ms = events[-1].get('Time', 0) - events[0].get('Time', 0)
    if file_duration_ms <= 0:
        return events, 0

    # Float ms - no rounding
    pause_duration = file_duration_ms * pct

    protected_set = set()
    for s, e in protected_ranges:
        for k in range(s, e + 1):
            protected_set.add(k)

    drag_indices = build_drag_index_set(events)

    first_safe = max(1, int(len(events) * 0.10))
    last_safe  = min(len(events) - 1, int(len(events) * 0.90))
    valid = [
        idx for idx in range(first_safe, last_safe)
        if idx not in protected_set
        and idx not in drag_indices
        and events[idx].get('Type') != 'DragStart'
        and (idx + 1 >= len(events) or events[idx + 1].get('Type') != 'DragStart')
    ]

    if not valid:
        return events, 0

    pause_idx = rng.choice(valid)
    for j in range(pause_idx, len(events)):
        events[j]['Time'] = events[j].get('Time', 0) + pause_duration

    return events, pause_duration
def insert_idle_mouse_movements(events, rng, movement_percentage):
    """
    Insert realistic human-like mouse movements during idle periods (gaps > 2 seconds).
    O(n) - drag membership and click-proximity lookups are precomputed as sets.
    """
    if not events or len(events) < 2:
        return events, 0

    # Precompute O(n) - used for O(1) per-event checks below
    drag_indices = build_drag_index_set(events)

    # Build set of indices that are within 3 s after a click event
    # (idle movements must not be placed in those windows)
    click_proximity = set()
    click_window = 3000
    click_types = {"Click", "LeftDown", "LeftUp", "RightDown", "RightUp"}
    for i, e in enumerate(events):
        if e.get("Type") in click_types:
            t_click = e.get("Time", 0)
            # mark all earlier indices whose next_time lands within the window
            for j in range(i - 1, -1, -1):
                if events[j].get("Time", 0) < t_click - click_window:
                    break
                click_proximity.add(j)

    result = []
    total_idle_time = 0

    for i in range(len(events)):
        result.append(events[i])

        if i < len(events) - 1:
            current_time = int(events[i].get("Time", 0))
            next_time    = int(events[i + 1].get("Time", 0))
            gap = next_time - current_time

            if gap >= 2000:
                if i in drag_indices:
                    continue
                if i in click_proximity:
                    continue
                
                # Calculate active window
                active_duration = int(gap * movement_percentage)
                buffer_start = (gap - active_duration) // 2
                movement_start = current_time + buffer_start
                
                # Get start position
                start_x, start_y = 500, 500
                for j in range(i, -1, -1):
                    x_val = events[j].get("X")
                    y_val = events[j].get("Y")
                    if x_val is not None and y_val is not None:
                        start_x = int(x_val)
                        start_y = int(y_val)
                        break
                
                # Get next position (where we need to end up)
                next_x, next_y = start_x, start_y
                for j in range(i + 1, min(i + 20, len(events))):
                    x_val = events[j].get("X")
                    y_val = events[j].get("Y")
                    if x_val is not None and y_val is not None:
                        next_x = int(x_val)
                        next_y = int(y_val)
                        break
                
                # Reserve last 25% for smooth transition back
                transition_duration = int(active_duration * 0.25)
                pattern_duration = active_duration - transition_duration
                
                # Choose movement behavior
                behavior = rng.choice([
                    'wander',      # Random wandering around
                    'check_edge',  # Quick look at screen edge
                    'fidget',      # Small nervous movements
                    'explore',     # Move far then return
                    'drift',       # Slow meandering
                    'scan'         # Move across screen
                ])
                
                pattern_end_x, pattern_end_y = start_x, start_y
                pattern_time_used = 0
                
                if behavior == 'wander':
                    # Random wandering - multiple small moves
                    num_moves = rng.randint(3, 6)
                    move_duration = pattern_duration // num_moves
                    
                    current_x, current_y = start_x, start_y
                    
                    for move_idx in range(num_moves):
                        # Pick random nearby target
                        target_x = current_x + rng.randint(-150, 150)
                        target_y = current_y + rng.randint(-100, 100)
                        target_x = max(100, min(1800, target_x))
                        target_y = max(100, min(1000, target_y))
                        
                        # Generate human path
                        path = generate_human_path(current_x, current_y, target_x, target_y, move_duration, rng)
                        
                        for path_time, px, py in path:
                            abs_time = movement_start + pattern_time_used + path_time
                            result.append({
                                "Time": abs_time,
                                "Type": "MouseMove",
                                "X": px,
                                "Y": py
                            })
                        
                        current_x, current_y = path[-1][1], path[-1][2]
                        pattern_time_used += move_duration
                    
                    pattern_end_x, pattern_end_y = current_x, current_y
                
                elif behavior == 'check_edge':
                    # Quick look at screen edge then back
                    edges = [
                        (150, start_y),    # Left edge
                        (1750, start_y),   # Right edge
                        (start_x, 150),    # Top edge
                        (start_x, 950),    # Bottom edge
                    ]
                    edge_x, edge_y = rng.choice(edges)
                    
                    # Move to edge (60% of time, fast)
                    edge_duration = int(pattern_duration * 0.6)
                    path_to_edge = generate_human_path(start_x, start_y, edge_x, edge_y, edge_duration, rng)
                    
                    for path_time, px, py in path_to_edge:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    # Return near start (40% of time, slower)
                    return_duration = pattern_duration - edge_duration
                    return_x = start_x + rng.randint(-40, 40)
                    return_y = start_y + rng.randint(-40, 40)
                    return_x = max(100, min(1800, return_x))
                    return_y = max(100, min(1000, return_y))
                    
                    path_return = generate_human_path(edge_x, edge_y, return_x, return_y, return_duration, rng)
                    
                    for path_time, px, py in path_return:
                        abs_time = movement_start + edge_duration + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path_return[-1][1], path_return[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'fidget':
                    # Small rapid movements in small area
                    num_fidgets = rng.randint(5, 10)
                    fidget_duration = pattern_duration // num_fidgets
                    
                    current_x, current_y = start_x, start_y
                    
                    for fidget_idx in range(num_fidgets):
                        # Small offset
                        target_x = current_x + rng.randint(-30, 30)
                        target_y = current_y + rng.randint(-30, 30)
                        target_x = max(100, min(1800, target_x))
                        target_y = max(100, min(1000, target_y))
                        
                        path = generate_human_path(current_x, current_y, target_x, target_y, fidget_duration, rng)
                        
                        for path_time, px, py in path:
                            abs_time = movement_start + pattern_time_used + path_time
                            result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                        
                        current_x, current_y = path[-1][1], path[-1][2]
                        pattern_time_used += fidget_duration
                    
                    pattern_end_x, pattern_end_y = current_x, current_y
                
                elif behavior == 'explore':
                    # Move far away then return near start
                    away_x = start_x + rng.randint(-400, 400)
                    away_y = start_y + rng.randint(-300, 300)
                    away_x = max(100, min(1800, away_x))
                    away_y = max(100, min(1000, away_y))
                    
                    # Go away (65% of time)
                    away_duration = int(pattern_duration * 0.65)
                    path_away = generate_human_path(start_x, start_y, away_x, away_y, away_duration, rng)
                    
                    for path_time, px, py in path_away:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    # Return (35% of time)
                    return_duration = pattern_duration - away_duration
                    return_x = start_x + rng.randint(-15, 15)
                    return_y = start_y + rng.randint(-15, 15)
                    return_x = max(100, min(1800, return_x))
                    return_y = max(100, min(1000, return_y))
                    
                    path_return = generate_human_path(away_x, away_y, return_x, return_y, return_duration, rng)
                    
                    for path_time, px, py in path_return:
                        abs_time = movement_start + away_duration + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path_return[-1][1], path_return[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'drift':
                    # Slow continuous drift
                    target_x = start_x + rng.randint(-200, 200)
                    target_y = start_y + rng.randint(-150, 150)
                    target_x = max(100, min(1800, target_x))
                    target_y = max(100, min(1000, target_y))
                    
                    path = generate_human_path(start_x, start_y, target_x, target_y, pattern_duration, rng)
                    
                    for path_time, px, py in path:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path[-1][1], path[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'scan':
                    # Scan across screen
                    scan_distance = rng.randint(300, 600)
                    direction = rng.choice(['horizontal', 'vertical', 'diagonal'])
                    
                    if direction == 'horizontal':
                        target_x = start_x + (scan_distance if rng.random() < 0.5 else -scan_distance)
                        target_y = start_y + rng.randint(-50, 50)
                    elif direction == 'vertical':
                        target_x = start_x + rng.randint(-50, 50)
                        target_y = start_y + (scan_distance if rng.random() < 0.5 else -scan_distance)
                    else:  # diagonal
                        target_x = start_x + (scan_distance if rng.random() < 0.5 else -scan_distance)
                        target_y = start_y + (scan_distance if rng.random() < 0.5 else -scan_distance)
                    
                    target_x = max(100, min(1800, target_x))
                    target_y = max(100, min(1000, target_y))
                    
                    path = generate_human_path(start_x, start_y, target_x, target_y, pattern_duration, rng)
                    
                    for path_time, px, py in path:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path[-1][1], path[-1][2]
                    pattern_time_used = pattern_duration
                
                # Smooth transition back to next recorded position
                transition_path = generate_human_path(
                    pattern_end_x, pattern_end_y,
                    next_x, next_y,
                    transition_duration,
                    rng
                )
                
                for path_time, px, py in transition_path:
                    abs_time = movement_start + pattern_duration + path_time
                    result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                
                total_idle_time += active_duration
    
    return result, total_idle_time

class QueueFileSelector:
    def __init__(self, rng, all_files, durations_cache):
        self.rng = rng
        self.durations = durations_cache
        self.efficient = [f for f in all_files if "??" not in f.name]
        self.inefficient = [f for f in all_files if "??" in f.name]
        self.eff_pool = list(self.efficient)
        self.ineff_pool = list(self.inefficient)
        self.rng.shuffle(self.eff_pool)
        self.rng.shuffle(self.ineff_pool)

    def get_sequence(self, target_minutes, force_inef=False, is_time_sensitive=False):
        seq, cur_ms = [], 0.0
        target_ms = target_minutes * 60000
        # Add +/-5% margin for flexibility
        margin = int(target_ms * 0.05)
        target_min = target_ms - margin
        target_max = target_ms + margin
        actual_force = force_inef if not is_time_sensitive else False
        
        # Keep adding files until we reach target
        # Stop conditions:
        # 1. Reached target OR
        # 2. Adding next file would overshoot by more than 4 minutes
        
        while cur_ms < target_max:
            # Try to get next file
            if actual_force and self.ineff_pool: pick = self.ineff_pool.pop(0)
            elif self.eff_pool: pick = self.eff_pool.pop(0)
            elif self.efficient:
                self.eff_pool = list(self.efficient); self.rng.shuffle(self.eff_pool)
                pick = self.eff_pool.pop(0)
            elif self.ineff_pool and not is_time_sensitive: pick = self.ineff_pool.pop(0)
            else: break  # No more files
            
            file_duration = self.durations.get(pick, 500)
            
            # File selector multiplier - CRITICAL for accuracy
            # 1.0x = too many files (overshoot 11-18 min)
            # 1.8x = too few files (undershoot 10-13 min)
            # 1.35x = sweet spot (target ?+/-2-4 min)
            if is_time_sensitive:
                estimated_time = file_duration * 1.05  # TIME SENSITIVE: minimal overhead
            else:
                estimated_time = file_duration * 1.35  # NORMAL: balanced estimate
            
            # Check if adding would overshoot too much
            potential_total = cur_ms + estimated_time
            overshoot = potential_total - target_ms
            
            if overshoot > margin:  # Would overshoot beyond acceptable margin
                # Only skip if we're already reasonably close to target
                if cur_ms >= (target_ms - (4 * 60000)):  # Within 4 min of target
                    break  # Close enough, stop
                else:
                    # Still far from target, add it anyway
                    seq.append(pick)
                    cur_ms += estimated_time
            else:
                # Safe to add (won't overshoot by more than 4 min)
                seq.append(pick)
                cur_ms += estimated_time
            
            # Safety limits
            if len(seq) > 800: break
            if cur_ms > target_ms * 3: break
        
        return seq



def insert_massive_pause(events: list, rng: random.Random, mult: float = 1.0) -> tuple:
    """
    Insert one massive pause (500-2900ms x multiplier) at random point.
    For INEFFICIENT files only.
    
    EXCLUDES pause from:
    - Drag sequences (between DragStart and DragEnd)
    - Rapid click sequences (double-clicks, spam clicks)
    - First/last 10% of file (for safety)
    
    Returns (events_with_pause, pause_duration_ms, split_index)
    """
    if not events or len(events) < 10:
        return events, 0, 0
    
    # Generate massive pause: 4-7 minutes (240000-420000ms) x multiplier
    pause_duration = int(rng.uniform(240000.0, 420000.0))  # no mult — flat 4-7 min
    
    # Detect protected ranges (rapid clicks, double-clicks)
    protected_ranges = detect_rapid_click_sequences(events)
    
    # Precompute drag membership O(n) -> O(1) lookups
    drag_indices = build_drag_index_set(events)

    # Find safe split points (not in drag, not in rapid click, not in first/last 10%)
    safe_indices = []
    first_safe = int(len(events) * 0.1)  # Skip first 10%
    last_safe = int(len(events) * 0.9)   # Skip last 10%
    
    for i in range(first_safe, last_safe):
        if i in drag_indices:
            continue
        if is_in_protected_range(i, protected_ranges):
            continue
        # Don't insert right before a DragStart
        if i + 1 < len(events) and events[i + 1].get("Type") == "DragStart":
            continue
        if i + 1 < len(events) and (i + 1) in drag_indices:
            continue
        safe_indices.append(i)
    
    # If no safe indices found, return original events
    if not safe_indices:
        return events, 0, 0
    
    # Pick random safe split point
    split_index = rng.choice(safe_indices)
    
    # Shift all events after split point
    for i in range(split_index + 1, len(events)):
        events[i]["Time"] += pause_duration
    
    return events, pause_duration, split_index

# ============================================================================
# STRING PARTS WITH ANTI-DETECTION
# ============================================================================

def string_cycle(subfolder_files, combination, rng, dmwm_file_set=set(),
                 distraction_files=None, distraction_chance=0.0,
                 is_click_sensitive=False,
                 play_always_first=True, play_always_last=True,
                 mult=1.0):
    """
    String one complete cycle (F1 -> F2 -> F3 -> ...) into a single unit.
    Returns raw events WITHOUT anti-detection features.
    play_always_first / play_always_last: for single-subfolder flat folders,
    always_first/last should fire only on the very first/last cycle of the whole
    strung file. Pass False for all but the first/last cycle respectively.
    Features will be applied to the ENTIRE cycle after.

    distraction_files: list of Path objects for generated distraction JSONs.
    distraction_chance: float in [0,1] - probability of inserting one distraction
                        file between each pair of folder transitions.
    is_click_sensitive: if True, skip cursor pathing between files (no coord changes).
    """
    
    def add_file_to_cycle(file_path, folder_num, is_dmwm, file_label):
        """Helper to add a file to the cycle"""
        nonlocal timeline, cycle_events, file_info_list, has_dmwm, total_pre_pause, total_transition_time, total_snap_gap_time, files_added
        
        # Load events
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception:
            return
        
        if not events:
            return
        
        # Capture base_time BEFORE filtering so that files where the first
        # event is a filtered key (e.g. END key at t=90ms) keep their full
        # original duration. Without this, base_time jumps to the first
        # surviving event and the entire leading gap is lost.
        base_time_pre_filter = min(e.get('Time', 0) for e in events)

        # Filter problematic keys only
        events = filter_problematic_keys(events)
        if not events:
            return

        # INTRA-FILE ZERO-GAP FIX (Feature 25)
        # Some recordings capture a MouseMove and DragStart/LeftDown at the same
        # millisecond (or within 1-14ms) at the same coordinates. The macro player
        # reads these as simultaneous - it can't distinguish "arrived THEN clicked"
        # from "both at once" - causing a left-button clamp at that position.
        # Fix: scan for any MouseMove -> click-type pair with a gap < 15ms and
        # shift the click event (and all subsequent events) forward by enough to
        # create a clean 20ms separation. This is applied to the raw event list
        # before any features are added so it doesn't interact with jitter/pauses.
        _CLICK_TYPES = {'DragStart', 'LeftDown', 'RightDown', 'Click'}
        _ZERO_GAP_THRESHOLD = 15    # ms - gaps below this are "simultaneous"
        _ZERO_GAP_TARGET    = 20    # ms - minimum clean separation to enforce
        for _zi in range(1, len(events)):
            if (events[_zi].get('Type') in _CLICK_TYPES
                    and events[_zi - 1].get('Type') == 'MouseMove'):
                _gap = events[_zi].get('Time', 0) - events[_zi - 1].get('Time', 0)
                if 0 <= _gap < _ZERO_GAP_THRESHOLD:
                    _shift = _ZERO_GAP_TARGET - _gap
                    for _j in range(_zi, len(events)):
                        events[_j]['Time'] = events[_j].get('Time', 0) + _shift

        # Check if dmwm file
        if is_dmwm:
            has_dmwm = True
        
        # Normalize timing — use pre-filter base so leading gaps are preserved
        base_time = base_time_pre_filter
        
        # PRE-FILE PAUSE: 0.8 seconds BEFORE file plays (FLAT, NO multiplier)
        # This prevents drag issues when previous file ended with a click!
        if cycle_events:
            # Random pause scaled by mult: base 500-800ms × mult
            pre_file_pause = rng.uniform(500.0, 800.0) * mult
            timeline += pre_file_pause

            # Track this pause
            total_pre_pause += pre_file_pause
            
            # NOW do cursor transition (AFTER pause, so click has time to release)
            # Get last position from previous file
            last_x, last_y = None, None
            for e in reversed(cycle_events):
                if e.get('X') is not None and e.get('Y') is not None:
                    last_x, last_y = int(e['X']), int(e['Y'])
                    break
            
            # Get first position of current file
            first_x, first_y = None, None
            for e in events:
                if e.get('X') is not None and e.get('Y') is not None:
                    first_x, first_y = int(e['X']), int(e['Y'])
                    break
            
            
            # CURSOR TRANSITION: skipped for click-sensitive folders
            # (no coordinate changes between files - cursor stays wherever it was)
            if not is_click_sensitive:
                transition_duration = rng.uniform(200.0, 400.0) * mult
                if last_x is not None and first_x is not None and (last_x != first_x or last_y != first_y):
                    transition_path = generate_human_path(
                        last_x, last_y, first_x, first_y,
                        int(transition_duration), rng
                    )
                    for rel_time, x, y in transition_path:
                        cycle_events.append({
                            'Type': 'MouseMove',
                            'Time': timeline + rel_time,
                            'X': x,
                            'Y': y
                        })
                    timeline += transition_duration
                    total_transition_time += int(transition_duration)
                    # Final snap to exact start position
                    cycle_events.append({
                        'Type': 'MouseMove',
                        'Time': timeline,
                        'X': first_x,
                        'Y': first_y
                    })
                    # POST-SNAP GAP
                    post_snap_gap = int(rng.uniform(80, 150))
                    timeline += post_snap_gap
                    total_snap_gap_time += post_snap_gap
        
        # Add events from current file
        for event in events:
            new_event = {**event}
            new_event['Time'] = event['Time'] - base_time + timeline
            cycle_events.append(new_event)
        
        # Update timeline and track THIS file's end time
        if cycle_events:
            timeline = cycle_events[-1]['Time']
            file_info_list.append((folder_num, file_label, is_dmwm, timeline))
        files_added += 1
    
    # Main cycle building
    cycle_events = []
    file_info_list = []
    timeline = 0
    has_dmwm = False
    
    files_added = 0  # Counts files added; guards pre-play buffer for every non-first file
    # NEW: Track pre-file pauses, post-pause delays, cursor transitions, and distraction durations
    total_pre_pause = 0
    total_transition_time = 0
    total_snap_gap_time = 0      # cumulative post-snap gaps (80-150ms per file transition)
    total_distraction_pause = 0  # cumulative duration of all inserted distraction files
    
    # SINGLE-SUBFOLDER MODE: if only one subfolder exists, always_first/last
    # should bracket the ENTIRE strung file (once at the very start, once at
    # the very end) rather than wrapping every single selected file.
    single_subfolder = len(subfolder_files) == 1
    if single_subfolder:
        # There is only one folder_num - grab its always_first/last once
        only_folder_num = next(iter(subfolder_files))
        only_folder_data = subfolder_files[only_folder_num]
        single_always_first = only_folder_data.get('always_first')
        single_always_last  = only_folder_data.get('always_last')
        # Play always_first only when flagged (outer loop controls first-cycle)
        if single_always_first and play_always_first:
            is_dmwm = single_always_first in dmwm_file_set
            add_file_to_cycle(single_always_first, only_folder_num, is_dmwm,
                              f"[ALWAYS FIRST] {single_always_first.name}")
    
    def _maybe_insert_distraction(cur_folder_num):
        """Roll the chance and insert one distraction file at the current timeline.
        Uses VirtualDistQueue so all 50 files play before any repeats."""
        nonlocal total_distraction_pause
        if not distraction_files or distraction_chance <= 0.0:
            return
        if rng.random() < distraction_chance:
            # distraction_files is a VirtualDistQueue when called from main()
            dist_path = (distraction_files.next()
                         if hasattr(distraction_files, 'next')
                         else rng.choice(distraction_files))
            t_before  = timeline
            add_file_to_cycle(dist_path, cur_folder_num, False,
                               f"[DISTRACTION] {dist_path.name}")
            total_distraction_pause += (timeline - t_before)

    def _play_nested_loop(nested_item):
        """Play ONE loop of the nested sub-cycle: F1->F2->F3->F4->optional.
        AF/AL are NOT included here - they wrap ALL loops, called once by the caller."""
        _sub_combo  = nested_item['combo']
        _nsf        = nested_item['nested_sf']
        for _sfn, _sfl in _sub_combo:
            _sfd = _nsf.get(_sfn, {})
            if not isinstance(_sfl, list):
                _sfl = [_sfl]
            _saf = _sfd.get('always_first')
            _sal = _sfd.get('always_last')
            if _saf:
                _is_dmwm = _saf in dmwm_file_set
                add_file_to_cycle(_saf, _sfn, _is_dmwm, f"[ALWAYS FIRST] {_saf.name}")
            for _fp in _sfl:
                if isinstance(_fp, dict) and _fp.get('_nested'):
                    _play_nested_loop(_fp)
                else:
                    _is_dmwm = _fp in dmwm_file_set
                    add_file_to_cycle(_fp, _sfn, _is_dmwm, _fp.name)
            if _sal:
                _is_dmwm = _sal in dmwm_file_set
                add_file_to_cycle(_sal, _sfn, _is_dmwm, f"[ALWAYS LAST] {_sal.name}")

    def _play_nested_group(nested_items_list):
        """Play all loops for a nested folder slot.
        AF fires ONCE before all loops; AL fires ONCE after all loops.
        Pattern: [AF] -> loop1 -> loop2 -> ... -> [AL]
        """
        if not nested_items_list:
            return
        _naf = nested_items_list[0].get('nested_root_af')
        _nal = nested_items_list[0].get('nested_root_al')
        if _naf:
            _is_dmwm = _naf in dmwm_file_set
            add_file_to_cycle(_naf, 0.0, _is_dmwm, f"[ALWAYS FIRST] {_naf.name}")
        for _ni in nested_items_list:
            _play_nested_loop(_ni)
        if _nal:
            _is_dmwm = _nal in dmwm_file_set
            add_file_to_cycle(_nal, 0.0, _is_dmwm, f"[ALWAYS LAST] {_nal.name}")

    for idx_combo, (folder_num, file_list) in enumerate(combination):
        folder_data = subfolder_files.get(folder_num, {})
        if not isinstance(file_list, list):
            file_list = [file_list]

        # DISTRACTION: maybe insert BEFORE this folder's files
        _maybe_insert_distraction(folder_num)

        # Separate nested dicts from regular file paths in this slot
        _nested_items = [it for it in file_list if isinstance(it, dict) and it.get('_nested')]
        _regular_items = [it for it in file_list if not (isinstance(it, dict) and it.get('_nested'))]

        if _nested_items:
            # Nested folder: AF once -> all loops -> AL once
            _play_nested_group(_nested_items)
        elif single_subfolder:
            # Single-subfolder: always_first/last already played above/below loop
            for item in _regular_items:
                is_dmwm = item in dmwm_file_set
                add_file_to_cycle(item, folder_num, is_dmwm, item.name)
        else:
            # Multi-subfolder: always_first/last wrap ONLY the files of their OWN folder.
            af = folder_data.get('always_first')
            al = folder_data.get('always_last')
            if af:
                is_dmwm = af in dmwm_file_set
                add_file_to_cycle(af, folder_num, is_dmwm, f"[ALWAYS FIRST] {af.name}")
            for item in _regular_items:
                is_dmwm = item in dmwm_file_set
                add_file_to_cycle(item, folder_num, is_dmwm, item.name)
            if al:
                is_dmwm = al in dmwm_file_set
                add_file_to_cycle(al, folder_num, is_dmwm, f"[ALWAYS LAST] {al.name}")

    # DISTRACTION: maybe insert AFTER the very last folder
    if combination:
        last_folder_num = combination[-1][0]
        _maybe_insert_distraction(last_folder_num)

    if single_subfolder and single_always_last and play_always_last:
        is_dmwm = single_always_last in dmwm_file_set
        add_file_to_cycle(single_always_last, only_folder_num, is_dmwm,
                          f"[ALWAYS LAST] {single_always_last.name}")

    return {
        'events': cycle_events,
        'file_info': file_info_list,
        'has_dmwm': has_dmwm,
        'pre_pause_total': total_pre_pause,
        'transition_total': total_transition_time,
        'snap_gap_total': total_snap_gap_time,
        'distraction_pause_total': total_distraction_pause,
    }


# ============================================================================
# DISTRACTION FILE GENERATION
# ============================================================================

# Windows Virtual Key codes for keyboard events
# (must be integers - the macro player does NOT accept strings)
_VK = {
    'a':8  # placeholder - built dynamically below
}
_VK = {}
for _c in 'abcdefghijklmnopqrstuvwxyz':
    _VK[_c] = ord(_c.upper())   # A=65 ? Z=90
_VK.update({
    '0': 48, '1': 49, '2': 50, '3': 51, '4': 52,
    '5': 53, '6': 54, '7': 55, '8': 56, '9': 57,
    'Back': 8,         # Backspace
    '.': 190, ',': 188, ';': 186, '/': 191,
    "'": 222, '[': 219, ']': 221, '\\': 220,
    '-': 189, '=': 187,
})


def _evt(type_, time, x=None, y=None, delta=None, keycode=None) -> dict:
    """
    Build a properly-structured macro event with ALL 6 required fields.
    The macro player expects Type, Time, X, Y, Delta, KeyCode on EVERY event.
    Keyboard events:  X=None, Y=None, Delta=None, KeyCode=<int VK code>
    Mouse events:     X=<int>, Y=<int>, Delta=None, KeyCode=None
    """
    return {
        'Type':    type_,
        'Time':    time,
        'X':       x,
        'Y':       y,
        'Delta':   delta,
        'KeyCode': keycode,
    }


# Common words / phrases a player might idly type then delete
_DISTRACTION_WORDS = [
    "nice", "lol", "gg", "hey", "ok", "sure", "brb", "back", "sec",
    "wait", "almost", "done", "yes", "no", "maybe", "idk", "nah",
    "yeah", "yep", "nope", "omg", "wow", "thanks", "ty", "np",
    "haha", "lmao", "ez", "rip", "oof", "yo", "kk",
    "cya", "afk", "gtg", "bbl", "wb", "ggwp", "niceone",
]

# Keys that players accidentally spam then erase (letters + symbols with VK mappings)
_SPAM_KEYS = list("asdfghjklqwertyuiopzxcvbnm/.,;'[]-=")


def _human_interval(rng, lo_ms: float, hi_ms: float) -> float:
    return rng.uniform(lo_ms, hi_ms)


def _safe_gap(rng) -> float:
    """Minimum advance so no two events share a timestamp."""
    return _human_interval(rng, 30.0, 120.0)


def _add_mouse_wander(events, timeline, rng, cur_x, cur_y):
    """
    Move cursor to 2-7 random destinations.
    Per-call: number of moves, speed envelope, and inter-move pause
    range are all re-randomised so no two wanders feel the same.
    Returns (timeline, x, y).
    """
    t = timeline + _safe_gap(rng)
    x, y = cur_x, cur_y
    # Randomise both envelope bounds so the RANGE of speeds varies per call
    spd_lo = rng.uniform(150.0, 500.0)
    spd_hi = rng.uniform(spd_lo + 200.0, spd_lo + 1200.0)
    gap_lo = rng.uniform(30.0, 150.0)
    gap_hi = rng.uniform(gap_lo + 100.0, gap_lo + 600.0)
    n_moves = rng.randint(2, 7)
    for _ in range(n_moves):
        tx = rng.randint(150, 950)
        ty = rng.randint(120, 620)
        seg_dur = _human_interval(rng, spd_lo, spd_hi)
        path = generate_human_path(x, y, tx, ty, int(seg_dur), rng)
        for rel, px, py in path:
            events.append(_evt('MouseMove', t + rel, px, py))
        t += seg_dur
        x, y = tx, ty
        t += _human_interval(rng, gap_lo, gap_hi)
    return t, x, y


def _add_cursor_pause(events, timeline, rng, cur_x, cur_y):
    """
    Stay still (or drift slightly) for a randomised duration.
    Drift probability, drift magnitude, and pause length all vary per call.
    Returns (timeline, x, y).
    """
    # Duration envelope randomised per call: 0.3s-4s range, but the actual
    # bounds shift so some calls are twitchy-short and some are long
    dur_lo = rng.uniform(300.0, 800.0)
    dur_hi = rng.uniform(dur_lo + 400.0, dur_lo + 2500.0)
    duration = _human_interval(rng, dur_lo, dur_hi)
    t_start  = timeline + _safe_gap(rng)
    # Drift: random probability AND random magnitude per call
    drift_prob = rng.uniform(0.20, 0.65)
    if rng.random() < drift_prob:
        drift_mag = rng.randint(3, 18)
        dx = max(100, min(1800, cur_x + rng.randint(-drift_mag, drift_mag)))
        dy = max(100, min(1000, cur_y + rng.randint(-drift_mag, drift_mag)))
        mid = t_start + duration * rng.uniform(0.2, 0.8)
        events.append(_evt('MouseMove', mid,              dx,    dy))
        events.append(_evt('MouseMove', t_start+duration, cur_x, cur_y))
    return t_start + duration, cur_x, cur_y


def _add_right_click(events, timeline, rng, cur_x, cur_y):
    """
    Approach a random nearby position then right-click.
    Approach speed, offset range, hover time, and hold duration all vary per call.
    Returns (timeline, x, y).
    """
    t  = timeline + _safe_gap(rng)
    # Randomise offset range per call: small twitch vs large repositioning
    off_x = rng.randint(20, 200)
    off_y = rng.randint(15, 140)
    tx = max(100, min(1800, cur_x + rng.randint(-off_x, off_x)))
    ty = max(100, min(1000, cur_y + rng.randint(-off_y, off_y)))
    spd_lo = rng.uniform(100.0, 300.0)
    move_dur = _human_interval(rng, spd_lo, spd_lo + rng.uniform(200.0, 700.0))
    path = generate_human_path(cur_x, cur_y, tx, ty, int(move_dur), rng)
    for rel, px, py in path:
        events.append(_evt('MouseMove', t + rel, px, py))
    t += move_dur
    cur_x, cur_y = tx, ty
    # Hover time randomised per call
    t += _human_interval(rng, 30.0, rng.uniform(100.0, 350.0))
    hold_lo = rng.uniform(40.0, 100.0)
    hold = _human_interval(rng, hold_lo, hold_lo + rng.uniform(80.0, 250.0))
    events.append(_evt('RightDown', t,        cur_x, cur_y))
    events.append(_evt('RightUp',   t + hold, cur_x, cur_y))
    # Post-click linger: sometimes brief, sometimes longer
    t += hold + _human_interval(rng, 80.0, rng.uniform(300.0, 900.0))
    return t, cur_x, cur_y


def _add_typing(events, timeline, rng, cur_x, cur_y):
    """
    Type a random word then erase it character by character.
    Typing speed, erasing speed, and hesitation pause all re-randomised
    per call so every typing event has its own rhythm.
    KeyCode = integer VK code, X/Y = None.
    """
    word = rng.choice(_DISTRACTION_WORDS)
    t    = timeline + _safe_gap(rng)
    # Per-call speed envelopes
    type_hold_lo = rng.uniform(40.0, 90.0)
    type_hold_hi = rng.uniform(type_hold_lo + 30.0, type_hold_lo + 120.0)
    type_gap_lo  = rng.uniform(50.0, 130.0)
    type_gap_hi  = rng.uniform(type_gap_lo + 40.0, type_gap_lo + 180.0)
    erase_hold_lo = rng.uniform(40.0, 100.0)
    erase_hold_hi = rng.uniform(erase_hold_lo + 30.0, erase_hold_lo + 110.0)
    erase_gap_lo  = rng.uniform(45.0, 110.0)
    erase_gap_hi  = rng.uniform(erase_gap_lo + 30.0, erase_gap_lo + 140.0)
    hesitation    = rng.uniform(100.0, rng.uniform(500.0, 3000.0))

    for ch in word:
        vk = _VK.get(ch, _VK.get(ch.lower()))
        if vk is None:
            continue
        hold = _human_interval(rng, type_hold_lo, type_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=vk))
        events.append(_evt('KeyUp',   t + hold, keycode=vk))
        t += hold + _human_interval(rng, type_gap_lo, type_gap_hi)
    t += hesitation
    bk = _VK['Back']
    for _ in word:
        hold = _human_interval(rng, erase_hold_lo, erase_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=bk))
        events.append(_evt('KeyUp',   t + hold, keycode=bk))
        t += hold + _human_interval(rng, erase_gap_lo, erase_gap_hi)
    return t


def _add_key_spam(events, timeline, rng, cur_x, cur_y):
    """
    Accidentally spam a key 2-9x, then erase with Backspace.
    Spam speed, erase speed, and the 'oh no' pause all re-randomised per call.
    KeyCode = integer VK code.
    """
    key   = rng.choice(_SPAM_KEYS)
    vk    = _VK.get(key)
    if vk is None:
        return timeline
    count = rng.randint(2, 9)
    t     = timeline + _safe_gap(rng)
    bk    = _VK['Back']
    # Spam envelope: sometimes key-repeat fast, sometimes deliberate
    spam_hold_lo = rng.uniform(25.0, 80.0)
    spam_hold_hi = rng.uniform(spam_hold_lo + 20.0, spam_hold_lo + 100.0)
    spam_gap_lo  = rng.uniform(15.0, 60.0)
    spam_gap_hi  = rng.uniform(spam_gap_lo + 15.0, spam_gap_lo + 80.0)
    # "Oh no" reaction: anywhere from a quick twitch to a long freeze
    ohno_pause = rng.uniform(150.0, rng.uniform(500.0, 1800.0))
    # Erase envelope: typically slower than spam (deliberate)
    erase_hold_lo = rng.uniform(45.0, 100.0)
    erase_hold_hi = rng.uniform(erase_hold_lo + 20.0, erase_hold_lo + 90.0)
    erase_gap_lo  = rng.uniform(40.0, 100.0)
    erase_gap_hi  = rng.uniform(erase_gap_lo + 20.0, erase_gap_lo + 110.0)

    for _ in range(count):
        hold = _human_interval(rng, spam_hold_lo, spam_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=vk))
        events.append(_evt('KeyUp',   t + hold, keycode=vk))
        t += hold + _human_interval(rng, spam_gap_lo, spam_gap_hi)
    t += ohno_pause
    for _ in range(count):
        hold = _human_interval(rng, erase_hold_lo, erase_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=bk))
        events.append(_evt('KeyUp',   t + hold, keycode=bk))
        t += hold + _human_interval(rng, erase_gap_lo, erase_gap_hi)
    return t


def _add_shape_movement(events, timeline, rng, cur_x, cur_y):
    """
    Trace a geometric shape: circle/donut (3-5 laps), triangle, square,
    rectangle, or star. Each shape has per-point jitter and varied speed
    so it reads human, not robotic.

    Returns (new_timeline, new_x, new_y).
    """
    shape = rng.choice(['circle', 'triangle', 'square', 'rectangle', 'star'])
    t     = timeline + _safe_gap(rng)

    # Speed factor: how long each segment between waypoints takes (ms).
    # Drawn once per shape so the whole shape is consistently fast or slow.
    ms_per_seg = rng.uniform(80.0, 400.0)   # fast (~80ms) to leisurely (~400ms)
    jitter_px  = rng.uniform(3.0, 10.0)     # positional jitter magnitude

    def _trace_waypoints(wpts):
        """Move through a list of (x, y) waypoints with jitter and human paths."""
        nonlocal t, cur_x, cur_y
        px, py = cur_x, cur_y
        for wx, wy in wpts:
            # Jitter: slightly randomise each target point
            wx = int(max(100, min(1800, wx + rng.uniform(-jitter_px, jitter_px))))
            wy = int(max(100, min(1000, wy + rng.uniform(-jitter_px, jitter_px))))
            # Per-segment time varies +/-40% for natural rhythm
            seg = ms_per_seg * rng.uniform(0.6, 1.4)
            path = generate_human_path(px, py, wx, wy, int(seg), rng)
            for rel, ex, ey in path:
                events.append(_evt('MouseMove', t + rel, ex, ey))
            t  += seg
            px, py = wx, wy
        return px, py

    # ------------------------------------------------------------------ circle
    if shape == 'circle':
        radius = rng.randint(60, 180)
        # Keep center so shape stays fully on screen
        cx = int(max(100 + radius, min(1800 - radius, cur_x + rng.randint(-120, 120))))
        cy = int(max(100 + radius, min(1000 - radius, cur_y + rng.randint(-100, 100))))
        laps   = rng.randint(3, 5)
        steps  = rng.randint(20, 36)   # points per lap (10-18 degree increments)
        wpts   = []
        for lap in range(laps):
            for s in range(steps):
                angle = (s / steps) * 2 * math.pi
                wpts.append((
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                ))
        last_x, last_y = _trace_waypoints(wpts)

    # --------------------------------------------------------------- triangle
    elif shape == 'triangle':
        spread = rng.randint(80, 220)
        # Generate 3 vertices roughly equilateral around current position
        vertices = []
        for k in range(3):
            angle = (k / 3) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            vx = cur_x + spread * math.cos(angle)
            vy = cur_y + spread * math.sin(angle)
            vertices.append((vx, vy))
        laps = rng.randint(1, 3)
        wpts = vertices * laps + [vertices[0]]   # close the last lap
        last_x, last_y = _trace_waypoints(wpts)

    # ----------------------------------------------------------------- square
    elif shape == 'square':
        side = rng.randint(80, 200)
        x0   = int(max(100, min(1800 - side, cur_x - side // 2)))
        y0   = int(max(100, min(1000 - side, cur_y - side // 2)))
        corners = [(x0, y0), (x0 + side, y0),
                   (x0 + side, y0 + side), (x0, y0 + side)]
        laps = rng.randint(1, 3)
        wpts = corners * laps + [corners[0]]
        last_x, last_y = _trace_waypoints(wpts)

    # -------------------------------------------------------------- rectangle
    elif shape == 'rectangle':
        w  = rng.randint(120, 280)
        h  = rng.randint(60,  160)
        x0 = int(max(100, min(1800 - w, cur_x - w // 2)))
        y0 = int(max(100, min(1000 - h, cur_y - h // 2)))
        corners = [(x0, y0), (x0 + w, y0),
                   (x0 + w, y0 + h), (x0, y0 + h)]
        laps = rng.randint(1, 3)
        wpts = corners * laps + [corners[0]]
        last_x, last_y = _trace_waypoints(wpts)

    # ------------------------------------------------------------------- star
    else:   # star
        outer_r = rng.randint(80, 160)
        inner_r = int(outer_r * rng.uniform(0.35, 0.55))
        points  = 5
        laps    = rng.randint(1, 2)
        wpts    = []
        for lap in range(laps):
            for k in range(points * 2):
                # Alternate outer/inner radius
                r     = outer_r if k % 2 == 0 else inner_r
                angle = (k / (points * 2)) * 2 * math.pi - math.pi / 2
                wpts.append((
                    cur_x + r * math.cos(angle),
                    cur_y + r * math.sin(angle),
                ))
        wpts.append(wpts[0])   # close shape
        last_x, last_y = _trace_waypoints(wpts)

    return t, int(last_x), int(last_y)



def generate_distraction_files(distractions_src_folder, out_folder, rng,
                                count: int = 50,
                                bundle_id: int = 0) -> int:
    """
    Generate `count` distraction files.
    Each file uses exactly 3 randomly-chosen features from {wander, pause,
    right_click, type, key_spam}.
    All events follow the exact 6-field macro schema:
      Type, Time, X, Y, Delta, KeyCode  (Delta/KeyCode None where unused)
    KeyCode values are Windows VK integers, never strings.
    No left clicks. Duration 1-3 min (float ms, rounded only at save).
    Per-feature cooldown: 17-40 s between successive triggers of the same
    feature, calculated in float ms, unique per feature per file.
    """
    from pathlib import Path as _Path
    out_folder = _Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    # 6 features - each file picks 3 at random.
    ACTION_WEIGHTS = [
        ('wander',      20),
        ('pause',       15),
        ('right_click', 22),
        ('type',        20),
        ('key_spam',    12),
        ('shapes',      21),
    ]
    action_names = [a[0] for a in ACTION_WEIGHTS]
    action_wts   = [a[1] for a in ACTION_WEIGHTS]

    written = 0
    for i in range(count):
        file_rng = random.Random(rng.random())
        target   = file_rng.uniform(30000.0, 120000.0)

        # Pick exactly 3 features for this file
        chosen     = file_rng.sample(action_names, 3)
        chosen_wts = [w for a, w in ACTION_WEIGHTS if a in chosen]

        events   = []
        timeline = 0.0
        cur_x    = file_rng.randint(300, 700)
        cur_y    = file_rng.randint(250, 450)
        last_act = None

        # Shared cooldown: after any action fires, ALL features are locked out
        # for a single random window of 17 000-30 000 ms (float ms, never rounded).
        # A fresh cooldown is drawn each time any feature triggers, so the gap
        # between every pair of consecutive actions is independently randomised.
        next_allowed_any = 0.0   # earliest ms any action may next fire

        # OVERLAP CONTROL
        # Sequential fraction: random decimal in [90.0, 95.0] percent.
        # For that share of triggers, the next action must wait until the
        # previous one has fully finished playing (action_busy_until).
        # For the remaining (100 - sequential_pct)% of triggers, the new action
        # may start while the previous is still playing (overlap allowed).
        sequential_pct  = file_rng.uniform(90.0, 95.0)   # e.g. 92.47%
        sequential_frac = sequential_pct / 100.0          # e.g. 0.9247
        action_busy_until = 0.0   # absolute ms when last action's events end

        # Opening move
        tx       = file_rng.randint(150, 950)
        ty       = file_rng.randint(120, 620)
        open_dur = _human_interval(file_rng, 350.0, 950.0)
        path     = generate_human_path(cur_x, cur_y, tx, ty, int(open_dur), file_rng)
        for rel, px, py in path:
            events.append(_evt('MouseMove', timeline + rel, px, py))
        timeline += open_dur
        action_busy_until = timeline
        cur_x, cur_y = tx, ty

        while timeline < target:
            # Wait for the shared cooldown window to expire
            if timeline < next_allowed_any:
                timeline = next_allowed_any + _human_interval(file_rng, 10.0, 80.0)
                action_busy_until = max(action_busy_until, timeline)

            # Actions available = chosen set minus consecutive-pause block
            available = [
                a for a in chosen
                if not (a == 'pause' and last_act == 'pause')
            ]

            if not available:
                # Only happens if all 3 chosen features are 'pause' (impossible
                # with sample(3)), but guard anyway
                last_act = None
                continue

            avail_wts = [w for a, w in ACTION_WEIGHTS if a in available]
            action    = file_rng.choices(available, weights=avail_wts, k=1)[0]

            # Decide: sequential (wait for previous to finish) or overlap?
            if file_rng.random() < sequential_frac:
                start_t = max(timeline, action_busy_until) + _safe_gap(file_rng)
            else:
                start_t = timeline + _safe_gap(file_rng)

            timeline = start_t

            if action == 'wander':
                timeline, cur_x, cur_y = _add_mouse_wander(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'pause':
                timeline, cur_x, cur_y = _add_cursor_pause(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'right_click':
                timeline, cur_x, cur_y = _add_right_click(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'type':
                timeline = _add_typing(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'key_spam':
                timeline = _add_key_spam(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'shapes':
                timeline, cur_x, cur_y = _add_shape_movement(events, timeline, file_rng, cur_x, cur_y)

            action_busy_until = timeline

            # Draw a fresh shared cooldown after every trigger (float ms, never rounded)
            cooldown = file_rng.uniform(17000.0, 30000.0)
            next_allowed_any = timeline + cooldown

            last_act = action
            if timeline <= 0:
                timeline = 1.0

        if not events:
            continue

        # Normalise times and enforce no zero-gaps
        base = min(e['Time'] for e in events)
        for e in events:
            e['Time'] = max(0, int(round(e['Time'] - base)))
        events.sort(key=lambda e: e['Time'])
        for j in range(1, len(events)):
            if events[j]['Time'] <= events[j-1]['Time']:
                events[j]['Time'] = events[j-1]['Time'] + 1

        # Trim any events that spilled past target due to cooldown overshoot.
        target_ms_int = int(round(target))
        events = [e for e in events if e['Time'] <= target_ms_int]
        if not events:
            continue

        # Ensure the file's duration matches its target (within 1s tolerance).
        # Cursor idle time during cooldown gaps produces no events, so the last
        # event may land well before target. A final anchor MouseMove captures
        # "cursor held still" and gives the file the correct playback length.
        if events[-1]['Time'] < target_ms_int - 1000:
            last_x = next((e['X'] for e in reversed(events) if e.get('X') is not None), cur_x)
            last_y = next((e['Y'] for e in reversed(events) if e.get('Y') is not None), cur_y)
            events.append({
                'Type': 'MouseMove', 'Time': target_ms_int,
                'X': int(last_x), 'Y': int(last_y),
                'Delta': None, 'KeyCode': None,
            })

        total_ms  = events[-1]['Time']
        total_min = total_ms // 60000
        total_sec = (total_ms % 60000) // 1000
        fname     = f"DISTRACTION_{str(i+1).zfill(2)}_{total_min}m{total_sec}s.json"
        (out_folder / fname).write_text(json.dumps(events, indent=2))
        written += 1

    return written

def apply_cycle_features(cycle_events, rng, is_raw, has_dmwm, is_inef=False,
                          is_click_sensitive=False, mult=1.0):
    """
    Apply anti-detection features to a complete cycle.

    Args:
        cycle_events: Events from one complete cycle
        rng: Random generator
        is_raw:  If True, 0% within-file pause (no pauses inserted)
        is_inef: If True, 15% within-file pause; False = 5% (normal)
        has_dmwm: If True, skip ALL modifications
        is_click_sensitive: If True, skip jitter and idle mouse movements
                            (no coordinate-changing features applied)

    Returns:
        (processed_events, stats)
    """
    stats = {
        'jitter_count': 0,
        'total_moves': 0,
        'jitter_percentage': 0.0,
        'intra_pauses': 0,
        'idle_movements': 0
    }

    if has_dmwm:
        return cycle_events, stats

    # Step 1: Jitter - SKIPPED for click-sensitive folders
    if not is_click_sensitive:
        events_with_jitter, jitter_count, move_count, jitter_pct = add_pre_click_jitter(cycle_events, rng)
        stats['jitter_count'] = jitter_count
        stats['total_moves'] = move_count
        stats['jitter_percentage'] = jitter_pct
    else:
        events_with_jitter = cycle_events

    # Step 2: Rapid click detection
    protected_ranges = detect_rapid_click_sequences(events_with_jitter)

    # Step 3: Within-file pause (percentage-based, range chosen per call)
    #   Raw: 0%   Normal: 2-5%   Inefficient: 10-15%
    file_type = 'raw' if is_raw else ('inef' if is_inef else 'normal')
    events_with_pauses, pause_time = insert_intra_file_pauses(
        events_with_jitter, rng, protected_ranges, file_type=file_type
    )
    stats['intra_pauses'] = pause_time

    # Step 3b: Multiplier-driven random mid-event pause (50% chance per cycle)
    # The multiplier can express itself as a short natural hesitation inserted
    # directly between recorded events rather than only making buffers longer.
    # Duration: rng.uniform(200, 800) * mult ms. Skipped for raw + click-sensitive.
    if not is_raw and not is_click_sensitive and rng.random() < 0.50:
        _mid_ms = rng.uniform(200.0, 800.0) * mult
        _drag_idx = build_drag_index_set(events_with_pauses)
        _p_set = set()
        for _s, _e in protected_ranges:
            for _k in range(_s, _e + 1):
                _p_set.add(_k)
        _fs = max(1, int(len(events_with_pauses) * 0.10))
        _ls = min(len(events_with_pauses) - 1, int(len(events_with_pauses) * 0.90))
        _valid = [
            _i for _i in range(_fs, _ls)
            if _i not in _p_set and _i not in _drag_idx
            and events_with_pauses[_i].get('Type') != 'DragStart'
            and (_i + 1 >= len(events_with_pauses)
                 or events_with_pauses[_i + 1].get('Type') != 'DragStart')
        ]
        if _valid:
            _ins = rng.choice(_valid)
            for _j in range(_ins, len(events_with_pauses)):
                events_with_pauses[_j]['Time'] = events_with_pauses[_j].get('Time', 0) + _mid_ms
            stats['intra_pauses'] += _mid_ms

    # Step 4: Idle movements - SKIPPED for click-sensitive folders
    if not is_click_sensitive:
        movement_pct = rng.uniform(0.40, 0.50)
        events_with_idle, idle_time = insert_idle_mouse_movements(
            events_with_pauses, rng, movement_pct
        )
        stats['idle_movements'] = idle_time
    else:
        events_with_idle = events_with_pauses

    return events_with_idle, stats



# ============================================================================
# FOLDER SCANNING
# ============================================================================

def scan_for_numbered_subfolders(base_path):
    """
    Scans folder for subfolders with numbers in their names.
    Also checks for "dont mess with me" subfolder and "optional" folders.
    
    NEW: Checks main folder name for "time sensitive" tag.
    If main folder is tagged, ALL subfolders become time_sensitive!
    
    Accepts: "1", "part1", "step2", "3-action", "3 optional- walk", "3.5- insert", etc.
    DECIMAL SUPPORT: "3.5" will be placed after "3" and before "4"
    
    Returns tuple: (numbered_folders_dict, dmwm_file_set, non_json_files_list)
    
    numbered_folders: {num: {'files': [...], 'is_optional': bool}}
    dmwm_file_set: set of files from "dont mess with me"
    non_json_files: [list of non-JSON files to copy]
    """
    base = Path(base_path)
    numbered_folders = {}
    unmodified_files = []
    non_json_files = []
    
    # Check if MAIN FOLDER is tagged - propagates to ALL subfolders
    _base_lower = base.name.lower()
    main_folder_time_sensitive  = 'time sensitive'  in _base_lower
    main_folder_click_sensitive = (
        'click sensitive'      in _base_lower or   # plain: "click sensitive"
        'click/time sensitive' in _base_lower or   # slash: "click/time sensitive"
        'click+time sensitive' in _base_lower or   # plus:  "click+time sensitive"
        'click time sensitive' in _base_lower      # space: "click time sensitive"
    )

    if main_folder_time_sensitive:
        print(f"  ??  MAIN FOLDER is TIME SENSITIVE - All subfolders will skip inefficient files!")
    if main_folder_click_sensitive:
        print(f"  ?  MAIN FOLDER is CLICK SENSITIVE - All subfolders will skip cursor/jitter/idle/distraction features!")
    
    for item in base.iterdir():
        if not item.is_dir():
            # Collect non-JSON files in root
            if not item.name.endswith('.json'):
                non_json_files.append(item)
            continue
        
        # Check for "Don't use features on me" folder (case-insensitive)
        # Also accepts old name "dont mess with me" for backward compatibility
        folder_name_lower = item.name.lower()
        if folder_name_lower == "don't use features on me" or folder_name_lower == "dont mess with me":
            # Add all JSON files from this folder as unmodified
            dmwm_files = sorted(item.glob("*.json"))
            unmodified_files.extend(dmwm_files)
            print(f"  [!]?  Found 'Don't use features on me' folder: {len(dmwm_files)} unmodified files")
            continue
        
        # Extract folder number - prefer explicit F<N> prefix (F1, F2, F3.5, etc.)
        # so that other numbers in the name (e.g. 'press 1', 'optional-2-') are ignored.
        _f_match = re.match(r'^[Ff](\d+(?:\.\d+)?)', item.name.strip())
        if _f_match:
            folder_num = float(_f_match.group(1))   # e.g. F3.5 -> 3.5
        else:
            # Fall back: first number anywhere (handles '1- mine', '3.5 optional- ...')
            _n_match = re.search(r'\d+\.?\d*', item.name)
            folder_num = float(_n_match.group()) if _n_match else None
        if folder_num is not None:
            all_json_files = sorted(item.glob("*.json"))
            
            # Separate "always first", "always last", and regular files
            always_first = None
            always_last = None
            regular_files = []
            
            for json_file in all_json_files:
                filename_lower = json_file.name.lower()
                if 'always first' in filename_lower or 'alwaysfirst' in filename_lower:
                    always_first = json_file
                    print(f"   Found 'always first' in folder {folder_num}: {json_file.name}")
                elif 'always last' in filename_lower or 'alwayslast' in filename_lower:
                    always_last = json_file
                    print(f"   Found 'always last' in folder {folder_num}: {json_file.name}")
                else:
                    regular_files.append(json_file)
            
            # Check if folder is "optional" (default 24-33%, or custom % from tag)
            is_optional = 'optional' in item.name.lower()
            optional_chance = parse_optional_chance(item.name) if is_optional else None
            
            # Check if folder is "end" (becomes definitive end point)
            is_end = bool(re.search(r'\bend\b', item.name, re.IGNORECASE))
            
            # Check if folder is "time sensitive" (1:1 raw:normal, no inef, minimal overhead)
            # Priority: Main folder tag > Individual subfolder tag
            if main_folder_time_sensitive:
                is_time_sensitive = True  # Main folder overrides all
            else:
                is_time_sensitive = 'time sensitive' in item.name.lower()

            # Check if folder is "click sensitive" (no cursor pathing between files)
            item_lower = item.name.lower()
            is_click_time_sensitive = ('click/time sensitive' in item_lower
                                       or 'click+time sensitive' in item_lower
                                       or 'click time sensitive' in item_lower)
            is_click_sensitive      = (('click sensitive' in item_lower)
                                       and not is_click_time_sensitive)
            # click/time sensitive implies both flags
            if is_click_time_sensitive:
                is_time_sensitive    = True
                is_click_sensitive   = True
            # Main folder tag propagates to all subfolders
            if main_folder_click_sensitive:
                is_click_sensitive = True

            # "optional+end" combo: optional folder that ends loop if chosen
            is_optional_end = is_optional and is_end

            # Detect nested numbered subfolders (e.g. F5 that has its own F1/F2/F3 inside)
            nested_subfolder_files = None
            nested_root_af = None
            nested_root_al = None
            if not regular_files:
                # No direct JSON files — check if there are numbered sub-subfolders
                _nested_subdirs = [
                    d for d in item.iterdir()
                    if d.is_dir() and re.search(r'^[Ff]?\d', d.name.strip())
                ]
                if _nested_subdirs:
                    # Recursively scan the nested folder
                    _nf, _nd, _nnj, _naf, _nal = scan_for_numbered_subfolders(item)
                    if _nf:
                        nested_subfolder_files = _nf
                        nested_root_af = _naf
                        nested_root_al = _nal
                        print(f"  Nested folder detected: {item.name} has {len(_nf)} sub-folders inside")

            if regular_files or nested_subfolder_files:
                numbered_folders[folder_num] = {
                    'files': regular_files,
                    'is_optional': is_optional,
                    'optional_chance': optional_chance,
                    'is_end': is_end,
                    'is_optional_end': is_optional_end,
                    'is_time_sensitive': is_time_sensitive,
                    'is_click_sensitive': is_click_sensitive,
                    'max_files': parse_max_files(item.name),
                    'always_first': always_first,
                    'always_last': always_last,
                    'nested_subfolder_files': nested_subfolder_files,
                    'nested_root_always_first': nested_root_af,
                    'nested_root_always_last': nested_root_al,
                    'folder_name': item.name,   # stored for name-lookup in specific-folders
                    'folder_path': item,
                }

            # Also collect non-JSON files from numbered folders
            for file in item.iterdir():
                if file.is_file() and not file.name.endswith('.' + 'json'):
                    non_json_files.append(file)
    
    # FLAT FOLDER SUPPORT:
    # If no numbered subfolders were found, check if there are JSON files
    # sitting directly in the folder itself. If so, treat the folder as a
    # single virtual subfolder (number 1.0) so everything downstream works
    # without any changes.
    if not numbered_folders:
        direct_json = sorted(base.glob('*.json'))
        
        # Exclude logout files from the pool
        logout_names = {'logout.json', '- logout.json', '-logout.json'}
        direct_json = [f for f in direct_json if f.name.lower() not in logout_names]
        
        if direct_json:
            # Separate always_first / always_last from regular files
            always_first = None
            always_last = None
            regular_files = []
            for json_file in direct_json:
                name_lower = json_file.name.lower()
                if 'always first' in name_lower or 'alwaysfirst' in name_lower:
                    always_first = json_file
                    print(f"   Found 'always first': {json_file.name}")
                elif 'always last' in name_lower or 'alwayslast' in name_lower:
                    always_last = json_file
                    print(f"   Found 'always last': {json_file.name}")
                else:
                    regular_files.append(json_file)
            
            if regular_files:
                print(f"   Flat folder detected - {len(regular_files)} file(s) treated as single pool (subfolder 1.0)")
                numbered_folders[1.0] = {
                    'files': regular_files,
                    'is_optional': False,
                    'optional_chance': None,
                    'is_end': False,
                    'is_optional_end': False,
                    'is_time_sensitive': main_folder_time_sensitive,
                    'is_click_sensitive': main_folder_click_sensitive,
                    'always_first': always_first,
                    'always_last': always_last
                }

    # Scan root-level JSON files for always_first / always_last even when
    # numbered subfolders exist. These wrap the ENTIRE strung file once —
    # not per cycle, not per subfolder. Separate from subfolder-level always tags.
    root_always_first = None
    root_always_last  = None
    if numbered_folders:  # only meaningful when there are actual subfolders
        for _rf in sorted(base.glob('*.json')):
            _name = _rf.name.lower()
            if 'always first' in _name or 'alwaysfirst' in _name:
                root_always_first = _rf
                print(f"  Found root-level 'always first': {_rf.name}")
            elif 'always last' in _name or 'alwayslast' in _name:
                root_always_last = _rf
                print(f"  Found root-level 'always last': {_rf.name}")

    # Add unmodified files to their respective numbered folder pools
    # They become regular files, just tracked separately
    dmwm_file_set = set(unmodified_files)

    return numbered_folders, dmwm_file_set, non_json_files, root_always_first, root_always_last

# ============================================================================
# SIMPLE PERSISTENT HISTORY (Like Bundle Counter!)
# ============================================================================


class ManualHistoryTracker:
    """
    Manual combination history - YOU upload combination files!
    
    Folder: input_macros/combination_history/
    
    Code reads ALL .txt files in that folder and ensures no duplicate combinations.
    You manually dump combination files from each bundle's output to this folder.
    
    Files can be named anything, code reads them all:
    - COMBINATION_HISTORY_39.txt
    - combos_from_bundle_40.txt
    - anything.txt
    
    All will be read and combined into one set of used combinations.
    """
    def __init__(self, subfolder_files, rng, folder_name, input_dir):
        self.subfolder_files = subfolder_files
        self.rng = rng
        self.folder_name = folder_name
        self.input_dir = input_dir
        
        # History folder (not a single file!)
        self.history_dir = input_dir / "combination_history"
        
        # Load ALL combinations from ALL files in the folder
        self.used_combinations = self._load_all_combinations()

        # Per-subfolder virtual queues: each subfolder gets its own shuffled
        # queue so no file repeats until all files in that subfolder are used.
        self._file_queues = {}   # {folder_num: [shuffled file paths]}
        for fn, fd in self.subfolder_files.items():
            pool = list(fd.get('files', []))
            self.rng.shuffle(pool)
            self._file_queues[fn] = pool

        # Nested trackers: for subfolders that contain their own sub-subfolders,
        # maintain a separate ManualHistoryTracker for each.
        self._nested_trackers = {}
        for fn, fd in self.subfolder_files.items():
            nsf = fd.get('nested_subfolder_files')
            if nsf:
                self._nested_trackers[fn] = ManualHistoryTracker(
                    nsf, self.rng, f"{self.folder_name}_nested_{fn}", self.input_dir
                )
        
        print(f"   {len(self.used_combinations)} combinations loaded from history")
        print(f"   History folder: {self.history_dir}")
    
    def _load_all_combinations(self):
        """Read ALL .txt files in history folder and build set of used combos"""
        all_used = set()
        
        if not self.history_dir.exists():
            print(f"   No history folder found (will skip tracking)")
            return all_used
        
        # Read ALL .txt files
        txt_files = list(self.history_dir.glob("*.txt"))
        if not txt_files:
            print(f"   History folder empty (no .txt files)")
            return all_used
        
        print(f"   Reading {len(txt_files)} history file(s)...")
        
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        
                        # Skip empty lines and headers
                        if not line or line.startswith('[') or line.startswith('='):
                            continue
                        
                        # Check if line is a combination (has F1=, F2=, etc.)
                        if 'F' in line and '=' in line and '|' in line:
                            # Extract just the folder name part if it's in [Folder: ...] format
                            if line.startswith('[') and ']' in line:
                                continue  # Skip section headers
                            
                            # This is a combination line
                            # Check if it matches current folder
                            # Format could be: F1=F1 (22).json|F2=F2 (39).json|F3=F3 (1).json
                            all_used.add(line)
                
                print(f"    [OK] {txt_file.name}: Loaded")
                
            except Exception as e:
                print(f"    [!]?  {txt_file.name}: Error - {e}")
        
        return all_used
    
    def _next_file(self, folder_num):
        """Return the next file from this subfolder's virtual queue.
        Refills and reshuffles when exhausted - no file repeats until all used.
        Boundary guard prevents the last file of one pass from being the first
        of the next pass (cross-boundary consecutive repeat)."""
        q = self._file_queues.get(folder_num)
        if not q:
            pool = list(self.subfolder_files.get(folder_num, {}).get('files', []))
            if not pool:
                return None
            self.rng.shuffle(pool)
            # Boundary guard: if the last item would repeat the previous pick,
            # swap it with a random other position
            last_key = f"_last_{folder_num}"
            last = getattr(self, last_key, None)
            if last is not None and len(pool) > 1 and pool[-1] == last:
                swap = self.rng.randint(0, len(pool) - 2)
                pool[-1], pool[swap] = pool[swap], pool[-1]
            self._file_queues[folder_num] = pool
            q = self._file_queues[folder_num]
        item = q.pop()
        setattr(self, f"_last_{folder_num}", item)
        return item

    def get_next_combination(self):
        """Get next unused combination (with end folder support)"""
        max_attempts = 500
        
        for _ in range(max_attempts):
            # Pick random combination
            combination = []
            for folder_num in sorted(self.subfolder_files.keys()):
                folder_data = self.subfolder_files[folder_num]
                
                # Check for "optional+end" combo (optional folder that ends loop if chosen)
                if folder_data.get('is_optional_end', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() < optional_chance:
                        # Optional/end folder was chosen - include it and STOP
                        _f = self._next_file(folder_num)
                        if _f: combination.append((folder_num, [_f]))
                        break  # End the loop here
                    else:
                        # Optional/end folder was skipped - continue to next folders
                        continue
                
                # Check for regular "end" folder (always included, always ends loop)
                if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                    # End folder - include it and STOP
                    _f = self._next_file(folder_num)
                    if _f: combination.append((folder_num, [_f]))
                    break  # End the loop here
                
                # Regular optional folder check (uses random 27-43% chance stored per folder)
                if folder_data.get('is_optional', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() >= optional_chance:
                        continue
                
                # Nested folder: build sub-combinations instead of picking files
                _nsf = folder_data.get('nested_subfolder_files')
                _max = folder_data.get('max_files', 1)
                _n = self.rng.randint(1, _max) if _max > 1 else 1
                if _nsf and folder_num in self._nested_trackers:
                    _nested_tracker = self._nested_trackers[folder_num]
                    _picked_nested = []
                    for _ in range(_n):
                        _sub_combo = _nested_tracker.get_next_combination()
                        if _sub_combo:
                            _picked_nested.append({
                                '_nested': True,
                                'combo': _sub_combo,
                                'nested_sf': _nsf,
                                'nested_root_af': folder_data.get('nested_root_always_first'),
                                'nested_root_al': folder_data.get('nested_root_always_last'),
                            })
                    if _picked_nested:
                        combination.append((folder_num, _picked_nested))
                else:
                    # Regular folder: pick files from virtual queue
                    _picked = []
                    for _ in range(_n):
                        _f = self._next_file(folder_num)
                        if _f:
                            _picked.append(_f)
                    if _picked:
                        combination.append((folder_num, _picked))
            
            if not combination:
                continue
            
            # Create signature (format folder numbers cleanly)
            signature = "|".join(
                f"F{int(fn) if fn == int(fn) else fn}=" +
                "+".join(fp.name if hasattr(fp, "name") else f"nested_{i}" for i, fp in enumerate(fl if isinstance(fl, list) else [fl]))
                for fn, fl in combination
            )
            
            # Check if unused
            if signature not in self.used_combinations:
                self.used_combinations.add(signature)  # Mark as used
                return combination
        
        # Fallback: return random (may repeat)
        print(f"  [!]?  Using random combination (may repeat)")
        combination = []
        for folder_num in sorted(self.subfolder_files.keys()):
            folder_data = self.subfolder_files[folder_num]
            
            # Handle optional+end
            if folder_data.get('is_optional_end', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() < optional_chance:
                    _f = self._next_file(folder_num)
                    if _f: combination.append((folder_num, [_f]))
                    break
                else:
                    continue
            
            # Handle regular end
            if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                files = folder_data['files']
                _f = self._next_file(folder_num)
                if _f: combination.append((folder_num, [_f]))
                break
            
            # Handle regular optional
            if folder_data.get('is_optional', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() >= optional_chance:
                    continue
            
            _f = self._next_file(folder_num)
            if _f: combination.append((folder_num, [_f]))
        
        return combination if combination else None


class VirtualDistQueue:
    """
    Virtual queue for distraction file selection (Feature 23).
    Works identically to the virtual queue used for macro file selection:
    - All 50 distraction files are shuffled into a queue at construction
    - Files are popped one at a time; no file repeats until ALL have been used
    - When the queue is exhausted it re-shuffles the full pool and starts again
    - Boundary guard: the first item of a new shuffle is never the same as
      the last item of the previous pass, preventing cross-boundary repeats
    - Each shuffle uses the shared rng so order varies per bundle
    """
    def __init__(self, files: list, rng):
        self._pool = list(files)
        self._rng  = rng
        self._queue: list = []
        self._last: object = None
        self._refill()

    def _refill(self):
        self._queue = list(self._pool)
        self._rng.shuffle(self._queue)
        # Prevent cross-boundary consecutive repeat
        if self._last is not None and len(self._queue) > 1 and self._queue[-1] == self._last:
            # Swap the would-be-first item with a random other position
            swap_idx = self._rng.randint(0, len(self._queue) - 2)
            self._queue[-1], self._queue[swap_idx] = self._queue[swap_idx], self._queue[-1]

    def next(self):
        if not self._queue:
            self._refill()
        item = self._queue.pop()
        self._last = item
        return item


def main():
    parser = argparse.ArgumentParser(description="String Macros v3.1.0")
    parser.add_argument("input_root", type=str)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--versions", type=int, default=12, help="Total versions (default: 12 = 3 Raw + 3 Inef + 6 Normal)")
    parser.add_argument("--target-minutes", type=int, default=35)
    parser.add_argument("--bundle-id", type=int, required=True)
    parser.add_argument("--no-chat", action="store_true", help="Disable chat inserts")
    parser.add_argument("--specific-folders", type=str, help="Path to file with specific folder names to include (one per line)")
    args = parser.parse_args()
    
    print("="*70)
    print(f"STRING MACROS v{VERSION}")
    print("="*70)
    print(f"Bundle ID: {args.bundle_id}")
    print(f"Target: {args.target_minutes} minutes per file")
    print(f"Versions: {args.versions} total (3 Raw + 3 Inef + 6 Normal)")
    print(f"Chat: {'DISABLED' if args.no_chat else 'ENABLED (50% chance)'}")
    print("="*70)
    
    # Setup
    search_base = Path(args.input_root).resolve()
    if not search_base.exists():
        print(f"[X] Input root not found: {search_base}")
        return
    
    output_root = Path(args.output_root).resolve()
    bundle_dir = output_root / f"stringed_bundle_{args.bundle_id}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Load chat files
    chat_files = []
    if not args.no_chat:
        chat_dir = Path(args.input_root).parent / "chat inserts"
        if chat_dir.exists() and chat_dir.is_dir():
            chat_files = list(chat_dir.glob("*.json"))
            if chat_files:
                print(f"? Found {len(chat_files)} chat insert files")
    
    # Scan for DISTRACTIONS trigger - accepts either:
    #   A) A folder named "DISTRACTIONS" (case-insensitive) containing >=1 .json
    #   B) A single file named "distraction_file.json" (or similar) at root level
    # Either presence activates the feature; the trigger content is irrelevant.
    distractions_src = None

    # Option A: folder-based trigger (original behaviour)
    for candidate in [search_base / "DISTRACTIONS",
                       search_base / "distractions",
                       search_base / "Distractions"]:
        if candidate.exists() and candidate.is_dir():
            distractions_src = candidate
            break
    if distractions_src is None:
        for candidate in [search_base.parent / "DISTRACTIONS",
                           search_base.parent / "distractions"]:
            if candidate.exists() and candidate.is_dir():
                distractions_src = candidate
                break

    # Option B: single trigger file at root level
    # Any .json file whose name contains "distraction" (case-insensitive) works
    if distractions_src is None:
        for candidate_dir in [search_base, search_base.parent]:
            for f in candidate_dir.glob("*.json"):
                if "distraction" in f.name.lower():
                    distractions_src = f.parent   # treat parent as the trigger dir
                    break
            if distractions_src:
                break

    if distractions_src:
        trigger_files = list(distractions_src.glob("*.json")) if distractions_src.is_dir() else []
        if not distractions_src.is_dir():
            # single-file trigger: src is the parent folder, just confirm the file is there
            trigger_files = [f for f in distractions_src.iterdir()
                             if f.suffix == '.json' and 'distraction' in f.name.lower()]
        if trigger_files:
            print(f"? Distraction trigger found - 50 distraction files will be generated")
        else:
            print(f"  Distraction trigger found but empty - feature disabled")
            distractions_src = None
    else:
        print(f"  No distraction trigger found - distraction generation disabled")
    
    # Look for logout file
    logout_file = None
    logout_patterns = ["logout.json", "- logout.json", "-logout.json", "logout", "- logout", "-logout"]
    for location_dir in [search_base, search_base.parent]:
        if logout_file:
            break
        for pattern in logout_patterns:
            test_file = location_dir / pattern
            for test_path in [test_file, Path(str(test_file) + ".json")]:
                if test_path.exists() and test_path.is_file():
                    logout_file = test_path
                    print(f"? Found logout file: {logout_file.name}")
                    break
    
    print()
    
    # Scan folders
    main_folders = []
    for folder in search_base.iterdir():
        if not folder.is_dir():
            continue

        # Skip the DISTRACTIONS source folder - it is not a macro folder,
        # only the generated output copy goes into the bundle.
        if folder.name.lower() == 'distractions':
            continue
        
        numbered_subfolders, dmwm_file_set, non_json_files, root_always_first, root_always_last = scan_for_numbered_subfolders(folder)
        
        # Add dmwm files to the appropriate numbered folder
        for dmwm_file in dmwm_file_set:
            # Try to determine which numbered folder it should belong to
            # For now, add to a special '0' key or just include in general pool
            if 0 not in numbered_subfolders:
                numbered_subfolders[0] = []
            numbered_subfolders[0].append(dmwm_file)
        
        if numbered_subfolders:
            main_folders.append({
                'path': folder,
                'name': folder.name,
                'root_always_first': root_always_first,
                'root_always_last': root_always_last,
                'subfolders': numbered_subfolders,
                'dmwm_files': dmwm_file_set,
                'non_json': non_json_files
            })
            print(f"? Found: {folder.name}")
            if numbered_subfolders:
                nums = sorted([k for k in numbered_subfolders.keys() if k != 0])
                print(f"  Subfolders: {nums}")
                
                # Show special folder types
                special_folders = []
                for num in nums:
                    if num in numbered_subfolders:
                        folder_info = numbered_subfolders[num]
                        if folder_info.get('is_optional_end'):
                            special_folders.append(f"{num} (optional+end)")
                        elif folder_info.get('is_end'):
                            special_folders.append(f"{num} (end)")
                        elif folder_info.get('is_optional'):
                            special_folders.append(f"{num} (optional)")
                        
                        # Also mark time_sensitive folders
                        if folder_info.get('is_time_sensitive'):
                            special_folders.append(f"{num} (time sensitive)")
                
                if special_folders:
                    print(f"  Special: {', '.join(special_folders)}")
            if dmwm_file_set:
                print(f"  Unmodified: {len(dmwm_file_set)} files (added to pool)")
            if non_json_files:
                print(f"  Non-JSON: {len(non_json_files)} files")
    
    if not main_folders:
        print("[X] No folders with numbered subfolders found!")
        return
    
    # Filter by specific folders (and optionally specific subfolders) if provided
    # File format (one entry per line):
    #   FolderName                     -> include that folder, ALL its subfolders
    #   FolderName: F1, F3, F4         -> include that folder, ONLY listed subfolders
    #   FolderName: F1, F3-F5          -> include that folder, subfolders F1 and F3..F5 range
    # Matching is case-insensitive and whitespace-stripped.
    if args.specific_folders:
        try:
            with open(args.specific_folders, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            # Parse lines — each line is either "FolderName" or "FolderName: F1, F2"
            # GitHub Actions may collapse newlines; handle commas-as-separators only
            # when there is NO colon present (legacy behaviour).
            entries = {}   # {folder_name_lower: set_of_subfolder_nums_or_None}
            for raw_line in raw_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if ':' in line:
                    # "FolderName: F1, F2, F3" — split on first colon only
                    folder_part, sf_part = line.split(':', 1)
                    folder_key = folder_part.strip().lower()
                    # Parse subfolder numbers from "F1, F2, F3-F5" etc.
                    sf_nums = set()
                    for tok in re.split(r'[,\s]+', sf_part.strip()):
                        tok = tok.strip()
                        if not tok:
                            continue
                        # Range: F3-F5 (note: only meaningful if written as "F3-F5" not "F3,F5")
                        range_m = re.match(r'^[Ff]?(\d+(?:\.\d+)?)-[Ff]?(\d+(?:\.\d+)?)$', tok)
                        if range_m:
                            lo, hi = float(range_m.group(1)), float(range_m.group(2))
                            # Add all integer steps between lo and hi
                            v = lo
                            while v <= hi + 0.001:
                                sf_nums.add(round(v, 4))
                                v += 1.0
                        else:
                            # Single: F1, F3, 2, 3.5
                            single_m = re.match(r'^[Ff]?(\d+(?:\.\d+)?)$', tok)
                            if single_m:
                                sf_nums.add(float(single_m.group(1)))
                    entries[folder_key] = sf_nums if sf_nums else None
                else:
                    # No colon — legacy comma-separated folder names (no subfolder filter)
                    for name in line.replace(',', '\n').splitlines():
                        name = name.strip()
                        if name:
                            entries[name.lower()] = None  # None = all subfolders

            if entries:
                print(f"\n Filtering to specific folders only:")
                for name, sfs in entries.items():
                    sf_str = f" (subfolders: {sorted(sfs)})" if sfs else " (all subfolders)"
                    print(f"  - {name}{sf_str}")

                filtered_folders = []
                for folder_data in main_folders:
                    key = folder_data['name'].lower()
                    if key in entries:
                        sf_filter = entries[key]
                        if sf_filter:
                            # Keep only the requested numbered subfolders
                            original_subs = folder_data['subfolders']
                            filtered_subs = {}
                            for num, data in original_subs.items():
                                if round(num, 4) in sf_filter or num == 0:
                                    # Force-include: strip optional/end so it always runs
                                    forced = dict(data)
                                    forced['is_optional']     = False
                                    forced['is_end']          = False
                                    forced['is_optional_end'] = False
                                    filtered_subs[num] = forced
                            if not filtered_subs:
                                print(f"  [!] No matching subfolders found in '{folder_data['name']}'")
                                print(f"      Requested: {sorted(sf_filter)}")
                                print(f"      Available: {sorted(k for k in original_subs if k != 0)}")
                                continue
                            # Clone folder_data with filtered+forced subfolders
                            filtered_fd = dict(folder_data)
                            filtered_fd['subfolders'] = filtered_subs
                            filtered_folders.append(filtered_fd)
                        else:
                            filtered_folders.append(folder_data)

                if not filtered_folders:
                    # Fallback: search by subfolder name (no colon needed)
                    # If the written name matches a subfolder folder_name, auto-promote it
                    for folder_data in main_folders:
                        for sf_num, sf_data in folder_data['subfolders'].items():
                            sf_name = sf_data.get('folder_name', '')
                            if sf_name.lower() in entries:
                                print(f"  [->] '{sf_name}' matched as subfolder of '{folder_data['name']}'")
                                # Build a synthetic main_folder from this single subfolder
                                # Force always-included (strip optional/end tags)
                                forced_sf = dict(sf_data)
                                forced_sf['is_optional']     = False
                                forced_sf['is_end']          = False
                                forced_sf['is_optional_end'] = False
                                forced_sf['max_files']       = 1  # ignored — nested handles loops

                                nsf = sf_data.get('nested_subfolder_files')
                                if nsf:
                                    # Nested: promote inner structure as top-level
                                    synthetic = {
                                        'path': sf_data.get('folder_path', folder_data['path']),
                                        'name': sf_name,
                                        'root_always_first': sf_data.get('nested_root_always_first'),
                                        'root_always_last':  sf_data.get('nested_root_always_last'),
                                        'subfolders': nsf,
                                        'dmwm_files': folder_data.get('dmwm_files', set()),
                                        'non_json':   folder_data.get('non_json', []),
                                    }
                                else:
                                    # Regular subfolder: treat as flat/single-subfolder folder
                                    synthetic = {
                                        'path': sf_data.get('folder_path', folder_data['path']),
                                        'name': sf_name,
                                        'root_always_first': sf_data.get('always_first'),
                                        'root_always_last':  sf_data.get('always_last'),
                                        'subfolders': {sf_num: forced_sf},
                                        'dmwm_files': folder_data.get('dmwm_files', set()),
                                        'non_json':   folder_data.get('non_json', []),
                                    }
                                filtered_folders.append(synthetic)

                if not filtered_folders:
                    print(f"\n[X] None of the specified folders were found!")
                    print(f"   Looking for: {list(entries.keys())}")
                    print(f"   Available main folders: {[f['name'] for f in main_folders]}")
                    print(f"   TIP: You can also write a subfolder name directly:")
                    print(f"     F0.5 optional-7- CAM2       <- auto-found inside any main folder")
                    print(f"   Or use colon format to specify parent:")
                    print(f"     22- Craft Dia: F0.5         <- explicit parent + subfolder")
                    sys.exit(1)

                main_folders = filtered_folders
                print(f"[OK] Filtered to {len(main_folders)} folder(s)")
            else:
                print(f"\n[!]?  Specific folders file is empty, processing ALL folders")
        
        except FileNotFoundError:
            print(f"\n[X] Specific folders file not found: {args.specific_folders}")
            return
        except Exception as e:
            print(f"\n[X] Error reading specific folders file: {e}")
            return
    
    print(f"\n Total folders to process: {len(main_folders)}")
    print("="*70)
    
    # Initialize global chat queue
    rng = random.Random(args.bundle_id * 42)
    global_chat_queue = list(chat_files) if chat_files else []
    if global_chat_queue:
        rng.shuffle(global_chat_queue)
        print(f" Initialized global chat queue with {len(global_chat_queue)} files")
        print()
    
    # Track ALL combinations for the bundle (one file at root level)
    bundle_combinations = {}  # {folder_name: [combination_signatures]}

    # Generate DISTRACTIONS now (before folder loop) so files are available
    # for inline insertion during stringing.
    # Files are written to a TEMP folder (not inside the bundle) - they are used
    # only as in-memory splice sources and are NOT included in the final output.
    import tempfile as _tempfile
    _dist_tmpdir = None
    distraction_files = []   # list of Path objects to pick from during stringing
    dist_queue = None        # VirtualDistQueue - cycles through all files before repeating
    if distractions_src:
        print("\n" + "="*70)
        print(" Generating DISTRACTION files (inline splice only, not saved to bundle)...")
        _dist_tmpdir = _tempfile.mkdtemp(prefix="string_macros_dist_")
        dist_tmp = Path(_dist_tmpdir) / "distractions"
        n_written = generate_distraction_files(distractions_src, dist_tmp, rng, count=50, bundle_id=args.bundle_id)
        print(f"  [OK] Generated {n_written} distraction files (virtual queue: no repeats until all used)")
        distraction_files = sorted(dist_tmp.glob("*.json"))
        dist_queue = VirtualDistQueue(distraction_files, rng)

    # Process each folder
    for folder_data in main_folders:
        folder_name = folder_data['name']
        subfolder_files = folder_data['subfolders']
        dmwm_file_set = folder_data['dmwm_files']
        non_json_files = folder_data['non_json']
        root_always_first = folder_data.get('root_always_first')
        root_always_last  = folder_data.get('root_always_last')

        # Per-folder distraction insertion chances (float decimal, drawn once per folder):
        # - Normal files:      7.0-10.0%  (tighter window, more controlled)
        # - Inefficient files: 7.0-14.0%  (wider window, more varied)
        # - Raw files:         0%          (never)
        folder_dist_chance_normal = rng.uniform(3.5,  5.0) / 100.0 if distraction_files else 0.0
        folder_dist_chance_inef   = rng.uniform(3.5,  7.0) / 100.0 if distraction_files else 0.0
        
        # D_ REMOVAL
        cleaned_folder_name = re.sub(r'[Dd]_', '', folder_name)
        
        # Extract folder number
        folder_num_match = re.search(r'\d+', cleaned_folder_name)
        folder_number = int(folder_num_match.group()) if folder_num_match else 0
        
        
        # Create output folder - append bundle ID in specific folders mode
        output_folder_name = cleaned_folder_name
        if args.specific_folders:
            output_folder_name = f"({args.bundle_id}) {cleaned_folder_name}"
        print(f"\n Processing: {output_folder_name}")
        out_folder = bundle_dir / output_folder_name
        out_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy logout file with @ prefix
        if logout_file:
            try:
                original_name = logout_file.name
                if original_name.startswith("-"):
                    new_name = f"@ {folder_number} {original_name[1:].strip()}".upper()
                else:
                    new_name = f"@ {folder_number} {original_name}".upper()
                shutil.copy2(logout_file, out_folder / new_name)
                print(f"  ? Copied logout: {new_name}")
            except Exception as e:
                print(f"  ? Error copying logout: {e}")
        
        # Copy non-JSON files with @ prefix
        for non_json_file in non_json_files:
            try:
                original_name = non_json_file.name
                if original_name.startswith("-"):
                    new_name = f"@ {folder_number} {original_name[1:].strip()}"
                else:
                    new_name = f"@ {folder_number} {original_name}"
                shutil.copy2(non_json_file, out_folder / new_name)
                print(f"  ? Copied non-JSON: {new_name}")
            except Exception as e:
                print(f"  ? Error copying {non_json_file.name}: {e}")
        
        if not subfolder_files:
            print("  [!]?  No numbered subfolders to process")
            continue
        
        # Use bundle-organized tracker
        tracker = ManualHistoryTracker(
            subfolder_files, rng, cleaned_folder_name, search_base
        )
        target_ms = args.target_minutes * 60000
        
        # Track all combinations used in THIS RUN for this folder
        folder_combinations_used = []
        
        # Calculate total original duration
        # Detect "copied" subfolders: subfolders whose file-name sets are identical
        # (e.g. F1-mine and F2-mine with same files). Count their files only once
        # so the duration reflects unique content, not duplicated repetitions.
        # Count each unique filename only once across ALL subfolders.
        # Copied folders (F1-mine, F2-mine) may share file names - count once.
        _seen_filenames = set()   # filenames already counted (by name, not path)
        total_original_files = 0
        total_original_ms = 0
        # Count subfolders whose *entire* file-name set is a duplicate of another
        _seen_filesets = []
        num_copied_folders = 0

        for _subfolder_data in subfolder_files.values():
            files = _subfolder_data['files']
            fileset = frozenset(f.name for f in files)
            if fileset in _seen_filesets:
                num_copied_folders += 1   # whole subfolder is a copy
            else:
                _seen_filesets.append(fileset)
            # Always count individual files that haven't been seen by name yet
            for f in files:
                if f.name not in _seen_filenames:
                    _seen_filenames.add(f.name)
                    total_original_files += 1
                    total_original_ms += get_file_duration_ms(f)

        
        # Build subfolder file count lines for manifest
        _subfolder_lines = []
        for _fn in sorted(subfolder_files.keys()):
            _fd = subfolder_files[_fn]
            _fn_label = str(int(_fn) if _fn == int(_fn) else _fn)
            _file_count = len(_fd.get('files', []))
            _always_note = ""
            if _fd.get('always_first'): _always_note += " + always_first"
            if _fd.get('always_last'):  _always_note += " + always_last"
            _subfolder_lines.append(f"  F{_fn_label}: {_file_count} file(s){_always_note}")

        # Manifest header
        manifest_lines = [
            f"MANIFEST FOR FOLDER: {cleaned_folder_name}",
            "=" * 40,
            f"Script Version: {VERSION}",
            f"Stringed Bundle: stringed_bundle_{args.bundle_id}",
            f"Total Original Files: {total_original_files}",
            (f"Total Original Files Duration: {format_ms_precise(total_original_ms)} ({num_copied_folders} copied folder(s))"
             if num_copied_folders > 0
             else f"Total Original Files Duration: {format_ms_precise(total_original_ms)}"),
        ] + _subfolder_lines + [""]
        
        # Check if any folders are 'time sensitive' (no inefficient files)
        has_time_sensitive = any(
            folder_data.get('is_time_sensitive', False) 
            for folder_data in subfolder_files.values()
        )
        
        # Debug: Show which folders are time_sensitive
        if has_time_sensitive:
            time_sensitive_folders = [
                str(int(num) if num == int(num) else num)
                for num, data in subfolder_files.items() 
                if data.get('is_time_sensitive', False)
            ]
            print(f"  ??  TIME SENSITIVE folders detected: {', '.join(time_sensitive_folders)}")
        
        # Version loop: 3 Raw + 3 Inef + 6 Normal = 12 total
        # OR: 3 Raw + 0 Inef + 9 Normal = 12 total (if time_sensitive)
        def get_version_letter(idx):
            """
            Generate version letter for any index, repeating letters after Z.
            0=A, 1=B, ..., 25=Z, 26=AA, 27=BB, ..., 51=ZZ, 52=AAA, etc.
            """

# ============================================================================
#  IMPORTANT REMINDER FOR AI/HUMAN EDITORS:
# ============================================================================
"""
[!]?  WHEN YOU MODIFY ANY FEATURE IN THIS CODE:

1. UPDATE THE FEATURE DOCUMENTATION BELOW (Lines 40-230)
   - Change the description
   - Update percentages/values
   - Update code line numbers
   - Update status if feature is disabled/enabled

2. UPDATE THE VERSION NUMBER ABOVE
   - Increment version (e.g., v3.12.0 -> v3.12.1)
   - Add change note in header

3. UPDATE THE MANIFEST OUTPUT (Lines ~1970-2030)
   - Ensure new features show in breakdown
   - Update pause calculations if changed

4. CHECK FOLDER/FILE TAG DETECTION (Lines ~1330-1350)
   - If adding new tags, document them below

This ensures the documentation stays accurate and users know what features exist!
"""

import argparse, json, random, re, sys, os, math, shutil, itertools
from pathlib import Path

VERSION = "v3.18.65"

# ============================================================================
# FEATURE DOCUMENTATION - ORGANIZED BY PURPOSE
# ============================================================================
"""
===========================================================================
                     DETECTED FOLDER & FILE TAGS
===========================================================================

FOLDER TAGS (detected in folder name, case-insensitive):
  - "optional"        -> Folder has 24-33% chance to be included per run
  - "end"             -> Folder becomes definitive loop endpoint (stops after)
  - "optional+end"    -> Combination: optional folder that ends loop IF chosen
  - "time sensitive"  -> No inefficient files generated (replaced with normal files)
                        Can be applied to:
                        - Main folder -> ALL subfolders become time_sensitive
                        - Individual subfolders -> Only that subfolder is time_sensitive
  - (Decimal support: "3.5" goes between folders 3 and 4)

FILE TAGS (detected in filename, case-insensitive):
  - "always first" or "alwaysfirst"  -> File always plays first in its folder
  - "always last" or "alwayslast"    -> File always plays last in its folder

SPECIAL FOLDER (exact name match, case-insensitive):
  - "Don't use features on me" -> Files inserted unmodified (no features applied)
  - (Also accepts old name "dont mess with me" for backward compatibility)

===========================================================================
                    GROUP 1: PAUSE BREAKS (Anti-Detection Timing)
===========================================================================

These features add natural pauses and delays to prevent robotic timing patterns.

1. WITHIN FILE PAUSES
   Status: [OK] ACTIVE (Normal and Inefficient files only)
   Old Name: "Intra-file pauses"
   What: A single pause inserted at a safe point inside each individual file.
         Duration is a PERCENTAGE of that file's own play time - so longer files
         get proportionally longer pauses.
   Values by File Type:
     - Raw:         0%  - no pause inserted
     - Normal:      5%  - e.g. 20s file -> 1.0s pause
     - Inefficient: 15% - e.g. 20s file -> 3.0s pause
   Safe Location: Middle 80% of file only; never inside drag sequences, never
                  inside rapid-click sequences, never immediately before DragStart.
   Duration: float ms (no rounding) = file_duration_ms x percentage
   Purpose: Natural hesitation that scales with file length
   Code: insert_intra_file_pauses() with file_type parameter
   Manifest: "Within File Pauses: Xm Xs"

2. PRE-PLAY BUFFER
   Status: [OK] ACTIVE (Always, all file types)
   Old Name: "Pre-file pauses"
   What: Fixed pause BEFORE each file starts playing
   Duration: 800ms (0.8 seconds) - FLAT, NO multiplier, NO randomization
   When: Applied BEFORE cursor movement (click release protection)
   Purpose: Ensures clicks from previous file are fully released
   Code: Line ~1376-1384 (pre_file_pause)
   Total Impact: ~2m 40s per 50-minute output (200 files x 800ms)
   Manifest: "PRE-Play Buffer: Xm Xs"
   Order: PRE-pause -> Cursor transition -> File plays

3. INEFFICIENT BEFORE FILE PAUSE
   Status: [OK] ACTIVE (Inefficient files ONLY, file >= 25 seconds)
   Old Name: "Before File Pause" or "Inter-file pauses" or "Between cycles pause"
   What: Longer pause between complete action cycles
   Duration: 10-30 seconds (10000-30000ms, random, NOT rounded, NO multiplier)
   File Length Check: Only applied if file duration >= 25 seconds
   File Types:
     - Raw: [X] DISABLED
     - Inefficient: [OK] ACTIVE (if file >= 25s)
     - Normal: [X] DISABLED
   Purpose: Major break between action sequences
   Code: Line ~2084-2093 (inter_cycle_pause with file length check)
   Manifest: "INEFFICIENT Before File Pause: Xm Xs"


5. INEFFICIENT MASSIVE PAUSE
   Status: [OK] ACTIVE (Inefficient files ONLY)
   Old Name: "Massive pause"
   What: One random pause inserted at safe location
   Duration: 4-7 minutes (240000-420000ms, random, NOT rounded) x multiplier
   Examples: x2.0 = 8-14 min | x3.0 = 12-21 min
   Safe Location Detection: EXCLUDES pause from:
     - Drag sequences (between DragStart and DragEnd)
     - Rapid click sequences (double-clicks, spam clicks)
     - First/last 10% of file (for safety)
     - Immediately BEFORE DragStart events (FIX v3.15.2)
   Where: Random safe point in middle 80% of file
   File Types:
     - Raw: [X] NOT USED
     - Inefficient: [OK] INSERTED
     - Normal: [X] NOT USED
   Purpose: Simulates AFK/distracted behavior
   Code: Line ~1171-1220 (insert_massive_pause with drag protection)
   Manifest: "INEFFICIENT MASSIVE PAUSE: Xm Xs"
   
   BUG FIX (v3.15.2): Added check to prevent pause insertion immediately before
   DragStart events. Previously, pauses could be inserted right before DragStart,
   which shifted the DragEnd forward in time, making clicks appear to last 1-4
   seconds instead of <150ms, causing drag/clamp issues.

6. MULTIPLIER SYSTEM
   Status: [OK] ACTIVE (Always)
   What: Scales all pause durations by multiplier value
   Values by File Type (UPDATED v3.13.0):
     Raw Files:
       - x1.0 (50% probability)
       - x1.1 (50% probability)
     
     Normal Files:
       - x1.3 (65% probability)
       - x1.5 (35% probability)
     
     Inefficient Files:
       - x2.0 (60% probability)
       - x3.0 (40% probability)
   
   Purpose: Varied timing patterns across output files
   Code: Line ~1918-1927 (multiplier selection)
   Manifest: "(xN Multiplier)" shown in each file header

===========================================================================
              GROUP 2: PATTERN BREAKING (Anti-Detection Variance)
===========================================================================

These features add variation and unpredictability to prevent detectable patterns.

1. CURSOR TO START POINT
   Status: [OK] ACTIVE (Skipped for click-sensitive folders)
   Old Name: "Cursor transitions"
   What: Smooth cursor movement from file end position to next file start
   Duration: 200-400ms per transition (varies by path style)
   Path Styles (random per transition):
     - Efficient: Direct path, few curves, faster
     - Swift: Very fast, straight line
     - Meandering: Curved path, more wandering
     - Hesitant: Slow start, acceleration, deceleration
   Speed Variations: Very fast (100-200ms) to Very slow (700-1000ms)
   Purpose: No mouse teleportation; realistic cursor flow with variety
   Code: Line ~498-576 (generate_human_path with path styles)
   Impact: Adds ~30-35s to 50-minute output
   Manifest: "CURSOR to Start Point: Xm Xs"
   Note: This DOES add time to total duration (intentional)

2. IDLE CURSOR WANDERING
   Status: [OK] ACTIVE (Always, during pauses > 1s)
   Old Name: "Idle mouse movements"
   What: Small random mouse wiggles during long pauses
   When: Any pause > 1 second
   Pattern: Smooth Bezier curves, realistic speed
   Purpose: Cursor doesn't stay frozen during waits
   Code: Line ~702-793 (add_idle_movements)
   Impact: ~7-11 minutes "movement time" per 50-min output
   Manifest: "Idle Mouse Movements: Xm Xs"
   Note: This does NOT extend file duration (happens during existing pauses)

3. MOUSE JITTER
   Status: [OK] ACTIVE (9-21% of movements, with exclusions)
   What: Random small offsets to cursor positions
   Percentage: 9-21% of all mouse movements get jittered
   Amount: Small random offset per movement
   Exclusion Zones (NO JITTER):
     - 1000ms before/after any click
     - 1500ms for rapid click sequences (3+ clicks in 1500ms)
     - During drag operations (hold + move + release)
   Purpose: Natural hand tremor, but maintains click accuracy
   Code: Line ~669-677 (apply_smart_jitter)
   Protection: Line ~552-589 (detect rapid clicks)
   Note: DISABLED near clicks to prevent off-target clicks
   Manifest: "Mouse Jitter: XX%"

4. RANDOM FILE QUEUE
   Status: [OK] ACTIVE (Always)
   What: Files selected randomly from each folder per cycle
   Method: Random choice from available files
   Avoids: Repeating same folder combination (via history)
   Purpose: No predictable file order
   Code: Line ~1475 (rng.choice for file selection)
   Manifest: File order visible in manifest list

===========================================================================
            GROUP 3: ENSURING SMOOTH OPERATION (Reliability)
===========================================================================

These features ensure files play correctly without breaking or causing errors.

1. RAPID CLICK PROTECTION
   Status: [OK] ACTIVE (Always)
   What: Detects rapid click sequences and extends jitter exclusion zones
   Detection: 3+ clicks within 1500ms
   Protection: Extends exclusion from 1000ms -> 1500ms
   Purpose: Prevents jitter from breaking rapid action sequences
   Code: Line ~552-589 (detect_rapid_click_sequences)

2. DRAG OPERATION PROTECTION
   Status: [OK] ACTIVE (Always)
   What: Detects drag operations and prevents jitter during them
   Detection: Hold + Move + Release patterns
   Protection: NO jitter during entire drag sequence
   Purpose: Maintains drag accuracy
   Code: Line ~596-628 (detect_drag_operations)

3. EVENT TIMING INTEGRITY PROTECTION
   Status: [OK] ACTIVE (Always, all time-adding features)
   What: Prevents pauses/modifications from interfering with drag/click timing
   Protection Zones (NO time modification):
     - Between DragStart and DragEnd pairs
     - Immediately BEFORE DragStart events
     - Within rapid click sequences
     - First/last 10% of file
   Impact: Maintains click responsiveness (<200ms), prevents drag/clamp issues
   Purpose: CRITICAL protection to prevent clicks being held 1-4 seconds
   Code: Line ~1171-1220 (insert_massive_pause with protection)
   Added: v3.15.2 (bug fix for click timing)

4. COMBINATION HISTORY
   Status: [OK] ACTIVE (Always)
   What: Tracks which folder combinations have been used
   Prevents: Repeating same combination across cycles
   Tracking: "F1=file01.json|F2=file05.json|F3=file12.json"
   File: COMBINATION_HISTORY_XX.txt (created per bundle)
   Purpose: Maximum variety across runs
   Code: Line ~1380-1510 (ManualHistoryTracker class)

5. MANUAL HISTORY UPLOAD
   Status: [OK] ACTIVE (If files present)
   What: Upload old combination files to avoid repeating them
   Location: input_macros/combination_history/
   Reads: All .txt files automatically
   Purpose: Never repeat across multiple runs/sessions
   Code: Line ~1410-1450 (load history from folder)

6. ALPHABETICAL NAMING
   Status: [OK] ACTIVE (Always)
   What: Organized naming convention for output files
   Pattern:
     Raw files:        ^XX_A, ^XX_B, ^XX_C
     Inefficient:      XX_D, XX_E, XX_F (with special prefix)
     Normal:           XX_G, XX_H, XX_I, XX_J, XX_K, XX_L
   Purpose: Easy identification of file type at a glance
   Code: Line ~1940-1980 (filename generation)

7. FOLDER-NUMBER BASED STRUCTURE
   Status: [OK] ACTIVE (Always, supports decimals)
   Old Name: "Folder-based structure"
   What: Folders numbered in sequence; files cycle through them
   Format: "1- action/", "2- bank/", "3.5- optional/", "4- continue/"
   Decimal Support: 3.5 goes after 3 and before 4
   Pattern: F1 -> F2 -> F3 -> F3.5 -> F4 -> F1 -> ...
   Purpose: Maintains sequential action steps
   Code: Line ~1318-1360 (folder number extraction & sorting)

8. 'OPTIONAL' TAGGED FOLDERS
   Status: [OK] ACTIVE (If "optional" in folder name)
   Old Name: "Optional folders"
   Tag Detection: "optional" anywhere in folder name (case-insensitive)
   Behavior: Folder has random chance to be included in each cycle
   Chance (default): 24.0-33.0% random float range (rolled once per bundle, consistent within bundle)
   Custom Chance: Append a number directly to the tag to override the default
     - "optional50%"   -> exactly 50% chance
     - "optional50.5"  -> exactly 50.5% chance  ? decimals supported
     - "optional33.3"  -> exactly 33.3% chance  ? decimals supported
     - "optional10"    -> exactly 10% chance
     - "optional75"    -> exactly 75% chance
     - "optional"      -> default 24.0-33.0% range (no number = use default)
     The number (integer OR decimal) is parsed from the tag; spaces, dashes, and % are ignored.
   Examples:
     "3 optional- bank early/"           -> default 24.0-33.0% chance
     "3 optional50- bank early/"         -> exactly 50.0% chance
     "3 optional50.5- bank early/"       -> exactly 50.5% chance
     "3 optional50%- bank early/"        -> exactly 50.0% chance
     "3 optional10- rare action/"        -> exactly 10.0% chance
   Purpose: Unpredictable action path variations with per-folder probability control
   Code: Line ~1442 (is_optional detection + parse_optional_chance())

9. 'END' TAGGED FOLDERS
   Status: [OK] ACTIVE (If "end" in folder name)
   Tag Detection: "end" anywhere in folder name (case-insensitive)
   Behavior: Folder becomes definitive loop endpoint (stops after)
   Example: "5 end- logout/"
   Purpose: Controlled endpoint timing
   Code: Line ~1347 (is_end detection)

10. 'OPTIONAL+END' COMBO TAGGED FOLDERS
    Status: [OK] ACTIVE (If both "optional" and "end" in name)
    Tag Detection: Both "optional" AND "end" in folder name
    Behavior: 
      - Chance to include folder (same custom % syntax as Feature 8)
      - IF included: Loop stops at this folder
      - IF skipped: Loop continues to next folders
    Examples:
      "3.5 optional+end- early bank/"      -> default 24.0-33.0% chance
      "3.5 optional50/end- early bank/"    -> exactly 50.0% chance
      "3.5 optional50.5/end- early bank/" -> exactly 50.5% chance
    Purpose: Sometimes end early, sometimes continue full loop
    Code: Line ~1448-1462 (is_optional_end handling)

11. 'TIME SENSITIVE' TAGGED FOLDERS
    Status: [OK] ACTIVE (If "time sensitive" in folder name)
    New Feature: v3.13.0 | Enhanced: v3.14.2 | Ratio updated: v3.18.32
    Tag Detection: "time sensitive" anywhere in folder name (case-insensitive)
    Behavior: NO inefficient files generated; 1:1 raw:normal ratio
    
    Two Application Modes:
      A) MAIN FOLDER TAGGED:
         Example: "61- Mining TIME SENSITIVE/"
                    ??? 1- setup/
                    ??? 2- mine/
                    ??? 3- bank/
         Result: ALL subfolders (1, 2, 3) become time_sensitive
         
      B) INDIVIDUAL SUBFOLDER TAGGED:
         Example: "61- Mining/"
                    ??? 1- setup/
                    ??? 2 time sensitive- mine/  ? Only this one
                    ??? 3- bank/
         Result: Only subfolder 2 is time_sensitive
    
    File Distribution Changes:
      - Regular folder: 2 Raw + 3 Inef + 7 Normal = 12 files (2:3:7 ratio)
      - Time sensitive: 6 Raw + 0 Inef + 6 Normal = 12 files (1:1 ratio)
    
    Priority: Main folder tag overrides individual subfolder tags
    Purpose: Activities requiring consistent timing (combat, PvP, timed tasks)
    Code: scan_for_numbered_subfolders() - main_folder_time_sensitive propagation
    Note: Entire bundle affected if ANY folder is time_sensitive

26. 'CLICK SENSITIVE' TAGGED FOLDERS
    Status: [OK] ACTIVE (If "click sensitive" in folder name)
    Added: v3.18.32 | Fixed propagation: v3.18.39
    Tag Detection: "click sensitive" anywhere in folder or main folder name (case-insensitive)
    Behavior: ALL coordinate-changing features are disabled for this folder.
    Features DISABLED when click-sensitive:
      - Cursor transition path between files (no human-path movements)
      - Mouse jitter (no random coord offsets)
      - Idle cursor wandering (no movements during pauses)
      - Distraction file insertion (distractions also move the cursor)
    Features STILL ACTIVE:
      - Within-file pauses (time-based, no coord changes)
      - Pre-play buffer (timing only)
      - Rapid click detection / drag protection
    
    Two Application Modes:
      A) MAIN FOLDER TAGGED:
         Example: "18- WC- draynor CLICK SENSITIVE/"
         Result: ALL subfolders skip coordinate-changing features
      B) INDIVIDUAL SUBFOLDER TAGGED:
         Example: "18- WC- draynor/"
                    ??? 2 click sensitive- click tree/
         Result: Only subfolder 2 is click-sensitive
    
    Accepted tag variants (all case-insensitive):
      "click sensitive", "click/time sensitive", "click+time sensitive"
    Purpose: Activities where cursor must stay at exact recorded coordinates
             (e.g. fishing spots, precise clicks, inventory management)
    Code: scan_for_numbered_subfolders(), apply_cycle_features(), string_cycle()

27. 'CLICK/TIME SENSITIVE' COMBO TAG
    Status: [OK] ACTIVE (Combines both tag rules)
    Added: v3.18.32
    Tag Detection: "click/time sensitive", "click+time sensitive", or
                   "click time sensitive" in folder name (case-insensitive)
    Behavior: Activates BOTH click-sensitive AND time-sensitive rules simultaneously:
      - 1:1 raw:normal ratio (no inefficient files) - from time sensitive
      - No cursor pathing, jitter, idle wandering, distractions - from click sensitive
    Example: "Fishing experimental- click+time sensitive/"
    Purpose: Precision timing activities where coordinates must also be exact

12. 'DON'T USE FEATURES ON ME' TAGGED FOLDERS
    Status: [OK] ACTIVE (If folder name matches)
    Old Name: "DMWM Support" or "dont mess with me"
    Tag Detection: Exact match "Don't use features on me" (case-insensitive)
    Backward Compatible: Also accepts old name "dont mess with me"
    Behavior: Files from this folder inserted completely unmodified
    Features Skipped: NO jitter, NO pauses, NO modifications
    Marked In Manifest: "[UNMODIFIED] filename.json"
    Purpose: Include specific pre-made sequences as-is
    Code: Line ~1433-1441 (folder detection)

13. ALWAYS FIRST/LAST FILES
    Status: [OK] ACTIVE (If tagged in filename)
    Tag Detection: "always first", "alwaysfirst", "always last", "alwayslast"
    Location: In filename (case-insensitive)
    
    Two Modes (auto-detected by folder structure):
    
      A) MULTI-SUBFOLDER MODE (2+ numbered subfolders):
         Original behaviour. always_first/last wrap every selected file, every cycle.
         Pattern per file slot: [ALWAYS FIRST] -> selected file -> [ALWAYS LAST]
         Use case: Opener/closer needed around each action step (e.g. login per step)
    
      B) SINGLE-SUBFOLDER MODE (1 subfolder OR flat folder):
         always_first plays once at the very beginning of the strung file.
         always_last plays once at the very end of the strung file.
         All selected files play in sequence in between.
         Pattern: [ALWAYS FIRST] -> file1 -> file2 -> file3 -> ... -> [ALWAYS LAST]
         Use case: Global opener/closer (e.g. login once, do N actions, logout once)
    
    Examples:
      "setup_always_first.json"   -> plays at start
      "cleanup_alwayslast.json"   -> plays at end
    Purpose: Guaranteed sequence control - either per-file or per-strung-file
    Code: string_cycle() - single_subfolder check before/after combination loop

14. COMPREHENSIVE MANIFEST
    Status: [OK] ACTIVE (Always)
    What: Detailed breakdown showing all timing and features
    Location: __MANIFEST_XX__.txt in output folder
    Shows:
      - All file types and durations
      - Complete pause breakdown by type
      - File list with cumulative timeline
      - Multiplier and jitter percentage
      - Folder structure
    Purpose: Complete transparency and verification
    Code: Line ~1965-2045 (manifest generation)

15. SPECIFIC FOLDERS FILTERING
    Status: ?? OPTIONAL (--specific-folders <file>)
    What: Only process folders listed in file
    Default: Process ALL numbered folders
    Usage: Pass text file with folder numbers (one per line)
    Purpose: Run subset of activities
    Code: Line ~1640-1665 (filtering logic)

16. CHAT INSERTS
    Status: ?? OPTIONAL (Disabled by default, --no-chat flag)
    What: One random chat macro is spliced into exactly one version per folder batch.
    Behaviour:
      - Per folder batch: 1 non-raw version is chosen at random to receive chat
      - That version gets 1 chat file inserted at a random point in its middle third
      - All other versions in the batch get no chat insert
      - Raw files are never chosen (they carry no added features)
      - If no chat files are found in "chat inserts/" folder, nothing happens
    Chat File Location: <input root>/../chat inserts/*.json
    Insertion Point: Random index in middle third of finished strung_events
      After insertion all subsequent event timestamps are shifted forward by
      the chat file's duration so timing integrity is preserved.
    Default: DISABLED in workflows (pass --no-chat to disable explicitly)
    Purpose: Natural social presence - one chat per activity run, unpredictable timing
    Code: chat_version_idx selection before version loop; splice block before save

17. PRE-PLAY BUFFER GUARANTEE (files_added counter)
    Status: [OK] ACTIVE (Always)
    Added: v3.17.2
    What: Guarantees the pre-play buffer (300ms) fires before EVERY file transition,
          including always_first and always_last files.
    Problem It Solved:
      - The original guard was "if cycle_events:" - checking if the events list was
        non-empty to decide whether to insert the buffer.
      - Python's nonlocal binding means if the outer scope ever rebinds cycle_events
        (e.g. cycle_events = []) after the inner function captures it, the inner
        function's nonlocal lookup sees the old empty reference.
      - Result: always_first / always_last files started at 0ms after the previous
        file ended - no buffer, no cursor path. Last click of previous file and first
        click of next file fired on the same millisecond, causing missed actions.
    Fix: Replaced "if cycle_events:" with "if files_added > 0:" using an explicit
         integer counter. Integers cannot be silently rebound the same way as lists.
         Counter is declared in outer scope, accessed via nonlocal, incremented by 1
         after every successful file add.
    Also Fixed: Cursor path condition was "if last_x and first_x" - this silently
                fails when X=0 (a valid screen coordinate, evaluates as falsy in Python).
                Changed to "if last_x is not None and first_x is not None".
    Impact: All file transitions now guaranteed to have:
              File ends -> 500-800ms buffer (random) -> cursor path -> next file starts
    Code: add_file_to_cycle() inner function; files_added init in string_cycle()

18. FAIL-FAST ERROR HANDLING
    Status: [OK] ACTIVE (Always)
    Added: v3.17.1
    What: All fatal early-exit conditions now call sys.exit(1) instead of return.
    Problem It Solved:
      - "return" in main() exits with code 0 (success). GitHub Actions saw the Python
        step succeed, continued to the ZIP step, and failed there with a confusing
        "empty directory" error - hiding the real cause.
      - Made debugging very slow: error appeared in the wrong step entirely.
    Conditions Now Covered:
      - Input root folder not found -> exits, prints the path it searched
      - No numbered subfolders found -> exits, prints directory contents
      - Specific folders file missing or unreadable -> exits with reason
      - None of the specified folder names matched -> exits, prints what it looked
        for vs what was actually available (most common cause: name mismatch)
    Result: Workflow fails at the Python step with the exact reason visible in logs.
    Code: main() - four sys.exit(1) calls replacing return statements

19. FLAT FOLDER SUPPORT
    Status: [OK] ACTIVE (Always, auto-detected)
    Added: v3.18.4
    What: Allows a main folder to contain JSON files directly with no numbered
          subfolders. The script detects this automatically and treats all files
          in the folder as a single pool (virtual subfolder 1.0).
    Structure Supported:
      NORMAL (numbered subfolders):        FLAT (files directly inside):
      20- Smth R2H/                        20- Smth R2H/
        1- action/                           file_a.json
          file.json                          file_b.json
        2- bank/                             always first.json
          file.json
    Behaviour:
      - Files are randomly selected from the pool each cycle (same as a regular
        numbered subfolder)
      - always_first / always_last tags in filenames still work
      - time_sensitive main folder tag still works
      - logout files are excluded from the pool automatically
      - Combination history tracks normally
    Detection: Triggered when zero numbered subfolders are found but JSON files
               exist directly in the folder
    Code: scan_for_numbered_subfolders() - flat folder block at end of function

21. DISTRACTION FILE GENERATION + INLINE INSERTION
    Status: [OK] ACTIVE (If DISTRACTIONS/ folder exists and is non-empty)
    Added: v3.18.14  Updated: v3.18.25
    What: Generates 50 distraction files simulating a player being momentarily
          distracted, then splices them randomly between folder transitions
          during stringing. Files are NOT saved to the bundle output folder -
          they are held in a temp folder and deleted after stringing completes.
    Activation:
      - Place a folder named "DISTRACTIONS" (case-insensitive) inside input_macros/
      - Place at least one .json file inside it (content irrelevant - just a trigger)
    Output:
      - 50 files generated in a temp folder, used for inline insertion, then deleted
      - Each file uses exactly 3 randomly chosen features from the 6 available
      - NEVER inserted into Raw or Inefficient versions - Normal only
    Per-file duration: random float 1-3 min (rng.uniform, never rounded)
    Insertion:
      - Per-folder chance: rng.uniform(7.0, 14.0)% (float decimal, once per folder)
      - Rolled at each folder transition (F1->F2, F2->F3, etc.) within a cycle
      - Never inserted after the last folder in a cycle
    6 available distraction features (each file picks 3):
      - CURSOR WANDER   - 2-7 moves, per-call randomised speed envelope
      - CURSOR PAUSE    - 0.3-4s, per-call randomised drift probability + magnitude
      - RIGHT CLICK     - approach + click, per-call randomised offset + hover + hold
      - TYPING          - type word + erase, per-call randomised speed/hesitation
      - KEY SPAM        - spam key + erase, per-call randomised speed envelopes
      - SHAPE MOVEMENT  - circle/triangle/square/rectangle/star with random jitter
    All timing envelopes (lo/hi bounds) are re-drawn per call so each action
    invocation has a genuinely different character - not just different values
    within fixed ranges, but different ranges each time.
    Manifest: "DISTRACTION File Pause: Xm Xs" in Normal file breakdown
    Code: generate_distraction_files() + _add_* helpers + string_cycle() insertion

22. SHAPE MOVEMENT (distraction sub-feature)
    Status: [OK] ACTIVE (as one of 6 distraction features)
    Added: v3.18.24
    What: Traces geometric shapes with per-point jitter and randomised speed
    Shapes: circle/donut (3-5 laps), triangle (1-3 laps), square (1-3 laps),
            rectangle (1-3 laps), star (1-2 laps)
    Jitter: per-shape random magnitude rng.uniform(3.0, 10.0) px applied to
            every waypoint - shape remains recognisable but hand-drawn
    Speed: ms_per_seg = rng.uniform(80, 400) drawn once per shape, then
           +/-40% per segment for natural rhythm variation
    Code: _add_shape_movement()

20. FILE TRANSITION START GAP PROTECTION
    Status: [OK] ACTIVE (Always, when positions differ between files)
    Added: v3.18.10
    What: Inserts a short gap (80-150ms) between the cursor snap event and the
          first event of the incoming file at every file transition.
    Problem It Solved:
      - After a cursor transition path, the script places a final "snap" MouseMove
        at exactly 'timeline'. The first event of the next file also lands at
        exactly 'timeline' (its relative time is always 0ms after normalisation).
      - When that first event is a DragStart, both the snap and the DragStart share
        the same timestamp. The macro player interprets simultaneous events as
        concurrent - the drag fires with no physical separation from the move,
        causing the mouse to clamp at the start position.
    Fix: After placing the snap MouseMove, advance 'timeline' by 80-150ms before
         appending any file events. The sequence becomes:
           ...cursor path...
           +0ms   MouseMove (snap to start position)  ? transition end
           +80-150ms gap
           +0ms   DragStart (file begins)             ? safely separated
    Relationship to Feature 17:
      Feature 17 (Pre-play Buffer) protects the END of the outgoing file (prevents
      the previous DragEnd from being immediately followed by a cursor snap).
      Feature 20 protects the START of the incoming file (prevents the cursor snap
      from being immediately followed by the file's first DragStart).
      Both are needed; they guard opposite sides of every transition.
    Code: add_file_to_cycle() - post_snap_gap after final snap MouseMove

25. INTRA-FILE ZERO-GAP PROTECTION (Feature 25)
    Status: [OK] ACTIVE (Always, applied to every source file on load)
    Added: v3.18.30
    What: Scans each source file's raw events for MouseMove -> DragStart/LeftDown/
          RightDown/Click pairs where the gap is under 15ms (virtually simultaneous
          as recorded by the macro capture tool) and shifts the click event forward
          to create a clean 20ms separation.
    Problem It Solved:
      Some recordings capture the cursor arriving at a click position and the click
      itself within 1ms of each other (same coordinates). The macro player sees
      these as simultaneous - it cannot distinguish "cursor moved here, THEN clicked"
      from "both happened at once" - causing the left button to clamp and hold at
      that position, dragging everything underneath it.
      Example (from __20_F_53m7s.json, 34:03.908):
        MouseMove  X=885, Y=429  t=2043908ms
        DragStart  X=885, Y=429  t=2043909ms  ? 1ms gap = clamp!
    Fix: For every such pair with gap in [0, 15ms), all events from the click
         onward are shifted forward by (20 - gap) ms, creating a guaranteed
         20ms minimum between the arrival move and the click.
    Scope: Applied to the raw event list BEFORE any features (jitter, pauses,
           idle movements) are added, so it never interacts with or undoes the
           fix during later processing steps.
    Threshold: < 15ms gap = zero-gap (recording tool resolution)
    Target separation: 20ms (imperceptible to player, sufficient for macro player)
    Code: add_file_to_cycle() - scan loop after filter_problematic_keys()
    Status: [OK] ACTIVE (When distraction trigger present)
    Added: v3.18.29
    What: Distraction files are selected via a shuffled virtual queue - every one
          of the 50 generated files plays before any file is reused. When all 50
          have been inserted the queue re-shuffles and cycles again.
    Behaviour:
      - At generation time, the 50 files are loaded into a VirtualDistQueue
      - Each insertion pops the next file from the shuffled queue
      - When the queue empties it re-shuffles the full pool using the bundle RNG
      - Guarantees maximum variety: no distraction file repeats until all others
        have been used at least once
    Why it matters: With ~8-14% insertion chance per folder transition and many
      cycles, the same short file would previously appear repeatedly. Now each
      insertion draws from a rotating pool of all 50.
    Code: VirtualDistQueue class; dist_queue.next() in _maybe_insert_distraction()

24. 2:3:7 FILE RATIO DISTRIBUTION
    Status: [OK] ACTIVE (Always, scales with --versions)
    Added: v3.18.29
    What: Output files follow a 2:3:7 ratio (raw:inefficient:normal) regardless
          of how many total versions are requested.
    Formula:
      raw    = max(1, round(versions x 2/12))
      inef   = max(1, round(versions x 3/12))
      normal = versions ? raw ? inef   (remainder always goes to normal)
    Examples:
      --versions 12  -> 2 raw + 3 inef + 7 normal   (2:3:7 exact)
      --versions 24  -> 4 raw + 6 inef + 14 normal  (4:6:14 exact)
      --versions 20  -> 3 raw + 5 inef + 12 normal  (closest to 2:3:7)
      --versions 10  -> 2 raw + 2 inef + 6 normal
      --versions 6   -> 1 raw + 2 inef + 3 normal
    Time-sensitive override: if any folder is time-sensitive, inefficient count
      becomes 0 and all its slots are added to normal (raw count unchanged).
    Code: VERSION DISTRIBUTION block in the per-folder version loop

===========================================================================
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_ms_precise(ms):
    """Format milliseconds as Xm Ys"""
    total_sec = int(ms / 1000)
    minutes = total_sec // 60
    seconds = total_sec % 60
    return f"{minutes}m {seconds}s"

def get_file_duration_ms(filepath):
    """Get file duration in milliseconds"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            events = json.load(f)
        if not events:
            return 0
        times = [e.get('Time', 0) for e in events]
        return max(times) - min(times)
    except:
        return 0

def filter_problematic_keys(events: list) -> list:
    """
    CRITICAL: Filter out keys that could stop macro playback.
    Removes: HOME(36), END(35), PAGE_UP(33), PAGE_DOWN(34), PAUSE(19), PRINT_SCREEN(44)
    NOTE: ESC(27) kept - it is a valid in-game key (e.g. closing menus).
    """
    problematic_codes = {19, 33, 34, 35, 36, 44}  # ESC(27) removed - valid in-game action
    filtered = []
    
    for event in events:
        keycode = event.get('KeyCode')
        if keycode in problematic_codes:
            continue
        filtered.append(event)
    
    return filtered

def parse_optional_chance(folder_name: str) -> float:
    """
    Parse the inclusion probability from an 'optional'-tagged folder name.

    Rules:
      - No number after 'optional'  -> random default 24.0-33.0% (float)
      - Number found (integer OR decimal) -> used as centre of +/-2% random range.
        e.g. optional23 -> rng.uniform(21.0, 25.0)%
        This adds variety so the same folder doesn't always hit the exact same
        threshold. Range is clamped so it never goes below 1% or above 99%.

    Accepted formats (all case-insensitive):
      "3 optional- bank/"           -> random 0.24-0.33
      "3 optional50- bank/"         -> random 0.48-0.52
      "3 optional50.5- bank/"       -> random 0.485-0.525
      "3 optional23-4- booth/"      -> random 0.21-0.25
      "3 optional33.3+end- logout/" -> random 0.313-0.353

    Returns a float in (0, 1).
    """
    import re
    # Capture integer OR decimal number after 'optional' (e.g. 50, 50.5, 33.3)
    match = re.search(r'optional[^-\d]*?(\d+(?:\.\d+)?)', folder_name, re.IGNORECASE)
    if match:
        centre = float(match.group(1))
        lo = max(1.0, centre - 2.0)
        hi = min(99.0, centre + 2.0)
        return random.uniform(lo, hi) / 100.0
    # No number -> default random range (float, never rounded)
    return random.uniform(0.24, 0.33)


def parse_max_files(folder_name: str) -> int:
    """
    Parse max-files count from folder name.
    Formats (case-insensitive, all combinations):
      "F3 optional58-6-"  -> max 6  (58% chance)
      "F3 optional-6-"    -> max 6  (default chance)
      "F1-4-"             -> max 4  (always included)
      "F3 optional58-"    -> max 1  (no max-files number = default 1)
      "F1- mine rock/"    -> max 1  (no number = default 1)

    The max-files number is the LAST standalone integer before a trailing dash,
    not the folder number or the optional-chance percentage.
    Returns int >= 1.
    """
    import re
    # Pattern: dash, then digits (the max-files count), then dash or end
    # We look for a bare integer surrounded by dashes that isn't the folder number
    # (folder number is at the very start) and isn't the optional-chance percentage
    # (which directly follows "optional").
    # Strategy: strip the leading folder number, strip optional-chance, then find
    # a remaining -N- or -N/ pattern.
    name = folder_name.strip('/').strip()
    # Remove folder number prefix (e.g. "3", "3.5", "F3")
    name = re.sub(r'^[Ff]?\d+(?:\.\d+)?\s*', '', name)
    # Remove optional-chance number (digits immediately after "optional")
    name = re.sub(r'optional\s*\d+(?:\.\d+)?', 'optional', name, flags=re.IGNORECASE)
    # Now look for -N- or -N/ or -N at end where N is 2-3 digits (1 digit would be ambiguous)
    # Actually look for any -digits- pattern remaining
    matches = re.findall(r'-(\d+)-', name)
    if matches:
        try:
            return max(1, int(matches[-1]))   # take the last one
        except ValueError:
            pass
    return 1   # default: 1 file


def fix_click_events(events: list) -> list:
    """
    Convert 'Click' events to LeftDown+LeftUp pairs.
    This prevents the mouse from clamping down and dragging.
    
    CRITICAL FIX from merge_macros.py!
    """
    fixed = []
    for event in events:
        if event.get('Type') == 'Click':
            # Replace Click with LeftDown + LeftUp pair
            time = event.get('Time', 0)
            x = event.get('X')
            y = event.get('Y')
            
            # LeftDown at same time
            left_down = {
                'Type': 'LeftDown',
                'Time': time,
            }
            if x is not None:
                left_down['X'] = x
            if y is not None:
                left_down['Y'] = y
            
            # LeftUp 10-20ms later (small random delay)
            left_up = {
                'Type': 'LeftUp',
                'Time': time + random.randint(10, 20),
            }
            if x is not None:
                left_up['X'] = x
            if y is not None:
                left_up['Y'] = y
            
            fixed.append(left_down)
            fixed.append(left_up)
        else:
            # Keep all other events as-is
            fixed.append(event)
    
    return fixed

def generate_human_path(start_x, start_y, end_x, end_y, duration_ms, rng):
    """
    Generate a human-like mouse path with variable speed, path styles, and wobbles.
    
    Path Styles:
    - Efficient: Direct path, few curves, faster
    - Meandering: Curved path, more wandering, varied speed
    - Hesitant: Slow start, acceleration, deceleration
    - Swift: Fast throughout, minimal curves
    
    Speed Variations:
    - Very fast: 100-200ms typical
    - Fast: 200-300ms typical
    - Normal: 300-500ms typical
    - Slow: 500-700ms typical
    - Very slow: 700-1000ms typical
    
    Returns: List of (time_ms, x, y) tuples.
    """
    if duration_ms < 100:
        return [(0, end_x, end_y)]
    
    path = []
    dx = end_x - start_x
    dy = end_y - start_y
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance < 5:
        return [(0, end_x, end_y)]
    
    # Choose path style (determines curvature and speed pattern)
    path_style = rng.choice(['efficient', 'meandering', 'hesitant', 'swift'])
    
    # Determine num_steps based on distance and path style
    if path_style == 'efficient':
        # Direct, fewer steps
        num_steps = max(3, min(int(distance / 20), int(duration_ms / 60)))
    elif path_style == 'swift':
        # Very fast, few steps
        num_steps = max(2, min(int(distance / 25), int(duration_ms / 80)))
    elif path_style == 'meandering':
        # More steps for smoother curves
        num_steps = max(5, min(int(distance / 10), int(duration_ms / 40)))
    else:  # hesitant
        # Medium steps
        num_steps = max(4, min(int(distance / 15), int(duration_ms / 50)))
    
    # Add control points based on path style
    if path_style == 'efficient':
        # Few or no control points (straighter path)
        num_control = rng.choice([0, 1])
        offset_range = 0.15  # Less curve
    elif path_style == 'swift':
        # No control points (direct)
        num_control = 0
        offset_range = 0.0
    elif path_style == 'meandering':
        # More control points (curvier path)
        num_control = rng.randint(2, 4)
        offset_range = 0.4  # More curve
    else:  # hesitant
        # Medium control points
        num_control = rng.randint(1, 2)
        offset_range = 0.25
    
    control_points = []
    for _ in range(num_control):
        offset = rng.uniform(-offset_range, offset_range) * distance
        t = rng.uniform(0.2, 0.8)
        ctrl_x = start_x + dx * t + (-dy / (distance + 1)) * offset
        ctrl_y = start_y + dy * t + (dx / (distance + 1)) * offset
        control_points.append((ctrl_x, ctrl_y, t))
    
    control_points.sort(key=lambda p: p[2])
    current_time = 0
    
    for step in range(num_steps + 1):
        t_raw = step / num_steps
        
        # Apply speed profile based on path style
        if path_style == 'efficient':
            # Smooth acceleration
            t = 1 - (1 - t_raw) ** 1.8
        elif path_style == 'swift':
            # Linear (constant speed)
            t = t_raw
        elif path_style == 'meandering':
            # Variable speed with slight deceleration at end
            t = 0.5 * (1 - math.cos(t_raw * math.pi))
        else:  # hesitant
            # Slow start, fast middle, slow end
            t = 0.5 * (1 - math.cos(t_raw * math.pi))
        
        # Calculate position
        if not control_points:
            x = start_x + dx * t
            y = start_y + dy * t
        else:
            x, y = start_x, start_y
            for i, (ctrl_x, ctrl_y, ctrl_t) in enumerate(control_points):
                if t <= ctrl_t:
                    segment_t = t / ctrl_t if ctrl_t > 0 else 0
                    x = start_x + (ctrl_x - start_x) * segment_t
                    y = start_y + (ctrl_y - start_y) * segment_t
                    break
                else:
                    if i == len(control_points) - 1:
                        segment_t = (t - ctrl_t) / (1 - ctrl_t) if (1 - ctrl_t) > 0 else 0
                        x = ctrl_x + (end_x - ctrl_x) * segment_t
                        y = ctrl_y + (end_y - ctrl_y) * segment_t
                    else:
                        start_x, start_y = ctrl_x, ctrl_y
        
        # Add wobble (less for swift, more for meandering)
        if path_style == 'swift':
            wobble = rng.uniform(0, 2) if step > 0 and step < num_steps else 0
        elif path_style == 'meandering':
            wobble = rng.uniform(1, 7) if step > 0 and step < num_steps else 0
        else:
            wobble = rng.uniform(1, 5) if step > 0 and step < num_steps else 0
        
        x += rng.uniform(-wobble, wobble)
        y += rng.uniform(-wobble, wobble)
        
        # Bounds
        x = max(100, min(1800, int(x)))
        y = max(100, min(1000, int(y)))
        
        step_time = int(t * duration_ms)
        current_time = max(current_time, step_time)
        path.append((current_time, x, y))
    
    return path

# ============================================================================
# COMBINATION TRACKER
# ============================================================================


def is_in_drag_sequence(events, index, drag_indices=None):
    """
    Check if the given index is inside a drag sequence (between DragStart and DragEnd).
    Returns True if we're in the middle of a drag.

    If drag_indices (a precomputed set from build_drag_index_set) is provided,
    the check is O(1). Otherwise falls back to the original O(n) scan.
    """
    if drag_indices is not None:
        return index in drag_indices

    drag_started = False
    for j in range(index, -1, -1):
        event_type = events[j].get("Type", "")
        if event_type == "DragEnd":
            return False
        elif event_type == "DragStart":
            drag_started = True
            break
    
    if not drag_started:
        return False
    
    for j in range(index + 1, len(events)):
        event_type = events[j].get("Type", "")
        if event_type == "DragEnd":
            return True
        elif event_type == "DragStart":
            return False
    
    return False


def build_drag_index_set(events) -> set:
    """
    Return the set of all event indices that are inside a drag sequence.
    O(n) single pass - call this once, then use the result for O(1) lookups.
    """
    drag_indices = set()
    in_drag = False
    for i, e in enumerate(events):
        t = e.get("Type", "")
        if t == "DragStart":
            in_drag = True
        elif t == "DragEnd":
            in_drag = False
        if in_drag:
            drag_indices.add(i)
    return drag_indices

def detect_rapid_click_sequences(events):
    """
    Detect sequences of rapid clicks at similar coordinates.
    
    Detects:
    - Double clicks (2 clicks within 500ms, +/-5 pixels)
    - Spam clicks (3+ clicks within 2 seconds, +/-10 pixels)
    
    Returns list of protected ranges: [(start_idx, end_idx), ...]
    These ranges should NOT have pauses/gaps inserted between them.
    """
    if not events or len(events) < 2:
        return []
    
    protected_ranges = []
    
    i = 0
    while i < len(events):
        event = events[i]
        
        # Check Click and DragStart events (both are click actions)
        event_type = event.get("Type")
        if event_type not in ("Click", "DragStart"):
            i += 1
            continue
        
        # Found a click, look for nearby clicks
        click_sequence = [i]
        first_time = event.get("Time", 0)
        first_x = event.get("X")
        first_y = event.get("Y")
        
        if first_x is None or first_y is None:
            i += 1
            continue
        
        # Look ahead for more clicks
        j = i + 1
        while j < len(events):
            next_event = events[j]
            next_time = next_event.get("Time", 0)
            
            # Stop looking if too far in time (2 seconds max)
            if next_time - first_time > 2000:
                break
            
            # Check if it's a click or drag
            next_type = next_event.get("Type")
            if next_type in ("Click", "DragStart"):
                next_x = next_event.get("X")
                next_y = next_event.get("Y")
                
                if next_x is not None and next_y is not None:
                    # Calculate distance from first click
                    dist = ((next_x - first_x) ** 2 + (next_y - first_y) ** 2) ** 0.5
                    
                    # If within 10 pixels, part of sequence
                    if dist <= 10:
                        click_sequence.append(j)
            
            j += 1
        
        # If found 2+ clicks, protect the sequence
        if len(click_sequence) >= 2:
            start_idx = click_sequence[0]
            end_idx = click_sequence[-1]
            protected_ranges.append((start_idx, end_idx))
            i = end_idx + 1
        else:
            i += 1
    
    return protected_ranges


def is_in_protected_range(index, protected_ranges):
    """Check if an index is within any protected range."""
    for start, end in protected_ranges:
        if start <= index <= end:
            return True
    return False


def add_pre_click_jitter(events: list, rng: random.Random) -> tuple:
    """
    SMART JITTER SYSTEM v3.9.0
    
    Add realistic micro-movements to 9-21% of TOTAL file movements.
    CRITICAL: NO jitter within 1 second before/after ANY click!
    
    Rules:
    1. Jitter percentage: 9-21% of total MouseMove events
    2. Exclusion zone: 1000ms before AND after any click
    3. Only jitter MouseMove events (never Click, DragStart, RightDown, etc.)
    4. Jitter = 2-3 micro-movements (+/-1-3px) + final snap to exact position
    
    Returns (events_with_jitter, jitter_count, total_moves, jitter_percentage).
    """
    if not events or len(events) < 2:
        return events, 0, 0, 0.0
    
    # Step 1: Find ALL click times (any click-like event)
    click_types = {'Click', 'LeftDown', 'RightDown', 'DragStart'}
    click_times_sorted = sorted(
        event.get('Time', 0) for event in events if event.get('Type') in click_types
    )

    import bisect
    exclusion_ms = 1000

    # Step 2: Find all MouseMove events that are SAFE to jitter
    # Safe = NOT within 1000ms before/after ANY click  (O(n log c) total)
    safe_movements = []
    total_moves = 0

    for i, event in enumerate(events):
        if event.get('Type') == 'MouseMove':
            total_moves += 1
            event_time = event.get('Time', 0)

            # Binary search: nearest click before and after
            pos = bisect.bisect_left(click_times_sorted, event_time)
            is_safe = True
            # Check click just before
            if pos > 0 and event_time - click_times_sorted[pos - 1] <= exclusion_ms:
                is_safe = False
            # Check click at or after
            if is_safe and pos < len(click_times_sorted) and click_times_sorted[pos] - event_time <= exclusion_ms:
                is_safe = False

            if is_safe:
                safe_movements.append((i, event))
    
    # Step 3: Calculate how many jitters to add (9-21% of TOTAL movements)
    jitter_percentage = rng.uniform(0.09, 0.21)
    target_jitters = int(total_moves * jitter_percentage)
    
    # Can't jitter more than safe movements available
    target_jitters = min(target_jitters, len(safe_movements))
    
    if target_jitters == 0:
        return events, 0, total_moves, jitter_percentage
    
    # Step 4: Randomly select which safe movements get jitter
    movements_to_jitter = rng.sample(safe_movements, target_jitters)
    
    # Sort by index (descending) so we insert from end to start
    # This prevents index shifting issues
    movements_to_jitter.sort(key=lambda x: x[0], reverse=True)
    
    # Step 5: Add jitter to selected movements
    jitter_count = 0
    
    for idx, event in movements_to_jitter:
        move_x = event.get('X')
        move_y = event.get('Y')
        move_time = event.get('Time')
        
        if move_x is None or move_y is None or move_time is None:
            continue
        
        # Generate 2-3 micro-movements
        num_jitters = rng.randint(2, 3)
        jitter_events = []
        
        # Time budget: 100-200ms total
        time_budget = rng.randint(100, 200)
        time_per_jitter = time_budget // (num_jitters + 1)
        
        # Cap time_budget so jitter events never go before t=0
        if move_time - time_budget < 0:
            time_budget = max(0, int(move_time) - 1)
        if time_budget == 0:
            continue  # Not enough room before this event - skip jitter
        current_time = move_time - time_budget
        
        # Add jitter movements (+/-1-3 pixels)
        for j in range(num_jitters):
            offset_x = rng.randint(-3, 3)
            offset_y = rng.randint(-3, 3)
            
            jitter_x = int(move_x) + offset_x
            jitter_y = int(move_y) + offset_y
            
            # Bounds check
            jitter_x = max(100, min(1800, jitter_x))
            jitter_y = max(100, min(1000, jitter_y))
            
            jitter_events.append({
                'Type': 'MouseMove',
                'Time': current_time,
                'X': jitter_x,
                'Y': jitter_y
            })
            
            current_time += time_per_jitter
        
        # Final movement: snap to EXACT target position
        jitter_events.append({
            'Type': 'MouseMove',
            'Time': current_time,
            'X': int(move_x),
            'Y': int(move_y)
        })
        
        # Insert jitter events BEFORE the original movement
        for jitter_idx, jitter_event in enumerate(jitter_events):
            events.insert(idx + jitter_idx, jitter_event)
        
        jitter_count += 1
    
    return events, jitter_count, total_moves, jitter_percentage

def insert_intra_file_pauses(events: list, rng: random.Random,
                              protected_ranges: list = None,
                              file_type: str = 'normal') -> tuple:
    """
    Insert a single within-file pause whose duration is a percentage of the
    individual file's own play time:
      Raw:         0%  - no pause inserted
      Normal:      5%  - e.g. 20s file -> 1s pause somewhere safe
      Inefficient: 15% - e.g. 20s file -> 3s pause somewhere safe

    The pause is inserted at a single randomly chosen safe point (not in a drag
    sequence, not in a rapid-click sequence, not in the first or last 10%).
    Returns (events_with_pause, total_pause_time_ms).
    """
    if not events or len(events) < 5:
        return events, 0

    # Raw = 0%, Normal = random in [2%, 5%], Inef = random in [10%, 15%]
    # Drawn fresh each call — decimal, never rounded (e.g. 2.14%, 3.87%, 11.6%)
    if file_type == 'raw':
        return events, 0
    elif file_type == 'inef':
        pct = rng.uniform(0.10, 0.15)
    else:  # normal
        pct = rng.uniform(0.02, 0.05)

    if protected_ranges is None:
        protected_ranges = []

    file_duration_ms = events[-1].get('Time', 0) - events[0].get('Time', 0)
    if file_duration_ms <= 0:
        return events, 0

    # Float ms - no rounding
    pause_duration = file_duration_ms * pct

    protected_set = set()
    for s, e in protected_ranges:
        for k in range(s, e + 1):
            protected_set.add(k)

    drag_indices = build_drag_index_set(events)

    first_safe = max(1, int(len(events) * 0.10))
    last_safe  = min(len(events) - 1, int(len(events) * 0.90))
    valid = [
        idx for idx in range(first_safe, last_safe)
        if idx not in protected_set
        and idx not in drag_indices
        and events[idx].get('Type') != 'DragStart'
        and (idx + 1 >= len(events) or events[idx + 1].get('Type') != 'DragStart')
    ]

    if not valid:
        return events, 0

    pause_idx = rng.choice(valid)
    for j in range(pause_idx, len(events)):
        events[j]['Time'] = events[j].get('Time', 0) + pause_duration

    return events, pause_duration
def insert_idle_mouse_movements(events, rng, movement_percentage):
    """
    Insert realistic human-like mouse movements during idle periods (gaps > 2 seconds).
    O(n) - drag membership and click-proximity lookups are precomputed as sets.
    """
    if not events or len(events) < 2:
        return events, 0

    # Precompute O(n) - used for O(1) per-event checks below
    drag_indices = build_drag_index_set(events)

    # Build set of indices that are within 3 s after a click event
    # (idle movements must not be placed in those windows)
    click_proximity = set()
    click_window = 3000
    click_types = {"Click", "LeftDown", "LeftUp", "RightDown", "RightUp"}
    for i, e in enumerate(events):
        if e.get("Type") in click_types:
            t_click = e.get("Time", 0)
            # mark all earlier indices whose next_time lands within the window
            for j in range(i - 1, -1, -1):
                if events[j].get("Time", 0) < t_click - click_window:
                    break
                click_proximity.add(j)

    result = []
    total_idle_time = 0

    for i in range(len(events)):
        result.append(events[i])

        if i < len(events) - 1:
            current_time = int(events[i].get("Time", 0))
            next_time    = int(events[i + 1].get("Time", 0))
            gap = next_time - current_time

            if gap >= 2000:
                if i in drag_indices:
                    continue
                if i in click_proximity:
                    continue
                
                # Calculate active window
                active_duration = int(gap * movement_percentage)
                buffer_start = (gap - active_duration) // 2
                movement_start = current_time + buffer_start
                
                # Get start position
                start_x, start_y = 500, 500
                for j in range(i, -1, -1):
                    x_val = events[j].get("X")
                    y_val = events[j].get("Y")
                    if x_val is not None and y_val is not None:
                        start_x = int(x_val)
                        start_y = int(y_val)
                        break
                
                # Get next position (where we need to end up)
                next_x, next_y = start_x, start_y
                for j in range(i + 1, min(i + 20, len(events))):
                    x_val = events[j].get("X")
                    y_val = events[j].get("Y")
                    if x_val is not None and y_val is not None:
                        next_x = int(x_val)
                        next_y = int(y_val)
                        break
                
                # Reserve last 25% for smooth transition back
                transition_duration = int(active_duration * 0.25)
                pattern_duration = active_duration - transition_duration
                
                # Choose movement behavior
                behavior = rng.choice([
                    'wander',      # Random wandering around
                    'check_edge',  # Quick look at screen edge
                    'fidget',      # Small nervous movements
                    'explore',     # Move far then return
                    'drift',       # Slow meandering
                    'scan'         # Move across screen
                ])
                
                pattern_end_x, pattern_end_y = start_x, start_y
                pattern_time_used = 0
                
                if behavior == 'wander':
                    # Random wandering - multiple small moves
                    num_moves = rng.randint(3, 6)
                    move_duration = pattern_duration // num_moves
                    
                    current_x, current_y = start_x, start_y
                    
                    for move_idx in range(num_moves):
                        # Pick random nearby target
                        target_x = current_x + rng.randint(-150, 150)
                        target_y = current_y + rng.randint(-100, 100)
                        target_x = max(100, min(1800, target_x))
                        target_y = max(100, min(1000, target_y))
                        
                        # Generate human path
                        path = generate_human_path(current_x, current_y, target_x, target_y, move_duration, rng)
                        
                        for path_time, px, py in path:
                            abs_time = movement_start + pattern_time_used + path_time
                            result.append({
                                "Time": abs_time,
                                "Type": "MouseMove",
                                "X": px,
                                "Y": py
                            })
                        
                        current_x, current_y = path[-1][1], path[-1][2]
                        pattern_time_used += move_duration
                    
                    pattern_end_x, pattern_end_y = current_x, current_y
                
                elif behavior == 'check_edge':
                    # Quick look at screen edge then back
                    edges = [
                        (150, start_y),    # Left edge
                        (1750, start_y),   # Right edge
                        (start_x, 150),    # Top edge
                        (start_x, 950),    # Bottom edge
                    ]
                    edge_x, edge_y = rng.choice(edges)
                    
                    # Move to edge (60% of time, fast)
                    edge_duration = int(pattern_duration * 0.6)
                    path_to_edge = generate_human_path(start_x, start_y, edge_x, edge_y, edge_duration, rng)
                    
                    for path_time, px, py in path_to_edge:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    # Return near start (40% of time, slower)
                    return_duration = pattern_duration - edge_duration
                    return_x = start_x + rng.randint(-40, 40)
                    return_y = start_y + rng.randint(-40, 40)
                    return_x = max(100, min(1800, return_x))
                    return_y = max(100, min(1000, return_y))
                    
                    path_return = generate_human_path(edge_x, edge_y, return_x, return_y, return_duration, rng)
                    
                    for path_time, px, py in path_return:
                        abs_time = movement_start + edge_duration + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path_return[-1][1], path_return[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'fidget':
                    # Small rapid movements in small area
                    num_fidgets = rng.randint(5, 10)
                    fidget_duration = pattern_duration // num_fidgets
                    
                    current_x, current_y = start_x, start_y
                    
                    for fidget_idx in range(num_fidgets):
                        # Small offset
                        target_x = current_x + rng.randint(-30, 30)
                        target_y = current_y + rng.randint(-30, 30)
                        target_x = max(100, min(1800, target_x))
                        target_y = max(100, min(1000, target_y))
                        
                        path = generate_human_path(current_x, current_y, target_x, target_y, fidget_duration, rng)
                        
                        for path_time, px, py in path:
                            abs_time = movement_start + pattern_time_used + path_time
                            result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                        
                        current_x, current_y = path[-1][1], path[-1][2]
                        pattern_time_used += fidget_duration
                    
                    pattern_end_x, pattern_end_y = current_x, current_y
                
                elif behavior == 'explore':
                    # Move far away then return near start
                    away_x = start_x + rng.randint(-400, 400)
                    away_y = start_y + rng.randint(-300, 300)
                    away_x = max(100, min(1800, away_x))
                    away_y = max(100, min(1000, away_y))
                    
                    # Go away (65% of time)
                    away_duration = int(pattern_duration * 0.65)
                    path_away = generate_human_path(start_x, start_y, away_x, away_y, away_duration, rng)
                    
                    for path_time, px, py in path_away:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    # Return (35% of time)
                    return_duration = pattern_duration - away_duration
                    return_x = start_x + rng.randint(-15, 15)
                    return_y = start_y + rng.randint(-15, 15)
                    return_x = max(100, min(1800, return_x))
                    return_y = max(100, min(1000, return_y))
                    
                    path_return = generate_human_path(away_x, away_y, return_x, return_y, return_duration, rng)
                    
                    for path_time, px, py in path_return:
                        abs_time = movement_start + away_duration + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path_return[-1][1], path_return[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'drift':
                    # Slow continuous drift
                    target_x = start_x + rng.randint(-200, 200)
                    target_y = start_y + rng.randint(-150, 150)
                    target_x = max(100, min(1800, target_x))
                    target_y = max(100, min(1000, target_y))
                    
                    path = generate_human_path(start_x, start_y, target_x, target_y, pattern_duration, rng)
                    
                    for path_time, px, py in path:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path[-1][1], path[-1][2]
                    pattern_time_used = pattern_duration
                
                elif behavior == 'scan':
                    # Scan across screen
                    scan_distance = rng.randint(300, 600)
                    direction = rng.choice(['horizontal', 'vertical', 'diagonal'])
                    
                    if direction == 'horizontal':
                        target_x = start_x + (scan_distance if rng.random() < 0.5 else -scan_distance)
                        target_y = start_y + rng.randint(-50, 50)
                    elif direction == 'vertical':
                        target_x = start_x + rng.randint(-50, 50)
                        target_y = start_y + (scan_distance if rng.random() < 0.5 else -scan_distance)
                    else:  # diagonal
                        target_x = start_x + (scan_distance if rng.random() < 0.5 else -scan_distance)
                        target_y = start_y + (scan_distance if rng.random() < 0.5 else -scan_distance)
                    
                    target_x = max(100, min(1800, target_x))
                    target_y = max(100, min(1000, target_y))
                    
                    path = generate_human_path(start_x, start_y, target_x, target_y, pattern_duration, rng)
                    
                    for path_time, px, py in path:
                        abs_time = movement_start + path_time
                        result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                    
                    pattern_end_x, pattern_end_y = path[-1][1], path[-1][2]
                    pattern_time_used = pattern_duration
                
                # Smooth transition back to next recorded position
                transition_path = generate_human_path(
                    pattern_end_x, pattern_end_y,
                    next_x, next_y,
                    transition_duration,
                    rng
                )
                
                for path_time, px, py in transition_path:
                    abs_time = movement_start + pattern_duration + path_time
                    result.append({"Time": abs_time, "Type": "MouseMove", "X": px, "Y": py})
                
                total_idle_time += active_duration
    
    return result, total_idle_time

class QueueFileSelector:
    def __init__(self, rng, all_files, durations_cache):
        self.rng = rng
        self.durations = durations_cache
        self.efficient = [f for f in all_files if "??" not in f.name]
        self.inefficient = [f for f in all_files if "??" in f.name]
        self.eff_pool = list(self.efficient)
        self.ineff_pool = list(self.inefficient)
        self.rng.shuffle(self.eff_pool)
        self.rng.shuffle(self.ineff_pool)

    def get_sequence(self, target_minutes, force_inef=False, is_time_sensitive=False):
        seq, cur_ms = [], 0.0
        target_ms = target_minutes * 60000
        # Add +/-5% margin for flexibility
        margin = int(target_ms * 0.05)
        target_min = target_ms - margin
        target_max = target_ms + margin
        actual_force = force_inef if not is_time_sensitive else False
        
        # Keep adding files until we reach target
        # Stop conditions:
        # 1. Reached target OR
        # 2. Adding next file would overshoot by more than 4 minutes
        
        while cur_ms < target_max:
            # Try to get next file
            if actual_force and self.ineff_pool: pick = self.ineff_pool.pop(0)
            elif self.eff_pool: pick = self.eff_pool.pop(0)
            elif self.efficient:
                self.eff_pool = list(self.efficient); self.rng.shuffle(self.eff_pool)
                pick = self.eff_pool.pop(0)
            elif self.ineff_pool and not is_time_sensitive: pick = self.ineff_pool.pop(0)
            else: break  # No more files
            
            file_duration = self.durations.get(pick, 500)
            
            # File selector multiplier - CRITICAL for accuracy
            # 1.0x = too many files (overshoot 11-18 min)
            # 1.8x = too few files (undershoot 10-13 min)
            # 1.35x = sweet spot (target ?+/-2-4 min)
            if is_time_sensitive:
                estimated_time = file_duration * 1.05  # TIME SENSITIVE: minimal overhead
            else:
                estimated_time = file_duration * 1.35  # NORMAL: balanced estimate
            
            # Check if adding would overshoot too much
            potential_total = cur_ms + estimated_time
            overshoot = potential_total - target_ms
            
            if overshoot > margin:  # Would overshoot beyond acceptable margin
                # Only skip if we're already reasonably close to target
                if cur_ms >= (target_ms - (4 * 60000)):  # Within 4 min of target
                    break  # Close enough, stop
                else:
                    # Still far from target, add it anyway
                    seq.append(pick)
                    cur_ms += estimated_time
            else:
                # Safe to add (won't overshoot by more than 4 min)
                seq.append(pick)
                cur_ms += estimated_time
            
            # Safety limits
            if len(seq) > 800: break
            if cur_ms > target_ms * 3: break
        
        return seq



def insert_massive_pause(events: list, rng: random.Random, mult: float = 1.0) -> tuple:
    """
    Insert one massive pause (500-2900ms x multiplier) at random point.
    For INEFFICIENT files only.
    
    EXCLUDES pause from:
    - Drag sequences (between DragStart and DragEnd)
    - Rapid click sequences (double-clicks, spam clicks)
    - First/last 10% of file (for safety)
    
    Returns (events_with_pause, pause_duration_ms, split_index)
    """
    if not events or len(events) < 10:
        return events, 0, 0
    
    # Generate massive pause: 4-7 minutes (240000-420000ms) x multiplier
    pause_duration = int(rng.uniform(240000.0, 420000.0))  # no mult — flat 4-7 min
    
    # Detect protected ranges (rapid clicks, double-clicks)
    protected_ranges = detect_rapid_click_sequences(events)
    
    # Precompute drag membership O(n) -> O(1) lookups
    drag_indices = build_drag_index_set(events)

    # Find safe split points (not in drag, not in rapid click, not in first/last 10%)
    safe_indices = []
    first_safe = int(len(events) * 0.1)  # Skip first 10%
    last_safe = int(len(events) * 0.9)   # Skip last 10%
    
    for i in range(first_safe, last_safe):
        if i in drag_indices:
            continue
        if is_in_protected_range(i, protected_ranges):
            continue
        # Don't insert right before a DragStart
        if i + 1 < len(events) and events[i + 1].get("Type") == "DragStart":
            continue
        if i + 1 < len(events) and (i + 1) in drag_indices:
            continue
        safe_indices.append(i)
    
    # If no safe indices found, return original events
    if not safe_indices:
        return events, 0, 0
    
    # Pick random safe split point
    split_index = rng.choice(safe_indices)
    
    # Shift all events after split point
    for i in range(split_index + 1, len(events)):
        events[i]["Time"] += pause_duration
    
    return events, pause_duration, split_index

# ============================================================================
# STRING PARTS WITH ANTI-DETECTION
# ============================================================================

def string_cycle(subfolder_files, combination, rng, dmwm_file_set=set(),
                 distraction_files=None, distraction_chance=0.0,
                 is_click_sensitive=False,
                 play_always_first=True, play_always_last=True,
                 mult=1.0):
    """
    String one complete cycle (F1 -> F2 -> F3 -> ...) into a single unit.
    Returns raw events WITHOUT anti-detection features.
    play_always_first / play_always_last: for single-subfolder flat folders,
    always_first/last should fire only on the very first/last cycle of the whole
    strung file. Pass False for all but the first/last cycle respectively.
    Features will be applied to the ENTIRE cycle after.

    distraction_files: list of Path objects for generated distraction JSONs.
    distraction_chance: float in [0,1] - probability of inserting one distraction
                        file between each pair of folder transitions.
    is_click_sensitive: if True, skip cursor pathing between files (no coord changes).
    """
    
    def add_file_to_cycle(file_path, folder_num, is_dmwm, file_label):
        """Helper to add a file to the cycle"""
        nonlocal timeline, cycle_events, file_info_list, has_dmwm, total_pre_pause, total_transition_time, total_snap_gap_time, files_added
        
        # Load events
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception:
            return
        
        if not events:
            return
        
        # Capture base_time BEFORE filtering so that files where the first
        # event is a filtered key (e.g. END key at t=90ms) keep their full
        # original duration. Without this, base_time jumps to the first
        # surviving event and the entire leading gap is lost.
        base_time_pre_filter = min(e.get('Time', 0) for e in events)

        # Filter problematic keys only
        events = filter_problematic_keys(events)
        if not events:
            return

        # INTRA-FILE ZERO-GAP FIX (Feature 25)
        # Some recordings capture a MouseMove and DragStart/LeftDown at the same
        # millisecond (or within 1-14ms) at the same coordinates. The macro player
        # reads these as simultaneous - it can't distinguish "arrived THEN clicked"
        # from "both at once" - causing a left-button clamp at that position.
        # Fix: scan for any MouseMove -> click-type pair with a gap < 15ms and
        # shift the click event (and all subsequent events) forward by enough to
        # create a clean 20ms separation. This is applied to the raw event list
        # before any features are added so it doesn't interact with jitter/pauses.
        _CLICK_TYPES = {'DragStart', 'LeftDown', 'RightDown', 'Click'}
        _ZERO_GAP_THRESHOLD = 15    # ms - gaps below this are "simultaneous"
        _ZERO_GAP_TARGET    = 20    # ms - minimum clean separation to enforce
        for _zi in range(1, len(events)):
            if (events[_zi].get('Type') in _CLICK_TYPES
                    and events[_zi - 1].get('Type') == 'MouseMove'):
                _gap = events[_zi].get('Time', 0) - events[_zi - 1].get('Time', 0)
                if 0 <= _gap < _ZERO_GAP_THRESHOLD:
                    _shift = _ZERO_GAP_TARGET - _gap
                    for _j in range(_zi, len(events)):
                        events[_j]['Time'] = events[_j].get('Time', 0) + _shift

        # Check if dmwm file
        if is_dmwm:
            has_dmwm = True
        
        # Normalize timing — use pre-filter base so leading gaps are preserved
        base_time = base_time_pre_filter
        
        # PRE-FILE PAUSE: 0.8 seconds BEFORE file plays (FLAT, NO multiplier)
        # This prevents drag issues when previous file ended with a click!
        if cycle_events:
            # Random pause scaled by mult: base 500-800ms × mult
            pre_file_pause = rng.uniform(500.0, 800.0) * mult
            timeline += pre_file_pause

            # Track this pause
            total_pre_pause += pre_file_pause
            
            # NOW do cursor transition (AFTER pause, so click has time to release)
            # Get last position from previous file
            last_x, last_y = None, None
            for e in reversed(cycle_events):
                if e.get('X') is not None and e.get('Y') is not None:
                    last_x, last_y = int(e['X']), int(e['Y'])
                    break
            
            # Get first position of current file
            first_x, first_y = None, None
            for e in events:
                if e.get('X') is not None and e.get('Y') is not None:
                    first_x, first_y = int(e['X']), int(e['Y'])
                    break
            
            
            # CURSOR TRANSITION: skipped for click-sensitive folders
            # (no coordinate changes between files - cursor stays wherever it was)
            if not is_click_sensitive:
                transition_duration = rng.uniform(200.0, 400.0) * mult
                if last_x is not None and first_x is not None and (last_x != first_x or last_y != first_y):
                    transition_path = generate_human_path(
                        last_x, last_y, first_x, first_y,
                        int(transition_duration), rng
                    )
                    for rel_time, x, y in transition_path:
                        cycle_events.append({
                            'Type': 'MouseMove',
                            'Time': timeline + rel_time,
                            'X': x,
                            'Y': y
                        })
                    timeline += transition_duration
                    total_transition_time += int(transition_duration)
                    # Final snap to exact start position
                    cycle_events.append({
                        'Type': 'MouseMove',
                        'Time': timeline,
                        'X': first_x,
                        'Y': first_y
                    })
                    # POST-SNAP GAP
                    post_snap_gap = int(rng.uniform(80, 150))
                    timeline += post_snap_gap
                    total_snap_gap_time += post_snap_gap
        
        # Add events from current file
        for event in events:
            new_event = {**event}
            new_event['Time'] = event['Time'] - base_time + timeline
            cycle_events.append(new_event)
        
        # Update timeline and track THIS file's end time
        if cycle_events:
            timeline = cycle_events[-1]['Time']
            file_info_list.append((folder_num, file_label, is_dmwm, timeline))
        files_added += 1
    
    # Main cycle building
    cycle_events = []
    file_info_list = []
    timeline = 0
    has_dmwm = False
    
    files_added = 0  # Counts files added; guards pre-play buffer for every non-first file
    # NEW: Track pre-file pauses, post-pause delays, cursor transitions, and distraction durations
    total_pre_pause = 0
    total_transition_time = 0
    total_snap_gap_time = 0      # cumulative post-snap gaps (80-150ms per file transition)
    total_distraction_pause = 0  # cumulative duration of all inserted distraction files
    
    # SINGLE-SUBFOLDER MODE: if only one subfolder exists, always_first/last
    # should bracket the ENTIRE strung file (once at the very start, once at
    # the very end) rather than wrapping every single selected file.
    single_subfolder = len(subfolder_files) == 1
    if single_subfolder:
        # There is only one folder_num - grab its always_first/last once
        only_folder_num = next(iter(subfolder_files))
        only_folder_data = subfolder_files[only_folder_num]
        single_always_first = only_folder_data.get('always_first')
        single_always_last  = only_folder_data.get('always_last')
        # Play always_first only when flagged (outer loop controls first-cycle)
        if single_always_first and play_always_first:
            is_dmwm = single_always_first in dmwm_file_set
            add_file_to_cycle(single_always_first, only_folder_num, is_dmwm,
                              f"[ALWAYS FIRST] {single_always_first.name}")
    
    def _maybe_insert_distraction(cur_folder_num):
        """Roll the chance and insert one distraction file at the current timeline.
        Uses VirtualDistQueue so all 50 files play before any repeats."""
        nonlocal total_distraction_pause
        if not distraction_files or distraction_chance <= 0.0:
            return
        if rng.random() < distraction_chance:
            # distraction_files is a VirtualDistQueue when called from main()
            dist_path = (distraction_files.next()
                         if hasattr(distraction_files, 'next')
                         else rng.choice(distraction_files))
            t_before  = timeline
            add_file_to_cycle(dist_path, cur_folder_num, False,
                               f"[DISTRACTION] {dist_path.name}")
            total_distraction_pause += (timeline - t_before)

    def _play_nested_loop(nested_item):
        """Play ONE loop of the nested sub-cycle: F1->F2->F3->F4->optional.
        AF/AL are NOT included here - they wrap ALL loops, called once by the caller."""
        _sub_combo  = nested_item['combo']
        _nsf        = nested_item['nested_sf']
        for _sfn, _sfl in _sub_combo:
            _sfd = _nsf.get(_sfn, {})
            if not isinstance(_sfl, list):
                _sfl = [_sfl]
            _saf = _sfd.get('always_first')
            _sal = _sfd.get('always_last')
            if _saf:
                _is_dmwm = _saf in dmwm_file_set
                add_file_to_cycle(_saf, _sfn, _is_dmwm, f"[ALWAYS FIRST] {_saf.name}")
            for _fp in _sfl:
                if isinstance(_fp, dict) and _fp.get('_nested'):
                    _play_nested_loop(_fp)
                else:
                    _is_dmwm = _fp in dmwm_file_set
                    add_file_to_cycle(_fp, _sfn, _is_dmwm, _fp.name)
            if _sal:
                _is_dmwm = _sal in dmwm_file_set
                add_file_to_cycle(_sal, _sfn, _is_dmwm, f"[ALWAYS LAST] {_sal.name}")

    def _play_nested_group(nested_items_list):
        """Play all loops for a nested folder slot.
        AF fires ONCE before all loops; AL fires ONCE after all loops.
        Pattern: [AF] -> loop1 -> loop2 -> ... -> [AL]
        """
        if not nested_items_list:
            return
        _naf = nested_items_list[0].get('nested_root_af')
        _nal = nested_items_list[0].get('nested_root_al')
        if _naf:
            _is_dmwm = _naf in dmwm_file_set
            add_file_to_cycle(_naf, 0.0, _is_dmwm, f"[ALWAYS FIRST] {_naf.name}")
        for _ni in nested_items_list:
            _play_nested_loop(_ni)
        if _nal:
            _is_dmwm = _nal in dmwm_file_set
            add_file_to_cycle(_nal, 0.0, _is_dmwm, f"[ALWAYS LAST] {_nal.name}")

    for idx_combo, (folder_num, file_list) in enumerate(combination):
        folder_data = subfolder_files.get(folder_num, {})
        if not isinstance(file_list, list):
            file_list = [file_list]

        # DISTRACTION: maybe insert BEFORE this folder's files
        _maybe_insert_distraction(folder_num)

        # Separate nested dicts from regular file paths in this slot
        _nested_items = [it for it in file_list if isinstance(it, dict) and it.get('_nested')]
        _regular_items = [it for it in file_list if not (isinstance(it, dict) and it.get('_nested'))]

        if _nested_items:
            # Nested folder: AF once -> all loops -> AL once
            _play_nested_group(_nested_items)
        elif single_subfolder:
            # Single-subfolder: always_first/last already played above/below loop
            for item in _regular_items:
                is_dmwm = item in dmwm_file_set
                add_file_to_cycle(item, folder_num, is_dmwm, item.name)
        else:
            # Multi-subfolder: always_first/last wrap ONLY the files of their OWN folder.
            af = folder_data.get('always_first')
            al = folder_data.get('always_last')
            if af:
                is_dmwm = af in dmwm_file_set
                add_file_to_cycle(af, folder_num, is_dmwm, f"[ALWAYS FIRST] {af.name}")
            for item in _regular_items:
                is_dmwm = item in dmwm_file_set
                add_file_to_cycle(item, folder_num, is_dmwm, item.name)
            if al:
                is_dmwm = al in dmwm_file_set
                add_file_to_cycle(al, folder_num, is_dmwm, f"[ALWAYS LAST] {al.name}")

    # DISTRACTION: maybe insert AFTER the very last folder
    if combination:
        last_folder_num = combination[-1][0]
        _maybe_insert_distraction(last_folder_num)

    if single_subfolder and single_always_last and play_always_last:
        is_dmwm = single_always_last in dmwm_file_set
        add_file_to_cycle(single_always_last, only_folder_num, is_dmwm,
                          f"[ALWAYS LAST] {single_always_last.name}")

    return {
        'events': cycle_events,
        'file_info': file_info_list,
        'has_dmwm': has_dmwm,
        'pre_pause_total': total_pre_pause,
        'transition_total': total_transition_time,
        'snap_gap_total': total_snap_gap_time,
        'distraction_pause_total': total_distraction_pause,
    }


# ============================================================================
# DISTRACTION FILE GENERATION
# ============================================================================

# Windows Virtual Key codes for keyboard events
# (must be integers - the macro player does NOT accept strings)
_VK = {
    'a':8  # placeholder - built dynamically below
}
_VK = {}
for _c in 'abcdefghijklmnopqrstuvwxyz':
    _VK[_c] = ord(_c.upper())   # A=65 ? Z=90
_VK.update({
    '0': 48, '1': 49, '2': 50, '3': 51, '4': 52,
    '5': 53, '6': 54, '7': 55, '8': 56, '9': 57,
    'Back': 8,         # Backspace
    '.': 190, ',': 188, ';': 186, '/': 191,
    "'": 222, '[': 219, ']': 221, '\\': 220,
    '-': 189, '=': 187,
})


def _evt(type_, time, x=None, y=None, delta=None, keycode=None) -> dict:
    """
    Build a properly-structured macro event with ALL 6 required fields.
    The macro player expects Type, Time, X, Y, Delta, KeyCode on EVERY event.
    Keyboard events:  X=None, Y=None, Delta=None, KeyCode=<int VK code>
    Mouse events:     X=<int>, Y=<int>, Delta=None, KeyCode=None
    """
    return {
        'Type':    type_,
        'Time':    time,
        'X':       x,
        'Y':       y,
        'Delta':   delta,
        'KeyCode': keycode,
    }


# Common words / phrases a player might idly type then delete
_DISTRACTION_WORDS = [
    "nice", "lol", "gg", "hey", "ok", "sure", "brb", "back", "sec",
    "wait", "almost", "done", "yes", "no", "maybe", "idk", "nah",
    "yeah", "yep", "nope", "omg", "wow", "thanks", "ty", "np",
    "haha", "lmao", "ez", "rip", "oof", "yo", "kk",
    "cya", "afk", "gtg", "bbl", "wb", "ggwp", "niceone",
]

# Keys that players accidentally spam then erase (letters + symbols with VK mappings)
_SPAM_KEYS = list("asdfghjklqwertyuiopzxcvbnm/.,;'[]-=")


def _human_interval(rng, lo_ms: float, hi_ms: float) -> float:
    return rng.uniform(lo_ms, hi_ms)


def _safe_gap(rng) -> float:
    """Minimum advance so no two events share a timestamp."""
    return _human_interval(rng, 30.0, 120.0)


def _add_mouse_wander(events, timeline, rng, cur_x, cur_y):
    """
    Move cursor to 2-7 random destinations.
    Per-call: number of moves, speed envelope, and inter-move pause
    range are all re-randomised so no two wanders feel the same.
    Returns (timeline, x, y).
    """
    t = timeline + _safe_gap(rng)
    x, y = cur_x, cur_y
    # Randomise both envelope bounds so the RANGE of speeds varies per call
    spd_lo = rng.uniform(150.0, 500.0)
    spd_hi = rng.uniform(spd_lo + 200.0, spd_lo + 1200.0)
    gap_lo = rng.uniform(30.0, 150.0)
    gap_hi = rng.uniform(gap_lo + 100.0, gap_lo + 600.0)
    n_moves = rng.randint(2, 7)
    for _ in range(n_moves):
        tx = rng.randint(150, 950)
        ty = rng.randint(120, 620)
        seg_dur = _human_interval(rng, spd_lo, spd_hi)
        path = generate_human_path(x, y, tx, ty, int(seg_dur), rng)
        for rel, px, py in path:
            events.append(_evt('MouseMove', t + rel, px, py))
        t += seg_dur
        x, y = tx, ty
        t += _human_interval(rng, gap_lo, gap_hi)
    return t, x, y


def _add_cursor_pause(events, timeline, rng, cur_x, cur_y):
    """
    Stay still (or drift slightly) for a randomised duration.
    Drift probability, drift magnitude, and pause length all vary per call.
    Returns (timeline, x, y).
    """
    # Duration envelope randomised per call: 0.3s-4s range, but the actual
    # bounds shift so some calls are twitchy-short and some are long
    dur_lo = rng.uniform(300.0, 800.0)
    dur_hi = rng.uniform(dur_lo + 400.0, dur_lo + 2500.0)
    duration = _human_interval(rng, dur_lo, dur_hi)
    t_start  = timeline + _safe_gap(rng)
    # Drift: random probability AND random magnitude per call
    drift_prob = rng.uniform(0.20, 0.65)
    if rng.random() < drift_prob:
        drift_mag = rng.randint(3, 18)
        dx = max(100, min(1800, cur_x + rng.randint(-drift_mag, drift_mag)))
        dy = max(100, min(1000, cur_y + rng.randint(-drift_mag, drift_mag)))
        mid = t_start + duration * rng.uniform(0.2, 0.8)
        events.append(_evt('MouseMove', mid,              dx,    dy))
        events.append(_evt('MouseMove', t_start+duration, cur_x, cur_y))
    return t_start + duration, cur_x, cur_y


def _add_right_click(events, timeline, rng, cur_x, cur_y):
    """
    Approach a random nearby position then right-click.
    Approach speed, offset range, hover time, and hold duration all vary per call.
    Returns (timeline, x, y).
    """
    t  = timeline + _safe_gap(rng)
    # Randomise offset range per call: small twitch vs large repositioning
    off_x = rng.randint(20, 200)
    off_y = rng.randint(15, 140)
    tx = max(100, min(1800, cur_x + rng.randint(-off_x, off_x)))
    ty = max(100, min(1000, cur_y + rng.randint(-off_y, off_y)))
    spd_lo = rng.uniform(100.0, 300.0)
    move_dur = _human_interval(rng, spd_lo, spd_lo + rng.uniform(200.0, 700.0))
    path = generate_human_path(cur_x, cur_y, tx, ty, int(move_dur), rng)
    for rel, px, py in path:
        events.append(_evt('MouseMove', t + rel, px, py))
    t += move_dur
    cur_x, cur_y = tx, ty
    # Hover time randomised per call
    t += _human_interval(rng, 30.0, rng.uniform(100.0, 350.0))
    hold_lo = rng.uniform(40.0, 100.0)
    hold = _human_interval(rng, hold_lo, hold_lo + rng.uniform(80.0, 250.0))
    events.append(_evt('RightDown', t,        cur_x, cur_y))
    events.append(_evt('RightUp',   t + hold, cur_x, cur_y))
    # Post-click linger: sometimes brief, sometimes longer
    t += hold + _human_interval(rng, 80.0, rng.uniform(300.0, 900.0))
    return t, cur_x, cur_y


def _add_typing(events, timeline, rng, cur_x, cur_y):
    """
    Type a random word then erase it character by character.
    Typing speed, erasing speed, and hesitation pause all re-randomised
    per call so every typing event has its own rhythm.
    KeyCode = integer VK code, X/Y = None.
    """
    word = rng.choice(_DISTRACTION_WORDS)
    t    = timeline + _safe_gap(rng)
    # Per-call speed envelopes
    type_hold_lo = rng.uniform(40.0, 90.0)
    type_hold_hi = rng.uniform(type_hold_lo + 30.0, type_hold_lo + 120.0)
    type_gap_lo  = rng.uniform(50.0, 130.0)
    type_gap_hi  = rng.uniform(type_gap_lo + 40.0, type_gap_lo + 180.0)
    erase_hold_lo = rng.uniform(40.0, 100.0)
    erase_hold_hi = rng.uniform(erase_hold_lo + 30.0, erase_hold_lo + 110.0)
    erase_gap_lo  = rng.uniform(45.0, 110.0)
    erase_gap_hi  = rng.uniform(erase_gap_lo + 30.0, erase_gap_lo + 140.0)
    hesitation    = rng.uniform(100.0, rng.uniform(500.0, 3000.0))

    for ch in word:
        vk = _VK.get(ch, _VK.get(ch.lower()))
        if vk is None:
            continue
        hold = _human_interval(rng, type_hold_lo, type_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=vk))
        events.append(_evt('KeyUp',   t + hold, keycode=vk))
        t += hold + _human_interval(rng, type_gap_lo, type_gap_hi)
    t += hesitation
    bk = _VK['Back']
    for _ in word:
        hold = _human_interval(rng, erase_hold_lo, erase_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=bk))
        events.append(_evt('KeyUp',   t + hold, keycode=bk))
        t += hold + _human_interval(rng, erase_gap_lo, erase_gap_hi)
    return t


def _add_key_spam(events, timeline, rng, cur_x, cur_y):
    """
    Accidentally spam a key 2-9x, then erase with Backspace.
    Spam speed, erase speed, and the 'oh no' pause all re-randomised per call.
    KeyCode = integer VK code.
    """
    key   = rng.choice(_SPAM_KEYS)
    vk    = _VK.get(key)
    if vk is None:
        return timeline
    count = rng.randint(2, 9)
    t     = timeline + _safe_gap(rng)
    bk    = _VK['Back']
    # Spam envelope: sometimes key-repeat fast, sometimes deliberate
    spam_hold_lo = rng.uniform(25.0, 80.0)
    spam_hold_hi = rng.uniform(spam_hold_lo + 20.0, spam_hold_lo + 100.0)
    spam_gap_lo  = rng.uniform(15.0, 60.0)
    spam_gap_hi  = rng.uniform(spam_gap_lo + 15.0, spam_gap_lo + 80.0)
    # "Oh no" reaction: anywhere from a quick twitch to a long freeze
    ohno_pause = rng.uniform(150.0, rng.uniform(500.0, 1800.0))
    # Erase envelope: typically slower than spam (deliberate)
    erase_hold_lo = rng.uniform(45.0, 100.0)
    erase_hold_hi = rng.uniform(erase_hold_lo + 20.0, erase_hold_lo + 90.0)
    erase_gap_lo  = rng.uniform(40.0, 100.0)
    erase_gap_hi  = rng.uniform(erase_gap_lo + 20.0, erase_gap_lo + 110.0)

    for _ in range(count):
        hold = _human_interval(rng, spam_hold_lo, spam_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=vk))
        events.append(_evt('KeyUp',   t + hold, keycode=vk))
        t += hold + _human_interval(rng, spam_gap_lo, spam_gap_hi)
    t += ohno_pause
    for _ in range(count):
        hold = _human_interval(rng, erase_hold_lo, erase_hold_hi)
        events.append(_evt('KeyDown', t,        keycode=bk))
        events.append(_evt('KeyUp',   t + hold, keycode=bk))
        t += hold + _human_interval(rng, erase_gap_lo, erase_gap_hi)
    return t


def _add_shape_movement(events, timeline, rng, cur_x, cur_y):
    """
    Trace a geometric shape: circle/donut (3-5 laps), triangle, square,
    rectangle, or star. Each shape has per-point jitter and varied speed
    so it reads human, not robotic.

    Returns (new_timeline, new_x, new_y).
    """
    shape = rng.choice(['circle', 'triangle', 'square', 'rectangle', 'star'])
    t     = timeline + _safe_gap(rng)

    # Speed factor: how long each segment between waypoints takes (ms).
    # Drawn once per shape so the whole shape is consistently fast or slow.
    ms_per_seg = rng.uniform(80.0, 400.0)   # fast (~80ms) to leisurely (~400ms)
    jitter_px  = rng.uniform(3.0, 10.0)     # positional jitter magnitude

    def _trace_waypoints(wpts):
        """Move through a list of (x, y) waypoints with jitter and human paths."""
        nonlocal t, cur_x, cur_y
        px, py = cur_x, cur_y
        for wx, wy in wpts:
            # Jitter: slightly randomise each target point
            wx = int(max(100, min(1800, wx + rng.uniform(-jitter_px, jitter_px))))
            wy = int(max(100, min(1000, wy + rng.uniform(-jitter_px, jitter_px))))
            # Per-segment time varies +/-40% for natural rhythm
            seg = ms_per_seg * rng.uniform(0.6, 1.4)
            path = generate_human_path(px, py, wx, wy, int(seg), rng)
            for rel, ex, ey in path:
                events.append(_evt('MouseMove', t + rel, ex, ey))
            t  += seg
            px, py = wx, wy
        return px, py

    # ------------------------------------------------------------------ circle
    if shape == 'circle':
        radius = rng.randint(60, 180)
        # Keep center so shape stays fully on screen
        cx = int(max(100 + radius, min(1800 - radius, cur_x + rng.randint(-120, 120))))
        cy = int(max(100 + radius, min(1000 - radius, cur_y + rng.randint(-100, 100))))
        laps   = rng.randint(3, 5)
        steps  = rng.randint(20, 36)   # points per lap (10-18 degree increments)
        wpts   = []
        for lap in range(laps):
            for s in range(steps):
                angle = (s / steps) * 2 * math.pi
                wpts.append((
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                ))
        last_x, last_y = _trace_waypoints(wpts)

    # --------------------------------------------------------------- triangle
    elif shape == 'triangle':
        spread = rng.randint(80, 220)
        # Generate 3 vertices roughly equilateral around current position
        vertices = []
        for k in range(3):
            angle = (k / 3) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            vx = cur_x + spread * math.cos(angle)
            vy = cur_y + spread * math.sin(angle)
            vertices.append((vx, vy))
        laps = rng.randint(1, 3)
        wpts = vertices * laps + [vertices[0]]   # close the last lap
        last_x, last_y = _trace_waypoints(wpts)

    # ----------------------------------------------------------------- square
    elif shape == 'square':
        side = rng.randint(80, 200)
        x0   = int(max(100, min(1800 - side, cur_x - side // 2)))
        y0   = int(max(100, min(1000 - side, cur_y - side // 2)))
        corners = [(x0, y0), (x0 + side, y0),
                   (x0 + side, y0 + side), (x0, y0 + side)]
        laps = rng.randint(1, 3)
        wpts = corners * laps + [corners[0]]
        last_x, last_y = _trace_waypoints(wpts)

    # -------------------------------------------------------------- rectangle
    elif shape == 'rectangle':
        w  = rng.randint(120, 280)
        h  = rng.randint(60,  160)
        x0 = int(max(100, min(1800 - w, cur_x - w // 2)))
        y0 = int(max(100, min(1000 - h, cur_y - h // 2)))
        corners = [(x0, y0), (x0 + w, y0),
                   (x0 + w, y0 + h), (x0, y0 + h)]
        laps = rng.randint(1, 3)
        wpts = corners * laps + [corners[0]]
        last_x, last_y = _trace_waypoints(wpts)

    # ------------------------------------------------------------------- star
    else:   # star
        outer_r = rng.randint(80, 160)
        inner_r = int(outer_r * rng.uniform(0.35, 0.55))
        points  = 5
        laps    = rng.randint(1, 2)
        wpts    = []
        for lap in range(laps):
            for k in range(points * 2):
                # Alternate outer/inner radius
                r     = outer_r if k % 2 == 0 else inner_r
                angle = (k / (points * 2)) * 2 * math.pi - math.pi / 2
                wpts.append((
                    cur_x + r * math.cos(angle),
                    cur_y + r * math.sin(angle),
                ))
        wpts.append(wpts[0])   # close shape
        last_x, last_y = _trace_waypoints(wpts)

    return t, int(last_x), int(last_y)



def generate_distraction_files(distractions_src_folder, out_folder, rng,
                                count: int = 50,
                                bundle_id: int = 0) -> int:
    """
    Generate `count` distraction files.
    Each file uses exactly 3 randomly-chosen features from {wander, pause,
    right_click, type, key_spam}.
    All events follow the exact 6-field macro schema:
      Type, Time, X, Y, Delta, KeyCode  (Delta/KeyCode None where unused)
    KeyCode values are Windows VK integers, never strings.
    No left clicks. Duration 1-3 min (float ms, rounded only at save).
    Per-feature cooldown: 17-40 s between successive triggers of the same
    feature, calculated in float ms, unique per feature per file.
    """
    from pathlib import Path as _Path
    out_folder = _Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    # 6 features - each file picks 3 at random.
    ACTION_WEIGHTS = [
        ('wander',      20),
        ('pause',       15),
        ('right_click', 22),
        ('type',        20),
        ('key_spam',    12),
        ('shapes',      21),
    ]
    action_names = [a[0] for a in ACTION_WEIGHTS]
    action_wts   = [a[1] for a in ACTION_WEIGHTS]

    written = 0
    for i in range(count):
        file_rng = random.Random(rng.random())
        target   = file_rng.uniform(30000.0, 120000.0)

        # Pick exactly 3 features for this file
        chosen     = file_rng.sample(action_names, 3)
        chosen_wts = [w for a, w in ACTION_WEIGHTS if a in chosen]

        events   = []
        timeline = 0.0
        cur_x    = file_rng.randint(300, 700)
        cur_y    = file_rng.randint(250, 450)
        last_act = None

        # Shared cooldown: after any action fires, ALL features are locked out
        # for a single random window of 17 000-30 000 ms (float ms, never rounded).
        # A fresh cooldown is drawn each time any feature triggers, so the gap
        # between every pair of consecutive actions is independently randomised.
        next_allowed_any = 0.0   # earliest ms any action may next fire

        # OVERLAP CONTROL
        # Sequential fraction: random decimal in [90.0, 95.0] percent.
        # For that share of triggers, the next action must wait until the
        # previous one has fully finished playing (action_busy_until).
        # For the remaining (100 - sequential_pct)% of triggers, the new action
        # may start while the previous is still playing (overlap allowed).
        sequential_pct  = file_rng.uniform(90.0, 95.0)   # e.g. 92.47%
        sequential_frac = sequential_pct / 100.0          # e.g. 0.9247
        action_busy_until = 0.0   # absolute ms when last action's events end

        # Opening move
        tx       = file_rng.randint(150, 950)
        ty       = file_rng.randint(120, 620)
        open_dur = _human_interval(file_rng, 350.0, 950.0)
        path     = generate_human_path(cur_x, cur_y, tx, ty, int(open_dur), file_rng)
        for rel, px, py in path:
            events.append(_evt('MouseMove', timeline + rel, px, py))
        timeline += open_dur
        action_busy_until = timeline
        cur_x, cur_y = tx, ty

        while timeline < target:
            # Wait for the shared cooldown window to expire
            if timeline < next_allowed_any:
                timeline = next_allowed_any + _human_interval(file_rng, 10.0, 80.0)
                action_busy_until = max(action_busy_until, timeline)

            # Actions available = chosen set minus consecutive-pause block
            available = [
                a for a in chosen
                if not (a == 'pause' and last_act == 'pause')
            ]

            if not available:
                # Only happens if all 3 chosen features are 'pause' (impossible
                # with sample(3)), but guard anyway
                last_act = None
                continue

            avail_wts = [w for a, w in ACTION_WEIGHTS if a in available]
            action    = file_rng.choices(available, weights=avail_wts, k=1)[0]

            # Decide: sequential (wait for previous to finish) or overlap?
            if file_rng.random() < sequential_frac:
                start_t = max(timeline, action_busy_until) + _safe_gap(file_rng)
            else:
                start_t = timeline + _safe_gap(file_rng)

            timeline = start_t

            if action == 'wander':
                timeline, cur_x, cur_y = _add_mouse_wander(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'pause':
                timeline, cur_x, cur_y = _add_cursor_pause(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'right_click':
                timeline, cur_x, cur_y = _add_right_click(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'type':
                timeline = _add_typing(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'key_spam':
                timeline = _add_key_spam(events, timeline, file_rng, cur_x, cur_y)
            elif action == 'shapes':
                timeline, cur_x, cur_y = _add_shape_movement(events, timeline, file_rng, cur_x, cur_y)

            action_busy_until = timeline

            # Draw a fresh shared cooldown after every trigger (float ms, never rounded)
            cooldown = file_rng.uniform(17000.0, 30000.0)
            next_allowed_any = timeline + cooldown

            last_act = action
            if timeline <= 0:
                timeline = 1.0

        if not events:
            continue

        # Normalise times and enforce no zero-gaps
        base = min(e['Time'] for e in events)
        for e in events:
            e['Time'] = max(0, int(round(e['Time'] - base)))
        events.sort(key=lambda e: e['Time'])
        for j in range(1, len(events)):
            if events[j]['Time'] <= events[j-1]['Time']:
                events[j]['Time'] = events[j-1]['Time'] + 1

        # Trim any events that spilled past target due to cooldown overshoot.
        target_ms_int = int(round(target))
        events = [e for e in events if e['Time'] <= target_ms_int]
        if not events:
            continue

        # Ensure the file's duration matches its target (within 1s tolerance).
        # Cursor idle time during cooldown gaps produces no events, so the last
        # event may land well before target. A final anchor MouseMove captures
        # "cursor held still" and gives the file the correct playback length.
        if events[-1]['Time'] < target_ms_int - 1000:
            last_x = next((e['X'] for e in reversed(events) if e.get('X') is not None), cur_x)
            last_y = next((e['Y'] for e in reversed(events) if e.get('Y') is not None), cur_y)
            events.append({
                'Type': 'MouseMove', 'Time': target_ms_int,
                'X': int(last_x), 'Y': int(last_y),
                'Delta': None, 'KeyCode': None,
            })

        total_ms  = events[-1]['Time']
        total_min = total_ms // 60000
        total_sec = (total_ms % 60000) // 1000
        fname     = f"DISTRACTION_{str(i+1).zfill(2)}_{total_min}m{total_sec}s.json"
        (out_folder / fname).write_text(json.dumps(events, indent=2))
        written += 1

    return written

def apply_cycle_features(cycle_events, rng, is_raw, has_dmwm, is_inef=False,
                          is_click_sensitive=False, mult=1.0):
    """
    Apply anti-detection features to a complete cycle.

    Args:
        cycle_events: Events from one complete cycle
        rng: Random generator
        is_raw:  If True, 0% within-file pause (no pauses inserted)
        is_inef: If True, 15% within-file pause; False = 5% (normal)
        has_dmwm: If True, skip ALL modifications
        is_click_sensitive: If True, skip jitter and idle mouse movements
                            (no coordinate-changing features applied)

    Returns:
        (processed_events, stats)
    """
    stats = {
        'jitter_count': 0,
        'total_moves': 0,
        'jitter_percentage': 0.0,
        'intra_pauses': 0,
        'idle_movements': 0
    }

    if has_dmwm:
        return cycle_events, stats

    # Step 1: Jitter - SKIPPED for click-sensitive folders
    if not is_click_sensitive:
        events_with_jitter, jitter_count, move_count, jitter_pct = add_pre_click_jitter(cycle_events, rng)
        stats['jitter_count'] = jitter_count
        stats['total_moves'] = move_count
        stats['jitter_percentage'] = jitter_pct
    else:
        events_with_jitter = cycle_events

    # Step 2: Rapid click detection
    protected_ranges = detect_rapid_click_sequences(events_with_jitter)

    # Step 3: Within-file pause (percentage-based, range chosen per call)
    #   Raw: 0%   Normal: 2-5%   Inefficient: 10-15%
    file_type = 'raw' if is_raw else ('inef' if is_inef else 'normal')
    events_with_pauses, pause_time = insert_intra_file_pauses(
        events_with_jitter, rng, protected_ranges, file_type=file_type
    )
    stats['intra_pauses'] = pause_time

    # Step 3b: Multiplier-driven random mid-event pause (50% chance per cycle)
    # The multiplier can express itself as a short natural hesitation inserted
    # directly between recorded events rather than only making buffers longer.
    # Duration: rng.uniform(200, 800) * mult ms. Skipped for raw + click-sensitive.
    if not is_raw and not is_click_sensitive and rng.random() < 0.50:
        _mid_ms = rng.uniform(200.0, 800.0) * mult
        _drag_idx = build_drag_index_set(events_with_pauses)
        _p_set = set()
        for _s, _e in protected_ranges:
            for _k in range(_s, _e + 1):
                _p_set.add(_k)
        _fs = max(1, int(len(events_with_pauses) * 0.10))
        _ls = min(len(events_with_pauses) - 1, int(len(events_with_pauses) * 0.90))
        _valid = [
            _i for _i in range(_fs, _ls)
            if _i not in _p_set and _i not in _drag_idx
            and events_with_pauses[_i].get('Type') != 'DragStart'
            and (_i + 1 >= len(events_with_pauses)
                 or events_with_pauses[_i + 1].get('Type') != 'DragStart')
        ]
        if _valid:
            _ins = rng.choice(_valid)
            for _j in range(_ins, len(events_with_pauses)):
                events_with_pauses[_j]['Time'] = events_with_pauses[_j].get('Time', 0) + _mid_ms
            stats['intra_pauses'] += _mid_ms

    # Step 4: Idle movements - SKIPPED for click-sensitive folders
    if not is_click_sensitive:
        movement_pct = rng.uniform(0.40, 0.50)
        events_with_idle, idle_time = insert_idle_mouse_movements(
            events_with_pauses, rng, movement_pct
        )
        stats['idle_movements'] = idle_time
    else:
        events_with_idle = events_with_pauses

    return events_with_idle, stats



# ============================================================================
# FOLDER SCANNING
# ============================================================================

def scan_for_numbered_subfolders(base_path):
    """
    Scans folder for subfolders with numbers in their names.
    Also checks for "dont mess with me" subfolder and "optional" folders.
    
    NEW: Checks main folder name for "time sensitive" tag.
    If main folder is tagged, ALL subfolders become time_sensitive!
    
    Accepts: "1", "part1", "step2", "3-action", "3 optional- walk", "3.5- insert", etc.
    DECIMAL SUPPORT: "3.5" will be placed after "3" and before "4"
    
    Returns tuple: (numbered_folders_dict, dmwm_file_set, non_json_files_list)
    
    numbered_folders: {num: {'files': [...], 'is_optional': bool}}
    dmwm_file_set: set of files from "dont mess with me"
    non_json_files: [list of non-JSON files to copy]
    """
    base = Path(base_path)
    numbered_folders = {}
    unmodified_files = []
    non_json_files = []
    
    # Check if MAIN FOLDER is tagged - propagates to ALL subfolders
    _base_lower = base.name.lower()
    main_folder_time_sensitive  = 'time sensitive'  in _base_lower
    main_folder_click_sensitive = (
        'click sensitive'      in _base_lower or   # plain: "click sensitive"
        'click/time sensitive' in _base_lower or   # slash: "click/time sensitive"
        'click+time sensitive' in _base_lower or   # plus:  "click+time sensitive"
        'click time sensitive' in _base_lower      # space: "click time sensitive"
    )

    if main_folder_time_sensitive:
        print(f"  ??  MAIN FOLDER is TIME SENSITIVE - All subfolders will skip inefficient files!")
    if main_folder_click_sensitive:
        print(f"  ?  MAIN FOLDER is CLICK SENSITIVE - All subfolders will skip cursor/jitter/idle/distraction features!")
    
    for item in base.iterdir():
        if not item.is_dir():
            # Collect non-JSON files in root
            if not item.name.endswith('.json'):
                non_json_files.append(item)
            continue
        
        # Check for "Don't use features on me" folder (case-insensitive)
        # Also accepts old name "dont mess with me" for backward compatibility
        folder_name_lower = item.name.lower()
        if folder_name_lower == "don't use features on me" or folder_name_lower == "dont mess with me":
            # Add all JSON files from this folder as unmodified
            dmwm_files = sorted(item.glob("*.json"))
            unmodified_files.extend(dmwm_files)
            print(f"  [!]?  Found 'Don't use features on me' folder: {len(dmwm_files)} unmodified files")
            continue
        
        # Extract folder number - prefer explicit F<N> prefix (F1, F2, F3.5, etc.)
        # so that other numbers in the name (e.g. 'press 1', 'optional-2-') are ignored.
        _f_match = re.match(r'^[Ff](\d+(?:\.\d+)?)', item.name.strip())
        if _f_match:
            folder_num = float(_f_match.group(1))   # e.g. F3.5 -> 3.5
        else:
            # Fall back: first number anywhere (handles '1- mine', '3.5 optional- ...')
            _n_match = re.search(r'\d+\.?\d*', item.name)
            folder_num = float(_n_match.group()) if _n_match else None
        if folder_num is not None:
            all_json_files = sorted(item.glob("*.json"))
            
            # Separate "always first", "always last", and regular files
            always_first = None
            always_last = None
            regular_files = []
            
            for json_file in all_json_files:
                filename_lower = json_file.name.lower()
                if 'always first' in filename_lower or 'alwaysfirst' in filename_lower:
                    always_first = json_file
                    print(f"   Found 'always first' in folder {folder_num}: {json_file.name}")
                elif 'always last' in filename_lower or 'alwayslast' in filename_lower:
                    always_last = json_file
                    print(f"   Found 'always last' in folder {folder_num}: {json_file.name}")
                else:
                    regular_files.append(json_file)
            
            # Check if folder is "optional" (default 24-33%, or custom % from tag)
            is_optional = 'optional' in item.name.lower()
            optional_chance = parse_optional_chance(item.name) if is_optional else None
            
            # Check if folder is "end" (becomes definitive end point)
            is_end = bool(re.search(r'\bend\b', item.name, re.IGNORECASE))
            
            # Check if folder is "time sensitive" (1:1 raw:normal, no inef, minimal overhead)
            # Priority: Main folder tag > Individual subfolder tag
            if main_folder_time_sensitive:
                is_time_sensitive = True  # Main folder overrides all
            else:
                is_time_sensitive = 'time sensitive' in item.name.lower()

            # Check if folder is "click sensitive" (no cursor pathing between files)
            item_lower = item.name.lower()
            is_click_time_sensitive = ('click/time sensitive' in item_lower
                                       or 'click+time sensitive' in item_lower
                                       or 'click time sensitive' in item_lower)
            is_click_sensitive      = (('click sensitive' in item_lower)
                                       and not is_click_time_sensitive)
            # click/time sensitive implies both flags
            if is_click_time_sensitive:
                is_time_sensitive    = True
                is_click_sensitive   = True
            # Main folder tag propagates to all subfolders
            if main_folder_click_sensitive:
                is_click_sensitive = True

            # "optional+end" combo: optional folder that ends loop if chosen
            is_optional_end = is_optional and is_end

            # Detect nested numbered subfolders (e.g. F5 that has its own F1/F2/F3 inside)
            nested_subfolder_files = None
            nested_root_af = None
            nested_root_al = None
            if not regular_files:
                # No direct JSON files — check if there are numbered sub-subfolders
                _nested_subdirs = [
                    d for d in item.iterdir()
                    if d.is_dir() and re.search(r'^[Ff]?\d', d.name.strip())
                ]
                if _nested_subdirs:
                    # Recursively scan the nested folder
                    _nf, _nd, _nnj, _naf, _nal = scan_for_numbered_subfolders(item)
                    if _nf:
                        nested_subfolder_files = _nf
                        nested_root_af = _naf
                        nested_root_al = _nal
                        print(f"  Nested folder detected: {item.name} has {len(_nf)} sub-folders inside")

            if regular_files or nested_subfolder_files:
                numbered_folders[folder_num] = {
                    'files': regular_files,
                    'is_optional': is_optional,
                    'optional_chance': optional_chance,
                    'is_end': is_end,
                    'is_optional_end': is_optional_end,
                    'is_time_sensitive': is_time_sensitive,
                    'is_click_sensitive': is_click_sensitive,
                    'max_files': parse_max_files(item.name),
                    'always_first': always_first,
                    'always_last': always_last,
                    'nested_subfolder_files': nested_subfolder_files,
                    'nested_root_always_first': nested_root_af,
                    'nested_root_always_last': nested_root_al,
                    'folder_name': item.name,   # stored for name-lookup in specific-folders
                    'folder_path': item,
                }

            # Also collect non-JSON files from numbered folders
            for file in item.iterdir():
                if file.is_file() and not file.name.endswith('.' + 'json'):
                    non_json_files.append(file)
    
    # FLAT FOLDER SUPPORT:
    # If no numbered subfolders were found, check if there are JSON files
    # sitting directly in the folder itself. If so, treat the folder as a
    # single virtual subfolder (number 1.0) so everything downstream works
    # without any changes.
    if not numbered_folders:
        direct_json = sorted(base.glob('*.json'))
        
        # Exclude logout files from the pool
        logout_names = {'logout.json', '- logout.json', '-logout.json'}
        direct_json = [f for f in direct_json if f.name.lower() not in logout_names]
        
        if direct_json:
            # Separate always_first / always_last from regular files
            always_first = None
            always_last = None
            regular_files = []
            for json_file in direct_json:
                name_lower = json_file.name.lower()
                if 'always first' in name_lower or 'alwaysfirst' in name_lower:
                    always_first = json_file
                    print(f"   Found 'always first': {json_file.name}")
                elif 'always last' in name_lower or 'alwayslast' in name_lower:
                    always_last = json_file
                    print(f"   Found 'always last': {json_file.name}")
                else:
                    regular_files.append(json_file)
            
            if regular_files:
                print(f"   Flat folder detected - {len(regular_files)} file(s) treated as single pool (subfolder 1.0)")
                numbered_folders[1.0] = {
                    'files': regular_files,
                    'is_optional': False,
                    'optional_chance': None,
                    'is_end': False,
                    'is_optional_end': False,
                    'is_time_sensitive': main_folder_time_sensitive,
                    'is_click_sensitive': main_folder_click_sensitive,
                    'always_first': always_first,
                    'always_last': always_last
                }

    # Scan root-level JSON files for always_first / always_last even when
    # numbered subfolders exist. These wrap the ENTIRE strung file once —
    # not per cycle, not per subfolder. Separate from subfolder-level always tags.
    root_always_first = None
    root_always_last  = None
    if numbered_folders:  # only meaningful when there are actual subfolders
        for _rf in sorted(base.glob('*.json')):
            _name = _rf.name.lower()
            if 'always first' in _name or 'alwaysfirst' in _name:
                root_always_first = _rf
                print(f"  Found root-level 'always first': {_rf.name}")
            elif 'always last' in _name or 'alwayslast' in _name:
                root_always_last = _rf
                print(f"  Found root-level 'always last': {_rf.name}")

    # Add unmodified files to their respective numbered folder pools
    # They become regular files, just tracked separately
    dmwm_file_set = set(unmodified_files)

    return numbered_folders, dmwm_file_set, non_json_files, root_always_first, root_always_last

# ============================================================================
# SIMPLE PERSISTENT HISTORY (Like Bundle Counter!)
# ============================================================================


class ManualHistoryTracker:
    """
    Manual combination history - YOU upload combination files!
    
    Folder: input_macros/combination_history/
    
    Code reads ALL .txt files in that folder and ensures no duplicate combinations.
    You manually dump combination files from each bundle's output to this folder.
    
    Files can be named anything, code reads them all:
    - COMBINATION_HISTORY_39.txt
    - combos_from_bundle_40.txt
    - anything.txt
    
    All will be read and combined into one set of used combinations.
    """
    def __init__(self, subfolder_files, rng, folder_name, input_dir):
        self.subfolder_files = subfolder_files
        self.rng = rng
        self.folder_name = folder_name
        self.input_dir = input_dir
        
        # History folder (not a single file!)
        self.history_dir = input_dir / "combination_history"
        
        # Load ALL combinations from ALL files in the folder
        self.used_combinations = self._load_all_combinations()

        # Per-subfolder virtual queues: each subfolder gets its own shuffled
        # queue so no file repeats until all files in that subfolder are used.
        self._file_queues = {}   # {folder_num: [shuffled file paths]}
        for fn, fd in self.subfolder_files.items():
            pool = list(fd.get('files', []))
            self.rng.shuffle(pool)
            self._file_queues[fn] = pool

        # Nested trackers: for subfolders that contain their own sub-subfolders,
        # maintain a separate ManualHistoryTracker for each.
        self._nested_trackers = {}
        for fn, fd in self.subfolder_files.items():
            nsf = fd.get('nested_subfolder_files')
            if nsf:
                self._nested_trackers[fn] = ManualHistoryTracker(
                    nsf, self.rng, f"{self.folder_name}_nested_{fn}", self.input_dir
                )
        
        print(f"   {len(self.used_combinations)} combinations loaded from history")
        print(f"   History folder: {self.history_dir}")
    
    def _load_all_combinations(self):
        """Read ALL .txt files in history folder and build set of used combos"""
        all_used = set()
        
        if not self.history_dir.exists():
            print(f"   No history folder found (will skip tracking)")
            return all_used
        
        # Read ALL .txt files
        txt_files = list(self.history_dir.glob("*.txt"))
        if not txt_files:
            print(f"   History folder empty (no .txt files)")
            return all_used
        
        print(f"   Reading {len(txt_files)} history file(s)...")
        
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        
                        # Skip empty lines and headers
                        if not line or line.startswith('[') or line.startswith('='):
                            continue
                        
                        # Check if line is a combination (has F1=, F2=, etc.)
                        if 'F' in line and '=' in line and '|' in line:
                            # Extract just the folder name part if it's in [Folder: ...] format
                            if line.startswith('[') and ']' in line:
                                continue  # Skip section headers
                            
                            # This is a combination line
                            # Check if it matches current folder
                            # Format could be: F1=F1 (22).json|F2=F2 (39).json|F3=F3 (1).json
                            all_used.add(line)
                
                print(f"    [OK] {txt_file.name}: Loaded")
                
            except Exception as e:
                print(f"    [!]?  {txt_file.name}: Error - {e}")
        
        return all_used
    
    def _next_file(self, folder_num):
        """Return the next file from this subfolder's virtual queue.
        Refills and reshuffles when exhausted - no file repeats until all used.
        Boundary guard prevents the last file of one pass from being the first
        of the next pass (cross-boundary consecutive repeat)."""
        q = self._file_queues.get(folder_num)
        if not q:
            pool = list(self.subfolder_files.get(folder_num, {}).get('files', []))
            if not pool:
                return None
            self.rng.shuffle(pool)
            # Boundary guard: if the last item would repeat the previous pick,
            # swap it with a random other position
            last_key = f"_last_{folder_num}"
            last = getattr(self, last_key, None)
            if last is not None and len(pool) > 1 and pool[-1] == last:
                swap = self.rng.randint(0, len(pool) - 2)
                pool[-1], pool[swap] = pool[swap], pool[-1]
            self._file_queues[folder_num] = pool
            q = self._file_queues[folder_num]
        item = q.pop()
        setattr(self, f"_last_{folder_num}", item)
        return item

    def get_next_combination(self):
        """Get next unused combination (with end folder support)"""
        max_attempts = 500
        
        for _ in range(max_attempts):
            # Pick random combination
            combination = []
            for folder_num in sorted(self.subfolder_files.keys()):
                folder_data = self.subfolder_files[folder_num]
                
                # Check for "optional+end" combo (optional folder that ends loop if chosen)
                if folder_data.get('is_optional_end', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() < optional_chance:
                        # Optional/end folder was chosen - include it and STOP
                        _f = self._next_file(folder_num)
                        if _f: combination.append((folder_num, [_f]))
                        break  # End the loop here
                    else:
                        # Optional/end folder was skipped - continue to next folders
                        continue
                
                # Check for regular "end" folder (always included, always ends loop)
                if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                    # End folder - include it and STOP
                    _f = self._next_file(folder_num)
                    if _f: combination.append((folder_num, [_f]))
                    break  # End the loop here
                
                # Regular optional folder check (uses random 27-43% chance stored per folder)
                if folder_data.get('is_optional', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() >= optional_chance:
                        continue
                
                # Nested folder: build sub-combinations instead of picking files
                _nsf = folder_data.get('nested_subfolder_files')
                _max = folder_data.get('max_files', 1)
                _n = self.rng.randint(1, _max) if _max > 1 else 1
                if _nsf and folder_num in self._nested_trackers:
                    _nested_tracker = self._nested_trackers[folder_num]
                    _picked_nested = []
                    for _ in range(_n):
                        _sub_combo = _nested_tracker.get_next_combination()
                        if _sub_combo:
                            _picked_nested.append({
                                '_nested': True,
                                'combo': _sub_combo,
                                'nested_sf': _nsf,
                                'nested_root_af': folder_data.get('nested_root_always_first'),
                                'nested_root_al': folder_data.get('nested_root_always_last'),
                            })
                    if _picked_nested:
                        combination.append((folder_num, _picked_nested))
                else:
                    # Regular folder: pick files from virtual queue
                    _picked = []
                    for _ in range(_n):
                        _f = self._next_file(folder_num)
                        if _f:
                            _picked.append(_f)
                    if _picked:
                        combination.append((folder_num, _picked))
            
            if not combination:
                continue
            
            # Create signature (format folder numbers cleanly)
            signature = "|".join(
                f"F{int(fn) if fn == int(fn) else fn}=" +
                "+".join(fp.name if hasattr(fp, "name") else f"nested_{i}" for i, fp in enumerate(fl if isinstance(fl, list) else [fl]))
                for fn, fl in combination
            )
            
            # Check if unused
            if signature not in self.used_combinations:
                self.used_combinations.add(signature)  # Mark as used
                return combination
        
        # Fallback: return random (may repeat)
        print(f"  [!]?  Using random combination (may repeat)")
        combination = []
        for folder_num in sorted(self.subfolder_files.keys()):
            folder_data = self.subfolder_files[folder_num]
            
            # Handle optional+end
            if folder_data.get('is_optional_end', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() < optional_chance:
                    _f = self._next_file(folder_num)
                    if _f: combination.append((folder_num, [_f]))
                    break
                else:
                    continue
            
            # Handle regular end
            if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                files = folder_data['files']
                _f = self._next_file(folder_num)
                if _f: combination.append((folder_num, [_f]))
                break
            
            # Handle regular optional
            if folder_data.get('is_optional', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() >= optional_chance:
                    continue
            
            _f = self._next_file(folder_num)
            if _f: combination.append((folder_num, [_f]))
        
        return combination if combination else None


class VirtualDistQueue:
    """
    Virtual queue for distraction file selection (Feature 23).
    Works identically to the virtual queue used for macro file selection:
    - All 50 distraction files are shuffled into a queue at construction
    - Files are popped one at a time; no file repeats until ALL have been used
    - When the queue is exhausted it re-shuffles the full pool and starts again
    - Boundary guard: the first item of a new shuffle is never the same as
      the last item of the previous pass, preventing cross-boundary repeats
    - Each shuffle uses the shared rng so order varies per bundle
    """
    def __init__(self, files: list, rng):
        self._pool = list(files)
        self._rng  = rng
        self._queue: list = []
        self._last: object = None
        self._refill()

    def _refill(self):
        self._queue = list(self._pool)
        self._rng.shuffle(self._queue)
        # Prevent cross-boundary consecutive repeat
        if self._last is not None and len(self._queue) > 1 and self._queue[-1] == self._last:
            # Swap the would-be-first item with a random other position
            swap_idx = self._rng.randint(0, len(self._queue) - 2)
            self._queue[-1], self._queue[swap_idx] = self._queue[swap_idx], self._queue[-1]

    def next(self):
        if not self._queue:
            self._refill()
        item = self._queue.pop()
        self._last = item
        return item


def main():
    parser = argparse.ArgumentParser(description="String Macros v3.1.0")
    parser.add_argument("input_root", type=str)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--versions", type=int, default=12, help="Total versions (default: 12 = 3 Raw + 3 Inef + 6 Normal)")
    parser.add_argument("--target-minutes", type=int, default=35)
    parser.add_argument("--bundle-id", type=int, required=True)
    parser.add_argument("--no-chat", action="store_true", help="Disable chat inserts")
    parser.add_argument("--specific-folders", type=str, help="Path to file with specific folder names to include (one per line)")
    args = parser.parse_args()
    
    print("="*70)
    print(f"STRING MACROS v{VERSION}")
    print("="*70)
    print(f"Bundle ID: {args.bundle_id}")
    print(f"Target: {args.target_minutes} minutes per file")
    print(f"Versions: {args.versions} total (3 Raw + 3 Inef + 6 Normal)")
    print(f"Chat: {'DISABLED' if args.no_chat else 'ENABLED (50% chance)'}")
    print("="*70)
    
    # Setup
    search_base = Path(args.input_root).resolve()
    if not search_base.exists():
        print(f"[X] Input root not found: {search_base}")
        return
    
    output_root = Path(args.output_root).resolve()
    bundle_dir = output_root / f"stringed_bundle_{args.bundle_id}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Load chat files
    chat_files = []
    if not args.no_chat:
        chat_dir = Path(args.input_root).parent / "chat inserts"
        if chat_dir.exists() and chat_dir.is_dir():
            chat_files = list(chat_dir.glob("*.json"))
            if chat_files:
                print(f"? Found {len(chat_files)} chat insert files")
    
    # Scan for DISTRACTIONS trigger - accepts either:
    #   A) A folder named "DISTRACTIONS" (case-insensitive) containing >=1 .json
    #   B) A single file named "distraction_file.json" (or similar) at root level
    # Either presence activates the feature; the trigger content is irrelevant.
    distractions_src = None

    # Option A: folder-based trigger (original behaviour)
    for candidate in [search_base / "DISTRACTIONS",
                       search_base / "distractions",
                       search_base / "Distractions"]:
        if candidate.exists() and candidate.is_dir():
            distractions_src = candidate
            break
    if distractions_src is None:
        for candidate in [search_base.parent / "DISTRACTIONS",
                           search_base.parent / "distractions"]:
            if candidate.exists() and candidate.is_dir():
                distractions_src = candidate
                break

    # Option B: single trigger file at root level
    # Any .json file whose name contains "distraction" (case-insensitive) works
    if distractions_src is None:
        for candidate_dir in [search_base, search_base.parent]:
            for f in candidate_dir.glob("*.json"):
                if "distraction" in f.name.lower():
                    distractions_src = f.parent   # treat parent as the trigger dir
                    break
            if distractions_src:
                break

    if distractions_src:
        trigger_files = list(distractions_src.glob("*.json")) if distractions_src.is_dir() else []
        if not distractions_src.is_dir():
            # single-file trigger: src is the parent folder, just confirm the file is there
            trigger_files = [f for f in distractions_src.iterdir()
                             if f.suffix == '.json' and 'distraction' in f.name.lower()]
        if trigger_files:
            print(f"? Distraction trigger found - 50 distraction files will be generated")
        else:
            print(f"  Distraction trigger found but empty - feature disabled")
            distractions_src = None
    else:
        print(f"  No distraction trigger found - distraction generation disabled")
    
    # Look for logout file
    logout_file = None
    logout_patterns = ["logout.json", "- logout.json", "-logout.json", "logout", "- logout", "-logout"]
    for location_dir in [search_base, search_base.parent]:
        if logout_file:
            break
        for pattern in logout_patterns:
            test_file = location_dir / pattern
            for test_path in [test_file, Path(str(test_file) + ".json")]:
                if test_path.exists() and test_path.is_file():
                    logout_file = test_path
                    print(f"? Found logout file: {logout_file.name}")
                    break
    
    print()
    
    # Scan folders
    main_folders = []
    for folder in search_base.iterdir():
        if not folder.is_dir():
            continue

        # Skip the DISTRACTIONS source folder - it is not a macro folder,
        # only the generated output copy goes into the bundle.
        if folder.name.lower() == 'distractions':
            continue
        
        numbered_subfolders, dmwm_file_set, non_json_files, root_always_first, root_always_last = scan_for_numbered_subfolders(folder)
        
        # Add dmwm files to the appropriate numbered folder
        for dmwm_file in dmwm_file_set:
            # Try to determine which numbered folder it should belong to
            # For now, add to a special '0' key or just include in general pool
            if 0 not in numbered_subfolders:
                numbered_subfolders[0] = []
            numbered_subfolders[0].append(dmwm_file)
        
        if numbered_subfolders:
            main_folders.append({
                'path': folder,
                'name': folder.name,
                'root_always_first': root_always_first,
                'root_always_last': root_always_last,
                'subfolders': numbered_subfolders,
                'dmwm_files': dmwm_file_set,
                'non_json': non_json_files
            })
            print(f"? Found: {folder.name}")
            if numbered_subfolders:
                nums = sorted([k for k in numbered_subfolders.keys() if k != 0])
                print(f"  Subfolders: {nums}")
                
                # Show special folder types
                special_folders = []
                for num in nums:
                    if num in numbered_subfolders:
                        folder_info = numbered_subfolders[num]
                        if folder_info.get('is_optional_end'):
                            special_folders.append(f"{num} (optional+end)")
                        elif folder_info.get('is_end'):
                            special_folders.append(f"{num} (end)")
                        elif folder_info.get('is_optional'):
                            special_folders.append(f"{num} (optional)")
                        
                        # Also mark time_sensitive folders
                        if folder_info.get('is_time_sensitive'):
                            special_folders.append(f"{num} (time sensitive)")
                
                if special_folders:
                    print(f"  Special: {', '.join(special_folders)}")
            if dmwm_file_set:
                print(f"  Unmodified: {len(dmwm_file_set)} files (added to pool)")
            if non_json_files:
                print(f"  Non-JSON: {len(non_json_files)} files")
    
    if not main_folders:
        print("[X] No folders with numbered subfolders found!")
        return
    
    # Filter by specific folders (and optionally specific subfolders) if provided
    # File format (one entry per line):
    #   FolderName                     -> include that folder, ALL its subfolders
    #   FolderName: F1, F3, F4         -> include that folder, ONLY listed subfolders
    #   FolderName: F1, F3-F5          -> include that folder, subfolders F1 and F3..F5 range
    # Matching is case-insensitive and whitespace-stripped.
    if args.specific_folders:
        try:
            with open(args.specific_folders, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            # Parse lines — each line is either "FolderName" or "FolderName: F1, F2"
            # GitHub Actions may collapse newlines; handle commas-as-separators only
            # when there is NO colon present (legacy behaviour).
            entries = {}   # {folder_name_lower: set_of_subfolder_nums_or_None}
            for raw_line in raw_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if ':' in line:
                    # "FolderName: F1, F2, F3" — split on first colon only
                    folder_part, sf_part = line.split(':', 1)
                    folder_key = folder_part.strip().lower()
                    # Parse subfolder numbers from "F1, F2, F3-F5" etc.
                    sf_nums = set()
                    for tok in re.split(r'[,\s]+', sf_part.strip()):
                        tok = tok.strip()
                        if not tok:
                            continue
                        # Range: F3-F5 (note: only meaningful if written as "F3-F5" not "F3,F5")
                        range_m = re.match(r'^[Ff]?(\d+(?:\.\d+)?)-[Ff]?(\d+(?:\.\d+)?)$', tok)
                        if range_m:
                            lo, hi = float(range_m.group(1)), float(range_m.group(2))
                            # Add all integer steps between lo and hi
                            v = lo
                            while v <= hi + 0.001:
                                sf_nums.add(round(v, 4))
                                v += 1.0
                        else:
                            # Single: F1, F3, 2, 3.5
                            single_m = re.match(r'^[Ff]?(\d+(?:\.\d+)?)$', tok)
                            if single_m:
                                sf_nums.add(float(single_m.group(1)))
                    entries[folder_key] = sf_nums if sf_nums else None
                else:
                    # No colon — legacy comma-separated folder names (no subfolder filter)
                    for name in line.replace(',', '\n').splitlines():
                        name = name.strip()
                        if name:
                            entries[name.lower()] = None  # None = all subfolders

            if entries:
                print(f"\n Filtering to specific folders only:")
                for name, sfs in entries.items():
                    sf_str = f" (subfolders: {sorted(sfs)})" if sfs else " (all subfolders)"
                    print(f"  - {name}{sf_str}")

                filtered_folders = []
                for folder_data in main_folders:
                    key = folder_data['name'].lower()
                    if key in entries:
                        sf_filter = entries[key]
                        if sf_filter:
                            # Keep only the requested numbered subfolders
                            original_subs = folder_data['subfolders']
                            filtered_subs = {}
                            for num, data in original_subs.items():
                                if round(num, 4) in sf_filter or num == 0:
                                    # Force-include: strip optional/end so it always runs
                                    forced = dict(data)
                                    forced['is_optional']     = False
                                    forced['is_end']          = False
                                    forced['is_optional_end'] = False
                                    filtered_subs[num] = forced
                            if not filtered_subs:
                                print(f"  [!] No matching subfolders found in '{folder_data['name']}'")
                                print(f"      Requested: {sorted(sf_filter)}")
                                print(f"      Available: {sorted(k for k in original_subs if k != 0)}")
                                continue
                            # Clone folder_data with filtered+forced subfolders
                            filtered_fd = dict(folder_data)
                            filtered_fd['subfolders'] = filtered_subs
                            filtered_folders.append(filtered_fd)
                        else:
                            filtered_folders.append(folder_data)

                if not filtered_folders:
                    # Fallback: search by subfolder name (no colon needed)
                    # If the written name matches a subfolder folder_name, auto-promote it
                    for folder_data in main_folders:
                        for sf_num, sf_data in folder_data['subfolders'].items():
                            sf_name = sf_data.get('folder_name', '')
                            if sf_name.lower() in entries:
                                print(f"  [->] '{sf_name}' matched as subfolder of '{folder_data['name']}'")
                                # Build a synthetic main_folder from this single subfolder
                                # Force always-included (strip optional/end tags)
                                forced_sf = dict(sf_data)
                                forced_sf['is_optional']     = False
                                forced_sf['is_end']          = False
                                forced_sf['is_optional_end'] = False
                                forced_sf['max_files']       = 1  # ignored — nested handles loops

                                nsf = sf_data.get('nested_subfolder_files')
                                if nsf:
                                    # Nested: promote inner structure as top-level
                                    synthetic = {
                                        'path': sf_data.get('folder_path', folder_data['path']),
                                        'name': sf_name,
                                        'root_always_first': sf_data.get('nested_root_always_first'),
                                        'root_always_last':  sf_data.get('nested_root_always_last'),
                                        'subfolders': nsf,
                                        'dmwm_files': folder_data.get('dmwm_files', set()),
                                        'non_json':   folder_data.get('non_json', []),
                                    }
                                else:
                                    # Regular subfolder: treat as flat/single-subfolder folder
                                    synthetic = {
                                        'path': sf_data.get('folder_path', folder_data['path']),
                                        'name': sf_name,
                                        'root_always_first': sf_data.get('always_first'),
                                        'root_always_last':  sf_data.get('always_last'),
                                        'subfolders': {sf_num: forced_sf},
                                        'dmwm_files': folder_data.get('dmwm_files', set()),
                                        'non_json':   folder_data.get('non_json', []),
                                    }
                                filtered_folders.append(synthetic)

                if not filtered_folders:
                    print(f"\n[X] None of the specified folders were found!")
                    print(f"   Looking for: {list(entries.keys())}")
                    print(f"   Available main folders: {[f['name'] for f in main_folders]}")
                    print(f"   TIP: You can also write a subfolder name directly:")
                    print(f"     F0.5 optional-7- CAM2       <- auto-found inside any main folder")
                    print(f"   Or use colon format to specify parent:")
                    print(f"     22- Craft Dia: F0.5         <- explicit parent + subfolder")
                    sys.exit(1)

                main_folders = filtered_folders
                print(f"[OK] Filtered to {len(main_folders)} folder(s)")
            else:
                print(f"\n[!]?  Specific folders file is empty, processing ALL folders")
        
        except FileNotFoundError:
            print(f"\n[X] Specific folders file not found: {args.specific_folders}")
            return
        except Exception as e:
            print(f"\n[X] Error reading specific folders file: {e}")
            return
    
    print(f"\n Total folders to process: {len(main_folders)}")
    print("="*70)
    
    # Initialize global chat queue
    rng = random.Random(args.bundle_id * 42)
    global_chat_queue = list(chat_files) if chat_files else []
    if global_chat_queue:
        rng.shuffle(global_chat_queue)
        print(f" Initialized global chat queue with {len(global_chat_queue)} files")
        print()
    
    # Track ALL combinations for the bundle (one file at root level)
    bundle_combinations = {}  # {folder_name: [combination_signatures]}

    # Generate DISTRACTIONS now (before folder loop) so files are available
    # for inline insertion during stringing.
    # Files are written to a TEMP folder (not inside the bundle) - they are used
    # only as in-memory splice sources and are NOT included in the final output.
    import tempfile as _tempfile
    _dist_tmpdir = None
    distraction_files = []   # list of Path objects to pick from during stringing
    dist_queue = None        # VirtualDistQueue - cycles through all files before repeating
    if distractions_src:
        print("\n" + "="*70)
        print(" Generating DISTRACTION files (inline splice only, not saved to bundle)...")
        _dist_tmpdir = _tempfile.mkdtemp(prefix="string_macros_dist_")
        dist_tmp = Path(_dist_tmpdir) / "distractions"
        n_written = generate_distraction_files(distractions_src, dist_tmp, rng, count=50, bundle_id=args.bundle_id)
        print(f"  [OK] Generated {n_written} distraction files (virtual queue: no repeats until all used)")
        distraction_files = sorted(dist_tmp.glob("*.json"))
        dist_queue = VirtualDistQueue(distraction_files, rng)

    # Process each folder
    for folder_data in main_folders:
        folder_name = folder_data['name']
        subfolder_files = folder_data['subfolders']
        dmwm_file_set = folder_data['dmwm_files']
        non_json_files = folder_data['non_json']
        root_always_first = folder_data.get('root_always_first')
        root_always_last  = folder_data.get('root_always_last')

        # Per-folder distraction insertion chances (float decimal, drawn once per folder):
        # - Normal files:      7.0-10.0%  (tighter window, more controlled)
        # - Inefficient files: 7.0-14.0%  (wider window, more varied)
        # - Raw files:         0%          (never)
        folder_dist_chance_normal = rng.uniform(3.5,  5.0) / 100.0 if distraction_files else 0.0
        folder_dist_chance_inef   = rng.uniform(3.5,  7.0) / 100.0 if distraction_files else 0.0
        
        # D_ REMOVAL
        cleaned_folder_name = re.sub(r'[Dd]_', '', folder_name)
        
        # Extract folder number
        folder_num_match = re.search(r'\d+', cleaned_folder_name)
        folder_number = int(folder_num_match.group()) if folder_num_match else 0
        
        
        # Create output folder - append bundle ID in specific folders mode
        output_folder_name = cleaned_folder_name
        if args.specific_folders:
            output_folder_name = f"({args.bundle_id}) {cleaned_folder_name}"
        print(f"\n Processing: {output_folder_name}")
        out_folder = bundle_dir / output_folder_name
        out_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy logout file with @ prefix
        if logout_file:
            try:
                original_name = logout_file.name
                if original_name.startswith("-"):
                    new_name = f"@ {folder_number} {original_name[1:].strip()}".upper()
                else:
                    new_name = f"@ {folder_number} {original_name}".upper()
                shutil.copy2(logout_file, out_folder / new_name)
                print(f"  ? Copied logout: {new_name}")
            except Exception as e:
                print(f"  ? Error copying logout: {e}")
        
        # Copy non-JSON files with @ prefix
        for non_json_file in non_json_files:
            try:
                original_name = non_json_file.name
                if original_name.startswith("-"):
                    new_name = f"@ {folder_number} {original_name[1:].strip()}"
                else:
                    new_name = f"@ {folder_number} {original_name}"
                shutil.copy2(non_json_file, out_folder / new_name)
                print(f"  ? Copied non-JSON: {new_name}")
            except Exception as e:
                print(f"  ? Error copying {non_json_file.name}: {e}")
        
        if not subfolder_files:
            print("  [!]?  No numbered subfolders to process")
            continue
        
        # Use bundle-organized tracker
        tracker = ManualHistoryTracker(
            subfolder_files, rng, cleaned_folder_name, search_base
        )
        target_ms = args.target_minutes * 60000
        
        # Track all combinations used in THIS RUN for this folder
        folder_combinations_used = []
        
        # Calculate total original duration
        # Detect "copied" subfolders: subfolders whose file-name sets are identical
        # (e.g. F1-mine and F2-mine with same files). Count their files only once
        # so the duration reflects unique content, not duplicated repetitions.
        # Count each unique filename only once across ALL subfolders.
        # Copied folders (F1-mine, F2-mine) may share file names - count once.
        _seen_filenames = set()   # filenames already counted (by name, not path)
        total_original_files = 0
        total_original_ms = 0
        # Count subfolders whose *entire* file-name set is a duplicate of another
        _seen_filesets = []
        num_copied_folders = 0

        for _subfolder_data in subfolder_files.values():
            files = _subfolder_data['files']
            fileset = frozenset(f.name for f in files)
            if fileset in _seen_filesets:
                num_copied_folders += 1   # whole subfolder is a copy
            else:
                _seen_filesets.append(fileset)
            # Always count individual files that haven't been seen by name yet
            for f in files:
                if f.name not in _seen_filenames:
                    _seen_filenames.add(f.name)
                    total_original_files += 1
                    total_original_ms += get_file_duration_ms(f)

        
        # Build subfolder file count lines for manifest
        _subfolder_lines = []
        for _fn in sorted(subfolder_files.keys()):
            _fd = subfolder_files[_fn]
            _fn_label = str(int(_fn) if _fn == int(_fn) else _fn)
            _file_count = len(_fd.get('files', []))
            _always_note = ""
            if _fd.get('always_first'): _always_note += " + always_first"
            if _fd.get('always_last'):  _always_note += " + always_last"
            _subfolder_lines.append(f"  F{_fn_label}: {_file_count} file(s){_always_note}")

        # Manifest header
        manifest_lines = [
            f"MANIFEST FOR FOLDER: {cleaned_folder_name}",
            "=" * 40,
            f"Script Version: {VERSION}",
            f"Stringed Bundle: stringed_bundle_{args.bundle_id}",
            f"Total Original Files: {total_original_files}",
            (f"Total Original Files Duration: {format_ms_precise(total_original_ms)} ({num_copied_folders} copied folder(s))"
             if num_copied_folders > 0
             else f"Total Original Files Duration: {format_ms_precise(total_original_ms)}"),
        ] + _subfolder_lines + [""]
        
        # Check if any folders are 'time sensitive' (no inefficient files)
        has_time_sensitive = any(
            folder_data.get('is_time_sensitive', False) 
            for folder_data in subfolder_files.values()
        )
        
        # Debug: Show which folders are time_sensitive
        if has_time_sensitive:
            time_sensitive_folders = [
                str(int(num) if num == int(num) else num)
                for num, data in subfolder_files.items() 
                if data.get('is_time_sensitive', False)
            ]
            print(f"  ??  TIME SENSITIVE folders detected: {', '.join(time_sensitive_folders)}")
        
        # Version loop: 3 Raw + 3 Inef + 6 Normal = 12 total
        # OR: 3 Raw + 0 Inef + 9 Normal = 12 total (if time_sensitive)
        def get_version_letter(idx):
            """
            Generate version letter for any index, repeating letters after Z.
            0=A, 1=B, ..., 25=Z, 26=AA, 27=BB, ..., 51=ZZ, 52=AAA, etc.
            """
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            repeat = (idx // 26) + 1   # how many chars: 1 for 0-25, 2 for 26-51, etc.
            letter = letters[idx % 26]
            return letter * repeat
        # VERSION DISTRIBUTION - 2:3:7 ratio (raw:inefficient:normal)
        # Scaled from the 12-file base using round() so it stays proportional
        # for any --versions value, with remainder going to normal files.
        # Time-sensitive folders replace all inefficient slots with normal.
        _total_parts = 12  # ratio denominator
        if has_time_sensitive:
            # 1:1 ratio for time-sensitive: half raw, half normal, zero inefficient
            num_raw    = max(1, round(args.versions / 2))
            num_inef   = 0
            num_normal = args.versions - num_raw
            print(f"   File distribution: {num_raw} Raw + 0 Inef + {num_normal} Normal (time sensitive - 1:1 ratio)")
        else:
            num_raw   = max(1, round(args.versions * 2 / _total_parts))
            num_inef  = max(1, round(args.versions * 3 / _total_parts))
            num_normal = args.versions - num_raw - num_inef
            if num_normal < 1:
                num_normal = 1
                num_inef = max(1, args.versions - num_raw - num_normal)
            print(f"   File distribution: {num_raw} Raw + {num_inef} Inef + {num_normal} Normal ({num_raw}:{num_inef}:{num_normal} ratio, target 2:3:7)")
        
        # CHAT INSERT: pick exactly 1 non-raw version per folder batch to receive
        # a single chat file inserted at a random midpoint in the finished strung file.
        # Raw files never get chat (they carry no added features).
        chat_version_idx = None
        chat_file_for_version = None
        if chat_files and not args.no_chat:
            non_raw_indices = list(range(num_raw, args.versions))
            if non_raw_indices:
                chat_version_idx = rng.choice(non_raw_indices)
                chat_file_for_version = rng.choice(chat_files)
                cv_letter = get_version_letter(chat_version_idx)
                print(f"   Chat insert: version {cv_letter} will receive 1 chat ({chat_file_for_version.name})")
        
        for v_idx in range(args.versions):
            v_letter = get_version_letter(v_idx)
            
            # Determine file type
            is_raw = (v_idx < num_raw)
            is_inef = (num_raw <= v_idx < num_raw + num_inef)
            is_normal = (v_idx >= num_raw + num_inef)
            
            # DEBUG: Show file type determination
            if v_idx == 0:  # First file
                print(f"\n   File Type Assignments:")
            
            file_type_str = "RAW" if is_raw else ("INEFFICIENT" if is_inef else "NORMAL")
            prefix_str = "^" if is_raw else ("\u00ac\u00ac" if is_inef else "none")
            print(f"     {v_letter}: {file_type_str:12s} (prefix: {prefix_str})")
            
            # Set multiplier — continuous random range (not rounded), giving decimal values
            # e.g. Normal picks anywhere in [1.3, 1.5] so 1.31, 1.44, 1.49, etc.
            if is_raw:
                # Raw: range 1.0 – 1.1  (e.g. 1.03, 1.07)
                mult = round(rng.uniform(1.1, 1.2), 4)
            elif is_inef:
                # Inefficient: range 2.0 – 3.0  (e.g. 2.14, 2.87)
                mult = round(rng.uniform(2.0, 3.0), 4)
            else:  # normal
                # Normal: range 1.3 – 1.5  (e.g. 1.33, 1.47)
                mult = round(rng.uniform(1.5, 1.7), 4)
            
            # Per-version target: ±5 minutes random variance around base target
            # Each version independently drawn — decimal ms, never rounded
            _variance_ms = rng.uniform(-5 * 60000, 5 * 60000)
            target_ms = _base_target_ms + _variance_ms
            _t_min = int(target_ms // 60000)
            _t_sec = int((target_ms % 60000) / 1000)
            print(f"     {v_letter}: target = {_t_min}m {_t_sec}s (base {args.target_minutes}m ± 5m)")

            # Build cycles until target reached
            stringed_events = []
            all_file_info_with_times = []  # List of (folder_num, filename, is_dmwm, end_time) tuples
            total_intra = 0
            total_inter = 0
            total_idle = 0
            total_normal_pauses = 0
            massive_pause_ms = 0
            jitter_pct = 0

            # NEW: Track pre-file pauses, post-pause delays, cursor transitions, distraction pauses
            total_pre_file = 0
            total_transitions = 0
            total_snap_gap = 0     # cumulative post-snap transition gaps (80-150ms each)
            total_dist_pause = 0   # cumulative distraction file duration inserted into this version

            # For flat/single-subfolder folders, always_first fires on the FIRST cycle
            # only and always_last fires once AFTER the whole loop.
            _is_flat_folder = (len(subfolder_files) == 1)
            _cycle_count = 0   # tracks which cycle we are on

            # INEF: reserve budget for the massive pause so the loop doesn't
            # overshoot target_ms once the pause is inserted after the loop.
            # Pre-sample the pause duration using the same formula as insert_massive_pause.
            # The loop uses (target_ms - massive_pause_budget) as its effective ceiling.
            if is_inef:
                _expected_massive_ms = int(rng.uniform(240000.0, 420000.0))  # no mult
                _effective_target = max(target_ms - _expected_massive_ms, target_ms // 4)
            else:
                _expected_massive_ms = 0
                _effective_target = target_ms

            # ROOT-LEVEL always_first: play ONCE before all cycles (not per cycle)
            if root_always_first:
                try:
                    _raf_events = json.load(open(root_always_first, encoding='utf-8'))
                    _raf_events = filter_problematic_keys(_raf_events)
                    if _raf_events:
                        _raf_base = min(e.get('Time', 0) for e in _raf_events)
                        for _e in _raf_events:
                            _ne = {**_e}
                            _ne['Time'] = _e['Time'] - _raf_base
                            stringed_events.append(_ne)
                        _raf_end = stringed_events[-1]['Time']
                        all_file_info_with_times.append(
                            (0.0, f"[ALWAYS FIRST] {root_always_first.name}",
                             root_always_first in dmwm_file_set, _raf_end)
                        )
                        # Advance timeline tracker so first cycle gets proper buffer
                        total_pre_file += rng.uniform(500.0, 800.0) * mult
                except Exception as _e:
                    print(f"  [!] Root always_first load error: {_e}")

            while True:
                combo = tracker.get_next_combination()
                if not combo:
                    break
                
                # Track this combination signature (format folder numbers cleanly)
                combo_signature = "|".join(
                    f"F{int(fn) if fn == int(fn) else fn}=" +
                    "+".join(fp.name if hasattr(fp, "name") else f"nested_{i}" for i, fp in enumerate(fl if isinstance(fl, list) else [fl]))
                    for fn, fl in combo
                )
                folder_combinations_used.append(combo_signature)
                
                # BUILD CYCLE (F1 -> F2 -> F3) WITHOUT features
                # Folder is click-sensitive if ANY subfolder in this folder is tagged
                folder_is_click_sensitive = any(
                    fd.get('is_click_sensitive', False)
                    for fd in subfolder_files.values()
                )
                # Distractions: Raw and click-sensitive folders never get any
                if is_raw or folder_is_click_sensitive:
                    cycle_dist_chance = 0.0
                elif is_inef:
                    cycle_dist_chance = folder_dist_chance_inef
                else:
                    cycle_dist_chance = folder_dist_chance_normal
                # Flat/single-subfolder: always_first only on cycle 0,
                # always_last suppressed here (injected once after loop ends)
                _play_af = (not _is_flat_folder) or (_cycle_count == 0)
                _play_al = not _is_flat_folder   # always_last injected after loop
                cycle_result = string_cycle(
                    subfolder_files, combo, rng, dmwm_file_set,
                    distraction_files=dist_queue,
                    distraction_chance=cycle_dist_chance,
                    is_click_sensitive=folder_is_click_sensitive,
                    play_always_first=_play_af,
                    play_always_last=_play_al,
                    mult=mult
                )
                _cycle_count += 1
                
                cycle_events = cycle_result['events']
                file_info = cycle_result['file_info']
                has_dmwm = cycle_result['has_dmwm']
                
                if not cycle_events:
                    break
                
                # APPLY FEATURES to ENTIRE cycle
                cycle_with_features, stats = apply_cycle_features(
                    cycle_events, rng, is_raw, has_dmwm, is_inef=is_inef,
                    is_click_sensitive=folder_is_click_sensitive, mult=mult
                )
                
                # Check if adding would exceed target
                current_duration = stringed_events[-1]['Time'] if stringed_events else 0
                cycle_duration = cycle_with_features[-1]['Time'] if cycle_with_features else 0
                
                # Add INEFFICIENT Before File Pause (only for inefficient files, only if file >= 25 sec)
                inter_cycle_pause = 0
                if stringed_events:
                    # PRE-PLAY BUFFER BETWEEN CYCLES (all file types)
                    # The intra-cycle add_file_to_cycle buffer fires for files WITHIN a cycle,
                    # but the very first file of each new cycle has files_added=0 so gets no buffer.
                    # Without this, the last DragEnd of cycle N and the cursor transition of cycle
                    # N+1 share the same timestamp -> the game reads them as simultaneous ->
                    # cursor teleports while button is still held -> drag-click at wrong position.
                    _cycle_gap = rng.uniform(500.0, 800.0)
                    inter_cycle_pause += int(_cycle_gap)
                    total_pre_file += _cycle_gap
                if stringed_events and is_inef:
                    # Check file length: Only apply if file is >= 25 seconds (25000ms)
                    file_duration = cycle_duration  # Current cycle duration in ms
                    if file_duration >= 25000:
                        # INEFFICIENT Before File Pause: 10-30 seconds (10000-30000ms)
                        # Random, not rounded, no multiplier applied
                        inter_cycle_pause = int(rng.uniform(10000.0, 30000.0))
                        total_inter += inter_cycle_pause
                    
                    # Add cursor transition during pause
                    last_x, last_y = None, None
                    for e in reversed(stringed_events):
                        if e.get('X') is not None and e.get('Y') is not None:
                            last_x, last_y = int(e['X']), int(e['Y'])
                            break
                    
                    first_x, first_y = None, None
                    for e in cycle_with_features:
                        if e.get('X') is not None and e.get('Y') is not None:
                            first_x, first_y = int(e['X']), int(e['Y'])
                            break
                    
                    if last_x and first_x and (last_x != first_x or last_y != first_y):
                        transition_path = generate_human_path(
                            last_x, last_y, first_x, first_y,
                            inter_cycle_pause, rng
                        )
                        
                        for rel_time, x, y in transition_path[:-1]:
                            if rel_time < inter_cycle_pause:
                                stringed_events.append({
                                    'Type': 'MouseMove',
                                    'Time': current_duration + rel_time,
                                    'X': x,
                                    'Y': y
                                })
                
                potential_total = current_duration + inter_cycle_pause + cycle_duration
                margin = int(_effective_target * 0.05)
                if potential_total > _effective_target + margin and stringed_events:
                    break
                
                # Add cycle to merged events
                offset = current_duration + inter_cycle_pause
                for e in cycle_with_features:
                    new_event = {**e}
                    new_event['Time'] = e['Time'] + offset
                    stringed_events.append(new_event)
                
                # Track file info with cumulative timeline
                # file_info now includes end time within cycle
                for folder_num, filename, is_dmwm, end_time_in_cycle in file_info:
                    # Add offset to get actual end time in merged events
                    actual_end_time = end_time_in_cycle + offset
                    all_file_info_with_times.append((folder_num, filename, is_dmwm, actual_end_time))
                
                # Update stats
                total_intra += stats['intra_pauses']
                total_idle += stats['idle_movements']
                jitter_pct = stats['jitter_percentage']
                
                # NEW: Accumulate pre-file pause, post-pause, and transition times
                total_pre_file += cycle_result.get('pre_pause_total', 0)
                total_transitions += cycle_result.get('transition_total', 0)
                total_snap_gap += cycle_result.get('snap_gap_total', 0)
                total_dist_pause += cycle_result.get('distraction_pause_total', 0)
                
                if len(all_file_info_with_times) > 2000:  # Safety limit (increased from 150)
                    break
            
            # Flat/single-subfolder: inject always_last once at the very end
            if _is_flat_folder and stringed_events:
                _only_fn  = next(iter(subfolder_files))
                _only_fd  = subfolder_files[_only_fn]
                _al_file  = _only_fd.get('always_last')
                if _al_file:
                    _al_events = json.load(open(_al_file, encoding='utf-8'))
                    _al_events = filter_problematic_keys(_al_events)
                    if _al_events:
                        _al_base  = min(e.get('Time', 0) for e in _al_events)
                        _al_start = stringed_events[-1]['Time'] if stringed_events else 0
                        # Pre-play buffer before always_last
                        _al_buf   = rng.uniform(500.0, 800.0)
                        _al_start += _al_buf
                        total_pre_file += _al_buf
                        for _e in _al_events:
                            _ne = {**_e}
                            _ne['Time'] = _e['Time'] - _al_base + _al_start
                            stringed_events.append(_ne)
                        _al_end = stringed_events[-1]['Time']
                        all_file_info_with_times.append(
                            (_only_fn, f"[ALWAYS LAST] {_al_file.name}",
                             _al_file in dmwm_file_set, _al_end)
                        )

            # ROOT-LEVEL always_last: play ONCE after all cycles
            if root_always_last and stringed_events:
                try:
                    _ral_events = json.load(open(root_always_last, encoding='utf-8'))
                    _ral_events = filter_problematic_keys(_ral_events)
                    if _ral_events:
                        _ral_base  = min(e.get('Time', 0) for e in _ral_events)
                        _ral_buf   = rng.uniform(500.0, 800.0) * mult
                        _ral_start = stringed_events[-1]['Time'] + _ral_buf
                        total_pre_file += _ral_buf
                        for _e in _ral_events:
                            _ne = {**_e}
                            _ne['Time'] = _e['Time'] - _ral_base + _ral_start
                            stringed_events.append(_ne)
                        _ral_end = stringed_events[-1]['Time']
                        all_file_info_with_times.append(
                            (0.0, f"[ALWAYS LAST] {root_always_last.name}",
                             root_always_last in dmwm_file_set, _ral_end)
                        )
                except Exception as _e:
                    print(f"  [!] Root always_last load error: {_e}")

            if not stringed_events:
                print(f"  [!]?  Version {v_letter}: no events built (all combos exceeded target or no valid combo) - skipping")
                continue
            
            # Add massive pause for INEFFICIENT
            if is_inef and len(stringed_events) > 1:
                stringed_events, massive_pause_ms, split_idx = insert_massive_pause(stringed_events, rng)  # mult not applied
                
                # FIX: Update file end times that occur after the massive pause
                if massive_pause_ms > 0 and split_idx > 0 and split_idx < len(stringed_events):
                    # Find the timestamp of the split point
                    split_time = stringed_events[split_idx]['Time']
                    
                    # Update all file end times that occur after the split
                    updated_file_info = []
                    for folder_num, filename, is_dmwm, end_time in all_file_info_with_times:
                        if end_time > split_time:
                            # File ends after the pause - shift its end time
                            updated_end_time = end_time + massive_pause_ms
                            updated_file_info.append((folder_num, filename, is_dmwm, updated_end_time))
                        else:
                            # File ends before the pause - keep original time
                            updated_file_info.append((folder_num, filename, is_dmwm, end_time))
                    
                    all_file_info_with_times = updated_file_info
            
            # Calculate total duration
            total_duration = stringed_events[-1]['Time']
            total_min = int(total_duration / 60000)
            total_sec = int((total_duration % 60000) / 1000)
            
            # File prefix and name
            if is_raw:
                prefix = "^"
            elif is_inef:
                prefix = "\u00ac\u00ac"
            else:
                prefix = ""
            
            v_code = f"{folder_number}_{v_letter}"
            fname = f"{prefix}{v_code}_{total_min}m{total_sec}s.json"
            
            # CRITICAL FIXES before saving:
            # 1. Convert Click events to LeftDown+LeftUp pairs (prevents clamp)
            # 2. Sort all events by Time (prevents out-of-order gaps)
            stringed_events = fix_click_events(stringed_events)
            # Round all Times to int (rng.uniform() produces floats) and ensure non-negative
            for e in stringed_events:
                if 'Time' in e:
                    e['Time'] = max(0, int(round(e['Time'])))
            stringed_events = sorted(stringed_events, key=lambda e: e.get('Time', 0))
            
            # CHAT INSERT: splice one chat file into the chosen version
            chat_inserted = False
            if v_idx == chat_version_idx and chat_file_for_version and not is_raw:
                try:
                    with open(chat_file_for_version, 'r', encoding='utf-8') as cf:
                        chat_events = json.load(cf)
                    if chat_events:
                        # Normalise chat event times to start at 0
                        chat_base = min(e.get('Time', 0) for e in chat_events)
                        chat_duration = max(e.get('Time', 0) for e in chat_events) - chat_base
                        
                        # Pick a random insertion point in the middle third of the file
                        if len(stringed_events) >= 6:
                            lo = len(stringed_events) // 3
                            hi = (2 * len(stringed_events)) // 3
                            insert_idx = rng.randint(lo, hi)
                        else:
                            insert_idx = len(stringed_events) // 2
                        
                        insert_time = stringed_events[insert_idx]['Time']
                        
                        # Shift all events after insertion point forward by chat duration
                        for e in stringed_events[insert_idx:]:
                            e['Time'] += chat_duration
                        
                        # Build chat events at insert_time
                        chat_splice = []
                        for e in chat_events:
                            ne = {**e}
                            ne['Time'] = insert_time + (e.get('Time', 0) - chat_base)
                            chat_splice.append(ne)
                        
                        # Splice in and re-sort
                        stringed_events = (
                            stringed_events[:insert_idx] +
                            chat_splice +
                            stringed_events[insert_idx:]
                        )
                        stringed_events = sorted(stringed_events, key=lambda e: e.get('Time', 0))
                        chat_inserted = True
                        print(f"      Chat inserted: {chat_file_for_version.name} at ~{insert_time//60000}m{(insert_time%60000)//1000}s")
                except Exception as chat_err:
                    print(f"     [!]?  Chat insert failed: {chat_err}")
            
            # Save file
            (out_folder / fname).write_text(json.dumps(stringed_events, indent=2))
            
            # DEBUG: Show created file
            type_label = "RAW" if is_raw else ("INEF" if is_inef else "NORM")
            chat_tag = " +CHAT" if chat_inserted else ""
            print(f"     ? Created: {fname:<30s} [{type_label}{chat_tag}]")
            
            # Build manifest entry
            separator = "=" * 40
            version_label = f"Version {prefix}{v_code}_{total_min}m{total_sec}s:"
            
            # Compute totals for all three types
            if is_raw:
                _intra_show = 0; _inter_show = 0; _massive_show = 0
            elif is_inef:
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                _intra_show = total_intra; _inter_show = total_inter; _massive_show = massive_pause_ms
            else:  # normal
                _intra_show = total_intra; _inter_show = 0; _massive_show = 0

            total_pause = (total_intra + total_pre_file + total_transitions
                           + total_snap_gap + total_dist_pause
                           + _inter_show + _massive_show)

            file_type_label = "Raw" if is_raw else ("Inefficient" if is_inef else "Normal")
            manifest_entry = [
                separator,
                "",
                version_label,
                f"FILE TYPE: {file_type_label}",
                f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                "",
                f"BREAKDOWN (x = mult applied, - = flat no mult):",
                f"                x PRE-Play Buffer: {format_ms_precise(total_pre_file)}",
                f"                x Within File Pauses: {format_ms_precise(_intra_show)}",
                f"                x CURSOR to Start Point: {format_ms_precise(total_transitions)}",
                f"                - POST-SNAP GAP: {format_ms_precise(total_snap_gap)}",
                f"                - DISTRACTION File Pause: {format_ms_precise(total_dist_pause)}",
                f"                - INEFFICIENT Before File Pause: {format_ms_precise(_inter_show)}",
                f"                - INEFFICIENT MASSIVE PAUSE: {format_ms_precise(_massive_show)}",
                ""
            ]
            
            # Add file list with F#* prefix and cumulative timeline
            for folder_num, filename, is_dmwm, end_time in all_file_info_with_times:
                prefix = "[UNMODIFIED] " if is_dmwm else ""
                manifest_entry.append(f"  * {prefix}{filename} (Ends at {format_ms_precise(end_time)})")
            
            manifest_lines.extend(manifest_entry)
        
        # Write manifest
        manifest_path = out_folder / f"!_MANIFEST_{folder_number}_!.txt"
        manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"\n   Manifest written: {manifest_path.name}")
        
        # Collect combinations for this folder (for bundle-level file)
        # Use the combinations we tracked during THIS RUN
        if folder_combinations_used:
            bundle_combinations[cleaned_folder_name] = folder_combinations_used
        files_written = len(folder_combinations_used)
        print(f"  [OK] Folder done: {output_folder_name} - {files_written} version(s) written")
    
    # Write ONE combination file at SAME LEVEL as bundle folder
    if bundle_combinations:
        combo_file = output_root / f"COMBINATION_HISTORY_{args.bundle_id}.txt"
        try:
            with open(combo_file, 'w') as f:
                f.write(f"=== BUNDLE {args.bundle_id} COMBINATION HISTORY ===\n\n")
                
                for folder_name in sorted(bundle_combinations.keys()):
                    combos = bundle_combinations[folder_name]
                    f.write(f"[{folder_name}]\n")
                    for combo in combos:
                        f.write(f"{combo}\n")
                    f.write(f"\n")
            
            total_combos = sum(len(c) for c in bundle_combinations.values())
            print(f"\n Combination file written: {combo_file.name}")
            print(f"   Total combinations: {total_combos} across {len(bundle_combinations)} folders")
        except Exception as e:
            print(f"\n[!]?  Could not write combination file: {e}")

    # Clean up temporary distraction files (used only for inline splicing, not saved to bundle)
    if _dist_tmpdir:
        import shutil as _shutil
        try:
            _shutil.rmtree(_dist_tmpdir, ignore_errors=True)
        except Exception:
            pass

    print("\n" + "="*70)
    print(f"[OK] STRING MACROS COMPLETE - Bundle {args.bundle_id}")
    print(f" Output: {bundle_dir}")
    print(f"\n To track combinations:")
    print(f"   1. Upload COMBINATION_HISTORY_{args.bundle_id}.txt to:")
    print(f"      input_macros/combination_history/")
    print(f"   2. Code will read ALL .txt files and avoid duplicates")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
