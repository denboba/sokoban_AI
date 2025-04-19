from typing import List, Tuple, Dict, Set
from scipy.optimize import linear_sum_assignment
import numpy as np
from sokoban.moves import *


def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """Calculate Manhattan distance between two points"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def path_exists(start: Tuple[int, int], end: Tuple[int, int], obstacles: Set[Tuple[int, int]],
                max_depth: int = 20) -> bool:
    """Check if there exists a path between start and end points avoiding obstacles"""
    if start == end:
        return True

    queue = [(start, 0)]
    visited = {start}

    while queue and queue[0][1] < max_depth:
        pos, depth = queue.pop(0)
        x, y = pos

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            next_pos = (x + dx, y + dy)
            if next_pos == end:
                return True
            if next_pos not in obstacles and next_pos not in visited:
                queue.append((next_pos, depth + 1))
                visited.add(next_pos)

    return False


def min_matching_distance(boxes: List[Tuple[int, int]],
                          targets: List[Tuple[int, int]]) -> float:
    """
    Optimized minimum matching distance using Hungarian algorithm.
    O(n³) time but provides optimal matching.
    """
    if not boxes or not targets:
        return 0.0

    # Create cost matrix
    cost_matrix = [[manhattan_distance(box, target) for target in targets]
                   for box in boxes]

    # Get optimal assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    return sum(cost_matrix[i][j] for i, j in zip(row_ind, col_ind))


def box_to_player_distance(state) -> float:
    """
    Optimized player-to-box distance calculation.
    Uses direct dictionary access instead of values() iteration.
    """
    player_pos = (state.player.x, state.player.y)
    min_dist = float('inf')

    # Directly iterate through positions to avoid Box object lookups
    for (box_x, box_y) in state.positions_of_boxes:
        dist = abs(player_pos[0] - box_x) + abs(player_pos[1] - box_y)
        if dist < min_dist:
            min_dist = dist
            if min_dist == 0:  # Early exit if we find adjacent box
                break

    return min_dist


def deadlock_heuristic(state) -> float:
    """
    Optimized deadlock detection with:
    - Early termination checks
    - Cached position lookups
    - More efficient neighbor checking
    """
    penalty = 0
    obstacles = state.obstacles
    box_positions = state.positions_of_boxes
    targets = state.targets

    # Convert to sets for faster membership testing
    obstacle_set = set(obstacles) if not isinstance(obstacles, set) else obstacles
    target_set = set(targets) if not isinstance(targets, set) else targets
    box_set = set(box_positions)

    for (box_x, box_y) in box_positions:
        # Skip if box is on target
        if (box_x, box_y) in target_set:
            continue

        # Check for immediate neighbors
        left = (box_x, box_y - 1)
        right = (box_x, box_y + 1)
        up = (box_x + 1, box_y)
        down = (box_x - 1, box_y)

        # Check for extended neighbors (2 steps away)
        left2 = (box_x, box_y - 2)
        right2 = (box_x, box_y + 2)
        up2 = (box_x + 2, box_y)
        down2 = (box_x - 2, box_y)

        # Check for diagonal neighbors
        up_left = (box_x + 1, box_y - 1)
        up_right = (box_x + 1, box_y + 1)
        down_left = (box_x - 1, box_y - 1)
        down_right = (box_x - 1, box_y + 1)

        # Basic blockage checks
        horizontal_blocked = ((left in obstacle_set or left in box_set) and
                              (right in obstacle_set or right in box_set))
        vertical_blocked = ((up in obstacle_set or up in box_set) and
                            (down in obstacle_set or down in box_set))

        # Extended path checks
        horizontal_path = not (left in obstacle_set and left2 in obstacle_set) and \
                          not (right in obstacle_set and right2 in obstacle_set)
        vertical_path = not (up in obstacle_set and up2 in obstacle_set) and \
                        not (down in obstacle_set and down2 in obstacle_set)

        # Diagonal escape routes
        diagonal_escape = not all(pos in obstacle_set or pos in box_set
                                  for pos in [up_left, up_right, down_left, down_right])

        # Calculate penalty
        if horizontal_blocked and vertical_blocked and not diagonal_escape:
            if not (horizontal_path or vertical_path):
                penalty += 1000  # Complete deadlock
            else:
                penalty += 500  # Potential escape route exists
        elif horizontal_blocked or vertical_blocked:
            if not diagonal_escape:
                penalty += 100  # Partial blockage without diagonal escape
            else:
                penalty += 50  # Partial blockage with diagonal escape

    return penalty


def sokoban_heuristic(state) -> float:
    """
    Enhanced heuristic with improved path analysis and dynamic weighting
    """
    # Get current state information
    box_positions = list(state.positions_of_boxes.keys())
    targets = state.targets
    obstacles = set(state.obstacles)
    player_pos = (state.player.x, state.player.y)

    # Calculate optimal box-target assignments
    cost_matrix = np.zeros((len(box_positions), len(targets)))
    path_penalties = np.zeros((len(box_positions), len(targets)))

    for i, box_pos in enumerate(box_positions):
        for j, target in enumerate(targets):
            base_dist = manhattan_distance(box_pos, target)
            cost_matrix[i, j] = base_dist

            # Check path viability
            other_boxes = set(p for p in box_positions if p != box_pos)
            blocked_cells = obstacles | other_boxes

            # Direct path check
            if not path_exists(box_pos, target, blocked_cells):
                path_penalties[i, j] += base_dist

            # Check push accessibility
            push_points = [
                (target[0] + dx, target[1] + dy)
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]
                if (target[0] + dx, target[1] + dy) not in blocked_cells
            ]
            if not any(path_exists(box_pos, pp, blocked_cells) for pp in push_points):
                path_penalties[i, j] += base_dist * 0.5

    # Apply penalties to cost matrix
    cost_matrix += path_penalties

    # Get optimal assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    total_distance = cost_matrix[row_ind, col_ind].sum() * 1.2

    # Player positioning cost
    boxes_not_on_target = [box for box in box_positions if box not in targets]
    if boxes_not_on_target:
        nearest_box_dist = min(manhattan_distance(player_pos, box) for box in boxes_not_on_target)
        total_distance += nearest_box_dist * 0.6

    # Deadlock analysis with progress-based scaling
    boxes_on_target = sum(1 for box in box_positions if box in targets)
    progress = boxes_on_target / len(targets)
    deadlock_penalty = deadlock_heuristic(state)

    if deadlock_penalty > 0:
        # Scale penalty based on progress and remaining boxes
        scale = (1 - progress) * 0.8
        total_distance += deadlock_penalty * scale

    # Movement efficiency
    possible_moves = state.filter_possible_moves()
    box_moves = sum(1 for m in possible_moves if m >= BOX_LEFT)
    total_distance += box_moves * 0.3  # Small penalty for complex box movements

    return total_distance


from typing import List, Dict, Optional, Set, Tuple
from .solver import Solver
from .heuristics import sokoban_heuristic, manhattan_distance
from sokoban.moves import *
from collections import defaultdict
import heapq


class LRTAStar(Solver):
    def __init__(self, max_iterations: int = 10000, max_visits: int = 3):
        """
        Optimized LRTA* solver with:
        - State visitation tracking
        - Priority queue for move selection
        - Efficient state representation
        """
        self.max_iterations = max_iterations
        self.max_visits = max_visits  # Max visits per state to prevent loops
        self.h_values: Dict[str, float] = {}  # Learning table
        self.visit_counts: Dict[str, int] = defaultdict(int)  # Track state visits

    def get_state_key(self, state) -> str:
        """Optimized state key generation using direct position access"""
        # Use frozenset for box positions since order doesn't matter
        box_positions = frozenset((box.x, box.y) for box in state.boxes.values())
        return f"{state.player.x},{state.player.y}|{hash(box_positions)}"

    def get_heuristic(self, state) -> float:
        """Cached heuristic lookup with fallback to sokoban_heuristic"""
        state_key = self.get_state_key(state)
        return self.h_values.get(state_key, sokoban_heuristic(state))

    def update_heuristic(self, state, value: float):
        """Update heuristic with max of current and new value"""
        state_key = self.get_state_key(state)
        self.h_values[state_key] = max(value, self.h_values.get(state_key, 0))

    def solve(self, initial_state) -> Optional[List[int]]:
        """Enhanced LRTA* implementation with adaptive exploration and smart backtracking"""
        current_state = initial_state
        path: List[int] = []
        iterations = 0
        visited_states: Set[str] = set()
        backtrack_count = 0
        last_progress = 0
        best_h_value = float('inf')
        best_state = None
        best_path = None
        plateau_count = 0
        adaptive_visits = self.max_visits

        while not current_state.is_solved() and iterations < self.max_iterations:
            iterations += 1
            current_key = self.get_state_key(current_state)
            current_h = self.get_heuristic(current_state)
            boxes_on_target = sum(1 for box in current_state.positions_of_boxes if box in current_state.targets)

            # Track best state seen so far
            if best_state is None or current_h < best_h_value:
                best_h_value = current_h
                best_state = current_state.copy()
                best_path = path.copy()
                last_progress = iterations
                plateau_count = 0
            else:
                plateau_count += 1

            # Adaptive visit limit based on progress
            if boxes_on_target > 0:
                adaptive_visits = self.max_visits * (1 + boxes_on_target / len(current_state.targets))

            # Smart backtracking when stuck
            if plateau_count > 100 or self.visit_counts[current_key] > adaptive_visits:
                if not path:
                    if best_path and len(best_path) > 0:
                        return best_path
                    return None

                # Determine backtrack depth based on progress
                if plateau_count > 200:
                    backtrack_depth = min(20, len(path))  # Deep backtrack
                    plateau_count = 0
                else:
                    backtrack_depth = min(5, len(path))  # Shallow backtrack

                # Remove moves and clear related states
                for _ in range(backtrack_depth):
                    if path:
                        old_key = self.get_state_key(current_state)
                        visited_states.discard(old_key)
                        self.visit_counts[old_key] = 0
                        path.pop()

                # Reset to backtrack point
                current_state = initial_state.copy()
                for move in path:
                    current_state.apply_move(move)
                continue

            # Get and evaluate possible moves
            possible_moves = current_state.filter_possible_moves()
            if not possible_moves:
                if best_path and len(best_path) > 0:
                    return best_path
                return None

            # Enhanced move evaluation
            move_queue = []
            for move in possible_moves:
                next_state = current_state.copy()
                try:
                    next_state.apply_move(move)
                except ValueError:
                    continue

                next_key = self.get_state_key(next_state)
                if next_key in visited_states:
                    continue

                # Dynamic move cost calculation
                g_cost = 2 if move >= BOX_LEFT else 1
                h_value = self.get_heuristic(next_state)
                visit_count = self.visit_counts[next_key]

                # Progressive visit penalty
                visit_penalty = 0.2 * visit_count * (1 + boxes_on_target / len(current_state.targets))

                # Calculate total cost with progress bonus
                f_value = g_cost + h_value + visit_penalty
                next_boxes_on_target = sum(1 for box in next_state.positions_of_boxes
                                           if box in next_state.targets)

                if next_boxes_on_target > boxes_on_target:
                    f_value -= 5  # Significant bonus for increasing boxes on target

                heapq.heappush(move_queue, (f_value, move, next_state))

            if not move_queue:
                visited_states.clear()
                continue

            # Select and apply best move
            _, best_move, best_next_state = heapq.heappop(move_queue)
            path.append(best_move)
            visited_states.add(current_key)
            self.visit_counts[current_key] += 1
            current_state = best_next_state

            # Periodic cleanup of old states
            if iterations % 30 == 0:
                # Keep only the most recent states
                if len(visited_states) > 1000:
                    recent_keys = set()
                    temp_state = initial_state.copy()
                    try:
                        # Keep states from recent moves
                        for move in path[-20:]:
                            temp_state.apply_move(move)
                            recent_keys.add(self.get_state_key(temp_state))
                        # Keep current state
                        recent_keys.add(current_key)
                        # Update visited states
                        visited_states.intersection_update(recent_keys)
                    except ValueError:
                        # If we hit an invalid move, just keep current state
                        visited_states = {current_key}

        return path if current_state.is_solved() else best_path