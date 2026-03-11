#!/usr/bin/env python3
"""
string_macros.py - v3.17.0 - PRE-Play Buffer Update & Workflow Improvements
- UPDATED: PRE-Play Buffer now 800ms (was 700ms testing value)
- CONFIRMED: PRE-play pause happens BEFORE cursor movement (original order)
  - Order: File ends → 800ms pause → Cursor moves → Next file
  - Ensures clicks are fully released before any movement
- Workflow v3.12.0: Flat ZIP structure when using specific folders mode
- All v3.16.0 features maintained
"""

# ============================================================================
# 🤖 IMPORTANT REMINDER FOR AI/HUMAN EDITORS:
# ============================================================================
"""
⚠️  WHEN YOU MODIFY ANY FEATURE IN THIS CODE:

1. UPDATE THE FEATURE DOCUMENTATION BELOW (Lines 40-230)
   - Change the description
   - Update percentages/values
   - Update code line numbers
   - Update status if feature is disabled/enabled

2. UPDATE THE VERSION NUMBER ABOVE
   - Increment version (e.g., v3.12.0 → v3.12.1)
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

VERSION = "v3.17.0"

# ============================================================================
# FEATURE DOCUMENTATION - ORGANIZED BY PURPOSE
# ============================================================================
"""
═══════════════════════════════════════════════════════════════════════════
                    📋 DETECTED FOLDER & FILE TAGS
═══════════════════════════════════════════════════════════════════════════

FOLDER TAGS (detected in folder name, case-insensitive):
  • "optional"        → Folder has 24-33% chance to be included per run
  • "end"             → Folder becomes definitive loop endpoint (stops after)
  • "optional/end"    → Combination: optional folder that ends loop IF chosen
  • "time sensitive"  → No inefficient files generated (replaced with normal files)
                        Can be applied to:
                        - Main folder → ALL subfolders become time_sensitive
                        - Individual subfolders → Only that subfolder is time_sensitive
  • (Decimal support: "3.5" goes between folders 3 and 4)

FILE TAGS (detected in filename, case-insensitive):
  • "always first" or "alwaysfirst"  → File always plays first in its folder
  • "always last" or "alwayslast"    → File always plays last in its folder

SPECIAL FOLDER (exact name match, case-insensitive):
  • "Don't use features on me" → Files inserted unmodified (no features applied)
  • (Also accepts old name "dont mess with me" for backward compatibility)

═══════════════════════════════════════════════════════════════════════════
                    GROUP 1: PAUSE BREAKS (Anti-Detection Timing)
═══════════════════════════════════════════════════════════════════════════

These features add natural pauses and delays to prevent robotic timing patterns.

1. WITHIN FILE PAUSES
   Status: ✅ ACTIVE (Inefficient & Normal files only)
   Old Name: "Intra-file pauses"
   What: Pauses between individual actions INSIDE files (except double-clicks)
   Source: From original macro recordings
   Duration: Varies (typically 2-3 min total per file)
   File Types: 
     - Raw: REMOVED (stripped out)
     - Inefficient: KEPT and multiplied
     - Normal: KEPT and multiplied
   Purpose: Natural hesitation between actions
   Code: Line ~850 (filter pauses in raw files)
   Manifest: "Within original files pauses: Xm Xs"

2. PRE-PLAY BUFFER
   Status: ✅ ACTIVE (Always, all file types)
   Old Name: "Pre-file pauses"
   What: Fixed pause BEFORE each file starts playing
   Duration: 800ms (0.8 seconds) - FLAT, NO multiplier, NO randomization
   When: Applied BEFORE cursor movement (click release protection)
   Purpose: Ensures clicks from previous file are fully released
   Code: Line ~1376-1384 (pre_file_pause)
   Total Impact: ~2m 40s per 50-minute output (200 files × 800ms)
   Manifest: "PRE-Play Buffer: Xm Xs"
   Order: PRE-pause → Cursor transition → File plays

3. INEFFICIENT BEFORE FILE PAUSE
   Status: ✅ ACTIVE (Inefficient files ONLY, file >= 25 seconds)
   Old Name: "Before File Pause" or "Inter-file pauses" or "Between cycles pause"
   What: Longer pause between complete action cycles
   Duration: 10-30 seconds (10000-30000ms, random, NOT rounded, NO multiplier)
   File Length Check: Only applied if file duration >= 25 seconds
   File Types:
     - Raw: ❌ DISABLED
     - Inefficient: ✅ ACTIVE (if file >= 25s)
     - Normal: ❌ DISABLED
   Purpose: Major break between action sequences
   Code: Line ~2084-2093 (inter_cycle_pause with file length check)
   Manifest: "INEFFICIENT Before File Pause: Xm Xs"

4. POST-PAUSE DELAYS
   Status: ⚠️ DISABLED (Marked for future removal)
   Old Name: "Post-pause delays"
   What: Delay after pre-pause, before cursor moves
   Duration: 500-1000ms × multiplier (when active)
   Reason Disabled: Redundant with PRE-PLAY BUFFER
   Code: Line ~1135-1140 (currently disabled)
   Future: Will be removed in v4.0
   Manifest: Shows 0m 0s when disabled

5. INEFFICIENT MASSIVE PAUSE
   Status: ✅ ACTIVE (Inefficient files ONLY)
   Old Name: "Massive pause"
   What: One random pause inserted at safe location
   Duration: 2-5 minutes (120000-300000ms, random, NOT rounded) × multiplier
   Examples: ×2.0 = 4-10 min | ×3.0 = 6-15 min
   Safe Location Detection: EXCLUDES pause from:
     - Drag sequences (between DragStart and DragEnd)
     - Rapid click sequences (double-clicks, spam clicks)
     - First/last 10% of file (for safety)
     - Immediately BEFORE DragStart events (FIX v3.15.2)
   Where: Random safe point in middle 80% of file
   File Types:
     - Raw: ❌ NOT USED
     - Inefficient: ✅ INSERTED
     - Normal: ❌ NOT USED
   Purpose: Simulates AFK/distracted behavior
   Code: Line ~1171-1220 (insert_massive_pause with drag protection)
   Manifest: "INEFFICIENT MASSIVE PAUSE: Xm Xs"
   
   BUG FIX (v3.15.2): Added check to prevent pause insertion immediately before
   DragStart events. Previously, pauses could be inserted right before DragStart,
   which shifted the DragEnd forward in time, making clicks appear to last 1-4
   seconds instead of <150ms, causing drag/clamp issues.

