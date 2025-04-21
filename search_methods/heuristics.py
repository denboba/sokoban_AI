import numpy as np
from scipy.optimize import linear_sum_assignment
from sokoban.moves import *
from typing import List, Tuple, Set


def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """Manhattan distance between two points"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def path_exists(start: Tuple[int, int], end: Tuple[int, int], obstacles: Set[Tuple[int, int]],
                max_depth: int = 20) -> bool:
    """check if there exists a path between start and end points avoiding obstacles"""
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


def min_matching_distance(boxes: List[Tuple[int, int]], targets: List[Tuple[int, int]]) -> float:
    """Minimum cost matching using the Hungarian algorithm for optimal box-target matching"""
    if not boxes or not targets:
        return 0.0
    cost_matrix = np.array([[manhattan_distance(box, target) for target in targets] for box in boxes])
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return cost_matrix[row_ind, col_ind].sum()


def deadlock_heuristic(state) -> float:
    """
    heuristic to detect potential deadlocks in the current state.
    """
    penalty = 0
    obstacles = state.obstacles
    box_positions = state.positions_of_boxes
    targets = state.targets

    # Set for faster lookup
    obstacle_set = set(obstacles) if not isinstance(obstacles, set) else obstacles
    target_set = set(targets) if not isinstance(targets, set) else targets
    box_set = set(box_positions) if not isinstance(box_positions, set) else box_positions

    for (box_x, box_y) in box_positions:
        # Skip if the box is on target it is not a deadlock
        if (box_x, box_y) in target_set:
            continue
        # check for immediate neighbors
        left = (box_x, box_y - 1)
        right = (box_x, box_y + 1)
        up = (box_x + 1, box_y)
        down = (box_x - 1, box_y)

        # Check for second neighbors (2 steps away)
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
    optimized Sokoban heuristic with reduced computation and smart caching
    """
    # Get current state information
    box_positions = list(state.positions_of_boxes.keys())
    targets = state.targets
    obstacles = set(state.obstacles)
    player_pos = (state.player.x, state.player.y)

    # Precompute distances and path checks
    cost_matrix = np.zeros((len(box_positions), len(targets)))
    path_penalties = np.zeros((len(box_positions), len(targets)))
    corner_penalties = np.zeros((len(box_positions), len(targets)))

    # Precompute deadlock penalties
    obstacle_set = set(obstacles)
    target_set = set(targets)

    # Cache for paths between boxes and targets to avoid recalculating
    path_cache = {}

    for i, box_pos in enumerate(box_positions):
        x, y = box_pos
        # Check if box is in a corner
        adjacent_obstacles = sum(1 for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                                 if (x + dx, y + dy) in obstacle_set)
        is_corner = adjacent_obstacles >= 2

        for j, target in enumerate(targets):
            # Base distance using Manhattan distance
            base_dist = manhattan_distance(box_pos, target)
            cost_matrix[i, j] = base_dist

            # Path check (cache results to avoid redundant calculations)
            if (box_pos, target) not in path_cache:
                path_cache[(box_pos, target)] = path_exists(box_pos, target, obstacle_set, max_depth=80)

            if not path_cache[(box_pos, target)]:
                path_penalties[i, j] += base_dist * 0.5  # Apply penalty if no path exists

            # Corner penalty if box is in a corner and not on target
            if is_corner and box_pos != target:
                corner_penalties[i, j] = base_dist * 1.0

    # Apply all penalties to the cost matrix
    cost_matrix += path_penalties + corner_penalties

    # Optimal matching using Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    total_distance = cost_matrix[row_ind, col_ind].sum() * 1.5

    # Enhanced player positioning cost: Minimize distance to the nearest box
    boxes_not_on_target = [box for box in box_positions if box not in targets]
    if boxes_not_on_target:
        nearest_box_dist = min(manhattan_distance(player_pos, box) for box in boxes_not_on_target)
        avg_box_dist = np.mean([manhattan_distance(player_pos, box) for box in boxes_not_on_target])
        total_distance += nearest_box_dist * 0.8 + avg_box_dist * 0.4

    # Deadlock analysis
    deadlock_penalty = deadlock_heuristic(state)
    if deadlock_penalty > 0:
        boxes_on_target = sum(1 for box in box_positions if box in targets)
        progress = boxes_on_target / len(targets)
        base_scale = (1 - progress) * 0.2
        difficulty_scale = len(targets) / 4
        total_distance += deadlock_penalty * base_scale * difficulty_scale

    # Additional penalty for adjacent boxes not on targets
    for box1 in box_positions:
        for box2 in box_positions:
            if box1 != box2 and manhattan_distance(box1, box2) == 1:
                if box1 not in targets or box2 not in targets:
                    total_distance += 5  # Penalty for adjacent boxes not on targets

    # Movement efficiency: Penalize complex box movements
    possible_moves = state.filter_possible_moves()
    box_moves = sum(1 for m in possible_moves if m >= BOX_LEFT)
    total_distance += box_moves * 0.3

    return total_distance
