import os
import networkx as nx
from sqlalchemy import select
from .models import Entity, Relation, Chunk, Document, Mention

def graph_data(db, owner_id):
    entities = db.scalars(select(Entity).where(Entity.owner_id == owner_id)).all()
    rows = db.execute(select(Relation, Chunk, Document).join(Chunk, Relation.passage_id == Chunk.id).join(Document, Chunk.document_id == Document.id).where(Document.owner_id == owner_id, Document.status == 'processed')).all()
    mentioned = set(db.scalars(select(Mention.entity_id).join(Chunk).join(Document).where(Document.owner_id == owner_id, Document.status == 'processed')).all())
    nodes = [{'id': e.id, 'name': e.name, 'type': e.type, 'synonyms': e.synonyms, 'identifiers': e.identifiers} for e in entities if e.id in mentioned]
    edges = [{'id': r.id, 'source': r.source, 'target': r.target, 'type': r.type, 'negated': r.negated, 'status': r.status, 'evidence_text': r.evidence,
              'source_document_id': d.id, 'source_passage_id': c.id, 'document_title': d.title, 'page_number': c.page, 'publication_year': d.meta.get('publication_year'),
              'evidence_type': d.meta.get('document_type'), 'synthetic': d.meta.get('synthetic',False), 'extraction_method': r.method} for r,c,d in rows]
    return {'nodes': nodes, 'edges': edges}

def network(data):
    graph = nx.MultiDiGraph()
    graph.add_nodes_from((n['id'], n) for n in data['nodes'])
    for edge in data['edges']: graph.add_edge(edge['source'], edge['target'], key=edge['id'], **edge)
    return graph

def neighborhood(data, entity_id, hops=1):
    graph = network(data).to_undirected()
    if entity_id not in graph: return {'nodes': [], 'edges': []}
    ids = set(nx.single_source_shortest_path_length(graph, entity_id, cutoff=hops))
    return {'nodes': [n for n in data['nodes'] if n['id'] in ids], 'edges': [e for e in data['edges'] if e['source'] in ids and e['target'] in ids]}

def sync_neo4j(data, owner_id):
    from neo4j import GraphDatabase
    if not os.getenv('NEO4J_URI'): return {'backend':'networkx', 'nodes':len(data['nodes']), 'relationships':len(data['edges'])}
    with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.getenv('NEO4J_USERNAME','neo4j'),os.environ['NEO4J_PASSWORD'])) as driver:
        def write(tx):
            tx.run('MATCH (n:PharmaEntity {owner:$owner}) DETACH DELETE n', owner=owner_id).consume()
            for n in data['nodes']:
                tx.run('MERGE (n:PharmaEntity {id:$id,owner:$owner}) SET n.name=$name,n.type=$type', id=n['id'],owner=owner_id,name=n['name'],type=n['type']).consume()
            for e in data['edges']:
                tx.run('MATCH (s:PharmaEntity {id:$source,owner:$owner}),(t:PharmaEntity {id:$target,owner:$owner}) MERGE (s)-[r:REPORTED {id:$id}]->(t) SET r.type=$type,r.passage=$passage,r.evidence=$evidence,r.negated=$negated',source=e['source'], target=e['target'],owner=owner_id,id=e['id'],type=e['type'],passage=e['source_passage_id'],evidence=e['evidence_text'],negated=e['negated']).consume()
        with driver.session() as session: session.execute_write(write)
    return {'backend':'neo4j', 'nodes':len(data['nodes']), 'relationships':len(data['edges'])}
