import os
import time
from typing import  Dict
from sokoban.map import Map
from search_methods.lrta_star import LRTAStar
from search_methods.simmulated_annealing import SimulatedAnnealing
def solve_and_visualize(solver, map_file: str, algorithm_name: str, quiet: bool = False) -> Dict:
    """Run solver on a map and collect metrics"""
    # Load the map
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

    if not quiet:
        if solution is None:
            print("No solution found!")
        else:
            print(f"Solution found with {results['moves']} moves")
            print(f"States explored: {results['states_explored']}")
            print(f"Pull moves used: {results['pull_moves']}")
            print(f"Time taken: {results['time']:.2f} seconds")

            # Save visualization in algorithm-specific subdirectory
            map_name = os.path.basename(map_file).replace(".yaml", "")
            output_dir = os.path.join(
                os.path.dirname(map_file),
                'solutions',
                algorithm_name.replace(' ', '_').lower(),
                map_name
            )
            os.makedirs(output_dir, exist_ok=True)

            state = initial_state.copy()
            state.save_map(output_dir, f'{map_name}_initial_state')

            for move in solution:
                state.apply_move(move)
            state.save_map(output_dir, f'{map_name}_final_state')

            print(f"\nSolution visualization saved in {output_dir}")

    return results


def main():
    # List of test maps
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

    # Results storage
    results = []

    # Test LRTA*
    print("\n=== Testing LRTA* Algorithm ===")
    algorithm_name = 'LRTA*'

    for map_file in test_maps:
        import random
        random.seed()  # Ensure independent randomness for each run
        lrta_solver = LRTAStar(max_iterations=600000)  # New solver instance for each map
        print(f"\nTesting {os.path.basename(map_file)}...")
        result = solve_and_visualize(lrta_solver, map_file, algorithm_name)
        result['algorithm'] = algorithm_name
        result['map'] = os.path.basename(map_file)
        results.append(result)

    # Test Simulated Annealing
    print("\n=== Testing Simulated Annealing Algorithm ===")
    sa_solver = SimulatedAnnealing(
        initial_temp=100.0,
        cooling_rate=0.9999,
        min_temp=0.05,
        max_iterations=200000,
        restart_temp=50.0,
        plateau_limit=100,
    )
    algorithm_name = 'Simulated Annealing'

    for map_file in test_maps:
        print(f"\nTesting {os.path.basename(map_file)}...")
        result = solve_and_visualize(sa_solver, map_file, algorithm_name)
        result['algorithm'] = algorithm_name
        result['map'] = os.path.basename(map_file)
        results.append(result)

if __name__ == '__main__':
    main()

