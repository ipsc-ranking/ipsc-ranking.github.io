import json
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
from scipy import optimize
from scipy.stats import norm
import openskill
import openskill.models
from combined_skill import IPSCRankingSystem, START_MU, START_SIGMA, PERCENTILE
from division_normalizer import normalize_division_name

class SigmaDecayOptimizer:
    def __init__(self):
        self.match_data = []
        self.player_activity_patterns = defaultdict(list)
        self.player_performance_consistency = defaultdict(list)
        self.temporal_gaps = []
        self.match_dates = []
        
    def load_and_analyze_data(self):
        """Load all match data and analyze temporal patterns"""
        print("Loading match data for analysis...")
        
        match_files_location = './match_data/'
        for filename in os.listdir(match_files_location):
            if filename.endswith('.json'):
                filepath = os.path.join(match_files_location, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        match_data = json.load(f)
                        if 'combined_results' in match_data and len(match_data['combined_results']) > 0:
                            self.match_data.append(match_data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort matches by date
        self.match_data.sort(key=lambda x: datetime.fromisoformat(x['match_date'].replace('Z', '+00:00')))
        self.match_dates = [datetime.fromisoformat(m['match_date'].replace('Z', '+00:00')) for m in self.match_data]
        
        print(f"Loaded {len(self.match_data)} matches from {self.match_dates[0].date()} to {self.match_dates[-1].date()}")
        
        self._analyze_player_activity_patterns()
        self._analyze_temporal_gaps()
        
    def _analyze_player_activity_patterns(self):
        """Analyze how often players compete and their consistency"""
        print("Analyzing player activity patterns...")
        
        player_matches = defaultdict(list)
        player_performances = defaultdict(list)
        
        for match in self.match_data:
            match_date = datetime.fromisoformat(match['match_date'].replace('Z', '+00:00'))
            
            for result in match['combined_results']:
                # Create player identifier
                division = normalize_division_name(result.get('division', 'Unknown'))
                player_id = f"{result['first_name']}_{result['last_name']}_{result.get('region', 'Unknown')}_{division}".lower().replace(' ', '_')
                
                player_matches[player_id].append(match_date)
                player_performances[player_id].append(result['match_percentage'])
        
        # Calculate activity patterns
        for player_id, match_dates in player_matches.items():
            if len(match_dates) > 1:
                # Sort dates
                match_dates.sort()
                
                # Calculate gaps between matches
                gaps = [(match_dates[i+1] - match_dates[i]).days for i in range(len(match_dates)-1)]
                
                self.player_activity_patterns[player_id] = {
                    'total_matches': len(match_dates),
                    'first_match': match_dates[0],
                    'last_match': match_dates[-1],
                    'career_span_days': (match_dates[-1] - match_dates[0]).days,
                    'average_gap_days': statistics.mean(gaps) if gaps else 0,
                    'median_gap_days': statistics.median(gaps) if gaps else 0,
                    'max_gap_days': max(gaps) if gaps else 0,
                    'gap_std': statistics.stdev(gaps) if len(gaps) > 1 else 0,
                    'gaps': gaps
                }
                
                # Calculate performance consistency
                performances = player_performances[player_id]
                if len(performances) > 1:
                    self.player_performance_consistency[player_id] = {
                        'mean_performance': statistics.mean(performances),
                        'std_performance': statistics.stdev(performances),
                        'coefficient_of_variation': statistics.stdev(performances) / statistics.mean(performances) if statistics.mean(performances) > 0 else 0,
                        'performances': performances
                    }
    
    def _analyze_temporal_gaps(self):
        """Analyze gaps between all matches to understand competition frequency"""
        print("Analyzing temporal gaps between matches...")
        
        if len(self.match_dates) > 1:
            self.temporal_gaps = [(self.match_dates[i+1] - self.match_dates[i]).days 
                                 for i in range(len(self.match_dates)-1)]
    
    def print_activity_analysis(self):
        """Print comprehensive activity analysis"""
        print("\n" + "="*80)
        print("PLAYER ACTIVITY ANALYSIS")
        print("="*80)
        
        if not self.player_activity_patterns:
            print("No activity patterns found.")
            return
        
        # Overall statistics
        total_players = len(self.player_activity_patterns)
        active_players = [p for p in self.player_activity_patterns.values() if p['total_matches'] >= 3]
        
        print(f"Total players analyzed: {total_players}")
        print(f"Players with 3+ matches: {len(active_players)}")
        
        # Activity frequency analysis
        all_gaps = []
        for pattern in self.player_activity_patterns.values():
            all_gaps.extend(pattern['gaps'])
        
        if all_gaps:
            print(f"\nActivity Gap Analysis (days between matches):")
            print(f"  Mean gap: {statistics.mean(all_gaps):.1f} days")
            print(f"  Median gap: {statistics.median(all_gaps):.1f} days")
            print(f"  Standard deviation: {statistics.stdev(all_gaps):.1f} days")
            print(f"  Min gap: {min(all_gaps)} days")
            print(f"  Max gap: {max(all_gaps)} days")
            
            # Gap distribution
            gap_ranges = [
                (0, 30, "0-30 days"),
                (31, 60, "31-60 days"),
                (61, 90, "61-90 days"),
                (91, 180, "91-180 days"),
                (181, 365, "181-365 days"),
                (366, float('inf'), "365+ days")
            ]
            
            print(f"\nGap Distribution:")
            for min_gap, max_gap, label in gap_ranges:
                count = sum(1 for gap in all_gaps if min_gap <= gap <= max_gap)
                percentage = (count / len(all_gaps)) * 100
                print(f"  {label}: {count} ({percentage:.1f}%)")
        
        # Performance consistency analysis
        if self.player_performance_consistency:
            cvs = [p['coefficient_of_variation'] for p in self.player_performance_consistency.values()]
            print(f"\nPerformance Consistency (Coefficient of Variation):")
            print(f"  Mean CV: {statistics.mean(cvs):.3f}")
            print(f"  Median CV: {statistics.median(cvs):.3f}")
            print(f"  Players with high consistency (CV < 0.1): {sum(1 for cv in cvs if cv < 0.1)}")
            print(f"  Players with low consistency (CV > 0.3): {sum(1 for cv in cvs if cv > 0.3)}")
    
    def simulate_decay_models(self):
        """Simulate different decay models and evaluate their effectiveness"""
        print("\n" + "="*80)
        print("SIMULATING DECAY MODELS")
        print("="*80)
        
        # Define different decay models to test
        decay_models = [
            # Current constant model
            {'name': 'Current Constant', 'type': 'constant', 'decay_per_day': 0.01, 'max_multiplier': 2.0},
            
            # Optimized constant models
            {'name': 'Low Constant', 'type': 'constant', 'decay_per_day': 0.005, 'max_multiplier': 2.0},
            {'name': 'Medium Constant', 'type': 'constant', 'decay_per_day': 0.015, 'max_multiplier': 2.0},
            {'name': 'High Constant', 'type': 'constant', 'decay_per_day': 0.02, 'max_multiplier': 2.0},
            
            # Logarithmic decay models
            {'name': 'Log Decay Slow', 'type': 'logarithmic', 'base_decay': 0.005, 'log_factor': 0.001, 'max_multiplier': 2.0},
            {'name': 'Log Decay Medium', 'type': 'logarithmic', 'base_decay': 0.01, 'log_factor': 0.002, 'max_multiplier': 2.0},
            {'name': 'Log Decay Fast', 'type': 'logarithmic', 'base_decay': 0.015, 'log_factor': 0.003, 'max_multiplier': 2.0},
            
            # Exponential decay models
            {'name': 'Exp Decay Slow', 'type': 'exponential', 'initial_decay': 0.002, 'growth_rate': 0.01, 'max_multiplier': 2.0},
            {'name': 'Exp Decay Medium', 'type': 'exponential', 'initial_decay': 0.005, 'growth_rate': 0.015, 'max_multiplier': 2.0},
            {'name': 'Exp Decay Fast', 'type': 'exponential', 'initial_decay': 0.008, 'growth_rate': 0.02, 'max_multiplier': 2.0},
            
            # Adaptive models based on player consistency
            {'name': 'Adaptive Low', 'type': 'adaptive', 'base_decay': 0.005, 'consistency_factor': 0.5, 'max_multiplier': 2.0},
            {'name': 'Adaptive Medium', 'type': 'adaptive', 'base_decay': 0.01, 'consistency_factor': 1.0, 'max_multiplier': 2.0},
            {'name': 'Adaptive High', 'type': 'adaptive', 'base_decay': 0.015, 'consistency_factor': 1.5, 'max_multiplier': 2.0},
        ]
        
        results = []
        
        for model in decay_models:
            print(f"Testing {model['name']}...")
            
            # Create a custom ranking system with this decay model
            ranking_system = self._create_custom_ranking_system(model)
            
            # Process all matches
            for match in self.match_data:
                ranking_system.process_match(match)
            
            # Evaluate the model
            evaluation = self._evaluate_model(ranking_system, model)
            results.append(evaluation)
        
        # Print results
        self._print_model_comparison(results)
        
        return results
    
    def _create_custom_ranking_system(self, model):
        """Create a ranking system with custom decay model"""
        class CustomRankingSystem(IPSCRankingSystem):
            def __init__(self, decay_model):
                super().__init__()
                self.decay_model = decay_model
                self.player_consistency = {}  # For adaptive models
            
            def adjust_for_inactivity(self, current_date):
                """Custom inactivity adjustment based on model type"""
                for player_id, player_data in self.players.items():
                    if player_id in self.player_last_match:
                        days_since_last_match = (current_date - self.player_last_match[player_id]).days
                        if days_since_last_match > 0:
                            current_rating = player_data['rating']
                            
                            # Calculate decay based on model type
                            if self.decay_model['type'] == 'constant':
                                additional_sigma = self.decay_model['decay_per_day'] * days_since_last_match
                            
                            elif self.decay_model['type'] == 'logarithmic':
                                additional_sigma = (self.decay_model['base_decay'] * days_since_last_match + 
                                                 self.decay_model['log_factor'] * np.log(1 + days_since_last_match))
                            
                            elif self.decay_model['type'] == 'exponential':
                                additional_sigma = (self.decay_model['initial_decay'] * 
                                                 (np.exp(self.decay_model['growth_rate'] * days_since_last_match / 30) - 1))
                            
                            elif self.decay_model['type'] == 'adaptive':
                                # Get player consistency (coefficient of variation)
                                consistency = self.player_consistency.get(player_id, 1.0)  # Default to average consistency
                                # Higher consistency (lower CV) = slower decay
                                consistency_multiplier = 1.0 + (consistency * self.decay_model['consistency_factor'])
                                additional_sigma = self.decay_model['base_decay'] * days_since_last_match * consistency_multiplier
                            
                            else:
                                additional_sigma = 0.01 * days_since_last_match  # Fallback
                            
                            # Apply the decay
                            new_sigma = current_rating.sigma + additional_sigma
                            max_sigma = START_SIGMA * self.decay_model['max_multiplier']
                            new_sigma = min(new_sigma, max_sigma)
                            
                            try:
                                player_data['rating'] = self.model.rating(
                                    mu=current_rating.mu,
                                    sigma=new_sigma
                                )
                            except Exception as e:
                                pass  # Skip if error
            
            def set_player_consistency(self, player_id, consistency):
                """Set player consistency for adaptive models"""
                self.player_consistency[player_id] = consistency
        
        ranking_system = CustomRankingSystem(model)
        
        # For adaptive models, set player consistency values
        if model['type'] == 'adaptive':
            for player_id, consistency_data in self.player_performance_consistency.items():
                ranking_system.set_player_consistency(player_id, consistency_data['coefficient_of_variation'])
        
        return ranking_system
    
    def _evaluate_model(self, ranking_system, model):
        """Evaluate a decay model's effectiveness"""
        rankings = ranking_system.generate_ranking(sweden_only=True)
        
        # Calculate various metrics
        total_players = len(rankings)
        if total_players == 0:
            return {
                'model': model,
                'total_players': 0,
                'avg_sigma': 0,
                'sigma_spread': 0,
                'rating_spread': 0,
                'active_player_ratio': 0
            }
        
        sigmas = [p['sigma'] for p in rankings]
        ratings = [p['conservative_rating'] for p in rankings]
        matches_played = [p['matches_played'] for p in rankings]
        
        # Players with reasonable uncertainty (not too high sigma)
        reasonable_uncertainty_players = sum(1 for s in sigmas if s < START_SIGMA * 1.5)
        
        evaluation = {
            'model': model,
            'total_players': total_players,
            'avg_sigma': statistics.mean(sigmas),
            'median_sigma': statistics.median(sigmas),
            'sigma_spread': statistics.stdev(sigmas) if len(sigmas) > 1 else 0,
            'max_sigma': max(sigmas),
            'min_sigma': min(sigmas),
            'avg_rating': statistics.mean(ratings),
            'rating_spread': statistics.stdev(ratings) if len(ratings) > 1 else 0,
            'avg_matches': statistics.mean(matches_played),
            'reasonable_uncertainty_ratio': reasonable_uncertainty_players / total_players,
            'high_sigma_players': sum(1 for s in sigmas if s > START_SIGMA * 1.8),
        }
        
        return evaluation
    
    def _print_model_comparison(self, results):
        """Print comparison of different decay models"""
        print("\n" + "="*120)
        print("DECAY MODEL COMPARISON")
        print("="*120)
        
        # Sort by a composite score (lower average sigma + higher reasonable uncertainty ratio)
        def composite_score(result):
            return result['avg_sigma'] - (result['reasonable_uncertainty_ratio'] * 5)
        
        results.sort(key=composite_score)
        
        print(f"{'Model':<20} {'Avg σ':<8} {'Med σ':<8} {'σ Spread':<10} {'Reasonable %':<12} {'High σ Count':<12} {'Avg Rating':<12}")
        print("-" * 120)
        
        for result in results:
            print(f"{result['model']['name']:<20} "
                  f"{result['avg_sigma']:<8.3f} "
                  f"{result['median_sigma']:<8.3f} "
                  f"{result['sigma_spread']:<10.3f} "
                  f"{result['reasonable_uncertainty_ratio']*100:<12.1f} "
                  f"{result['high_sigma_players']:<12} "
                  f"{result['avg_rating']:<12.1f}")
        
        print("\nBest models (lowest composite score):")
        for i, result in enumerate(results[:3]):
            print(f"{i+1}. {result['model']['name']}: {result['model']}")
    
    def recommend_optimal_parameters(self, results):
        """Recommend optimal decay parameters based on analysis"""
        print("\n" + "="*80)
        print("OPTIMAL DECAY PARAMETER RECOMMENDATIONS")
        print("="*80)
        
        if not results:
            print("No results to analyze.")
            return
        
        # Find the best performing model
        best_model = results[0]  # Already sorted by composite score
        
        print(f"Recommended model: {best_model['model']['name']}")
        print(f"Model parameters: {best_model['model']}")
        
        print(f"\nPerformance metrics:")
        print(f"  Average sigma: {best_model['avg_sigma']:.3f}")
        print(f"  Median sigma: {best_model['median_sigma']:.3f}")
        print(f"  Players with reasonable uncertainty: {best_model['reasonable_uncertainty_ratio']*100:.1f}%")
        print(f"  Players with high sigma: {best_model['high_sigma_players']}")
        
        # Generate code for implementation
        print(f"\nImplementation code:")
        print("="*50)
        
        model = best_model['model']
        if model['type'] == 'constant':
            print(f"SIGMA_DECAY_PER_DAY = {model['decay_per_day']}")
            print(f"MAX_SIGMA_MULTIPLIER = {model['max_multiplier']}")
        
        elif model['type'] == 'logarithmic':
            print("# Replace the adjust_for_inactivity method with:")
            print(f"additional_sigma = {model['base_decay']} * days_since_last_match + {model['log_factor']} * np.log(1 + days_since_last_match)")
        
        elif model['type'] == 'exponential':
            print("# Replace the adjust_for_inactivity method with:")
            print(f"additional_sigma = {model['initial_decay']} * (np.exp({model['growth_rate']} * days_since_last_match / 30) - 1)")
        
        elif model['type'] == 'adaptive':
            print("# Implement adaptive decay based on player consistency")
            print(f"base_decay = {model['base_decay']}")
            print(f"consistency_factor = {model['consistency_factor']}")
            print("# consistency_multiplier = 1.0 + (player_cv * consistency_factor)")
            print("# additional_sigma = base_decay * days_since_last_match * consistency_multiplier")
        
        return best_model

def main():
    optimizer = SigmaDecayOptimizer()
    
    # Load and analyze the data
    optimizer.load_and_analyze_data()
    
    # Print activity analysis
    optimizer.print_activity_analysis()
    
    # Simulate different decay models
    results = optimizer.simulate_decay_models()
    
    # Recommend optimal parameters
    best_model = optimizer.recommend_optimal_parameters(results)
    
    print(f"\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("The analysis has identified the optimal sigma decay parameters for your IPSC ranking system.")
    print("Consider implementing the recommended model to improve rating accuracy and uncertainty management.")

if __name__ == "__main__":
    main()