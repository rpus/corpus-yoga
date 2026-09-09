#!/usr/bin/env python
"""
mcp_face.py - the two faces of the mcp factoring (#605), derived from the factored
schema by stated rules, on the pattern of the maintainer's Expander (AsConsumer,
AsProducer): a party validates what it receives against the CONSUMER face and what
it sends against the PRODUCER face.

- consumer: every definition flat - its allOf resolved into one object, the bases'
  members merged in, so a validator chases no composition - and open, as draft-04
  leaves an object without additionalProperties: unknown members are tolerated,
  since the wire adds `_meta` keys and extensions. Its law: every instance the
  factoring admits, the consumer face admits (flattening is the conjunction allOf
  states, spelled as one object).
- producer: every definition flat as well - an allOf member closed by
  additionalProperties: false would refuse the members its siblings supply - and
  closed: every object schema with members and no index signature, at any depth,
  gets additionalProperties: false, so a producer emits nothing the protocol does
  not name. Its law: every instance the producer face admits, the factoring admits
  (closing only restricts).

Both are written under tmp/cache/mcp/ by `corpus-yoga mcp sync` beside the
derivation's other faces (rsc/cache_io.csv), never committed: they are readings of
the committed version file, and the dev gate holds them derivable from it and
valid draft-04 (mcp.faces_derivable).
"""

import json
import sys
from pathlib import Path

SELF = 'src/main/mcp/mcp_face.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
from schema_walk import rebuilt  # noqa: E402
sys.path.insert(0, str(REPO / 'src' / 'main'))
import mcp_factoring as factoring  # noqa: E402  (sibling module)

FACES = ('consumer', 'producer')
LAW = {
    'consumer': 'every instance the factoring admits, this face admits',
    'producer': 'every instance this face admits, the factoring admits',
}


def _flat(definitions: dict) -> dict:
    """Every definition with its allOf resolved into one object, in the factoring's order."""
    return {name: factoring.flattened(body, definitions) for name, body in definitions.items()}


def _closed(node: dict) -> dict:
    """node with every object schema that has members and no index signature closed,
    at every schema position."""
    out = dict(node)
    if out.get('type') == 'object' and out.get('properties') and 'additionalProperties' not in out:
        out['additionalProperties'] = False
    return rebuilt(out, _closed)


def face(doc: dict, which: str) -> dict:
    """The consumer or producer face of a factored document."""
    assert which in FACES, which
    definitions = _flat(doc['definitions'])
    if which == 'producer':
        definitions = {name: _closed(body) for name, body in definitions.items()}
    title = doc['title']
    return {
        '$schema': doc['$schema'],
        'title': f'{title}{which.capitalize()}',
        'description': (f'The {which} face of {title} (#605): every definition flat - its allOf resolved into one '
                        f'object - and {"open, unknown members tolerated" if which == "consumer" else "closed, additionalProperties false on every object with members and no index signature"}; '
                        f'its law: {LAW[which]}. Derived from the committed version file by corpus-yoga mcp sync, never hand-edited; '
                        f'a party validates what it {"receives" if which == "consumer" else "sends"} against it.'),
        'allOf': doc['allOf'],
        'definitions': {name: factoring._ordered(body) for name, body in definitions.items()},
    }


def written(doc: dict) -> list[Path]:
    """Write both faces under tmp/cache/mcp/."""
    factoring.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for which in FACES:
        path = factoring.CACHE_DIR / f'{which}.json'
        path.write_text(factoring.rendered(face(doc, which)))
        out.append(path)
    return out


def current(doc: dict) -> bool:
    """Whether tmp/cache/mcp/ holds both faces as derived from doc now."""
    return all((factoring.CACHE_DIR / f'{which}.json').is_file()
               and (factoring.CACHE_DIR / f'{which}.json').read_text() == factoring.rendered(face(doc, which))
               for which in FACES)
