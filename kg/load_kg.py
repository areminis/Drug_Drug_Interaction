"""
load_kg.py

Loads pharmaceutical data into Neo4j including:
- Drugs, Conditions, Ingredients
- Drug-Drug interactions
- Drug-Ingredient mappings (CONTAINS relationships)
- Ingredient-Ingredient interactions
- Drug-Condition relationships (indications)
"""

import csv
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Paths
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "neo4j_schema.cypher")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DRUGS = os.path.join(DATA_DIR, "drugs.csv")
INGREDIENTS = os.path.join(DATA_DIR, "ingredients.csv")
DRUG_INGREDIENTS = os.path.join(DATA_DIR, "drug_ingredients.csv")
INGREDIENT_INTERACTIONS = os.path.join(DATA_DIR, "ingredient_interactions.csv")
INTERACTIONS = os.path.join(DATA_DIR, "interactions.csv")
CONDITIONS = os.path.join(DATA_DIR, "conditions.csv")
INDICATIONS = os.path.join(DATA_DIR, "indications.csv")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_schema():
    """Execute the Cypher schema to create constraints and indexes."""
    print("📋 Running schema...")
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = f.read()
    with driver.session() as s:
        for stmt in [x.strip() for x in schema.split(";") if x.strip()]:
            s.run(stmt)
    print("✅ Schema created")


def clear_database():
    """Clear all nodes and relationships from the database."""
    print("🗑️  Clearing existing data...")
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
    print("✅ Database cleared")


def load_drugs():
    """Load Drug nodes."""
    print("💊 Loading drugs...")
    count = 0
    with driver.session() as s:
        with open(DRUGS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MERGE (d:Drug {drug_id:$id}) "
                    "SET d.name=$name, d.class=$drug_class, d.atc_code=$atc",
                    id=r["drug_id"], 
                    name=r["name"], 
                    drug_class=r.get("class", ""),
                    atc=r.get("atc_code", "")
                )
                count += 1
    print(f"✅ Loaded {count} drugs")


def load_ingredients():
    """Load Ingredient nodes."""
    print("⚗️  Loading ingredients...")
    count = 0
    with driver.session() as s:
        with open(INGREDIENTS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MERGE (i:Ingredient {ingredient_id:$id}) "
                    "SET i.name=$name, i.type=$type, i.cas_number=$cas",
                    id=r["ingredient_id"],
                    name=r["name"],
                    type=r["type"],
                    cas=r.get("cas_number", "")
                )
                count += 1
                if count % 1000 == 0:
                    print(f"  ... {count} ingredients loaded")
    print(f"✅ Loaded {count} ingredients")


def load_drug_ingredients():
    """Load Drug-Ingredient CONTAINS relationships."""
    print("🔗 Loading drug-ingredient mappings...")
    count = 0
    with driver.session() as s:
        with open(DRUG_INGREDIENTS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MATCH (d:Drug {drug_id:$drug_id}) "
                    "MATCH (i:Ingredient {ingredient_id:$ing_id}) "
                    "MERGE (d)-[rel:CONTAINS]->(i) "
                    "SET rel.quantity_mg=$qty, rel.role=$role",
                    drug_id=r["drug_id"],
                    ing_id=r["ingredient_id"],
                    qty=float(r.get("quantity_mg", 0)),
                    role=r.get("role", "")
                )
                count += 1
                if count % 2000 == 0:
                    print(f"  ... {count} mappings loaded")
    print(f"✅ Loaded {count} drug-ingredient mappings")


def load_ingredient_interactions():
    """Load Ingredient-Ingredient INTERACTS_WITH relationships."""
    print("⚡ Loading ingredient-ingredient interactions...")
    count = 0
    with driver.session() as s:
        with open(INGREDIENT_INTERACTIONS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MATCH (a:Ingredient {ingredient_id:$a}) "
                    "MATCH (b:Ingredient {ingredient_id:$b}) "
                    "MERGE (a)-[rel:INTERACTS_WITH]->(b) "
                    "SET rel.mechanism=$m, rel.severity=$sev, rel.evidence_type=$ev",
                    a=r["ingredient_a_id"],
                    b=r["ingredient_b_id"],
                    m=r["mechanism"],
                    sev=r["severity"],
                    ev=r.get("evidence_type", "")
                )
                count += 1
                if count % 5000 == 0:
                    print(f"  ... {count} interactions loaded")
    print(f"✅ Loaded {count} ingredient-ingredient interactions")


