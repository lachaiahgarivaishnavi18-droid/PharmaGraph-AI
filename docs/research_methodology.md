# Research methodology and reproducibility

1. Assemble a corpus with recorded access rights, timestamps, study types and identifiers. Keep synthetic examples separate from any evaluation corpus. Preserve raw uploads and hashes.
2. Extract text without inventing unavailable pagination or bibliographic metadata. Flag unreadable/scanned content and record every failed stage.
3. Chunk within page/section boundaries using 260-word windows and 40-word overlap. Track passage IDs throughout.
4. Extract curated text-bound entities, aliases and explicit typed annotations. Keep original forms. Test entity disambiguation independently; the supplied lexicon is a baseline.
5. Construct directed, source-linked explicit relationships with negation. Record reported-finding status, source type and synthetic provenance. Never treat co-occurrence as a mechanism or therapy edge.
6. Generate normalized vectors with a versioned model. Default lexical hashing needs no downloads. Pretrained semantic models must be downloaded explicitly, pinned and reprocessed consistently.
7. Search with normalized BM25, vector similarity, bounded graph evidence and title overlap. Avoid describing title overlap as study quality. Tune weights on held-out questions, not anecdotal examples.
8. Build an evidence package from retrieved passages. Return exact extracts, or use an optional provider to select validated exact quotes. Preserve uncertainty, synthetic labels and source limitations.
9. Validate citation membership, identifiers, pages and exact quotations. Do not claim automated clinical correctness or entailment beyond those checks.
10. Flag explicit contradictory relations. Have experts assess whether study contexts and outcomes are comparable.

Evaluation: create a human-labeled biomedical entity/relation set and a question set with relevant passages. Report precision/recall/F1 for spans and relations, retrieval recall@k/MRR/nDCG, citation traceability coverage, exact quote accuracy, abstention behavior, and expert-rated evidence sufficiency. Split by document to avoid overlap leakage. Include negative questions and out-of-corpus topics. Compare BM25-only, vector-only and hybrid ablations. Record model version, corpus hashes, ranking weights, top-k, environment, and limitations. No benchmark results are asserted by this project.

Synthetic integration tests validate mechanics, not biomedical performance. Real model quality, literature coverage and clinical correctness require separate research validation.
