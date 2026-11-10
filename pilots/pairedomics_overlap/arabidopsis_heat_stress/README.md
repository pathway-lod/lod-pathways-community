# Pilot: paired omics (transcriptomics, proteomics, and metabolomics) vs PlantMetWiki
Thirumalaikumar, V.P., Yu, L., Arora, D. et al. Multi-Omics Dataset of Heat Stress-Induced Memory in Arabidopsis. Sci Data 13, 1447 (2026). https://doi.org/10.1038/s41597-026-07813-z

**Heat stress priming of Arabidopsis seedlings, measured paired omics data for timepoints: 1d, 2d, 3d, 4d**
five-day-old seedlings were subjected to a heat regime of 1.5 h at 37 °C (incubator), 1.5 h recovery at 22 °C, and 45 min at 44 °C (hot water bath)

**four biological replicates**

**Transcriptomics raw:** SRA SRP589115

**Proteomics raw:** MassIVE repository MSV000098061

**Metabolomics raw:** MassIVE repository MSV000098074

**Analysis reported:**

_Transcriptomics:_ Illumina HiSeq. 4000 platform (100 bp single-end reads), Sequencing adaptors and low-quality bases were removed using Trimmomatic v0.38[25](https://www.nature.com/articles/s41597-026-07813-z#ref-CR25), and reads shorter than 25 bp were discarded. Filtered short reads were then aligned to the Arabidopsis reference genome using Hisat2 with default settings, and the gene-level transcription abundance was quantified using featureCounts[26](https://www.nature.com/articles/s41597-026-07813-z#ref-CR26), parameter: (-t exon, -g gene ID, -s 0) based on the latest gene annotation of Arabidopsis[27](https://www.nature.com/articles/s41597-026-07813-z#ref-CR27). To ensure accuracy, only uniquely mapped reads were retained to avoid multiple counting of ambiguously aligned reads. Gene expression profiling was performed using the DESeq 2 package in R/Bioconductor

_Proteomics:_ Q-Exactive (Thermo Fisher Scientific, Dreieich, Germany) mass spectrometer coupled to an EASY-nLC 1000 system, Proteome Discoverer (version 2.5, Thermo Fisher Scientific) software using the Arabidopsis protein database (Version 10, The Arabidopsis Information Resource, [www.arabidopsis.org](http://www.arabidopsis.org/)). An in-house list of common contaminants was added to the search. SEQUEST HT was used to assign the peptides, allowing a maximum of 2 missed tryptic cleavages. Additionally, a minimum peptide length of six amino acids, a precursor mass tolerance of 10 ppm, and a fragment mass tolerance of 0.02 Da were selected. Carbamidomethylation of cysteines and oxidation of methionine were specified as static and dynamic modifications, respectively. False discovery rates (FDRs) of 0.01 and 0.05 validated peptide spectral matches at high and medium confidence, respectively. Label-free quantification (LFQ) based on MS1 precursor ion intensity was performed in Proteome Discoverer with a minimum Quan value threshold set to 0.0001 for unique peptides. The ‘Top 3N’ peptides were used for area calculation. The normalized protein abundances were used among the samples, and values were log2-transformed and imputed using a normal distribution pattern.

_Metabolomics_: GC-TOF-MS untargeted metabolomics workflow using two-step derivatization (methoxyamination + MSTFA), followed by peak detection and compound annotation with TargetSearch.
