"""
agents/ingredient_analyzer.py

Analyzes ingredient-level interactions and calculates quantitative contributions.
Shows which specific ingredients from Drug A interact with ingredients from Drug B,
and how much each interaction contributes to the overall DDI effect.
"""

import math
from typing import List, Dict, Tuple
from agents.kg_agent import KGClient, CY_DRUG_INGREDIENTS, CY_INGREDIENT_INTERACTIONS


class IngredientAnalyzer:
    """Analyzes ingredient-level interactions with quantitative contribution analysis."""
    
    def __init__(self):
        """Initialize with KG client."""
        self.kg = KGClient()
    
    def get_drug_composition(self, drug_name: str) -> List[Dict]:
        """
        Get all ingredients for a drug with quantities and percentages.
        Separates active and inactive ingredients.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            List of ingredients with: {
                'ingredient': str,
                'quantity_mg': float,
                'percentage': float,
                'role': str,
                'type': str,
                'display_category': str  # 'Active' or 'Inactive'
            }
        """
        ingredients = self.kg.query(CY_DRUG_INGREDIENTS, {"drug": drug_name})
        
        if not ingredients:
            return []
        
        # Validate ingredient existence (NEW) - prevent hallucination
        validated_ingredients = []
        for ing in ingredients:
            if ing.get('ingredient'):  # Ensure ingredient name exists
                validated_ingredients.append(ing)
        
        # Calculate total quantity across ALL ingredients (ENHANCED)
        total_mg = sum(float(ing.get('quantity_mg', 0)) for ing in validated_ingredients)
        
        # Add percentage and categorize (ENHANCED)
        for ing in validated_ingredients:
            qty = float(ing.get('quantity_mg', 0))
            ing['percentage'] = (qty / total_mg * 100) if total_mg > 0 else 0
            
            # Explicit type/role categorization (NEW)
            ing_type = ing.get('type', ing.get('role', 'Unknown'))
            ing['display_category'] = 'Active' if ing_type == 'Active' else 'Inactive'
        
        # Sort by category (Active first) then by quantity
        validated_ingredients.sort(
            key=lambda x: (x['display_category'] != 'Active', -x.get('quantity_mg', 0))
        )
        
        return validated_ingredients
    
    def get_ingredient_interactions(self, drug1: str, drug2: str) -> List[Dict]:
        """
        Get all ingredient-ingredient interactions between two drugs.
        
        Args:
            drug1: First drug name
            drug2: Second drug name
            
        Returns:
            List of interactions with mechanism, severity, ingredients
        """
        interactions = self.kg.query(CY_INGREDIENT_INTERACTIONS, {
            "drug1": drug1,
            "drug2": drug2
        })
        
        return interactions
    
    def calculate_contribution_weight(
        self,
        interaction: Dict,
        drug1_composition: List[Dict],
        drug2_composition: List[Dict]
    ) -> float:
        """
        Calculate weight for an ingredient-ingredient interaction.
        
        Weight = quantity_factor * 0.3 + severity_factor * 0.5 + mechanism_factor * 0.2
        
        Args:
            interaction: Ingredient interaction dict
            drug1_composition: List of drug1 ingredients
            drug2_composition: List of drug2 ingredients
            
        Returns:
            Weight value (0-1 scale)
        """
        # Get ingredient quantities
        ing_a = interaction.get('ingredient_a', '')
        ing_b = interaction.get('ingredient_b', '')
        
        qty_a = 0
        qty_b = 0
        
        for ing in drug1_composition:
            if ing.get('ingredient', '') == ing_a:
                qty_a = float(ing.get('quantity_mg', 0))
                break
        
        for ing in drug2_composition:
            if ing.get('ingredient', '') == ing_b:
                qty_b = float(ing.get('quantity_mg', 0))
                break
        
        # Quantity factor (geometric mean, normalized)
        if qty_a > 0 and qty_b > 0:
            quantity_factor = min(math.sqrt(qty_a * qty_b) / 1000, 1.0)
        else:
            quantity_factor = 0.1  # Small baseline for interactions with unknown quantities
        
        # Severity factor
        severity = interaction.get('severity', 'Minor')
        severity_map = {
            'Major': 1.0,
            'Moderate': 0.6,
            'Minor': 0.3
        }
        severity_factor = severity_map.get(severity, 0.5)
        
        # Mechanism factor (CYP interactions are typically more important)
        mechanism = interaction.get('mechanism', '')
        mechanism_factor = 1.0 if 'CYP' in mechanism else 0.7
        
        # Weighted sum
        weight = (
            quantity_factor * 0.3 +
            severity_factor * 0.5 +
            mechanism_factor * 0.2
        )
        
        return weight
    
    def calculate_contributions(
        self,
        interactions: List[Dict],
        drug1_composition: List[Dict],
        drug2_composition: List[Dict]
    ) -> List[Tuple[Dict, float]]:
        """
        Calculate percentage contribution for each ingredient interaction.
        
        Args:
            interactions: List of ingredient-ingredient interactions
            drug1_composition: Drug 1 ingredients
            drug2_composition: Drug 2 ingredients
            
        Returns:
            List of (interaction, contribution_percentage) tuples
        """
        if not interactions:
            return []
        
        # Calculate weights
        weights = []
        for interaction in interactions:
            weight = self.calculate_contribution_weight(
                interaction,
                drug1_composition,
                drug2_composition
            )
            weights.append(weight)
        
        # Normalize to percentages
        total_weight = sum(weights)
        if total_weight == 0:
            # Equal distribution if no weights
            contributions = [100.0 / len(interactions)] * len(interactions)
        else:
            contributions = [(w / total_weight) * 100 for w in weights]
        
        # Combine and sort by contribution (highest first)
        results = list(zip(interactions, contributions))
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def categorize_by_contribution(
        self,
        interaction_contributions: List[Tuple[Dict, float]]
    ) -> Dict[str, List[Tuple[Dict, float]]]:
        """
        Categorize interactions by contribution level.
        
        Args:
            interaction_contributions: List of (interaction, percentage) tuples
            
        Returns:
            Dict with 'primary', 'secondary', 'minor' keys
        """
        primary = []      # >= 50%
        secondary = []    # 20-49%
        minor = []        # < 20%
        
        for interaction, pct in interaction_contributions:
            if pct >= 50:
                primary.append((interaction, pct))
            elif pct >= 20:
                secondary.append((interaction, pct))
            else:
                minor.append((interaction, pct))
        
        return {
            'primary': primary,
            'secondary': secondary,
            'minor': minor
        }
    
    def analyze_drug_interaction(self, drug1: str, drug2: str) -> Dict:
        """
        Complete ingredient-level analysis for a drug-drug interaction.
        
        Args:
            drug1: First drug name
            drug2: Second drug name
            
        Returns:
            Dict with:
                - drug1_composition: List of ingredients
                - drug2_composition: List of ingredients
                - interactions: Raw ingredient interactions
                - contributions: Categorized contributions
                - total_interactions: Count
        """
        # Get compositions
        drug1_comp = self.get_drug_composition(drug1)
        drug2_comp = self.get_drug_composition(drug2)
        
        # Get ingredient interactions
        interactions = self.get_ingredient_interactions(drug1, drug2)
        
        if not interactions:
            return {
                'drug1_composition': drug1_comp,
                'drug2_composition': drug2_comp,
                'interactions': [],
                'contributions': {'primary': [], 'secondary': [], 'minor': []},
                'total_interactions': 0
            }
        
        # Calculate contributions
        contributions_list = self.calculate_contributions(
            interactions,
            drug1_comp,
            drug2_comp
        )
        
        # Categorize
        categorized = self.categorize_by_contribution(contributions_list)
        
        return {
            'drug1_composition': drug1_comp,
            'drug2_composition': drug2_comp,
            'interactions': interactions,
            'contributions': categorized,
            'total_interactions': len(interactions)
        }
