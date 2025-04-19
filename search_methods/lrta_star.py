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
                    backtrack_depth = min(5, len(path))   # Shallow backtrack

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