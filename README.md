# LOD-pathways-community

This file serves as a reference for establishing a community of collaborators around a knowledge base to annotate pathway. 

## Overall aim and objectives

## Milestones 
- Write a collaborative whitepaper/opinion paper/review to agree on the vision 

## Collaborators (confirmed) 
- Elena Del Pup, Wageningen University, elena.delpup@wur.nl
- Marnix Medema 
- Justin van der Hooft
- Mitja Zdouc
- Tito Damiani
- Adriano Rutz
- Pierre-Marie Allard
- Denise Slenter
- Egon Willighagen
- Louis Felix Nothias
- Daniel Probst 

## Other potential collaborators (to be confirmed) 
- Yasin El Abiead
- Fabien Gandon at the INRIA

## Targeted Brainstorming - 14 October 
[Google doc notes](https://docs.google.com/document/d/15J9CHluMGA2IqFc5C-PF6YFRhbDHEHFe0tTbf9sYd4U/edit?tab=t.0)

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
  E1 --- B1[MIBiG BGC]
  E1 --- B2[(p)lantiSMASH-detected BGC]
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


