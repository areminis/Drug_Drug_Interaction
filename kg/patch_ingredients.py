"""
patch_ingredients.py

Patches Neo4j with updated ingredients.csv and drug_ingredients.csv
WITHOUT clearing the existing database.

Run: python kg/patch_ingredients.py
"""

import csv
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Password")

DATA_DIR           = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INGREDIENTS_CSV    = os.path.join(DATA_DIR, "ingredients.csv")
DRUG_INGREDIENTS_CSV = os.path.join(DATA_DIR, "drug_ingredients.csv")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def patch_ingredients():
    """Add/update Ingredient nodes (including new Inactive ones)."""
    print("⚗️  Patching Ingredient nodes...")
    count = 0
    with driver.session() as s:
        with open(INGREDIENTS_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s.run(
                    "MERGE (i:Ingredient {ingredient_id: $id}) "
                    "SET i.name=$name, i.type=$type, i.cas_number=$cas",
                    id=r["ingredient_id"],
                    name=r["name"],
                    type=r["type"],
                    cas=r.get("cas_number", "")
                )
                count += 1
    print(f"✅ {count} ingredients patched (MERGE — existing unchanged, new ones added)")


def patch_drug_ingredients():
    """Add/update CONTAINS relationships from drug_ingredients.csv."""
    print("🔗 Patching Drug-Ingredient CONTAINS relationships...")
    count = 0
    skipped = 0
    with driver.session() as s:
        with open(DRUG_INGREDIENTS_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                result = s.run(
                    "MATCH (d:Drug {drug_id: $drug_id}) "
                    "MATCH (i:Ingredient {ingredient_id: $ing_id}) "
                    "MERGE (d)-[rel:CONTAINS]->(i) "
                    "SET rel.quantity_mg=$qty, rel.role=$role "
                    "RETURN d.name as drug, i.name as ingredient",
                    drug_id=r["drug_id"],
                    ing_id=r["ingredient_id"],
                    qty=float(r.get("quantity_mg", 0)),
                    role=r.get("role", "Active")
                )
                record = result.single()
                if record:
                    count += 1
                else:
                    skipped += 1
                    print(f"  ⚠️  Skipped: drug_id={r['drug_id']} + ingredient_id={r['ingredient_id']} not found in KG")
    print(f"✅ {count} drug-ingredient relationships patched")
    if skipped:
        print(f"⚠️  {skipped} skipped (drug or ingredient not in KG)")


def verify():
    """Show current ingredient counts by type."""
    print("\n📊 Verification:")
    with driver.session() as s:
        total_ing = s.run("MATCH (i:Ingredient) RETURN count(i) as c").single()["c"]
        active_ing = s.run("MATCH (i:Ingredient {type:'Active'}) RETURN count(i) as c").single()["c"]
        inactive_ing = s.run("MATCH (i:Ingredient {type:'Inactive'}) RETURN count(i) as c").single()["c"]
        total_contains = s.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) as c").single()["c"]
        active_rel = s.run("MATCH ()-[r:CONTAINS {role:'Active'}]->() RETURN count(r) as c").single()["c"]
        inactive_rel = s.run("MATCH ()-[r:CONTAINS {role:'Inactive'}]->() RETURN count(r) as c").single()["c"]

        print(f"   Total Ingredients      : {total_ing}")
        print(f"   ├── Active             : {active_ing}")
        print(f"   └── Inactive/Excipients: {inactive_ing}")
        print(f"   Total CONTAINS rels    : {total_contains}")
        print(f"   ├── Active role        : {active_rel}")
        print(f"   └── Inactive role      : {inactive_rel}")

        # Check specific drugs
        print("\n   Sample check — Warfarin ingredients:")
        rows = s.run(
            "MATCH (d:Drug)-[r:CONTAINS]->(i:Ingredient) "
            "WHERE toLower(d.name) CONTAINS 'warfarin' "
            "RETURN i.name as ingredient, r.role as role, r.quantity_mg as qty "
            "ORDER BY r.role"
        )
        for row in rows:
            icon = "🔵" if row["role"] == "Active" else "⚪"
            print(f"     {icon} {row['ingredient']} — {row['qty']} mg ({row['role']})")


if __name__ == "__main__":
    print("=" * 60)
    print("INGREDIENT PATCH — DDI Chatbot KG Update")
    print("=" * 60)
    print()
    try:
        patch_ingredients()
        print()
        patch_drug_ingredients()
        verify()
        print("\n" + "=" * 60)
        print("✅ PATCH COMPLETE — Restart Streamlit to see inactive ingredients")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
