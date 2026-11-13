"""Transcriptomics claims (lod-pathways-community pattern) from the results of this pilot.

Reads only results/ (written by run_pilot.py) and data/ (dated PlantMetWiki snapshots). build() returns one
graph with all claim sets in CLAIM_SETS; shape_constraints/build_rdf.py calls it ("transcriptomics" case)
and validates the graph. Run alone, it writes the Turtle to a file without validation.

Claims (each an rdf:Statement whose IRI is built from its triple, lodp:claim_<subject>_<predicate>_<object>,
so the same triple from several datasets or routes is one claim with one evidence IRI per run,
lodp:evidence_<claim>_<study>):
  differential expression  gene  lodp:differentiallyExpressedIn  contrast (per experiment)
  response profile         gene  lodp:expressionDeviatesIn       condition
  gene co-expression       gene  RO:0002610 correlated with      gene (the two gene IRIs in alphabetical order)
  pathway co-expression    pathway  rdf:type  lodp:CoexpressedGenePathway
The direction is on each evidence node (lodp:direction): RO:0002245 over- or RO:0002246 under-expressed in
(sign of log2FC or z), RO:0017003 positively or RO:0017004 negatively correlated with (sign of r), so
datasets that disagree give conflicting evidence on one claim. The claim also refers (sio:SIO_000628) to the
PlantMetWiki gene nodes or the pathway, next to rdf:subject/rdf:object (redundant; kept for review). There is
no anchor, anchor tier or organism on the claims: pathway and organism are reached from the PlantMetWiki gene
node by query (dcterms:isPartOf, wp:organism). Gene nodes are found by their Solyc locus ("gene-" prefix and
version suffix removed); the locus itself is not written. Values sit on the evidence node.
Details are statements, not extra nodes: the contrast or condition that is the object of a claim is an IRI
with no statements of its own, and what it stands for is stated on the claim (lodp:conditionType treatment,
lodp:testCondition and lodp:referenceCondition as text, lodp:testReplicateCount and lodp:referenceReplicateCount
or lodp:replicateCount, lodp:plantStructure as a PO term). The matrix a run read is stated on the run
(lodp:inputUnit: STATO counts, TPM, FPKM or RPKM; lodp:inputFile); a differential expression run is also typed
with its multiple-testing method (OBI:0200036) and states its normalisation (lodp:normalisationMethod
STATO:0000590 median of ratios; lodp:normalisedFile).

Usage (from this folder; rdflib and pandas, e.g. the shape_constraints venv):
  python to_turtle.py [-o transcriptomics.ttl]
  python to_turtle.py --refresh-genes | --refresh-pathways     (new PlantMetWiki snapshots in data/)
"""
import argparse
import csv
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

PILOT = Path(__file__).resolve().parent
DATA = PILOT / "data"
RESULTS = PILOT / "results"
ENDPOINT = "https://plantmetwiki.bioinformatics.nl/sparql"

