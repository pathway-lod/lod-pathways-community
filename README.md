# LOD-pathways-community

This file serves as a reference for establishing a community of collaborators around a knowledge base to annotate pathway. 

## Collaborators 
- Elena Del Pup, Wageningen University, elena.delpup@wur.nl
- Marnix Medema 
- Justin van der Hoooft
- Mitja Zdouc
- Tito Damiani
- Adriano Rutz
- Pierre-Marie Allard
- Denise Slenter
- Egon Willighagen
- Louis Felix Nothias
- Daniel Probst 

## Other potential collaborators 
- 

## Mermaid plot for rendering of the knowledge graph 

```mermaid

flowchart LR
  S[Substrate] --> R((Reaction))
  R --> P[Product]

  %% Enzymes in plantiSMASH clusters
  E1[Enzyme A] --> R
  E2[Enzyme B] --> R

  %% Per-enzyme context
  E1 --- O1[Orthologs]
  E1 --- T1[Transcriptomics]
  E2 --- O2[Orthologs]
  E2 --- T2[Transcriptomics]

  %% Evidence for substrate
  S --- SS[Spectral data]
  S --- SM[Metabolomics]
  S --- SN[LOTUS / Wikidata]

  %% Evidence for product
  P --- PS1[Spectral data]
  P --- PM[Metabolomics]
  P --- PN[LOTUS / Wikidata]

  %% Curated knowledge
  R --- WP[WikiPathways]

```


