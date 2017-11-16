from rdflib import Graph, Namespace
from rdflib.namespace import FOAF

PROV = Namespace("http://www.w3.org/ns/prov#")
SSSC = Namespace("http://example.org/sssc#")

ns_bindings = [
    ('foaf', FOAF),
    ('prov', PROV),
    ('sssc', SSSC)
]


def rdf_graph(triples=None):
    """Return a new rdflib.Graph with default ns bindings.

    It will be populated with triples if any are supplied.

    """
    g = Graph()
    for prefix, ns in ns_bindings:
        g.bind(prefix, ns)
    if triples:
        for t in triples:
            g.add(t)
    return g