6. MULTIPLIER SYSTEM
   Status: ✅ ACTIVE (Always)
   What: Scales all pause durations by multiplier value
   Values by File Type (UPDATED v3.13.0):
     Raw Files:
       • x1.0 (50% probability)
       • x1.1 (50% probability)
     
     Normal Files:
       • x1.3 (65% probability)
       • x1.5 (35% probability)
     
     Inefficient Files:
       • x2.0 (60% probability)
       • x3.0 (40% probability)
   
   Purpose: Varied timing patterns across output files
   Code: Line ~1918-1927 (multiplier selection)
   Manifest: "(xN Multiplier)" shown in each file header

═══════════════════════════════════════════════════════════════════════════
              GROUP 2: PATTERN BREAKING (Anti-Detection Variance)
═══════════════════════════════════════════════════════════════════════════

These features add variation and unpredictability to prevent detectable patterns.

1. CURSOR TO START POINT
   Status: ✅ ACTIVE (Always)
   Old Name: "Cursor transitions"
   What: Smooth cursor movement from file end position to next file start
   Duration: 200-400ms per transition (varies by path style)
   Path Styles (random per transition):
     • Efficient: Direct path, few curves, faster
     • Swift: Very fast, straight line
     • Meandering: Curved path, more wandering
     • Hesitant: Slow start, acceleration, deceleration
   Speed Variations: Very fast (100-200ms) to Very slow (700-1000ms)
   Purpose: No mouse teleportation; realistic cursor flow with variety
   Code: Line ~498-576 (generate_human_path with path styles)
   Impact: Adds ~30-35s to 50-minute output
   Manifest: "CURSOR to Start Point: Xm Xs"
   Note: This DOES add time to total duration (intentional)

2. IDLE CURSOR WANDERING
   Status: ✅ ACTIVE (Always, during pauses > 1s)
   Old Name: "Idle mouse movements"
   What: Small random mouse wiggles during long pauses
   When: Any pause > 1 second
   Pattern: Smooth Bézier curves, realistic speed
   Purpose: Cursor doesn't stay frozen during waits
   Code: Line ~702-793 (add_idle_movements)
   Impact: ~7-11 minutes "movement time" per 50-min output
   Manifest: "Idle Mouse Movements: Xm Xs"
   Note: This does NOT extend file duration (happens during existing pauses)

3. MOUSE JITTER
   Status: ✅ ACTIVE (9-21% of movements, with exclusions)
   What: Random small offsets to cursor positions
   Percentage: 9-21% of all mouse movements get jittered
   Amount: Small random offset per movement
   Exclusion Zones (NO JITTER):
     • 1000ms before/after any click
     • 1500ms for rapid click sequences (3+ clicks in 1500ms)
     • During drag operations (hold + move + release)
   Purpose: Natural hand tremor, but maintains click accuracy
   Code: Line ~669-677 (apply_smart_jitter)
   Protection: Line ~552-589 (detect rapid clicks)
   Note: DISABLED near clicks to prevent off-target clicks
   Manifest: "Mouse Jitter: XX%"

4. RANDOM FILE QUEUE
   Status: ✅ ACTIVE (Always)
   What: Files selected randomly from each folder per cycle
   Method: Random choice from available files
   Avoids: Repeating same folder combination (via history)
   Purpose: No predictable file order
   Code: Line ~1475 (rng.choice for file selection)
   Manifest: File order visible in manifest list

═══════════════════════════════════════════════════════════════════════════
            GROUP 3: ENSURING SMOOTH OPERATION (Reliability)
═══════════════════════════════════════════════════════════════════════════

These features ensure files play correctly without breaking or causing errors.

1. RAPID CLICK PROTECTION
   Status: ✅ ACTIVE (Always)
   What: Detects rapid click sequences and extends jitter exclusion zones
   Detection: 3+ clicks within 1500ms
   Protection: Extends exclusion from 1000ms → 1500ms
   Purpose: Prevents jitter from breaking rapid action sequences
   Code: Line ~552-589 (detect_rapid_click_sequences)

2. DRAG OPERATION PROTECTION
   Status: ✅ ACTIVE (Always)
   What: Detects drag operations and prevents jitter during them
   Detection: Hold + Move + Release patterns
   Protection: NO jitter during entire drag sequence
   Purpose: Maintains drag accuracy
   Code: Line ~596-628 (detect_drag_operations)

3. EVENT TIMING INTEGRITY PROTECTION
   Status: ✅ ACTIVE (Always, all time-adding features)
   What: Prevents pauses/modifications from interfering with drag/click timing
   Protection Zones (NO time modification):
     • Between DragStart and DragEnd pairs
     • Immediately BEFORE DragStart events
     • Within rapid click sequences
     • First/last 10% of file
   Impact: Maintains click responsiveness (<200ms), prevents drag/clamp issues
   Purpose: CRITICAL protection to prevent clicks being held 1-4 seconds
   Code: Line ~1171-1220 (insert_massive_pause with protection)
   Added: v3.15.2 (bug fix for click timing)

4. COMBINATION HISTORY
   Status: ✅ ACTIVE (Always)
   What: Tracks which folder combinations have been used
   Prevents: Repeating same combination across cycles
   Tracking: "F1=file01.json|F2=file05.json|F3=file12.json"
   File: COMBINATION_HISTORY_XX.txt (created per bundle)
   Purpose: Maximum variety across runs
   Code: Line ~1380-1510 (ManualHistoryTracker class)

4. COMBINATION HISTORY
   Status: ✅ ACTIVE (Always)
   What: Tracks which folder combinations have been used
   Prevents: Repeating same combination across cycles
   Tracking: "F1=file01.json|F2=file05.json|F3=file12.json"
   File: COMBINATION_HISTORY_XX.txt (created per bundle)
   Purpose: Maximum variety across runs
   Code: Line ~1380-1510 (ManualHistoryTracker class)

5. MANUAL HISTORY UPLOAD
   Status: ✅ ACTIVE (If files present)
   What: Upload old combination files to avoid repeating them
   Location: input_macros/combination_history/
   Reads: All .txt files automatically
   Purpose: Never repeat across multiple runs/sessions
   Code: Line ~1410-1450 (load history from folder)

6. ALPHABETICAL NAMING
   Status: ✅ ACTIVE (Always)
   What: Organized naming convention for output files
   Pattern:
     Raw files:        ^XX_A, ^XX_B, ^XX_C
     Inefficient:      ¬¬XX_D, ¬¬XX_E, ¬¬XX_F
     Normal:           XX_G, XX_H, XX_I, XX_J, XX_K, XX_L
   Purpose: Easy identification of file type at a glance
   Code: Line ~1940-1980 (filename generation)

