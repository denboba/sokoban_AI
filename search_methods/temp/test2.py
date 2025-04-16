lrta_results = []
sa_results = []

def run_solver(solver, map_path, show_plots=True):
    sokoban_map = Map.from_yaml(map_path)

    start_time = time.time()
    solution = solver.solve(sokoban_map)
    solve_time = time.time() - start_time

    if solution:
        print(f"✓ {solver.__class__.__name__}: Solution found with {len(solution)} moves")
        print(f"✓ Pull moves used: {sum(1 for move in solution if move >= 4)}")
        print(f"✓ Time taken: {solve_time:.2f} seconds")

        final_state = Map.from_yaml(map_path)
        try:
            for move in solution:
                final_state.apply_move(move)
        except ValueError as e:
            print(f"✗ Replay error for {solver.__class__.__name__}: {e}")
            return False

        if show_plots:
            final_state.plot_map()

        # Save final visualization
        output_name = f"{solver.__class__.__name__.lower()}_{map_path.split('/')[-1].replace('.yaml', '')}"
        final_state.save_map('images', f'{output_name}_solution.png')

        return True
    else:
        print(f"✗ {solver.__class__.__name__}: No solution found")
        return False

# Run tests
for map_path in test_maps[:4]:  # First 4 maps (easy and medium)
    print("\n" + "="*60)
    print(f"Testing map: {map_path}")
    print("="*60)

    # Load and show initial map once
    initial_map = Map.from_yaml(map_path)
    print("\nInitial state:")
    initial_map.plot_map()

    # Test LRTA*
    print("\n--- LRTA* Solution ---")
    lrta_solver = LRTAStar(max_iterations=50000)
    lrta_success = run_solver(lrta_solver, map_path)
    lrta_results.append((map_path, lrta_success))

    # Test Simulated Annealing
    print("\n--- Simulated Annealing Solution ---")
    sa_solver = SimulatedAnnealing(
        initial_temp=100.0,
        cooling_rate=0.995,
        min_temp=0.01,
        max_iterations=10000
    )
    sa_success = run_solver(sa_solver, map_path)
    sa_results.append((map_path, sa_success))

# Final Summary
print("\n" + "="*60)
print("Test Summary")
print("="*60)

print("\nLRTA* Results:")
for map_path, passed in lrta_results:
    print(f"{map_path}: {'Passed ✓' if passed else 'Failed ✗'}")
print(f"Total Passed: {sum(1 for _, passed in lrta_results if passed)}/{len(lrta_results)}")

print("\nSimulated Annealing Results:")
for map_path, passed in sa_results:
    print(f"{map_path}: {'Passed ✓' if passed else 'Failed ✗'}")
print(f"Total Passed: {sum(1 for _, passed in sa_results if passed)}/{len(sa_results)}")
