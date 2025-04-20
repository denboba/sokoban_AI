from typing import List, Dict, Optional, Set, Tuple
from .solver import Solver
from .heuristics import sokoban_heuristic, manhattan_distance
from sokoban.moves import *
from collections import defaultdict
import heapq

class LRTAStar(Solver):
    def __init__(self, max_iterations: int = 100000, max_visits: int = 8):
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
        self.states_explored = 0

    def get_state_key(self, state) -> str:
        """Optimized state key generation using direct position access"""
        # Use frozenset for box positions since order doesn't matter
        box_positions = frozenset((box.x, box.y) for box in state.boxes.values())
        return f"{state.player.x},{state.player.y}|{hash(box_positions)}"

    def get_heuristic(self, state) -> float:
        """Enhanced heuristic with dynamic caching and state analysis"""
        state_key = self.get_state_key(state)
        if state_key in self.h_values:
            return self.h_values[state_key]
        
        # Get base heuristic
        h_value = sokoban_heuristic(state)
        
        # Cache and return
        self.h_values[state_key] = h_value
        return h_value

    def update_heuristic(self, state, value: float):
        """Update heuristic with max of current and new value"""
        state_key = self.get_state_key(state)
        self.h_values[state_key] = max(value, self.h_values.get(state_key, 0))

    def verify_solution(self, initial_state, moves: List[int]) -> bool:
        """Verify that applying the moves to initial_state leads to a solved state"""
        if not moves:
            return False
        
        state = initial_state.copy()
        try:
            for move in moves:
                state.apply_move(move)
            return state.is_solved()
        except ValueError:
            return False

    def solve(self, initial_state) -> Optional[List[int]]:
        """Enhanced LRTA* implementation with adaptive exploration and smart backtracking"""
        current_state = initial_state
        path: List[int] = []
        self.states_explored = 0
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
            boxes_on_target = sum(1 for box in current_state.positions_of_boxes if box in current_state.targets)
            if boxes_on_target > 0 and current_h < best_h_value:
                best_h_value = current_h
                best_state = current_state.copy()
                best_path = path.copy()
                last_progress = iterations
                plateau_count = 0
            else:
                plateau_count += 1

            # Dynamic visit limit based on state analysis
            progress_ratio = boxes_on_target / len(current_state.targets)
            base_visits = self.max_visits
            
            # Scale visits based on progress and puzzle difficulty
            if boxes_on_target > 0:
                # More visits allowed as we make progress
                progress_bonus = progress_ratio * 4
                # Extra visits for harder puzzles
                difficulty_bonus = len(current_state.targets) / 3
                adaptive_visits = base_visits * (2 + progress_bonus + difficulty_bonus)
                
                # Significant boost when we're close to solution
                if progress_ratio > 0.7:
                    adaptive_visits *= 2.5
                elif progress_ratio > 0.5:
                    adaptive_visits *= 1.8
            else:
                # Encourage exploration when stuck
                adaptive_visits = base_visits * 0.7
                
            # Adjust for search phase
            if iterations > self.max_iterations * 0.7:
                # More aggressive in later stages
                adaptive_visits *= 0.5

            # Advanced backtracking with state analysis
            if plateau_count > 40 or self.visit_counts[current_key] > adaptive_visits:
                if not path:
                    if best_path and self.verify_solution(initial_state, best_path):
                        return best_path
                    return None

                # Dynamic backtracking based on multiple factors
                if plateau_count > 80:
                    # Deep backtrack for long plateaus
                    backtrack_ratio = 0.5
                    max_depth = 40
                elif boxes_on_target == 0:
                    # Aggressive backtrack when stuck
                    backtrack_ratio = 0.4
                    max_depth = 30
                elif progress_ratio < 0.3:
                    # Medium backtrack for low progress
                    backtrack_ratio = 0.3
                    max_depth = 25
                else:
                    # Shallow backtrack with good progress
                    backtrack_ratio = 0.2
                    max_depth = 15
                
                # Scale backtrack depth with path length and difficulty
                path_length = len(path)
                difficulty_factor = len(current_state.targets) / 4
                backtrack_depth = min(int(path_length * backtrack_ratio * (1 + difficulty_factor * 0.2)), max_depth)
                
                # Ensure minimum backtrack
                backtrack_depth = max(backtrack_depth, 5)
                
                # Reset plateau count
                plateau_count = 0

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
                if best_path and self.verify_solution(initial_state, best_path):
                    return best_path
                return None

            # Enhanced move evaluation with look-ahead
            move_queue = []
            current_boxes_on_target = boxes_on_target
            
            for move in possible_moves:
                next_state = current_state.copy()
                try:
                    next_state.apply_move(move)
                except ValueError:
                    continue

                next_key = self.get_state_key(next_state)
                if next_key in visited_states:
                    continue

                # Sophisticated move cost calculation
                base_cost = 2 if move >= BOX_LEFT else 1
                h_value = self.get_heuristic(next_state)
                visit_count = self.visit_counts[next_key]
                
                # Calculate progress metrics
                next_boxes_on_target = sum(1 for box in next_state.positions_of_boxes 
                                          if box in next_state.targets)
                progress_delta = next_boxes_on_target - current_boxes_on_target
                
                # Dynamic visit penalty based on search phase
                visit_penalty = 0.3 * visit_count
                if iterations > self.max_iterations * 0.5:
                    visit_penalty *= 1.5  # Increase penalty in later stages
                
                # Calculate move priority
                move_priority = base_cost + h_value + visit_penalty
                
                # Apply bonuses and penalties
                if progress_delta > 0:
                    # Major bonus for increasing boxes on target
                    move_priority -= 8 * progress_delta
                elif progress_delta < 0:
                    # Major penalty for decreasing boxes on target
                    move_priority += 10 * abs(progress_delta)
                
                # Look-ahead bonus
                next_moves = next_state.filter_possible_moves()
                if next_moves:
                    move_priority -= len(next_moves) * 0.2  # Bonus for states with more options
                
                # Bonus for moves that keep boxes away from corners
                if move >= BOX_LEFT:
                    box_pos = None
                    for pos in next_state.positions_of_boxes:
                        if pos not in current_state.positions_of_boxes:
                            box_pos = pos
                            break
                    if box_pos:
                        x, y = box_pos
                        corner_count = sum(1 for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]
                                         if (x+dx, y+dy) in next_state.obstacles)
                        if corner_count >= 2 and box_pos not in next_state.targets:
                            move_priority += 5  # Penalty for moving box to corner

                heapq.heappush(move_queue, (move_priority, move, next_state))

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

            self.states_explored += 1

        # Return the current path if it leads to a solved state
        if current_state.is_solved() and self.verify_solution(initial_state, path):
            return path

        # If current path doesn't work, try the best path we found
        if best_path and self.verify_solution(initial_state, best_path):
            return best_path

        return None