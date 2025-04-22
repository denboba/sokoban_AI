import os
import time
import random
import argparse
import shutil
from typing import Dict
from sokoban.map import Map
from search_methods.lrta_star import LRTAStar
from search_methods.simmulated_annealing import SimulatedAnnealing
from sokoban.gif import save_images, create_gif
def solve_and_visualize(solver, map_file: str, algorithm_name: str, generate_gif: bool = False) -> Dict:
    """Run solver on a map and collect metrics."""
    initial_state = Map.from_yaml(map_file)

    # Time the solution
    start_time = time.time()
    solution = solver.solve(initial_state)
    solve_time = time.time() - start_time

    results = {
        'solved': solution is not None,
        'time': solve_time,
        'moves': len(solution) if solution else 0,
        'states_explored': getattr(solver, 'states_explored', 0),
        'pull_moves': sum(1 for move in solution if move >= 4) if solution else 0
    }

    if solution is None:
        print("No solution found!")
    else:
        print(f"Solution found with {results['moves']} moves")
        print(f"States explored: {results['states_explored']}")
        print(f"Pull moves used: {results['pull_moves']}")
        print(f"Time taken: {results['time']:.2f} seconds")

        # Save state
        map_name = os.path.basename(map_file).replace(".yaml", "")
        output_dir = os.path.join(
            os.path.dirname(map_file),
            'solutions',
            algorithm_name.replace(' ', '-').lower(),
            map_name
        )
        os.makedirs(output_dir, exist_ok=True)

        # Save initial state
        initial_state.save_map(output_dir, f'{map_name}_initial_state')
        
        # Create a list to store all states
        states = [initial_state.copy()]
        state = initial_state.copy()
        
        # Apply moves and store states
        for move in solution:
            state.apply_move(move)
            states.append(state.copy())
        
        # Save final state
        state.save_map(output_dir, f'{map_name}_final_state')
        
        # Save intermediate states and create GIF
        if generate_gif:
            temp_dir = os.path.join(output_dir, 'temp_frames')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save all states in sequence
            for i, state in enumerate(states):
                state.save_map(temp_dir, f'step{i:04d}')
            
            # Create GIF
            create_gif(temp_dir, f'{map_name}_solution.gif', output_dir)
            
            # Clean up temporary frames
            shutil.rmtree(temp_dir)

        print(f"\nSolution visualization saved in {output_dir}")

    return results


def initialize_solver(algorithm: str):
    """Initialize the solver based on the algorithm."""
    if algorithm == 'lrta*':
        return LRTAStar(max_iterations=600000)
    elif algorithm == 'simulated-annealing':
        return SimulatedAnnealing(
            initial_temp=100.0,
            cooling_rate=0.9999,
            min_temp=0.05,
            max_iterations=200000,
            restart_temp=50.0,
            plateau_limit=100,
        )
    else:
        raise ValueError("Invalid algorithm specified.")


def test_maps_with_solver(solver, test_maps, algorithm_name, generate_gif: bool = False):
    """Test a solver on a list of maps."""
    results = []
    for map_file in test_maps:
        print(f"\nTesting {os.path.basename(map_file)}...")
        result = solve_and_visualize(solver, map_file, algorithm_name, generate_gif=generate_gif)
        result['algorithm'] = algorithm_name
        result['map'] = os.path.basename(map_file)
        results.append(result)
    return results


def main():
    # Command-line arguments
    parser = argparse.ArgumentParser(description="Run Sokoban solver with specified algorithm and input file.")
    parser.add_argument('positional_algorithm', type=str, nargs='?', default=None,
                        help="Algorithm to use: 'lrta*' or 'simulated-annealing'.")
    parser.add_argument('positional_input', type=str, nargs='?', default=None,
                        help="Path to the input map file.")
    parser.add_argument('-a', '--algorithm', type=str, choices=['lrta*', 'simulated-annealing'], default=None,
                        help="Algorithm to use: 'lrta*' or 'simulated-annealing'.")
    parser.add_argument('-i', '--input', type=str, default=None, help="Path to the input map file.")
    parser.add_argument('-g', '--gif', action='store_true', help="Generate a GIF animation of the solution")
    args = parser.parse_args()

    # Determine algorithm and input file
    algorithm = args.algorithm or args.positional_algorithm
    input_file = args.input or args.positional_input

    # Default test maps
    test_maps = [
        'tests/easy_map1.yaml',
        'tests/easy_map2.yaml',
        'tests/medium_map1.yaml',
        'tests/medium_map2.yaml',
        'tests/hard_map1.yaml',
        'tests/hard_map2.yaml',
        'tests/large_map1.yaml',
        'tests/large_map2.yaml',
        'tests/super_hard_map1.yaml'
    ]

    results = []

    if not algorithm and not input_file:
        # Default behavior: Test all maps with both algorithms
        print("\n=== Testing LRTA* Algorithm ===")
        lrta_solver = initialize_solver('lrta*')
        results.extend(test_maps_with_solver(lrta_solver, test_maps, 'LRTA*', generate_gif=args.gif))

        print("\n=== Testing Simulated Annealing Algorithm ===")
        sa_solver = initialize_solver('simulated-annealing')
        results.extend(test_maps_with_solver(sa_solver, test_maps, 'Simulated Annealing', generate_gif=args.gif))

    elif algorithm and not input_file:
        # Test all maps with the specified algorithm
        try:
            solver = initialize_solver(algorithm)
            print(f"\n=== Running {algorithm.upper()} Algorithm ===")
            results.extend(test_maps_with_solver(solver, test_maps, algorithm, generate_gif=args.gif))
        except ValueError as e:
            print(e)

    elif algorithm and input_file:
        # Run with specified algorithm and input file
        if not os.path.exists(input_file):
            print("Error: Input file is required and must exist.")
            return

        try:
            solver = initialize_solver(algorithm)
            print(f"\n=== Running {algorithm.upper()} Algorithm ===")
            result = solve_and_visualize(solver, input_file, algorithm, generate_gif=args.gif)
            results.append(result)
        except ValueError as e:
            print(e)

    else:
        print("Error: Invalid arguments provided.")



if __name__ == "__main__":
    main()