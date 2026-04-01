import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileWriteable
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class genotypegvcfOptionGenerator():
    def __init__(self):
        self.allOptions = [
        ]
        self.perfOptions = [
            PBOption(category="genotypeGVCFOption", name="--num-threads", default=4, typeName=int, helpStr="Number of threads for worker.")
        ]

def genotypegvcf(argList):
    genotypegvcf_parser = argparse.ArgumentParser(description="Convert GVCF to VCF.",
                                                  formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                                  usage='''pbrun genotypegvcf <options>\nHelp: pbrun genotypegvcf -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable), 
                PBOption(category="IOOption", name="--in-gvcf", required=True,
                        helpStr="Input a g.vcf or g.vcf.gz file that will be converted to VCF.  Required.",
                        typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--out-vcf", required=True, helpStr="Path to output VCF file.",
                          typeName=IsFileWriteable)]
    genotypegvcf_parser_iogroup = genotypegvcf_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(genotypegvcf_parser_iogroup, IOOptions)

    genotypegvcfOpts = genotypegvcfOptionGenerator()
    genotypegvcf_parser_toolgroup = genotypegvcf_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(genotypegvcf_parser_toolgroup, genotypegvcfOpts.allOptions)

    genotypegvcf_parser_perfgroup = genotypegvcf_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(genotypegvcf_parser_perfgroup, genotypegvcfOpts.perfOptions)

    genotypegvcf_parser_sysgroup = genotypegvcf_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(genotypegvcf_parser_sysgroup, sysOptionGenerator(False).allOptions)

    args = genotypegvcf_parser.parse_args(argList[2:])
    return args
