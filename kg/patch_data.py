import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def patch_demo_data():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("🔧 Patching data for Imatinib and Fluconazole demo...")
    
    with driver.session() as session:
        # 1. Update Imatinib's active ingredient name
        session.run("""
            MATCH (d:Drug {name: 'Imatinib'})-[:CONTAINS]->(i:Ingredient {type: 'Active'})
            SET i.name = 'Imatinib Mesylate'
            RETURN i.name
        """)
        print("✅ Updated Imatinib ingredient to 'Imatinib Mesylate'")

        # 2. Update Fluconazole's active ingredient name
        session.run("""
            MATCH (d:Drug {name: 'Fluconazole'})-[:CONTAINS]->(i:Ingredient {type: 'Active'})
            SET i.name = 'Fluconazole Base'
            RETURN i.name
        """)
        print("✅ Updated Fluconazole ingredient to 'Fluconazole Base'")

        # 3. Create explicit interaction between them
        session.run("""
            MATCH (i1:Ingredient {name: 'Imatinib Mesylate'})
            MATCH (i2:Ingredient {name: 'Fluconazole Base'})
            MERGE (i2)-[r:INTERACTS_WITH]->(i1)
            SET r.mechanism = 'CYP3A4 inhibition',
                r.severity = 'Major',
                r.evidence_type = 'Clinical Study'
            RETURN r
        """)
        print("✅ Created interaction: Fluconazole Base -[CYP3A4 inhibition]-> Imatinib Mesylate")

    driver.close()

if __name__ == "__main__":
    try:
        patch_demo_data()
        print("\n🎉 Data patched! Try asking 'What happens if Imatinib is given with Fluconazole?' again.")
    except Exception as e:
        print(f"❌ Error: {e}")
