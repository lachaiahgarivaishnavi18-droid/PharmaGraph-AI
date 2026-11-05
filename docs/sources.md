# External source contracts

The adapters use fixed official HTTPS endpoints, validated parameters, a per-source delay, and bounded result sizes. They return discovery metadata only; no arbitrary URL fetch, restricted-source scraping, paywall bypass, or automatic full-text import occurs.

- [NCBI E-utilities documentation](https://www.ncbi.nlm.nih.gov/books/NBK25501/) — PubMed ESearch; configure `PUBMED_API_KEY` when available.
- [Europe PMC REST API](https://europepmc.org/RestfulWebService) — core metadata search and explicit source/access information.
- [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) — numeric CID property lookup.
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api) — v2 study search; returned registrations do not independently establish trial outcomes.
- [UniProt REST API](https://www.uniprot.org/help/api) — UniProtKB metadata search.

Check source licenses and access terms before storing article content. Uploaded documents retain user-supplied license information; it is not independently certified. No DrugBank/UMLS entitlement is assumed and no identifier is invented. Connector tests mock official responses; live availability/rate policies and content rights must be verified when deploying.

Implementation references: [FastAPI bearer/JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [Vite setup](https://vite.dev/guide/).
