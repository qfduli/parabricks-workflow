from pbutils import OptError

# Some help strings occur multiple times.  Define them once.
IN_FQ_HELP = "Path to the pair-ended FASTQ files followed by optional read groups with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:foo\"). " \
        "The files must be in fastq or fastq.gz format. " \
        "All sets of inputs should have a read group; otherwise, none should have a read group, and it will be automatically added by the pipeline. " \
        "This option can be repeated multiple times. " \
        "Example 1: --in-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz --in-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz. " \
        "Example 2: --in-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:unit1\" " \
        "--in-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz \"@RG\\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:unit2\". " \
        "For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU."
IN_SE_FQ_HELP = "Path to the single-ended FASTQ file followed by optional read group with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:foo\"). " \
        "The file must be in fastq or fastq.gz format. " \
        "Either all sets of inputs have a read group, or none should have one, and it will be automatically added by the pipeline. " \
        "This option can be repeated multiple times. " \
        "Example 1: --in-se-fq sampleX_1.fastq.gz --in-se-fq sampleX_2.fastq.gz . " \
        "Example 2: --in-se-fq sampleX_1.fastq.gz \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:unit1\" --in-se-fq sampleX_2.fastq.gz \"@RG\\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:sample\\tPU:unit2\" . " \
        "For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU."
IN_TUMOR_FQ_HELP = "Path to the pair-ended FASTQ files followed by optional read group with quotes (Example: \"@RG\\tID:foo\\tLB:lib1\\tPL:bar\\tSM:20\"). " \
        "The files can be in fastq or fastq.gz format. " \
        "Either all sets of inputs have a read group, or none should have one, and it will be automatically added by the pipeline. " \
        "This option can be repeated multiple times. " \
        "Example 1: --in-tumor-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz --in-tumor-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz. " \
        "Example 2: --in-tumor-fq sampleX_1_1.fastq.gz sampleX_1_2.fastq.gz \"@RG\tID:foo\\tLB:lib1\\tPL:bar\\tSM:sm_tumor\\tPU:unit1\" " \
        "--in-tumor-fq sampleX_2_1.fastq.gz sampleX_2_2.fastq.gz \"@RG\tID:foo2\\tLB:lib1\\tPL:bar\\tSM:sm_tumor\\tPU:unit2\". " \
        "For the same sample, Read Groups should have the same sample name (SM) and a different ID and PU."
KNOWN_SITES_HELP = "Path to a known indels file. The file must be in vcf.gz format. This option can be used multiple times."

# 1st param to ArgumentParser.add_argument_group() call. Also used as the main
# section header in the command line help output.
ARG_GROUP_IO_OPTIONS = "Input Output file options"
ARG_GROUP_TOOL_OPTIONS = "Tool Options"
ARG_GROUP_RUN_OPTIONS = "Run Options"
ARG_GROUP_PERF_OPTIONS = "Performance Options"

# 2nd param to ArgumentParser.add_argument_group() call.  Also used as a
# sub-title in the command line help output.
IO_OPTIONS = "Options for Input and Output files for this tool."
TOOL_OPTIONS = "Options specific to the tool."
RUN_OPTIONS = "Options related to resource/verbosity/etc."
PERF_OPTIONS = "Performance Tuning Options."


class PBOption(object):
    def __init__(self, category, name, helpStr, default=None, required=False, action=None, nargs=None, typeName=None, short_name=None, const=None):
        self.category = category
        if '_' in name:
            OptError("Option names should not have _ . We use - for options.")
        if (category == "IOOption") and (default is not None):
            OptError("This Option is wrongly configured. IOOption should not have a default value.")
        self.name = name
        self.helpStr = helpStr
        self.default = default
        self.required = required
        if action is not None:
            self.action = action
        if nargs is not None:
            self.nargs = nargs
        if typeName is not None:
            self.typeName = typeName
        if short_name is not None:
            self.short_name = short_name
        if const is not None:
            self.const = const

    def __str__(self):
        return f"PBOption {self.name}({self.default})"

    def __repr__(self):
        return f"PBOption {self.name}({self.default})"


def addToParser(new_parser, allOptions):
    for option in allOptions:
        argDict = {}
        #attrs = vars(curOption)
        #print ",".join("%s: %s" % item for item in attrs.items())
        if hasattr(option, "default"):
            argDict["default"] = option.default
        if hasattr(option, "action"):
            argDict["action"] = option.action
        if hasattr(option, "nargs"):
            argDict["nargs"] = option.nargs
        if hasattr(option, "required"):
            argDict["required"] = option.required
        if hasattr(option, "typeName"):
            argDict["type"] = option.typeName
        argDict["help"] = option.helpStr
        if hasattr(option, "short_name"):
            new_parser.add_argument(option.short_name, option.name, **argDict)
        else:
            new_parser.add_argument(option.name, **argDict)


def getIOList(IOOptions):
    '''
    @param IOOptions: should be a collection of PBOption.
    @return: A list of PBOption names with leading & trailing hyphens removed, internal hyphens changed to underscores.
    '''
    IOList = []
    for option in IOOptions:
        trimmedOption = option.name.strip('-')
        newOption = trimmedOption.replace('-', '_')
        IOList.append(newOption)
    return IOList
