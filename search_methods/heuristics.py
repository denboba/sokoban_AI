from math import sqrt
from typing import List, Tuple
from sokoban.moves import *

def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """Calculate Manhattan distance between two points"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def min_matching_distance(boxes: List[Tuple[int, int]], targets: List[Tuple[int, int]]) -> float:
    """Calculate minimum sum of distances between boxes and targets using greedy matching"""
    total_distance = 0
    unmatched_targets = targets.copy()
    
    for box in boxes:
        if not unmatched_targets:
            break
            
        # Find closest target for this box
        min_dist = float('inf')
        best_target = None
        best_target_idx = None
        
        for i, target in enumerate(unmatched_targets):
            dist = manhattan_distance(box, target)
            if dist < min_dist:
                min_dist = dist
                best_target = target
                best_target_idx = i
                
        if best_target is not None:
            total_distance += min_dist
            unmatched_targets.pop(best_target_idx)
            
    return total_distance

def box_to_player_distance(state) -> float:
    """Calculate minimum distance from player to any box"""
    player_pos = (state.player.x, state.player.y)
    min_dist = float('inf')
    
    for box in state.boxes.values():
        dist = manhattan_distance(player_pos, (box.x, box.y))
        min_dist = min(min_dist, dist)
    
    return min_dist

def deadlock_heuristic(state) -> float:
    """Penalize states that might lead to deadlocks"""
    penalty = 0
    
    # Get box positions
    box_positions = [(box.x, box.y) for box in state.boxes.values()]
    
    for box_x, box_y in box_positions:
        # Skip if box is already on target
        if (box_x, box_y) in state.targets:
            continue
            
        # Check for corner deadlock
        horizontal_blocked = False
        vertical_blocked = False
        
        # Check horizontal walls/obstacles/boxes
        left_blocked = (box_x, box_y-1) in state.obstacles or (box_x, box_y-1) in state.positions_of_boxes
        right_blocked = (box_x, box_y+1) in state.obstacles or (box_x, box_y+1) in state.positions_of_boxes
        if left_blocked and right_blocked:
            horizontal_blocked = True
            
        # Check vertical walls/obstacles/boxes
        down_blocked = (box_x-1, box_y) in state.obstacles or (box_x-1, box_y) in state.positions_of_boxes
        up_blocked = (box_x+1, box_y) in state.obstacles or (box_x+1, box_y) in state.positions_of_boxes
        if up_blocked and down_blocked:
            vertical_blocked = True
            
        # Corner deadlock
        if horizontal_blocked and vertical_blocked:
            penalty += 1000
        # Partial blocking penalty
        elif horizontal_blocked or vertical_blocked:
            penalty += 100
                
    return penalty

def sokoban_heuristic(state) -> float:
    """Combined heuristic for Sokoban"""
    # Get current box positions
    box_positions = [(box.x, box.y) for box in state.boxes.values()]
    
    # Calculate minimum matching distance between boxes and targets
    distance_cost = min_matching_distance(box_positions, state.targets) * 2.0
    
    # Calculate player-to-box distance
    player_cost = box_to_player_distance(state)
    
    # Calculate deadlock penalty
    deadlock_cost = deadlock_heuristic(state) * 3.0
    
    # Add penalties for box moves and pull moves
    box_move_penalty = len([m for m in state.filter_possible_moves() if m >= BOX_LEFT]) * 2.0
    pull_penalty = state.undo_moves * 3.0
    
    return distance_cost + player_cost + deadlock_cost + box_move_penalty + pull_penalty
