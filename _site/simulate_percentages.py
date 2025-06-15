import numpy as np
import matplotlib.pyplot as plt

def simulate_match_scores(shooters, num_simulations=10000):
    """
    shooters: list of tuples [(name, mu, sigma), ...]
    Returns: dictionary with score statistics for each shooter
    """
    all_scores = {name: [] for name, _, _ in shooters}
    
    for _ in range(num_simulations):
        # Sample performance for each shooter
        performances = []
        for name, mu, sigma in shooters:
            # Sample from their skill distribution
            performance = np.random.normal(mu, sigma)
            performances.append((name, performance))
        
        # Convert performances to match percentages
        # Method 1: Normalize to 0-100% based on relative performance
        min_perf = min(perf for _, perf in performances)
        max_perf = max(perf for _, perf in performances)
        
        if max_perf > min_perf:  # Avoid division by zero
            for name, perf in performances:
                # Scale to 0-100%
                percentage = ((perf - min_perf) / (max_perf - min_perf)) * 100
                all_scores[name].append(percentage)
        else:
            # All performances equal - everyone gets 50%
            for name, _ in performances:
                all_scores[name].append(50.0)
    
    # Calculate statistics
    results = {}
    for name, scores in all_scores.items():
        results[name] = {
            'mean': np.mean(scores),
            'std': np.std(scores),
            'median': np.median(scores),
            'percentiles': {
                '25th': np.percentile(scores, 25),
                '75th': np.percentile(scores, 75),
                '90th': np.percentile(scores, 90),
                '10th': np.percentile(scores, 10)
            },
            'scores': scores  # Keep raw data for plotting
        }
    
    return results

# Alternative Method 2: Convert TrueSkill to IPSC-style percentages
def simulate_ipsc_percentages(shooters, num_simulations=10000):
    """
    Simulate IPSC-style match percentages where best shooter gets 100%
    """
    all_scores = {name: [] for name, _, _ in shooters}
    
    for _ in range(num_simulations):
        performances = []
        for name, mu, sigma in shooters:
            # Sample performance (could represent hit factor, time, etc.)
            performance = np.random.normal(mu, sigma)
            performances.append((name, performance))
        
        # Find best performance
        best_perf = max(perf for _, perf in performances)
        
        # Calculate percentages relative to best
        for name, perf in performances:
            if best_perf > 0:
                percentage = (perf / best_perf) * 100
            else:
                percentage = 100.0
            
            # Ensure non-negative percentages
            percentage = max(0, percentage)
            all_scores[name].append(percentage)
    
    return calculate_statistics(all_scores)

def calculate_statistics(all_scores):
    results = {}
    for name, scores in all_scores.items():
        results[name] = {
            'mean': np.mean(scores),
            'std': np.std(scores),
            'median': np.median(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'scores': scores
        }
    return results

# Example usage
shooters = [
    ("David", 90.9, 6.6),
    ("Kent", 40.3, 10.5),
    ("Jonas", 20.5, 13.1)
]

# Simulate match scores
results = simulate_match_scores(shooters)

# Print results
for name, stats in results.items():
    print(f"\n{name}:")
    print(f"  Average match %: {stats['mean']:.1f}%")
    print(f"  Std deviation: {stats['std']:.1f}%")
    print(f"  Typical range: {stats['percentiles']['25th']:.1f}% - {stats['percentiles']['75th']:.1f}%")

# Plot distributions
plt.figure(figsize=(12, 6))
for name, stats in results.items():
    plt.hist(stats['scores'], alpha=0.6, bins=30, label=name, density=True)

plt.xlabel('Match Percentage')
plt.ylabel('Density')
plt.title('Simulated Match Score Distributions')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()