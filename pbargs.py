#!/usr/bin/env python3

import argparse
from importlib import import_module
import os
import sys
import pbversion
import toolversion
from pbutils import OptMesg, pbExit, OptError


# The order here determines the order in which 'pbrun -h' lists tools.
standaloneTools = sorted([
        "applybqsr", "bam2fq", "bammetrics", "bamsort", "bqsr", "collectmultiplemetrics",
        "dbsnp", "deepvariant", "deepsomatic", "pangenome_aware_deepvariant", "fq2bam", "genotypegvcf", "haplotypecaller", "indexgvcf",
        "markdup", "minimap2", "mutectcaller", "postpon", "prepon", "rna_fq2bam", "starfusion",
        "fq2bam_meth", "giraffe"
        ])
cpuTools = [
        "bam2fq", "bamsort", "collectmultiplemetrics", "dbsnp", "genotypegvcf", "indexgvcf", "markdup", "postpon", "prepon", "starfusion"
        ]

class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

    def _fill_text(self, text, width, indent):
        if text.startswith('R|'):
            return text[2:]
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


class PBRun:
    """
    Has one method for each tool which, when called, returns the parsed arguments for that tool.
    """
    def __init__(self, argList):
        current_file_folder = os.path.dirname(os.path.abspath(__file__))
        parser_help_message = """R|
command can be a TOOL or FULL PIPELINE. Example:
pbrun fq2bam --ref genome.fa --in-fq sample_1.fq.gz sample_2.fq.gz --out-bam sample.bam
pbrun germline --ref genome.fa --in-fq sample_1.fq.gz sample_2.fq.gz --out-bam sample.bam --out-variants sample.vcf
\ncommand options for standalone TOOL
"""
        tool_to_description = {
            "applybqsr"                  : "applybqsr                   - Apply BQSR report to a BAM file and generate a new BAM file",
            "bam2fq"                     : "bam2fq                      - Convert a BAM file to FASTQ",
            "bammetrics"                 : "bammetrics                  - Collect WGS Metrics on a BAM file",
            "bamsort"                    : "bamsort                     - Sort a BAM file",
            "bqsr"                       : "bqsr                        - Collect BQSR report on a BAM file",
            "collectmultiplemetrics"     : "collectmultiplemetrics      - Collect multiple classes of metrics on a BAM file",
            "dbsnp"                      : "dbsnp                       - Annotate variants based on a dbsnp",
            "deepvariant"                : "deepvariant                 - Run GPU-DeepVariant for calling germline variants",
            "deepsomatic"                : "deepsomatic                 - Run GPU-DeepSomatic for calling somatic variants",
            "pangenome_aware_deepvariant": "pangenome_aware_deepvariant - Run GPU-Pangenome-aware-deepvariant that uses a pangenome reference for calling germline variants",
            "fq2bam"                     : "fq2bam                      - Run bwa mem, co-ordinate sorting, marking duplicates, and Base Quality Score Recalibration",
            "fq2bam_meth"                : "fq2bam_meth                 - Run GPU-accelerated bwa-meth compatible alignment, co-ordinate sorting, marking duplicates, and Base Quality Score Recalibration",
            "giraffe"                    : "giraffe                     - Run GPU-accelerated VG-giraffe compatible pangenome alignment and co-ordinate sorting",
            "genotypegvcf"               : "genotypegvcf                - Convert a GVCF to VCF",
            "haplotypecaller"            : "haplotypecaller             - Run GPU-HaplotypeCaller for calling germline variants",
            "indexgvcf"                  : "indexgvcf                   - Index a GVCF file",
            "markdup"                    : "markdup                     - Identifies duplicate reads",
            "minimap2"                   : "minimap2                    - Align long read sequences against a large reference database to convert FASTQ to BAM/CRAM",
            "mutectcaller"               : "mutectcaller                - Run GPU-Mutect2 for tumor-normal analysis",
            "postpon"                    : "postpon                     - Generate the final VCF output of doing mutect pon",
            "prepon"                     : "prepon                      - Build an index for PON file, which is the prerequisite to performing mutect pon",
            "rna_fq2bam"                 : "rna_fq2bam                  - Run RNA-seq data through the fq2bam pipeline",
            "starfusion"                 : "starfusion                  - Identify candidate fusion transcripts supported by Illumina reads",
        }
        for tool in standaloneTools:
            if os.path.exists(os.path.join(current_file_folder, f"pbargs_{tool}.py")):
                parser_help_message += "\n" + tool_to_description[tool]
        can_run_germline_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_germline.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_fq2bam.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_haplotypecaller.py"))
        can_run_deepvariant_germline_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_deepvariant_germline.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_fq2bam.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_deepvariant.py"))
        can_run_pacbio_germline_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_pacbio_germline.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_minimap2.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_deepvariant.py"))
        can_run_ont_germline_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_ont_germline.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_minimap2.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_deepvariant.py"))
        can_run_pangenome_germline_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_pangenome_germline.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_giraffe.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_pangenome_aware_deepvariant.py"))
        can_run_somatic_pipeline = \
            os.path.exists(os.path.join(current_file_folder, "pbargs_somatic.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_fq2bam.py")) and \
            os.path.exists(os.path.join(current_file_folder, "pbargs_mutectcaller.py"))
        if any([can_run_germline_pipeline, can_run_deepvariant_germline_pipeline, can_run_pacbio_germline_pipeline, can_run_ont_germline_pipeline, can_run_pangenome_germline_pipeline, can_run_somatic_pipeline]):
            parser_help_message += """
\ncommand options for commonly used FULL PIPELINES
"""
            if can_run_deepvariant_germline_pipeline:
                parser_help_message += "\ndeepvariant_germline    - Run the germline pipeline from FASTQ to VCF using a deep neural network analysis"
            if can_run_pacbio_germline_pipeline:
                parser_help_message += "\npacbio_germline         - Run the germline pipeline from FASTQ/BAM to VCF by aligning long read sequences with minimap2 and using a deep neural network analysis"
            if can_run_ont_germline_pipeline:
                parser_help_message += "\nont_germline            - Run the germline pipeline from FASTQ/BAM to VCF by aligning long read ONT sequences with minimap2 and using a deep neural network analysis"
            if can_run_pangenome_germline_pipeline:
                parser_help_message += "\npangenome_germline      - Run the germline pipeline from FASTQ to VCF using pangenome alignment (Giraffe) and pangenome-aware DeepVariant"
            if can_run_germline_pipeline:
                parser_help_message += "\ngermline                - Run the germline pipeline from FASTQ to VCF"
            if can_run_somatic_pipeline:
                parser_help_message += "\nsomatic                 - Run the somatic pipeline from FASTQ to VCF"

        parser_help_message += """
\nInformation about the software
version                 - Current version of Parabricks

Please visit https://docs.nvidia.com/clara/#parabricks for detailed documentation
"""
        parser = argparse.ArgumentParser(description=parser_help_message,
                                         formatter_class=SmartFormatter,
                                         usage='''pbrun <command> [<args>]\nHelp: pbrun -h''')
        parser.add_argument("command", help="The pipeline or tool to run.")
        args = parser.parse_args(argList[1:2])
        if args.command not in standaloneTools + ["germline", "deepvariant_germline", "pacbio_germline", "ont_germline", "pangenome_germline", "somatic"]:
            if args.command == "version":
                PBRun.version()
            OptError(f"The command argument {args.command} is not a valid Parabricks tools/pipeline")
        else:
            if not os.path.exists(os.path.join(current_file_folder, "pbargs_{}.py".format(args.command))):
                OptError(f"{args.command} standalone tool is not installed in this container")
        # self.runArgs should be a list of PBTool objects.
        # The attribute name is determined by the command being executed.
        tool_module = import_module(f"pbargs_{args.command}")
    
        self.runArgs = getattr(tool_module, args.command)(argList)
        self.command = args.command

    @staticmethod
    def version():
        print("pbrun: " + pbversion.versionNumber)
        pbExit(0)


