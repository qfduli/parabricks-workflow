import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileStreamReadable, IsDirWriteable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class collectmultiplemetricsOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="collectmultiplemetricsOption", name="--gen-all-metrics", action="store_true", helpStr="Generate QC for every analysis."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-alignment", action="store_true", helpStr="Generate QC for alignment summary metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-quality-score", action="store_true", helpStr="Generate QC for quality score distribution metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-insert-size", action="store_true", helpStr="Generate QC for insert size metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-mean-quality-by-cycle", action="store_true", helpStr="Generate QC for mean quality by cycle metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-base-distribution-by-cycle", action="store_true", helpStr="Generate QC for base distribution by cycle metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-gc-bias", action="store_true", helpStr="Prefix name used to generate detail and summary files for gc bias metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-seq-artifact", action="store_true", helpStr="Generate QC for sequencing artifact metric."),
            PBOption(category="collectmultiplemetricsOption", name="--gen-quality-yield", action="store_true", helpStr="Generate QC for quality yield metric."),
        ]
        self.perfOptions = [
            PBOption(category="collectmultiplemetricsOption", name="--bam-decompressor-threads", typeName=int, default=3, helpStr="Number of threads for BAM decompression."),
            ]


def collectmultiplemetrics(argList):
    collectmultiplemetrics_parser = argparse.ArgumentParser(
        description="Run collectmultiplemetrics on a BAM file to generate files for multiple classes of metrics.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun collectmultiplemetrics <options>\nHelp: pbrun collectmultiplemetrics -h''')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--bam", required=True, helpStr="Path to the BAM file.",
                              typeName=IsFileStreamReadable))
    IOOptions.append(PBOption(category="IOOption", name="--out-qc-metrics-dir", required=True, typeName=IsDirWriteable,
                              helpStr="Output Directory to store results of each analysis."))
    collectmultiplemetrics_parser_iogroup = collectmultiplemetrics_parser.add_argument_group(ARG_GROUP_IO_OPTIONS,
                                                                                             IO_OPTIONS)
    addToParser(collectmultiplemetrics_parser_iogroup, IOOptions)

    cmmOpts = collectmultiplemetricsOptionGenerator()
    collectmultiplemetrics_parser_toolgroup = collectmultiplemetrics_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS,
                                                                                               TOOL_OPTIONS)
    addToParser(collectmultiplemetrics_parser_toolgroup, cmmOpts.allOptions)

    collectmultiplemetrics_parser_perfgroup = collectmultiplemetrics_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS,
                                                                                               PERF_OPTIONS)
    addToParser(collectmultiplemetrics_parser_perfgroup, cmmOpts.perfOptions)

    collectmultiplemetrics_parser_sysgroup = collectmultiplemetrics_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS,
                                                                                              RUN_OPTIONS)
    addToParser(collectmultiplemetrics_parser_sysgroup, sysOptionGenerator().allOptions)

    args = collectmultiplemetrics_parser.parse_args(argList[2:])
    return args
