import argparse
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable, IsDirWriteable
from PBOption import PBOption, addToParser, IN_FQ_HELP, IN_SE_FQ_HELP, KNOWN_SITES_HELP,\
    ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
    ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS, \
    ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
    ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from sysOptionGenerator import sysOptionGenerator
from giraffeOptionGenerator import giraffeOptionGenerator
import PbHelpFormatter

def giraffe(argList):
    giraffe_parser = argparse.ArgumentParser(
        description="Align reads to a pangenome graph.",
        formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
        usage='''pbrun giraffe [<args>]\nHelp: pbrun giraffe -h''')
    IOOptions = []
    IOOptions.append(PBOption(category="IOOption", name="--in-fq", helpStr="Path to the paired-end FASTQ files. The files must be in fastq or fastq.gz format. Example 1: --in-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz.", nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-fq-list", helpStr="Path to a file that contains the locations of pair-ended FASTQ files.  Each line must contain the location of the FASTQ files followed by a read group, each separated by a space. Each pair of files (and associated read group) must be on a separate line. Files must be in fastq/fastq.gz format. Line syntax: <fastq_1> <fastq_2> <read group>.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq", helpStr="Path to the single-end FASTQ file. The file must be in fastq or fastq.gz format.", nargs='*', action='append', typeName=IsInFQList))
    IOOptions.append(PBOption(category="IOOption", name="--in-se-fq-list", helpStr="Path to a file that contains the locations of single-ended FASTQ files.  Each line must contain the location of the FASTQ files followed by a read group, each separated by a space. Each file (and associated read group) must be on a separate line. Files must be in fastq/fastq.gz format. Line syntax: <fastq> <read group>.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--dist-name", short_name="-d", helpStr="Cluster using this distance index.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--minimizer-name", short_name="-m", helpStr="Use this minimizer index.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--gbz-name", short_name="-Z", helpStr="Map to this GBZ graph.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--zipcodes-name", short_name="-z", helpStr="Use this zipcodes file for clustering.", required=True, typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--xg-name", short_name="-x", helpStr="XG graph used for BAM output.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--graph-name", short_name="-g", helpStr="GBWTGraph used for mapping.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--gbwt-name", short_name="-H", helpStr="GBWT index for mapping.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--out-bam", helpStr="Path of a BAM file for output.", required=True, typeName=IsFileStreamWritable))
    IOOptions.append(PBOption(category="IOOption", name="--ref-paths", helpStr="Path to file containing ordered list of paths in the graph, one per line or HTSlib .dict, for HTSLib @SQ headers.", typeName=IsFileReadable))
    IOOptions.append(PBOption(category="IOOption", name="--out-duplicate-metrics", typeName=IsFileStreamWritable, helpStr="Path of duplicate metrics file after marking duplicates."))
    IOOptions.append(PBOption(category="IOOption", name="--out-qc-metrics-dir", typeName=IsDirWriteable, helpStr=argparse.SUPPRESS))  # helpStr="Path of the directory where QC metrics will be generated."))
    # no bqsr yet
    # IOOptions.append(PBOption(category="IOOption", name="--knownSites", required=False, action='append', typeName=IsFileReadable, helpStr=KNOWN_SITES_HELP))
    # IOOptions.append(PBOption(category="IOOption", name="--interval-file", required=False, action='append', typeName=IsFileReadable, helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."))
    
    giraffe_parser_iogroup = giraffe_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(giraffe_parser_iogroup, IOOptions)

    giraffeOpts = giraffeOptionGenerator()
    giraffe_parser_toolgroup = giraffe_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(giraffe_parser_toolgroup, giraffeOpts.allOptions)

    giraffe_parser_perfgroup = giraffe_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(giraffe_parser_perfgroup, giraffeOpts.perfOptions)

    giraffe_parser_sysgroup = giraffe_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(giraffe_parser_sysgroup, sysOptionGenerator().allOptions)

    args = giraffe_parser.parse_args(argList[2:])
    return args
