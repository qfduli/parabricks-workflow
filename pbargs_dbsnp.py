import argparse
from PBOption import PBOption, addToParser, ARG_GROUP_IO_OPTIONS, IO_OPTIONS, ARG_GROUP_TOOL_OPTIONS,\
    TOOL_OPTIONS, ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class dbsnpOptionGenerator():
    def __init__(self):
        self.allOptions = []


def dbsnp(argList):
    dbsnp_parser = argparse.ArgumentParser(description="Annotate variants based on a dbSNP.",
                                           formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                           usage='''pbrun dbsnp <options>\nHelp: pbrun dbsnp -h''')
    IOOptions = [PBOption(category="IOOption", name="--in-vcf", required=True, helpStr="Path to the input VCF file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-dbsnp-file", required=True,
                          helpStr="Path to the input DBSNP file in vcf.gz format, with its tabix index.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--out-vcf", required=True, typeName=IsFileStreamWritable,
                          helpStr="Output annotated VCF file.")]
    dbsnp_parser_iogroup = dbsnp_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(dbsnp_parser_iogroup, IOOptions)

    dbsnp_parser_toolgroup = dbsnp_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(dbsnp_parser_toolgroup, dbsnpOptionGenerator().allOptions)

    dbsnp_parser_sysgroup = dbsnp_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(dbsnp_parser_sysgroup, sysOptionGenerator(sys_options=False).allOptions)

    args = dbsnp_parser.parse_args(argList[2:])
    return args