LODP = Namespace("https://example.org/lod-pathways/pilot/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
EFO = Namespace("http://www.ebi.ac.uk/efo/")
SIO = Namespace("http://semanticscience.org/resource/")
PROV = Namespace("http://www.w3.org/ns/prov#")
SWO = Namespace("http://www.ebi.ac.uk/swo/")
EDAM = Namespace("http://edamontology.org/")

# DESeq2 results column -> property on the evidence node (TX-08 to TX-12; terms from ontology_terms.csv)
DESEQ2_VALUES = {
    "log2FoldChange": LODP.log2FoldChange,   # TX-08, local
    "stat": OBO.STATO_0000584,               # TX-09, Wald statistic
    "lfcSE": OBO.STATO_0000562,              # TX-10, standard error of estimate (stand-in)
    "baseMean": OBO.STATO_0000401,           # TX-11, sample mean (stand-in)
    "pvalue": OBO.OBI_0000175,               # p-value (as PO-05)
    "padj": LODP.adjustedPValue,             # TX-12, local
}

GENES_QUERY = """PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?gene ?label ?solyc WHERE {
  ?gene a wp:GeneProduct ; wp:isAbout ?node .
  OPTIONAL { ?gene rdfs:label ?label }
  ?node <http://rdf-plantmetwiki.bioinformatics.nl/vocab/gpmlProperty> ?p .
  ?p <http://rdf-plantmetwiki.bioinformatics.nl/vocab/key> ?k ;
     <http://rdf-plantmetwiki.bioinformatics.nl/vocab/value> ?solyc .
  FILTER(STRSTARTS(STR(?solyc), "Solyc"))
} ORDER BY ?solyc"""


class FullDouble(Literal):
    """xsd:double written as "<repr>"^^xsd:double: the Turtle shorthand rdflib uses for doubles ("%e")
    keeps only 7 significant digits."""

    def _literal_n3(self, use_plain=False, qname_callback=None):
        return super()._literal_n3(use_plain=False, qname_callback=qname_callback)


def double(v):
    return FullDouble(repr(float(v)), datatype=XSD.double)


def locus(gene_id):
    """Solyc locus without "gene-" prefix and version suffix."""
    return re.sub(r"\.\d+$", "", re.sub(r"^gene-", "", str(gene_id).strip()))


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_")


# --- Claims as rdf:Statement --------------------------------------------------------------------------
PREDICATE_NAMES = {                     # rdf:predicate of each claim type -> name used in the claim IRI
    "https://example.org/lod-pathways/pilot/differentiallyExpressedIn": "differentiallyExpressedIn",
    "https://example.org/lod-pathways/pilot/expressionDeviatesIn": "expressionDeviatesIn",
    "http://purl.obolibrary.org/obo/RO_0002610": "correlatedWith",
    str(RDF.type): "type",
}


def local_id(iri):
    """Last part of an IRI for use in a claim IRI (G18C3-3, HQ293016, PWY18C3-3, EMTAB11876_jasmonate_vs_none)."""
    s = re.split(r"[/#]", str(iri))[-1]
    s = re.sub(r"^(contrast|condition)_", "", s)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


def add_statement(g, cls, subject, predicate, obj, label, refers=()):
    """A claim reified as an rdf:Statement; its IRI is built from the triple, so it is the same for every
    dataset or route that supports the triple."""
    claim = LODP["claim_" + "_".join([local_id(subject), PREDICATE_NAMES[str(predicate)], local_id(obj)])]
    g.add((claim, RDF.type, cls))
    g.add((claim, RDF.subject, URIRef(subject)))
    g.add((claim, RDF.predicate, URIRef(predicate)))
    g.add((claim, RDF.object, URIRef(obj)))
    g.add((claim, RDFS.label, Literal(label)))
    for r in refers:                                   # kept next to rdf:subject/rdf:object (redundant)
        g.add((claim, SIO.SIO_000628, URIRef(r)))
    return claim


def add_evidence(g, claim, run, study, types):
    """Evidence IRI: one per claim and study (run), lodp:evidence_<claim without claim_>_<study>."""
    ev = LODP["evidence_" + str(claim)[len(str(LODP)) + len("claim_"):] + "_" + slug(study)]
    g.add((claim, SIO.SIO_000772, ev))
    for ty in types:
        g.add((ev, RDF.type, ty))
    g.add((ev, PROV.wasGeneratedBy, run))
    return ev


def sign_term(value, positive, negative):
    """Direction term from the sign of a value (none for 0 or NaN)."""
    if pd.isna(value) or value == 0:
        return None
    return positive if value > 0 else negative


# --- PlantMetWiki gene nodes ------------------------------------------------------------------------
def refresh_genes():
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": GENES_QUERY})
    req = urllib.request.Request(url, headers={"Accept": "text/tab-separated-values"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = list(csv.reader(r.read().decode().splitlines(), delimiter="\t"))
    out = DATA / f"plantmetwiki_tomato_gene_nodes_{datetime.date.today().isoformat()}.tsv"
    DATA.mkdir(exist_ok=True)
    with open(out, "w", newline="") as f:
        f.write(f"# PlantMetWiki gene nodes with a Solyc locus (GPML property), {ENDPOINT}, "
                f"{datetime.date.today().isoformat()}; query in pilots/transcriptomics_overlap/to_turtle.py\n")
        w = csv.writer(f, delimiter="\t")
        w.writerow(["gene_node", "label", "solyc"])
        for gene, label, solyc in rows[1:]:
            w.writerow([gene.strip('"<>'), label.strip('"'), solyc.strip('"')])
    print(f"wrote data/{out.name} ({len(rows) - 1} genes)")
    return out


def load_genes():
    snaps = sorted(DATA.glob("plantmetwiki_tomato_gene_nodes_*.tsv"))
    if not snaps:
        sys.exit("no PlantMetWiki gene snapshot in data/; run to_turtle.py --refresh-genes")
    df = pd.read_csv(snaps[-1], sep="\t", comment="#", dtype=str)
    df["locus"] = df["solyc"].map(locus)
    dup = df["locus"].duplicated(keep=False)
    if dup.any():
        print(f"warning: loci with several gene nodes, skipped: {sorted(set(df.loc[dup, 'locus']))}")
    df = df[~dup]
    
    return df.set_index("locus"), snaps[-1]


# --- PlantMetWiki pathway membership of the gene nodes (pathway co-expression) -------------------------
PATHWAYS_QUERY = """PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT DISTINCT ?gene ?pathway ?source ?title WHERE {
  ?gene a wp:GeneProduct ; wp:isAbout ?node ; dcterms:isPartOf ?rev .
  ?rev a wp:Pathway ; dc:identifier ?pathway .
  OPTIONAL { ?rev dcterms:source ?source }
  OPTIONAL { ?rev dc:title ?title }
  ?node <http://rdf-plantmetwiki.bioinformatics.nl/vocab/gpmlProperty> ?p .
  ?p <http://rdf-plantmetwiki.bioinformatics.nl/vocab/value> ?solyc .
  FILTER(STRSTARTS(STR(?solyc), "Solyc"))
} ORDER BY ?pathway ?gene"""


def refresh_pathways():
    """Gene node -> pathway (dc:identifier pathways/PC<n> or RC<n>, PlantCyc source, title), for the gene
    nodes with a Solyc locus. PC numbers change between PlantMetWiki builds; the PlantCyc ID does not."""
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": PATHWAYS_QUERY})
    req = urllib.request.Request(url, headers={"Accept": "text/tab-separated-values"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = list(csv.reader(r.read().decode().splitlines(), delimiter="\t"))
    out = DATA / f"plantmetwiki_tomato_gene_pathways_{datetime.date.today().isoformat()}.tsv"
    with open(out, "w", newline="") as f:
        f.write(f"# PlantMetWiki pathways (dcterms:isPartOf, wp:Pathway) of the gene nodes with a Solyc locus, {ENDPOINT}, "
                f"{datetime.date.today().isoformat()}; query in pilots/transcriptomics_overlap/to_turtle.py\n")
        w = csv.writer(f, delimiter="\t")
        w.writerow(["gene_node", "pathway", "plantcyc", "title"])
        for row in rows[1:]:
            w.writerow([v.strip('"<>') for v in row])
    print(f"wrote data/{out.name} ({len(rows) - 1} gene-pathway rows)")
    return out


# --- Input matrix of a run (TX-03, TX-04) --------------------------------------------------------------
INPUT_UNITS = {                         # what the matrix a run read holds -> value type
    "COUNTS": OBO.STATO_0000064,        # TX-03 sequence read count
    "TPM": OBO.STATO_0000589,           # TX-04
    "FPKM": OBO.STATO_0000172,
    "RPKM": OBO.STATO_0000206,
}

# assay of the dataset -> RNA-seq or microarray ECO class, added to the gene co-expression evidence next to ECO:0007590 (TX-01/TX-02)
ASSAY_ECO = {"rnaseq": OBO.ECO_0006069, "microarray": OBO.ECO_0007301}


def add_input(g, run, unit, label):
    """The matrix the run read, as statements on the run: lodp:inputFile (file and source) and lodp:inputUnit
    (its value type) when it is counts, TPM, FPKM or RPKM (none for other values, e.g. log2 ComBat: a comment
    instead; the shapes warn)."""
    g.add((run, LODP.inputFile, Literal(label)))
    t = INPUT_UNITS.get(str(unit).upper())
    if t is not None:
        g.add((run, LODP.inputUnit, t))
    else:
        g.add((run, RDFS.comment, Literal(f"input values: {unit} (no TX-03/TX-04 term)")))


# --- Reading an nf-core differentialabundance folder (or an adapter folder) ------------------------
def add_structure(g, claim, curie, note=None):
    """TX-19: plant structure of the samples, as a Plant Ontology term on the claim (samplesheet column
    plant_structure, e.g. PO:0009005 root); plant_structure_note as a comment (e.g. hairy root, no PO term)."""
    if isinstance(curie, str) and re.fullmatch(r"PO:\d{7}", curie):
        g.add((claim, LODP.plantStructure, OBO[curie.replace(":", "_")]))
    if isinstance(note, str) and note and note != "nan":
        g.add((claim, RDFS.comment, Literal(f"plant structure: {note}")))


# --- Differential expression claims ------------------------------------------------------------------
def differential(d, datasets, study, experiment):
    """d: results/differential_<study>.tsv (export_differential.py) and its .provenance.json."""
    genes, _ = load_genes()
    info = json.loads(provenance_file(d).read_text())
    res_all = pd.read_csv(d, sep="\t", dtype={"locus": str})

    g = Graph()
    for p, ns in [("lodp", LODP), ("obo", OBO), ("efo", EFO), ("sio", SIO), ("prov", PROV), ("swo", SWO),
                  ("edam", EDAM), ("rdfs", RDFS), ("xsd", XSD)]:
        g.bind(p, ns)
    run = LODP[f"run_differential_expression_{study}"]
    g.add((run, RDF.type, LODP.DifferentialExpressionRun))
    g.add((run, RDF.type, EDAM.operation_3223))           # TX-07 differential gene expression profiling
    g.add((run, RDFS.label, Literal(f"Differential expression, {study} ({info['note']})")))
    g.add((run, LODP.software, Literal(info["software"])))
    g.add((run, SWO.SWO_0004000, Literal(info["version"])))
    for ds in datasets:
        g.add((run, PROV.used, URIRef(ds)))
    add_input(g, run, "counts", info["input"])               # DESeq2 reads raw counts (TX-03)
    if info["p_adjust"] == "BH":
        g.add((run, RDF.type, OBO.OBI_0200036))            # TX-13 Benjamini-Hochberg correction
    # TX-05: DESeq2 normalises by median of ratios; the normalised matrix is an output of the run
    g.add((run, LODP.normalisationMethod, OBO.STATO_0000590))
    g.add((run, LODP.normalisedFile, Literal(info["normalised"])))

    n = 0
    for c in info["contrasts"]:
        # the contrast is the claim's object, an IRI with no statements; what it compares is stated on the claim
        contrast = LODP[f"contrast_{slug(experiment)}_{slug(c['id'])}"]
        test, ref = c["conditions"][c["target"]], c["conditions"][c["reference"]]
        for r in res_all[res_all["contrast"] == c["id"]].itertuples():
            if r.locus not in genes.index or pd.isna(r.log2FoldChange):
                continue
            gene = genes.loc[r.locus]
            claim = add_statement(g, LODP.DifferentialExpressionClaim, gene["gene_node"], LODP.differentiallyExpressedIn,
                                  contrast, f"{gene['label']} differentially expressed in {c['target']} vs {c['reference']}",
                                  refers=[gene["gene_node"]])
            g.add((claim, LODP.conditionType, EFO.EFO_0000727))                 # TX-20 treatment
            g.add((claim, LODP.testCondition, Literal(f"{c['variable']}: {c['target']}")))
            g.add((claim, LODP.referenceCondition, Literal(f"{c['variable']}: {c['reference']}")))
            g.add((claim, LODP.testReplicateCount, Literal(int(test["replicates"]))))        # TX-18
            g.add((claim, LODP.referenceReplicateCount, Literal(int(ref["replicates"]))))
            for meta in (test, ref):                                                         # TX-19
                add_structure(g, claim, meta.get("plant_structure"), meta.get("plant_structure_note"))
            if c.get("blocking"):
                g.add((claim, RDFS.comment, Literal(f"blocking factor(s): {c['blocking']}")))
            ev = add_evidence(g, claim, run, study, [OBO.ECO_0006069])   # TX-02 RNA-sequencing evidence (automatic)
            direction = sign_term(r.log2FoldChange, OBO.RO_0002245, OBO.RO_0002246)   # over- / under-expressed in
            if direction is not None:
                g.add((ev, LODP.direction, direction))
            for col, prop in DESEQ2_VALUES.items():
                v = getattr(r, col)
                if pd.notna(v):
                    g.add((ev, prop, double(v)))
            n += 1
    return g, n


# --- Co-expression claims ------------------------------------------------------------------------------
COEXPRESSION_VALUES = {
    "pearson_r": OBO.STATO_0000280,     # TX-14 Pearson's correlation coefficient
    "pearson_p": OBO.OBI_0000175,       # p-value of the Pearson correlation (as PO-05)
    "spearman_rho": OBO.STATO_0000201,  # TX-14 alternative, Spearman's rank correlation coefficient
    "mutual_rank": LODP.mutualRank,     # TX-16, local
}


def coexpression(d, datasets, out, study, assay):
    """d: results/coexpression_<study>.tsv (coexpression_table.py) and its .provenance.json.
    Claim: gene RO:0002610 (correlated with) gene, the two gene IRIs in alphabetical order (the relation is
    symmetric, so each pair has one claim); the sign is on the evidence (RO:0017003 / RO:0017004). Claims
    from several datasets merge into one claim with one evidence node per dataset."""
    genes, snapshot = load_genes()
    prov = json.loads(provenance_file(d).read_text())
    pairs = pd.read_csv(d, sep="\t")

    g = Graph()
    for p, ns in [("lodp", LODP), ("obo", OBO), ("sio", SIO), ("prov", PROV), ("swo", SWO),
                  ("edam", EDAM), ("rdfs", RDFS), ("xsd", XSD)]:
        g.bind(p, ns)
    g.bind("plantcyc", "https://identifiers.org/plantcyc/")
    g.bind("ncbigene", "https://identifiers.org/ncbigene/")
    run = LODP[f"run_coexpression_{study}"]
    g.add((run, RDF.type, LODP.CoexpressionRun))
    g.add((run, RDF.type, EDAM.operation_3463))           # expression correlation analysis
    g.add((run, RDFS.label, Literal(f"Co-expression of PlantMetWiki tomato genes, {study} ({prov['source_note']})")))
    g.add((run, LODP.software, Literal(f"{prov['script']} (numpy, scipy.stats)")))
    v = prov["versions"]
    g.add((run, SWO.SWO_0004000, Literal(
        f"run {prov['run_on']}; scipy {v['scipy']}, numpy {v['numpy']}; transform {prov['transform']}; "
        f"{prov['samples']} samples, mutual rank over {prov['genes_with_variance']} genes")))
    for ds in datasets:
        g.add((run, PROV.used, URIRef(ds)))
    add_input(g, run, prov.get("unit", ""), f"{Path(prov['matrix']).name} ({prov['matrix']}), {prov['source_note']}")

    n = 0
    for r in pairs.itertuples():
        if r.gene_a not in genes.index or r.gene_b not in genes.index:
            continue
        (na, la), (nb, lb) = sorted([(genes.loc[r.gene_a, "gene_node"], genes.loc[r.gene_a, "label"]),
                                     (genes.loc[r.gene_b, "gene_node"], genes.loc[r.gene_b, "label"])])
        claim = add_statement(g, LODP.GeneCoexpressionAssociation, na, OBO.RO_0002610, nb,
                              f"{la} and {lb}: expression correlated", refers=[na, nb])
        # high throughput expression pattern evidence (as PO) + the assay: RNA-seq or expression microarray
        ev = add_evidence(g, claim, run, study, [OBO.ECO_0007590, ASSAY_ECO[assay]])
        direction = sign_term(r.pearson_r, OBO.RO_0017003, OBO.RO_0017004)   # positively / negatively correlated with
        if direction is not None:
            g.add((ev, LODP.direction, direction))
        for col, prop in COEXPRESSION_VALUES.items():
            val = getattr(r, col)
            if pd.notna(val):
                g.add((ev, prop, double(val)))
        n += 1

    return g, n


# --- Pathway co-expression claims ------------------------------------------------------------------------
def pathway_coexpression(d, datasets, out, study, assay, pathway_iri):
    """d: results/pathway_coexpression_<study>.tsv (pathway_coexpression_table.py) and its .provenance.json.
    The claim refers to the pathway: pathway_iri "plantcyc" uses the PlantCyc ID (dcterms:source, stable
    across PlantMetWiki builds), "pmw" the PlantMetWiki pathway IRI (pathways/PC<n>, renumbered between
    builds). Which one is open (QUESTIONS.md). Claim: pathway rdf:type lodp:CoexpressedGenePathway (a
    property of one pathway, stated as class membership); files from several datasets merge into one
    claim per pathway with one evidence node per dataset."""
    prov = json.loads(provenance_file(d).read_text())
    table = pd.read_csv(d, sep="\t")

    g = Graph()
    for p, ns in [("lodp", LODP), ("obo", OBO), ("sio", SIO), ("prov", PROV), ("swo", SWO),
                  ("edam", EDAM), ("rdfs", RDFS), ("xsd", XSD)]:
        g.bind(p, ns)
    g.bind("plantcyc", "https://identifiers.org/plantcyc/")
    g.bind("pmwpath", "http://rdf-plantmetwiki.bioinformatics.nl/pathways/")
    run = LODP[f"run_pathway_coexpression_{study}"]
    g.add((run, RDF.type, LODP.PathwayCoexpressionRun))
    g.add((run, RDF.type, EDAM.operation_3463))           # expression correlation analysis
    g.add((run, RDFS.label, Literal(f"Pathway co-expression against random gene sets, {study} ({prov['source_note']})")))
    g.add((run, LODP.software, Literal(f"{prov['script']} (numpy)")))
    v = prov["versions"]
    g.add((run, SWO.SWO_0004000, Literal(
        f"run {prov['run_on']}; numpy {v['numpy']}, pandas {v['pandas']}; transform {prov['transform']}; "
        f"statistic: {prov['statistic']}; null: {prov['null']}; p: {prov['empirical_p']}; "
        f"{prov['samples']} samples, {prov['genes_with_variance']} genes with variance; "
        f"PlantMetWiki pathways: {prov['plantmetwiki_pathways']}")))
    for ds in datasets:
        g.add((run, PROV.used, URIRef(ds)))
    add_input(g, run, prov.get("unit", ""), f"{Path(prov['matrix']).name} ({prov['matrix']}), {prov['source_note']}")

    for r in table.itertuples():
        pathway = r.plantcyc if pathway_iri == "plantcyc" else r.pathway
        claim = add_statement(g, LODP.PathwayCoexpressionClaim, pathway, RDF.type, LODP.CoexpressedGenePathway,
                              f"Genes of {r.title} are co-expressed more than random gene sets", refers=[pathway])
        ev = add_evidence(g, claim, run, study, [OBO.ECO_0007590, ASSAY_ECO[assay]])   # as gene co-expression
        g.add((ev, LODP.meanPairwiseCorrelation, double(r.mean_r)))
        g.add((ev, OBO.OBI_0000175, double(r.empirical_p)))   # empirical p-value against the random sets
        g.add((ev, LODP.geneCount, Literal(int(r.genes_used))))
        g.add((ev, LODP.randomSetCount, Literal(int(r.n_random))))
        g.add((ev, RDFS.comment, Literal(f"genes used ({r.genes_used} of {r.genes_in_pathway} PlantMetWiki genes with a "
                                         f"Solyc locus): {r.labels.replace(',', ', ')}; random sets: mean r "
                                         f"{r.null_mean:.4f}, SD {r.null_sd:.4f}")))

    return g, len(table)


# --- Response profile claims (z-score per gene and condition) -------------------------------------------
UNIT_TERMS = {                          # TX-04: normalised expression value, by unit
    "TPM": OBO.STATO_0000589,
    "FPKM": OBO.STATO_0000172,
    "RPKM": OBO.STATO_0000206,
}


def profile(d, datasets, out, study, experiment=None):
    """d: results/expression_profile_<study>.tsv (expression_profile_table.py) and its .provenance.json.
    One claim per gene and condition; all rows are written (|z| < 2 is flagged by the shapes, not dropped)."""
    genes, snapshot = load_genes()
    prov = json.loads(provenance_file(d).read_text())
    table = pd.read_csv(d, sep="\t", dtype={"condition": str})
    unit_prop = UNIT_TERMS.get(prov["unit"].upper())
    if unit_prop is None:
        sys.exit(f"unit {prov['unit']!r} has no TX-04 term; known: {sorted(UNIT_TERMS)}")
    factors = prov["factors"]
    experiment = experiment or study                      # condition IRIs

    g = Graph()
    for p, ns in [("lodp", LODP), ("obo", OBO), ("efo", EFO), ("sio", SIO), ("prov", PROV), ("swo", SWO),
                  ("edam", EDAM), ("rdfs", RDFS), ("xsd", XSD)]:
        g.bind(p, ns)
    g.bind("plantcyc", "https://identifiers.org/plantcyc/")
    g.bind("ncbigene", "https://identifiers.org/ncbigene/")
    run = LODP[f"run_expression_profile_{study}"]
    g.add((run, RDF.type, LODP.ExpressionProfileRun))
    g.add((run, RDF.type, EDAM.operation_0314))           # gene expression profiling
    g.add((run, RDFS.label, Literal(f"Response profile (z-score per condition) of PlantMetWiki tomato genes, "
                                    f"{study} ({prov['source_note']})")))
    g.add((run, LODP.software, Literal(f"{prov['script']} (pandas)")))
    v = prov["versions"]
    g.add((run, SWO.SWO_0004000, Literal(
        f"run {prov['run_on']}; pandas {v['pandas']}, numpy {v['numpy']}; z-score {prov['zscore']}; "
        f"transform {prov['transform']}; {prov['conditions']} conditions ({' x '.join(factors)}), {prov['samples']} samples")))
    for ds in datasets:
        g.add((run, PROV.used, URIRef(ds)))
    add_input(g, run, prov["unit"], f"{Path(prov['matrix']).name} ({prov['matrix']}), {prov['source_note']}")

    n = 0
    for r in table.itertuples(index=False):
        r = r._asdict()
        if r["gene"] not in genes.index:
            continue
        gene = genes.loc[r["gene"]]
        what = ", ".join(f"{f} {r[f]}" for f in factors)
        # the condition is the claim's object, an IRI with no statements; what it stands for is stated on the claim
        cond = LODP[f"condition_{slug(experiment)}_{slug(r['condition'])}"]
        claim = add_statement(g, LODP.ExpressionProfileClaim, gene["gene_node"], LODP.expressionDeviatesIn, cond,
                              f"{gene['label']}: expression unusual under {what}", refers=[gene["gene_node"]])
        g.add((claim, LODP.conditionType, EFO.EFO_0000727))                     # TX-20 treatment
        g.add((claim, LODP.testCondition, Literal(what)))
        g.add((claim, LODP.replicateCount, Literal(int(r["replicates"]))))      # TX-18
        add_structure(g, claim, r.get("plant_structure"), r.get("plant_structure_note"))   # TX-19
        ev = add_evidence(g, claim, run, study, [OBO.ECO_0006069])   # TX-02 RNA-sequencing evidence (automatic)
        direction = sign_term(r["zscore"], OBO.RO_0002245, OBO.RO_0002246)   # over- / under-expressed in
        if direction is not None:
            g.add((ev, LODP.direction, direction))
        g.add((ev, OBO.STATO_0000104, double(r["zscore"])))         # TX-06 z-score
        g.add((ev, unit_prop, double(r["mean_expression"])))       # TX-04 mean of the condition, in its unit
        n += 1

    return g, n


# --- Claim sets of the pilot -----------------------------------------------------------------------------
AE = "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-11876"
ENA = "https://www.ebi.ac.uk/ena/browser/view/PRJEB53936"
ZENODO_MEANTOOLS = "https://doi.org/10.5281/zenodo.15697913"
ATTED = "https://atted.jp/download/Sly-r.c6-0/exp/Sly-r.c6-0.expression.combat.txt.zip"
ENSEMBL_ENTREZ = ("https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-63/tsv/solanum_lycopersicum_gca000188115v5cm/"
                  "Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.entrez.tsv.gz")

# (kind, results table name (results/<name>.tsv and <name>.provenance.json), study = run identifier, options)
CLAIM_SETS = [
    ("differential", "differential_EMTAB11876_nfcore_salmon", "EMTAB11876_nfcore_salmon", {"experiment": "EMTAB11876", "datasets": [AE, ENA]}),
    ("differential", "differential_EMTAB11876_atlas_counts", "EMTAB11876_atlas_counts", {"experiment": "EMTAB11876", "datasets": [AE]}),
    ("differential", "differential_EMTAB11876_atlas_published", "EMTAB11876_atlas_published", {"experiment": "EMTAB11876", "datasets": [AE]}),
    ("profile", "expression_profile_meantools_rpkm", "meantools_rpkm", {"experiment": "meantools", "datasets": [ZENODO_MEANTOOLS]}),
    ("coexpression", "coexpression_meantools_rpkm", "meantools_rpkm", {"assay": "rnaseq", "datasets": [ZENODO_MEANTOOLS]}),
    ("coexpression", "coexpression_atted_Sly_r_c6_0", "atted_Sly_r_c6_0", {"assay": "rnaseq", "datasets": [ATTED, ENSEMBL_ENTREZ]}),
    ("coexpression", "coexpression_EMTAB11876_nfcore_salmon", "EMTAB11876_nfcore_salmon", {"assay": "rnaseq", "datasets": [AE, ENA]}),
    ("pathway_coexpression", "pathway_coexpression_meantools_rpkm", "meantools_rpkm", {"assay": "rnaseq", "datasets": [ZENODO_MEANTOOLS]}),
    ("pathway_coexpression", "pathway_coexpression_atted_Sly_r_c6_0", "atted_Sly_r_c6_0", {"assay": "rnaseq", "datasets": [ATTED, ENSEMBL_ENTREZ]}),
]


def provenance_file(table):
    """results/<name>.tsv -> results/<name>.provenance.json"""
    return table.with_name(table.stem + ".provenance.json")


def build(results=RESULTS, pathway_iri="plantcyc"):
    """All claim sets in one graph; returns (graph, stats). Claim sets whose results table is missing are skipped."""
    out = Graph()
    stats = {}
    for kind, folder, study, opt in CLAIM_SETS:
        d = Path(results) / f"{folder}.tsv"
        if not d.exists():
            stats[folder] = "skipped (no results table)"
            continue
        if kind == "differential":
            g, n = differential(d, opt["datasets"], study, opt["experiment"])
        elif kind == "profile":
            g, n = profile(d, opt["datasets"], None, study, opt["experiment"])
        elif kind == "coexpression":
            g, n = coexpression(d, opt["datasets"], None, study, opt["assay"])
        else:
            g, n = pathway_coexpression(d, opt["datasets"], None, study, opt["assay"], pathway_iri)
        for p, ns in g.namespaces():
            out.bind(p, ns, override=False)
        out += g
        stats[folder] = f"{n} claims"
    for s in list(out):                                      # keep full double precision after merging
        if isinstance(s[2], Literal) and s[2].datatype == XSD.double and not isinstance(s[2], FullDouble):
            out.remove(s)
            out.add((s[0], s[1], double(s[2])))
    stats["distinct claims"] = len(set(out.subjects(RDF.subject, None)))
    return out, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--out", type=Path, default=PILOT / "transcriptomics.ttl")
    ap.add_argument("--pathway-iri", choices=["plantcyc", "pmw"], default="plantcyc",
                    help="pathway co-expression claims refer to the PlantCyc ID (stable; default) or to pathways/PC<n>")
    ap.add_argument("--refresh-genes", action="store_true", help="query PlantMetWiki and write a new gene snapshot")
    ap.add_argument("--refresh-pathways", action="store_true", help="query PlantMetWiki and write a new gene-pathway snapshot")
    a = ap.parse_args()
    if a.refresh_genes or a.refresh_pathways:
        if a.refresh_genes:
            refresh_genes()
        if a.refresh_pathways:
            refresh_pathways()
        return
    g, stats = build(pathway_iri=a.pathway_iri)
    g.serialize(destination=str(a.out), format="turtle")
    print(f"wrote {a.out.name}: {len(g)} triples; " + "; ".join(f"{k}: {v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
