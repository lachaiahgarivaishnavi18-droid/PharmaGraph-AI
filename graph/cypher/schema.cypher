CREATE CONSTRAINT pharma_entity_id IF NOT EXISTS FOR (n:PharmaEntity) REQUIRE (n.owner, n.id) IS UNIQUE;
CREATE INDEX pharma_name IF NOT EXISTS FOR (n:PharmaEntity) ON (n.name);
