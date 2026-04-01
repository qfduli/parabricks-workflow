import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class applybqsrOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="applyBQSROption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call applyBQSR from the input reads. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            PBOption(category="applyBQSROption", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including."),
        ]
        self.perfOptions = [
            PBOption(category="applyBQSROption", name="--num-threads", default=8, typeName=int, helpStr="Number of threads for worker.")
            ]


def applybqsr(argList):
    abqsr_parser = argparse.ArgumentParser(description="Update the Base Quality Scores using the BQSR report.",
                                           formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                           usage='''pbrun applybqsr <options>\nHelp: pbrun applybqsr -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-bam", required=True, helpStr="Path to the BAM file.",
                          typeName=IsFileStreamReadable),
                 PBOption(category="IOOption", name="--in-recal-file", required=True,
                          helpStr="Path to the BQSR report file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--out-bam", required=True, typeName=IsFileStreamWritable,
                          helpStr="Output BAM file.")]
    abqsr_parser_iogroup = abqsr_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(abqsr_parser_iogroup, IOOptions)

    abqsrOpts = applybqsrOptionGenerator()
    abqsr_parser_toolgroup = abqsr_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(abqsr_parser_toolgroup, abqsrOpts.allOptions)

    abqsr_parser_perfgroup = abqsr_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(abqsr_parser_perfgroup, abqsrOpts.perfOptions)

    abqsr_parser_sysgroup = abqsr_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(abqsr_parser_sysgroup, sysOptionGenerator().allOptions)

    args = abqsr_parser.parse_args(argList[2:])
    return args