def dict_from_module(module):
    context = {}
    for setting in dir(module):
      context[setting] = getattr(module, setting)
    return context


def printToolVersion(argList):
  tool = argList[1]

  if tool == "--version":
    argList = [argList[0], "version"]
    return PBRun(argList)

  #get the compatibility lines from toolversion.py
  toolDict = dict_from_module(toolversion)
  compatibilityExists = True
  try:
    compatibilityLines = toolDict[tool]
  except:
    if tool == "germline" or tool == "human_par":
      try:
        compatibilityLines = toolDict["fq2bam"] + toolDict["haplotypecaller"]
      except:
        OptMesg("Missing toolversion.py info for fq2bam or haplotypecaller.")
        exit(1)
    elif tool == "somatic":
      try:
        compatibilityLines = toolDict["fq2bam"] + toolDict["mutectcaller"]
      except:
        OptMesg("Missing toolversion.py info for fq2bam or mutectcaller.")
        exit(1)
    else:
      compatibilityExists = False

  #give each compatibility line the proper amount of tabs
  if compatibilityExists:
    compatibilityString = ""
    for line in compatibilityLines:
      pair = line.split(": ")
      key = pair[0] + ":"
      value = pair[1]
      numTabs = int(4 - ((len(key) + 1) / 8))
      compatibilityString += key + ("\t" * numTabs) + value + "\n"

  print("------------------------------------------------------------------------------------------")
  print("Version Information")
  print("------------------------------------------------------------------------------------------")
  print("Tool:\t\t\t" + tool)
  print("pbrun:\t\t\t" + pbversion.versionNumber)

  if compatibilityExists:
    print("------------------------------------------------------------------------------------------")
    print("Compatible With:")
    print(compatibilityString[:-1])

  print("------------------------------------------------------------------------------------------")
  pbExit(0)


def getArgs():
    """
    @return: A PBRun object with the options & arguments all parsed.
    """
    if "--version" in sys.argv:
        printToolVersion(sys.argv)
    return PBRun(sys.argv)


def pb_args_main():
    print(getArgs())


if __name__ == '__main__':
    pb_args_main()
