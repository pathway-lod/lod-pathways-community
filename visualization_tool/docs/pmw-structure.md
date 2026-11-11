# PlantMetWiki structure for the global view

Input for building the centre of the global view: a simplified PlantMetWiki (PMW) of about 100 to 1,000 nodes, with
the user's data placed on it. **PMW always means PlantMetWiki.** All numbers come from the live endpoint
<https://plantmetwiki.bioinformatics.nl/sparql> on 2026-11-11 (release in the IRIs: `r17.0.0_20260605-171052`);
the queries are at the end, so you can re-run them.

D5 (no PMW queries) is cancelled by D24 (see [decisions.md](decisions.md)): the viewer may use PMW content, from a
shipped snapshot and/or live SPARQL (CORS is open).

## Goal (Martin, 2026-11-11)

In the global view, PMW sits in the middle as a simplified graph. The user sees which parts of PMW their data maps to
(and which data maps nowhere).

## 1. What PMW contains

| Thing | Count | How to recognise it |
|---|---|---|
| `wp:Pathway` total | 2,478 | |
| PlantCyc pathways | 1,162 | IRI contains `/pathways/PC`; all have a PlantCyc class |
| Single orphan reactions | 1,316 | IRI contains `/pathways/RC`; title = reaction id (`RXN-16329`) or enzyme name; only GPML key `UniqueID`, **no class** |
| `wp:Metabolite` | 4,577 | `dc:source`: InChIKey 4,111, ChEBI 174, MetaNetX 172, PubChem 75, KEGG 43, HMDB 2 |
| Metabolites in ≥1 PlantCyc pathway | 3,810 | |
| `wp:Protein` | 3,750 | `dc:source`: Uniprot-TrEMBL 1,797, plantcyc 1,633, TAIR gene name 316, ... |
| `wp:GeneProduct` | 3,666 | `dc:source`: plantcyc 1,369, TAIR gene name 955, Entrez Gene 361, ... |
| BGCs (`pmw-vocab:BiosyntheticGeneCluster`) | 108 | 1,412 `obo:RO_0000051` (has part) links; graphs `bgc-plantismash`, `bgc-mibig`. Whether their parts are the same IRIs as pathway genes: **not checked** |

Prefixes: `wp: <http://vocabularies.wikipathways.org/wp#>`, `v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>`,
`dc: <http://purl.org/dc/elements/1.1/>`, `dct: <http://purl.org/dc/terms/>`.

**Data node IRIs are the identifiers themselves** (e.g. `https://identifiers.org/inchikey/...`,
`https://identifiers.org/uniprot/...`). They are linked to their pathways by `dct:isPartOf`. A user anchor IRI can be
matched to PMW by string equality: the metabolomics pilot's `lodp:anchoredToMetabolite` values are the same
InChIKey IRIs. On a 30-claim sample, 25 of 26 anchors were found in PMW.

**Use `v:plantcycId` (`PWY-7205`) as the stable pathway key, not the PC number.** All 1,162 PC pathways have one, and
the ids are unique. PC numbers changed since the 2026-10-01 snapshot (PC1159 is now CoA biosynthesis), so `PC<n>` IRIs are
not stable across releases.

### Pathway properties (GPML key/value pairs)

Stored as `?pathway v:gpmlProperty ?gp . ?gp v:key ?k ; v:value ?val` (graph `gpml-properties-extra`). Useful keys:
`UniqueID` (PWY id), `Type`, `Type_1`, `Type_2`, `Type_3` (PlantCyc pathway class), `ReactionIDs`, `PathwayLinks`
(622 pathways, e.g. `(CPD-14501 PWY-7070)` = links to other pathways through a compound), `ReactionCount`,
`PrimaryCompoundCount`, `Organism`, `TaxonomicRange_n`.

Compounds carry `Smiles` (21,976 values), `Inchi`, `InchiKey`, `AlternativeId_Chebi` (20,109), PubChem, HMDB, etc.
(counts are property values, not distinct compounds), so compound classes can be computed from PMW content.

`wp:ontologyTag` on pathways = **NCBITaxon only** (424 taxa; Arabidopsis 3702 on 1,038 pathways). Use it as a species
filter, not as a clustering.

### Pathway classes

- 1,162 of 1,162 PlantCyc pathways have a class. 397 distinct classes; 274 pathways have 2 or more, 30 have 3.
- Largest: Super-Pathways 113, Metabolic-Clusters 43, FLAVONOL-SYN 33, ANTHOCYANIN-SYN 29, ISOFLAVONOID-SYN 28,
  TRITERPENOID-SYN 27, SESQUITERPENOID-SYN 24, Glycosylation-Pathways 22, DITERPENOID-SYN 21, Lipid-Biosynthesis 17,
  Interconversion 17, ALKALOIDS-SYN 17, ISOFLAVONOID-PHYTOALEXINS 17, MONOTERPENOID-SYN 16, COUMARIN-SYN 15,
  FLAVONE-SYN 15, C40-Carotenoids-Biosynthesis 14.
- `Super-Pathways` and `Metabolic-Clusters` are bookkeeping classes, not biology. Place those pathways by their other
  class, or by the classes of their member pathways.
