#!/usr/bin/env python3
"""
string_macros.py - v3.8.5 - Bundle-Level Combination File
- NEW: ONE combination file per bundle at root level (lists ALL folders)
- NEW: Optional folders: 40-60% random chance (not fixed 38%)
- "Always first/last" files supported
- Manual history: YOU upload files to input_macros/combination_history/
"""

import argparse, json, random, re, sys, os, math, shutil, itertools
from pathlib import Path

VERSION = "v3.9.4"

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
    SMART JITTER SYSTEM v3.9.0
    
    Add realistic micro-movements to 21-32% of TOTAL file movements.
    CRITICAL: NO jitter within 1 second before/after ANY click!
    
    Rules:
    1. Jitter percentage: 21-32% of total MouseMove events
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
    
    # Step 3: Calculate how many jitters to add (21-32% of TOTAL movements)
    jitter_percentage = rng.uniform(0.21, 0.32)
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



def insert_massive_pause(events: list, rng: random.Random) -> tuple:
    """
    Insert one massive pause (4-9 minutes) at random point.
    For INEFFICIENT files only.
    Returns (events_with_pause, pause_duration_ms, split_index)
    """
    if not events or len(events) < 2:
        return events, 0, 0
    
    # Generate massive pause: 4-9 minutes (240000-540000ms)
    pause_duration = rng.randint(240000, 540000)
    
    # Pick random split point
    split_index = rng.randint(0, len(events) - 2)
    
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
        (cycle_events, file_info_list, has_dmwm)
        file_info_list: [(folder_num, filename, is_dmwm, end_time_within_cycle), ...]
        has_dmwm: True if any dmwm file in cycle
    """
    
    def add_file_to_cycle(file_path, folder_num, is_dmwm, file_label):
        """Helper to add a file to the cycle"""
        nonlocal timeline, cycle_events, file_info_list, has_dmwm
        
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
        
        # PRE-FILE PAUSE: 0.8-1.5 seconds BEFORE file plays
        # This prevents drag issues when previous file ended with a click!
        if cycle_events:
            # Random pause: 800-1500ms (calculated to millisecond precision)
            pre_file_pause = int(rng.uniform(800.0, 1500.0))
            timeline += pre_file_pause
            
            # NOW do cursor transition (AFTER pause, so click has time to release)
            # Get last position
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
            
            # ADDITIONAL pause after pre-file pause: 0.5-1 second
            post_pause_delay = int(rng.uniform(500.0, 1000.0))
            timeline += post_pause_delay
            
            # Transition duration: 200-400ms (for actual cursor movement)
            transition_duration = int(rng.uniform(200, 400))
            
            # Add smooth transition AFTER both pauses
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
    
    return cycle_events, file_info_list, has_dmwm


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
    
    Accepts: "1", "part1", "step2", "3-action", "3 optional- walk", etc.
    Returns tuple: (numbered_folders_dict, dmwm_file_set, non_json_files_list)
    
    numbered_folders: {num: {'files': [...], 'is_optional': bool}}
    dmwm_file_set: set of files from "dont mess with me"
    non_json_files: [list of non-JSON files to copy]
    """
    base = Path(base_path)
    numbered_folders = {}
    unmodified_files = []
    non_json_files = []
    
    for item in base.iterdir():
        if not item.is_dir():
            # Collect non-JSON files in root
            if not item.name.endswith('.json'):
                non_json_files.append(item)
            continue
        
        # Check for "dont mess with me" folder (case-insensitive)
        if item.name.lower() == 'dont mess with me':
            # Add all JSON files from this folder as unmodified
            dmwm_files = sorted(item.glob("*.json"))
            unmodified_files.extend(dmwm_files)
            print(f"  ⚠️  Found 'dont mess with me' folder: {len(dmwm_files)} unmodified files")
            continue
        
        # Extract number from folder name using regex
        match = re.search(r'\d+', item.name)
        if match:
            folder_num = int(match.group())
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
            
            # Check if folder is "optional" (27-43% random chance to include)
            is_optional = 'optional' in item.name.lower()
            optional_chance = random.uniform(0.27, 0.43) if is_optional else None
            
            if regular_files:  # Must have at least one regular file
                numbered_folders[folder_num] = {
                    'files': regular_files,
                    'is_optional': is_optional,
                    'optional_chance': optional_chance,
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
        """Get next unused combination"""
        max_attempts = 500
        
        for _ in range(max_attempts):
            # Pick random combination
            combination = []
            for folder_num in sorted(self.subfolder_files.keys()):
                folder_data = self.subfolder_files[folder_num]
                
                # Optional folder check (uses random 40-60% chance stored per folder)
                if folder_data.get('is_optional', False):
                    optional_chance = folder_data.get('optional_chance', 0.50)
                    if self.rng.random() >= optional_chance:
                        continue
                
                # Pick random file
                files = folder_data['files']
                if files:
                    chosen_file = self.rng.choice(files)
                    combination.append((folder_num, chosen_file))
            
            if not combination:
                continue
            
            # Create signature
            signature = "|".join(f"F{fn}={f.name}" for fn, f in combination)
            
            # Check if unused
            if signature not in self.used_combinations:
                self.used_combinations.add(signature)  # Mark as used
                return combination
        
        # Fallback: return random (may repeat)
        print(f"  ⚠️  Using random combination (may repeat)")
        combination = []
        for folder_num in sorted(self.subfolder_files.keys()):
            folder_data = self.subfolder_files[folder_num]
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
            f"Subfolders: {sorted(subfolder_files.keys())}",
            ""
        ]
        
        # Version loop: 3 Raw + 3 Inef + 6 Normal = 12 total
        version_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
        num_raw = 3
        num_inef = 3
        num_normal = 6
        
        for v_idx in range(min(args.versions, 12)):
            v_letter = version_letters[v_idx]
            
            # Determine file type
            is_raw = (v_idx < num_raw)
            is_inef = (num_raw <= v_idx < num_raw + num_inef)
            is_normal = (v_idx >= num_raw + num_inef)
            
            # Set multiplier
            if is_raw:
                mult = rng.choices([1, 2, 3], weights=[50, 30, 20], k=1)[0]
            elif is_inef:
                mult = rng.choices([2, 3], weights=[50, 50], k=1)[0]
            else:  # normal
                mult = rng.choices([1, 2], weights=[62.5, 37.5], k=1)[0]
            
            # Build cycles until target reached
            stringed_events = []
            all_file_info_with_times = []  # List of (folder_num, filename, is_dmwm, end_time) tuples
            total_intra = 0
            total_inter = 0
            total_idle = 0
            total_normal_pauses = 0
            massive_pause_ms = 0
            jitter_pct = 0
            
            while True:
                combo = tracker.get_next_combination()
                if not combo:
                    break
                
                # Track this combination signature
                combo_signature = "|".join(f"F{fn}={f.name}" for fn, f in combo)
                folder_combinations_used.append(combo_signature)
                
                # BUILD CYCLE (F1 → F2 → F3) WITHOUT features
                cycle_events, file_info, has_dmwm = string_cycle(
                    subfolder_files, combo, rng, dmwm_file_set
                )
                
                if not cycle_events:
                    break
                
                # APPLY FEATURES to ENTIRE cycle
                cycle_with_features, stats = apply_cycle_features(
                    cycle_events, rng, is_raw, has_dmwm
                )
                
                # Check if adding would exceed target
                current_duration = stringed_events[-1]['Time'] if stringed_events else 0
                cycle_duration = cycle_with_features[-1]['Time'] if cycle_with_features else 0
                
                # Add inter-cycle pause
                inter_cycle_pause = 0
                if stringed_events:
                    inter_cycle_pause = int(rng.uniform(500.123, 4999.987) * mult)
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
                
                if len(all_file_info_with_times) > 150:  # Safety limit
                    break
            
            if not stringed_events:
                continue
            
            # Add massive pause for INEFFICIENT
            if is_inef and len(stringed_events) > 1:
                stringed_events, massive_pause_ms, split_idx = insert_massive_pause(stringed_events, rng)
                
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
            
            # Build manifest entry
            separator = "=" * 40
            version_label = f"Version {prefix}{v_code}_{total_min}m{total_sec}s:"
            
            if is_raw:
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Raw (no time-adding features, no chat)",
                    f"  Between files pause: {format_ms_precise(total_inter)} (x{mult} Multiplier)",
                    f"Idle Mouse Movements: {format_ms_precise(total_idle)}",
                    f"Mouse Jitter: {int(jitter_pct * 100)}%",
                    ""
                ]
            elif is_inef:
                total_pause = total_intra + total_inter
                original_intra = total_intra
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Inefficient",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                    f"BREAKDOWN",
                    f"total before    - Within original files pauses: {format_ms_precise(original_intra)}",
                    f"multiplier      - Between original files pauses: {format_ms_precise(original_inter)}",
                    f"                - Normal file pause: {format_ms_precise(total_normal_pauses)}",
                    f"Idle Mouse Movements: {format_ms_precise(total_idle)}",
                    f"Mouse Jitter: {int(jitter_pct * 100)}%",
                    ""
                ]
                if massive_pause_ms > 0:
                    manifest_entry.insert(-2, f"Massive P1: {format_ms_precise(massive_pause_ms)}")
            else:  # normal
                total_pause = total_intra + total_inter
                original_intra = total_intra
                original_inter = int(total_inter / mult) if mult > 0 else total_inter
                
                manifest_entry = [
                    separator,
                    "",
                    version_label,
                    f"FILE TYPE: Normal",
                    f"  Total PAUSE ADDED: {format_ms_precise(total_pause)} (x{mult} Multiplier)",
                    f"BREAKDOWN",
                    f"total before    - Within original files pauses: {format_ms_precise(original_intra)}",
                    f"multiplier      - Between original files pauses: {format_ms_precise(original_inter)}",
                    f"                - Normal file pause: {format_ms_precise(total_normal_pauses)}",
                    f"Idle Mouse Movements: {format_ms_precise(total_idle)}",
                    f"Mouse Jitter: {int(jitter_pct * 100)}%",
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
