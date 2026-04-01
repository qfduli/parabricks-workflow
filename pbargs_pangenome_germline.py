import argparse
from PBOption import PBOption, addToParser, IN_FQ_HELP, IN_SE_FQ_HELP
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable
from sysOptionGenerator import sysOptionGenerator
from giraffeOptionGenerator import giraffeOptionGenerator
from pangenomeAwareDeepvariantOptionGenerator import pangenomeAwareDeepvariantOptionGenerator
import PbHelpFormatter


def pangenome_germline(argList):
    pangenome_germline_parser = argparse.ArgumentParser(
        description="Run the germline pipeline from FASTQ to VCF using pangenome alignment (Giraffe) and pangenome-aware DeepVariant. The reference FASTA (--ref) must be the same reference used for the graph (GBZ) and for the ref-paths file.",
        formatter_class=PbHelpFormatter.PbHelpFormatter,
        usage='''pbrun pangenome_germline <options>\nHelp: pbrun pangenome_germline -h''')
    IOOptions = [
        PBOption(category="IOOption", name="--ref", helpStr="Path to the reference FASTA (for DeepVariant). Must match the reference used for the graph and ref-paths.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--in-fq", helpStr=IN_FQ_HELP, nargs='*', action='append', typeName=IsInFQList),
        PBOption(category="IOOption", name="--in-se-fq", helpStr=IN_SE_FQ_HELP, required=False, nargs='*', action='append', typeName=IsInFQList),
        PBOption(category="IOOption", name="--in-fq-list", helpStr="Path to a file that contains the locations of pair-ended FASTQ files. Each line: <fastq_1> <fastq_2> <read group>.", typeName=IsFileReadable),
        PBOption(category="IOOption", name="--in-se-fq-list", helpStr="Path to a file that contains the locations of single-ended FASTQ files. Each line: <fastq> <read group>.", typeName=IsFileReadable),
        PBOption(category="IOOption", name="--gbz-name", short_name="-Z", helpStr="Map to this GBZ graph.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--dist-name", short_name="-d", helpStr="Cluster using this distance index.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--minimizer-name", short_name="-m", helpStr="Use this minimizer index.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--zipcodes-name", short_name="-z", helpStr="Use this zipcodes file for clustering.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--ref-paths", helpStr="Path to file containing ordered list of paths in the graph (one per line or HTSlib .dict). Must match contigs in --ref.", required=True, typeName=IsFileReadable),
        PBOption(category="IOOption", name="--out-bam", helpStr="Path of BAM file for output.", required=True, typeName=IsFileStreamWritable),
        PBOption(category="IOOption", name="--out-variants", helpStr="Path of the vcf/vcf.gz/gvcf/gvcf.gz file after variant calling.", required=True, typeName=IsFileStreamWritable),
        PBOption(category="IOOption", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call variants. This option can be used multiple times."),
        PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                 helpStr="Path to an interval file (BED format). This option can be used multiple times."),
        PBOption(category="IOOption", name="--pb-model-file", typeName=IsFileReadable,
                 helpStr="Path to a non-default parabricks model file for pangenome-aware deepvariant."),
        PBOption(category="IOOption", name="--run-ref-verification", action="store_true", helpStr="Run the pre-flight reference verification step that checks the FASTA (.fai + sequences) against the GBZ graph."),
    ]
    pangenome_germline_parser_iogroup = pangenome_germline_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(pangenome_germline_parser_iogroup, IOOptions)

    giraffeOpts = giraffeOptionGenerator()
    dvOpts = pangenomeAwareDeepvariantOptionGenerator(is_pipeline=True)
    pangenome_germline_parser_toolgroup = pangenome_germline_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(pangenome_germline_parser_toolgroup, giraffeOpts.allOptions)
    addToParser(pangenome_germline_parser_toolgroup, dvOpts.allOptions)

    pangenome_germline_parser_perfgroup = pangenome_germline_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(pangenome_germline_parser_perfgroup, giraffeOpts.perfOptions)
    addToParser(pangenome_germline_parser_perfgroup, dvOpts.perfOptions)

    pangenome_germline_parser_sysgroup = pangenome_germline_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(pangenome_germline_parser_sysgroup, sysOptionGenerator().allOptions)

    args = pangenome_germline_parser.parse_args(argList[2:])
    return args
