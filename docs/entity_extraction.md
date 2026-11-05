# Entity extraction

The included extractor uses text-bound lexicon/alias matches with token boundaries and case normalization. It also accepts explicit typed annotations for user-supplied terms. It retains the original surface form. Unsupported terms stay unrecognized rather than being inferred. A dictionary mention is not a biomedical disambiguation guarantee.

Manual entity corrections update normalized names, types and aliases with audit records. Reprocess documents after changing the term vocabulary or correcting a type so relationships are rebuilt. IDs are not resolved from external systems by default; external discovery results are evidence to inspect, not permission to invent DrugBank, PubChem, UniProt, MeSH or UMLS identifiers.

Evaluate exact-span and normalized-entity precision/recall on an independently labeled corpus before deploying biomedical extraction at scale. Review ambiguous terms and negation. Integrating a biomedical NER model and licensed controlled vocabularies is a separate extension.
