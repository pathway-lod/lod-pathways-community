# Case study: plantiSMASH 2.0 BGC predictions vs PlantMetWiki genes and pathways

All plantiSMASH BGCs are *predictions*. How many of them can be linked to PlantMetWiki genes and pathways, how much do they overlap, and which evidence must a link carry?

This pilot tests evidence case 1 (BGC predictions) in the [specification](../../specification/SPECIFICATION.md#2-bgc---plantismash-bgcs). The resulting evidence model is part of the [sample graph](../../README.md#sample-graph-the-four-cases-combined) there.

## Starting point

PlantMetWiki already links BGCs to pathways for *Arabidopsis thaliana* only ([`map-to-rdf`](https://doi.org/10.5281/zenodo.20640349)). That works because BGC genes and PlantCyc genes share TAIR locus IDs. For other species, plantiSMASH uses NCBI RefSeq gene models, which PlantCyc does not use.

## Inputs

| Input | Source |
|---|---|
| plantiSMASH 2.0 precalculated database: clusters, rules, core domains, genes, KnownClusterBLAST (MIBiG) matches | `plantismash.bioinformatics.nl/precalc/v2/<genome>/geneclusters.js`, 430 genomes |
| RefSeq and GenBank protein → UniProt accession and EC | UniProt ID-mapping service, snapshot `data/protein_to_uniprot.tsv.gz` |
| PlantMetWiki TAIR gene → pathway, pathway ECs, enzyme UniProt ids | SPARQL snapshots (2026-09-29): `data/plantmetwiki_tair_gene_pathways.csv`, and the snapshots of [`../meantools_overlap`](../meantools_overlap/) |
| PlantMetWiki pathway classes | reused from [`../metabolomics_overlap`](../metabolomics_overlap/) |

## Method

Each BGC gene is linked to PlantMetWiki pathways in three tiers, strongest first:

| Tier | Rule | Species |
|---|---|---|
| `gene_direct` | the BGC gene's TAIR locus is a gene of the pathway (the existing PlantMetWiki links) | *A. thaliana* |
| `gene_uniprot` | the BGC's *biosynthetic* protein (RefSeq/GenBank → UniProt) is an enzyme of the pathway | all |
| `gene_ec` | the biosynthetic protein's *complete* EC number (UniProt) catalyses a reaction of the pathway | all |

For every BGC the evidence points of the BGC use case in the [specification](../../specification/SPECIFICATION.md#2-bgc---plantismash-bgcs) are collected: the prediction, the detection rule(s) and core domains, the plantiSMASH version, the MIBiG match (% of genes similar) and the overlap with the pathway.

## Setup and run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # pinned versions
.venv/bin/python match_plantismash.py    # first run: downloads plantiSMASH (~15 min), maps proteins to UniProt
```

Then open [`explore_results.ipynb`](explore_results.ipynb) with the `.venv` kernel and **Run All**.

- The plantiSMASH website serves the current database, with no version or checksum. The per-genome cache `data/plantismash_v2/` is gitignored, so [`results/plantismash_clusters.csv.gz`](results/plantismash_clusters.csv.gz) is committed as the record of what was analysed.
- The index lists 431 entries; one (`tfbs-finder`) is a tool folder, not a genome.
- UniProt ID mapping returns incomplete results for very large jobs, so the script maps in batches of 10,000 IDs and prints how many each batch mapped.

## Outputs

- [`explore_results.ipynb`](explore_results.ipynb) holds the results with written interpretation.
- `results/plantismash_clusters.csv.gz`: one row per BGC (type, rules, core domains, MIBiG match).
- `results/bgc_pathway_links.csv.gz`: one row per BGC × pathway, with tier, linking genes and overlap values.
- `results/bgc_evidence.ttl`: a **draft** RDF export of the 448 BGC–pathway links of the direct and UniProt tiers and the 57 BGCs they involve. It does not conform to the [shape constraints](../../shape_constraints/) (for example, it has no anchor tier and attributes the link to plantiSMASH itself) and is superseded by `build_rdf.py bgc` there, which writes validated RDF.

## Results (2026-09-29)

- **The database:** 30,426 predicted BGCs in 430 genomes, with 161,054 biosynthetic genes. 17% of the BGCs are hybrids, and 5.5% have a KnownClusterBLAST hit to MIBiG (136 with 100% of the genes similar).
- **Direct links (*A. thaliana*):** 33 BGCs, 53 genes, 216 pathways. These include all 181 gene–pathway pairs of the `map-to-rdf` summary, plus more. The extra pairs probably come from a newer PlantMetWiki release (not verified).
- **Other species:** only about half of the biosynthetic proteins map to UniProt (49%), and only 6% to a *complete* EC number. The enzymes that define BGCs (P450s, glycosyltransferases) usually carry only partial ECs.

| Tier | BGCs linked | Species | Pathways |
|---|---|---|---|
| `gene_direct` | 33 | 1 | 216 |
| `gene_uniprot` | 43 | 8 | 139 |
| `gene_ec` | 5,237 | 238 | 538 |

- **The EC tier is imprecise.** In *A. thaliana*, only 30% of its BGC–pathway pairs are also direct pairs, and it finds 22% of the direct ones. It is not simply biased to primary pathways (35% primary, against 45% for direct links).
- **A shared-gene count does not make a link correct.** The thalianol cluster (`cluster-60`) links to *thalianol and derivatives biosynthesis* (3 of the pathway's 4 genes), but also to *heme degradation I* through the same three genes. A saccharide cluster links to *hypusine biosynthesis*. I have not investigated why, but such links should be checked before they are shown as facts.
- **MIBiG vs PlantMetWiki:** only 4 of the 136 complete MIBiG matches have a strong link. This mostly reflects the missing gene-ID bridge outside *A. thaliana*, not a gap in PlantMetWiki.
- **Evidence model:** all five evidence points can be expressed with existing terms (SO, ECO, SKOS, RO, PROV, SWO). Two gaps need small local vocabularies: the plantiSMASH detection rules and the overlap scores. See the main README.
- **PlantMetWiki's BGC graph** uses `obo:RO_0000051` for *has part*, which I could not find in the Ontology Lookup Service (the OBO term is `BFO:0000051`). It also lacks the evidence fields. Worth checking with the `map-to-rdf` authors.

## Caveats and next steps

- [ ] An identifier crosswalk (BridgeDb: RefSeq/NCBI Gene ↔ Phytozome/ITAG) to add direct links for the species PlantCyc curates, e.g. tomato and rice.
- [ ] Species-aware links: is the pathway recorded in PlantMetWiki for the BGC's species or genus?
- [ ] Check the odd links (e.g. cluster-60 ↔ heme degradation I) and decide how to flag them.
- [ ] A SKOS scheme for the 12 plantiSMASH detection rules, and properties for overlap scores.
- [ ] Load `results/bgc_evidence.ttl` next to PlantMetWiki in a test graph and write example SPARQL queries.
- [ ] Discuss the `RO_0000051` → `BFO:0000051` fix in `map-to-rdf`.
