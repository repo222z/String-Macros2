#!/usr/bin/env python3
"""
string_macros.py - v3.0.0 - Full Anti-Detection Suite
- Complete anti-detection suite with all features
- Mouse jitter (20-45% of movements)
- Idle mouse movements (fills gaps >=5 seconds)  
- Intra-part pauses (1-4 per part, 1000-2000ms)
- Inter-part pauses (500-5000ms × multiplier)
- Rapid click protection (double-click/spam detection)
- File types: Raw (3 versions) + Normal (6 versions) = 9 total
- D_ removal from folder names
- Chat queue ensures unique inserts (no repeats until all used)
"""

import argparse, json, random, re, sys, os, math, shutil, itertools
from pathlib import Path

VERSION = "v3.0.0"

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

def generate_human_path(start_x, start_y, end_x, end_y, duration_ms, rng):
    """
    Generate a human-like mouse path with variable speed and wobbles.
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
    
    speed_profile = rng.choice(['fast_start', 'slow_start', 'medium', 'hesitant'])
    num_steps = max(3, min(int(distance / 15), int(duration_ms / 50)))
    
    # Add control points for curved path
    num_control = rng.randint(1, 3)
    control_points = []
    for _ in range(num_control):
        offset = rng.uniform(-0.3, 0.3) * distance
        t = rng.uniform(0.2, 0.8)
        ctrl_x = start_x + dx * t + (-dy / (distance + 1)) * offset
        ctrl_y = start_y + dy * t + (dx / (distance + 1)) * offset
        control_points.append((ctrl_x, ctrl_y, t))
    
    control_points.sort(key=lambda p: p[2])
    current_time = 0
    
    for step in range(num_steps + 1):
        t_raw = step / num_steps
        
        # Apply speed profile
        if speed_profile == 'fast_start':
            t = 1 - (1 - t_raw) ** 2
        elif speed_profile == 'slow_start':
            t = t_raw ** 2
        elif speed_profile == 'hesitant':
            t = 0.5 * (1 - math.cos(t_raw * math.pi))
        else:
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
        
        # Add wobble
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
    Add realistic pre-move jitter: before a random 20-45% of ALL mouse movements,
    add 2-3 micro-movements around the target (Â±1-3px), then snap to exact position.
    The percentage is randomly chosen per file (non-rounded).
    Returns (events_with_jitter, jitter_count, total_moves, jitter_percentage).
    """
    if not events or len(events) < 2:
        return events, 0, 0, 0.0
    
    # Randomly choose jitter percentage for this file (20-45%, non-rounded)
    jitter_percentage = rng.uniform(0.20, 0.45)
    
    jitter_count = 0
    total_moves = 0
    i = 0
    
    while i < len(events):
        event = events[i]
        event_type = event.get('Type', '')
        
        # Apply to ALL mouse movements (MouseMove, Click, RightDown)
        if event_type in ('MouseMove', 'Click', 'RightDown'):
            total_moves += 1
            
            # Random chance based on jitter_percentage
            if rng.random() < jitter_percentage:
                move_x = event.get('X')
                move_y = event.get('Y')
                move_time = event.get('Time')
                
                if move_x is not None and move_y is not None and move_time is not None:
                    num_jitters = rng.randint(2, 3)
                    jitter_events = []
                    
                    time_budget = rng.randint(100, 200)
                    time_per_jitter = time_budget // (num_jitters + 1)
                    
                    current_time = move_time - time_budget
                    
                    for j in range(num_jitters):
                        offset_x = rng.randint(-3, 3)
                        offset_y = rng.randint(-3, 3)
                        
                        jitter_x = int(move_x) + offset_x
                        jitter_y = int(move_y) + offset_y
                        
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
                    
                    for idx, jitter_event in enumerate(jitter_events):
                        events.insert(i + idx, jitter_event)
                    
                    i += len(jitter_events)
                    jitter_count += 1
        
        i += 1
    
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
    Insert realistic human-like mouse movements during idle periods (gaps > 5 seconds).
    
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
            
            # Only process gaps >= 5 seconds
            if gap >= 5000:
                # Skip if in drag sequence
                if is_in_drag_sequence(events, i):
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


# ============================================================================
# STRING PARTS WITH ANTI-DETECTION
# ============================================================================

