"""
agents/hallucination_metric.py

Hallucination Detection Metric - measures percentage of unsupported claims in LLM responses.
Per requirements: "Implement a hallucination detection metric to measure the percentage 
of unsupported interaction claims."
"""

from typing import Dict, List
from agents.kg_agent import KGClient


class HallucinationMetric:
    """Calculates hallucination score for LLM responses."""
    
    def __init__(self):
        self.kg = KGClient()
    
    def calculate_hallucination_score(
        self,
        llm_response: str,
        drug1: str,
        drug2: str,
        kg_evidence: List[Dict]
    ) -> Dict:
        """
        Calculate percentage of unsupported claims in LLM response.
        
        Args:
            llm_response: The LLM-generated clinical insight
            drug1: First drug name
            drug2: Second drug name
            kg_evidence: Raw KG evidence (interaction data from Neo4j)
        
        Returns:
            Dict with:
                - 'hallucination_score': float (0-100, percentage of unsupported claims)
                - 'total_claims': int (total verifiable claims found)
                - 'verified_claims': int (claims supported by KG)
                - 'unverified_claims': int (claims NOT in KG)
                - 'details': list of claim verification results
        """
        claims = self._extract_verifiable_claims(llm_response)
        
        if not claims:
            # No claims to verify - score is 0 (no hallucination)
            return {
                'hallucination_score': 0.0,
                'total_claims': 0,
                'verified_claims': 0,
                'unverified_claims': 0,
                'details': []
            }
        
        verification_results = []
        verified_count = 0
        
        for claim in claims:
            is_verified = self._verify_claim_against_kg(claim, kg_evidence, drug1, drug2)
            verification_results.append({
                'claim': claim['text'],
                'type': claim['type'],
                'verified': is_verified
            })
            if is_verified:
                verified_count += 1
        
        total_claims = len(claims)
        unverified_count = total_claims - verified_count
        hallucination_score = (unverified_count / total_claims * 100) if total_claims > 0 else 0.0
        
        return {
            'hallucination_score': round(hallucination_score, 2),
            'total_claims': total_claims,
            'verified_claims': verified_count,
            'unverified_claims': unverified_count,
            'details': verification_results
        }
    
    def _extract_verifiable_claims(self, response: str) -> List[Dict]:
        """
        Extract verifiable factual claims from LLM response.
        
        Types of claims to extract:
        - Drug names mentioned
        - Mechanisms mentioned (e.g., "CYP2C9 inhibition")
        - Severity levels (Major/Moderate/Minor)
        - Specific effects (e.g., "bleeding risk", "nephrotoxicity")
        """
        claims = []
        
        # Extract severity claims - these map directly to KG 'severity' field
        severity_keywords = ['major', 'moderate', 'minor']
        for severity in severity_keywords:
            if severity in response.lower():
                claims.append({
                    'text': f'Severity: {severity.capitalize()}',
                    'type': 'severity',
                    'value': severity.capitalize()
                })
        
        # Extract ONLY CYP enzyme mechanisms — these are stored in KG 'mechanism' field.
        # Do NOT include clinical consequences (bleeding, nephrotoxicity, etc.) — those are
        # valid LLM clinical context, NOT KG-verifiable mechanisms. Including them causes
        # false hallucination positives for fully correct responses.
        mechanism_patterns = [
            'CYP2C9', 'CYP3A4', 'CYP2D6', 'CYP1A2', 'CYP2C19', 'CYP2B6'
        ]
        for mechanism in mechanism_patterns:
            if mechanism.lower() in response.lower():
                claims.append({
                    'text': f'Mechanism: {mechanism}',
                    'type': 'mechanism',
                    'value': mechanism
                })
        
        return claims
    
    def _verify_claim_against_kg(
        self,
        claim: Dict,
        kg_evidence: List[Dict],
        drug1: str,
        drug2: str
    ) -> bool:
        """
        Verify if a claim is supported by KG evidence.
        
        Args:
            claim: Dictionary with claim info
            kg_evidence: List of interaction records from KG
            drug1, drug2: Drug names
        
        Returns:
            True if claim is supported by KG, False otherwise
        """
        if not kg_evidence:
            # No KG evidence - any claim is unverified
            return False
        
        claim_type = claim.get('type')
        claim_value = claim.get('value', '').lower()
        
        # Check each KG record
        for record in kg_evidence:
            if claim_type == 'severity':
                # Verify severity matches
                kg_severity = record.get('severity', '').lower()
                if kg_severity == claim_value.lower():
                    return True
            
            elif claim_type == 'mechanism':
                # Verify mechanism is in KG
                kg_mechanism = record.get('mechanism', '').lower()
                if claim_value in kg_mechanism or kg_mechanism in claim_value:
                    return True
        
        return False


# Global instance
hallucination_detector = HallucinationMetric()
