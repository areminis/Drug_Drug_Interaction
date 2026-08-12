"""
agents/kg_agent.py

Neo4j Knowledge Graph client for querying drug interactions, contraindications,
and ingredient-level interactions.
"""

from neo4j import GraphDatabase
from agents.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGClient:
    """Client for querying the Neo4j knowledge graph."""
    
    def __init__(self):
        """Initialize Neo4j driver connection."""
        self.driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def query(self, cypher: str, params: dict = None) -> list:
        """
        Execute a Cypher query against the knowledge graph.
        
        Args:
            cypher: Cypher query string
            params: Query parameters dictionary
            
        Returns:
            List of result dictionaries
        """
        with self.driver.session() as session:
            results = [record.data() for record in session.run(cypher, params or {})]
            return results


# ============================================================================
# DRUG-DRUG INTERACTION QUERIES
# ============================================================================

# Cypher query for drug-drug interactions (bidirectional)
CY_DDI = """
MATCH (d1:Drug)-[r:INTERACTS_WITH]-(d2:Drug)
WHERE (toLower(d1.name) CONTAINS toLower($drug1) AND toLower(d2.name) CONTAINS toLower($drug2))
   OR (toLower(d1.name) CONTAINS toLower($drug2) AND toLower(d2.name) CONTAINS toLower($drug1))
RETURN d1.name AS drug_a, d2.name AS drug_b, r.severity AS severity,
       r.mechanism AS mechanism, r.evidence_pubmed AS pmid, r.evidence_label_url AS label
"""

# ============================================================================
# DRUG-CONDITION QUERIES
# ============================================================================

# Cypher query for drug-condition relationships (indications/contraindications)
CY_CONTRA = """
MATCH (d:Drug)-[:USED_IN|:INDICATED_FOR|:TREATS]-(c:Condition)
WHERE toLower(d.name) CONTAINS toLower($drug)
  AND toLower(c.name) CONTAINS toLower($cond)
RETURN d.name AS drug, c.name AS condition
"""

# Cypher query to verify drug existence in KG (NEW - for no-interaction handling)
CY_DRUG_EXISTS = """
MATCH (d:Drug {name: $drug})
RETURN d.name as drug_name
LIMIT 1
"""

# Cypher query for ALL indications of a drug (for "what is X used for?" queries)
CY_DRUG_INDICATIONS = """
MATCH (d:Drug)-[:USED_IN|:INDICATED_FOR|:TREATS]-(c:Condition)
WHERE toLower(d.name) CONTAINS toLower($drug)
RETURN d.name AS drug, c.name AS condition
"""

# ============================================================================
# INGREDIENT QUERIES
# ============================================================================

# Query for drug ingredients
CY_DRUG_INGREDIENTS = """
MATCH (d:Drug)-[r:CONTAINS]->(i:Ingredient)
WHERE toLower(d.name) CONTAINS toLower($drug)
RETURN d.name AS drug, 
       i.name AS ingredient, 
       i.type AS type,
       r.quantity_mg AS quantity_mg,
       r.role AS role
ORDER BY 
    CASE i.type 
        WHEN 'Active' THEN 1 
        ELSE 2 
    END,
    i.name
"""

# Query for ingredient-ingredient interactions between two drugs
CY_INGREDIENT_INTERACTIONS = """
MATCH (d1:Drug)-[:CONTAINS]->(i1:Ingredient)
MATCH (d2:Drug)-[:CONTAINS]->(i2:Ingredient)
MATCH (i1)-[r:INTERACTS_WITH]-(i2)
WHERE (toLower(d1.name) CONTAINS toLower($drug1) AND toLower(d2.name) CONTAINS toLower($drug2))
   OR (toLower(d1.name) CONTAINS toLower($drug2) AND toLower(d2.name) CONTAINS toLower($drug1))
RETURN DISTINCT
       i1.name AS ingredient_a, 
       i2.name AS ingredient_b,
       r.mechanism AS mechanism, 
       r.severity AS severity,
       r.evidence_type AS evidence
"""

# Query to get all ingredients for multiple drugs at once
CY_MULTIPLE_DRUG_INGREDIENTS = """
UNWIND $drugs AS drug_name
MATCH (d:Drug)-[r:CONTAINS]->(i:Ingredient)
WHERE toLower(d.name) CONTAINS toLower(drug_name)
RETURN d.name AS drug,
       i.name AS ingredient,
       i.type AS type,
       r.quantity_mg AS quantity_mg,
       r.role AS role
ORDER BY d.name, 
    CASE i.type 
        WHEN 'Active' THEN 1 
        ELSE 2 
    END,
    i.name
"""