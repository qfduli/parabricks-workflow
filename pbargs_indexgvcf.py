import argparse
from pbutils import IsFileReadable
from PBOption import addToParser, PBOption, ARG_GROUP_IO_OPTIONS, IO_OPTIONS, ARG_GROUP_TOOL_OPTIONS, \
    TOOL_OPTIONS, ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class indexgvcfOptionGenerator():
    def __init__(self):
        self.allOptions = []


def indexgvcf(argList):
    indexgvcf_parser = argparse.ArgumentParser(description="Index a GVCF file.",
                                               formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                               usage='''pbrun indexgvcf <options>\nHelp: pbrun indexgvcf -h''')
    IOOptions = [PBOption(category="IOOption", name="--input", required=True,
                          helpStr="Path to the g.vcf/g.vcf.gz file to be indexed.", typeName=IsFileReadable)]
    indexgvcf_parser_iogroup = indexgvcf_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(indexgvcf_parser_iogroup, IOOptions)

    indexgvcf_parser_toolgroup = indexgvcf_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(indexgvcf_parser_toolgroup, indexgvcfOptionGenerator().allOptions)

    indexgvcf_parser_sysgroup = indexgvcf_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(indexgvcf_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = indexgvcf_parser.parse_args(argList[2:])
    return args
