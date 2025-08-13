#!/usr/bin/env python3

import numpy as np
from scipy.stats import norm
import openskill
import openskill.models

# Test what happens with different percentiles
START_MU = 25

def calculate_conservative_rating(rating, percentile=80.0):
    """Calculate conservative rating using specified percentile"""
    alpha = 1
    target = 0
    z = abs(norm.ppf(percentile / 100.0))
    return rating.ordinal(z=z, alpha=alpha, target=target)

def test_percentile_behavior():
    """Test how different percentiles affect rating calculations"""
    
    # Create a sample rating
    model = openskill.models.BradleyTerryPart(mu=START_MU, sigma=START_MU/2.84)  # 80th percentile sigma
    rating = model.rating(mu=30, sigma=5)  # Player with mu=30, sigma=5
    
    print("Testing conservative rating calculation with different percentiles:")
    print(f"Player: mu={rating.mu:.2f}, sigma={rating.sigma:.2f}")
    print()
    
    percentiles = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]
    for p in percentiles:
        try:
            z_score = abs(norm.ppf(p / 100.0))
            conservative = calculate_conservative_rating(rating, p)
            print(f"Percentile {p:2d}%: z={z_score:.3f}, conservative_rating={conservative:.2f}")
        except Exception as e:
            print(f"Percentile {p:2d}%: ERROR - {e}")
    
    print("\nKey insight:")
    print("- Lower percentiles = higher conservative ratings (less penalty for uncertainty)")
    print("- Higher percentiles = lower conservative ratings (more penalty for uncertainty)")
    print()
    print("This explains why 50% performs 'better' in predictions:")
    print("- 50% gives ratings closest to mu (less conservative)")
    print("- Less conservative = more optimistic predictions")
    print("- This might lead to overfitting to historical data")

def test_prediction_bias():
    """Test if lower percentiles create prediction bias"""
    
    print("\n" + "="*60)
    print("TESTING PREDICTION BIAS")
    print("="*60)
    
    # Simulate 3 players with different uncertainty levels
    model = openskill.models.BradleyTerryPart(mu=START_MU, sigma=START_MU/2.84)
    
    players = [
        ("Experienced", model.rating(mu=30, sigma=2)),  # Low uncertainty
        ("Average", model.rating(mu=25, sigma=5)),      # Medium uncertainty  
        ("Newcomer", model.rating(mu=20, sigma=8))      # High uncertainty
    ]
    
    print("Player ratings:")
    for name, rating in players:
        print(f"{name:12}: mu={rating.mu:.1f}, sigma={rating.sigma:.1f}")
    
    print("\nConservative ratings by percentile:")
    print("Percentile   Experienced  Average     Newcomer    Spread")
    print("-" * 55)
    
    for p in [50, 70, 80, 90]:
        conservative_ratings = []
        for name, rating in players:
            conservative = calculate_conservative_rating(rating, p)
            conservative_ratings.append(conservative)
        
        spread = max(conservative_ratings) - min(conservative_ratings)
        print(f"{p:2d}%         {conservative_ratings[0]:8.1f}     {conservative_ratings[1]:7.1f}     {conservative_ratings[2]:8.1f}     {spread:5.1f}")
    
    print("\nObservation:")
    print("- Lower percentiles compress the rating spread")
    print("- This makes predictions less discriminating")
    print("- But also less sensitive to uncertainty")
    print("- This could create a false sense of 'better' predictions")

if __name__ == "__main__":
    test_percentile_behavior()
    test_prediction_bias()