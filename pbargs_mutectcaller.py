import argparse
from PBOption import PBOption, addToParser
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsFileWriteable, IsFileStreamWritable, IsFileStreamReadable
from sysOptionGenerator import sysOptionGenerator
from mutectOptionGenerator import mutectOptionGenerator
import PbHelpFormatter


def mutectcaller(argList):
    mutect_parser = argparse.ArgumentParser(description="Run GPU mutect2 to convert BAM/CRAM to VCF.",
                                            formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                            usage='''pbrun mutectcaller <options>\nHelp: pbrun mutectcaller -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--out-vcf", typeName=IsFileStreamWritable,
                          helpStr="Path of the VCF file after Variant Calling. (Allowed: .vcf, .vcf.gz)", required=True),
                 PBOption(category="IOOption", name="--in-tumor-bam", typeName=IsFileStreamReadable,
                          helpStr="Path of the BAM/CRAM file for tumor reads.", required=True),
                 PBOption(category="IOOption", name="--in-normal-bam", typeName=IsFileStreamReadable,
                          helpStr="Path of the BAM/CRAM file for normal reads."),
                 PBOption(category="IOOption", name="--in-tumor-recal-file", typeName=IsFileStreamReadable,
                          helpStr="Path of the report file after Base Quality Score Recalibration for tumor sample."),
                 PBOption(category="IOOption", name="--in-normal-recal-file", typeName=IsFileStreamReadable,
                          helpStr="Path of the report file after Base Quality Score Recalibration for normal sample."),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--mutect-bam-output", typeName=IsFileStreamWritable, helpStr="File to which assembled haplotypes should be written. If passing with --run-partition, multiple BAM files will be written."),
                 PBOption(category="IOOption", name="--pon", typeName=IsFileStreamReadable,
                          helpStr="Path of the vcf.gz PON file. Make sure you run prepon first and there is a '.pon' file already."),
                 PBOption(category="IOOption", name="--mutect-germline-resource", typeName=IsFileStreamReadable,
                          helpStr="Path of the vcf.gz germline resource file. Population VCF of germline sequencing containing allele fractions."),
                 PBOption(category="IOOption", name="--mutect-f1r2-tar-gz", typeName=IsFileStreamWritable,
                          helpStr="Path of the tar.gz of collecting F1R2 counts."),
                 PBOption(category="IOOption", name="--mutect-alleles", typeName=IsFileStreamReadable,
                          helpStr="Path of the vcf.gz force-call file. The set of alleles to force-call regardless of evidence.")]

    mutect_parser_iogroup = mutect_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(mutect_parser_iogroup, IOOptions)

    mutectOpts = mutectOptionGenerator()
    mutect_parser_toolgroup = mutect_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(mutect_parser_toolgroup, mutectOpts.allOptions)

    mutect_parser_perfgroup = mutect_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(mutect_parser_perfgroup, mutectOpts.perfOptions)

    mutect_parser_sysgroup = mutect_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(mutect_parser_sysgroup, sysOptionGenerator().allOptions)

    args = mutect_parser.parse_args(argList[2:])
    return args
