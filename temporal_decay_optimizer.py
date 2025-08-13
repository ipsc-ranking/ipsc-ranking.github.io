#!/usr/bin/env python3

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from scipy import optimize
from scipy.stats import norm
import openskill
import openskill.models
from multiprocessing import Pool, cpu_count
import functools
from generate_all_rankings import IPSCRankingSystem, START_MU, START_SIGMA, PERCENTILE, OPENSKILL_MODEL

class TemporalDecayOptimizer:
    def __init__(self):
        self.match_data = []
        self.train_matches = []
        self.test_matches = []
        self.split_date = None
        
    def load_and_split_data(self, train_ratio=0.8):
        """Load matches and split temporally for validation"""
        print("Loading and splitting match data temporally...")
        
        # Load all matches
        match_files_location = './data/matches/'
        for filename in os.listdir(match_files_location):
            if filename.endswith('.json'):
                filepath = os.path.join(match_files_location, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        match_data = json.load(f)
                        
                        # Create combined_results from divisions if missing
                        if 'combined_results' not in match_data and 'divisions' in match_data:
                            combined_results = []
                            divisions = match_data.get('divisions', {})
                            
                            if isinstance(divisions, dict):
                                # IPSCResults format: divisions is a dict
                                for div_name, div_data in divisions.items():
                                    if isinstance(div_data, dict) and 'shooters' in div_data:
                                        combined_results.extend(div_data['shooters'])
                            elif isinstance(divisions, list):
                                # SSI format: divisions is a list
                                for division in divisions:
                                    if isinstance(division, dict) and 'shooters' in division:
                                        combined_results.extend(division['shooters'])
                            
                            match_data['combined_results'] = combined_results
                        
                        if 'combined_results' in match_data and len(match_data['combined_results']) > 0:
                            # Filter for handgun matches only
                            if self._is_handgun_match(match_data):
                                self.match_data.append(match_data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort by date
        self.match_data.sort(key=lambda x: datetime.fromisoformat(x['match_date'].replace('Z', '+00:00')))
        
        # Split temporally
        split_index = int(len(self.match_data) * train_ratio)
        self.train_matches = self.match_data[:split_index]
        self.test_matches = self.match_data[split_index:]
        self.split_date = datetime.fromisoformat(self.train_matches[-1]['match_date'].replace('Z', '+00:00'))
        
        print(f"Loaded {len(self.match_data)} total matches")
        print(f"Train: {len(self.train_matches)} matches (up to {self.split_date.date()})")
        print(f"Test: {len(self.test_matches)} matches (from {self.split_date.date()})")
        
        return len(self.train_matches), len(self.test_matches)
    
    def _is_handgun_match(self, match_data):
        """Check if a match is a handgun match based on division URLs or division names"""
        source = match_data.get('source', '')
        
        # Handle IPSCResults.org files (they have divisions as dict with division names)
        if source == 'ipscresults':
            divisions = match_data.get('divisions', {})
            if isinstance(divisions, dict):
                # IPSCResults.org structure: check division names
                handgun_divisions = [
                    'open', 'standard', 'production', 'production optics', 
                    'classic', 'revolver', 'limited', 'carry optics', 
                    'pcc', 'pistol caliber carbine'
                ]
                
                for div_name in divisions.keys():
                    if div_name.lower() in handgun_divisions:
                        return True
        
        # Handle SSI files (they have divisions as list with URL patterns)
        elif isinstance(match_data.get('divisions', []), list):
            divisions = match_data.get('divisions', [])
            
            # Check for handgun division URL patterns (SSI format)
            handgun_patterns = ['/hg1/', '/hg2/', '/hg3/', '/hg4/', '/hg5/', '/hg12/', '/hg18/', '/hg19/']
            
            for division in divisions:
                division_url = division.get('url', '')
                if any(pattern in division_url for pattern in handgun_patterns):
                    return True
        
        # Also check match title for explicit handgun indication
        match_title = match_data.get('match_title', '').lower()
        if 'handgun' in match_title and 'shotgun' not in match_title and 'rifle' not in match_title:
            return True
            
        return False
    
    def evaluate_decay_model_temporal(self, decay_model):
        """Evaluate a decay model using temporal validation"""
        print(f"Evaluating {decay_model['name']} with temporal validation...")
        
        # Create custom ranking system
        ranking_system = self._create_custom_ranking_system(decay_model)
        
        # Train on historical matches
        for match in self.train_matches:
            ranking_system.process_match(match)
        
        # Apply decay from split_date to each test match date
        test_predictions = []
        test_actuals = []
        
        for test_match in self.test_matches:
            test_date = datetime.fromisoformat(test_match['match_date'].replace('Z', '+00:00'))
            
            # Apply decay to split date
            ranking_system.adjust_for_inactivity(test_date)
            
            # Get predictions for this match
            predictions = self._get_match_predictions(ranking_system, test_match)
            if predictions:
                test_predictions.extend(predictions['predicted'])
                test_actuals.extend(predictions['actual'])
            
            # Process the match to update ratings for next iteration
            ranking_system.process_match(test_match)
        
        # Calculate prediction metrics
        if not test_predictions:
            return {
                'model': decay_model,
                'prediction_error': float('inf'),
                'log_likelihood': -float('inf'),
                'test_matches': 0,
                'test_predictions': 0
            }
        
        # Mean Absolute Error for placements
        mae = np.mean(np.abs(np.array(test_predictions) - np.array(test_actuals)))
        
        # Correlation between predicted and actual
        correlation = np.corrcoef(test_predictions, test_actuals)[0, 1] if len(test_predictions) > 1 else 0
        
        # Rank correlation (Spearman)
        from scipy.stats import spearmanr
        rank_correlation = spearmanr(test_predictions, test_actuals)[0] if len(test_predictions) > 1 else 0
        
        result = {
            'model': decay_model,
            'mae': mae,
            'correlation': correlation,
            'rank_correlation': rank_correlation,
            'test_matches': len(self.test_matches),
            'test_predictions': len(test_predictions),
            'prediction_score': -mae + correlation  # Higher is better
        }
        
        print(f"Completed {decay_model['name']}: MAE={mae:.3f}, Corr={correlation:.3f}")
        return result
    
    def _get_match_predictions(self, ranking_system, match_data):
        """Get predictions for a single match"""
        if 'combined_results' not in match_data:
            return None
        
        results_data = match_data['combined_results']
        if len(results_data) < 2:
            return None
        
        # Get current ratings for all participants
        participant_ratings = []
        actual_placements = []
        
        for result in results_data:
            from division_normalizer import normalize_division_name
            division = normalize_division_name(result.get('division', 'Unknown'))
            player_id = ranking_system.get_player_id(
                result['first_name'],
                result['last_name'], 
                result.get('region'),
                division
            )
            
            # Get or create player (but don't update matches_played yet)
            if player_id not in ranking_system.players:
                ranking_system.get_or_create_player(
                    result['first_name'],
                    result['last_name'],
                    result.get('region'),
                    division
                )
            
            current_rating = ranking_system.players[player_id]['rating']
            conservative_rating = ranking_system.calculate_conservative_rating(current_rating)
            participant_ratings.append(conservative_rating)
            
            # Get actual placement (1-indexed)
            actual_placements.append(result.get('placement', len(results_data)))
        
        # Predict placements based on conservative ratings (higher rating = better placement)
        rating_indices = list(enumerate(participant_ratings))
        rating_indices.sort(key=lambda x: x[1], reverse=True)  # Sort by rating, high to low
        
        predicted_placements = [0] * len(participant_ratings)
        for rank, (original_index, _) in enumerate(rating_indices):
            predicted_placements[original_index] = rank + 1  # 1-indexed
        
        return {
            'predicted': predicted_placements,
            'actual': actual_placements
        }
    
    def _create_custom_ranking_system(self, decay_model):
        """Create a ranking system with custom decay model"""
        class CustomTemporalRankingSystem(IPSCRankingSystem):
            def __init__(self, decay_model):
                super().__init__()
                self.decay_model = decay_model
            
            def adjust_for_inactivity(self, current_date):
                """Custom inactivity adjustment based on model type"""
                import math
                for player_id, player_data in self.players.items():
                    if player_id in self.player_last_match:
                        days_since_last_match = (current_date - self.player_last_match[player_id]).days
                        if days_since_last_match > 0:
                            current_rating = player_data['rating']
                            
                            # Calculate decay based on model type
                            if self.decay_model['type'] == 'constant':
                                additional_sigma = self.decay_model['decay_per_day'] * days_since_last_match
                            
                            elif self.decay_model['type'] == 'sqrt':
                                # Square root decay: sigma + decay_rate * sqrt(days_since)
                                additional_sigma = self.decay_model['decay_rate'] * math.sqrt(max(0, days_since_last_match))
                            
                            elif self.decay_model['type'] == 'exponential':
                                # Exponential decay: sigma_adjusted = max(current_sigma, START_SIGMA - (START_SIGMA - current_sigma) * exp(-decay_rate * days_inactive))
                                decay_factor = math.exp(-self.decay_model['decay_rate'] * days_since_last_match)
                                new_sigma = max(current_rating.sigma, START_SIGMA - (START_SIGMA - current_rating.sigma) * decay_factor)
                                additional_sigma = new_sigma - current_rating.sigma
                            
                            elif self.decay_model['type'] == 'constant_no_cap':
                                additional_sigma = self.decay_model['decay_per_day'] * days_since_last_match
                            
                            elif self.decay_model['type'] == 'confidence_based':
                                base_decay = self.decay_model['base_decay']
                                sigma_factor = self.decay_model['sigma_factor']
                                confidence_multiplier = sigma_factor * (START_SIGMA / current_rating.sigma)
                                additional_sigma = base_decay * days_since_last_match * confidence_multiplier
                            
                            else:
                                additional_sigma = 0.083 * days_since_last_match  # Fallback
                            
                            # Apply cap if specified
                            if self.decay_model['type'] not in ['constant_no_cap']:
                                max_sigma = START_SIGMA * self.decay_model.get('max_multiplier', 1.0)
                                new_sigma = min(current_rating.sigma + additional_sigma, max_sigma)
                            else:
                                new_sigma = current_rating.sigma + additional_sigma
                            
                            try:
                                player_data['rating'] = self.model.rating(
                                    mu=current_rating.mu,
                                    sigma=new_sigma
                                )
                            except Exception as e:
                                pass  # Skip if error
        
        return CustomTemporalRankingSystem(decay_model)
    
    def evaluate_percentile_temporal(self, decay_model, percentile):
        """Evaluate a specific percentile value using temporal validation"""
        print(f"Evaluating percentile {percentile} with {decay_model['name']}...")
        
        # Create custom ranking system with specific percentile
        ranking_system = self._create_custom_percentile_ranking_system(decay_model, percentile)
        
        # Train on historical matches
        for match in self.train_matches:
            ranking_system.process_match(match)
        
        # Apply decay from split_date to each test match date
        test_predictions = []
        test_actuals = []
        
        for test_match in self.test_matches:
            test_date = datetime.fromisoformat(test_match['match_date'].replace('Z', '+00:00'))
            
            # Apply decay to split date
            ranking_system.adjust_for_inactivity(test_date)
            
            # Get predictions for this match
            predictions = self._get_match_predictions(ranking_system, test_match)
            if predictions:
                test_predictions.extend(predictions['predicted'])
                test_actuals.extend(predictions['actual'])
            
            # Process the match to update ratings for next iteration
            ranking_system.process_match(test_match)
        
        # Calculate prediction metrics
        if not test_predictions:
            return {
                'percentile': percentile,
                'prediction_error': float('inf'),
                'log_likelihood': -float('inf'),
                'test_matches': 0,
                'test_predictions': 0
            }
        
        # Mean Absolute Error for placements
        mae = np.mean(np.abs(np.array(test_predictions) - np.array(test_actuals)))
        
        # Correlation between predicted and actual
        correlation = np.corrcoef(test_predictions, test_actuals)[0, 1] if len(test_predictions) > 1 else 0
        
        # Rank correlation (Spearman)
        from scipy.stats import spearmanr
        rank_correlation = spearmanr(test_predictions, test_actuals)[0] if len(test_predictions) > 1 else 0
        
        result = {
            'percentile': percentile,
            'mae': mae,
            'correlation': correlation,
            'rank_correlation': rank_correlation,
            'test_matches': len(self.test_matches),
            'test_predictions': len(test_predictions),
            'prediction_score': -mae + correlation  # Higher is better
        }
        
        print(f"Completed percentile {percentile}: MAE={mae:.3f}, Corr={correlation:.3f}")
        return result
    
    def _create_custom_percentile_ranking_system(self, decay_model, percentile):
        """Create a ranking system with custom decay model and percentile"""
        from scipy.stats import norm
        
        # Calculate START_SIGMA based on percentile
        z_score = abs(norm.ppf(percentile / 100.0))
        custom_start_sigma = START_MU / z_score
        
        class CustomPercentileRankingSystem(IPSCRankingSystem):
            def __init__(self, decay_model, percentile, custom_start_sigma):
                super().__init__()
                self.decay_model = decay_model
                self.percentile = percentile
                self.custom_start_sigma = custom_start_sigma
                
                # Override the model with custom START_SIGMA
                self.model = OPENSKILL_MODEL(
                    mu=START_MU,
                    sigma=custom_start_sigma,
                    beta=START_MU/12,
                    tau=START_MU/300,
                )
            
            def get_or_create_player(self, first_name, last_name, region, division=None, alias=None):
                """Override to use custom START_SIGMA"""
                player_id = self.get_player_id(first_name, last_name, region, division)
                
                if player_id not in self.players:
                    # Store normalized names for display
                    from name_normalizer import normalize_name
                    normalized_first = normalize_name(first_name) if first_name else ""
                    normalized_last = normalize_name(last_name) if last_name else ""
                    
                    self.players[player_id] = {
                        'rating': self.model.rating(name=player_id),
                        'first_name': normalized_first,
                        'last_name': normalized_last,
                        'alias': alias,
                        'region': region,
                        'matches_played': 0
                    }
                
                return player_id
            
            def calculate_conservative_rating(self, rating, percentile_override=None):
                """Override to use custom percentile"""
                target_percentile = percentile_override or self.percentile
                from scipy.stats import norm
                alpha = 1
                target = 0
                z = abs(norm.ppf(target_percentile / 100.0))
                return rating.ordinal(z=z, alpha=alpha, target=target)
            
            def adjust_for_inactivity(self, current_date):
                """Custom inactivity adjustment based on model type"""
                import math
                for player_id, player_data in self.players.items():
                    if player_id in self.player_last_match:
                        days_since_last_match = (current_date - self.player_last_match[player_id]).days
                        if days_since_last_match > 0:
                            current_rating = player_data['rating']
                            
                            # Calculate decay based on model type
                            if self.decay_model['type'] == 'constant':
                                additional_sigma = self.decay_model['decay_per_day'] * days_since_last_match
                            
                            elif self.decay_model['type'] == 'sqrt':
                                # Square root decay: sigma + decay_rate * sqrt(days_since)
                                additional_sigma = self.decay_model['decay_rate'] * math.sqrt(max(0, days_since_last_match))
                            
                            elif self.decay_model['type'] == 'exponential':
                                # Exponential decay: sigma_adjusted = max(current_sigma, START_SIGMA - (START_SIGMA - current_sigma) * exp(-decay_rate * days_inactive))
                                decay_factor = math.exp(-self.decay_model['decay_rate'] * days_since_last_match)
                                new_sigma = max(current_rating.sigma, START_SIGMA - (START_SIGMA - current_rating.sigma) * decay_factor)
                                additional_sigma = new_sigma - current_rating.sigma
                            
                            elif self.decay_model['type'] == 'constant_no_cap':
                                additional_sigma = self.decay_model['decay_per_day'] * days_since_last_match
                            
                            elif self.decay_model['type'] == 'confidence_based':
                                base_decay = self.decay_model['base_decay']
                                sigma_factor = self.decay_model['sigma_factor']
                                confidence_multiplier = sigma_factor * (self.custom_start_sigma / current_rating.sigma)
                                additional_sigma = base_decay * days_since_last_match * confidence_multiplier
                            
                            else:
                                additional_sigma = 0.083 * days_since_last_match  # Fallback
                            
                            # Apply cap if specified (using custom START_SIGMA)
                            if self.decay_model['type'] not in ['constant_no_cap']:
                                max_sigma = self.custom_start_sigma * self.decay_model.get('max_multiplier', 1.0)
                                new_sigma = min(current_rating.sigma + additional_sigma, max_sigma)
                            else:
                                new_sigma = current_rating.sigma + additional_sigma
                            
                            try:
                                player_data['rating'] = self.model.rating(
                                    mu=current_rating.mu,
                                    sigma=new_sigma
                                )
                            except Exception as e:
                                pass  # Skip if error
        
        return CustomPercentileRankingSystem(decay_model, percentile, custom_start_sigma)
    
    def optimize_decay_models(self):
        """Test exponential decay models vs current constant decay"""
        print("\n" + "="*80)
        print("TEMPORAL VALIDATION: EXPONENTIAL vs CONSTANT DECAY")
        print("="*80)
        
        decay_models = []
        
        # Test exponential decay models (most realistic)
        # Lower rates for exponential since it approaches asymptote
        for decay_rate in [0.002, 0.005]:
            decay_models.append({
                'name': f'Exp_{decay_rate:.3f}',
                'type': 'exponential',
                'decay_rate': decay_rate,
                'max_multiplier': 1.0
            })
        
        # Add current constant decay for comparison
        decay_models.append({
            'name': 'Constant_0.150',
            'type': 'constant', 
            'decay_per_day': 0.150,
            'max_multiplier': 1.0
        })
        
        print(f"Testing {len(decay_models)} decay models (exponential vs constant)...")
        
        results = []
        for model in decay_models:
            result = self.evaluate_decay_model_temporal(model)
            results.append(result)
        
        # Sort by prediction score (higher is better)
        results.sort(key=lambda x: x['prediction_score'], reverse=True)
        
        # Print results with time analysis
        self._print_exp_results(results)
        
        return results
    
    def optimize_percentile(self, best_decay_model=None):
        """Test different percentile values with temporal validation"""
        print("\n" + "="*80)
        print("TEMPORAL VALIDATION OF PERCENTILE VALUES")
        print("="*80)
        
        # Use the best decay model if provided, otherwise use optimal constant model
        if best_decay_model is None:
            best_decay_model = {
                'name': 'Constant_0.150_Capped',
                'type': 'constant',
                'decay_per_day': 0.150,
                'max_multiplier': 1.0
            }
        
        # Test different percentile values
        percentiles_to_test = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]
        
        print(f"Testing {len(percentiles_to_test)} percentile values using temporal validation...")
        print(f"Using decay model: {best_decay_model['name']}")
        
        results = []
        for percentile in percentiles_to_test:
            print(f"\nEvaluating percentile {percentile}...")
            result = self.evaluate_percentile_temporal(best_decay_model, percentile)
            results.append(result)
        
        # Sort by prediction score (higher is better)
        results.sort(key=lambda x: x['prediction_score'], reverse=True)
        
        # Print results
        self._print_percentile_results(results)
        
        return results
    
    def _print_temporal_results(self, results):
        """Print temporal validation results"""
        print("\n" + "="*100)
        print("TEMPORAL VALIDATION RESULTS (Based on Actual Prediction Accuracy)")
        print("="*100)
        print(f"{'Rank':<4} {'Model':<30} {'MAE':<8} {'Correlation':<11} {'Rank Corr':<10} {'Score':<8} {'Predictions':<11}")
        print("-" * 100)
        
        for i, result in enumerate(results):
            rank = "🏆" if i == 0 else f"{i+1:2d}"
            print(f"{rank} {result['model']['name']:<29} "
                  f"{result['mae']:<8.3f} "
                  f"{result['correlation']:<11.3f} "
                  f"{result['rank_correlation']:<10.3f} "
                  f"{result['prediction_score']:<8.3f} "
                  f"{result['test_predictions']:<11}")
        
        # Highlight best model
        best = results[0]
        print(f"\n🏆 BEST MODEL (Based on Actual Predictive Performance):")
        print(f"   Model: {best['model']['name']}")
        print(f"   Mean Absolute Error: {best['mae']:.3f} placements")
        print(f"   Correlation: {best['correlation']:.3f}")
        print(f"   Rank Correlation: {best['rank_correlation']:.3f}")
        print(f"   Tested on {best['test_predictions']} predictions from {best['test_matches']} matches")
        
        if best['model']['type'] == 'constant':
            print(f"   Recommended decay rate: {best['model']['decay_per_day']:.3f} per day")
        elif best['model']['type'] == 'constant_no_cap':
            print(f"   Recommended decay rate: {best['model']['decay_per_day']:.3f} per day (no cap)")
        elif best['model']['type'] == 'confidence_based':
            print(f"   Recommended base_decay: {best['model']['base_decay']:.3f}")
            print(f"   Recommended sigma_factor: {best['model']['sigma_factor']:.1f}")
    
    def _print_percentile_results(self, results):
        """Print percentile validation results"""
        print("\n" + "="*100)
        print("PERCENTILE VALIDATION RESULTS (Based on Actual Prediction Accuracy)")
        print("="*100)
        print(f"{'Rank':<4} {'Percentile':<10} {'MAE':<8} {'Correlation':<11} {'Rank Corr':<10} {'Score':<8} {'Predictions':<11}")
        print("-" * 100)
        
        for i, result in enumerate(results):
            rank = "🏆" if i == 0 else f"{i+1:2d}"
            print(f"{rank} {result['percentile']:<9} "
                  f"{result['mae']:<8.3f} "
                  f"{result['correlation']:<11.3f} "
                  f"{result['rank_correlation']:<10.3f} "
                  f"{result['prediction_score']:<8.3f} "
                  f"{result['test_predictions']:<11}")
        
        # Highlight best percentile
        best = results[0]
        print(f"\n🏆 BEST PERCENTILE (Based on Actual Predictive Performance):")
        print(f"   Percentile: {best['percentile']}%")
        print(f"   Mean Absolute Error: {best['mae']:.3f} placements")
        print(f"   Correlation: {best['correlation']:.3f}")
        print(f"   Rank Correlation: {best['rank_correlation']:.3f}")
        print(f"   Tested on {best['test_predictions']} predictions from {best['test_matches']} matches")
        print(f"\n   Current PERCENTILE = 80, Optimal PERCENTILE = {best['percentile']}")
        
        # Calculate START_SIGMA for the optimal percentile
        from scipy.stats import norm
        z_score = abs(norm.ppf(best['percentile'] / 100.0))
        optimal_start_sigma = START_MU / z_score
        print(f"   Current START_SIGMA ≈ {START_SIGMA:.2f}, Optimal START_SIGMA ≈ {optimal_start_sigma:.2f}")

    def _print_sqrt_results(self, results):
        """Print square root decay results with time analysis"""
        import math
        
        print("\n" + "="*120)
        print("SQUARE ROOT vs CONSTANT DECAY RESULTS")
        print("="*120)
        print(f"{'Rank':<4} {'Model':<20} {'MAE':<8} {'Correlation':<11} {'Score':<8} {'1 Year':<10} {'2 Years':<10} {'Time to Max':<12}")
        print("-" * 120)
        
        for i, result in enumerate(results):
            rank = "🏆" if i == 0 else f"{i+1:2d}"
            model = result['model']
            
            # Calculate sigma after 1 year and 2 years
            initial_sigma = START_SIGMA * 0.5  # Assume some experience
            
            if model['type'] == 'sqrt':
                sigma_1yr = min(START_SIGMA, initial_sigma + model['decay_rate'] * math.sqrt(365))
                sigma_2yr = min(START_SIGMA, initial_sigma + model['decay_rate'] * math.sqrt(730))
                # Time to reach max: solve START_SIGMA = initial_sigma + decay_rate * sqrt(days)
                # sqrt(days) = (START_SIGMA - initial_sigma) / decay_rate
                # days = ((START_SIGMA - initial_sigma) / decay_rate)^2
                days_to_max = ((START_SIGMA - initial_sigma) / model['decay_rate']) ** 2
                years_to_max = days_to_max / 365
            else:  # constant
                sigma_1yr = min(START_SIGMA, initial_sigma + model['decay_per_day'] * 365)
                sigma_2yr = min(START_SIGMA, initial_sigma + model['decay_per_day'] * 730)
                days_to_max = (START_SIGMA - initial_sigma) / model['decay_per_day']
                years_to_max = days_to_max / 365
            
            # Convert to conservative ratings
            z_score = 0.842  # 80th percentile
            conservative_1yr = START_MU - z_score * sigma_1yr
            conservative_2yr = START_MU - z_score * sigma_2yr
            
            time_str = f"{years_to_max:.1f}y" if years_to_max < 10 else "10y+"
            
            print(f"{rank} {model['name']:<19} "
                  f"{result['mae']:<8.3f} "
                  f"{result['correlation']:<11.3f} "
                  f"{result['prediction_score']:<8.3f} "
                  f"{conservative_1yr:<10.1f} "
                  f"{conservative_2yr:<10.1f} "
                  f"{time_str:<12}")
        
        best = results[0]
        print(f"\n🏆 BEST MODEL: {best['model']['name']}")
        print(f"   MAE: {best['mae']:.3f}, Correlation: {best['correlation']:.3f}")
        
        if best['model']['type'] == 'sqrt':
            print(f"   Square root decay with rate: {best['model']['decay_rate']:.1f}")
            print(f"   Formula: sigma = min(sigma + {best['model']['decay_rate']:.1f} * sqrt(days_since), START_SIGMA)")
        else:
            print(f"   Linear decay with rate: {best['model']['decay_per_day']:.3f} per day")

    def _print_exp_results(self, results):
        """Print exponential decay results with time analysis"""
        import math
        
        print("\n" + "="*130)
        print("EXPONENTIAL vs CONSTANT DECAY RESULTS")
        print("="*130)
        print(f"{'Rank':<4} {'Model':<15} {'MAE':<8} {'Correlation':<11} {'Score':<8} {'1 Year':<10} {'2 Years':<10} {'5 Years':<10} {'Half-life':<10}")
        print("-" * 130)
        
        for i, result in enumerate(results):
            rank = "🏆" if i == 0 else f"{i+1:2d}"
            model = result['model']
            
            # Calculate sigma after different time periods
            initial_sigma = START_SIGMA * 0.5  # Assume some experience
            
            if model['type'] == 'exponential':
                # sigma_adjusted = max(current_sigma, START_SIGMA - (START_SIGMA - current_sigma) * exp(-decay_rate * days))
                def exp_sigma(days):
                    decay_factor = math.exp(-model['decay_rate'] * days)
                    return max(initial_sigma, START_SIGMA - (START_SIGMA - initial_sigma) * decay_factor)
                
                sigma_1yr = exp_sigma(365)
                sigma_2yr = exp_sigma(730)
                sigma_5yr = exp_sigma(1825)
                
                # Half-life: time for half the remaining uncertainty to decay
                # 0.5 = exp(-decay_rate * t_half)
                # ln(0.5) = -decay_rate * t_half
                # t_half = -ln(0.5) / decay_rate = ln(2) / decay_rate
                half_life_days = math.log(2) / model['decay_rate']
                half_life_years = half_life_days / 365
                
            else:  # constant
                sigma_1yr = min(START_SIGMA, initial_sigma + model['decay_per_day'] * 365)
                sigma_2yr = min(START_SIGMA, initial_sigma + model['decay_per_day'] * 730)
                sigma_5yr = min(START_SIGMA, initial_sigma + model['decay_per_day'] * 1825)
                
                # Time to reach max uncertainty
                days_to_max = (START_SIGMA - initial_sigma) / model['decay_per_day']
                half_life_years = days_to_max / 365 / 2  # Rough approximation
            
            # Convert to conservative ratings
            z_score = 0.842  # 80th percentile
            conservative_1yr = START_MU - z_score * sigma_1yr
            conservative_2yr = START_MU - z_score * sigma_2yr
            conservative_5yr = START_MU - z_score * sigma_5yr
            
            half_life_str = f"{half_life_years:.1f}y" if half_life_years < 10 else "10y+"
            
            print(f"{rank} {model['name']:<14} "
                  f"{result['mae']:<8.3f} "
                  f"{result['correlation']:<11.3f} "
                  f"{result['prediction_score']:<8.3f} "
                  f"{conservative_1yr:<10.1f} "
                  f"{conservative_2yr:<10.1f} "
                  f"{conservative_5yr:<10.1f} "
                  f"{half_life_str:<10}")
        
        best = results[0]
        print(f"\n🏆 BEST MODEL: {best['model']['name']}")
        print(f"   MAE: {best['mae']:.3f}, Correlation: {best['correlation']:.3f}")
        
        if best['model']['type'] == 'exponential':
            print(f"   Exponential decay with rate: {best['model']['decay_rate']:.3f}")
            print(f"   Formula: sigma = max(current_sigma, START_SIGMA - (START_SIGMA - current_sigma) * exp(-{best['model']['decay_rate']:.3f} * days_inactive))")
            
            # Calculate half-life
            half_life_days = math.log(2) / best['model']['decay_rate']
            print(f"   Half-life: {half_life_days:.0f} days ({half_life_days/30:.1f} months)")
        else:
            print(f"   Linear decay with rate: {best['model']['decay_per_day']:.3f} per day")

def main():
    optimizer = TemporalDecayOptimizer()
    
    # Load and split data
    train_count, test_count = optimizer.load_and_split_data(train_ratio=0.8)
    
    if test_count == 0:
        print("No test matches available!")
        return
    
    # Run temporal validation for decay models only
    decay_results = optimizer.optimize_decay_models()
    
    print(f"\n" + "="*80)
    print("TEMPORAL VALIDATION COMPLETE")
    print("="*80)
    print("This analysis shows which decay model actually predicts future match outcomes best!")
    print("Unlike rating separation, this measures real predictive performance.")
    print("Percentile is kept at 80% as requested.")
    
    if decay_results:
        best_decay = decay_results[0]['model']
        print(f"\n🎯 OPTIMAL DECAY CONFIGURATION:")
        print(f"   Decay Model: {best_decay['name']}")
        print(f"   Percentile: 80% (unchanged)")
        print(f"   MAE: {decay_results[0]['mae']:.3f}")
        print(f"   Correlation: {decay_results[0]['correlation']:.3f}")
        
        if best_decay['type'] == 'constant':
            print(f"\n   Current decay_per_day: 0.150")
            print(f"   Optimal decay_per_day: {best_decay['decay_per_day']:.3f}")
            if abs(best_decay['decay_per_day'] - 0.150) > 0.001:
                print(f"   ⚠️  Consider updating generate_all_rankings.py line ~179")
            else:
                print(f"   ✅ Current value is already optimal!")

if __name__ == "__main__":
    main()