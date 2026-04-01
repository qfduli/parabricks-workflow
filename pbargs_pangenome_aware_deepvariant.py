import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileStreamWritable, IsDirReadable
from sysOptionGenerator import sysOptionGenerator
from pangenomeAwareDeepvariantOptionGenerator import pangenomeAwareDeepvariantOptionGenerator
import PbHelpFormatter


def pangenome_aware_deepvariant(argList):
    pangenome_aware_deepvariant_parser = argparse.ArgumentParser(description="Run pangenome_aware_deepvariant to convert BAM/CRAM to VCF.",
            formatter_class=PbHelpFormatter.PbHelpFormatter, usage='pbrun pangenome_aware_deepvariant <options>\nHelp: pbrun pangenome_aware_deepvariant -h')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--pangenome", helpStr="Path to the pangenome gbz file.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-bam", typeName=IsFileStreamReadable, required=True, helpStr="Path to the input BAM/CRAM file for variant calling."))
    IOOptions.append(PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable, helpStr="Path to a BED file (.bed) for selective access. This option can be used multiple times."))
    IOOptions.append(PBOption(category="IOOption", name="--out-variants", typeName=IsFileStreamWritable, helpStr="Path of the vcf/vcf.gz/g.vcf/g.vcf.gz file after variant calling.", required=True))
    IOOptions.append(PBOption(category="IOOption", name="--pb-model-file", typeName=IsFileReadable, helpStr="Path to a non-default parabricks model file for pangenome_aware_deepvariant."))
    #IOOptions.append(PBOption(category="IOOption", name="--pb-model-dir", typeName=IsDirReadable, helpStr="Path to a non-default parabricks model dir that contains multiple engine files for one model"))
    #IOOptions.append(PBOption(category="IOOption", name="--proposed-variants", typeName=IsFileReadable, helpStr="Path of the vcf.gz file, which has proposed variants for the make examples stage."))
    pangenome_aware_deepvariant_iogroup = pangenome_aware_deepvariant_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(pangenome_aware_deepvariant_iogroup, IOOptions)

    dvOpts = pangenomeAwareDeepvariantOptionGenerator()
    pangenome_aware_deepvariant_toolgroup = pangenome_aware_deepvariant_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(pangenome_aware_deepvariant_toolgroup, dvOpts.allOptions)

    pangenome_aware_deepvariant_perfgroup = pangenome_aware_deepvariant_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(pangenome_aware_deepvariant_perfgroup, dvOpts.perfOptions)

    pangenome_aware_deepvariant_sysgroup = pangenome_aware_deepvariant_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(pangenome_aware_deepvariant_sysgroup, sysOptionGenerator().allOptions)

    args = pangenome_aware_deepvariant_parser.parse_args(argList[2:])
    return args