def string_parts(subfolder_files, combination, rng, is_raw=False, multiplier=1):
    """
    String together parts from numbered subfolders with full anti-detection.
    
    Args:
        subfolder_files: Dict of {folder_num: [files]}
        combination: List of selected files (one per subfolder)
        rng: Random number generator
        is_raw: If True, skip intra-part pauses
        multiplier: Inter-part pause multiplier (1, 2, or 3)
    
    Returns:
        (stringed_events, file_names, stats)
    """
    stringed_events = []
    timeline = 0
    
    # Statistics tracking
    stats = {
        'total_jitter_count': 0,
        'total_moves': 0,
        'jitter_percentage': 0.0,
        'total_intra_pauses': 0,
        'total_inter_pauses': 0,
        'total_idle_movements': 0,
        'movement_percentage': rng.uniform(0.40, 0.50)
    }
    
    for idx, (folder_num, file_path) in enumerate(combination):
        # Load events from this part
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception as e:
            print(f"    ⚠️ Error loading {file_path.name}: {e}")
            continue
        
        if not events:
            continue
        
        # CRITICAL: Filter problematic keys
        events = filter_problematic_keys(events)
        if not events:
            continue
        
        # STEP 1: Add pre-move jitter (20-45% of movements)
        events_with_jitter, jitter_count, click_count, jitter_pct = add_pre_click_jitter(events, rng)
        stats['total_jitter_count'] += jitter_count
        stats['total_moves'] += click_count
        stats['jitter_percentage'] = jitter_pct  # Last file's percentage
        
        # STEP 2: Detect rapid click sequences (protect from pauses)
        protected_ranges = detect_rapid_click_sequences(events_with_jitter)
        
        # STEP 3: Add intra-part pauses (skip for RAW files)
        if not is_raw:
            events_with_pauses, intra_pause_time = insert_intra_file_pauses(
                events_with_jitter, rng, protected_ranges
            )
            stats['total_intra_pauses'] += intra_pause_time
        else:
            events_with_pauses = events_with_jitter
        
        # STEP 4: Add idle mouse movements (fills gaps >=5 seconds)
        events_with_movements, idle_time = insert_idle_mouse_movements(
            events_with_pauses, rng, stats['movement_percentage']
        )
        stats['total_idle_movements'] += idle_time
        
        # Normalize timing to start at 0
        base_time = min(e.get('Time', 0) for e in events_with_movements)
        
        # STEP 5: Inter-part pause (between parts)
        if idx > 0:
            # Calculate inter-part pause with multiplier
            inter_pause = int(rng.uniform(500.123, 4999.987) * multiplier)
            stats['total_inter_pauses'] += inter_pause
            
            # Add cursor transition during inter-part pause
            if stringed_events and events_with_movements:
                # Get last cursor position from previous part
                last_cursor_event = None
                for e in reversed(stringed_events):
                    if e.get('X') is not None and e.get('Y') is not None:
                        last_cursor_event = e
                        break
                
                # Get first cursor position from current part
                first_cursor_event = None
                for e in events_with_movements:
                    if e.get('X') is not None and e.get('Y') is not None:
                        first_cursor_event = e
                        break
                
                # Add smooth transition if positions differ
                if last_cursor_event and first_cursor_event:
                    last_x, last_y = int(last_cursor_event['X']), int(last_cursor_event['Y'])
                    first_x, first_y = int(first_cursor_event['X']), int(first_cursor_event['Y'])
                    
                    if (last_x != first_x) or (last_y != first_y):
                        # Generate smooth path during inter-pause
                        transition_path = generate_human_path(
                            last_x, last_y,
                            first_x, first_y,
                            inter_pause,
                            rng
                        )
                        
                        # Insert transition events (skip last, will be first event of next part)
                        for rel_time, x, y in transition_path[:-1]:
                            if rel_time < inter_pause:
                                stringed_events.append({
                                    'Type': 'MouseMove',
                                    'Time': timeline + rel_time,
                                    'X': x,
                                    'Y': y
                                })
            
            timeline += inter_pause
        
        # STEP 6: Add events from current part
        for event in events_with_movements:
            new_event = {**event}
            new_event['Time'] = event['Time'] - base_time + timeline
            stringed_events.append(new_event)
        
        # Update timeline (after this part)
        if stringed_events:
            timeline = stringed_events[-1]['Time']
    
    return stringed_events, [f[1].name for f in combination], stats


# ============================================================================
# FOLDER SCANNING
# ============================================================================

def scan_for_numbered_subfolders(base_path):
    """
    Scans folder for subfolders with numbers in their names.
    Accepts: "1", "part1", "step2", "3-action", etc.
    Returns dict: {extracted_number: [list of .json files]}
    """
    base = Path(base_path)
    numbered_folders = {}
    
    for item in base.iterdir():
        if not item.is_dir():
            continue
        
        # Extract number from folder name using regex
        match = re.search(r'\d+', item.name)
        if match:
            folder_num = int(match.group())
            json_files = sorted(item.glob("*.json"))
            if json_files:
                numbered_folders[folder_num] = json_files
    
    return numbered_folders

# ============================================================================
# COMBINATION TRACKER (Virtual Queue)
# ============================================================================

