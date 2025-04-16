# Create a function to run tests and collect metrics
def run_analysis(solver, map_files, heuristics=None):
    results = defaultdict(dict)

    for map_file in map_files:
        map_name = os.path.basename(map_file).replace('.yaml', '')
        sokoban_map = Map.from_yaml(map_file)

        # Run solver
        start_time = time.time()
        solution = solver.solve(sokoban_map)
        solve_time = time.time() - start_time

        # Collect metrics
        results[map_name] = {
            'time': solve_time,
            'moves': len(solution) if solution else 0,
            'pull_moves': sum(1 for move in solution if move >= 4) if solution else 0,
            'solved': solution is not None
        }

    return results

# List of test maps
test_maps = [
    'tests/easy_map1.yaml',
    'tests/medium_map1.yaml',
    'tests/hard_map1.yaml'
]

# Run analysis for both solvers
lrta_solver = LRTAStar(max_iterations=10000)
sa_solver = SimulatedAnnealing(initial_temp=100, cooling_rate=0.99)

lrta_results = run_analysis(lrta_solver, test_maps)
sa_results = run_analysis(sa_solver, test_maps)

# Create bar plot for solution times
plt.figure(figsize=(12, 6))
maps = list(lrta_results.keys())
lrta_times = [lrta_results[m]['time'] for m in maps]
sa_times = [sa_results[m]['time'] for m in maps]

x = np.arange(len(maps))
width = 0.35

plt.bar(x - width/2, lrta_times, width, label='LRTA*')
plt.bar(x + width/2, sa_times, width, label='Simulated Annealing')

plt.xlabel('Maps')
plt.ylabel('Runtime (seconds)')
plt.title('Runtime Comparison: LRTA* vs Simulated Annealing')
plt.xticks(x, maps)
plt.legend()
plt.yscale('log')  # Use log scale for better visualization
plt.grid(True, alpha=0.3)
plt.show()

# Create bar plot for pull moves
plt.figure(figsize=(12, 6))
lrta_pulls = [lrta_results[m]['pull_moves'] for m in maps]
sa_pulls = [sa_results[m]['pull_moves'] for m in maps]

plt.bar(x - width/2, lrta_pulls, width, label='LRTA*')
plt.bar(x + width/2, sa_pulls, width, label='Simulated Annealing')

plt.xlabel('Maps')
plt.ylabel('Number of Pull Moves')
plt.title('Pull Moves Comparison: LRTA* vs Simulated Annealing')
plt.xticks(x, maps)
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

# Print detailed statistics
print("\nDetailed Statistics:")
print("-" * 50)
for map_name in maps:
    print(f"\nMap: {map_name}")
    print("LRTA*:")
    print(f"  Time: {lrta_results[map_name]['time']:.2f} seconds")
    print(f"  Total moves: {lrta_results[map_name]['moves']}")
    print(f"  Pull moves: {lrta_results[map_name]['pull_moves']}")
    print(f"  Solved: {lrta_results[map_name]['solved']}")

    print("\nSimulated Annealing:")
    print(f"  Time: {sa_results[map_name]['time']:.2f} seconds")
    print(f"  Total moves: {sa_results[map_name]['moves']}")
    print(f"  Pull moves: {sa_results[map_name]['pull_moves']}")
    print(f"  Solved: {sa_results[map_name]['solved']}")