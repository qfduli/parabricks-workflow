import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileStreamWritable, IsDirReadable
from sysOptionGenerator import sysOptionGenerator
from deepvariantOptionGenerator import deepvariantOptionGenerator
import PbHelpFormatter


def deepvariant(argList):
    deepvariant_parser = argparse.ArgumentParser(description="Run DeepVariant to convert BAM/CRAM to VCF.",
            formatter_class=PbHelpFormatter.PbHelpFormatter, usage='pbrun deepvariant <options>\nHelp: pbrun deepvariant -h')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-bam", typeName=IsFileStreamReadable, required=True, helpStr="Path to the input BAM/CRAM file for variant calling."))
    IOOptions.append(PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable, helpStr="Path to a BED file (.bed) for selective access. This option can be used multiple times."))
    IOOptions.append(PBOption(category="IOOption", name="--out-variants", typeName=IsFileStreamWritable, helpStr="Path of the vcf/vcf.gz/g.vcf/g.vcf.gz file after variant calling.", required=True))
    IOOptions.append(PBOption(category="IOOption", name="--pb-model-file", typeName=IsFileReadable, helpStr="Path to a non-default parabricks model file for deepvariant."))
    IOOptions.append(PBOption(category="IOOption", name="--pb-small-model-file", typeName=IsFileReadable, helpStr="Path to a non-default parabricks model file for the small model."))
    #IOOptions.append(PBOption(category="IOOption", name="--pb-model-dir", typeName=IsDirReadable, helpStr="Path to a non-default parabricks model dir that contains multiple engine files for one model"))
    IOOptions.append(PBOption(category="IOOption", name="--proposed-variants", typeName=IsFileReadable, helpStr="Path of the vcf.gz file, which has proposed variants for the make examples stage."))
    deepvariant_parser_iogroup = deepvariant_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(deepvariant_parser_iogroup, IOOptions)

    dvOpts = deepvariantOptionGenerator()
    deepvariant_parser_toolgroup = deepvariant_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(deepvariant_parser_toolgroup, dvOpts.allOptions)

    deepvariant_parser_perfgroup = deepvariant_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(deepvariant_parser_perfgroup, dvOpts.perfOptions)

    deepvariant_parser_sysgroup = deepvariant_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(deepvariant_parser_sysgroup, sysOptionGenerator().allOptions)

    args = deepvariant_parser.parse_args(argList[2:])
    return args
