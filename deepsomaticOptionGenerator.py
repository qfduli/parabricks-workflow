from PBOption import PBOption


class deepsomaticOptionGenerator():
    def __init__(self, is_pipeline=False, is_denovomutation=False, is_pacbio_germline=False):
        self.allOptions = [
            PBOption(category="deepvariantOption", name="--disable-use-window-selector-model", action="store_true", helpStr="Change the window selector model from Allele Count Linear to Variant Reads. This option will increase the accuracy and runtime."),
            #PBOption(category="deepvariantOption", name="--gvcf", action="store_true", helpStr="Generate variant calls in .gvcf Format."),
            PBOption(category="deepvariantOption", name="--norealign-reads", action="store_true", helpStr="Do not locally realign reads before calling variants. Reads longer than 500 bp are never realigned."),
            PBOption(category="deepvariantOption", name="--sort-by-haplotypes", action="store_true", helpStr="Reads are sorted by haplotypes (using HP tag)."),
            #PBOption(category="deepvariantOption", name="--keep-duplicates", action="store_true", helpStr="Keep reads that are duplicate."),
            PBOption(category="deepvariantOption", name="--vsc-min-count-snps", typeName=int, helpStr="SNP alleles occurring at least this many times in the AlleleCount will be advanced as candidates."),
            PBOption(category="deepvariantOption", name="--vsc-min-count-indels", typeName=int, helpStr="Indel alleles occurring at least this many times in the AlleleCount will be advanced as candidates."),
            PBOption(category="deepvariantOption", name="--vsc-min-fraction-snps", typeName=float, helpStr="SNP alleles occurring at least this fraction of all counts in the AlleleCount will be advanced as candidates."),
            PBOption(category="deepvariantOption", name="--vsc-min-fraction-indels", typeName=float, helpStr="Indel alleles occurring at least this fraction of all counts in the AlleleCount will be advanced as candidates."),
            PBOption(category="deepvariantOption", name="--min-mapping-quality", typeName=int, helpStr="By default, reads with any mapping quality are kept. Setting this field to a positive integer i will only keep reads that have a MAPQ >= i. Note this only applies to aligned reads."),
            #PBOption(category="deepvariantOption", name="--min-base-quality", default=10, typeName=int, helpStr="Minimum base quality. This option enforces a minimum base quality score for alternate alleles. Alternate alleles will only be considered if all bases in the allele have a quality greater than min_base_quality."),
            PBOption(category="deepvariantOption", name="--mode", default="shortread", helpStr="Value can be one of [shortread, pacbio, ont]. By default, it is shortread."),
            PBOption(category="deepvariantOption", name="--alt-aligned-pileup", helpStr="Value can be one of [none, diff_channels]. Include alignments of reads against each candidate alternate allele in the pileup image."),
            #PBOption(category="deepvariantOption", name="--variant-caller", helpStr="Value can be one of [VERY_SENSITIVE_CALLER, VCF_CANDIDATE_IMPORTER]. The caller to use to make examples. If you use VCF_CANDIDATE_IMPORTER, it implies force calling. Default is VERY_SENSITIVE_CALLER."),
            PBOption(category="deepvariantOption", name="--add-hp-channel", action="store_true", helpStr="Add another channel to represent HP tags per read."),
            PBOption(category="deepvariantOption", name="--parse-sam-aux-fields", action="store_true", helpStr="Auxiliary fields of the BAM/CRAM records are parsed. If either --sort-by-haplotypes or --add-hp-channel is set, then this option must also be set."),
            PBOption(category="deepvariantOption", name="--use-wes-model", action="store_true", helpStr="If passed, the WES model file will be used. Only used in shortread mode."),
            #PBOption(category="deepvariantOption", name="--include-med-dp", action="store_true", helpStr="If True, include MED_DP in the output gVCF records."),
            #PBOption(category="deepvariantOption", name="--normalize-reads", action="store_true", helpStr="If True, allele counter left align INDELs for each read."),
            PBOption(category="deepvariantOption", name="--pileup-image-width", typeName=int, helpStr="Pileup image width. Only change this if you know your model supports this width."), # in base pairs?
            # PBOption(category="deepvariantOption", name="--channel-insert-size", action="store_true", helpStr="If True, add insert_size channel into pileup image. By default, this parameter is true."),
            PBOption(category="deepvariantOption", name="--no-channel-insert-size", action="store_true", default=False, helpStr="If True, don't add insert_size channel into the pileup image."),
            #PBOption(category="deepvariantOption", name="--max-read-size-512", action="store_true", helpStr="Allow deepvariant to run on reads of size 512bp. The default size is 320 bp."),
            #PBOption(category="deepvariantOption", name="--prealign-helper-thread", action="store_true", helpStr="Use an extra thread for the pre-align step. This parameter is more useful when --max-reads-size-512 is set."),
            PBOption(category="deepvariantOption", name="--track-ref-reads", action="store_true", helpStr="If True, allele counter keeps track of reads supporting ref.  By default, allele counter keeps a simple count of the number of reads supporting ref."),
            PBOption(category="deepvariantOption", name="--phase-reads", action="store_true", helpStr="Calculate phases and add HP tag to all reads automatically."),
            #PBOption(category="deepvariantOption", name="--dbg-min-base-quality", default=15, typeName=int, helpStr="Minimum base quality in a k-mer sequence to consider."),
            #PBOption(category="deepvariantOption", name="--ws-min-windows-distance", default=80, typeName=int, helpStr="Minimum distance between candidate windows for local assembly."),
            #PBOption(category="deepvariantOption", name="--channel-gc-content", action="store_true", helpStr="If specified, add gc_content channel into the pileup image."),
            #PBOption(category="deepvariantOption", name="--channel-hmer-deletion-quality", action="store_true", helpStr="If specified, add hmer deletion quality channel into the pileup image."),
            #PBOption(category="deepvariantOption", name="--channel-hmer-insertion-quality", action="store_true", helpStr="If specified, add hmer insertion quality channel into the pileup image."),
            #PBOption(category="deepvariantOption", name="--channel-non-hmer-insertion-quality", action="store_true", helpStr="If specified, add non-hmer insertion quality channel into the pileup image."),
            #PBOption(category="deepvariantOption", name="--skip-bq-channel", action="store_true", helpStr="If specified, ignore base quality channel."),
            #PBOption(category="deepvariantOption", name="--aux-fields-to-keep", default="HP", helpStr="Comma-delimited list of auxiliary BAM fields to keep. Values can be [HP, tp, t0]."),
            #PBOption(category="deepvariantOption", name="--vsc-min-fraction-hmer-indels", typeName=float, helpStr="Hmer Indel alleles occurring at least this be advanced as candidates. Use this threshold if hmer and non-hmer indels should be treated differently (Ultima reads)Default will use the same threshold for hmer and non-hmer indels, as defined in vsc_min_fraction_indels."),
            #PBOption(category="deepvariantOption", name="--vsc-turn-on-non-hmer-ins-proxy-support", action="store_true", helpStr="Add read-support from soft-clipped reads and other non-hmer insertion alleles,to the most frequent non-hmer insertion allele."),
            #PBOption(category="deepvariantOption", name="--consider-strand-bias", action="store_true", helpStr="If specified, expect SB field in calls and write it to the VCF file."),
            #PBOption(category="deepvariantOption", name="--p-error", default=0.001, typeName=float, helpStr="Basecalling error for reference confidence model."),
            #PBOption(category="deepvariantOption", name="--channel-ins-size", action="store_true", helpStr="If specified, add another channel to represent size of insertions (good for flow-based sequencing)."),
            #PBOption(category="deepvariantOption", name="--max-ins-size", default=10, typeName=int, helpStr="Max insertion size for ins_size_channel, larger insertions will look like max (have max intensity)."),
            #PBOption(category="deepvariantOption", name="--disable-group-variants", action="store_true", helpStr="If using vcf_candidate_importer and multi-allelic sites are split across multiple lines in VCF, add this flag so that variants are not grouped when transforming CallVariantsOutput to Variants."),
            #PBOption(category="deepvariantOption", name="--filter-reads-too-long", action="store_true", helpStr="Ignore all input BAM reads with size > 512bp."),
            #PBOption(category="deepvariantOption", name="--haploid-contigs", required=False, helpStr="Optional list of non autosomal chromosomes. For all listed chromosomes HET probabilities are not considered."),
            PBOption(category="deepvariantOption", name="--vsc-max-fraction-indels-for-non-target-sample", typeName=float, default=0.5, helpStr="Maximum fraction of indels allowed in non-target samples."),
            PBOption(category="deepvariantOption", name="--vsc-max-fraction-snps-for-non-target-sample", typeName=float, default=0.5, helpStr="Maximum fraction of snps allowed in non-target samples."),
            # Remove for v4.6
            # PBOption(category="deepvariantOption", name="--create-complex-alleles", action="store_true", helpStr="If specified, create complex alleles."),
            # PBOption(category="deepvariantOption", name="--realign-all", action="store_true", helpStr="If specified, realign all reads. With this option window selector is not used."),
            # PBOption(category="deepvariantOption", name="--max-read-length-to-realign", default=500, typeName=int, helpStr="If specified, realign all reads with length <= this value. Set to 0 to realign all reads."),
        ]
        self.perfOptions = [
            PBOption(category="deepvariantOption", name="--num-cpu-threads-per-stream", default=6, typeName=int, helpStr="Number of CPU threads to use per stream."),
            PBOption(category="deepvariantOption", name="--num-streams-per-gpu", default="auto", typeName=str, helpStr="Number of streams to use per GPU. Default is 'auto' which will try to use an optimal amount of streams based on the GPU."),
            PBOption(category="deepvariantOption", name="--run-partition", action="store_true", helpStr="Divide the whole genome into multiple partitions and run multiple processes at the same time, each on one partition."),
            PBOption(category="deepvariantOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr="Number of GPUs to use per partition."),
            #PBOption(category="deepvariantOption", name="--use-tf32", action="store_true", helpStr="Enable inference optimization using Tensor Float 32(TF32) on ampere+ gpu. Note that this might introduce a few mismatches in the output VCF."),
            #PBOption(category="deepvariantOption", name="--max-reads-per-partition", default=1500, typeName=int, helpStr="The maximum number of reads per partition that are considered before following processing such as sampling and realignment."),
            PBOption(category="deepvariantOption", name="--partition-size", typeName=int, helpStr="The maximum number of basepairs allowed in a region before splitting it into multiple smaller subregions."),
        ]
        if not is_pipeline:
            self.allOptions.extend([
                PBOption(category="deepvariantOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call the variants from the BAM/CRAM file. Overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            ])
