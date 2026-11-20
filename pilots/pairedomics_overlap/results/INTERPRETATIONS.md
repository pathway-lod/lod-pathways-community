# Curating biological interpretations

[association_interpretations.csv](association_interpretations.csv) is a curation
worksheet derived from the committed cluster_pairs.csv, gene_pathway_map.csv,
and metabolite_pathway_map.csv. It does not assert biological mechanisms and is
not yet consumed by the RDF builder.

There is one row per exact transcript identifier × metabolite feature, combining
repeated cluster memberships: 8,657 pairs (7,512 positive, 570 negative, 575 with
no recorded direct correlation). Transcript versions are retained. Statistics
were checked for agreement across repeated memberships before deduplication.
Cluster IDs and their p-values are retained together; significant_cluster_ids
uses the existing cluster_P < 0.05 convention, not a pair-level significance test.

## How to curate

1. Filter association_type to direct_correlation for signed interpretations.
   Examine pair statistics, cluster context, and sample-level profiles. P is
   copied unchanged into pair_p_value; its adjustment status is not inferred.
   adjusted_p_value and multiple_testing_method remain blank until verified.
   Correcting only this cluster-selected subset would not recover correction
   across the original tested family.
2. Check the gene mapping tier and metabolite candidates. These metabolite
   matches are mass-only; they include alternative identities and adducts.
   Candidate names are connectivity-level labels, not resolved identities.
3. Replace interpretation_type = unassigned with a proposed explanation, e.g.
   product_accumulation, substrate_consumption, shared_response,
   competing_branch, or unexplained. Sign alone is insufficient to choose one.
4. Record the candidate_metabolite and reaction_id the explanation depends on,
   if applicable. Fill biological_context, supporting_reference, curator,
   rationale, and validation_needed. Record unresolved assumptions explicitly.
5. Change interpretation_status from not_reviewed to hypothesis when a reasoned
   explanation has been recorded. A curator may mark an explanation supported
   or rejected only with an accompanying rationale and independent evidence.
   These are worksheet conventions, not currently enforced SHACL terms.

For alternative explanations, duplicate the row, assign a distinct interpretation_id
(e.g. append _hypothesis2), and retain its original gene, feature and statistics.
Blank interpretation fields mean not assessed, not negative evidence.

Missing correlations remain blank with association_type = cluster_comembership_only;
they are not assigned zero or a sign. Blank shared_pathways indicates no recorded
shared-pathway mapping, not proof that the biological association is absent.

For later RDF integration, the current validated builder creates one association
per locus × feature × cluster (and filters by significance, available statistics,
and anchoring). This worksheet instead retains transcript IDs and combines clusters;
interpretation_id is a worksheet identifier, not an existing association IRI.
A future exporter must map to the appropriate existing association claims explicitly.
