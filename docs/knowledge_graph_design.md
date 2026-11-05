# Graph design

Entities preserve an original mention, a normalized name, type, aliases and user-recorded identifiers. A mention connects a stored entity to a passage. A relationship stores directed source/target IDs, relationship type, exact sentence, passage FK, extraction method, negation and `reported_finding` status. Document identity, year, study type and synthetic flag are joined from that passage's owner-scoped document.

Default supported verbs are inhibits, targets, activates, treats, interacts with, is associated with (adverse event), belongs to (class), and is involved in (pathway). Only explicit supported phrases with compatible entity types create edges. Negated statements remain separate reported edges. Confidence probabilities are not assigned because patterns have not been calibrated.

The local graph is a MultiDiGraph, preserving parallel evidence. The explorer limits neighborhoods to two hops and path searches to four hops and twenty paths. No arbitrary Cypher is accepted. Neo4j is an optional materialized mirror: `PharmaEntity` nodes and parameterized `REPORTED` relationships, partitioned by owner. SQL remains authoritative and changes need an explicit mirror sync. `graph/cypher/schema.cypher` contains indexes/constraints. Deletion in SQL is immediate for local retrieval; sync removes stale mirrored edges.
