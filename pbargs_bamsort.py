import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileStreamReadable, IsFileStreamWritable, IsFileReadable, GetDefaultMemoryLimit
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter

class bamsortOptionGenerator():
    def __init__(self, is_pipeline=False):
        self.allOptions = [
        ]
        self.perfOptions = [
            PBOption(category="bamsortOption", name="--num-zip-threads", typeName=int, helpStr="Number of CPUs to use for zipping BAM files in a run (default 16 for coordinate sorts and 10 otherwise)."),
            PBOption(category="bamsortOption", name="--num-sort-threads", typeName=int, helpStr="Number of CPUs to use for sorting in a run (default 10 for coordinate sorts and 16 otherwise)."),
            PBOption(category="bamsortOption", name="--max-records-in-ram", default=65000000, typeName=int, helpStr="Maximum number of records in RAM when using a queryname or template coordinate sort mode; lowering this number will decrease maximum memory usage."),
            PBOption(category="bamsortOption", name="--mem-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr="Memory limit in GBs during sorting and postsorting. By default, the limit is half of the total system memory."),
            PBOption(category="bamsortOption", name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category="bamsortOption", name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None)", typeName=int),
            PBOption(category="bamsortOption", name="--gpusort", helpStr="Use GPUs to accelerate sorting and marking.", action="store_true"),
        ]
        if not is_pipeline:
            self.allOptions.extend([
                PBOption(category="bamsortOption", name="--sort-order", default="coordinate", typeName=str, helpStr="Type of sort to be done. Possible values are {coordinate,queryname,templatecoordinate}."),
                PBOption(category="bamsortOption", name="--sort-compatibility", default="picard", typeName=str, helpStr="Sort comparator compatibility to be used for compatibility with other tools. Possible values are {picard,fgbio}. TemplateCoordinate will only use fgbio."),
            ])


def bamsort(argList):
    bamsort_parser = argparse.ArgumentParser(
        description="Sort BAM files. There are five modes: Coordinate sort (Picard-compatible), Coordinate sort (fgbio-compatible), queryname sort (Picard-compatible), queryname sort (fgbio-compatible), and template coordinate sort (fgbio-compatible).",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun bamsort <options>\nHelp: pbrun bamsort -h''')
    IOOptions = [PBOption(category="IOOption", name="--in-bam", required=True, typeName=IsFileStreamReadable,
                          helpStr="Path of BAM/CRAM for sorting. This option is required."),
                 PBOption(category="IOOption", name="--out-bam", required=True,
                          helpStr="Path of BAM/CRAM file after sorting.",
                          typeName=IsFileStreamWritable),
                 PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable)]
    bamsort_parser_iogroup = bamsort_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(bamsort_parser_iogroup, IOOptions)

    bamsortOpts = bamsortOptionGenerator()
    bamsort_parser_toolgroup = bamsort_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(bamsort_parser_toolgroup, bamsortOpts.allOptions)

    bamsort_parser_perfgroup = bamsort_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(bamsort_parser_perfgroup, bamsortOpts.perfOptions)

    bamsort_parser_sysgroup = bamsort_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(bamsort_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = bamsort_parser.parse_args(argList[2:])
    return args
