import argparse
from PBOption import PBOption


class htcOptionGenerator():
  def __init__(self, is_pipeline=False, is_human_par=False, is_rna_gatk=False, is_denovomutation=False):
    htcOptionsHelp = "Pass supported haplotype caller options as one string. The following are currently supported original haplotypecaller options: " \
            "-A <AS_BaseQualityRankSumTest, AS_FisherStrand, AS_InbreedingCoeff, AS_MappingQualityRankSumTest, " \
            "    AS_QualByDepth, AS_RMSMappingQuality, AS_ReadPosRankSumTest, AS_StrandOddsRatio, " \
            "    BaseQualityRankSumTest, ChromosomeCounts, ClippingRankSumTest, Coverage, " \
            "    DepthPerAlleleBySample, DepthPerSampleHC, ExcessHet, FisherStrand, InbreedingCoeff, " \
            "    MappingQualityRankSumTest, QualByDepth, RMSMappingQuality, ReadPosRankSumTest, " \
            "    ReferenceBases, StrandBiasBySample, StrandOddsRatio, TandemRepeat, AssemblyComplexity>," \
            "-AX <same options as -A>," \
            "--output-mode <EMIT_VARIANTS_ONLY, EMIT_ALL_CONFIDENT_SITES, EMIT_ALL_ACTIVE_SITES> ," \
            "-max-reads-per-alignment-start <int>, " \
            "-min-dangling-branch-length <int>, " \
            "-min-pruning <int>, " \
            "-pcr-indel-model <NONE, HOSTILE, AGGRESSIVE, CONSERVATIVE>, " \
            "-standard-min-confidence-threshold-for-calling <int>, " \
            "--activeregion-alt-multiplier <double>" \
        "(e.g. --haplotypecaller-options=\"-min-pruning 4 -standard-min-confidence-threshold-for-calling 30\")."
    self.allOptions = [
                        PBOption(category="htcOption", name="--haplotypecaller-options", helpStr=htcOptionsHelp),
                        PBOption(category="htcOption", name="--static-quantized-quals", default=None, typeName=int, action='append', helpStr="Use static quantized quality scores to a given number of levels. Repeat this option multiple times for multiple bins."),
                        PBOption(category="htcOption", name="--gvcf", action="store_true", helpStr="Generate variant calls in .gvcf format."),
                        PBOption(category="htcOption", name="--disable-read-filter", action='append', helpStr="Disable the read filters for BAM entries. Currently, the supported read filters that can be disabled are MappingQualityAvailableReadFilter, MappingQualityReadFilter, NotSecondaryAlignmentReadFilter, and WellformedReadFilter."),
                        PBOption(category="htcOption", name="--max-alternate-alleles", typeName=int, helpStr="Maximum number of alternate alleles to genotype."),
                        PBOption(category="htcOption", name="--annotation-group", short_name="-G", action='append', helpStr="The groups of annotations to add to the output variant calls. Currently supported annotation groups are StandardAnnotation, StandardHCAnnotation, and AS_StandardAnnotation."),
                        PBOption(category="htcOption", name="--gvcf-gq-bands", short_name="-GQB", typeName=int, action='append', helpStr="Exclusive upper bounds for reference confidence GQ bands. Must be in the range [1, 100] and specified in increasing order."),
                        PBOption(category="htcOption", name="--rna", required=False, action="store_true", helpStr="Run haplotypecaller optimized for RNA data."),
                        PBOption(category="htcOption", name="--dont-use-soft-clipped-bases", required=False, action="store_true", helpStr="Don't use soft clipped bases for variant calling."),
                        PBOption(category="htcOption", name="--minimum-mapping-quality", typeName=int, helpStr="Minimum mapping quality to keep (inclusive)."),
                        PBOption(category="htcOption", name="--mapping-quality-threshold-for-genotyping", typeName=int, helpStr="Control the threshold for discounting reads from the genotyper due to mapping quality after the active region detection and assembly steps but before genotyping."),
                        PBOption(category="htcOption", name="--enable-dynamic-read-disqualification-for-genotyping", action="store_true", helpStr="Will enable less strict read disqualification low base quality reads."),
                        PBOption(category="htcOption", name="--min-base-quality-score", typeName=int, helpStr="Minimum base quality required to consider a base for calling."),
                        PBOption(category="htcOption", name="--adaptive-pruning", action="store_true", helpStr="Use adaptive graph pruning algorithm when pruning De Bruijn graph."),
                        PBOption(category="htcOption", name="--force-call-filtered-alleles", action="store_true", helpStr="Force-call filtered alleles included in the resource specified by --alleles."),
                        PBOption(category="htcOption", name="--filter-reads-too-long", required=False, action="store_true", helpStr="Ignore all input BAM reads with size > 500bp."),
                        # PBOption(category="htcOption", name="--male-min", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                        # PBOption(category="htcOption", name="--male-max", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                        # PBOption(category="htcOption", name="--female-min", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                        # PBOption(category="htcOption", name="--female-max", required=False, typeName=int, helpStr=argparse.SUPPRESS)
                        #PBOption(category="htcOption", name="--read-from-tmp-dir", action="store_true", helpStr="Read from the temporary files generated by fq2bam."),
                      ]
    self.perfOptions = [
                        PBOption(category="htcOption", name="--htvc-low-memory", action="store_true", helpStr="Use low memory mode in htvc."),
                        PBOption(category="htcOption", name="--num-htvc-threads", default=5, typeName=int, helpStr="Number of CPU threads per GPU to use."),
                      ]

    if is_human_par:
      self.allOptions.extend([
                        PBOption(category="htcOption", name="--no-alt-contigs", action="store_true", helpStr=argparse.SUPPRESS),
                        PBOption(category="htcOption", name="--ploidy", default=2, typeName=int, helpStr=argparse.SUPPRESS),
                        PBOption(category="htcOption", name="--sample-sex", required=False, helpStr="Sex of the sample input. This option will override the sex determined from any X/Y read ratio range. Must be either male or female."),
                        PBOption(category="htcOption", name="--range-male", required=False, helpStr="Inclusive male range for the X/Y read ratio. The sex is declared male if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-male 1-10\")."),
                        PBOption(category="htcOption", name="--range-female", required=False, helpStr="Inclusive female range for the X/Y read ratio. The sex is declared female if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-female 150-250\")."),
                        PBOption(category="htcOption", name="--use-GRCh37-regions", required=False, action="store_true", helpStr="Use the pseudoautosomal regions for GRCh37 reference types. This flag should be used for GRCh37 and UCSC hg19 references. By default, GRCh38 regions are used."),
                      ])
      self.perfOptions.extend([
                        PBOption(category="htcOption", name="--run-partition", action="store_true", helpStr="Divide the whole genome into multiple partitions and run multiple processes at the same time, each on one partition."),
                        PBOption(category="htcOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr="Number of GPUs to use per partition."),
          ])
    elif is_pipeline:
      self.allOptions.extend([
                        PBOption(category="htcOption", name="--no-alt-contigs", action="store_true", helpStr="Get rid of output records for alternate contigs."),
                        PBOption(category="htcOption", name="--ploidy", default=2, typeName=int, helpStr="Ploidy assumed for the BAM file. Currently only haploid (ploidy 1) and diploid (ploidy 2) are supported."),
                        PBOption(category="htcOption", name="--sample-sex", required=False, helpStr="Sex of the sample input. This option will override the sex determined from any X/Y read ratio range. Must be either male or female."),
                        PBOption(category="htcOption", name="--range-male", required=False, helpStr="Inclusive male range for the X/Y read ratio. The sex is declared male if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-male 1-10\")."),
                        PBOption(category="htcOption", name="--range-female", required=False, helpStr="Inclusive female range for the X/Y read ratio. The sex is declared female if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-female 150-250\")."),
                        PBOption(category="htcOption", name="--use-GRCh37-regions", required=False, action="store_true", helpStr="Use the pseudoautosomal regions for GRCh37 reference types. This flag should be used for GRCh37 and UCSC hg19 references. By default, GRCh38 regions are used."),
                      ])
      self.perfOptions.extend([
                        PBOption(category="htcOption", name="--run-partition", action="store_true", helpStr="Divide the whole genome into multiple partitions and run multiple processes at the same time, each on one partition."),
                        PBOption(category="htcOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr="Number of GPUs to use per partition."),
                        PBOption(category="htcOption", name="--read-from-tmp-dir", action="store_true", helpStr="Running variant caller reading from bin files generated by Aligner and sort. Run postsort in parallel. This option will increase device memory usage.")
          ])
      if is_rna_gatk:
        self.allOptions.extend([
                        PBOption(category="htcOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call the variants from the BAM/CRAM file. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
                        PBOption(category="htcOption", name="--exclude-intervals", short_name="-XL", action='append', helpStr="Genomic intervals to exclude from processing. Use the same format as --interval option. Excluded intervals are subtracted from the include intervals. This option can be used multiple times (e.g. \"-XL chr1:1000-2000 -XL chr2:5000-6000\")."),
                        PBOption(category="htcOption", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including."),
                      ])
    else:
      self.allOptions.extend([
                        PBOption(category="htcOption", name="--no-alt-contigs", action="store_true", helpStr="Get rid of output records for alternate contigs."),
                        PBOption(category="htcOption", name="--ploidy", default=2, typeName=int, helpStr="Ploidy assumed for the BAM file. Currently only haploid (ploidy 1) and diploid (ploidy 2) are supported."),
                        PBOption(category="htcOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call the variants from the BAM/CRAM file. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
                        PBOption(category="htcOption", name="--exclude-intervals", short_name="-XL", action='append', helpStr="Genomic intervals to exclude from processing. Use the same format as --interval option. Excluded intervals are subtracted from the include intervals. This option can be used multiple times (e.g. \"-XL chr1:1000-2000 -XL chr2:5000-6000\")."),
                        PBOption(category="htcOption", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including."),
                        PBOption(category="htcOption", name="--sample-sex", required=False, helpStr="Sex of the sample input. This option will override the sex determined from any X/Y read ratio range. Must be either male or female."),
                        PBOption(category="htcOption", name="--range-male", required=False, helpStr="Inclusive male range for the X/Y read ratio. The sex is declared male if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-male 1-10\")."),
                        PBOption(category="htcOption", name="--range-female", required=False, helpStr="Inclusive female range for the X/Y read ratio. The sex is declared female if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-female 150-250\")."),
                        PBOption(category="htcOption", name="--use-GRCh37-regions", required=False, action="store_true", helpStr="Use the pseudoautosomal regions for GRCh37 reference types. This flag should be used for GRCh37 and UCSC hg19 references. By default, GRCh38 regions are used."),
                      ])
      self.perfOptions.extend([
                        PBOption(category="htcOption", name="--run-partition", action="store_true", helpStr="Divide the whole genome into multiple partitions and run multiple processes at the same time, each on one partition."),
                        PBOption(category="htcOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr="Number of GPUs to use per partition."),
                        PBOption(category="htcOption", name="--read-from-tmp-dir", action="store_true", helpStr=argparse.SUPPRESS)
          ])
    if is_denovomutation:
      self.allOptions = [
                          PBOption(category="htcOption", name="--haplotypecaller-options", default="-standard-min-confidence-threshold-for-calling 30", helpStr=htcOptionsHelp),
                          PBOption(category="htcOption", name="--static-quantized-quals", typeName=int, nargs="*", action='append', helpStr="Use static quantized quality scores to a given number of levels. Repeat this option multiple times for multiple bins."),
                          PBOption(category="htcOption", name="--disable-read-filter", action='append', helpStr="Disable the read filters for BAM entries. Currently, the supported read filters can be disabled are MappingQualityAvailableReadFilter, MappingQualityReadFilter, NotSecondaryAlignmentReadFilter, and WellformedReadFilter."),
                          PBOption(category="htcOption", name="--max-alternate-alleles", typeName=int, helpStr="Maximum number of alternate alleles to genotype."),
                          PBOption(category="htcOption", name="--annotation-group", short_name="-G", action='append', helpStr="The groups of annotations to add to the output variant calls. Currently supported annotation groups are StandardAnnotation, StandardHCAnnotation, and AS_StandardAnnotation."),
                          PBOption(category="htcOption", name="--gvcf-gq-bands", short_name="-GQB", typeName=int, nargs="*", action='append', helpStr="Exclusive upper bounds for reference confidence GQ bands. Must be in the range [1, 100] and specified in increasing order."),
                          PBOption(category="htcOption", name="--rna", required=False, action="store_true", helpStr="Run haplotypecaller optimized for RNA data."),
                          PBOption(category="htcOption", name="--dont-use-soft-clipped-bases", required=False, action="store_true", helpStr="Don't use soft clipped bases for variant calling."),
                          PBOption(category="htcOption", name="--male-min", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                          PBOption(category="htcOption", name="--male-max", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                          PBOption(category="htcOption", name="--female-min", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                          PBOption(category="htcOption", name="--female-max", required=False, typeName=int, helpStr=argparse.SUPPRESS),
                          PBOption(category="htcOption", name="--ploidy", default=2, typeName=int, helpStr="Ploidy assumed for the BAM file. Currently only haploid (ploidy 1) and diploid (ploidy 2) are supported."),
                          PBOption(category="htcOption", name="--sample-sex", required=False, helpStr="Sex of the sample input. This option will override the sex determined from any X/Y read ratio range. Must be either male or female."),
                          PBOption(category="htcOption", name="--range-male", required=False, helpStr="Inclusive male range for the X/Y read ratio. The sex is declared male if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-male 1-10\")."),
                          PBOption(category="htcOption", name="--range-female", required=False, helpStr="Inclusive female range for the X/Y read ratio. The sex is declared female if the actual ratio falls in the specified range. Syntax is \"<min>-<max>\" (e.g. \"--range-female 150-250\")."),
                          PBOption(category="htcOption", name="--use-GRCh37-regions", required=False, action="store_true", helpStr="Use the pseudoautosomal regions for GRCh37 reference types. This flag should be used for GRCh37 and UCSC hg19 references. By default, GRCh38 regions are used."),
                          PBOption(category="htcOption", name="--htvc-low-memory", action="store_true", helpStr="Use low memory mode in htvc.")
                        ]
      self.perfOptions = ([
                          PBOption(category="htcOption", name="--run-partition", action="store_true", helpStr="Divide the whole genome into multiple partitions and run multiple processes at the same time, each on one partition."),
                          PBOption(category="htcOption", name="--gpu-num-per-partition", required=False, typeName=int, helpStr=argparse.SUPPRESS),
          ])
