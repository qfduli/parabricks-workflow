import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsFileWriteable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class bammetricsOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="CGWSMOption", name="--minimum-base-quality", default=20, typeName=int, helpStr="Minimum base quality for a base to contribute coverage."),
            PBOption(category="CGWSMOption", name="--minimum-mapping-quality", default=20, typeName=int, helpStr="Minimum mapping quality for a read to contribute coverage."),
            PBOption(category="CGWSMOption", name="--count-unpaired", action="store_true", helpStr="If specified, count unpaired reads and paired reads with one end unmapped."),
            PBOption(category="CGWSMOption", name="--coverage-cap", default=250, typeName=int, helpStr="Treat positions with coverage exceeding this value as if they had coverage at this value (but calculate the difference for PCT_EXC_CAPPED)."),
            PBOption(category="CGWSMOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to collect metrics from the BAM/CRAM file. All intervals will have a padding of 0 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\").")
        ]
        self.perfOptions = [
            PBOption(category="CGWSMOption", name="--num-threads", default=12, typeName=int, helpStr="Number of threads to run."),
        ]


def bammetrics(argList):
    bammetrics_parser = argparse.ArgumentParser(description="Run bammetrics on a BAM file to generate a metrics file.",
                                                formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                                usage='''pbrun bammetrics <options>\nHelp: pbrun bammetrics -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--bam", required=True, helpStr="Path to the BAM file.",
                          typeName=IsFileStreamReadable),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--out-metrics-file", required=True, typeName=IsFileWriteable,
                          helpStr="Output Metrics File.")]
    bammetrics_parser_iogroup = bammetrics_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(bammetrics_parser_iogroup, IOOptions)

    bammetricsOpts = bammetricsOptionGenerator()
    bammetrics_parser_toolgroup = bammetrics_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(bammetrics_parser_toolgroup, bammetricsOpts.allOptions)

    bammetrics_parser_perfgroup = bammetrics_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(bammetrics_parser_perfgroup, bammetricsOpts.perfOptions)

    bammetrics_parser_sysgroup = bammetrics_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(bammetrics_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = bammetrics_parser.parse_args(argList[2:])
    return args
