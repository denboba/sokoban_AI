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
        self.restart_temp = restart_temp  # Temperature to restart from when stuck
        self.plateau_limit = plateau_limit  # Number of iterations before considering stuck
        self.max_visits = 3  # Fixed value for state visit limit
        self.learning_rate = 0.2  # Fixed value for learning rate

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
        best_boxes = sum(1 for box in current_state.positions_of_boxes 
                        if box in current_state.targets)
        temperature = self.initial_temp
        iterations = 0
        last_improvement = 0
        visited = set()  # Using set for faster lookups
        visited_states: Set[str] = set()

        while iterations < self.max_iterations:
            iterations += 1

            # Get possible moves from current state
            possible_moves = current_state.filter_possible_moves()
            valid_moves = []

            # Filter moves that don't lead to previously visited states
            for move in possible_moves:
                next_state = current_state.copy()
                next_state.apply_move(move)
                state_key = self.get_state_key(next_state)

                if state_key not in visited_states:
                    valid_moves.append((move, next_state, state_key))

            # If no valid moves, clear visited states and try again
            if not valid_moves:
                visited_states.clear()
                continue

            # Select and apply a move
            move, next_state, state_key = random.choice(valid_moves)
            next_path = current_path + [move]
            next_cost = sokoban_heuristic(next_state)

            # Check if solved
            if next_state.is_solved():
                return next_path

            # Update best solution
            if next_cost < best_score:
                best_state = next_state
                best_path = next_path.copy()
                best_score = next_cost
                best_boxes = sum(1 for box in next_state.positions_of_boxes 
                                if box in next_state.targets)
                last_improvement = iterations

            # Check for plateau
            if iterations - last_improvement > self.plateau_limit:
                # Adaptive restart strategy with more exploration
                progress = (sokoban_heuristic(initial_state) - best_score) / sokoban_heuristic(initial_state)
                current_complexity = len(current_state.boxes) * len(current_state.obstacles)

                # Adjust strategy based on progress and complexity
                if progress > 0.3:  # Even modest progress is good
                    current_state = best_state
                    current_path = best_path.copy()
                    # Very high temperature for exploration
                    temperature = self.initial_temp * 0.8

                    # Aggressive random walk
                    for _ in range(random.randint(5, 15)):
                        moves = current_state.filter_possible_moves()
                        if moves:
                            # Prefer box moves when exploring
                            box_moves = [m for m in moves if m >= 4]
                            if box_moves and random.random() < 0.7:
                                move = random.choice(box_moves)
                            else:
                                move = random.choice(moves)
                            current_state.apply_move(move)
                            current_path.append(move)
                else:  # Poor progress, try extreme measures
                    if random.random() < 0.6:  # 60% chance for fresh start
                        current_state = initial_state
                        current_path = []
                        temperature = self.initial_temp
                    else:  # 40% chance for very long random walk
                        current_state = best_state
                        current_path = best_path.copy()
                        # Much more random moves when stuck
                        for _ in range(random.randint(20, 30)):
                            moves = current_state.filter_possible_moves()
                            if moves:
                                # Prefer box moves when exploring
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

            # Get current metrics
            current_score = sokoban_heuristic(current_state)
            current_boxes = sum(1 for box in current_state.positions_of_boxes 
                              if box in current_state.targets)
            current_key = self.get_state_key(current_state)

            # Check visit limit
            if current_key in visited:
                if best_path:
                    current_state = best_state
                    current_path = best_path.copy()
                    visited.clear()
                    temperature = self.initial_temp
                    continue
                return None

            # Decide whether to accept the new state
            if self.acceptance_probability(best_score, current_score, temperature) > random.random():
                current_state = next_state
                current_path = next_path
                best_score = current_score
                visited.add(current_key)

            # Simple memory management
            if len(visited) > 5000:
                visited.clear()

            # Cool down
            temperature *= self.cooling_rate
            if temperature < self.min_temp:
                temperature = self.initial_temp
                visited_states.clear()

        return None  # No solution found within iteration limit