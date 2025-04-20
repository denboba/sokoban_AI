from typing import List, Optional
from .solver import Solver
from .heuristics import sokoban_heuristic  # Now we're using this heuristic
import random
import math

class SimulatedAnnealing(Solver):
    def __init__(self,
                 initial_temp: float = 75.0,
                 cooling_rate: float = 0.995,
                 min_temp: float = 0.5,
                 max_iterations: int = 50000,
                 restart_temp: float = 30.0,
                 plateau_limit: int = 50):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations = max_iterations
        self.restart_temp = restart_temp
        self.plateau_limit = plateau_limit
        self.heuristic_cache = {}

    def acceptance_probability(self, old_cost: float, new_cost: float, temperature: float) -> float:
        return 1.0 if new_cost < old_cost else math.exp((old_cost - new_cost) / temperature)

    def get_state_key(self, state) -> str:
        box_positions = sorted((b.x, b.y) for b in state.boxes.values())
        return f"p{state.player.x},{state.player.y}|b{box_positions}"

    def solve(self, initial_state) -> Optional[List[int]]:
        current_state = initial_state
        current_path = []
        best_state = current_state
        best_path = []
        best_score = sokoban_heuristic(current_state)  # Use sokoban_heuristic here
        temperature = self.initial_temp
        iterations = 0
        last_improvement = 0
        visited_states = {}

        while iterations < self.max_iterations:
            iterations += 1
            possible_moves = current_state.filter_possible_moves()
            if not possible_moves:
                if best_path:
                    current_state, current_path = best_state, best_path[:]
                    continue
                return None

            sampled_moves = random.sample(possible_moves, min(5, len(possible_moves)))

            move_scores = []
            for move in sampled_moves:
                next_state = current_state.copy()
                next_state.apply_move(move)
                state_key = self.get_state_key(next_state)
                visits = visited_states.get(state_key, 0)
                if visits > 2:
                    continue
                score = (-10 if move >= 4 else 0) + visits * 5
                move_scores.append((move, next_state, state_key, score))

            if not move_scores:
                visited_states.clear()
                continue

            if random.random() < temperature / self.initial_temp:
                move, next_state, state_key, _ = random.choice(move_scores)
            else:
                move, next_state, state_key, _ = min(move_scores, key=lambda x: x[3])

            next_cost = sokoban_heuristic(next_state)  # Use sokoban_heuristic here

            if next_cost == 0 or next_state.is_solved():
                return current_path + [move]

            if next_cost < best_score:
                best_state, best_path, best_score = next_state, current_path + [move], next_cost
                last_improvement = iterations

            if iterations - last_improvement > self.plateau_limit:
                if random.random() < 0.5:
                    current_state, current_path = best_state, best_path[:]
                    temperature = self.restart_temp
                else:
                    for _ in range(random.randint(10, 15)):
                        moves = current_state.filter_possible_moves()
                        if not moves:
                            break
                        move = random.choice([m for m in moves if m >= 4] or moves)
                        current_state.apply_move(move)
                        current_path.append(move)
                    temperature = self.initial_temp
                visited_states.clear()
                last_improvement = iterations
                continue

            if random.random() < self.acceptance_probability(best_score, next_cost, temperature):
                current_state, current_path = next_state, current_path + [move]
                visited_states[state_key] = visited_states.get(state_key, 0) + 1

            temperature *= self.cooling_rate
            if temperature < self.min_temp:
                temperature = self.restart_temp

        return best_path if best_path else None
