
#!/usr/bin/env python3
"""
Arabidopsis heat-stress multi-omics pathway annotation.

Install:
    pip install pandas requests

Run:
    python map_omics_to_plantmetwiki.py --refresh

Optional:
    python map_omics_to_plantmetwiki.py --exact-inchikey

INPUTS
------
input/**/Significant_*.csv
results/metabolomics_biocyc.csv

OUTPUTS
-------
results/annotated_correlations/
results/mapping_tables/

PRIORITY
--------
Transcript:
    1. AGI -> pathway
    2. AGI -> UniProt -> pathway
    3. AGI -> UniProt -> EC -> pathway

Protein:
    1. UniProt -> pathway
    2. UniProt -> AGI -> pathway
    3. UniProt -> EC -> pathway

Metabolite:
    1. Full InChIKey -> pathway
    2. InChIKey first 14 characters -> pathway

The first successful tier wins.
All pathways within that tier are retained.
"""

from __future__ import annotations

import argparse
import re
import time

from collections import defaultdict
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIGURATION
# ============================================================

SPARQL_ENDPOINT = (
    "https://plantmetwiki.bioinformatics.nl/sparql"
)

UNIPROT_ENDPOINT = (
    "https://rest.uniprot.org/uniprotkb/search"
)

TAXON = 3702
TIMEOUT = 180
SPARQL_LIMIT_WARNING = 9500

PREFIX = """
PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
"""

AGI = re.compile(
    r"(?<![A-Za-z0-9])AT(?:[1-5]|M|C)G\d{5}(?!\d)",
    re.I
)

EC = re.compile(
    r"(?<![0-9.])(?:EC[- : ]*)?"
    r"(\d+\.\d+\.\d+\.\d+)(?![0-9.])",
    re.I
)

IK = re.compile(
    r"[A-Z]{14}-[A-Z]{10}-[A-Z]",
    re.I
)

PC = re.compile(
    r"(?:^|/)(PC\d+)(?:_[^/?#]*)?(?:[/?#]|$)",
    re.I
)

UNIPROT = re.compile(
    r"(?:"
    r"[OPQ][0-9][A-Z0-9]{3}[0-9]|"
    r"[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9])|"
    r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]"
    r"(?:[A-Z0-9]{3}[0-9])?"
    r")(?:-\d+)?",
    re.I
)

REQUIRED = {
    "Feature_1",
    "Feature_2",
    "Omics_Comparison",
    "p_value",
    "n_samples",
    "padj"
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def norm_name(value):
    value = clean(value).casefold()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"[()\[\],;:]", " ", value)

    return re.sub(
        r"\s+", " ", value
    ).strip()


def norm_key(value):
    return re.sub(
        r"[^a-z0-9]",
        "",
        clean(value).rsplit("/", 1)[-1].casefold()
    )


def agis(value):
    return {
        x.upper()
        for x in AGI.findall(clean(value))
    }


def ecs(value):
    return set(EC.findall(clean(value)))


def inchikeys(value):
    return {
        x.upper()
        for x in IK.findall(clean(value))
    }


def uniprots(value):
    value = clean(value).upper()

    if value.startswith(("SP|", "TR|")):
        value = value.split("|", 2)[1]

    pattern = (
        rf"(?<![A-Z0-9])"
        rf"(?:{UNIPROT.pattern})"
        rf"(?![A-Z0-9])"
    )

    return {
        m.group(0).split("-", 1)[0]
        for m in re.finditer(
            pattern, value, re.I
        )
    }


def pc_from_uri(value):
    match = PC.search(clean(value))

    return (
        match.group(1).upper()
        if match
        else ""
    )


def comparison(value):
    value = clean(value).casefold()

    if "transcript" in value and "proteom" in value:
        return "tp"

    if "transcript" in value and "metabolom" in value:
        return "tm"

    if "proteom" in value and "metabolom" in value:
        return "pm"

    return ""


def get_csv(path):
    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )

    df.columns = df.columns.str.strip()

    return df


# ============================================================
# HTTP AND CACHE
# ============================================================

def query_csv(session, endpoint, params, label):

    for attempt in range(4):

        try:
            headers = {
                "Accept": (
                    "text/csv"
                    if endpoint == SPARQL_ENDPOINT
                    else "text/tab-separated-values"
                ),
                "User-Agent": "Arabidopsis-omics-mapper/4.0"
            }

            response = session.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=TIMEOUT
            )

            response.raise_for_status()

            if not response.text.strip():
                raise RuntimeError(
                    f"{label}: empty response"
                )

            sep = (
                ","
                if endpoint == SPARQL_ENDPOINT
                else "\t"
            )

            return pd.read_csv(
                StringIO(response.text),
                sep=sep,
                dtype=str,
                keep_default_na=False
            )

        except (
            requests.RequestException,
            pd.errors.ParserError
        ) as exc:

            if attempt == 3:
                raise RuntimeError(
                    f"{label}: request failed: {exc}"
                ) from exc

            time.sleep(2 ** attempt)


