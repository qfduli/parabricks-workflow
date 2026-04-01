import argparse
from PBOption import PBOption, addToParser, IN_TUMOR_FQ_HELP, KNOWN_SITES_HELP
from PBOption import \
        ARG_GROUP_IO_OPTIONS, IO_OPTIONS, \
        ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS,\
        ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS, \
        ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS
from pbutils import IsFileReadable, IsInFQList, IsFileStreamWritable
#from fq2bamOptionGenerator import fq2bamOptionGenerator
from fq2bamOptionGenerator import fq2bamfastOptionGenerator
from mutectOptionGenerator import mutectOptionGenerator
from sysOptionGenerator import sysOptionGenerator
import PbHelpFormatter


def somatic(argList):
    somatic_parser = argparse.ArgumentParser(description="Run the tumor normal somatic pipeline from FASTQ to VCF.",
                                             formatter_class=PbHelpFormatter.PbHelpFormatter, #argparse.ArgumentDefaultsHelpFormatter,
                                             usage='''pbrun somatic <options>\nHelp: pbrun somatic -h''')
    IOOptions = [PBOption(category="IOOption", name="--ref", required=True, helpStr="Path to the reference file.",
                          typeName=IsFileReadable),
                 PBOption(category="IOOption", name="--in-tumor-fq", nargs='*', action='append',
                          helpStr=IN_TUMOR_FQ_HELP,
                          typeName=IsInFQList),
                 PBOption(category="IOOption", name="--in-se-tumor-fq",
                          helpStr="Path to the single-ended FASTQ file followed by an optional read group with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:foo\"). The file must be in fastq or fastq.gz format. Either all sets of inputs have a read group, or none should have one; if no read group is provided, one will be added automatically by the pipeline. This option can be repeated multiple times. Example 1: --in-se-tumor-fq sampleX_1.fastq.gz --in-se-tumor-fq sampleX_2.fastq.gz . Example 2: --in-se-tumor-fq sampleX_1.fastq.gz \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:tumor\\tPU:unit1\" --in-se-tumor-fq sampleX_2.fastq.gz \"@RG\\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:tumor\\tPU:unit2\" . For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU.",
                          nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--in-normal-fq", nargs='*', action='append',
                          helpStr="Path to the pair-ended FASTQ files followed by an optional read group with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:20\"). The files must be in fastq or fastq.gz format. Either all sets of inputs have a read group, or none should have one; if no read group is provided, one will be automatically added by the pipeline. This option can be repeated multiple times. Example 1: --in-normal-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz --in-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz . Example 2: --in-normal-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz \"@RG\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sm_normal\\tPU:unit1\" --in-normal-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz \"@RG\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:sm_normal\\tPU:unit2\". For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU.",
                          typeName=IsInFQList),
                 PBOption(category="IOOption", name="--in-se-normal-fq",
                          helpStr="Path to the single-ended FASTQ file followed by optional read group with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:foo\"). The file must be in fastq or fastq.gz format. Either all sets of inputs have a read group, or none should have one; if no read group is provided, one will be added automatically by the pipeline. This option can be repeated multiple times. Example 1: --in-se-normal-fq sampleX_1.fastq.gz --in-se-normal-fq sampleX_2.fastq.gz . Example 2: --in-se-normal-fq sampleX_1.fastq.gz \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:normal\\tPU:unit1\" --in-se-normal-fq sampleX_2.fastq.gz \"@RG\\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:normal\\tPU:unit2\" . For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU.",
                          nargs='*', action='append', typeName=IsInFQList),
                 PBOption(category="IOOption", name="--knownSites", action='append', typeName=IsFileReadable,
                          helpStr=KNOWN_SITES_HELP),
                 PBOption(category="IOOption", name="--interval-file", action='append', typeName=IsFileReadable,
                          helpStr="Path to an interval file in one of these formats: Picard-style (.interval_list or .picard), GATK-style (.list or .intervals), or BED file (.bed). This option can be used multiple times."),
                 PBOption(category="IOOption", name="--out-vcf", typeName=IsFileStreamWritable, required=True,
                          helpStr="Path of the VCF file after Variant Calling. (Allowed: .vcf, .vcf.gz)"),
                 PBOption(category="IOOption", name="--out-tumor-bam", typeName=IsFileStreamWritable, required=True,
                          helpStr="Path of the BAM file for tumor reads."),
                 PBOption(category="IOOption", name="--out-normal-bam", typeName=IsFileStreamWritable,
                          helpStr="Path of the BAM file for normal reads."),
                 PBOption(category="IOOption", name="--mutect-bam-output", typeName=IsFileStreamWritable,
                          helpStr="File to which assembled haplotypes should be written in Mutect. If passing with --run-partition, multiple BAM files will be written."),
                 PBOption(category="IOOption", name="--out-tumor-recal-file", typeName=IsFileStreamWritable,
                          helpStr="Path of the report file after Base Quality Score Recalibration for tumor sample."),
                 PBOption(category="IOOption", name="--out-normal-recal-file", typeName=IsFileStreamWritable,
                          helpStr="Path of the report file after Base Quality Score Recalibration for normal sample."),
                 PBOption(category="IOOption", name="--mutect-germline-resource", typeName=IsFileReadable,
                          helpStr="Path of the vcf.gz germline resource file. Population VCF of germline sequencing containing allele fractions."),
                 PBOption(category="IOOption", name="--mutect-alleles", typeName=IsFileReadable,
                          helpStr="Path of the vcf.gz force-call file. The set of alleles to force-call regardless of evidence."),
                 PBOption(category="IOOption", name="--mutect-f1r2-tar-gz", typeName=IsFileStreamWritable,
                          helpStr="Path of the tar.gz of collecting F1R2 counts.")]
    somatic_parser_iogroup = somatic_parser.add_argument_group(ARG_GROUP_IO_OPTIONS, IO_OPTIONS)
    addToParser(somatic_parser_iogroup, IOOptions)

    fq2bamfastOpts = fq2bamfastOptionGenerator(is_somatic_pipeline=True)
    mutectOpts = mutectOptionGenerator(True)
    somatic_parser_toolgroup = somatic_parser.add_argument_group(ARG_GROUP_TOOL_OPTIONS, TOOL_OPTIONS)
    addToParser(somatic_parser_toolgroup, fq2bamfastOpts.allOptions)
    addToParser(somatic_parser_toolgroup, mutectOpts.allOptions)

    rgOptions = [
        PBOption(category="rgOptionGroup", name="--tumor-read-group-sm",
                 helpStr="SM tag for read groups for tumor sample.", default=None),
        PBOption(category="rgOptionGroup", name="--tumor-read-group-lb",
                 helpStr="LB tag for read groups for tumor sample.", default=None),
        PBOption(category="rgOptionGroup", name="--tumor-read-group-pl",
                 helpStr="PL tag for read groups for tumor sample.", default=None),
        PBOption(category="rgOptionGroup", name="--tumor-read-group-id-prefix",
                 helpStr="Prefix for ID and PU tag for read groups for tumor sample. This prefix will be used for all pair of tumor FASTQ files in this run. The ID and PU tag will consist of this prefix and an identifier which will be unique for a pair of FASTQ files.",
                 default=None),
        PBOption(category="rgOptionGroup", name="--normal-read-group-sm",
                 helpStr="SM tag for read groups for normal sample.", default=None),
        PBOption(category="rgOptionGroup", name="--normal-read-group-lb",
                 helpStr="LB tag for read groups for normal sample.", default=None),
        PBOption(category="rgOptionGroup", name="--normal-read-group-pl",
                 helpStr="PL tag for read groups for normal sample.", default=None),
        PBOption(category="rgOptionGroup", name="--normal-read-group-id-prefix",
                 helpStr="Prefix for ID and PU tags for read groups of a normal sample. This prefix will be used for all pairs of normal FASTQ files in this run. The ID and PU tags will consist of this prefix and an identifier that will be unique for a pair of FASTQ files.",
                 default=None)
    ]
    addToParser(somatic_parser_toolgroup, rgOptions)

    somatic_parser_perfgroup = somatic_parser.add_argument_group(ARG_GROUP_PERF_OPTIONS, PERF_OPTIONS)
    addToParser(somatic_parser_perfgroup, fq2bamfastOpts.perfOptions)
    addToParser(somatic_parser_perfgroup, mutectOpts.perfOptions)

    somatic_parser_sysgroup = somatic_parser.add_argument_group(ARG_GROUP_RUN_OPTIONS, RUN_OPTIONS)
    addToParser(somatic_parser_sysgroup, sysOptionGenerator().allOptions)

    args = somatic_parser.parse_args(argList[2:])
    return args
