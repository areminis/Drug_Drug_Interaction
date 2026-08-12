"""
agents/verification_agent.py

Simple verification agent (MVP) that validates LLM-generated clinical insights
against the Neo4j knowledge graph to prevent hallucinations.

This is the MVP version - focuses on core verification with simple badges.
"""

import re
from typing import Dict, List, Tuple
from agents.kg_agent import KGClient, CY_DDI


class VerificationAgent:
    """Simple verification agent for LLM output validation (MVP)."""
    
    def __init__(self):
        """Initialize with KG client."""
        self.kg = KGClient()
    
    def extract_key_claims(self, llm_output: str, context: Dict) -> Dict:
        """
        Extract key verifiable claims from LLM output.
        
        MVP version extracts:
        - Mechanisms mentioned (CYP2C9, CYP3A4, etc.)
        - Severity mentioned (Major, Moderate, Minor)
        - Drug names
        
        Args:
            llm_output: The LLM-generated clinical insight text
            context: Context dict with 'drug1', 'drug2', 'kg_rows'
            
        Returns:
            Dict with extracted claims
        """
        claims = {
            'mechanisms': [],
            'severity': None,
            'drugs': [],
            'effects': []
        }
        
        # Extract mechanisms (CYP enzymes, common mechanisms)
        mechanism_patterns = [
            r'CYP\d[A-Z]\d+',  # CYP2C9, CYP3A4, etc.
            r'protein binding',
            r'renal clearance',
            r'nephrotoxicity',
            r'hepatotoxicity',
            r'ototoxicity',
            r'bleeding',
            r'antiplatelet',
            r'anticoagulant',
        ]
        
        for pattern in mechanism_patterns:
            matches = re.findall(pattern, llm_output, re.IGNORECASE)
            claims['mechanisms'].extend([m.upper() for m in matches])
        
        # Remove duplicates
        claims['mechanisms'] = list(set(claims['mechanisms']))
        
        # Extract severity
        severity_match = re.search(r'\b(major|moderate|minor)\b', llm_output, re.IGNORECASE)
        if severity_match:
            claims['severity'] = severity_match.group(1).capitalize()
        
        # Extract drug names from context
        claims['drugs'] = [context.get('drug1', ''), context.get('drug2', '')]
        claims['drugs'] = [d for d in claims['drugs'] if d]  # Remove empty
        
        # Extract effects (bleeding, toxicity, etc.)
        effect_patterns = [
            r'bleeding',
            r'toxicity',
            r'damage',
            r'failure',
            r'risk',
        ]
        
        for pattern in effect_patterns:
            if re.search(pattern, llm_output, re.IGNORECASE):
                claims['effects'].append(pattern)
        
        return claims
    
    def verify_against_kg(self, claims: Dict, context: Dict) -> Dict:
        """
        Verify extracted claims against the knowledge graph.
        
        Args:
            claims: Extracted claims dict
            context: Context with drug names and KG rows
            
        Returns:
            Dict with verification results
        """
        verification = {
            'drug_pair_verified': False,
            'mechanism_verified': False,
            'severity_verified': False,
            'overall_status': 'unverified',
            'details': []
        }
        
        drug1 = context.get('drug1', '')
        drug2 = context.get('drug2', '')
        kg_rows = context.get('kg_rows', [])
        
        # Verify drug pair exists in KG
        if kg_rows:
            verification['drug_pair_verified'] = True
            verification['details'].append(f"✅ Drug pair verified: {drug1}-{drug2} found in knowledge graph")
        else:
            verification['details'].append(f"⚠️ Drug pair not found: {drug1}-{drug2} not in knowledge graph")
        
        # Verify mechanism
        if claims['mechanisms'] and kg_rows:
            kg_mechanisms = [row.get('mechanism', '') for row in kg_rows]
            kg_mechanisms_upper = [m.upper() for m in kg_mechanisms]
            
            # Check if any extracted mechanism matches KG
            for claimed_mechanism in claims['mechanisms']:
                # Flexible matching (substring match)
                for kg_mech in kg_mechanisms_upper:
                    if claimed_mechanism in kg_mech or kg_mech in claimed_mechanism:
                        verification['mechanism_verified'] = True
                        verification['details'].append(f"✅ Mechanism verified: {claimed_mechanism} matches knowledge graph")
                        break
                
                if verification['mechanism_verified']:
                    break
            
            if not verification['mechanism_verified'] and claims['mechanisms']:
                verification['details'].append(f"⚠️ Mechanism not verified: {', '.join(claims['mechanisms'])} not found in KG")
        
        # Verify severity
        if claims['severity'] and kg_rows:
            kg_severities = [row.get('severity', '') for row in kg_rows]
            
            if claims['severity'] in kg_severities:
                verification['severity_verified'] = True
                verification['details'].append(f"✅ Severity verified: {claims['severity']} matches knowledge graph")
            else:
                verification['details'].append(f"⚠️ Severity mismatch: LLM says {claims['severity']}, KG shows {', '.join(kg_severities)}")
        
        # Determine overall status
        verified_count = sum([
            verification['drug_pair_verified'],
            verification['mechanism_verified'],
            verification['severity_verified']
        ])
        
        if verified_count == 3:
            verification['overall_status'] = 'verified'
        elif verified_count >= 2:
            verification['overall_status'] = 'mostly_verified'
        elif verified_count >= 1:
            verification['overall_status'] = 'partially_verified'
        else:
            verification['overall_status'] = 'unverified'
        
        return verification
    
    def format_verified_output(self, llm_output: str, verification: Dict) -> str:
        """
        Format LLM output with verification status.
        
        Args:
            llm_output: Original LLM clinical insight
            verification: Verification results dict
            
        Returns:
            Formatted output with verification badges
        """
        # Status badge
        status_badges = {
            'verified': '✅ Verified',
            'mostly_verified': '⚠️ Mostly Verified',
            'partially_verified': '⚠️ Partially Verified',
            'unverified': '❌ Unverified'
        }
        
        status = verification['overall_status']
        badge = status_badges.get(status, '⚠️ Unknown')
        
        # Build output
        output = [
            f"🧠 Clinical Insight: {badge}\n",
            llm_output,
            "\n" + "━" * 70,
            "📊 Verification Report:",
        ]
        
        # Add verification details
        for detail in verification['details']:
            output.append(f"   {detail}")
        
        output.append("━" * 70)
        
        return "\n".join(output)
    
    def verify_llm_output(
        self, 
        llm_output: str, 
        drug1: str, 
        drug2: str, 
        kg_rows: List[Dict]
    ) -> str:
        """
        Main verification method - extracts claims, verifies, and formats output.
        
        Args:
            llm_output: LLM-generated clinical insight
            drug1: First drug name
            drug2: Second drug name
            kg_rows: Knowledge graph query results
            
        Returns:
            Formatted output with verification
        """
        context = {
            'drug1': drug1,
            'drug2': drug2,
            'kg_rows': kg_rows
        }
        
        # Extract claims
        claims = self.extract_key_claims(llm_output, context)
        
        # Verify against KG
        verification = self.verify_against_kg(claims, context)
        
        # Format output
        formatted = self.format_verified_output(llm_output, verification)
        
        return formatted



    def verify_ingredient_existence(self, llm_response, drug1, drug2):
        from agents.kg_agent import CY_DRUG_INGREDIENTS

        drug1_comp = self.kg.query(CY_DRUG_INGREDIENTS, {"drug": drug1})
        drug2_comp = self.kg.query(CY_DRUG_INGREDIENTS, {"drug": drug2})

        kg_ingredients = set()
        for ing in (drug1_comp or []) + (drug2_comp or []):
            name = ing.get("ingredient", "")
            if name:
                kg_ingredients.add(name.lower())

        mentioned_ingredients = set()
        for kg_ing in kg_ingredients:
            if kg_ing and kg_ing in llm_response.lower():
                mentioned_ingredients.add(kg_ing)

        fabricated = []
        for word in llm_response.split():
            clean = word.strip(".,;:()")
            if clean and len(clean) > 6 and clean[0].isupper():
                if clean.lower() not in kg_ingredients and clean.lower() not in mentioned_ingredients:
                    fabricated.append(clean)

        return {
            "all_verified": len(fabricated) == 0,
            "mentioned_ingredients": list(mentioned_ingredients),
            "kg_ingredients": list(kg_ingredients),
            "fabricated_ingredients": fabricated[:5]
        }
