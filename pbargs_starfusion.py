import argparse
from PBOption import PBOption,  addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsDirReadable, IsDirWriteable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class starfusionOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="starfusionOption", name="--out-prefix", helpStr="Prefix filename for output data.")
        ]
        self.perfOptions = [
            PBOption(category="starfusionOption", name="--num-threads", default=4, typeName=int, helpStr="Number of threads for worker."),
            ]


def starfusion(argList):
    starfusion_parser = argparse.ArgumentParser(
        description="Identify candidate fusion transcripts supported by Illumina reads.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun starfusion <options>\nHelp: pbrun starfusion -h''')
    IOOptions = [PBOption(category="IOOption", name="--chimeric-junction", required=True,
                          helpStr="Path to the Chimeric.out.junction file produced by STAR.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--genome-lib-dir", required=True,
                          helpStr="Path to a genome resource library directory. For more information, visit https://github.com/STAR-Fusion/STAR-Fusion/wiki/installing-star-fusion#data-resources-required.",
                          typeName=IsDirReadable),
                 PBOption(category="IOOption", name="--output-dir", required=True,
                          helpStr="Path to the directory that will contain all of the generated files.",
                          typeName=IsDirWriteable)]
    starfusion_parser_iogroup = starfusion_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(starfusion_parser_iogroup, IOOptions)

    sfOpts = starfusionOptionGenerator()
    starfusion_parser_toolgroup = starfusion_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(starfusion_parser_toolgroup, sfOpts.allOptions)

    starfusion_parser_perfgroup = starfusion_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(starfusion_parser_perfgroup, sfOpts.perfOptions)

    starfusion_parser_sysgroup = starfusion_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(starfusion_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = starfusion_parser.parse_args(argList[2:])
    return args
