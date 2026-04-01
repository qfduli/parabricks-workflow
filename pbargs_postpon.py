import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class postponOptionGenerator():
    def __init__(self):
        self.allOptions = []


def postpon(argList):
    postpon_parser = argparse.ArgumentParser(description="Annotate variants based on a PON file.",
                                             formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                             usage='''pbrun postpon <options>\nHelp: pbrun postpon -h''')
    IOOptions = []
    IOOptions.append(
        PBOption(category="IOOption", name="--in-vcf", required=True, helpStr="Path to the input VCF file.",
                 typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-pon-file", required=True,
                              helpStr="Path to the input PON file in vcf.gz format with its tabix index.",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--out-vcf", required=True, typeName=IsFileStreamWritable,
                              helpStr="Output annotated VCF file."))
    postpon_parser_iogroup = postpon_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(postpon_parser_iogroup, IOOptions)

    postpon_parser_toolgroup = postpon_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(postpon_parser_toolgroup, postponOptionGenerator().allOptions)

    postpon_parser_sysgroup = postpon_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(postpon_parser_sysgroup, sysOptionGenerator().allOptions)

    args = postpon_parser.parse_args(argList[2:])
    return args
