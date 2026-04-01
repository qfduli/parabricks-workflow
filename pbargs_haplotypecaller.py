import argparse
from pbutils import IsFileReadable, IsBamValid, IsFileStreamReadable, IsOutVarValid
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
from htcOptionGenerator import htcOptionGenerator
import PbHelpFormatter


def haplotypecaller(argList):
    htc_parser = argparse.ArgumentParser(description="Run HaplotypeCaller to convert BAM/CRAM to VCF.",
                                         formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                         usage='''pbrun haplotypecaller <options>\nHelp: pbrun haplotypecaller -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True,
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-bam", typeName=IsBamValid, required=True,
                          helpStr="Path to the input BAM/CRAM file for variant calling. The argument may also be a local folder containing several BAM files."),
                 PBOption(category="IOOption", name="--in-recal-file", typeName=IsFileStreamReadable,
                          helpStr="Path to the input BQSR report."),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--htvc-bam-output", typeName=IsOutVarValid, helpStr="File to which assembled haplotypes should be written. If passing with --run-partition, multiple BAM files will be written."),
                 PBOption(category="IOOption", name="--out-variants", typeName=IsOutVarValid,
                          helpStr="Path of the vcf/vcf.gz/g.vcf/gvcf.gz file after variant calling.",
                          required=True),
                 PBOption(category="IOOption", name="--htvc-alleles", typeName=IsFileStreamReadable,
                          helpStr="Path of the vcf.gz force-call file. The set of alleles to force-call regardless of evidence.")]
    htc_parser_iogroup = htc_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(htc_parser_iogroup, IOOptions)

    htcOpts = htcOptionGenerator()
    htc_parser_toolgroup = htc_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(htc_parser_toolgroup, htcOpts.allOptions)

    htc_parser_perfgroup = htc_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(htc_parser_perfgroup, htcOpts.perfOptions)

    htc_parser_sysgroup = htc_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(htc_parser_sysgroup, sysOptionGenerator().allOptions)

    args = htc_parser.parse_args(argList[2:])
    return args
