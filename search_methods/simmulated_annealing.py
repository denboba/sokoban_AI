from typing import List, Optional, Set
from .solver import Solver
from .heuristics import sokoban_heuristic
from sokoban.moves import LEFT, RIGHT, UP, DOWN, BOX_LEFT, BOX_RIGHT, BOX_UP, BOX_DOWN
import random
import math


class SimulatedAnnealing(Solver):
    def __init__(self,
                 initial_temp: float = 100.0,
                 cooling_rate: float = 0.99,
                 min_temp: float = 0.1,
                 max_iterations: int = 100000,
                 restart_temp: float = 50.0,
                 plateau_limit: int = 100,
                 exploration_factor: float = 0.4):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations = max_iterations
        self.restart_temp = restart_temp
        self.plateau_limit = plateau_limit
        self.heuristic_cache = {}

    def quick_heuristic(self, state) -> float:
        """Faster heuristic that only considers Manhattan distance and target coverage"""
        cache_key = self.get_state_key(state)
        if cache_key in self.heuristic_cache:
            return self.heuristic_cache[cache_key]

        total_dist = 0
        boxes_on_target = 0
        for box in state.positions_of_boxes:
            min_dist = float('inf')
            is_on_target = False
            for target in state.targets:
                dist = abs(box[0] - target[0]) + abs(box[1] - target[1])
                min_dist = min(min_dist, dist)
                if box == target:
                    is_on_target = True
                    boxes_on_target += 1
            total_dist += min_dist

        # Heavy penalty for boxes not on targets
        score = total_dist + (len(state.boxes) - boxes_on_target) * 50
        self.heuristic_cache[cache_key] = score
        return score

    def acceptance_probability(self, old_cost: float, new_cost: float, temperature: float) -> float:
        """Calculate probability of accepting a worse solution"""
        if new_cost < old_cost:
            return 1.0
        return math.exp((old_cost - new_cost) / temperature)

    def get_state_key(self, state) -> str:
        """Create a unique key for a state"""
        box_positions = sorted((box.x, box.y) for box in state.boxes.values())
        return f"p{state.player.x},{state.player.y}|b{box_positions}"

    def solve(self, initial_state) -> Optional[List[int]]:
        """Optimized Simulated Annealing solver"""
        current_state = initial_state
        current_path = []
        best_state = current_state
        best_path = []
        best_score = sokoban_heuristic(current_state)
        temperature = self.initial_temp
        iterations = 0
        last_improvement = 0
        visited_states = {}

        while iterations < self.max_iterations:
            iterations += 1

            # Get possible moves from current state
            possible_moves = current_state.filter_possible_moves()
            if not possible_moves:
                if best_path:
                    current_state = best_state
                    current_path = best_path[:]
                    continue
                return None

            # Quick evaluation of moves
            move_scores = []
            for move in possible_moves:
                next_state = current_state.copy()
                next_state.apply_move(move)
                state_key = self.get_state_key(next_state)
                
                # Skip if we've seen this state too many times
                visits = visited_states.get(state_key, 0)
                if visits > 2:
                    continue

                # Prefer box moves and states we haven't seen
                is_box_move = move >= 4
                score = -10 if is_box_move else 0
                score += visits * 5  # Penalty for revisiting states
                move_scores.append((move, next_state, state_key, score))

            if not move_scores:
                visited_states.clear()
                continue

            # Select move based on temperature
            if random.random() < temperature / self.initial_temp:
                # High temperature: More random selection
                move, next_state, state_key, _ = random.choice(move_scores)
            else:
                # Low temperature: Prefer promising moves
                move_scores.sort(key=lambda x: x[3])
                move, next_state, state_key, _ = move_scores[0]

            # Check if solved
            if next_state.is_solved():
                return current_path + [move]

            # Evaluate new state
            next_cost = sokoban_heuristic(next_state)

            # Update best solution
            if next_cost < best_score:
                best_state = next_state
                best_path = current_path + [move]
                best_score = next_cost
                last_improvement = iterations

            # Check for plateau
            if iterations - last_improvement > self.plateau_limit:
                if random.random() < 0.5:
                    # Try continuing from best state with high temperature
                    current_state = best_state
                    current_path = best_path[:]
                    temperature = self.restart_temp
                else:
                    # Aggressive random walk
                    for _ in range(random.randint(10, 20)):
                        moves = current_state.filter_possible_moves()
                        if moves:
                            box_moves = [m for m in moves if m >= 4]
                            if box_moves and random.random() < 0.7:
                                move = random.choice(box_moves)
                            else:
                                move = random.choice(moves)
                            current_state.apply_move(move)
                            current_path.append(move)
                    temperature = self.initial_temp

                visited_states.clear()
                last_improvement = iterations
                continue

            # Apply acceptance probability
            if random.random() < self.acceptance_probability(best_score, next_cost, temperature):
                current_state = next_state
                current_path.append(move)
                visited_states[state_key] = visited_states.get(state_key, 0) + 1

            # Cool down temperature
            temperature *= self.cooling_rate
            if temperature < self.min_temp:
                temperature = self.restart_temp

        # Return best solution found if no solution was reached
        return best_path if best_path else None