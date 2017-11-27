from rdflib import BNode, Literal, URIRef, RDF
from .namespaces import PROV, SSSC


def add_prov_derivation(g, subject, entity):
    """Add a new Derivation to g, relating subject and entity, returning it. """
    derivation = BNode()
    g.add((subject, PROV.wasDerivedFrom, entity))
    g.add((subject, PROV.qualifiedDerivation, derivation))
    g.add((derivation, RDF.type, PROV.Derivation))
    g.add((derivation, PROV.entity, entity))
    return derivation


def add_prov_dependency(g, subject, dependency):
    """Add dependency d to prov graph g.

    """
    triples = []

    # Toolbox dependencies provide a URL, others just record the info.
    if dependency.type == "toolbox":
        d = URIRef(dependency.identifier)
    else:
        d = BNode("dependency{}".format(dependency.id))

    derivation = add_prov_derivation(g, subject, d)
    triples.extend([
        (derivation, RDF.type, SSSC.Dependency),
        (derivation, PROV.entity, d),
        (derivation, SSSC.dependencyType, Literal(dependency.type)),
        (derivation, SSSC.dependencyIdentifier, Literal(dependency.identifier))
    ])

    if dependency.version is not None:
        triples.append((derivation,
                        SSSC.dependencyVersion,
                        Literal(dependency.version)))
    if dependency.repository is not None:
        triples.append((derivation,
                        SSSC.dependencyRepository,
                        URIRef(dependency.repository)))

    for t in triples:
        g.add(t)

    return g


