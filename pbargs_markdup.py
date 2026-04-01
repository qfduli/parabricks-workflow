import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileStreamReadable, IsFileStreamWritable, IsFileReadable, GetDefaultMemoryLimit
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter

class markdupOptionGenerator():
    def __init__(self, is_pipeline=False):
        self.allOptions = [
            PBOption(category="markdupOption", name="--markdups-assume-sortorder-queryname", helpStr="Assume the reads are sorted by queryname for marking duplicates. This will mark secondary, supplementary, and unmapped reads as duplicates as well. This flag will not impact variant calling while increasing processing times.", action="store_true"),
            PBOption(category="markdupOption", name="--optical-duplicate-pixel-distance", helpStr="The maximum offset between two duplicate clusters in order to consider them optical duplicates.", typeName=int, default=None),
            PBOption(category="markdupOption", name="--markdups-single-ended-start-end", action="store_true", helpStr="Mark duplicate on single-ended reads by 5' and 3' end."),
            PBOption(category="markdupOption", name="--ignore-rg-markdups-single-ended", action="store_true", helpStr="Ignore read group info in marking duplicates on single-ended reads. This option must be used with `--markdups-single-ended-start-end`."),
        ]
        self.perfOptions = [
            PBOption(category="markdupOption", name="--num-zip-threads", typeName=int, helpStr="Number of CPUs to use for zipping BAM/CRAM files in a run (default 10)."),
            PBOption(category="markdupOption", name="--num-worker-threads", typeName=int, helpStr="Number of CPUs to use for markdup in a run (default 10)."),
            PBOption(category="markdupOption", name="--mem-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr="Memory limit in GBs during sorting and postsorting. By default, the limit is half of the total system memory."),
            PBOption(category="markdupOption", name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category="markdupOption", name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None)", typeName=int),
            PBOption(category="markdupOption", name="--gpusort", helpStr="Use GPUs to accelerate sorting and marking.", action="store_true"),
        ]


def markdup(argList):
    markdup_parser = argparse.ArgumentParser(
        description="Mark duplicate reads in BAM file. The input file should be sorted by queryname.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun markdup <options>\nHelp: pbrun markdup -h''')
    IOOptions = [PBOption(category="IOOption", name="--in-bam", required=True, typeName=IsFileStreamReadable,
                          helpStr="Path of BAM/CRAM for marking duplicate. Need to be sorted by queryname already. This option is required."),
                 PBOption(category="IOOption", name="--out-bam", required=True,
                          helpStr="Path of BAM/CRAM file after marking duplicate.",
                          typeName=IsFileStreamWritable),
                 PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--out-duplicate-metrics",
                          helpStr="Path of duplicate metrics file after marking duplicates.",
                          typeName=IsFileStreamWritable)]
    markdup_parser_iogroup = markdup_parser.add_argument_group(ARG_GROUP_IO_OPTIONS,
                                                               IO_OPTIONS)
    addToParser(markdup_parser_iogroup, IOOptions)

    md_options = markdupOptionGenerator()

    markdup_parser_toolgroup = markdup_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS,
                                                                 TOOL_OPTIONS)
    addToParser(markdup_parser_toolgroup, md_options.allOptions)

    markdup_parser_perfgroup = markdup_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(markdup_parser_perfgroup, md_options.perfOptions)

    markdup_parser_sysgroup = markdup_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS,
                                                                RUN_OPTIONS)
    addToParser(markdup_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = markdup_parser.parse_args(argList[2:])
    return args
