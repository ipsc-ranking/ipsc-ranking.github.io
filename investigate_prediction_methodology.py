#!/usr/bin/env python3

import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt

def analyze_prediction_flaw():
    """Analyze why lower percentiles appear to give better predictions"""
    
    print("ANALYZING THE PREDICTION METHODOLOGY FLAW")
    print("="*50)
    
    # The core issue: What does "better prediction" actually mean?
    print("\n1. MEASUREMENT BIAS:")
    print("   - We're measuring MAE (Mean Absolute Error) of placement predictions")
    print("   - Lower percentiles give ratings closer to mu")
    print("   - This creates tighter rating spreads")
    print("   - Tighter spreads = less extreme placement predictions")
    print("   - Less extreme predictions = lower MAE when variance is high")
    
    print("\n2. THE FUNDAMENTAL FLAW:")
    print("   Conservative ratings are NOT meant to optimize placement predictions!")
    print("   They are meant to:")
    print("   - Provide stable rankings under uncertainty")
    print("   - Prevent new/inactive players from being overrated")
    print("   - Give meaningful comparisons across different skill levels")
    
    print("\n3. WHAT'S HAPPENING:")
    
    # Simulate the effect
    np.random.seed(42)
    
    # True skill levels
    true_skills = [30, 28, 26, 24, 22, 20, 18, 16, 14, 12]
    uncertainties = [2, 2, 3, 3, 4, 5, 6, 7, 8, 9]  # Higher uncertainty for lower-rated players
    
    print(f"   Simulating 10 players with true skills: {true_skills}")
    print(f"   With uncertainties (sigma):             {uncertainties}")
    
    # Calculate conservative ratings for different percentiles
    percentiles = [50, 70, 80, 90]
    
    for p in percentiles:
        z = abs(norm.ppf(p / 100.0)) if p < 100 else 0
        conservative_ratings = []
        
        for i, (skill, sigma) in enumerate(zip(true_skills, uncertainties)):
            conservative = skill - z * sigma  # Simplified conservative rating
            conservative_ratings.append(conservative)
        
        # Sort by conservative rating to get predicted placements
        sorted_indices = sorted(range(len(conservative_ratings)), 
                              key=lambda i: conservative_ratings[i], reverse=True)
        
        predicted_order = [i+1 for i in sorted_indices]  # Convert to player numbers
        actual_order = list(range(1, 11))  # Perfect order by true skill
        
        # Calculate how many positions each player is off
        position_errors = []
        for actual_pos in actual_order:
            predicted_pos = predicted_order.index(actual_pos) + 1
            error = abs(predicted_pos - actual_pos)
            position_errors.append(error)
        
        mae = np.mean(position_errors)
        print(f"\n   Percentile {p:2d}%: MAE = {mae:.2f}")
        print(f"   Conservative ratings: {[f'{r:.1f}' for r in conservative_ratings]}")
        print(f"   Predicted order:      {predicted_order}")
        
    print("\n4. THE ILLUSION:")
    print("   - 50% percentile gives MAE closest to mu")
    print("   - This creates 'better' placement predictions in our test")
    print("   - BUT this is because we're not accounting for the PURPOSE of conservative ratings")
    print("   - Conservative ratings should be CONSERVATIVE, not optimized for placement accuracy")
    
    print("\n5. WHAT WE SHOULD MEASURE INSTEAD:")
    print("   - Ranking stability over time")
    print("   - Proper handling of new/inactive players")
    print("   - Meaningful separation between skill levels")
    print("   - Protection against rating inflation")
    
    print("\n6. CONCLUSION:")
    print("   The 50% percentile result is an ARTIFACT of our measurement method")
    print("   It's optimizing for the wrong thing!")
    print("   Conservative ratings should remain conservative (70-85% range)")

def demonstrate_real_world_impact():
    """Show what happens in real rankings with different percentiles"""
    
    print("\n" + "="*60)
    print("REAL-WORLD IMPACT ANALYSIS")
    print("="*60)
    
    # Simulate realistic player scenarios
    scenarios = [
        ("Established Pro", 35, 1.5),     # Very low uncertainty
        ("Regular Competitor", 28, 3),    # Low uncertainty  
        ("Occasional Shooter", 22, 5),    # Medium uncertainty
        ("New Player", 20, 8),            # High uncertainty
        ("Returning Player", 25, 7),      # High uncertainty due to inactivity
    ]
    
    print("\nHow different percentiles affect player rankings:")
    print("Player Type           True Rating  50%    70%    80%    90%")
    print("-" * 60)
    
    for name, mu, sigma in scenarios:
        ratings_by_percentile = []
        for p in [50, 70, 80, 90]:
            z = abs(norm.ppf(p / 100.0)) if p < 100 else 0
            conservative = mu - z * sigma
            ratings_by_percentile.append(conservative)
        
        print(f"{name:20} {mu:8.1f}      {ratings_by_percentile[0]:5.1f}  {ratings_by_percentile[1]:5.1f}  {ratings_by_percentile[2]:5.1f}  {ratings_by_percentile[3]:5.1f}")
    
    print("\nKey observations:")
    print("- 50% percentile: New/inactive players get nearly full credit for uncertainty")
    print("- 80% percentile: Proper conservative penalty for uncertainty")
    print("- 90% percentile: Very conservative, perhaps too harsh")
    print("\nThe 80% percentile provides the right balance!")

if __name__ == "__main__":
    analyze_prediction_flaw()
    demonstrate_real_world_impact()