import argparse
from pbutils import IsFileReadable
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class preponOptionGenerator():
    def __init__(self):
        self.allOptions = []


def prepon(argList):
    prepon_parser = argparse.ArgumentParser(
        description="Build the index for a PON file; this is a prerequisite for mutect PON.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun prepon <options>\nHelp: pbrun prepon -h''')
    IOOptions = [PBOption(category="IOOption", name="--in-pon-file", required=True,
                          helpStr="Path to the input PON file in vcf.gz format with its tabix index.",
                          typeName=IsFileReadable)]
    prepon_parser_iogroup = prepon_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(prepon_parser_iogroup, IOOptions)

    prepon_parser_toolgroup = prepon_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(prepon_parser_toolgroup, preponOptionGenerator().allOptions)

    prepon_parser_sysgroup = prepon_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(prepon_parser_sysgroup, sysOptionGenerator().allOptions)

    args = prepon_parser.parse_args(argList[2:])
    return args