class CombinationTracker:
    """
    Tracks which file combinations have been used.
    Ensures no repeats until ALL combinations exhausted.
    """
    def __init__(self, subfolder_files, rng):
        self.subfolder_files = subfolder_files
        self.rng = rng
        self.used_combinations = set()
        
        # Calculate total possible combinations
        self.total_combinations = 1
        for files in subfolder_files.values():
            self.total_combinations *= len(files)
    
    def get_next_combination(self):
        """
        Get next unused combination.
        Returns: List of (folder_num, file_path) tuples in order.
        """
        if len(self.used_combinations) >= self.total_combinations:
            # All combinations used - reset
            self.used_combinations.clear()
        
        # Try to find unused combination
        max_attempts = self.total_combinations * 2
        for _ in range(max_attempts):
            # Pick one random file from each subfolder
            combination = []
            for folder_num in sorted(self.subfolder_files.keys()):
                files = self.subfolder_files[folder_num]
                chosen_file = self.rng.choice(files)
                combination.append((folder_num, chosen_file))
            
            # Create signature for this combination
            signature = tuple(f.name for _, f in combination)
            
            if signature not in self.used_combinations:
                self.used_combinations.add(signature)
                return combination
        
        # Fallback: return any combination
        combination = []
        for folder_num in sorted(self.subfolder_files.keys()):
            files = self.subfolder_files[folder_num]
            chosen_file = self.rng.choice(files)
            combination.append((folder_num, chosen_file))
        return combination

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="String Macros v3.0.0")
    parser.add_argument("input_root", type=str)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--versions", type=int, default=9, help="Total versions (default: 9 = 3 Raw + 6 Normal)")
    parser.add_argument("--target-minutes", type=int, default=35)
    parser.add_argument("--bundle-id", type=int, required=True)
    parser.add_argument("--no-chat", action="store_true", help="Disable chat inserts")
    args = parser.parse_args()
    
    print("="*70)
    print(f"STRING MACROS v{VERSION}")
    print("="*70)
    print(f"Bundle ID: {args.bundle_id}")
    print(f"Target: {args.target_minutes} minutes per file")
    print(f"Versions: {args.versions} total")
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
    
    # Load chat files (optional)
    chat_files = []
    if not args.no_chat:
        chat_dir = Path(args.input_root).parent / "chat inserts"
        if chat_dir.exists() and chat_dir.is_dir():
            chat_files = list(chat_dir.glob("*.json"))
            if chat_files:
                print(f"✓ Found {len(chat_files)} chat insert files")
            else:
                print(f"⚠️ Chat inserts folder empty")
        else:
            print(f"⚠️ No chat inserts folder found")
    else:
        print(f"🔕 Chat inserts DISABLED")
    
    print()
    
    # Scan folders
    main_folders = []
    for folder in search_base.iterdir():
        if not folder.is_dir():
            continue
        
        numbered_subfolders = scan_for_numbered_subfolders(folder)
        
        if numbered_subfolders:
            main_folders.append({
                'path': folder,
                'name': folder.name,
                'subfolders': numbered_subfolders
            })
            print(f"✓ Found: {folder.name}")
            print(f"  Subfolders: {sorted(numbered_subfolders.keys())}")
    
    if not main_folders:
        print("❌ No folders with numbered subfolders found!")
        return
    
    print(f"\n📁 Total folders to process: {len(main_folders)}")
    print("="*70)
    
    # Initialize global chat queue (persists across all folders)
    rng = random.Random(args.bundle_id * 42)
    global_chat_queue = list(chat_files) if chat_files else []
    if global_chat_queue:
        rng.shuffle(global_chat_queue)
        print(f"🔄 Initialized global chat queue with {len(global_chat_queue)} files")
        print()
    
    # Process each folder
    for folder_data in main_folders:
        folder_name = folder_data['name']
        subfolder_files = folder_data['subfolders']
        
        # D_ REMOVAL: Remove D_ or d_ from folder name
        cleaned_folder_name = re.sub(r'[Dd]_', '', folder_name)
        
        # Extract folder number for version code (e.g. "47- Canifis" → 47)
        folder_num_match = re.search(r'\d+', cleaned_folder_name)
        folder_number = int(folder_num_match.group()) if folder_num_match else 0
        
        print(f"\n🔨 Processing: {cleaned_folder_name}")
        
        tracker = CombinationTracker(subfolder_files, rng)
        
        out_folder = bundle_dir / cleaned_folder_name
        out_folder.mkdir(parents=True, exist_ok=True)
        
        target_ms = args.target_minutes * 60000
        
        # Manifest header
        total_original_files = sum(len(files) for files in subfolder_files.values())
        manifest_lines = [
            f"MANIFEST FOR FOLDER: {cleaned_folder_name}",
            "=" * 40,
            f"Script Version: {VERSION}",
            f"Stringed Bundle: stringed_bundle_{args.bundle_id}",
            f"Total Original Parts: {total_original_files}",
            f"Subfolders: {sorted(subfolder_files.keys())}",
            ""
        ]
        
        # Generate versions: 3 Raw + 6 Normal = 9 total
        version_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        num_raw = 3
        num_normal = 6
        
        for v_idx in range(args.versions):
            v_letter = version_letters[v_idx] if v_idx < len(version_letters) else chr(65 + v_idx)
            
            # Determine file type
            is_raw = (v_idx < num_raw)
            
            # Set multiplier based on file type
            if is_raw:
                # Raw: x1 (50%), x2 (30%), x3 (20%)
                mult = rng.choices([1, 2, 3], weights=[50, 30, 20], k=1)[0]
            else:
                # Normal: x1 (62.5%), x2 (37.5%)
                mult = rng.choices([1, 2], weights=[62.5, 37.5], k=1)[0]
            
            # Keep stringing until we reach target
            stringed_events = []
            all_combos = []
            all_stats = []
            
            while True:
                combo = tracker.get_next_combination()
                events, file_names, stats = string_parts(
                    subfolder_files, combo, rng, 
                    is_raw=is_raw, 
                    multiplier=mult
                )
                
                if not events:
                    break
                
                # Check if adding would exceed target significantly
                current_duration = stringed_events[-1]['Time'] if stringed_events else 0
                new_duration = events[-1]['Time'] if events else 0
                potential_total = current_duration + new_duration
                
                # ±5% margin
                margin = int(target_ms * 0.05)
                if potential_total > target_ms + margin and stringed_events:
                    # Close enough, stop
                    break
                
                # Add this string to the total
                offset = current_duration
                for e in events:
                    new_event = {**e}
                    new_event['Time'] = e['Time'] + offset
                    stringed_events.append(new_event)
                
                all_combos.append((combo, file_names))
                all_stats.append(stats)
                
                # Safety limit
                if len(all_combos) > 50:
                    break
            
            if not stringed_events:
                continue
            
            # Calculate total duration
            total_duration = stringed_events[-1]['Time']
            total_min = int(total_duration / 60000)
            total_sec = int((total_duration % 60000) / 1000)
            
            # File prefix and name
            prefix = "^" if is_raw else ""
            v_code = f"{folder_number}_{v_letter}"
            fname = f"{prefix}{v_code}_{total_min}m{total_sec}s.json"
            
            # Save file
            (out_folder / fname).write_text(json.dumps(stringed_events, indent=2))
            
            # Aggregate stats
            total_jitter = sum(s['total_jitter_count'] for s in all_stats)
            total_moves = sum(s['total_moves'] for s in all_stats)
            jitter_pct = (all_stats[-1]['jitter_percentage'] * 100) if all_stats else 0
            total_intra = sum(s['total_intra_pauses'] for s in all_stats)
            total_inter = sum(s['total_inter_pauses'] for s in all_stats)
            total_idle = sum(s['total_idle_movements'] for s in all_stats)
            
            # Add to manifest
            separator = "=" * 40
            version_label = f"Version {prefix}{v_code}_{total_min}m{total_sec}s:"
            
            if is_raw:
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Raw (no intra-part pauses, no chat)",
                    f"  Inter-part pauses: {format_ms_precise(total_inter)} (x{mult} Multiplier)",
                    f"  Idle Mouse Movements: {format_ms_precise(total_idle)}",
                    f"  Mouse Jitter: {int(jitter_pct)}%",
                    ""
                ]
            else:
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Normal",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_intra + total_inter)} (x{mult} Multiplier)",
                    f"BREAKDOWN",
                    f"  - Within parts pauses: {format_ms_precise(total_intra)}",
                    f"  - Between parts pauses: {format_ms_precise(total_inter)}",
                    f"  Idle Mouse Movements: {format_ms_precise(total_idle)}",
                    f"  Mouse Jitter: {int(jitter_pct)}%",
                    ""
                ]
            
            # Add file list
            for combo, file_names in all_combos:
                for folder_num, file_path in combo:
                    manifest_entry.append(f"  F{folder_num}* {file_path.name}")
            
            manifest_lines.extend(manifest_entry)
        
        # Write manifest
        manifest_path = out_folder / f"!_MANIFEST_{folder_number}_!.txt"
        manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"\n  📋 Manifest written: {manifest_path.name}")
    
    print("\n" + "="*70)
    print(f"✅ STRING MACROS COMPLETE - Bundle {args.bundle_id}")
    print(f"📦 Output: {bundle_dir}")
    print("="*70)

if __name__ == "__main__":
    main()
