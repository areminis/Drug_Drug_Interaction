// ============================================================================
// NEO4J SCHEMA FOR ONCOLOGY DDI CHATBOT WITH INGREDIENT SUPPORT
// ============================================================================

// === Constraints ===
CREATE CONSTRAINT drug_id_unique IF NOT EXISTS
FOR (d:Drug) REQUIRE d.drug_id IS UNIQUE;

CREATE CONSTRAINT cond_id_unique IF NOT EXISTS
FOR (c:Condition) REQUIRE c.cond_id IS UNIQUE;

CREATE CONSTRAINT ingredient_id_unique IF NOT EXISTS
FOR (i:Ingredient) REQUIRE i.ingredient_id IS UNIQUE;

// === Indexes for faster lookups ===
CREATE INDEX drug_name_idx IF NOT EXISTS
FOR (d:Drug) ON (d.name);

CREATE INDEX cond_name_idx IF NOT EXISTS
FOR (c:Condition) ON (c.name);

CREATE INDEX ingredient_name_idx IF NOT EXISTS
FOR (i:Ingredient) ON (i.name);

CREATE INDEX ingredient_type_idx IF NOT EXISTS
FOR (i:Ingredient) ON (i.type);
