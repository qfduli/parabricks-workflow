import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileStreamWritable, IsDirReadable
from sysOptionGenerator import sysOptionGenerator
from deepsomaticOptionGenerator import deepsomaticOptionGenerator
import PbHelpFormatter


def deepsomatic(argList):
    deepsomatic_parser = argparse.ArgumentParser(description="Run DeepSomatic to convert BAM/CRAM to VCF.",
            formatter_class=PbHelpFormatter.PbHelpFormatter, usage='pbrun deepsomatic <options>\nHelp: pbrun deepsomatic -h')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-tumor-bam", typeName=IsFileStreamReadable, required=True, helpStr="Path to the input tumor BAM/CRAM file for somatic variant calling."))
    IOOptions.append(PBOption(category="IOOption", name="--in-normal-bam", typeName=IsFileStreamReadable, required=True, helpStr="Path to the input normal BAM/CRAM file for somatic variant calling."))
    IOOptions.append(PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable, helpStr="Path to a BED file (.bed) for selective access. This option can be used multiple times."))
    IOOptions.append(PBOption(category="IOOption", name="--out-variants", typeName=IsFileStreamWritable, helpStr="Path of the vcf/vcf.gz/g.vcf/g.vcf.gz file after variant calling.", required=True))
    IOOptions.append(PBOption(category="IOOption", name="--pb-model-file", typeName=IsFileReadable, helpStr="Path to a non-default parabricks model file for deepsomatic."))
    #IOOptions.append(PBOption(category="IOOption", name="--pb-model-dir", typeName=IsDirReadable, helpStr="Path to a non-default parabricks model dir that contains multiple engine files for one model"))
    #IOOptions.append(PBOption(category="IOOption", name="--proposed-variants", typeName=IsFileReadable, helpStr="Path of the vcf.gz file, which has proposed variants for the make examples stage."))
    deepsomatic_parser_iogroup = deepsomatic_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(deepsomatic_parser_iogroup, IOOptions)

    dvOpts = deepsomaticOptionGenerator()
    deepsomatic_parser_toolgroup = deepsomatic_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(deepsomatic_parser_toolgroup, dvOpts.allOptions)

    deepsomatic_parser_perfgroup = deepsomatic_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(deepsomatic_parser_perfgroup, dvOpts.perfOptions)

    deepsomatic_parser_sysgroup = deepsomatic_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(deepsomatic_parser_sysgroup, sysOptionGenerator().allOptions)

    args = deepsomatic_parser.parse_args(argList[2:])
    return args
