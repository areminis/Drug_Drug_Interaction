import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def patch_final_demo():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("🔧 Patching final demo scenarios for 10-question list...")
    
    with driver.session() as session:
        # =====================================================================
        # Scenario 5: Cisplatin + Gentamicin (Nephrotoxicity)
        # =====================================================================
        print("  > Setting up Cisplatin + Gentamicin...")
        session.run("""
            MERGE (d1:Drug {name: 'Cisplatin'})
            MERGE (d2:Drug {name: 'Gentamicin'})
            MERGE (d1)-[r:INTERACTS_WITH]->(d2)
            SET r.severity = 'Major',
                r.mechanism = 'Additive Nephrotoxicity',
                r.evidence_label_url = 'https://labels.fda.gov/cisplatin'
        """)

        # =====================================================================
        # Scenario 6: Methotrexate + Ibuprofen (Toxicity)
        # =====================================================================
        print("  > Setting up Methotrexate + Ibuprofen...")
        session.run("""
            MERGE (d1:Drug {name: 'Methotrexate'})
            MERGE (d2:Drug {name: 'Ibuprofen'})
            MERGE (d1)-[r:INTERACTS_WITH]->(d2)
            SET r.severity = 'Major',
                r.mechanism = 'Decreased renal clearance of Methotrexate',
                r.evidence_label_url = 'https://labels.fda.gov/methotrexate'
        """)

        # =====================================================================
        # Scenario 9: Indication - Imatinib for CML
        # =====================================================================
        print("  > Setting up Imatinib -> Chronic Myeloid Leukemia...")
        session.run("""
            MERGE (d:Drug {name: 'Imatinib'})
            MERGE (c:Condition {name: 'Chronic Myeloid Leukemia'})
            MERGE (d)-[:TREATS]->(c)
        """)

        # =====================================================================
        # Scenario 10: Indication - Gefitinib for Lung Cancer
        # =====================================================================
        print("  > Setting up Gefitinib -> Lung Cancer...")
        session.run("""
            MERGE (d:Drug {name: 'Gefitinib'})
            MERGE (c:Condition {name: 'Lung Cancer'})
            MERGE (d)-[:TREATS]->(c)
        """)

    driver.close()

if __name__ == "__main__":
    try:
        patch_final_demo()
        print("\n🎉 Final demo scenarios patched!")
    except Exception as e:
        print(f"❌ Error: {e}")
