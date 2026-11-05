# Evidence validation

Grounding preserves the chain document → page/section passage → mention/relationship → retrieved source → quoted answer finding. A citation must use a retrieved passage ID and that passage's document ID. Page values and stored DOI/PMID values must match. Quotes must be nonempty exact substrings, and the finding must be that same extract. Key findings must cover those numbered excerpts. General unchecked narrative claims are rejected by the evidence-check route.

This procedure validates traceability rather than the truth of the source or general semantic entailment. Page references remain null for formats without reliable pagination. Missing DOI/PMID is not repaired by an LLM. Synthetic studies are explicitly labeled and have no evidentiary value about real medicines.

Potential conflicts require the same source entity, target entity and relation type with both affirmative and negated reports. Differences in study model, dose, population, outcome and methodology can explain apparent disagreement. Absence of a conflict flag does not imply consistency. Clinical efficacy, regulatory approval and adverse-event frequencies are never inferred from the existence of an edge.