- Only the **leaf** class is stored (sometimes a higher one, e.g. SECONDARY-METABOLITE-BIOSYNTHESIS 7, FLAVONOID-SYN 8).
  **The class hierarchy is not in PMW** (graph `vocabularies` has 26 `rdfs:subClassOf`, none for these classes). It
  has to come from the PlantCyc/MetaCyc pathway ontology (`classes.dat` in the PMN data download). Availability and
  licence: **not checked**.

### Hub metabolites

PlantCyc pathways per metabolite (3,810 metabolites):

| Pathways | Metabolites |
|---|---|
| 1 | 2,192 |
| 2-3 | 1,020 |
| 4-10 | 418 |
| 11-50 | 138 |
| >50 | 42 |

Top: H+ `GPRLSGONYQIRFK-UHFFFAOYSA-N` 898, water `XLYOFNOQVPJJNP-UHFFFAOYSA-N` 754, O2 `MYMOFIZGZYHOMD-UHFFFAOYSA-N`
388, then `XPPKVPWEQAFLFU-UHFFFAOYSA-K` 303, `CURLTUGMZLYLDI-UHFFFAOYSA-N` (CO2) 294, ... So 84 % of metabolites
are in at most 3 pathways, and a few dozen currency metabolites would light up the whole map if counted naively.

## 2. Options for the simplified PMW

1. **PlantCyc pathway-class tree (recommended by Claude, not yet decided by Martin).** Probably about 10 top classes,
   about 100 mid classes, 397 leaf classes, then 1,162 pathways (the top/mid counts are a guess until the hierarchy
   is loaded). Natural levels of about 100 and 1,000 nodes, PlantCyc's own vocabulary, deterministic. Fits a
   sunburst or circle packing in the centre; clicking a segment zooms in. Open: the hierarchy source (above), where
   the 1,316 orphan reactions go (one "reactions outside pathways" segment, or the class of the pathways they share
   non-hub metabolites with), and the Super-Pathways / Metabolic-Clusters rule.
2. **Compound-class tree** (NPClassifier: about 7 pathways / 70 superclasses / 670 classes, or ClassyFire), computed
   from PMW SMILES/InChIKeys. Each metabolite has exactly one place, so there is no hub problem. But it shows
   chemistry, not PMW's structure, and cannot place genes or BGCs. Better as a switchable second view for
   metabolomics data.
3. **Data-driven communities** (e.g. Leiden on a pathway-pathway graph through shared non-hub metabolites, or through
   `PathwayLinks`): about 50-150 unnamed clusters that need labels (e.g. majority class). Less explainable and
   seed-dependent (layout must stay deterministic, CLAUDE.md rule 2). Use it only as a check of option 1.
4. **Taxonomy**: a filter only.

## 3. Mapping user data onto it

- Metabolite anchor (InChIKey IRI) → `dct:isPartOf` pathways → their class(es) → up the tree.
- Gene/protein anchor → same route, when the IRI matches one of the identifier schemes above (check how the
  paired-omics pilot writes gene IRIs before relying on this).
- Pathway anchor (`pmw:PC<n>`) → class directly. Because of the PC renumbering, prefer matching by PlantCyc id
  where the data has it.
- **Hubs:** either drop metabolites above a cutoff (e.g. >50 pathways) or give each anchor weight 1/n over its n
  pathways. Without this, one water anchor colours the whole map.
- Not found in PMW → the separate "not linked" area of the global view (D21).

## 4. Suggested implementation

- A build script (Python, next to `tools/build_viewer_bundle.py`) that queries PMW once and writes a snapshot JSON:
  the class tree, PWY id → (class, PC IRI, title, size), and an index from data-node IRI to PWY ids. Size estimate
  1-2 MB (not measured). The viewer loads it like the other bundles, with an optional live SPARQL check.
- Record the PMW release (from the pathway IRIs) in the snapshot, so a stale snapshot can be detected.

## Queries used

Run with `curl -s -G https://plantmetwiki.bioinformatics.nl/sparql -H 'Accept: text/csv' --data-urlencode "query=..."`.
Virtuoso gotcha: a query with single-quoted string literals inside nested `IF(...)` failed with
`SP030 ... End-of-line in a short single-quoted string`; using double-quoted literals worked.

```sparql
# classes per pathway (Type, Type_1..3)
SELECT ?pw ?pwy ?c WHERE {
  ?pw a wp:Pathway ; v:plantcycId ?pwy ; v:gpmlProperty ?gp .
  ?gp v:key ?k ; v:value ?c FILTER(STRSTARTS(?k, "Type"))
}

# metabolite -> PlantCyc pathways
SELECT ?m ?pw WHERE {
  ?m a wp:Metabolite ; dct:isPartOf ?pw FILTER(CONTAINS(STR(?pw), "/pathways/PC"))
}

# pathways per metabolite (histogram input)
SELECT ?n (COUNT(*) AS ?metabolites) WHERE {
  { SELECT ?m (COUNT(DISTINCT ?pw) AS ?n) WHERE {
      ?m a wp:Metabolite ; dct:isPartOf ?pw FILTER(CONTAINS(STR(?pw), "/pathways/PC")) } GROUP BY ?m }
} GROUP BY ?n ORDER BY ?n

# all GPML keys with an example value
SELECT ?k (COUNT(*) AS ?n) (SAMPLE(?val) AS ?ex) WHERE {
  GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/gpml-properties-extra> { ?gp v:key ?k ; v:value ?val }
} GROUP BY ?k ORDER BY DESC(?n)
```