7. FOLDER-NUMBER BASED STRUCTURE
   Status: ✅ ACTIVE (Always, supports decimals)
   Old Name: "Folder-based structure"
   What: Folders numbered in sequence; files cycle through them
   Format: "1- action/", "2- bank/", "3.5- optional/", "4- continue/"
   Decimal Support: 3.5 goes after 3 and before 4
   Pattern: F1 → F2 → F3 → F3.5 → F4 → F1 → ...
   Purpose: Maintains sequential action steps
   Code: Line ~1318-1360 (folder number extraction & sorting)

8. 'OPTIONAL' TAGGED FOLDERS
   Status: ✅ ACTIVE (If "optional" in folder name)
   Old Name: "Optional folders"
   Tag Detection: "optional" anywhere in folder name (case-insensitive)
   Behavior: Folder has random chance to be included in each cycle
   Chance: 24-33% (randomized per bundle, consistent within bundle)
   Example: "3 optional- bank early/"
   Purpose: Unpredictable action path variations
   Code: Line ~1442 (is_optional detection)

9. 'END' TAGGED FOLDERS
   Status: ✅ ACTIVE (If "end" in folder name)
   Tag Detection: "end" anywhere in folder name (case-insensitive)
   Behavior: Folder becomes definitive loop endpoint (stops after)
   Example: "5 end- logout/"
   Purpose: Controlled endpoint timing
   Code: Line ~1347 (is_end detection)

10. 'OPTIONAL/END' COMBO TAGGED FOLDERS
    Status: ✅ ACTIVE (If both "optional" and "end" in name)
    Tag Detection: Both "optional" AND "end" in folder name
    Behavior: 
      - 24-33% chance to include folder
      - IF included: Loop stops at this folder
      - IF skipped: Loop continues to next folders
    Example: "3.5 optional/end- early bank/"
    Purpose: Sometimes end early, sometimes continue full loop
    Code: Line ~1448-1462 (is_optional_end handling)

11. 'TIME SENSITIVE' TAGGED FOLDERS
    Status: ✅ ACTIVE (If "time sensitive" in folder name)
    New Feature: v3.13.0 | Enhanced: v3.14.2
    Tag Detection: "time sensitive" anywhere in folder name (case-insensitive)
    Behavior: NO inefficient files generated
    
    Two Application Modes:
      A) MAIN FOLDER TAGGED:
         Example: "61- Mining TIME SENSITIVE/"
                    └── 1- setup/
                    └── 2- mine/
                    └── 3- bank/
         Result: ALL subfolders (1, 2, 3) become time_sensitive
         
      B) INDIVIDUAL SUBFOLDER TAGGED:
         Example: "61- Mining/"
                    └── 1- setup/
                    └── 2 time sensitive- mine/  ← Only this one
                    └── 3- bank/
         Result: Only subfolder 2 is time_sensitive
    
    File Distribution Changes:
      - Regular folder: 3 Raw + 3 Inef + 6 Normal = 12 files
      - Time sensitive: 3 Raw + 0 Inef + 9 Normal = 12 files
    
    Priority: Main folder tag overrides individual subfolder tags
    Purpose: Activities requiring consistent timing (combat, PvP, timed tasks)
    Code: Line ~1449-1459 (main folder check), Line ~1505-1511 (subfolder check)
    Note: Entire bundle affected if ANY folder is time_sensitive

12. 'DON'T USE FEATURES ON ME' TAGGED FOLDERS
    Status: ✅ ACTIVE (If folder name matches)
    Old Name: "DMWM Support" or "dont mess with me"
    Tag Detection: Exact match "Don't use features on me" (case-insensitive)
    Backward Compatible: Also accepts old name "dont mess with me"
    Behavior: Files from this folder inserted completely unmodified
    Features Skipped: NO jitter, NO pauses, NO modifications
    Marked In Manifest: "[UNMODIFIED] filename.json"
    Purpose: Include specific pre-made sequences as-is
    Code: Line ~1433-1441 (folder detection)

13. ALWAYS FIRST/LAST FILES
    Status: ✅ ACTIVE (If tagged in filename)
    Tag Detection: "always first", "alwaysfirst", "always last", "alwayslast"
    Location: In filename (case-insensitive)
    Behavior:
      - "always first" → Plays first in its folder (before random selection)
      - "always last" → Plays last in its folder (after random selection)
    Example: "setup_always_first.json", "cleanup_alwayslast.json"
    Purpose: Guaranteed sequence control within folders
    Code: Line ~1333-1340 (always_first/last detection)

14. COMPREHENSIVE MANIFEST
    Status: ✅ ACTIVE (Always)
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
    Status: ⚙️ OPTIONAL (--specific-folders <file>)
    What: Only process folders listed in file
    Default: Process ALL numbered folders
    Usage: Pass text file with folder numbers (one per line)
    Purpose: Run subset of activities
    Code: Line ~1640-1665 (filtering logic)

16. CHAT INSERTS
    Status: ⚙️ OPTIONAL (Disabled by default, --no-chat flag)
    What: Random chat messages inserted in files
    Frequency: 50% of files when enabled
    Default: DISABLED in workflows
    Purpose: Social presence simulation
    Code: Line ~1850-1860 (chat insertion - currently bypassed)

