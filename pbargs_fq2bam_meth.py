import argparse
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable, IsDirWriteable, IsMethylReferenceReadable
from PBOption import PBOption, addToParser, IN_FQ_HELP, IN_SE_FQ_HELP, KNOWN_SITES_HELP,\
    ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
    ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS, \
    ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
    ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
from fq2bamOptionGenerator import fq2bamfastOptionGenerator
import PbHelpFormatter


def fq2bam_meth(argList):
    bsmb_parser = argparse.ArgumentParser(
        description="Run GPU-accelerated bwa-meth compatible alignment, co-ordinate sorting, marking duplicates, and Base Quality Score Recalibration to convert bisulfite reads from FASTQ to BAM/CRAM.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun fq2bam_meth [<args>]\nHelp: pbrun fq2bam_meth -h''')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", helpStr="Path to the reference file. We will automatically look for <filename>.bwameth.c2t. Converted fasta reference must exist from prior conversion with baseline bwa-meth.", required=True,
                              typeName=IsMethylReferenceReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-fq", helpStr=IN_FQ_HELP,
                              required=False, nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq", helpStr=IN_SE_FQ_HELP,
                              required=False, nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-fq-list",
                              helpStr="Path to a file that contains the locations of pair-ended FASTQ files.  Each line must contain the location of two FASTQ files followed by a read group, each separated by a space. Each set of files (and associated read group) must be on a separate line. Files must be in fastq/fastq.gz format. Line syntax: <fastq_1> <fastq_2> <read group>.",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq-list",
                              helpStr="Path to a file that contains the locations of single-ended FASTQ files.  Each line must contain the location of the FASTQ files followed by a read group, each separated by a space. Each file (and associated read group) must be on a separate line. Files must be in fastq/fastq.gz format. Line syntax: <fastq> <read group>.",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--knownSites", action='append', typeName=IsFileReadable,
                              helpStr=KNOWN_SITES_HELP))
    IOOptions.append(PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                              helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."))
    IOOptions.append(PBOption(category="IOOption", name="--out-recal-file", typeName=IsFileStreamWritable,
                              helpStr="Path of a report file after Base Quality Score Recalibration."))
    IOOptions.append(PBOption(category="IOOption", name="--out-bam", required=True, typeName=IsFileStreamWritable,
                              helpStr="Path of a BAM/CRAM file."))
    IOOptions.append(PBOption(category="IOOption", name="--out-duplicate-metrics", typeName=IsFileStreamWritable,
                              helpStr="Path of duplicate metrics file after marking duplicates."))
    IOOptions.append(PBOption(category="IOOption", name="--out-qc-metrics-dir", typeName=IsDirWriteable,
                              helpStr="Path of the directory where QC metrics will be generated."))

    opt_generator = fq2bamfastOptionGenerator()

    # methylation-specific parameters
    fq2bam_meth_specific_opts = [
        PBOption(category="fq2bam_methOption", name="--set-as-failed",
                 helpStr="Flag alignments to strand 'f' or 'r' as failing quality-control (QC) with the"
                         " failed QC flag 0x200. BS-Seq libraries are often to a single strand; other strands"
                         " can be flagged as QC failures. Note: f == OT, r == OB. Valid options are 'f' or 'r'.",
                 typeName=str, default=None),
        PBOption(category="fq2bam_methOption", name="--do-not-penalize-chimeras",
                 helpStr="Turn off the default heuristic which marks alignments as failing QC if"
                         " the longest match is less than 44%% of the original sequence length. "
                         "Alignments which fail this heuristic are also un-paired.",
                 action="store_true")
    ]
    opt_generator.allOptions.extend(fq2bam_meth_specific_opts)

    bsmb_parser_iogroup = bsmb_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(bsmb_parser_iogroup, IOOptions)

    bsmb_parser_toolgroup = bsmb_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(bsmb_parser_toolgroup, opt_generator.allOptions)

    bsmb_parser_perfgroup = bsmb_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(bsmb_parser_perfgroup, opt_generator.perfOptions)

    bsmb_parser_sysgroup = bsmb_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(bsmb_parser_sysgroup, sysOptionGenerator().allOptions)

    args = bsmb_parser.parse_args(argList[2:])
    return args
