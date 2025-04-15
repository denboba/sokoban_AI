import os
import time
import argparse
from typing import List
from sokoban.map import Map
from search_methods.lrta_star import LRTAStar
from search_methods.simmulated_annealing import SimulatedAnnealing

def solve_and_visualize(solver, map_file: str) -> List[float]:
    """Run solver on a map and collect metrics"""
    # Load the map
    initial_state = Map.from_yaml(map_file)
    
    # Time the solution
    start_time = time.time()
    solution = solver.solve(initial_state)
    solve_time = time.time() - start_time
    
    if solution is None:
        print("No solution found!")
        return [solve_time, 0, 0]
    
    print(f"Solution found with {len(solution)} moves")
    print(f"States explored: {getattr(solver, 'states_explored', 0)}")
    print(f"Pull moves used: {sum(1 for move in solution if move >= 4)}")
    print(f"Time taken: {solve_time:.2f} seconds")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(map_file), 'solution')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save initial state
    state = initial_state.copy()
    state.save_map(output_dir, 'initial_state')
    
    # Apply all moves and save final state
    for move in solution:
        state.apply_move(move)
    state.save_map(output_dir, 'final_state')
    
    print(f"\nSolution visualization saved in {output_dir}")
    print("Initial state: initial_state.png")
    print("Final state: final_state.png")
    
    return [solve_time, getattr(solver, 'states_explored', 0), sum(1 for move in solution if move >= 4)]

def main():
    parser = argparse.ArgumentParser(description='Solve Sokoban puzzle')
    parser.add_argument('algorithm', choices=['lrta', 'simulated-annealing'],
                      help='Algorithm to use for solving')
    parser.add_argument('map_file', help='Path to map file')
    
    args = parser.parse_args()
    
    # Create solver based on algorithm choice
    if args.algorithm == 'lrta':
        solver = LRTAStar(max_iterations=10000)
    else:  # simulated-annealing
        solver = SimulatedAnnealing(
            initial_temp=100.0,
            cooling_rate=0.995,
            min_temp=0.01,
            max_iterations=10000
        )
    
    # Solve the puzzle
    solve_and_visualize(solver, args.map_file)

if __name__ == '__main__':
    main()
