from PBOption import PBOption


class mutectOptionGenerator():
    def __init__(self, is_pipeline=False):
        self.allOptions = [
            PBOption(category="mutectOption", name="--max-mnp-distance", default=1, typeName=int, helpStr="Two or more phased substitutions separated by this distance or less are merged into MNPs."),
            PBOption(category="mutectOption", name="--mutectcaller-options", helpStr="Pass supported mutectcaller options as one string. The following are currently supported original mutectcaller options: -pcr-indel-model <NONE, HOSTILE, AGGRESSIVE, CONSERVATIVE>, -max-reads-per-alignment-start <int>, -A <AssemblyComplexity>, -min-dangling-branch-length <int> (e.g. --mutectcaller-options=\"-pcr-indel-model HOSTILE -max-reads-per-alignment-start 30\")."),
            PBOption(category="mutectOption", name="--initial-tumor-lod", required=False, typeName=float, helpStr="Log 10 odds threshold to consider pileup active."),
            PBOption(category="mutectOption", name="--tumor-lod-to-emit", required=False, typeName=float, helpStr="Log 10 odds threshold to emit variant to VCF."),
            PBOption(category="mutectOption", name="--pruning-lod-threshold", required=False, typeName=float, helpStr="Ln likelihood ratio threshold for adaptive pruning algorithm."),
            PBOption(category="mutectOption", name="--active-probability-threshold", required=False, typeName=float, helpStr="Minimum probability for a locus to be considered active."),
            PBOption(category="mutectOption", name="--no-alt-contigs", action="store_true", helpStr="Ignore commonly known alternate contigs."),
            PBOption(category="mutectOption", name="--genotype-germline-sites", action="store_true", helpStr="Call all apparent germline site even though they will ultimately be filtered."),
            PBOption(category="mutectOption", name="--genotype-pon-sites", action="store_true", helpStr="Call sites in the PoN even though they will ultimately be filtered."),
            PBOption(category="mutectOption", name="--force-call-filtered-alleles", action="store_true", helpStr="Force-call filtered alleles included in the resource specified by --alleles."),
            PBOption(category="mutectOption", name="--filter-reads-too-long", action="store_true", helpStr="Ignore all input BAM reads with size > 500bp."),
            
            PBOption(category="mutectOption", name="--minimum-mapping-quality", required=False, typeName=int, helpStr="Minimum mapping quality to keep (inclusive)."),
            PBOption(category="mutectOption", name="--min-base-quality-score", required=False, typeName=int, helpStr="Minimum base quality required to consider a base for calling."),
            PBOption(category="mutectOption", name="--f1r2-median-mq", required=False, typeName=int, helpStr="skip sites with median mapping quality below this value."),
            PBOption(category="mutectOption", name="--base-quality-score-threshold", required=False, typeName=int, helpStr="Base qualities below this threshold will be reduced to the minimum (6)."),
            PBOption(category="mutectOption", name="--normal-lod", required=False, typeName=float, helpStr="Log 10 odds threshold for calling normal variant non-germline."),
            PBOption(category="mutectOption", name="--allow-non-unique-kmers-in-ref", action="store_true", helpStr="Allow graphs that have non-unique kmers in the reference."),
            PBOption(category="mutectOption", name="--enable-dynamic-read-disqualification-for-genotyping", action="store_true", helpStr="Will enable less strict read disqualification low base quality reads."),
            PBOption(category="mutectOption", name="--recover-all-dangling-branches", action="store_true", helpStr="Recover all dangling branches."),
            PBOption(category="mutectOption", name="--pileup-detection", action="store_true", helpStr="If enabled, the variant caller will create pileup-based haplotypes in addition to the assembly-based haplotype generation."),
            PBOption(category="mutectOption", name="--mitochondria-mode", action="store_true", helpStr="Mitochondria mode sets emission and initial LODs to 0."),
        ]
        self.perfOptions = [
            PBOption(category="mutectOption", name="--mutect-low-memory", action="store_true", helpStr="Use low memory mode in mutect caller."),
            PBOption(category="mutectOption", name="--run-partition", action="store_true", helpStr="Turn on partition mode; divides genome into multiple partitions and runs 1 process per partition."),
            PBOption(category="mutectOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr="Number of GPUs to use per partition."),
            PBOption(category="mutectOption", name="--num-htvc-threads", default=5, typeName=int, helpStr="Number of CPU threads per GPU to use."),
            ]
        if not is_pipeline:
            self.allOptions.extend([
                PBOption(category="mutectOption", name="--tumor-name", helpStr="Name of the sample for tumor reads.  This MUST match the SM tag in the tumor BAM file.", required=True),
                PBOption(category="mutectOption", name="--normal-name", helpStr="Name of the sample for normal reads.  If specified, this MUST match the SM tag in the normal BAM file."),
                PBOption(category="mutectOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call the variants from the BAM/CRAM file. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
                PBOption(category="mutectOption", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including.")
            ])
