import argparse
from PBOption import PBOption, addToParser, IN_FQ_HELP, KNOWN_SITES_HELP, IN_SE_FQ_HELP
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable
#from fq2bamOptionGenerator import fq2bamOptionGenerator
from fq2bamOptionGenerator import fq2bamfastOptionGenerator
from deepvariantOptionGenerator import deepvariantOptionGenerator
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


def deepvariant_germline(argList):
    deepvariant_germline_parser = argparse.ArgumentParser(
        description="Run the germline pipeline from FASTQ to VCF using a deep neural network analysis.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun deepvariant_germline <options>\nHelp: pbrun deepvariant_germline -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True,
                          typeName=IsFileReadable), PBOption(category="IOOption", name="--in-fq", helpStr=IN_FQ_HELP,
                                                             nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--in-se-fq", helpStr=IN_SE_FQ_HELP,
                          required=False, nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--knownSites", action='append', typeName=IsFileReadable,
                          helpStr=KNOWN_SITES_HELP),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--pb-model-file", typeName=IsFileReadable,
                          helpStr="Path to a non-default parabricks model file for deepvariant."),
                 PBOption(category="IOOption", name="--pb-small-model-file", typeName=IsFileReadable,
                          helpStr="Path to a non-default parabricks model file for the small model."),
                 PBOption(category="IOOption", name="--out-recal-file", typeName=IsFileStreamWritable,
                          helpStr="Path of the report file after Base Quality Score Recalibration."),
                 PBOption(category="IOOption", name="--out-bam", typeName=IsFileStreamWritable,
                          helpStr="Path of BAM file after marking duplicates.", required=True),
                 PBOption(category="IOOption", name="--out-variants", typeName=IsFileStreamWritable,
                          helpStr="Path of the vcf/vcf.gz/gvcf/gvcf.gz file after variant calling.", required=True),
                 PBOption(category="IOOption", name="--out-duplicate-metrics", typeName=IsFileStreamWritable,
                          helpStr="Path of a duplicate metrics file after marking duplicates."),
                 PBOption(category="IOOption", name="--proposed-variants", typeName=IsFileReadable,
                          helpStr="Path of the VCF file, which has proposed variants for the make examples stage.")]
    deepvariant_germline_parser_iogroup = deepvariant_germline_parser.add_argument_group(ARG_GROUP_IO_OPTIONS,
                                                                                         IO_OPTIONS)
    addToParser(deepvariant_germline_parser_iogroup, IOOptions)

    deepvariant_germline_parser_toolgroup = deepvariant_germline_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS,
                                                                                           TOOL_OPTIONS)
    fq2bamfastOpts = fq2bamfastOptionGenerator(is_deepvariant_pipeline=True)
    dvOpts = deepvariantOptionGenerator(is_pipeline=True)
    addToParser(deepvariant_germline_parser_toolgroup, fq2bamfastOpts.allOptions)
    addToParser(deepvariant_germline_parser_toolgroup, dvOpts.allOptions)

    deepvariant_germline_parser_perfgroup = deepvariant_germline_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(deepvariant_germline_parser_perfgroup, fq2bamfastOpts.perfOptions)
    addToParser(deepvariant_germline_parser_perfgroup, dvOpts.perfOptions)

    deepvariant_germline_parser_sysgroup = deepvariant_germline_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS,
                                                                                          RUN_OPTIONS)
    addToParser(deepvariant_germline_parser_sysgroup, sysOptionGenerator().allOptions)

    args = deepvariant_germline_parser.parse_args(argList[2:])
    return args
