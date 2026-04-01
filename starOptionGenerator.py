import argparse
from pbutils import GetDefaultMemoryLimit, GetNumCPUs
from PBOption import PBOption


class starOptionGenerator():
    """
    Used for rna_fq2bam, not starfusion.
    """
    def __init__(self, is_pipeline=False):
        self.allOptions = [
            PBOption(category="starOption", name="--out-prefix", helpStr="Prefix filename for output data."),
            PBOption(category="starOption", name="--read-files-command", helpStr="Command line to execute for each of the input files. This command should generate FASTA or FASTQ text and send it to stdout: For example, zcat to uncompress .gz files, bzcat to uncompress .bz2 files, etc."),
            PBOption(category="starOption", name="--read-group-sm", helpStr="SM tag for read groups in this run.", default=None),
            PBOption(category="starOption", name="--read-group-lb", helpStr="LB tag for read groups in this run.", default=None),
            PBOption(category="starOption", name="--read-group-pl", helpStr="PL tag for read groups in this run.", default=None),
            PBOption(category="starOption", name="--read-group-id-prefix", helpStr="Prefix for the ID and PU tags for read groups in this run. This prefix will be used for all pairs of FASTQ files in this run. The ID and PU tags will consist of this prefix and an identifier that will be unique for a pair of FASTQ files.", default=None),
            PBOption(category="starOption", name="--markdups-assume-sortorder-queryname", action="store_true", helpStr=argparse.SUPPRESS),#"Assume the reads are sorted by queryname for marking duplicates. This will mark secondary, supplementary, and unmapped reads as duplicates as well. This flag will not impact variant calling while increasing processing times."),
            PBOption(category="starOption", name="--optical-duplicate-pixel-distance", typeName=int, default=None, helpStr=argparse.SUPPRESS),#"The maximum offset between two duplicate clusters in order to consider them optical duplicates. Ignored if --out-duplicate-metrics is not passed."),

        ]
        self.perfOptions = [
            PBOption(category="starOption", name="--num-threads", default="auto", typeName=str, helpStr="Number of worker threads per GPU stream. Default is 'auto' which will configure based on GPU and system memory."),
            PBOption(category="starOption", name="--enable-gpu-helper-threads", default=0, typeName=int, helpStr="Number of worker threads that are enabled to share workload with the GPU. A small number of such threads can improve the overall performance on GPUs with lower compute capabilities."),
            PBOption(category="starOption", name="--num-streams-per-gpu", default="auto", typeName=str, helpStr="Number of streams per GPU. Default is 'auto' which will configure based on GPU memory and system memory."),
            PBOption(category="starOption", name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category="starOption", name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None)", typeName=int),
            PBOption(category="starOption", name="--gpusort", helpStr="Use GPUs to accelerate sorting and marking.", action="store_true"),
            PBOption(category="starOption", name="--use-gds", helpStr="Use GPUDirect Storage (GDS) to enable a direct data path for direct memory access (DMA) transfers between GPU memory and storage. Must be used concurrently with `--gpuwrite`. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.", action="store_true"),
            PBOption(category="starOption", name="--memory-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr="System memory limit in GBs during sorting and postsorting. By default, the limit is half of the total system memory."),
            PBOption(category="starOption", name="--low-memory", helpStr="Use low memory mode.", action="store_true", default=False),
            ]
        if not is_pipeline:
            self.allOptions.extend([
                PBOption(category="starOption", name="--num-sa-bases", default=14, typeName=int, helpStr="Length (bases) of the SA pre-indexing string. Longer strings will use more memory, but allow for faster searches. A value between 10 and 15 is recommended. For small genomes, the parameter must be scaled down to min(14, log2(GenomeLength)/2 - 1)."),
                PBOption(category="starOption", name="--max-intron-size", default=0, typeName=int, helpStr="Maximum align intron size. If this value is 0, the maximum size will be determined by (2^winBinNbits)*winAnchorDistNbins."),
                PBOption(category="starOption", name="--min-intron-size", default=21, typeName=int, helpStr="Minimum align intron size. Genomic gap is considered intron if its length is greater than or equal to this value, otherwise it is considered Deletion."),
                PBOption(category="starOption", name="--min-match-filter", default=0, typeName=int, helpStr="Minimum number of matched bases required for alignment output."),
                PBOption(category="starOption", name="--min-match-filter-normalized", default=0.66, typeName=float, helpStr="Same as --min-match-filter, but normalized to the read length (sum of the mate lengths for paired-end reads)."),
                PBOption(category="starOption", name="--out-filter-intron-motifs", default="None", helpStr="Type of filter alignment using its motifs. This string can be \"None\" for no filtering, \"RemoveNoncanonical\" for filtering out alignments that contain non-canonical junctions, or \"RemoveNoncanonicalUnannotated\" for filtering out alignments that contain non-canonical unannotated junctions when using the annotated splice junctions database. The annotated non-canonical junctions will be kept."),
                PBOption(category="starOption", name="--max-out-filter-mismatch", default=10, typeName=int, helpStr="Maximum number of mismatches allowed for an alignment to be output."),
                PBOption(category="starOption", name="--max-out-filter-mismatch-ratio", default=0.3, typeName=float, helpStr="Maximum ratio of mismatches to mapped length allowed for an alignment to be output."),
                PBOption(category="starOption", name="--max-out-filter-multimap", default=10, typeName=int, helpStr="Maximum number of loci the read is allowed to map to for all alignments to be output. Otherwise, no alignments will be output and the read will be counted as \"mapped to too many loci\" in the Log.final.out."),
                PBOption(category="starOption", name="--out-reads-unmapped", default="None", helpStr="Type of output of unmapped and partially mapped (i.e. mapped only one mate of a paired-end read) reads in separate file(s). This string can be \"None\" for no output or \"Fastx\" for output in separate FASTA/FASTQ files, Unmapped.out.mate1/2."),
                PBOption(category="starOption", name="--out-sam-unmapped", default="None", helpStr="Type of output of unmapped reads in SAM format. The string can be \"None\" to produce no output, \"Within\" to output unmapped reads within the main SAM file. Option \"Within_KeepPairs\" will produce the same result as \"Within\" because unmapped mates are ignored for sorted SAM/BAM output such as the output produced by this tool."),
                PBOption(category="starOption", name="--out-sam-attributes", default="Standard", nargs="+", helpStr="A string of SAM attributes in the order desired for the output SAM. The string can contain any combination of the following attributes: {NH, HI, AS, nM, NM, MD, jM, jI, XS, MC, ch}. Alternatively, the string can be \"None\" for no attributes, \"Standard\" for the attributes {NH, HI, AS, nM}, or \"All\" for the attributes {NH, HI, AS, nM, NM, MD, jM, jI, MC, ch} (e.g. \"--outSAMattributes NH nM jI XS ch\")."),
                PBOption(category="starOption", name="--out-sam-strand-field", default="None", helpStr="Cufflinks-like strand field flag. The string can be \"None\" for no flag or \"intronMotif\" for the strand derived from the intron motif. Reads with inconsistent and/or non-canonical introns will be filtered out."),
                PBOption(category="starOption", name="--out-sam-mode", default="Full", helpStr="SAM output mode. The string can be \"None\" for no SAM output, \"Full\" for full SAM output, or \"NoQS\" for full SAM output without quality scores."),
                PBOption(category="starOption", name="--out-sam-mapq-unique", default=255, typeName=int, helpStr="The MAPQ value for unique mappers. Must be in the range [0, 255]."),
                PBOption(category="starOption", name="--min-score-filter", default=0.66, typeName=float, helpStr="Minimum score required for alignment output, normalized to the read length (i.e. the sum of mate lengths for paired-end reads)."),
                PBOption(category="starOption", name="--min-spliced-mate-length", default=0.66, typeName=float, helpStr="Minimum mapped length for a read mate that is spliced and normalized to the mate length. Must be greater than 0."),
                PBOption(category="starOption", name="--max-junction-mismatches", default=[0, -1, 0, 0], nargs=4, typeName=int, helpStr="Maximum number of mismatches for stitching of the splice junctions. A limit must be specified for each of the following: (1) non-canonical motifs, (2) GT/AG and CT/AC motif, (3) GC/AG and CT/GC motif, (4) AT/AC and GT/AT motif. To indicate no limit for any of the four options, use -1."),
                PBOption(category="starOption", name="--max-out-read-size", default=100000, typeName=int, helpStr="Maximum size of the SAM record (bytes) for one read. Recommended value: > 2*(LengthMate1+LengthMate2+100)*outFilterMultimapNmax. Must be greater than 0."),
                PBOption(category="starOption", name="--max-alignments-per-read", default=10000, typeName=int, helpStr="Maximum number of different alignments per read to consider. Must be greater than 0."),
                PBOption(category="starOption", name="--score-gap", default=0, typeName=int, helpStr="Splice junction penalty (independent of intron motif)."),
                PBOption(category="starOption", name="--seed-search-start", default=50, typeName=int, helpStr="Defines the search start point through the read. The read split pieces will not be longer than this value. Must be greater than 0."),
                PBOption(category="starOption", name="--max-bam-sort-memory", default=0, typeName=int, helpStr="Maximum available RAM (bytes) for sorting BAM. If this value is 0, it will be set to the genome index size. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--align-ends-type", default="Local", helpStr="Type of read ends alignment. Can be one of two options: \"Local\" will perform a standard local alignment with soft-clipping allowed; \"EndToEnd\" will force an end-to-end read alignment with no soft-clipping."),
                PBOption(category="starOption", name="--align-insertion-flush", default="None", helpStr="Flush ambiguous insertion positions. The string can be \"None\" to not flush insertions or \"Right\" to flush insertions to the right."),
                PBOption(category="starOption", name="--max-align-mates-gap", default=0, typeName=int, helpStr="Maximum gap between two mates. If 0, the max intron gap will be determined by (2^winBinNbits)*winAnchorDistNbins."),
                PBOption(category="starOption", name="--min-align-spliced-mate-map", default=0, typeName=int, helpStr="Minimum mapped length for a read mate that is spliced. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--max-collapsed-junctions", default=1000000, typeName=int, helpStr="Maximum number of collapsed junctions. Must be greater than 0."),
                PBOption(category="starOption", name="--min-align-sj-overhang", default=5, typeName=int, helpStr="Minimum overhang (i.e. block size) for spliced alignments. Must be greater than 0."),
                PBOption(category="starOption", name="--min-align-sjdb-overhang", default=3, typeName=int, helpStr="Minimum overhang (i.e. block size) for annotated (sjdb) spliced alignments. Must be greater than 0."),
                PBOption(category="starOption", name="--sjdb-overhang", default=100, typeName=int, helpStr="Length of the donor/acceptor sequence on each side of the junctions. Ideally, this value should be equal to mate_length - 1. Must be greater than 0."),
                PBOption(category="starOption", name="--min-chim-overhang", default=20, typeName=int, helpStr="Minimum overhang for the Chimeric.out.junction file. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--min-chim-segment", default=0, typeName=int, helpStr="Minimum chimeric segment length. If it is set to 0, there will be no chimeric output. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--max-chim-multimap", default=0, typeName=int, helpStr="Maximum number of chimeric multi-alignments. If it is set to 0, the old scheme for chimeric detection, which only considered unique alignments, will be used. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--chim-multimap-score-range", default=1, typeName=int, helpStr="The score range for multi-mapping chimeras below the best chimeric score. This option only works with --max-chim-multimap > 1. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--chim-score-non-gtag", default=-1, typeName=int, helpStr="The penalty for a non-GT/AG chimeric junction."),
                PBOption(category="starOption", name="--min-non-chim-score-drop", default=20, typeName=int, helpStr="To trigger chimeric detection, the drop in the best non-chimeric alignment score with respect to the read length has to be smaller than this value. Must be greater than or equal to 0."),
                PBOption(category="starOption", name="--out-chim-format", default=0, typeName=int, helpStr="Formatting type for the Chimeric.out.junction file. Possible types are {0, 1}. If type 0, there will be no comment lines/headers. If type 1, there will be comment lines at the end of the file: command line and Nreads: total, unique, multi."),
                PBOption(category="starOption", name="--two-pass-mode", default="None", helpStr="Two-pass mapping mode. The string can be \"None\" for one-pass mapping or \"Basic\" for basic two-pass mapping, with all first pass junctions inserted into the genome indices on the fly."),
                PBOption(category="starOption", name="--out-chim-type", action='append', helpStr="Type of chimeric output. This string can be \"Junctions\" for Chimeric.out.junction, \"WithinBAM\" for main aligned BAM files (Aligned.*.bam), \"WithinBAM_HardClip\" for hard-clipping in the CIGAR for supplemental chimeric alignments, or \"WithinBAM_SoftClip\" for soft-clipping in the CIGAR for supplemental chimeric alignments."),
                PBOption(category="starOption", name="--no-markdups", action="store_true", helpStr="Do not perform the Mark Duplicates step. Return BAM after sorting."),
                PBOption(category="starOption", name="--read-name-separator", default="/", nargs="+", helpStr="Character(s) separating the part of the read names that will be trimmed in output (read name after space is always trimmed)."),
                # STAR Solo parameters
                PBOption(category="starOption", name="--soloType", default="None", helpStr="Type of single-cell RNA-seq. Can be \"None\" for no single-cell RNA-seq or \"Droplet\" for droplet single-cell RNA-seq."),
                PBOption(category="starOption", name="--soloBarcodeReadLength", default=0, typeName=int, helpStr="Length of the barcode read (the read containing cell barcode and UMI). If set to 0, barcode length equals the sum of cell barcode and UMI lengths."),
                PBOption(category="starOption", name="--soloCBwhitelist", helpStr="Path to file containing whitelist of cell barcodes. Required for --soloType Droplet."),
                PBOption(category="starOption", name="--soloCBstart", default=1, typeName=int, helpStr="Cell barcode start position (1-based) in the barcode read."),
                PBOption(category="starOption", name="--soloCBlen", default=16, typeName=int, helpStr="Cell barcode length."),
                PBOption(category="starOption", name="--soloUMIstart", default=17, typeName=int, helpStr="UMI start position (1-based) in the barcode read."),
                PBOption(category="starOption", name="--soloUMIlen", default=10, typeName=int, helpStr="UMI length."),
                PBOption(category="starOption", name="--soloFeatures", default=["Gene"], nargs="+", helpStr="Features type for which the UMI counts per Cell Barcode are collected. Can include one or more of: Gene, SJ, GeneFull."),
                PBOption(category="starOption", name="--soloStrand", default="Forward", helpStr="Strand for UMI-deduplication. Can be \"Unstranded\", \"Forward\", or \"Reverse\"."),
                PBOption(category="starOption", name="--quantMode", default=None, nargs="+", helpStr="Types of quantification requested. Can include: TranscriptomeSAM - output SAM/BAM alignments to transcriptome into a separate file, GeneCounts - output gene counts in ReadsPerGene.out.tab file")
            ])
        else:
            self.allOptions.extend([
                PBOption(category="starOption", name="--two-pass-mode", default="Basic", helpStr="Two-pass mapping mode. The string can be \"None\" for one-pass mapping or \"Basic\" for basic two-pass mapping with all 1st pass junctions inserted into the genome indices on the fly."),
                PBOption(category="starOption", name="--read-length", typeName=int, helpStr="Input read length used to determine sjdbOverhang.")
            ])
