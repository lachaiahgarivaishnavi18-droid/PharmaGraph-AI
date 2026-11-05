"""Conservative lexicon and explicit-verb extraction. Never infer co-occurrence edges."""
import re
from sqlalchemy import select
from .models import Entity, Mention, Relation

LEXICON = {
 'Drug': {'aspirin': ['acetylsalicylic acid'], 'metformin': [], 'imatinib': [], 'ibuprofen': [], 'gefitinib': [], 'erlotinib': [], 'atorvastatin': [], 'amoxicillin': [], 'Drug Aster': ['Aster'], 'Drug Boreal': ['Boreal']},
 'Disease': {'type 2 diabetes': ['T2DM'], 'lung cancer': [], 'chronic myeloid leukemia': ['CML'], 'inflammation': [], 'Condition Delta': []},
 'Target': {'EGFR': ['epidermal growth factor receptor'], 'BCR-ABL': ['BCR–ABL'], 'COX-1': ['cyclooxygenase-1'], 'COX-2': ['cyclooxygenase-2'], 'AMPK': [], 'Target Sigma': []},
 'Pathway': {'PI3K/AKT': [], 'MAPK': [], 'Pathway Aurora': []},
 'Adverse Event': {'nausea': [], 'headache': [], 'bleeding': []},
 'Gene': {'BRCA1': [], 'TP53': []},
 'Drug Class': {'biguanide': [], 'tyrosine kinase inhibitor': []},
}
VERBS = {
 'inhibits': ('DRUG_INHIBITS_TARGET', {'Drug','Compound'}, {'Target','Protein','Enzyme','Receptor'}),
 'targets': ('DRUG_TARGETS_PROTEIN', {'Drug','Compound'}, {'Target','Protein'}),
 'activates': ('DRUG_ACTIVATES_TARGET', {'Drug','Compound'}, {'Target','Protein'}),
 'treats': ('DRUG_TREATS_DISEASE', {'Drug'}, {'Disease'}),
 'is involved in': ('TARGET_INVOLVED_IN_PATHWAY', {'Target','Protein'}, {'Pathway'}),
 'is associated with': ('DRUG_ASSOCIATED_WITH_ADVERSE_EVENT', {'Drug'}, {'Adverse Event'}),
 'interacts with': ('DRUG_INTERACTS_WITH_DRUG', {'Drug'}, {'Drug'}),
 'belongs to': ('COMPOUND_BELONGS_TO_CLASS', {'Drug','Compound'}, {'Drug Class'}),
 'has mechanism': ('DRUG_HAS_MECHANISM', {'Drug'}, {'Mechanism'}),
 'encodes': ('GENE_ENCODES_PROTEIN', {'Gene'}, {'Protein'}),
 'is associated with gene': ('DISEASE_ASSOCIATED_WITH_GENE', {'Disease'}, {'Gene'}),
 'is investigated in': ('DRUG_INVESTIGATED_IN_TRIAL', {'Drug'}, {'Clinical Trial'}),
}

def extract(text, custom=()):
    terms = [(name, kind, aliases) for kind, entries in LEXICON.items() for name, aliases in entries.items()]
    terms += [(e.name, e.type, e.synonyms) for e in custom]
    found = {}
    for name, kind, aliases in terms:
        for alias in [name, *aliases]:
            match = re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text, re.I)
            if match:
                found[(name.lower(), kind)] = {'name': name, 'type': kind, 'original_name': match.group(), 'synonyms': aliases, 'method': 'curated_dictionary', 'identifiers': {}}
                break
    # Explicit annotations allow an offline corpus to introduce unknown terms without guessing.
    for m in re.finditer(r'\b(Drug|Compound|Disease|Target|Protein|Gene|Pathway|Mechanism|Clinical Trial|Enzyme|Receptor|Biological Process|Dosage Form|API|Medical Condition|Drug Class|Adverse Event)\s*:\s*([\w][\w -]{0,70})(?=[.;\n]|$)', text):
        name = m[2].strip()
        found[(name.lower(), m[1])] = {'name': name, 'type': m[1], 'original_name': name, 'synonyms': [], 'identifiers': {}, 'method': 'explicit_annotation'}
    return list(found.values())

def populate(db, owner_id, chunks):
    existing = db.scalars(select(Entity).where(Entity.owner_id == owner_id)).all()
    lookup = {(e.name.lower(), e.type): e for e in existing}
    for chunk in chunks:
        entities = []
        for item in extract(chunk.text, existing):
            key = (item['name'].lower(), item['type'])
            entity = lookup.get(key)
            if not entity:
                entity = Entity(owner_id=owner_id, **{k:v for k,v in item.items() if k != 'method'})
                db.add(entity); db.flush(); lookup[key] = entity
            db.add(Mention(entity_id=entity.id, passage_id=chunk.id, original=item['original_name'], method=item['method']))
            entities.append(entity)
        for sentence in re.split(r'(?<=[.!?])\s+|\n', chunk.text):
            for source in entities:
                for target in entities:
                    if source.id == target.id: continue
                    src = '(?:' + '|'.join(re.escape(n) for n in [source.name, *source.synonyms]) + ')'
                    dst = '(?:' + '|'.join(re.escape(n) for n in [target.name, *target.synonyms]) + ')'
                    for verb, (kind, allowed_s, allowed_t) in VERBS.items():
                        if source.type not in allowed_s or target.type not in allowed_t: continue
                        # Accept only a short, explicit subject-verb-object phrase.
                        pattern = r'(?<!\w)' + src + r'\s+(?P<neg>does not |did not |may not |not )?(?:' + re.escape(verb) + '|' + re.escape(verb.removesuffix('s')) + r')\s+' + dst + r'(?!\w)'
                        match = re.search(pattern, sentence, re.I)
                        if match:
                            db.add(Relation(source=source.id, target=target.id, type=kind, passage_id=chunk.id, evidence=sentence.strip(), negated=bool(match['neg'])))