def cached_sparql(
    session, cache_dir, name, query, refresh=False
):

    path = cache_dir / f"{name}.csv"

    if path.exists() and not refresh:
        return get_csv(path)

    df = query_csv(
        session,
        SPARQL_ENDPOINT,
        {"query": PREFIX + query},
        name
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(path, index=False)

    return df


# ============================================================
# SPARQL QUERIES
# ============================================================

PATHWAYS_QUERY = """
SELECT DISTINCT
    ?pc ?plantcyc_id ?pathway_name
WHERE {
    ?pw a wp:Pathway ;
        v:plantcycId ?plantcyc_id ;
        dc:identifier ?id .

    OPTIONAL {
        ?pw dc:title ?pathway_name .
    }

    BIND(
        REPLACE(STR(?id), "^.*/", "")
        AS ?pc
    )
}
"""

PROPERTY_PATTERN = (
    r"uniprot|tair|ensembl|agi|gene.?id|"
    r"unique.?id|^ec.?number|^ec$|"
    r"enzyme.?commission|inchi.?key"
)

PROPERTY_QUERY = """
SELECT DISTINCT
    ?gp ?element ?propertyKey ?propertyValue
WHERE {
    ?element dcterms:isPartOf ?gp ;
             v:gpmlProperty ?property .

    ?property v:key ?propertyKey ;
              v:value ?propertyValue .

    FILTER(
        REGEX(
            STR(?propertyKey),
            '%s',
            'i'
        )
    )

    %s
}
"""

METABOLITES_QUERY = """
SELECT DISTINCT
    ?inchikey ?plantcyc_id ?pathway
WHERE {
    ?m a wp:Metabolite ;
       wp:bdbInChIKey ?ik ;
       dcterms:isPartOf ?pw .

    ?pw a wp:Pathway ;
        v:plantcycId ?plantcyc_id .

    OPTIONAL {
        ?pw dc:title ?pathway .
    }

    BIND(
        REPLACE(
            REPLACE(
                STR(?ik), "^.*/", ""
            ),
            "^InChIKey=", "", "i"
        ) AS ?inchikey
    )

    FILTER(
        STRSTARTS(UCASE(?inchikey), "%s")
    )
}
"""

METABOLITE_COUNT_QUERY = """
SELECT (COUNT(DISTINCT ?m) AS ?n)
WHERE {
    ?m a wp:Metabolite ;
       wp:bdbInChIKey ?ik ;
       dcterms:isPartOf ?pw .

    ?pw a wp:Pathway ;
        v:plantcycId ?plantcyc_id .
}
"""


# ============================================================
# PATHWAY CATALOGUE
# ============================================================

def load_pathway_catalog(session, cache, refresh):

    df = cached_sparql(
        session,
        cache,
        "pathway_catalog",
        PATHWAYS_QUERY,
        refresh
    )

    needed = {"pc", "plantcyc_id"}

    if not needed.issubset(df.columns):
        raise RuntimeError(
            f"Pathway catalog missing {needed - set(df.columns)}"
        )

    df["pc"] = df["pc"].map(
        lambda x: pc_from_uri(x) or clean(x).upper()
    )

    df["plantcyc_id"] = df["plantcyc_id"].map(
        lambda x: clean(x).rsplit("/", 1)[-1]
    )

    if "pathway_name" not in df:
        df["pathway_name"] = ""

    df = df[
        df["pc"].str.fullmatch(r"PC\d+")
        & df["plantcyc_id"].ne("")
        & ~df["plantcyc_id"].str.contains(
            "RXN", case=False
        )
    ].drop_duplicates()

    if df.empty:
        raise RuntimeError(
            "No valid PlantCyc pathways"
        )

    ambiguous = (
        df.groupby("pc")["plantcyc_id"]
        .nunique()
        .max()
    )

    if ambiguous > 1:
        raise RuntimeError(
            "One PC maps to multiple PlantCyc IDs"
        )

    return df


# ============================================================
# GPML PARTITIONING
# ============================================================

def gpml_prefix_filter(prefix, exact=False):

    prefix = str(prefix)

    if not re.fullmatch(r"[0-9]+", prefix):
        raise ValueError(
            f"Invalid PC prefix: {prefix}"
        )

    suffix = (
        r"(_|$)"
        if exact
        else r"[0-9]*(_|$)"
    )

    return (
        f'FILTER(REGEX(STR(?gp), '
        f'"/Pathway/PC{prefix}{suffix}"))'
    )


def property_rows(session, cache, refresh):

    needed = {
        "gp",
        "element",
        "propertyKey",
        "propertyValue"
    }

    def fetch_partition(name, filter_clause):

        df = cached_sparql(
            session,
            cache,
            name,
            PROPERTY_QUERY % (
                PROPERTY_PATTERN,
                filter_clause
            ),
            refresh
        )

        if not needed.issubset(df.columns):
            raise RuntimeError(
                f"{name}: missing GPML columns"
            )

        return df

    def fetch_prefix(prefix, depth=0):

        if depth > 12:
            raise RuntimeError(
                f"Maximum GPML partition depth: PC{prefix}"
            )

        label = f"gpml_properties_PC{prefix}"

        part = fetch_partition(
            label,
            gpml_prefix_filter(prefix)
        )

        if len(part) < SPARQL_LIMIT_WARNING:
            return [part]

        print(
            f"{label}: {len(part)} rows; splitting"
        )

        exact = fetch_partition(
            f"{label}_exact",
            gpml_prefix_filter(prefix, exact=True)
        )

        if len(exact) >= SPARQL_LIMIT_WARNING:
            raise RuntimeError(
                f"Exact PC{prefix} may be truncated"
            )

        children = []

        for digit in "0123456789":
            children.extend(
                fetch_prefix(prefix + digit, depth + 1)
            )

        return [exact, *children]

    all_df = fetch_partition(
        "gpml_properties_all",
        ""
    )

    if len(all_df) < SPARQL_LIMIT_WARNING:
        df = all_df

    else:
        print(
            "GPML query may be truncated; "
            "partitioning by PC prefix"
        )

        parts = []

        for digit in "0123456789":
            parts.extend(fetch_prefix(digit))

        df = pd.concat(
            parts,
            ignore_index=True
        ).drop_duplicates()

    df["pc"] = df["gp"].map(pc_from_uri)

    result = df[
        df["pc"].ne("")
    ].copy()

    print(
        "GPML property rows:",
        len(result)
    )

    return result


# ============================================================
# GPML GENE / PROTEIN / EC EVIDENCE
# ============================================================

def build_gpml_evidence(raw, catalog):

    id_map = dict(
        zip(catalog["pc"], catalog["plantcyc_id"])
    )

    name_map = dict(
        zip(catalog["pc"], catalog["pathway_name"])
    )

    records = []

    for row in raw.itertuples(index=False):

        pc = clean(row.pc)
        pathway = id_map.get(pc, "")

        if not pathway:
            continue

        key = norm_key(row.propertyKey)
        value = clean(row.propertyValue)

        found = []

        if (
            key in {
                "uniqueid",
                "geneid",
                "agiid",
                "tairid",
                "alternativeidtair",
                "alternativeidensemblplants",
                "ensemblplants",
                "tair"
            }
            or key.endswith("tair")
        ):
            found.extend(
                ("gene", x, "gene_locus", 1)
                for x in agis(value)
            )

        if "uniprot" in key:
            found.extend(
                ("uniprot", x, "protein_direct", 1)
                for x in uniprots(value)
            )

        if (
            key in {
                "ec",
                "ecnumber",
                "ecnumbers",
                "enzymecommission",
                "enzymecommissionnumber"
            }
            or key.startswith("ecnumber")
        ):
            found.extend(
                ("ec", x, "ec_functional", 3)
                for x in ecs(value)
            )

        for typ, ident, tier, rank in found:

            records.append({
                "identifier_type": typ,
                "identifier": ident,
                "pc": pc,
                "plantcyc_id": pathway,
                "pathway_name": name_map.get(pc, ""),
                "tier": tier,
                "rank": rank,
                "property_key": row.propertyKey,
                "property_value": value,
                "element_uri": row.element,
                "gpml_uri": row.gp
            })

    columns = [
        "identifier_type",
        "identifier",
        "pc",
        "plantcyc_id",
        "pathway_name",
        "tier",
        "rank",
        "property_key",
        "property_value",
        "element_uri",
        "gpml_uri"
    ]

    return pd.DataFrame(
        records,
        columns=columns
    ).drop_duplicates()


# ============================================================
# COLLECT FEATURES
# ============================================================

def collect_features(tables):

    accessions = set()
    genes = set()
    mets = set()

    for df in tables:

        for row in df.itertuples(index=False):

            kind = comparison(row.Omics_Comparison)

            if kind in ("tp", "tm"):
                genes.update(agis(row.Feature_1))

            if kind in ("tp", "pm"):

                protein = (
                    row.Feature_2
                    if kind == "tp"
                    else row.Feature_1
                )

                accessions.update(
                    uniprots(protein)
                )

                genes.update(agis(protein))

            if kind in ("tm", "pm"):
                mets.add(norm_name(row.Feature_2))

    return accessions, genes, mets


# ============================================================
# UNIPROT — IMPROVED
# ============================================================

def load_uniprot(
    session, accessions, genes, cache, refresh
):

    # New cache name prevents loading the old,
    # less complete UniProt columns.
    path = cache / "uniprot_arabidopsis_v4.csv"

    if path.exists() and not refresh:
        raw = get_csv(path)

    else:
        frames = []

        for label, values, field in (
            ("accessions", sorted(accessions), "accession"),
            ("genes", sorted(genes), "gene_exact")
        ):

            for start in range(0, len(values), 25):

                batch = values[start:start + 25]

                query = (
                    "("
                    + " OR ".join(
                        f"{field}:{x}"
                        for x in batch
                    )
                    + f") AND organism_id:{TAXON}"
                )

                frames.append(
                    query_csv(
                        session,
                        UNIPROT_ENDPOINT,
                        {
                            "query": query,
                            "format": "tsv",
                            "size": 500,
                            "fields": (
                                "accession,reviewed,"
                                "protein_name,ec,"
                                "gene_names,gene_oln,"
                                "xref_tair,"
                                "xref_ensemblplants,"
                                "xref_araport"
                            )
                        },
                        f"UniProt {label}"
                    )
                )

                time.sleep(0.15)

        raw = (
            pd.concat(
                frames,
                ignore_index=True
            ).drop_duplicates()
            if frames
            else pd.DataFrame()
        )

        raw.to_csv(path, index=False)

    if raw.empty:
        return pd.DataFrame(
            columns=[
                "uniprot_id",
                "gene_id",
                "ec_number"
            ]
        )

    col = {
        re.sub(
            r"[^a-z0-9]", "", key.lower()
        ): key
        for key in raw.columns
    }

    entry = col.get("entry")

    if not entry:
        raise RuntimeError(
            f"UniProt response lacks Entry: {list(raw)}"
        )

    gene_cols = [
        col[k]
        for k in (
            "tair",
            "ensemblplants",
            "araport",
            "crossreferencetair",
            "crossreferenceensemblplants",
            "crossreferencearaport",
            "genenames",
            "genenamesorderedlocus"
        )
        if k in col
    ]

    ec_col = col.get("ecnumber")

    records = []

    for _, row in raw.iterrows():

        accession = clean(row[entry]).upper()

        row_genes = (
            set().union(
                *(
                    agis(row[column])
                    for column in gene_cols
                )
            )
            if gene_cols
            else set()
        )

        row_ecs = (
            ecs(row[ec_col])
            if ec_col
            else set()
        )

        # Preserve proteins even if no gene or EC is known.
        for gene in sorted(row_genes) or [""]:

            for ec in sorted(row_ecs) or [""]:

                records.append(
                    (accession, gene, ec)
                )

    return pd.DataFrame(
        records,
        columns=[
            "uniprot_id",
            "gene_id",
            "ec_number"
        ]
    ).drop_duplicates()


# ============================================================
# BIOCYC
# ============================================================

def load_biocyc(path):

    bio = get_csv(path)

    columns = {
        norm_key(c): c
        for c in bio.columns
    }

    query_col = columns.get("query")
    ik_col = columns.get("inchikey")

    if not query_col or not ik_col:
        raise ValueError(
            "BioCyc CSV requires Query and InChIKey columns"
        )

    bio = bio.rename(
        columns={
            query_col: "Query",
            ik_col: "InChiKey"
        }
    )

    by_name = defaultdict(set)

    for row in bio.itertuples(index=False):
        by_name[
            norm_name(row.Query)
        ].update(
            inchikeys(row.InChiKey)
        )

    by_name.pop("", None)

    return bio, by_name


# ============================================================
# RDF METABOLITE MEMBERSHIPS
# ============================================================

def load_metabolite_memberships(
    session, bio_index, cache, refresh
):

    keys = (
        set().union(*bio_index.values())
        if bio_index
        else set()
    )

    columns = [
        "inchikey",
        "plantcyc_id",
        "pathway"
    ]

    if not keys:
        return pd.DataFrame(columns=columns)

    def fetch(prefix, depth=0):

        if depth > 14:
            raise RuntimeError(
                f"Metabolite partition too deep: {prefix}"
            )

        name = f"metabolite_memberships_v3_{prefix}"

        part = cached_sparql(
            session,
            cache,
            name,
            METABOLITES_QUERY % prefix,
            refresh
        )

        if not set(columns).issubset(part.columns):
            raise RuntimeError(
                f"Unexpected metabolite columns: {list(part)}"
            )

        if len(part) < SPARQL_LIMIT_WARNING:
            return [part]

        print(
            f"Metabolite prefix {prefix}: splitting"
        )

        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"

        if len(prefix) < 14:
            children = sorted({
                k[len(prefix)]
                for k in keys
                if k.startswith(prefix)
                and len(k) > len(prefix)
            })
        else:
            children = list(alphabet)

        if not children:
            raise RuntimeError(
                f"Cannot subdivide {prefix}"
            )

        parts = []

        for character in children:
            parts.extend(
                fetch(prefix + character, depth + 1)
            )

        return parts

    frames = []

    for first in sorted({
        key[0] for key in keys
    }):
        frames.extend(fetch(first))

    result = (
        pd.concat(
            frames,
            ignore_index=True
        ).drop_duplicates()
        if frames
        else pd.DataFrame(columns=columns)
    )

    print(
        "RDF metabolite membership rows:",
        len(result)
    )

    if result.empty:
        probe = cached_sparql(
            session,
            cache,
            "metabolite_membership_probe_v3",
            METABOLITE_COUNT_QUERY,
            refresh
        )

        print(
            "RDF membership probe:",
            probe.to_dict("records")
        )

        return result

    result["inchikey"] = result["inchikey"].map(
        lambda x: next(
            iter(sorted(inchikeys(x))), ""
        )
    )

    result["plantcyc_id"] = result[
        "plantcyc_id"
    ].map(
        lambda x: clean(x).rsplit("/", 1)[-1]
    )

    return result[
        result["inchikey"].ne("")
        & result["plantcyc_id"].ne("")
    ].drop_duplicates()


# ============================================================
# GPML METABOLITE MEMBERSHIPS
# ============================================================

def build_gpml_metabolite_memberships(raw, catalog):

    pc_to_id = dict(
        zip(
            catalog["pc"],
            catalog["plantcyc_id"]
        )
    )

    pc_to_name = dict(
        zip(
            catalog["pc"],
            catalog["pathway_name"]
        )
    )

    rows = []

    for row in raw.itertuples(index=False):

        if "inchikey" not in norm_key(row.propertyKey):
            continue

        pathway = pc_to_id.get(clean(row.pc), "")

        if not pathway:
            continue

        for key in inchikeys(row.propertyValue):
            rows.append({
                "inchikey": key,
                "plantcyc_id": pathway,
                "pathway": pc_to_name.get(clean(row.pc), ""),
                "mapping_source": "gpml_inchikey"
            })

    return pd.DataFrame(
        rows,
        columns=[
            "inchikey",
            "plantcyc_id",
            "pathway",
            "mapping_source"
        ]
    ).drop_duplicates()


def combine_metabolite_memberships(
    rdf_memberships, gpml_memberships
):

    columns = [
        "inchikey",
        "plantcyc_id",
        "pathway",
        "mapping_source"
    ]

    rdf = rdf_memberships.copy()
    gpml = gpml_memberships.copy()

    if "mapping_source" not in rdf:
        rdf["mapping_source"] = "rdf_bdbInChIKey"

    for frame in (rdf, gpml):
        for column in columns:
            if column not in frame:
                frame[column] = ""

    combined = pd.concat(
        [rdf[columns], gpml[columns]],
        ignore_index=True
    ).drop_duplicates()

    return combined[
        combined["inchikey"].ne("")
        & combined["plantcyc_id"].ne("")
        & ~combined["plantcyc_id"].str.contains(
            "RXN",
            case=False,
            na=False
        )
    ].reset_index(drop=True)


# ============================================================
# METABOLITE DIAGNOSTICS
# ============================================================

def diagnose_metabolites(
    bio_index, memberships, directory
):

    exact = defaultdict(set)
    block = defaultdict(set)

    for row in memberships.itertuples(index=False):
        exact[row.inchikey].add(row.plantcyc_id)
        block[row.inchikey[:14]].add(row.plantcyc_id)

    rows = []

    for name, keys in sorted(bio_index.items()):

        full = set()
        connectivity = set()

        for key in keys:
            full.update(exact.get(key, ()))
            connectivity.update(block.get(key[:14], ()))

        tier = (
            "exact_inchikey"
            if full
            else "connectivity_14"
            if connectivity
            else "missing_biocyc_inchikey"
            if not keys
            else "not_in_plantmetwiki"
        )

        selected = full or connectivity

        rows.append({
            "metabolite_lookup_key": name,
            "biocyc_inchikeys": "; ".join(sorted(keys)),
            "match_tier": tier,
            "n_pathways": len(selected),
            "plantcyc_pathways": "; ".join(sorted(selected))
        })

    df = pd.DataFrame(
        rows,
        columns=[
            "metabolite_lookup_key",
            "biocyc_inchikeys",
            "match_tier",
            "n_pathways",
            "plantcyc_pathways"
        ]
    )

    df.to_csv(
        directory / "metabolite_mapping_diagnostics.csv",
        index=False
    )

    print(
        "Metabolite diagnostics:",
        df["match_tier"].value_counts().to_dict()
    )

    return df


# ============================================================
# BUILD MAPPING INDEXES
# ============================================================

def make_indexes(
    evidence,
    uniprot_map,
    memberships,
    catalog,
    bio_index,
    connectivity=True
):

    genes = defaultdict(
        lambda: defaultdict(set)
    )

    proteins = defaultdict(
        lambda: defaultdict(set)
    )

    ecpath = defaultdict(
        lambda: defaultdict(set)
    )

    for row in evidence.itertuples(index=False):

        target = {
            "gene": genes,
            "uniprot": proteins,
            "ec": ecpath
        }[row.identifier_type]

        target[
            row.identifier
        ][
            row.plantcyc_id
        ].add((
            row.tier,
            f"GPML:{row.property_key}={row.property_value}"
        ))

    # Bidirectional UniProt <-> AGI.
    gene_to_up = defaultdict(set)
    up_to_gene = defaultdict(set)
    up_to_ec = defaultdict(set)

    for row in uniprot_map.itertuples(index=False):

        if row.gene_id:
            gene_to_up[row.gene_id].add(
                row.uniprot_id
            )

            up_to_gene[row.uniprot_id].add(
                row.gene_id
            )

        if row.ec_number:
            up_to_ec[row.uniprot_id].add(
                row.ec_number
            )

    # Metabolite indexes.
    exact = defaultdict(set)
    block = defaultdict(set)

    catalog_ids = set(catalog["plantcyc_id"])

    unknown_pathways = (
        set(memberships["plantcyc_id"])
        - catalog_ids
    )

    if unknown_pathways:
        print(
            "Metabolite pathways outside catalogue:",
            len(unknown_pathways)
        )

    for row in memberships.itertuples(index=False):

        exact[row.inchikey].add(row.plantcyc_id)
        block[row.inchikey[:14]].add(row.plantcyc_id)

    # --------------------------------------------------------
    # PROTEIN RESOLVER — UPDATED
    # --------------------------------------------------------

    def protein_result(accession):

        out = defaultdict(set)

        # Tier 1: direct UniProt -> pathway.
        for pathway, sources in proteins.get(
            accession, {}
        ).items():

            for _, via in sources:
                out[pathway].add((
                    "protein_direct",
                    f"UniProt:{accession};{via}"
                ))

        if out:
            return out

        # Tier 2: UniProt -> AGI -> pathway.
        for gene in up_to_gene.get(accession, ()):

            for pathway, sources in genes.get(
                gene, {}
            ).items():

                for _, via in sources:
                    out[pathway].add((
                        "protein_gene_locus",
                        f"UniProt:{accession};AGI:{gene};{via}"
                    ))

        if out:
            return out

        # Tier 3: UniProt -> EC -> pathway.
        for ec in up_to_ec.get(accession, ()):

            for pathway in ecpath.get(ec, {}):
                out[pathway].add((
                    "protein_ec",
                    f"UniProt:{accession};EC:{ec}"
                ))

        return out

    # --------------------------------------------------------
    # TRANSCRIPT RESOLVER — PRIORITY UNCHANGED
    # --------------------------------------------------------

    def gene_result(gene):

        out = defaultdict(set)

        # Tier 1: direct AGI -> pathway.
        for pathway, sources in genes.get(
            gene, {}
        ).items():
            out[pathway].update(sources)

        if out:
            return out

        accessions = gene_to_up.get(gene, set())

        # Tier 2: AGI -> UniProt -> pathway.
        for up in accessions:

            for pathway, sources in proteins.get(
                up, {}
            ).items():

                for _, via in sources:
                    out[pathway].add((
                        "gene_uniprot",
                        f"UniProt:{up};{via}"
                    ))

        if out:
            return out

        # Tier 3: AGI -> UniProt -> EC -> pathway.
        for up in accessions:

            for ec in up_to_ec.get(up, ()):

                for pathway in ecpath.get(ec, {}):
                    out[pathway].add((
                        "gene_ec",
                        f"UniProt:{up};EC:{ec}"
                    ))

        return out

    # --------------------------------------------------------
    # METABOLITE RESOLVER — UNCHANGED
    # --------------------------------------------------------

    def metabolite_result(name):

        keys = bio_index.get(
            norm_name(name), ()
        )

        out = defaultdict(set)

        # Tier 1: full InChIKey.
        for ik in keys:

            for pathway in exact.get(ik, ()):
                out[pathway].add((
                    "metabolite_exact_inchikey",
                    f"BioCyc:{ik}"
                ))

        if out or not connectivity:
            return out

        # Tier 2: 14-character connectivity block.
        for ik in keys:

            for pathway in block.get(ik[:14], ()):
                out[pathway].add((
                    "metabolite_connectivity",
                    f"BioCyc:key14:{ik[:14]}"
                ))

        return out

    return (
        gene_result,
        protein_result,
        metabolite_result
    )


# ============================================================
# TIER LABELS
# ============================================================

def best_tier(evidences):

    order = {
        "gene_locus": 1,
        "gene_uniprot": 2,
        "gene_ec": 3,

        "protein_direct": 1,
        "protein_gene_locus": 2,
        "protein_ec": 3,

        "metabolite_exact_inchikey": 1,
        "metabolite_connectivity": 2
    }

    return min(
        (tier for tier, _ in evidences),
        key=lambda tier: order.get(tier, 99)
    )


# ============================================================
# ANNOTATE CORRELATIONS
# ============================================================

def annotate(
    df, indexes, detailed_rows, filename
):

    gene_result, protein_result, metabolite_result = indexes

    output = df.copy()

    new_columns = [
        "Feature1_mapped_pathway",
        "Feature2_mapped_pathway",
        "pathway_relationship",
        "shared_pathway_ids",
        "Feature1_mapping_tier",
        "Feature2_mapping_tier",
        "pathway_mapping_status"
    ]

    additions = {
        column: []
        for column in new_columns
    }

    for i, row in enumerate(df.itertuples(index=False)):

        kind = comparison(row.Omics_Comparison)

        a = clean(row.Feature_1)
        b = clean(row.Feature_2)

        first = defaultdict(set)
        second = defaultdict(set)

        # Feature 1.
        if kind in ("tp", "tm"):

            for gene in agis(a):

                for pathway, evidence in gene_result(
                    gene
                ).items():
                    first[pathway].update(evidence)

        elif kind == "pm":

            if agis(a):
                for gene in agis(a):
                    for pathway, evidence in gene_result(
                        gene
                    ).items():
                        first[pathway].update(evidence)

            else:
                for up in uniprots(a):
                    for pathway, evidence in protein_result(
                        up
                    ).items():
                        first[pathway].update(evidence)

        # Feature 2.
        if kind == "tp":

            if agis(b):
                for gene in agis(b):
                    for pathway, evidence in gene_result(
                        gene
                    ).items():
                        second[pathway].update(evidence)

            else:
                for up in uniprots(b):
                    for pathway, evidence in protein_result(
                        up
                    ).items():
                        second[pathway].update(evidence)

        elif kind in ("tm", "pm"):
            second = metabolite_result(b)

        shared = set(first) & set(second)

        additions[
            "Feature1_mapped_pathway"
        ].append(
            "; ".join(sorted(first))
        )

        additions[
            "Feature2_mapped_pathway"
        ].append(
            "; ".join(sorted(second))
        )

        additions[
            "shared_pathway_ids"
        ].append(
            "; ".join(sorted(shared))
        )

        relationship = (
            "same"
            if shared
            else "different"
            if first and second
            else "not_comparable"
        )

        additions[
            "pathway_relationship"
        ].append(relationship)

        additions[
            "Feature1_mapping_tier"
        ].append(
            "; ".join(sorted({
                best_tier(ev)
                for ev in first.values()
            }))
        )

        additions[
            "Feature2_mapping_tier"
        ].append(
            "; ".join(sorted({
                best_tier(ev)
                for ev in second.values()
            }))
        )

        status = (
            "unknown_comparison"
            if not kind
            else "both_mapped"
            if first and second
            else "feature1_only"
            if first
            else "feature2_only"
            if second
            else "neither_mapped"
        )

        additions[
            "pathway_mapping_status"
        ].append(status)

        # Evidence provenance.
        for feature_no, name, resolved in (
            (1, a, first),
            (2, b, second)
        ):

            for pathway, ev in resolved.items():

                for tier, via in sorted(ev):

                    detailed_rows.append({
                        "file": filename,
                        "row_number": i + 2,
                        "feature_side": feature_no,
                        "feature_original": name,
                        "plantcyc_id": pathway,
                        "tier": tier,
                        "via": via,
                        "is_shared": pathway in shared
                    })

    for name, values in additions.items():
        output[name] = values

    if len(output) != len(df):
        raise RuntimeError(
            "Annotation changed row count"
        )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parent
    )

    parser.add_argument(
        "--refresh",
        action="store_true"
    )

    parser.add_argument(
        "--exact-inchikey",
        action="store_true"
    )

    args = parser.parse_args()

    base = args.project_dir.resolve()

    results = base / "results"
    mapping = results / "mapping_tables"
    annotations = results / "annotated_correlations"

    mapping.mkdir(
        parents=True,
        exist_ok=True
    )

    annotations.mkdir(
        parents=True,
        exist_ok=True
    )

    paths = sorted(
        (base / "input").rglob(
            "Significant_*.csv"
        )
    )

    if not paths:
        parser.error(
            "No Significant_*.csv input files found"
        )

    tables = [
        get_csv(path)
        for path in paths
    ]

    for path, df in zip(paths, tables):

        missing = REQUIRED - set(df.columns)

        has_coefficient = bool(
            {"Pearson_r", "Spearman_rho"} & set(df.columns)
        )

        if missing or not has_coefficient:
            raise ValueError(
                f"{path}: missing {sorted(missing)} "
                "or correlation coefficient"
            )

    bio, bio_index = load_biocyc(
        results / "metabolomics_biocyc.csv"
    )

    accessions, genes, mets = collect_features(tables)

    print(
        f"Inputs: {len(paths)} files; "
        f"{len(genes)} genes; "
        f"{len(accessions)} proteins; "
        f"{len(mets)} metabolites"
    )

    with requests.Session() as session:

        catalog = load_pathway_catalog(
            session, mapping, args.refresh
        )

        raw = property_rows(
            session, mapping, args.refresh
        )

        evidence = build_gpml_evidence(
            raw, catalog
        )

        uniprot_map = load_uniprot(
            session,
            accessions,
            genes,
            mapping,
            args.refresh
        )

        rdf_memberships = load_metabolite_memberships(
            session,
            bio_index,
            mapping,
            args.refresh
        )

    gpml_memberships = build_gpml_metabolite_memberships(
        raw, catalog
    )

    memberships = combine_metabolite_memberships(
        rdf_memberships,
        gpml_memberships
    )

    print(
        "RDF memberships:",
        len(rdf_memberships)
    )

    print(
        "GPML memberships:",
        len(gpml_memberships)
    )

    print(
        "Combined memberships:",
        len(memberships)
    )

    diagnose_metabolites(
        bio_index, memberships, mapping
    )

    # Save mapping tables.
    catalog.to_csv(
        mapping / "plantcyc_pathway_catalog.csv",
        index=False
    )

    raw.to_csv(
        mapping / "gpml_properties_parsed.csv",
        index=False
    )

    evidence.to_csv(
        mapping / "gpml_identifier_evidence.csv",
        index=False
    )

    uniprot_map.to_csv(
        mapping / "uniprot_species_mapping.csv",
        index=False
    )

    rdf_memberships.to_csv(
        mapping / "rdf_metabolite_memberships.csv",
        index=False
    )

    gpml_memberships.to_csv(
        mapping / "gpml_metabolite_memberships.csv",
        index=False
    )

    memberships.to_csv(
        mapping / "metabolite_pathway_memberships.csv",
        index=False
    )

    bio[["Query", "InChiKey"]].drop_duplicates().to_csv(
        mapping / "metabolite_inchikey_mapping.csv",
        index=False
    )

    # Report metabolite identifier overlap.
    available_full = set(memberships["inchikey"])

    requested = (
        set().union(*bio_index.values())
        if bio_index
        else set()
    )

    print(
        "BioCyc exact InChIKey hits:",
        len(requested & available_full)
    )

    print(
        "BioCyc connectivity hits:",
        len(
            {x[:14] for x in requested}
            & {x[:14] for x in available_full}
        )
    )

    indexes = make_indexes(
        evidence,
        uniprot_map,
        memberships,
        catalog,
        bio_index,
        connectivity=not args.exact_inchikey
    )

    details = []
    totals = []

    for path, df in zip(paths, tables):

        annotated = annotate(
            df,
            indexes,
            details,
            str(path.relative_to(base))
        )

        dest = (
            annotations
            / f"{path.stem}_annotated.csv"
        )

        annotated.to_csv(
            dest,
            index=False
        )

        counts = (
            annotated["pathway_relationship"]
            .value_counts()
            .to_dict()
        )

        totals.append({
            "input": str(path.relative_to(base)),
            "rows": len(df),
            **counts
        })

        print(
            f"{dest.name}: {counts}"
        )

    pd.DataFrame(
        details,
        columns=[
            "file",
            "row_number",
            "feature_side",
            "feature_original",
            "plantcyc_id",
            "tier",
            "via",
            "is_shared"
        ]
    ).to_csv(
        mapping / "mapping_provenance.csv",
        index=False
    )

    pd.DataFrame(totals).fillna(0).to_csv(
        mapping / "mapping_coverage.csv",
        index=False
    )

    print("\nCompleted.")
    print("Results:", results)
    print("Pathways:", len(catalog))
    print("GPML evidence:", len(evidence))
    print("Metabolite memberships:", len(memberships))


if __name__ == "__main__":
    main()
