import argparse
from PBOption import PBOption, addToParser, KNOWN_SITES_HELP, ARG_GROUP_IO_OPTIONS, IO_OPTIONS,\
    ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS, ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class bqsrOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="bqsrOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call BQSR from the input reads. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            PBOption(category="bqsrOption", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including.")
        ]


def bqsr(argList):
    bqsr_parser = argparse.ArgumentParser(description="Run BQSR on a BAM file to generate a BQSR report.",
                                          formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                          usage='''pbrun bqsr <options>\nHelp: pbrun bqsr -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-bam", required=True, helpStr="Path to the BAM file.",
                          typeName=IsFileStreamReadable),
                 PBOption(category="IOOption", name="--knownSites", action='append', required=True,
                          typeName=IsFileReadable,
                          helpStr=KNOWN_SITES_HELP),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--out-recal-file", required=True, typeName=IsFileStreamWritable,
                          helpStr="Output Report File.")]
    bqsr_parser_iogroup = bqsr_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(bqsr_parser_iogroup, IOOptions)

    bqsr_parser_toolgroup = bqsr_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(bqsr_parser_toolgroup, bqsrOptionGenerator().allOptions)

    bqsr_parser_sysgroup = bqsr_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(bqsr_parser_sysgroup, sysOptionGenerator().allOptions)

    args = bqsr_parser.parse_args(argList[2:])
    return args