═══════════════════════════════════════════════════════════════════════════
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
    Removes: HOME(36), END(35), PAGE_UP(33), PAGE_DOWN(34), ESC(27), PAUSE(19), PRINT_SCREEN(44)
    """
    problematic_codes = {27, 19, 33, 34, 35, 36, 44}
    filtered = []
    
    for event in events:
        keycode = event.get('KeyCode')
        if keycode in problematic_codes:
            continue
        filtered.append(event)
    
    return filtered

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


def is_in_drag_sequence(events, index):
    """
    Check if the given index is inside a drag sequence (between DragStart and DragEnd).
    Returns True if we're in the middle of a drag.
    """
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

def detect_rapid_click_sequences(events):
    """
    Detect sequences of rapid clicks at similar coordinates.
    
    Detects:
    - Double clicks (2 clicks within 500ms, ±5 pixels)
    - Spam clicks (3+ clicks within 2 seconds, ±10 pixels)
    
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
    4. Jitter = 2-3 micro-movements (±1-3px) + final snap to exact position
    
    Returns (events_with_jitter, jitter_count, total_moves, jitter_percentage).
    """
    if not events or len(events) < 2:
        return events, 0, 0, 0.0
    
    # Step 1: Find ALL click times (any click-like event)
    click_types = {'Click', 'LeftDown', 'RightDown', 'DragStart'}
    click_times = set()
    
    for event in events:
        if event.get('Type') in click_types:
            click_times.add(event.get('Time', 0))
    
    # Step 2: Find all MouseMove events that are SAFE to jitter
    # Safe = NOT within 1000ms before/after ANY click
    safe_movements = []
    total_moves = 0
    
    for i, event in enumerate(events):
        if event.get('Type') == 'MouseMove':
            total_moves += 1
            event_time = event.get('Time', 0)
            
            # Check if within exclusion zone of ANY click
            is_safe = True
            for click_time in click_times:
                time_diff = abs(event_time - click_time)
                if time_diff <= 1000:  # Within 1 second
                    is_safe = False
                    break
            
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
        
        current_time = move_time - time_budget
        
        # Add jitter movements (±1-3 pixels)
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

def insert_intra_file_pauses(events: list, rng: random.Random, protected_ranges: list = None) -> tuple:
    """
    Insert random pauses before recorded actions.
    Each file gets 1-4 random pauses (randomly chosen per file).
    Each pause is 1000-2000ms (non-rounded).
    Protected ranges (rapid click sequences) are skipped.
    Returns (events_with_pauses, total_pause_time).
    """
    if not events or len(events) < 5:
        return events, 0
    
    if protected_ranges is None:
        protected_ranges = []
    
    # Randomly decide how many pauses for this file (1-4)
    num_pauses = rng.randint(1, 4)
    
    # Find valid indices (not in protected ranges)
    valid_indices = []
    for idx in range(1, len(events)):
        if not is_in_protected_range(idx, protected_ranges):
            valid_indices.append(idx)
    
    if not valid_indices:
        return events, 0
    
    # Select random unique indices from valid ones
    num_pauses = min(num_pauses, len(valid_indices))
    pause_indices = rng.sample(valid_indices, num_pauses)
    pause_indices.sort()
    
    total_pause_added = 0
    
    # Apply pauses at selected indices
    for pause_idx in pause_indices:
        # Generate non-rounded pause duration (1000-2000ms)
        pause_duration = int(rng.uniform(1000.123, 1999.987))
        total_pause_added += pause_duration
        
        # Shift this event and all subsequent events by the pause (no rounding!)
        for j in range(pause_idx, len(events)):
            events[j]["Time"] = events[j]["Time"] + pause_duration
    
    return events, total_pause_added

def insert_idle_mouse_movements(events, rng, movement_percentage):
    """
    Insert realistic human-like mouse movements during idle periods (gaps > 2 seconds).
    
    Movements have:
    - Variable speeds (fast bursts, slow drifts, hesitations)
    - Imperfect paths (wobbles, overshoots, corrections)
    - Natural patterns (wandering, checking, fidgeting)
    - Smooth transition back to next recorded position
    """
    if not events or len(events) < 2:
        return events, 0
    
    result = []
    total_idle_time = 0
    
    for i in range(len(events)):
        result.append(events[i])
        
        # Check gap to next event
        if i < len(events) - 1:
            current_time = int(events[i].get("Time", 0))
            next_time = int(events[i + 1].get("Time", 0))
            gap = next_time - current_time
            
            # Only process gaps >= 2 seconds
            if gap >= 2000:
                # Skip if in drag sequence
                if is_in_drag_sequence(events, i):
                    continue
                
                # CRITICAL: Check if there's a click within 3 seconds AFTER this gap
                # This prevents idle movements from interfering with clicks!
                click_too_close = False
                check_window = 3000  # 3 seconds in ms
                
                for j in range(i + 1, len(events)):
                    event_time = events[j].get("Time", 0)
                    if event_time > next_time + check_window:
                        break  # Past the 3-second window
                    
                    event_type = events[j].get("Type", "")
                    if event_type in ("Click", "LeftDown", "LeftUp", "RightDown", "RightUp"):
                        # Found a click within 3 seconds - skip idle movements!
                        click_too_close = True
                        break
                
                if click_too_close:
                    continue  # Skip idle movements for this gap
                
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
        self.efficient = [f for f in all_files if "¬¬" not in f.name]
        self.inefficient = [f for f in all_files if "¬¬" in f.name]
        self.eff_pool = list(self.efficient)
        self.ineff_pool = list(self.inefficient)
        self.rng.shuffle(self.eff_pool)
        self.rng.shuffle(self.ineff_pool)

    def get_sequence(self, target_minutes, force_inef=False, is_time_sensitive=False):
        seq, cur_ms = [], 0.0
        target_ms = target_minutes * 60000
        # Add ±5% margin for flexibility
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
            # 1.35x = sweet spot (target Â±2-4 min)
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
    Insert one massive pause (500-2900ms × multiplier) at random point.
    For INEFFICIENT files only.
    
    EXCLUDES pause from:
    - Drag sequences (between DragStart and DragEnd)
    - Rapid click sequences (double-clicks, spam clicks)
    - First/last 10% of file (for safety)
    
    Returns (events_with_pause, pause_duration_ms, split_index)
    """
    if not events or len(events) < 10:
        return events, 0, 0
    
    # Generate massive pause: 2-5 minutes (120000-300000ms) × multiplier
    pause_duration = int(rng.uniform(120000.0, 300000.0) * mult)
    
    # Detect protected ranges (rapid clicks, double-clicks)
    protected_ranges = detect_rapid_click_sequences(events)
    
    # Find safe split points (not in drag, not in rapid click, not in first/last 10%)
    safe_indices = []
    first_safe = int(len(events) * 0.1)  # Skip first 10%
    last_safe = int(len(events) * 0.9)   # Skip last 10%
    
    for i in range(first_safe, last_safe):
        # Check if in drag sequence
        if is_in_drag_sequence(events, i):
            continue
        
        # Check if in protected range (rapid clicks)
        if is_in_protected_range(i, protected_ranges):
            continue
        
        # CRITICAL FIX: Check if NEXT event is DragStart
        # If pause is inserted right before DragStart, it shifts the DragEnd forward,
        # making the drag appear to last much longer than it actually does!
        if i + 1 < len(events) and events[i + 1].get("Type") == "DragStart":
            continue
        
        # Also check if NEXT event is part of a drag sequence
        # (this catches edge cases where there might be events between pause and DragStart)
        if i + 1 < len(events) and is_in_drag_sequence(events, i + 1):
            continue
        
        # This is a safe index
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

