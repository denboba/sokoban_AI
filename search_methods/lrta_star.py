from typing import List, Dict, Optional, Set
from search_methods.solver import Solver
from search_methods.heuristics import sokoban_heuristic
from sokoban.moves import *
from collections import defaultdict
import heapq

class LRTAStar(Solver):
    def __init__(self, max_iterations: int = 100000, max_visits: int = 8):
        self.max_iterations = max_iterations
        self.max_visits = max_visits
        self.h_values: Dict[str, float] = {}
        self.visit_counts: Dict[str, int] = defaultdict(int)
        self.states_explored = 0

    def get_state_key(self, state) -> str:
        box_positions = frozenset((box.x, box.y) for box in state.boxes.values())
        return f"{state.player.x},{state.player.y}|{hash(box_positions)}"

    def get_heuristic(self, state) -> float:
        key = self.get_state_key(state)
        if key not in self.h_values:
            self.h_values[key] = sokoban_heuristic(state)
        return self.h_values[key]

    def update_heuristic(self, state, value: float):
        key = self.get_state_key(state)
        self.h_values[key] = max(value, self.h_values.get(key, 0))

    def verify_solution(self, initial_state, moves: List[int]) -> bool:
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
        current_state = initial_state
        path: List[int] = []
        best_path = None
        best_h_value = float('inf')
        iterations = 0
        plateau_count = 0
        visited_states: Set[str] = set()

        while not current_state.is_solved() and iterations < self.max_iterations:
            iterations += 1
            key = self.get_state_key(current_state)
            h = self.get_heuristic(current_state)
            boxes_on_target = sum(1 for box in current_state.positions_of_boxes if box in current_state.targets)
            progress_ratio = boxes_on_target / len(current_state.targets)

            if boxes_on_target > 0 and h < best_h_value:
                best_h_value = h
                best_path = path.copy()
                plateau_count = 0
            else:
                plateau_count += 1

            adaptive_visits = self.max_visits * (2 + progress_ratio * 4 + len(current_state.targets) / 3)
            if progress_ratio > 0.7:
                adaptive_visits *= 2.5
            elif progress_ratio > 0.5:
                adaptive_visits *= 1.8
            elif boxes_on_target == 0:
                adaptive_visits *= 0.7

            if iterations > self.max_iterations * 0.7:
                adaptive_visits *= 0.5

            if plateau_count > 40 or self.visit_counts[key] > adaptive_visits:
                if not path:
                    return best_path if best_path and self.verify_solution(initial_state, best_path) else None
                backtrack_depth = min(max(int(len(path) * 0.2), 5), 25)
                for _ in range(backtrack_depth):
                    if path:
                        old_key = self.get_state_key(current_state)
                        visited_states.discard(old_key)
                        self.visit_counts[old_key] = 0
                        path.pop()
                current_state = initial_state.copy()
                for move in path:
                    current_state.apply_move(move)
                plateau_count = 0
                continue

            move_queue = []
            for move in current_state.filter_possible_moves():
                next_state = current_state.copy()
                try:
                    next_state.apply_move(move)
                except ValueError:
                    continue
                next_key = self.get_state_key(next_state)
                if next_key in visited_states:
                    continue
                base_cost = 2 if move >= BOX_LEFT else 1
                h_next = self.get_heuristic(next_state)
                visit_penalty = 0.3 * self.visit_counts[next_key] * (1.5 if iterations > self.max_iterations * 0.5 else 1)
                delta_target = sum(1 for b in next_state.positions_of_boxes if b in next_state.targets) - boxes_on_target
                priority = base_cost + h_next + visit_penalty - 8 * delta_target if delta_target > 0 else base_cost + h_next + visit_penalty + 10 * abs(delta_target)
                priority -= len(next_state.filter_possible_moves()) * 0.2
                if move >= BOX_LEFT:
                    moved_box = next((p for p in next_state.positions_of_boxes if p not in current_state.positions_of_boxes), None)
                    if moved_box:
                        x, y = moved_box
                        if sum((x + dx, y + dy) in next_state.obstacles for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]) >= 2 and moved_box not in next_state.targets:
                            priority += 5
                heapq.heappush(move_queue, (priority, move, next_state))

            if not move_queue:
                visited_states.clear()
                continue

            _, chosen_move, next_state = heapq.heappop(move_queue)
            path.append(chosen_move)
            visited_states.add(key)
            self.visit_counts[key] += 1
            current_state = next_state
            self.states_explored += 1

            if iterations % 30 == 0 and len(visited_states) > 1000:
                try:
                    temp_state = initial_state.copy()
                    recent_keys = set()
                    for move in path[-20:]:
                        temp_state.apply_move(move)
                        recent_keys.add(self.get_state_key(temp_state))
                    visited_states.intersection_update(recent_keys)
                except ValueError:
                    visited_states = {key}

        if current_state.is_solved() and self.verify_solution(initial_state, path):
            return path
        if best_path and self.verify_solution(initial_state, best_path):
            return best_path
        return None
