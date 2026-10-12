"""
Tests for the shapes: take the valid sample graph, break it in one specific way, and check that
validate.py reports the expected problem. Run from shape_constraints/:

    python -m unittest discover -s tests -v

Each case: a name, a function that edits a copy of the sample graph, and the expected
(severity, message fragment) pairs. Other messages may appear too (one edit can break several rules).
"""

import sys
import unittest
from pathlib import Path

from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import validate  # noqa: E402

SAMPLE = HERE.parent.parent / "examples" / "sample_evidence_graph.ttl"

LODP = Namespace("https://example.org/lod-pathways/pilot/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
SIO = Namespace("http://semanticscience.org/resource/")
PROV = Namespace("http://www.w3.org/ns/prov#")
SWO = Namespace("http://www.ebi.ac.uk/swo/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCT = Namespace("http://purl.org/dc/terms/")
WP = Namespace("http://vocabularies.wikipathways.org/wp#")
PMW = Namespace("http://rdf-plantmetwiki.bioinformatics.nl/pathways/")
HAS_EVIDENCE = SIO.SIO_000772

BGC = URIRef("https://plantismash.bioinformatics.nl/precalc/v2/Arabidopsis_thaliana_GCF_000001735.4/index.html#cluster-60")
LINK = LODP.link_cluster60_PC800
ASSOC = LODP.assoc_fungal_DR10_C257_Solyc07g043480_M492T803
ANNOT = LODP.annotation_MTBLS14270_pos_741
CLAIM4 = LODP.claim_GDQC_108527_MONOMER_PC992
FEATURE = LODP.feature_MTBLS14270_pos_741
KEY = URIRef("https://identifiers.org/inchikey/GMMLNKINDDUDCF-BYNGITTOSA-M")
D = lambda x: Literal(x, datatype=XSD.double)  # noqa: E731
I = lambda x: Literal(x, datatype=XSD.integer)  # noqa: E731


# ---------------------------------------------------------------- helpers
def rm(g, s, p, o=None):
    g.remove((s, p, o))


def put(g, s, p, o):
    """Replace all values of (s, p) by o."""
    g.remove((s, p, None))
    g.add((s, p, o))


def evidence(g, claim, key, value=None):
    """The evidence node of `claim` whose property `key` is `value` (any value if None)."""
    for ev in g.objects(claim, HAS_EVIDENCE):
        vals = list(g.objects(ev, key))
        if vals and (value is None or Literal(value) in vals):
            return ev
    raise KeyError(f"no evidence on {claim} with {key}={value}")


def retype(g, ev, eco):
    """Give an evidence node exactly one ECO class (other than its current ones)."""
    g.remove((ev, RDF.type, None))
    g.add((ev, RDF.type, eco))


def swap_match(g, relation, iri):
    """Replace the MIBiG match of the BGC by `relation` -> iri."""
    g.remove((BGC, SKOS.exactMatch, None))
    g.remove((BGC, SKOS.closeMatch, None))
    g.add((BGC, relation, URIRef(iri)))


def one_input_only(g):
    g.remove((LODP.run_bgc_pathway_linking, PROV.used, URIRef("https://rest.uniprot.org/")))
    g.remove((LODP.run_bgc_pathway_linking, PROV.used, URIRef("https://plantmetwiki.bioinformatics.nl/sparql")))


V, W = "Violation", "Warning"


def cases():
    yield "claim without evidence", lambda g: rm(g, LINK, HAS_EVIDENCE), [(V, "needs at least one evidence node")]
    yield "claim without anchor tier", lambda g: rm(g, LINK, LODP.anchorTier), [(V, "exactly one lodp:anchorTier")]
    yield "anchor tier not in the list", lambda g: put(g, CLAIM4, LODP.anchorTier, Literal("probably")), [(V, "exactly one lodp:anchorTier")]
    yield "claim without any anchor", lambda g: rm(g, CLAIM4, LODP.anchoredInPathway), [(V, "must be anchored to PlantMetWiki")]
    yield "anchored to a single-reaction diagram (RC)", lambda g: put(g, CLAIM4, LODP.anchoredInPathway, PMW.RC12), [(V, "must be a PlantMetWiki pathway IRI")]
    yield "metabolite anchor is not an InChIKey IRI", lambda g: put(g, ANNOT, LODP.anchoredToMetabolite, URIRef("http://example.org/glucoraphanin")), [(V, "must be an identifiers.org InChIKey IRI")]

    # weak anchors are flagged, not rejected
    def weak(g):
        put(g, ASSOC, LODP.anchorTier, Literal("gene_ec")); put(g, ASSOC, LODP.geneAnchorTier, Literal("gene_ec"))
    yield "weak anchor (gene_ec) is a warning", weak, [(W, "Weak anchor")]

    # evidence nodes
    yield "evidence without ECO class", lambda g: g.remove((evidence(g, CLAIM4, LODP.originalEvidenceCode), RDF.type, None)), [(V, "typed with at least one ECO class")]
    yield "evidence without run", lambda g: rm(g, evidence(g, CLAIM4, LODP.originalEvidenceCode), PROV.wasGeneratedBy), [(V, "exactly one prov:wasGeneratedBy")]
    yield "evidence run is not a lodp:Run", lambda g: put(g, evidence(g, CLAIM4, LODP.originalEvidenceCode), PROV.wasGeneratedBy, LODP.not_a_run), [(V, "instance of a lodp:Run subclass")]

    # runs
    yield "run without software", lambda g: rm(g, LODP.run_meantools, LODP.software), [(V, "needs exactly one lodp:software")]
    yield "run without input data", lambda g: rm(g, LODP.run_meantools, PROV.used), [(V, "needs at least one prov:used")]
    yield "run without version is a warning", lambda g: rm(g, LODP.run_meantools, SWO.SWO_0004000), [(W, "Version missing")]
    yield "MEANtools run without decay rate", lambda g: rm(g, LODP.run_meantools, LODP.decayRate), [(V, "needs exactly one lodp:decayRate")]
    yield "MEANtools run with an unusual decay rate", lambda g: put(g, LODP.run_meantools, LODP.decayRate, I(7)), [(V, "needs exactly one lodp:decayRate")]
    yield "linking run with one input only is a warning", one_input_only, [(W, "combines at least two inputs")]
    yield "PlantCyc run with another software name", lambda g: put(g, LODP.run_plantcyc, LODP.software, Literal("MetaCyc")), [(V, "lodp:software 'PlantCyc'")]

    # features
    yield "feature without id", lambda g: rm(g, FEATURE, LODP.featureId), [(V, "needs exactly one lodp:featureId")]
    yield "feature without dataset", lambda g: rm(g, FEATURE, LODP.dataset), [(V, "needs exactly one lodp:dataset")]
    yield "feature with unknown ion mode", lambda g: put(g, FEATURE, LODP.ionMode, Literal("both")), [(V, "'positive' or 'negative'")]

    # case 1: BGC
    yield "BGC without species", lambda g: rm(g, BGC, WP.organismName), [(V, "exactly one wp:organismName")]
    yield "BGC with unknown detection rule", lambda g: put(g, evidence(g, BGC, LODP.detectionRule), LODP.detectionRule, Literal("hybrid")), [(V, "plantiSMASH 2.0 rules")]
    yield "BGC without detection rule", lambda g: rm(g, evidence(g, BGC, LODP.detectionRule), LODP.detectionRule), [(V, "at least one lodp:detectionRule")]
    yield "BGC without evidence", lambda g: rm(g, BGC, HAS_EVIDENCE), [(V, "needs evidence for the prediction")]
    yield "BGC prediction from another ECO class is a warning", lambda g: retype(g, evidence(g, BGC, LODP.detectionRule), OBO.ECO_0000006), [(W, "usually obo:ECO_0000256")]
    yield "exact MIBiG match with 75% genes similar", lambda g: put(g, g.value(BGC, LODP.mibigMatchEvidence), LODP.percentGenesSimilar, I(75)), [(V, "Inconsistent MIBiG match")]
    yield "close MIBiG match with 100% genes similar", lambda g: swap_match(g, SKOS.closeMatch, "https://mibig.secondarymetabolites.org/repository/BGC0000670"), [(V, "Inconsistent MIBiG match")]
    yield "MIBiG match without evidence node", lambda g: rm(g, BGC, LODP.mibigMatchEvidence), [(V, "needs lodp:mibigMatchEvidence")]
    yield "MIBiG percentage above 100", lambda g: put(g, g.value(BGC, LODP.mibigMatchEvidence), LODP.percentGenesSimilar, I(120)), [(V, "between 0 and 100")]
    yield "MIBiG IRI is not a MIBiG accession", lambda g: swap_match(g, SKOS.exactMatch, "http://example.org/BGC1"), [(V, "must be a MIBiG IRI")]

    # case 1: link
    yield "link without tier", lambda g: rm(g, evidence(g, LINK, LODP.linkTier), LODP.linkTier), [(V, "exactly one lodp:linkTier")]
    yield "link with 0 shared genes", lambda g: put(g, evidence(g, LINK, LODP.linkTier), LODP.nSharedGenes, I(0)), [(V, "lodp:nSharedGenes")]
    yield "link fraction above 1", lambda g: put(g, evidence(g, LINK, LODP.linkTier), LODP.fractionPathwayGenes, D(1.5)), [(V, "above 0 and at most 1")]
    yield "link fraction given as decimal, not double", lambda g: put(g, evidence(g, LINK, LODP.linkTier), LODP.fractionPathwayGenes, Literal("0.75", datatype=XSD.decimal)), [(V, "fractionPathwayGenes")]
    yield "gene_direct link without the linking genes", lambda g: rm(g, evidence(g, LINK, LODP.linkTier), LODP.linkingGene), [(V, "must list what links the BGC")]
    yield "link tier gene_ec without EC evidence", lambda g: [put(g, evidence(g, LINK, LODP.linkTier), LODP.linkTier, Literal("gene_ec")), put(g, LINK, LODP.anchorTier, Literal("gene_ec"))], [(V, "needs its matching evidence")]
    yield "link anchor tier differs from link tier", lambda g: put(g, LINK, LODP.anchorTier, Literal("gene_uniprot")), [(V, "must equal the lodp:linkTier")]
    yield "link evidence from plantiSMASH instead of a linking run", lambda g: put(g, evidence(g, LINK, LODP.linkTier), PROV.wasGeneratedBy, LODP.run_plantismash), [(V, "must come from a lodp:LinkingRun")]
    yield "link anchored in another pathway than it overlaps", lambda g: put(g, LINK, LODP.anchoredInPathway, PMW.PC1159), [(V, "must be the pathway that the BGC overlaps")]
    yield "link without the overlapped pathway", lambda g: g.remove((LINK, OBO.RO_0002131, PMW.PC800)), [(V, "exactly one PlantMetWiki pathway IRI")]
    yield "link evidence has the wrong ECO class", lambda g: retype(g, evidence(g, LINK, LODP.linkTier), OBO.ECO_0000006), [(V, "ECO_0007679")]

    # case 2: association
    yield "Pearson r above 1", lambda g: put(g, evidence(g, ASSOC, OBO.STATO_0000280), OBO.STATO_0000280, D(1.5)), [(V, "Pearson's r")]
    yield "correlation p-value missing", lambda g: rm(g, evidence(g, ASSOC, OBO.STATO_0000280), OBO.OBI_0000175), [(V, "p-value")]
    yield "mutual rank below 1", lambda g: put(g, evidence(g, ASSOC, OBO.STATO_0000280), LODP.mutualRank, D(0.5)), [(V, "lodp:mutualRank")]
    yield "edge weight above 1", lambda g: put(g, evidence(g, ASSOC, OBO.STATO_0000280), LODP.edgeWeight, D(2.0)), [(V, "lodp:edgeWeight")]
    yield "non-significant cluster is a warning", lambda g: None, [(W, "not significant")]
    yield "association without the cluster id", lambda g: rm(g, evidence(g, ASSOC, OBO.STATO_0000280), LODP.functionalCluster), [(V, "lodp:functionalCluster")]
    yield "association evidence from a non-MEANtools run", lambda g: put(g, evidence(g, ASSOC, OBO.STATO_0000280), PROV.wasGeneratedBy, LODP.run_sirius), [(V, "lodp:MEANtoolsRun")]
    yield "association evidence with an unrelated ECO class", lambda g: retype(g, evidence(g, ASSOC, OBO.STATO_0000280), OBO.ECO_0000006), [(V, "expression/combinatorial evidence class")]
    yield "association with side gene but no gene tier", lambda g: rm(g, ASSOC, LODP.geneAnchorTier), [(V, "needs its tier")]
    yield "association anchor tier not among the side tiers", lambda g: put(g, ASSOC, LODP.anchorTier, Literal("mass_match")), [(V, "does not match any side tier")]
    yield "association anchor tier stronger than the weakest side", lambda g: [put(g, ASSOC, LODP.anchoredSide, Literal("both")), g.add((ASSOC, LODP.metaboliteAnchorTier, Literal("mass_match")))], [(V, "must be one of the side tiers")]
    yield "association without a feature", lambda g: rm(g, ASSOC, SIO.SIO_000628, LODP.feature_MTBLS1039_M492T803), [(V, "exactly one metabolite feature")]
    yield "association with two genes", lambda g: g.add((ASSOC, SIO.SIO_000628, URIRef("https://plants.ensembl.org/Solanum_lycopersicum/Gene/Summary?g=Solyc01g000001"))), [(V, "exactly one gene")]
    yield "association without anchored side", lambda g: rm(g, ASSOC, LODP.anchoredSide), [(V, "exactly one lodp:anchoredSide")]

    # case 3: annotation
    yield "annotation uses skos:exactMatch", lambda g: g.add((ANNOT, SKOS.exactMatch, KEY)), [(V, "cannot be exact")]
    yield "annotation without feature", lambda g: rm(g, ANNOT, LODP.feature), [(V, "exactly one lodp:feature")]
    yield "annotation without match level", lambda g: rm(g, ANNOT, LODP.matchLevel), [(V, "exactly one lodp:matchLevel")]
    yield "annotation anchor not repeated as closeMatch", lambda g: g.remove((ANNOT, SKOS.closeMatch, KEY)), [(V, "must also be a skos:closeMatch")]
    yield "annotation evidence without tier", lambda g: rm(g, evidence(g, ANNOT, LODP.siriusConfidenceApprox), LODP.identificationTier), [(V, "exactly one lodp:identificationTier")]
    yield "annotation evidence with unknown tier", lambda g: put(g, evidence(g, ANNOT, LODP.siriusConfidenceApprox), LODP.identificationTier, Literal("magic")), [(V, "exactly one lodp:identificationTier")]
    yield "annotation evidence without LC-MS/MS class", lambda g: g.remove((evidence(g, ANNOT, LODP.siriusConfidenceApprox), RDF.type, OBO.ECO_0001580)), [(V, "Evidence class")]
    yield "consensus without the ECO integration class", lambda g: g.remove((evidence(g, ANNOT, LODP.matchType), RDF.type, OBO.ECO_0007653)), [(V, "Evidence class")]
    yield "consensus run is a plain tool run", lambda g: put(g, evidence(g, ANNOT, LODP.matchType), PROV.wasGeneratedBy, LODP.run_sirius), [(V, "Run type")]
    yield "tool tier from a consensus run", lambda g: put(g, evidence(g, ANNOT, LODP.siriusConfidenceApprox), PROV.wasGeneratedBy, LODP.run_consensus), [(V, "Run type")]
    yield "consensus without match type", lambda g: rm(g, evidence(g, ANNOT, LODP.matchType), LODP.matchType), [(V, "consensus evidence needs")]
    yield "partial consensus with score 1.0", lambda g: put(g, evidence(g, ANNOT, LODP.matchType), LODP.agreementScore, D(1.0)), [(V, "consensus evidence needs")]
    yield "partial consensus with one agreeing tool", lambda g: g.remove((evidence(g, ANNOT, LODP.matchType), LODP.agreeingTool, Literal("MS2Query"))), [(V, "consensus evidence needs")]
    yield "full consensus with two agreeing tools", lambda g: [put(g, evidence(g, ANNOT, LODP.matchType), LODP.matchType, Literal("full")), put(g, evidence(g, ANNOT, LODP.matchType), LODP.agreementScore, D(1.0))], [(V, "consensus evidence needs")]
    yield "agreeing tool not in the list", lambda g: g.add((evidence(g, ANNOT, LODP.matchType), LODP.agreeingTool, Literal("Magic"))), [(V, "must be SIRIUS, MS2Query or DreaMS")]
    yield "SIRIUS confidence above 1", lambda g: put(g, evidence(g, ANNOT, LODP.siriusConfidenceApprox), LODP.siriusConfidenceApprox, D(1.4)), [(V, "siriusConfidenceApprox")]
    yield "SIRIUS evidence without its score is a warning", lambda g: rm(g, evidence(g, ANNOT, LODP.siriusConfidenceApprox), LODP.siriusConfidenceApprox), [(W, "should carry its score")]
    yield "annotation anchored by mass instead of structure", lambda g: put(g, ANNOT, LODP.anchorTier, Literal("mass_match")), [(V, "anchored by structure_match")]

    # case 4: PlantCyc
    ev4 = lambda g: evidence(g, CLAIM4, LODP.originalEvidenceCode)  # noqa: E731
    yield "PlantCyc code with the wrong ECO class", lambda g: put(g, ev4(g), LODP.originalEvidenceCode, Literal("EV-EXP-IEP")), [(V, "does not match the PlantCyc code")]
    yield "PlantCyc code without a proposed mapping is a warning", lambda g: [put(g, ev4(g), LODP.originalEvidenceCode, Literal("EV-FOO"))], [(W, "no proposed ECO mapping")]
    yield "PlantCyc code in a wrong format", lambda g: put(g, ev4(g), LODP.originalEvidenceCode, Literal("exp-ida")), [(V, "original PlantCyc code")]
    yield "PlantCyc subject from another pathway", lambda g: put(g, CLAIM4, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#object"), PMW.PC800) or put(g, CLAIM4, LODP.anchoredInPathway, PMW.PC800), [(V, "PC number in rdf:subject")]
    yield "PlantCyc predicate is not isPartOf", lambda g: put(g, CLAIM4, RDF.predicate, DCT.references), [(V, "dcterms:isPartOf")]
    yield "PlantCyc claim anchored elsewhere than its object", lambda g: put(g, CLAIM4, LODP.anchoredInPathway, PMW.PC800), [(V, "pathway of rdf:object")]
    yield "PlantCyc claim not anchored as curated", lambda g: put(g, CLAIM4, LODP.anchorTier, Literal("mass_match")), [(V, "anchored as 'curated'")]
    yield "PubMed reference is not an identifiers.org IRI", lambda g: put(g, ev4(g), DCT.references, URIRef("http://example.org/22186372")), [(V, "PubMed IRI")]
    yield "PlantCyc evidence from another run type", lambda g: put(g, ev4(g), PROV.wasGeneratedBy, LODP.run_sirius), [(V, "lodp:PlantCycCuration")]

    # references to PlantMetWiki (checked by validate.py, not by SHACL)
    yield "anchor to a pathway that does not exist", lambda g: [g.remove((CLAIM4, LODP.anchoredInPathway, None)), g.add((CLAIM4, LODP.anchoredInPathway, PMW.PC99999)), g.remove((CLAIM4, RDF.object, None)), g.add((CLAIM4, RDF.object, PMW.PC99999))], [(V, "pathway does not exist in the snapshot")]
    yield "anchor to a metabolite that does not exist", lambda g: [g.remove((ANNOT, LODP.anchoredToMetabolite, None)), g.add((ANNOT, LODP.anchoredToMetabolite, URIRef("https://identifiers.org/inchikey/AAAAAAAAAAAAAA-BBBBBBBBBB-C"))), g.add((ANNOT, SKOS.closeMatch, URIRef("https://identifiers.org/inchikey/AAAAAAAAAAAAAA-BBBBBBBBBB-C")))], [(V, "metabolite (InChIKey) does not exist")]


class SampleIsValid(unittest.TestCase):
    def test_sample_has_no_violations_and_one_warning(self):
        res = validate.validate([SAMPLE])
        self.assertEqual(res["violations"], 0, validate.format_report(res))
        self.assertEqual([r["message"] for r in res["results"]], ["The functional cluster is not significant (ClusterONE p >= 0.05)."])


class BrokenSamples(unittest.TestCase):
    def test_each_break_is_reported(self):
        for name, edit, expected in cases():
            with self.subTest(name):
                g = Graph().parse(str(SAMPLE), format="turtle")
                edit(g)
                res = validate.validate(g)
                for severity, fragment in expected:
                    found = [r["message"] for r in res["results"] if r["severity"] == severity and fragment in r["message"]]
                    self.assertTrue(found, f"expected a {severity} containing {fragment!r}; got:\n" +
                                    "\n".join(f"  {r['severity']}: {r['message'][:110]}" for r in res["results"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
