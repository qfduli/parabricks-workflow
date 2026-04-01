import argparse
from PBOption import PBOption, addToParser, IN_FQ_HELP, IN_SE_FQ_HELP, KNOWN_SITES_HELP
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
#from fq2bamOptionGenerator import fq2bamOptionGenerator
from fq2bamOptionGenerator import fq2bamfastOptionGenerator
from htcOptionGenerator import htcOptionGenerator
import PbHelpFormatter


def germline(argList):
    germline_parser = argparse.ArgumentParser(description="Run Germline pipeline to convert FASTQ to VCF.",
                                              formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                              usage='''pbrun germline <options>\nHelp: pbrun germline -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True,
                          typeName=IsFileReadable), PBOption(category="IOOption", name="--in-fq", helpStr=IN_FQ_HELP,
                                                             nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--in-se-fq", helpStr=IN_SE_FQ_HELP,
                          required=False, nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--knownSites", action='append', typeName=IsFileReadable,
                          helpStr=KNOWN_SITES_HELP),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--out-recal-file", typeName=IsFileStreamWritable,
                          helpStr="Path of the report file after Base Quality Score Recalibration."),
                 PBOption(category="IOOption", name="--out-bam", typeName=IsFileStreamWritable,
                          helpStr="Path of BAM file after marking duplicates.", required=True),
                 PBOption(category="IOOption", name="--htvc-bam-output", typeName=IsFileStreamWritable,
                          helpStr="File to which assembled haplotypes should be written in HaplotypeCaller. If passing with --run-partition, multiple BAM files will be written."),
                 PBOption(category="IOOption", name="--out-variants", typeName=IsFileStreamWritable,
                          helpStr="Path of the vcf/vcf.gz/gvcf/gvcf.gz file after variant calling.", required=True),
                 PBOption(category="IOOption", name="--out-duplicate-metrics", typeName=IsFileStreamWritable,
                          helpStr="Path of duplicate metrics file after marking duplicates."),
                 PBOption(category="IOOption", name="--htvc-alleles", typeName=IsFileReadable,
                          helpStr="Path of the vcf.gz force-call file. The set of alleles to force-call regardless of evidence.")]

    # IOOptions.append(PBOption(category="IOOption", name="--in-mba-file", typeName=IsFileReadable, helpStr="Options for MergeBAMAlignment. Currently supported options are ATTRIBUTES_TO_RETAIN, ATTRIBUTES_TO_REMOVE, ATTRIBUTES_TO_REMOVE, MAX_INSERTIONS_OR_DELETIONS, PRIMARY_ALIGNMENT_STRATEGY, UNMAPPED_READ_STRATEGY, ALIGNER_PROPER_PAIR_FLAGS, UNMAP_CONTAMINANT_READS, ADD_PG_TAG_TO_READS. Refer to Picard MergeBAMAlignment documentation for details on these options. These options maybe repeated."))
    germline_parser_iogroup = germline_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(germline_parser_iogroup, IOOptions)

    fq2bamfastOpts = fq2bamfastOptionGenerator()
    htcOpts = htcOptionGenerator(is_pipeline=True)
    germline_parser_toolgroup = germline_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(germline_parser_toolgroup, fq2bamfastOpts.allOptions)
    addToParser(germline_parser_toolgroup, htcOpts.allOptions)

    germline_parser_perfgroup = germline_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(germline_parser_perfgroup, fq2bamfastOpts.perfOptions)
    addToParser(germline_parser_perfgroup, htcOpts.perfOptions)

    germline_parser_sysgroup = germline_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(germline_parser_sysgroup, sysOptionGenerator().allOptions)

    args = germline_parser.parse_args(argList[2:])
    return args
