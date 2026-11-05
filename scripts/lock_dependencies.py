"""Record exact installed runtime/test dependency graph, excluding unrelated audit tools."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root=Path(__file__).resolve().parents[1]
pending=[Requirement(line) for line in (root/'backend'/'requirements.txt').read_text().splitlines() if line and not line.startswith('#')]
seen={}; visited=set()
while pending:
    request=pending.pop(); name=canonicalize_name(request.name)
    variant=(name,tuple(sorted(request.extras)))
    if variant in visited: continue
    visited.add(variant)
    package=distribution(name);seen[name]=package.version
    for dependency in package.requires or []:
        requirement=Requirement(dependency)
        if not requirement.marker or any(requirement.marker.evaluate({'extra':extra}) for extra in ('',*request.extras)):
            pending.append(requirement)
(root/'backend'/'requirements.lock').write_text('# Resolved on Python 3.12; install with pip install -r backend/requirements.lock\n'+'\n'.join(f'{name}=={version}' for name,version in sorted(seen.items()))+'\n')
print(f'Locked {len(seen)} packages.')
