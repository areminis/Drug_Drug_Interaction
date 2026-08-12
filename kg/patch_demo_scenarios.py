import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def patch_demo_scenarios():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("🔧 Patching additional demo scenarios...")
    
    with driver.session() as session:
        # =====================================================================
        # Scenario 2: Warfarin + Ibuprofen (Classic DDI)
        # =====================================================================
        print("  > Setting up Warfarin + Ibuprofen...")
        # Ensure ingredients exist and are named correctly
        session.run("""
            MERGE (d:Drug {drug_id: 'D0201'}) SET d.name = 'Warfarin'
            MERGE (i:Ingredient {ingredient_id: 'I_WARF'}) SET i.name = 'Warfarin Sodium', i.type = 'Active'
            MERGE (d)-[:CONTAINS {quantity_mg: 5.0, role: 'Active'}]->(i)
        """)
        session.run("""
            MERGE (d:Drug {drug_id: 'D1102'}) SET d.name = 'Ibuprofen'
            MERGE (i:Ingredient {ingredient_id: 'I_IBU'}) SET i.name = 'Ibuprofen', i.type = 'Active'
            MERGE (d)-[:CONTAINS {quantity_mg: 200.0, role: 'Active'}]->(i)
        """)
        # Create DDI
        session.run("""
            MATCH (d1:Drug {name: 'Warfarin'})
            MATCH (d2:Drug {name: 'Ibuprofen'})
            MERGE (d1)-[r:INTERACTS_WITH]->(d2)
            SET r.severity = 'Major',
                r.mechanism = 'Pharmacodynamic synergism (bleeding risk)',
                r.evidence_label_url = 'https://labels.fda.gov/warfarin'
        """)

        # =====================================================================
        # Scenario 3: Gentamicin + Acetaminophen (Safe / No Interaction)
        # =====================================================================
        print("  > Setting up Gentamicin + Acetaminophen...")
        # Add Gentamicin
        session.run("""
            MERGE (d:Drug {drug_id: 'D_GEN'}) SET d.name = 'Gentamicin', d.class = 'Antibiotic'
            MERGE (i:Ingredient {ingredient_id: 'I_GEN'}) SET i.name = 'Gentamicin Sulfate', i.type = 'Active'
            MERGE (d)-[:CONTAINS {quantity_mg: 80.0, role: 'Active'}]->(i)
        """)
        # Add Acetaminophen
        session.run("""
            MERGE (d:Drug {drug_id: 'D_APAP'}) SET d.name = 'Acetaminophen', d.class = 'Analgesic'
            MERGE (i:Ingredient {ingredient_id: 'I_APAP'}) SET i.name = 'Acetaminophen', i.type = 'Active'
            MERGE (d)-[:CONTAINS {quantity_mg: 500.0, role: 'Active'}]->(i)
        """)
        # Ensure NO interaction exists (delete if any)
        session.run("""
            MATCH (d1:Drug {name: 'Gentamicin'})-[r:INTERACTS_WITH]-(d2:Drug {name: 'Acetaminophen'})
            DELETE r
        """)

        # =====================================================================
        # Scenario 4: Acetaminophen + Tylenol (Duplicate Therapy)
        # =====================================================================
        print("  > Setting up Acetaminophen + Tylenol (Duplicate)...")
        # Add Tylenol (Brand name for Acetaminophen)
        session.run("""
            MERGE (d:Drug {drug_id: 'D_TYL'}) SET d.name = 'Tylenol', d.class = 'Analgesic'
            WITH d
            MATCH (i:Ingredient {name: 'Acetaminophen'})
            MERGE (d)-[:CONTAINS {quantity_mg: 500.0, role: 'Active'}]->(i)
        """)

    driver.close()

if __name__ == "__main__":
    try:
        patch_demo_scenarios()
        print("\n🎉 Demo scenarios patched successfully!")
        print("1. Warfarin + Ibuprofen (Major DDI)")
        print("2. Gentamicin + Acetaminophen (Safe)")
        print("3. Acetaminophen + Tylenol (Duplicate Ingredient)")
    except Exception as e:
        print(f"❌ Error: {e}")
