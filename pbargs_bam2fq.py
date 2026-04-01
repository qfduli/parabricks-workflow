import argparse
from pbutils import IsFileReadable, IsBamValid, IsFileWriteable
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


class bam2fqOptionGenerator():
    def __init__(self):
        self.allOptions = [
            PBOption(category="bam2fqOption", name="--out-suffixF", default="_1.fastq.gz", helpStr="Output suffix used for paired reads that are first in pair. The suffix must end with \".gz\"."),
            PBOption(category="bam2fqOption", name="--out-suffixF2", default="_2.fastq.gz", helpStr="Output suffix used for paired reads that are second in pair. The suffix must end with \".gz\"."),
            PBOption(category="bam2fqOption", name="--out-suffixO", helpStr="Output suffix used for orphan/unmatched reads that are first in pair. The suffix must end with \".gz\". If no suffix is provided, these reads will be ignored."),
            PBOption(category="bam2fqOption", name="--out-suffixO2", helpStr="Output suffix used for orphan/unmatched reads that are second in pair. The suffix must end with \".gz\". If no suffix is provided, these reads will be ignored."),
            PBOption(category="bam2fqOption", name="--out-suffixS", helpStr="Output suffix used for single-end/unpaired reads. The suffix must end with \".gz\". If no suffix is provided, these reads will be ignored."),
            PBOption(category="bam2fqOption", name="--rg-tag", required=False, helpStr="Split reads into different FASTQ files based on the read group tag. Must be either PU or ID."),
            PBOption(category="bam2fqOption", name="--remove-qc-failure", action="store_true", helpStr="Remove reads from the output that have abstract QC failure."),
        ]
        self.perfOptions = [
            PBOption(category="bam2fqOption", name="--num-threads", default=8, typeName=int, helpStr="Number of threads to run."),
            ]

def bam2fq(argList):
    bam2fq_parser = argparse.ArgumentParser(description="Run bam2fq to convert BAM/CRAM to FASTQ.",
                                     formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                     usage='''pbrun bam2fq [<args>]\nHelp: pbrun bam2fq -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref",
                          helpStr="Path to the reference file. This argument is only required for CRAM input.",
                          required=False, typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-bam", typeName=IsBamValid, required=True,
                          helpStr="Path to the input BAM/CRAM file to convert to fastq.gz."),
                 PBOption(category="IOOption", name="--out-prefix", required=True,
                          helpStr="Prefix filename for output FASTQ files.", typeName=IsFileWriteable)]

    bam2fq_iogroup = bam2fq_parser.add_argument_group(ARG_GROUP_IO_OPTIONS,
                                               IO_OPTIONS)
    addToParser(bam2fq_iogroup, IOOptions)

    bam2fqOpts = bam2fqOptionGenerator()
    bam2fq_toolgroup = bam2fq_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(bam2fq_toolgroup, bam2fqOpts.allOptions)

    bam2fq_perfgroup = bam2fq_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(bam2fq_perfgroup, bam2fqOpts.perfOptions)

    bam2fq_sysgroup = bam2fq_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(bam2fq_sysgroup, sysOptionGenerator(False).allOptions)

    args = bam2fq_parser.parse_args(argList[2:])
    return args
