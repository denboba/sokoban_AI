from typing import List, Dict, Tuple, Optional, Set
from .solver import Solver
from .heuristics import sokoban_heuristic
from sokoban.moves import *

class LRTAStar(Solver):
    def __init__(self, max_iterations=10000):
        self.max_iterations = max_iterations
        self.h_values: Dict[str, float] = {}  # Learning table for heuristic values
        
    def get_state_key(self, state) -> str:
        """Create a unique key for a state"""
        # Include player position and all box positions in the key
        box_positions = sorted((box.x, box.y) for box in state.boxes.values())
        return f"p{state.player.x},{state.player.y}|b{box_positions}"
        
    def get_heuristic(self, state) -> float:
        """Get heuristic value for a state, using learned values if available"""
        state_key = self.get_state_key(state)
        if state_key not in self.h_values:
            self.h_values[state_key] = sokoban_heuristic(state)
        return self.h_values[state_key]
    
    def update_heuristic(self, state, value):
        """Update learned heuristic value for a state"""
        state_key = self.get_state_key(state)
        self.h_values[state_key] = max(value, self.h_values.get(state_key, 0))
    
    def solve(self, initial_state) -> Optional[List[int]]:
        """Solve Sokoban puzzle using LRTA* algorithm"""
        current_state = initial_state
        path = []
        iterations = 0
        visited_states: Set[str] = set()
        last_best_h = float('inf')
        stagnation_counter = 0
        
        while not current_state.is_solved() and iterations < self.max_iterations:
            iterations += 1
            current_key = self.get_state_key(current_state)
            
            # Get all possible moves from current state
            possible_moves = current_state.filter_possible_moves()
            if not possible_moves:
                return None  # No solution found
            
            # Find the best move based on learned heuristics
            min_f = float('inf')
            best_move = None
            best_next_state = None
            
            for move in possible_moves:
                next_state = current_state.copy()
                next_state.apply_move(move)
                next_key = self.get_state_key(next_state)
                
                # Skip if we've seen this state too many times
                if next_key in visited_states:
                    continue
                
                # f(s') = g(s,s') + h(s')
                g_cost = 2 if move >= BOX_LEFT else 1
                h_value = self.get_heuristic(next_state)
                f_value = g_cost + h_value
                
                if f_value < min_f:
                    min_f = f_value
                    best_move = move
                    best_next_state = next_state
            
            # If all neighbors are visited, reset visited set
            if best_move is None:
                visited_states.clear()
                continue
            
            # Update heuristic value of current state
            self.update_heuristic(current_state, min_f)
            
            # Check for stagnation
            current_h = self.get_heuristic(current_state)
            if abs(current_h - last_best_h) < 0.01:
                stagnation_counter += 1
                if stagnation_counter > 100:  # Reset if stuck
                    visited_states.clear()
                    stagnation_counter = 0
            else:
                stagnation_counter = 0
            last_best_h = current_h
            
            # Make the move
            path.append(best_move)
            visited_states.add(current_key)
            current_state = best_next_state
            
            # Early success check
            if current_state.is_solved():
                return path
            
        return None  # No solution found within iteration limit
