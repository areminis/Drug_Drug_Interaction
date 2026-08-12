"""
agents/evaluator_agent.py

Evidence formatter for knowledge graph query results.
Converts raw Neo4j results into human-readable evidence statements.
Supports drug-drug interactions, drug-condition relationships, and ingredient-level interactions.
"""


def enforce_evidence(rows: list, kind: str) -> str:
    """
    Format knowledge graph query results into readable evidence.
    
    Args:
        rows: List of result dictionaries from Neo4j query
        kind: Type of query - 'ddi' (drug-drug interaction) or 'contra' (contraindication)
        
    Returns:
        Formatted evidence string with bullet points
    """
    if not rows:
        return "⚠️ No evidence found in the Knowledge Graph."

    if kind == "ddi":
        bullets = [
            f"- {r['drug_a']} ↔ {r['drug_b']} | Severity: {r['severity']} | Mechanism: {r['mechanism']} | "
            f"Evidence: {r.get('pmid','N/A')} | Label: {r.get('label','N/A')}"
            for r in rows
        ]
        return "✅ Based on KG evidence:\n" + "\n".join(bullets)

    if kind == "contra":
        bullets = [f"- {r['drug']} is used in {r['condition']} (no contraindication flagged)" for r in rows]
        return "✅ From KG (indications):\n" + "\n".join(bullets)

    return "⚠️ No evidence found in KG."


def format_drug_ingredients(rows: list) -> str:
    """
    Format drug ingredients into readable list.
    
    Args:
        rows: List of ingredient dictionaries from Neo4j query
        
    Returns:
        Formatted ingredient list grouped by drug
    """
    if not rows:
        return ""
    
    # Group by drug
    drugs = {}
    for r in rows:
        drug_name = r['drug']
        if drug_name not in drugs:
            drugs[drug_name] = []
        drugs[drug_name].append(r)
    
    # Format output
    output = []
    for drug_name, ingredients in drugs.items():
        output.append(f"\n**{drug_name}** contains:")
        
        # Separate active and excipients
        active = [i for i in ingredients if i['type'] == 'Active']
        excipients = [i for i in ingredients if i['type'] != 'Active']
        
        # Show active ingredients first
        for ing in active:
            qty = f"{ing.get('quantity_mg', 0):.1f} mg" if ing.get('quantity_mg') else ""
            output.append(f"  • **{ing['ingredient']}** (Active) {qty}".strip())
        
        # Show excipients
        for ing in excipients:
            qty = f"{ing.get('quantity_mg', 0):.1f} mg" if ing.get('quantity_mg') else ""
            ing_type = ing.get('type', 'Excipient')
            output.append(f"  • {ing['ingredient']} ({ing_type}) {qty}".strip())
    
    return "\n".join(output)


def format_ingredient_interactions(rows: list) -> str:
    """
    Format ingredient-ingredient interactions into readable list.
    
    Args:
        rows: List of ingredient interaction dictionaries from Neo4j query
        
    Returns:
        Formatted interaction list with severity and mechanism
    """
    if not rows:
        return "⚠️ No ingredient-level interactions found in the Knowledge Graph."
    
    bullets = []
    for r in rows:
        evidence = r.get('evidence', 'N/A')
        bullets.append(
            f"- **{r['ingredient_a']}** ↔ **{r['ingredient_b']}** | "
            f"Severity: {r['severity']} | Mechanism: {r['mechanism']} | "
            f"Evidence: {evidence}"
        )
    
    return "✅ Ingredient-level interactions found:\n" + "\n".join(bullets)


# ==================== NEW: Enhanced Ingredient Analysis Formatting ====================

def format_drug_composition_with_percentages(composition: list, drug_name: str) -> str:
    """
    Format drug composition with quantities and percentages.
    Clearly separates active and inactive ingredients.
    
    Args:
        composition: List of ingredient dicts with percentage calculated
        drug_name: Name of the drug
        
    Returns:
        Beautiful formatted composition string
    
"""
    if not composition:
        return f"**{drug_name}**: ⚠️ No composition data available"
    
    output = [f"**{drug_name}** contains:"]
    
    # Separate active and inactive (NEW)
    active_ings = [i for i in composition if i.get('display_category') == 'Active' or i.get('role') == 'Active']
    inactive_ings = [i for i in composition if i.get('display_category') == 'Inactive' or i.get('role') != 'Active']
    
    # Display active ingredients (ENHANCED)
    if active_ings:
        output.append("  🔵 **Active Ingredients:**")
        for ing in active_ings[:5]:  # Show top 5
            ingredient = ing.get('ingredient', 'Unknown')
            qty = ing.get('quantity_mg', 0)
            pct = ing.get('percentage', 0)
            output.append(f"    • {ingredient} - {qty:.1f} mg ({pct:.1f}%)")
        
        if len(active_ings) > 5:
            remaining = len(active_ings) - 5
            remaining_pct = sum(i.get('percentage', 0) for i in active_ings[5:])
            output.append(f"    • [{remaining} more active] - ({remaining_pct:.1f}%)")
    else:
        output.append("  ⚠️ No active ingredients found in database")
    
    # Display inactive ingredients (NEW)
    if inactive_ings:
        output.append("  ⚪ **Inactive Ingredients/Excipients:**")
        for ing in inactive_ings[:3]:  # Show top 3
            ingredient = ing.get('ingredient', 'Unknown')
            qty = ing.get('quantity_mg', 0)
            pct = ing.get('percentage', 0)
            ing_type = ing.get('type', ing.get('role', 'Excipient'))
            output.append(f"    • {ingredient} ({ing_type}) - {qty:.1f} mg ({pct:.1f}%)")
        
        if len(inactive_ings) > 3:
            remaining = len(inactive_ings) - 3
            remaining_pct = sum(i.get('percentage', 0) for i in inactive_ings[3:])
            output.append(f"    • [{remaining} more inactive] - ({remaining_pct:.1f}%)")
    
    return "\n".join(output)


