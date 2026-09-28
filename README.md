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
%%{init: {"theme": "base", "themeVariables": {"fontSize": "16px"}}}%%

flowchart RL

%% =========================
%%   GENOMICS / ENZYMES (TOP)
%% =========================
subgraph A[Genomics & Enzymes]
direction RL
  E1 --- O1[Orthologs/other species]:::genomic
  E1 --- T1[Transcriptomics]:::genomic
  E2 --- T2[Transcriptomics]:::genomic
  B1[BGC MIBiG/antiSMASH]:::reaction --- E1
  B1[BGC MIBiG/antiSMASH]:::reaction --- E2
end

%% =========================
%%   REACTION / PATHWAY (MIDDLE)
%% =========================
subgraph B[Reaction / Pathway]
direction LR
  E1[Enzyme A]:::genomic --> R
  E2[Enzyme B]:::genomic --> R
  WP[WikiPathways]:::reaction --- R
end

%% =========================
%%   METABOLOMICS / EVIDENCE (BOTTOM)
%% =========================
subgraph C[Metabolomics & Databases]
direction LR
  S[Substrate]:::chemical --> R((Reaction)):::reaction --> P[Product]:::chemical
  S --- SS[Spectral data]:::chemical
  S --- SM[Metabolomics]:::chemical
  S --- SN[LOTUS / Wikidata]:::chemical
  SN[LOTUS / Wikidata] --- WP[WikiPathways]

  P --- PS1[Spectral data]:::chemical
  P --- PM[Metabolomics]:::chemical
  P --- PN[LOTUS / Wikidata]:::chemical
end

%% =========================
%%   COLORS
%% =========================
classDef reaction fill:#fca5a5,stroke:#b91c1c,stroke-width:2px,color:#7f1d1d;
classDef genomic  fill:#86efac,stroke:#15803d,stroke-width:2px,color:#064e3b;
classDef chemical fill:#d8b4fe,stroke:#7e22ce,stroke-width:2px,color:#3b0764;
```


# Git track 
Committed to GitHub with https://github.com/Vinzent03/obsidian-git 