def string_cycle(subfolder_files, combination, rng, dmwm_file_set=set()):
    """
    String one complete cycle (F1 → F2 → F3 → ...) into a single unit.
    Returns raw events WITHOUT anti-detection features.
    Features will be applied to the ENTIRE cycle after.
    
    Args:
        subfolder_files: Dict of {folder_num: {'files': [...], 'is_optional': bool, 
                                               'always_first': Path, 'always_last': Path}}
        combination: List of (folder_num, file_path) tuples
        rng: Random generator
        dmwm_file_set: Set of unmodified file paths
    
    Returns:
        Dict with keys:
            'events': cycle_events (list)
            'file_info': file_info_list [(folder_num, filename, is_dmwm, end_time_within_cycle), ...]
            'has_dmwm': True if any dmwm file in cycle
            'pre_pause_total': Total pre-file pause time (ms)
            'post_pause_total': Total post-pause delay time (ms)
            'transition_total': Total cursor transition time (ms)
    """
    
    def add_file_to_cycle(file_path, folder_num, is_dmwm, file_label):
        """Helper to add a file to the cycle"""
        nonlocal timeline, cycle_events, file_info_list, has_dmwm, total_pre_pause, total_post_pause, total_transition_time
        
        # Load events
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception:
            return
        
        if not events:
            return
        
        # Filter problematic keys only
        events = filter_problematic_keys(events)
        if not events:
            return
        
        # Check if dmwm file
        if is_dmwm:
            has_dmwm = True
        
        # Normalize timing
        base_time = min(e.get('Time', 0) for e in events)
        
        # PRE-FILE PAUSE: 0.8 seconds BEFORE file plays (FLAT, NO multiplier)
        # This prevents drag issues when previous file ended with a click!
        if cycle_events:
            # Fixed pause: 800ms exactly
            pre_file_pause = 800
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
            
            # POST-PAUSE DELAY: DISABLED (marked for removal in v4.0)
            post_pause_delay = 0
            timeline += post_pause_delay
            total_post_pause += post_pause_delay
            
            # Transition duration: 200-400ms (for actual cursor movement)
            transition_duration = int(rng.uniform(200, 400))
            
            # Add smooth cursor transition AFTER pause
            if last_x and first_x and (last_x != first_x or last_y != first_y):
                transition_path = generate_human_path(
                    last_x, last_y, first_x, first_y,
                    transition_duration, rng
                )
                
                # Add transition movements
                for rel_time, x, y in transition_path:
                    cycle_events.append({
                        'Type': 'MouseMove',
                        'Time': timeline + rel_time,
                        'X': x,
                        'Y': y
                    })
                
                timeline += transition_duration
                
                # Track transition time
                total_transition_time += transition_duration
                
                # Final position to ensure exact placement
                cycle_events.append({
                    'Type': 'MouseMove',
                    'Time': timeline,
                    'X': first_x,
                    'Y': first_y
                })
        
        # Add events from current file
        for event in events:
            new_event = {**event}
            new_event['Time'] = event['Time'] - base_time + timeline
            cycle_events.append(new_event)
        
        # Update timeline and track THIS file's end time
        if cycle_events:
            timeline = cycle_events[-1]['Time']
            # Track file info with its individual end time
            file_info_list.append((folder_num, file_label, is_dmwm, timeline))
    
    # Main cycle building
    cycle_events = []
    file_info_list = []
    timeline = 0
    has_dmwm = False
    
    # NEW: Track pre-file pauses, post-pause delays, and cursor transitions
    total_pre_pause = 0
    total_post_pause = 0
    total_transition_time = 0
    
    for folder_num, file_path in combination:
        # Get folder data
        folder_data = subfolder_files.get(folder_num, {})
        
        # FIRST: Play "always first" if it exists
        always_first = folder_data.get('always_first')
        if always_first:
            is_dmwm = always_first in dmwm_file_set
            add_file_to_cycle(always_first, folder_num, is_dmwm, f"[ALWAYS FIRST] {always_first.name}")
        
        # SECOND: Play the selected file
        is_dmwm = file_path in dmwm_file_set
        add_file_to_cycle(file_path, folder_num, is_dmwm, file_path.name)
        
        # THIRD: Play "always last" if it exists
        always_last = folder_data.get('always_last')
        if always_last:
            is_dmwm = always_last in dmwm_file_set
            add_file_to_cycle(always_last, folder_num, is_dmwm, f"[ALWAYS LAST] {always_last.name}")
    
    return {
        'events': cycle_events,
        'file_info': file_info_list,
        'has_dmwm': has_dmwm,
        'pre_pause_total': total_pre_pause,
        'post_pause_total': total_post_pause,
        'transition_total': total_transition_time
    }