def format_ingredient_contributions(categorized_contributions: dict) -> str:
    """
    Format ingredient interaction contributions with beautiful categorization.
    
    Args:
        categorized_contributions: Dict with 'primary', 'secondary', 'minor' keys
        
    Returns:
        Formatted contribution string with emojis and categories
    """
    output = []
    
    # Primary interactions (>= 50%)
    primary = categorized_contributions.get('primary', [])
    if primary:
        output.append("\n🔴 **PRIMARY INTERACTIONS** (>= 50% contribution):")
        for interaction, pct in primary:
            ing_a = interaction.get('ingredient_a', 'Unknown')
            ing_b = interaction.get('ingredient_b', 'Unknown')
            mechanism = interaction.get('mechanism', 'Unknown mechanism')
            severity = interaction.get('severity', 'Moderate')
            
            output.append(f"   • {ing_a} ↔ {ing_b} ({pct:.1f}%)")
            output.append(f"     → Mechanism: {mechanism}")
            output.append(f"     → Severity: {severity}")
    
    # Secondary interactions (20-49%)
    secondary = categorized_contributions.get('secondary', [])
    if secondary:
        output.append("\n🟡 **SECONDARY INTERACTIONS** (20-49% contribution):")
        for interaction, pct in secondary:
            ing_a = interaction.get('ingredient_a', 'Unknown')
            ing_b = interaction.get('ingredient_b', 'Unknown')
            mechanism = interaction.get('mechanism', 'Unknown mechanism')
            severity = interaction.get('severity', 'Moderate')
            
            output.append(f"   • {ing_a} ↔ {ing_b} ({pct:.1f}%)")
            output.append(f"     → Mechanism: {mechanism}")
            output.append(f"     → Severity: {severity}")
    
    # Minor interactions (< 20%)
    minor = categorized_contributions.get('minor', [])
    if minor:
        total_minor_pct = sum(pct for _, pct in minor)
        output.append(f"\n⚪ **MINOR INTERACTIONS** (< 20% contribution, {total_minor_pct:.1f}% total):")
        for interaction, pct in minor[:3]:  # Show up to 3 minor interactions
            ing_a = interaction.get('ingredient_a', 'Unknown')
            ing_b = interaction.get('ingredient_b', 'Unknown')
            output.append(f"   • {ing_a} ↔ {ing_b} ({pct:.1f}%)")
        
        if len(minor) > 3:
            output.append(f"   • ... and {len(minor) - 3} more minor interactions")
    
    if not primary and not secondary and not minor:
        return "\n⚠️ No ingredient-level interaction contributions calculated."
    
    return "\n".join(output)


def format_complete_ingredient_analysis(analysis_result: dict, drug1: str, drug2: str) -> str:
    """
    Format complete ingredient analysis with composition and contributions.
    
    Args:
        analysis_result: Result from IngredientAnalyzer.analyze_drug_interaction()
        drug1: First drug name
        drug2: Second drug name
        
    Returns:
        Complete formatted ingredient analysis string
    """
    output = [f"\n{'='*70}"]
    output.append("⚗️  INGREDIENT-LEVEL INTERACTION ANALYSIS")
    output.append(f"{'='*70}\n")
    
    # Drug compositions
    output.append("📋 **DRUG COMPOSITION:**")
    output.append("")
    
    drug1_comp = analysis_result.get('drug1_composition', [])
    drug2_comp = analysis_result.get('drug2_composition', [])
    
    output.append(format_drug_composition_with_percentages(drug1_comp, drug1))
    output.append("")
    output.append(format_drug_composition_with_percentages(drug2_comp, drug2))
    
    # Ingredient interaction contributions
    total_interactions = analysis_result.get('total_interactions', 0)
    
    if total_interactions == 0:
        output.append("\n⚠️ No ingredient-level interactions found in knowledge graph.")
        output.append("(This may be due to limited ingredient interaction data)")
    else:
        output.append(f"\n⚗️  **INGREDIENT INTERACTION ANALYSIS** ({total_interactions} interactions found):")
        contributions = analysis_result.get('contributions', {})
        output.append(format_ingredient_contributions(contributions))
    
    output.append(f"\n{'='*70}\n")
    
    return "\n".join(output)