def load_conditions():
    """Load Condition nodes."""
    print("🏥 Loading conditions...")
    count = 0
    with driver.session() as s:
        with open(CONDITIONS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MERGE (c:Condition {condition_id:$id}) "
                    "SET c.name=$name, c.category=$cat",
                    id=r["condition_id"],
                    name=r["name"],
                    cat=r.get("category", "")
                )
                count += 1
    print(f"✅ Loaded {count} conditions")


def load_indications():
    """Load Drug-Condition relationships."""
    print("📊 Loading drug-condition relationships...")
    count = 0
    with driver.session() as s:
        with open(INDICATIONS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rel_type = r.get("relationship", "USED_IN")
                s.run(
                    f"MATCH (d:Drug {{drug_id:$drug_id}}) "
                    f"MATCH (c:Condition {{condition_id:$cond_id}}) "
                    f"MERGE (d)-[:{rel_type}]->(c)",
                    drug_id=r["drug_id"],
                    cond_id=r["condition_id"]
                )
                count += 1
    print(f"✅ Loaded {count} drug-condition relationships")


def load_drug_interactions():
    """Load Drug-Drug INTERACTS_WITH relationships."""
    print("💥 Loading drug-drug interactions...")
    count = 0
    with driver.session() as s:
        with open(INTERACTIONS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MATCH (a:Drug {drug_id:$a}) "
                    "MATCH (b:Drug {drug_id:$b}) "
                    "MERGE (a)-[rel:INTERACTS_WITH]->(b) "
                    "SET rel.mechanism=$m, rel.severity=$sev, "
                    "rel.evidence_pubmed=$pmid, rel.evidence_label_url=$url",
                    a=r["drug_a_id"],
                    b=r["drug_b_id"],
                    m=r["mechanism"],
                    sev=r["severity"],
                    pmid=r.get("evidence_pubmed", ""),
                    url=r.get("evidence_label_url", "")
                )
                count += 1
                if count % 1000 == 0:
                    print(f"  ... {count} interactions loaded")
    print(f"✅ Loaded {count} drug-drug interactions")


def verify_data():
    """Verify loaded data counts."""
    print("\n📊 Verifying data...")
    with driver.session() as s:
        drug_count = s.run("MATCH (d:Drug) RETURN count(d) as count").single()["count"]
        ing_count = s.run("MATCH (i:Ingredient) RETURN count(i) as count").single()["count"]
        cond_count = s.run("MATCH (c:Condition) RETURN count(c) as count").single()["count"]
        
        drug_ing_count = s.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) as count").single()["count"]
        ing_int_count = s.run("MATCH (i1:Ingredient)-[r:INTERACTS_WITH]->(i2:Ingredient) RETURN count(r) as count").single()["count"]
        drug_int_count = s.run("MATCH (d1:Drug)-[r:INTERACTS_WITH]->(d2:Drug) RETURN count(r) as count").single()["count"]
        
        print(f"\n✅ Verification Results:")
        print(f"   Drugs: {drug_count}")
        print(f"   Ingredients: {ing_count}")
        print(f"   Conditions: {cond_count}")
        print(f"   Drug-Ingredient mappings: {drug_ing_count}")
        print(f"   Ingredient-Ingredient interactions: {ing_int_count}")
        print(f"   Drug-Drug interactions: {drug_int_count}")
        print(f"\n   Total nodes: {drug_count + ing_count + cond_count}")
        print(f"   Total relationships: {drug_ing_count + ing_int_count + drug_int_count}")


if __name__ == "__main__":
    print("=" * 70)
    print("NEO4J DATA LOADING - INGREDIENT-ENHANCED DDI CHATBOT")
    print("=" * 70)
    print()
    
    try:
        # Step 1: Run schema
        run_schema()
        
        # Step 2: Clear existing data (optional - comment out to keep existing data)
        clear_database()
        
        # Step 3: Load nodes
        load_drugs()
        load_ingredients()
        load_conditions()
        
        # Step 4: Load relationships
        load_drug_ingredients()
        load_ingredient_interactions()
        load_drug_interactions()
        load_indications()
        
        # Step 5: Verify
        verify_data()
        
        print("\n" + "=" * 70)
        print("✅ KG LOAD COMPLETE!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