def apply_cycle_features(cycle_events, rng, is_raw, has_dmwm):
    """
    Apply anti-detection features to a complete cycle.
    This is where jitter, pauses, idle movements are added to the ENTIRE cycle.
    
    Args:
        cycle_events: Events from one complete cycle
        rng: Random generator
        is_raw: If True, skip intra-cycle pauses
        has_dmwm: If True, skip ALL modifications (cycle contains dmwm file)
    
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
        # Cycle contains dmwm file - no modifications
        return cycle_events, stats
    
    # Step 1: Jitter (RE-ENABLED)
    events_with_jitter, jitter_count, move_count, jitter_pct = add_pre_click_jitter(cycle_events, rng)
    stats['jitter_count'] = jitter_count
    stats['total_moves'] = move_count
    stats['jitter_percentage'] = jitter_pct
    
    # Step 2: Rapid click detection
    protected_ranges = detect_rapid_click_sequences(events_with_jitter)
    
    # Step 3: Intra-cycle pauses (skip for raw)
    if not is_raw:
        events_with_pauses, pause_time = insert_intra_file_pauses(
            events_with_jitter, rng, protected_ranges
        )
        stats['intra_pauses'] = pause_time
    else:
        events_with_pauses = events_with_jitter
    
    # Step 4: Idle movements
    movement_pct = rng.uniform(0.40, 0.50)
    events_with_idle, idle_time = insert_idle_mouse_movements(
        events_with_pauses, rng, movement_pct
    )
    stats['idle_movements'] = idle_time
    
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
    
    # NEW: Check if MAIN FOLDER is tagged with "time sensitive"
    # If so, ALL subfolders inside will be time_sensitive!
    main_folder_time_sensitive = 'time sensitive' in base.name.lower()
    if main_folder_time_sensitive:
        print(f"  ⏱️  MAIN FOLDER is TIME SENSITIVE - All subfolders will skip inefficient files!")
    
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
            print(f"  ⚠️  Found 'Don't use features on me' folder: {len(dmwm_files)} unmodified files")
            continue
        
        # Extract number from folder name using regex (supports decimals!)
        # Matches: "1", "2.5", "3.14", etc.
        match = re.search(r'\d+\.?\d*', item.name)
        if match:
            folder_num = float(match.group())
            all_json_files = sorted(item.glob("*.json"))
            
            # Separate "always first", "always last", and regular files
            always_first = None
            always_last = None
            regular_files = []
            
            for json_file in all_json_files:
                filename_lower = json_file.name.lower()
                if 'always first' in filename_lower or 'alwaysfirst' in filename_lower:
                    always_first = json_file
                    print(f"  📌 Found 'always first' in folder {folder_num}: {json_file.name}")
                elif 'always last' in filename_lower or 'alwayslast' in filename_lower:
                    always_last = json_file
                    print(f"  📌 Found 'always last' in folder {folder_num}: {json_file.name}")
                else:
                    regular_files.append(json_file)
            
            # Check if folder is "optional" (24-33% random chance to include)
            is_optional = 'optional' in item.name.lower()
            optional_chance = random.uniform(0.24, 0.33) if is_optional else None
            
            # Check if folder is "end" (becomes definitive end point)
            is_end = 'end' in item.name.lower()
            
            # Check if folder is "time sensitive" (no inefficient files generated)
            # Priority: Main folder tag > Individual subfolder tag
            if main_folder_time_sensitive:
                is_time_sensitive = True  # Main folder overrides all
            else:
                is_time_sensitive = 'time sensitive' in item.name.lower()
            
            # "optional/end" combo: optional folder that ends loop if chosen
            is_optional_end = is_optional and is_end
            
            if regular_files:  # Must have at least one regular file
                numbered_folders[folder_num] = {
                    'files': regular_files,
                    'is_optional': is_optional,
                    'optional_chance': optional_chance,
                    'is_end': is_end,
                    'is_optional_end': is_optional_end,
                    'is_time_sensitive': is_time_sensitive,
                    'always_first': always_first,
                    'always_last': always_last
                }
                
            # Also collect non-JSON files from numbered folders
            for file in item.iterdir():
                if file.is_file() and not file.name.endswith('.json'):
                    non_json_files.append(file)
    
    # Add unmodified files to their respective numbered folder pools
    # They become regular files, just tracked separately
    dmwm_file_set = set(unmodified_files)
    
    return numbered_folders, dmwm_file_set, non_json_files

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
        
        print(f"  📊 {len(self.used_combinations)} combinations loaded from history")
        print(f"  📁 History folder: {self.history_dir}")
    
    def _load_all_combinations(self):
        """Read ALL .txt files in history folder and build set of used combos"""
        all_used = set()
        
        if not self.history_dir.exists():
            print(f"  📝 No history folder found (will skip tracking)")
            return all_used
        
        # Read ALL .txt files
        txt_files = list(self.history_dir.glob("*.txt"))
        if not txt_files:
            print(f"  📝 History folder empty (no .txt files)")
            return all_used
        
        print(f"  📂 Reading {len(txt_files)} history file(s)...")
        
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
                
                print(f"    ✅ {txt_file.name}: Loaded")
                
            except Exception as e:
                print(f"    ⚠️  {txt_file.name}: Error - {e}")
        
        return all_used
    
    def get_next_combination(self):
        """Get next unused combination (with end folder support)"""
        max_attempts = 500
        
        for _ in range(max_attempts):
            # Pick random combination
            combination = []
            for folder_num in sorted(self.subfolder_files.keys()):
                folder_data = self.subfolder_files[folder_num]
                
                # Check for "optional/end" combo (optional folder that ends loop if chosen)
                if folder_data.get('is_optional_end', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() < optional_chance:
                        # Optional/end folder was chosen - include it and STOP
                        files = folder_data['files']
                        if files:
                            chosen_file = self.rng.choice(files)
                            combination.append((folder_num, chosen_file))
                        break  # End the loop here
                    else:
                        # Optional/end folder was skipped - continue to next folders
                        continue
                
                # Check for regular "end" folder (always included, always ends loop)
                if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                    # End folder - include it and STOP
                    files = folder_data['files']
                    if files:
                        chosen_file = self.rng.choice(files)
                        combination.append((folder_num, chosen_file))
                    break  # End the loop here
                
                # Regular optional folder check (uses random 27-43% chance stored per folder)
                if folder_data.get('is_optional', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() >= optional_chance:
                        continue
                
                # Pick random file from this folder
                files = folder_data['files']
                if files:
                    chosen_file = self.rng.choice(files)
                    combination.append((folder_num, chosen_file))
            
            if not combination:
                continue
            
            # Create signature (format folder numbers cleanly)
            signature = "|".join(
                f"F{int(fn) if fn == int(fn) else fn}={f.name}" 
                for fn, f in combination
            )
            
            # Check if unused
            if signature not in self.used_combinations:
                self.used_combinations.add(signature)  # Mark as used
                return combination
        
        # Fallback: return random (may repeat)
        print(f"  ⚠️  Using random combination (may repeat)")
        combination = []
        for folder_num in sorted(self.subfolder_files.keys()):
            folder_data = self.subfolder_files[folder_num]
            
            # Handle optional/end
            if folder_data.get('is_optional_end', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() < optional_chance:
                    files = folder_data['files']
                    if files:
                        combination.append((folder_num, self.rng.choice(files)))
                    break
                else:
                    continue
            
            # Handle regular end
            if folder_data.get('is_end', False) and not folder_data.get('is_optional', False):
                files = folder_data['files']
                if files:
                    combination.append((folder_num, self.rng.choice(files)))
                break
            
            # Handle regular optional
            if folder_data.get('is_optional', False):
                optional_chance = folder_data.get('optional_chance', 0.50)
                if self.rng.random() >= optional_chance:
                    continue
            
            files = folder_data['files']
            if files:
                combination.append((folder_num, self.rng.choice(files)))
        
        return combination if combination else None

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
        print(f"❌ Input root not found: {search_base}")
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
                print(f"✓ Found {len(chat_files)} chat insert files")
    
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
                    print(f"✓ Found logout file: {logout_file.name}")
                    break
    
    print()
    
    # Scan folders
    main_folders = []
    for folder in search_base.iterdir():
        if not folder.is_dir():
            continue
        
        numbered_subfolders, dmwm_file_set, non_json_files = scan_for_numbered_subfolders(folder)
        
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
                'subfolders': numbered_subfolders,
                'dmwm_files': dmwm_file_set,
                'non_json': non_json_files
            })
            print(f"✓ Found: {folder.name}")
            if numbered_subfolders:
                nums = sorted([k for k in numbered_subfolders.keys() if k != 0])
                print(f"  Subfolders: {nums}")
                
                # Show special folder types
                special_folders = []
                for num in nums:
                    if num in numbered_subfolders:
                        folder_info = numbered_subfolders[num]
                        if folder_info.get('is_optional_end'):
                            special_folders.append(f"{num} (optional/end)")
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
        print("❌ No folders with numbered subfolders found!")
        return
    
    # Filter by specific folders if provided
    if args.specific_folders:
        try:
            with open(args.specific_folders, 'r', encoding='utf-8') as f:
                # Read folder names, strip whitespace, ignore empty lines
                specific_names = [line.strip() for line in f if line.strip()]
            
            if specific_names:
                print(f"\n📋 Filtering to specific folders only:")
                for name in specific_names:
                    print(f"  - {name}")
                
                # Filter main_folders to only include specified folders
                filtered_folders = []
                for folder_data in main_folders:
                    if folder_data['name'] in specific_names:
                        filtered_folders.append(folder_data)
                
                if not filtered_folders:
                    print(f"\n❌ None of the specified folders were found!")
                    print(f"   Available folders: {[f['name'] for f in main_folders]}")
                    return
                
                main_folders = filtered_folders
                print(f"✅ Filtered to {len(main_folders)} folder(s)")
            else:
                print(f"\n⚠️  Specific folders file is empty, processing ALL folders")
        
        except FileNotFoundError:
            print(f"\n❌ Specific folders file not found: {args.specific_folders}")
            return
        except Exception as e:
            print(f"\n❌ Error reading specific folders file: {e}")
            return
    
    print(f"\n📁 Total folders to process: {len(main_folders)}")
    print("="*70)
    
    # Initialize global chat queue
    rng = random.Random(args.bundle_id * 42)
    global_chat_queue = list(chat_files) if chat_files else []
    if global_chat_queue:
        rng.shuffle(global_chat_queue)
        print(f"🔄 Initialized global chat queue with {len(global_chat_queue)} files")
        print()
    
    # Track ALL combinations for the bundle (one file at root level)
    bundle_combinations = {}  # {folder_name: [combination_signatures]}
    
    # Process each folder
    for folder_data in main_folders:
        folder_name = folder_data['name']
        subfolder_files = folder_data['subfolders']
        dmwm_file_set = folder_data['dmwm_files']
        non_json_files = folder_data['non_json']
        
        # D_ REMOVAL
        cleaned_folder_name = re.sub(r'[Dd]_', '', folder_name)
        
        # Extract folder number
        folder_num_match = re.search(r'\d+', cleaned_folder_name)
        folder_number = int(folder_num_match.group()) if folder_num_match else 0
        
        print(f"\n🔨 Processing: {cleaned_folder_name}")
        
        # Create output folder
        out_folder = bundle_dir / cleaned_folder_name
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
                print(f"  ✓ Copied logout: {new_name}")
            except Exception as e:
                print(f"  ✗ Error copying logout: {e}")
        
        # Copy non-JSON files with @ prefix
        for non_json_file in non_json_files:
            try:
                original_name = non_json_file.name
                if original_name.startswith("-"):
                    new_name = f"@ {folder_number} {original_name[1:].strip()}"
                else:
                    new_name = f"@ {folder_number} {original_name}"
                shutil.copy2(non_json_file, out_folder / new_name)
                print(f"  ✓ Copied non-JSON: {new_name}")
            except Exception as e:
                print(f"  ✗ Error copying {non_json_file.name}: {e}")
        
        if not subfolder_files:
            print("  ⚠️  No numbered subfolders to process")
            continue
        
        # Use bundle-organized tracker
        tracker = ManualHistoryTracker(
            subfolder_files, rng, cleaned_folder_name, search_base
        )
        target_ms = args.target_minutes * 60000
        
        # Track all combinations used in THIS RUN for this folder
        folder_combinations_used = []
        
        # Calculate total original duration
        total_original_files = 0
        total_original_ms = 0
        
        for folder_data in subfolder_files.values():
            files = folder_data['files']
            total_original_files += len(files)
            for f in files:
                total_original_ms += get_file_duration_ms(f)

        
        # Manifest header
        manifest_lines = [
            f"MANIFEST FOR FOLDER: {cleaned_folder_name}",
            "=" * 40,
            f"Script Version: {VERSION}",
            f"Stringed Bundle: stringed_bundle_{args.bundle_id}",
            f"Total Original Files: {total_original_files}",
            f"Total Original Files Duration: {format_ms_precise(total_original_ms)}",
            ""
        ]
        
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
            print(f"  ⏱️  TIME SENSITIVE folders detected: {', '.join(time_sensitive_folders)}")
        
        # Version loop: 3 Raw + 3 Inef + 6 Normal = 12 total
        # OR: 3 Raw + 0 Inef + 9 Normal = 12 total (if time_sensitive)
        version_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
        num_raw = 3
        
        if has_time_sensitive:
            # Time sensitive: Replace inefficient files with normal files
            num_inef = 0
            num_normal = 9
            print(f"  📊 File distribution: 3 Raw + 0 Inef + 9 Normal (instead of 3 Inef + 6 Normal)")
        else:
            # Regular: Standard distribution
            num_inef = 3
            num_normal = 6
            print(f"  📊 File distribution: 3 Raw + 3 Inef + 6 Normal (standard)")
        
        for v_idx in range(min(args.versions, 12)):
            v_letter = version_letters[v_idx]
            
            # Determine file type
            is_raw = (v_idx < num_raw)
            is_inef = (num_raw <= v_idx < num_raw + num_inef)
            is_normal = (v_idx >= num_raw + num_inef)
            
            # DEBUG: Show file type determination
            if v_idx == 0:  # First file
                print(f"\n  🔍 File Type Assignments:")
            
            file_type_str = "RAW" if is_raw else ("INEFFICIENT" if is_inef else "NORMAL")
            prefix_str = "^" if is_raw else ("¬¬" if is_inef else "none")
            print(f"     {v_letter}: {file_type_str:12s} (prefix: {prefix_str})")
            
            # Set multiplier (UPDATED v3.13.0)
            if is_raw:
                # Raw: x1.0 or x1.1 (50/50)
                mult = rng.choices([1.0, 1.1], weights=[50, 50], k=1)[0]
            elif is_inef:
                # Inefficient: x2.0 or x3.0 (60/40)
                mult = rng.choices([2.0, 3.0], weights=[60, 40], k=1)[0]
            else:  # normal
                # Normal: x1.3 or x1.5 (65/35)
                mult = rng.choices([1.3, 1.5], weights=[65, 35], k=1)[0]
            
            # Build cycles until target reached
            stringed_events = []
            all_file_info_with_times = []  # List of (folder_num, filename, is_dmwm, end_time) tuples
            total_intra = 0
            total_inter = 0
            total_idle = 0
            total_normal_pauses = 0
            massive_pause_ms = 0
            jitter_pct = 0
            
            # NEW: Track pre-file pauses, post-pause delays, and cursor transitions
            total_pre_file = 0
            total_post_pause = 0
            total_transitions = 0
            
            while True:
                combo = tracker.get_next_combination()
                if not combo:
                    break
                
                # Track this combination signature (format folder numbers cleanly)
                combo_signature = "|".join(
                    f"F{int(fn) if fn == int(fn) else fn}={f.name}" 
                    for fn, f in combo
                )
                folder_combinations_used.append(combo_signature)
                
                # BUILD CYCLE (F1 → F2 → F3) WITHOUT features
                cycle_result = string_cycle(
                    subfolder_files, combo, rng, dmwm_file_set
                )
                
                cycle_events = cycle_result['events']
                file_info = cycle_result['file_info']
                has_dmwm = cycle_result['has_dmwm']
                
                if not cycle_events:
                    break
                
                # APPLY FEATURES to ENTIRE cycle
                cycle_with_features, stats = apply_cycle_features(
                    cycle_events, rng, is_raw, has_dmwm
                )
                
                # Check if adding would exceed target
                current_duration = stringed_events[-1]['Time'] if stringed_events else 0
                cycle_duration = cycle_with_features[-1]['Time'] if cycle_with_features else 0
                
                # Add INEFFICIENT Before File Pause (only for inefficient files, only if file >= 25 sec)
                inter_cycle_pause = 0
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
                margin = int(target_ms * 0.05)
                if potential_total > target_ms + margin and stringed_events:
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
                total_post_pause += cycle_result.get('post_pause_total', 0)
                total_transitions += cycle_result.get('transition_total', 0)
                
                if len(all_file_info_with_times) > 150:  # Safety limit
                    break
            
            if not stringed_events:
                continue
            
            # Add massive pause for INEFFICIENT
            if is_inef and len(stringed_events) > 1:
                stringed_events, massive_pause_ms, split_idx = insert_massive_pause(stringed_events, rng, mult)
                
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
                prefix = "¬¬"
            else:
                prefix = ""
            
            v_code = f"{folder_number}_{v_letter}"
            fname = f"{prefix}{v_code}_{total_min}m{total_sec}s.json"
            
            # CRITICAL FIXES before saving:
            # 1. Convert Click events to LeftDown+LeftUp pairs (prevents clamp)
            # 2. Sort all events by Time (prevents out-of-order gaps)
            stringed_events = fix_click_events(stringed_events)
            stringed_events = sorted(stringed_events, key=lambda e: e.get('Time', 0))
            
            # Save file
            (out_folder / fname).write_text(json.dumps(stringed_events, indent=2))
            
            # DEBUG: Show created file
            type_label = "RAW" if is_raw else ("INEF" if is_inef else "NORM")
            print(f"     ✓ Created: {fname:<30s} [{type_label}]")
            
            # Build manifest entry
            separator = "=" * 40
            version_label = f"Version {prefix}{v_code}_{total_min}m{total_sec}s:"
            
            if is_raw:
                total_pause = total_inter + total_pre_file + total_post_pause + total_transitions
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Raw (no time-adding features, no chat)",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                    f"BREAKDOWN before multiplier:",
                    f"                - PRE-Play Buffer: {format_ms_precise(total_pre_file)}",
                    f"                - CURSOR to Start Point: {format_ms_precise(total_transitions)}",
                    ""
                ]
            elif is_inef:
                total_pause = total_intra + total_inter + total_pre_file + total_post_pause + total_transitions + massive_pause_ms
                original_intra = total_intra
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Inefficient",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                    f"BREAKDOWN before multiplier:",
                    f"                - Within File Pauses: {format_ms_precise(original_intra)}",
                    f"                - INEFFICIENT Before File Pause: {format_ms_precise(original_inter)}",
                    f"                - PRE-Play Buffer: {format_ms_precise(total_pre_file)}",
                    f"                - CURSOR to Start Point: {format_ms_precise(total_transitions)}",
                    ""
                ]
                if massive_pause_ms > 0:
                    manifest_entry.insert(-1, f"                - INEFFICIENT MASSIVE PAUSE: {format_ms_precise(massive_pause_ms)}")
            else:  # normal
                total_pause = total_intra + total_inter + total_pre_file + total_post_pause + total_transitions
                original_intra = total_intra
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Normal",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                    f"BREAKDOWN before multiplier:",
                    f"                - Within File Pauses: {format_ms_precise(original_intra)}",
                    f"                - PRE-Play Buffer: {format_ms_precise(total_pre_file)}",
                    f"                - CURSOR to Start Point: {format_ms_precise(total_transitions)}",
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
        print(f"\n  📋 Manifest written: {manifest_path.name}")
        
        # Collect combinations for this folder (for bundle-level file)
        # Use the combinations we tracked during THIS RUN
        if folder_combinations_used:
            bundle_combinations[cleaned_folder_name] = folder_combinations_used
            print(f"  📊 Tracked {len(folder_combinations_used)} combinations for bundle file")
    
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
            print(f"\n📝 Combination file written: {combo_file.name}")
            print(f"   Total combinations: {total_combos} across {len(bundle_combinations)} folders")
        except Exception as e:
            print(f"\n⚠️  Could not write combination file: {e}")
    
    print("\n" + "="*70)
    print(f"✅ STRING MACROS COMPLETE - Bundle {args.bundle_id}")
    print(f"📦 Output: {bundle_dir}")
    print(f"\n💡 To track combinations:")
    print(f"   1. Upload COMBINATION_HISTORY_{args.bundle_id}.txt to:")
    print(f"      input_macros/combination_history/")
    print(f"   2. Code will read ALL .txt files and avoid duplicates")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
