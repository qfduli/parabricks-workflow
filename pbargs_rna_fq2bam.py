import argparse
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable, IsDirWriteable, IsDirReadable
from PBOption import PBOption, addToParser, IN_FQ_HELP, IN_SE_FQ_HELP
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
from starOptionGenerator import starOptionGenerator
import PbHelpFormatter


def rna_fq2bam(argList):
    rna_fq2bam_parser = argparse.ArgumentParser(
        description="Run RNA-seq data through the fq2bam pipeline. It will run STAR aligner, co-ordinate sorting and mark duplicates.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun rna_fq2bam <options>\nHelp: pbrun rna_fq2bam -h''')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-fq", helpStr=IN_FQ_HELP,
                              required=False, nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq", helpStr=IN_SE_FQ_HELP,
                              required=False, nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-fq-list",
                              helpStr="Path to a file that contains the locations of pair-ended FASTQ files. " +
    "Each line must contain the location of two FASTQ files followed by an optional read group, " +
    "each separated by a space. Each set of files (and associated read group) must be on a separate line. " +
    "Files must be in fastq/fastq.gz format. Line syntax: <fastq_1> <fastq_2> <read group>",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq-list",
                              helpStr="Path to a file that contains the locations of single-ended FASTQ files. " +
    "Each line must contain the location of the FASTQ files followed by an optional read group, " +
    "each separated by a space. Each file (and associated read group) must be on a separate line. " +
    "Files must be in fastq/fastq.gz format. Line syntax: <fastq> <read group>",
                              typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--genome-lib-dir", required=True,
                              helpStr="Path to a genome resource library directory. The indexing required to run STAR should be completed by the user beforehand.",
                              typeName=IsDirReadable))
    IOOptions.append(PBOption(category="IOOption", name="--output-dir", required=True,
                              helpStr="Path to the directory that will contain all of the generated files.",
                              typeName=IsDirWriteable))
    IOOptions.append(PBOption(category="IOOption", name="--out-bam", required=True, typeName=IsFileStreamWritable,
                              helpStr="Path of the output BAM file."))
    IOOptions.append(PBOption(category="IOOption", name="--out-duplicate-metrics", typeName=IsFileStreamWritable, helpStr="Path of duplicate metrics file after marking duplicates."))
    IOOptions.append(PBOption(category="IOOption", name="--out-qc-metrics-dir", required=False, typeName=IsDirWriteable, helpStr="Path of the directory where QC metrics will be generated."))
    rna_fq2bam_parser_iogroup = rna_fq2bam_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(rna_fq2bam_parser_iogroup, IOOptions)

    starOpts = starOptionGenerator()
    rna_fq2bam_parser_toolgroup = rna_fq2bam_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(rna_fq2bam_parser_toolgroup, starOpts.allOptions)

    rna_fq2bam_parser_perfgroup = rna_fq2bam_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(rna_fq2bam_parser_perfgroup, starOpts.perfOptions)

    rna_fq2bam_parser_sysgroup = rna_fq2bam_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(rna_fq2bam_parser_sysgroup, sysOptionGenerator(True).allOptions)

    args = rna_fq2bam_parser.parse_args(argList[2:])
    return args
