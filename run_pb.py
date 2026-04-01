#!/usr/bin/env python3
'''
This is where the translation
between the pbrun-style command line args and binary command line args happens.
Each binary has unique, specific and sometimes very different command line args.
The translation happens in the runXYZ() functions, where XYZ is the name of the
tool.
'''

import os
import os.path
import sys
import subprocess
import signal
import shutil
import random
import string
import tempfile
import pbargs
import pbversion
import pbargs_check
import common_err_mesg
from pbutils import GetFullDirPath, pbExit, rreplace, GetNumCPUs, OptMesg, OptError, getDefaultBwaCPUThreadPool, check_se_bam, gen_rg_from_bam_input, GetNumGPUs, handle_return_vals, handle_signal_vals
from datetime import datetime
import platform

file_directory = os.path.dirname(os.path.realpath(__file__))


def exitFunction():
    print(common_err_mesg.common_err_mesg)
    print("Exiting...")
    pbExit(1)


def signal_handler(signal, _):
    handle_signal_vals(signal)
    exitFunction()


def cleanDir(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
            exitFunction()


def WriteCmd(runArgs, command):
  with open("cmd.txt", "w") as cmdFile:
    cmdFile.write("pbrun "+ command + "\n")
    cmdFile.write(pbversion.versionNumber + "\n")
    bamCmdList = sys.argv[1:]
    tmpDirIndex = [idx for idx, s in enumerate(bamCmdList) if '--tmp-dir' in s][0]
    tmpDirString=""
    if "=" not in bamCmdList[tmpDirIndex]:
        tmpDirIndex = tmpDirIndex + 1
    else:
        tmpDirString = "--tmp-dir "
    bamCmdList[tmpDirIndex] = tmpDirString + runArgs.tmp_dir[0:-9]
    cmdFile.write("pbrun " + " ".join(bamCmdList) + "\n")

def WriteVcfCmd(runArgs, command):
  with open("vcf_cmd.txt", "w") as cmdFile:
    cmdFile.write(command + "\n")

    bamCmdList = sys.argv[1:]
    tmpDirIndex = [idx for idx, s in enumerate(bamCmdList) if '--tmp-dir' in s][0]
    tmpDirString=""
    if "=" not in bamCmdList[tmpDirIndex]:
        tmpDirIndex = tmpDirIndex + 1
    else:
        tmpDirString = "--tmp-dir "
    bamCmdList[tmpDirIndex] = tmpDirString + runArgs.tmp_dir[0:-9]
    cmdFile.write("pbrun " + " ".join(bamCmdList) + "\n")
    
    cmdFile.write(pbversion.versionNumber + "\n")
    cmdFile.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "\n")

def SetUpEnv(cmdLine, installDir, lib_paths, petaGenePath, printCmd):
    if printCmd:
        print(' '.join(cmdLine))
        sys.stdout.flush()

    myEnv = os.environ.copy()
    myEnv["TCMALLOC_LARGE_ALLOC_REPORT_THRESHOLD"] = "99999999999"
    if "LD_LIBRARY_PATH" in myEnv:
        myEnv["LD_LIBRARY_PATH"] = ":".join(lib_paths + [installDir + "/lib:" + myEnv["LD_LIBRARY_PATH"]])
    else:
        myEnv["LD_LIBRARY_PATH"] = ":".join(lib_paths + [installDir + "/lib"])
    if petaGenePath != None:
        myEnv["LD_PRELOAD"] = petaGenePath + "/bin/petalink.so"

    return myEnv


def RunBinaryNoWait(cmdLine, \
              installDir, \
              lib_paths=[], \
              petaGenePath=None, \
              printCmd=False):
  
  myEnv = SetUpEnv(cmdLine, installDir, lib_paths, petaGenePath, printCmd)
  return subprocess.Popen(cmdLine, env=myEnv, shell=False)

def RunBinary(cmdLine, \
              installDir, \
              lib_paths=[], \
              petaGenePath=None, \
              printCmd=False):

    myEnv = SetUpEnv(cmdLine, installDir, lib_paths, petaGenePath, printCmd)
      
    try:
        retVal = subprocess.call(cmdLine, env=myEnv, shell=False)
        if retVal != 0:
            handle_return_vals(retVal)
            exitFunction()
    except subprocess.CalledProcessError as e:
        exitFunction()


def createqcimages(inBam, inputDir, installDir, runAll=True, out_quality_score=None, out_insert_size=None, out_mean_quality_by_cycle=None, out_base_distribution_by_cycle=None, out_gc_bias=None):
    # A call to tempfile.TemporaryDirectory() sets permissions to 0700 and deletes
    # the temp dir when the mplconfigdir context is completed.
    with tempfile.TemporaryDirectory(prefix="matplotlib_") as mplconfigdir:
        os.environ["MPLCONFIGDIR"] = mplconfigdir
        bashCmds = []

        if runAll or out_quality_score:
            bashCmds.extend(["\npython3", "-W", "ignore",
                             os.path.join(installDir, "python_plotting/qualityScoreDistribution.py"),
                             inputDir + "/qualityscore.txt",
                             inputDir + "/qualityscore.pdf",
                             inBam])
        if runAll or out_insert_size:
            bashCmds.extend(["\npython3", "-W", "ignore",
                             os.path.join(installDir, "python_plotting/insertSize.py"),
                             inputDir + "/insert_size.txt",
                             inputDir + "/insert_size.pdf",
                             inBam])
        if runAll or out_mean_quality_by_cycle:
            bashCmds.extend(["\npython3", "-W", "ignore",
                             os.path.join(installDir, "python_plotting/meanQualityByCycle.py"),
                             inputDir + "/mean_quality_by_cycle.txt",
                             inputDir + "/mean_quality_by_cycle.pdf",
                             inBam])
        if runAll or out_base_distribution_by_cycle:
            bashCmds.extend(["\npython3", "-W", "ignore",
                             os.path.join(installDir, "python_plotting/baseDistByCycle.py"),
                             inputDir + "/base_distribution_by_cycle.txt",
                             inputDir + "/base_distribution_by_cycle.pdf",
                             inBam])
        if runAll or out_gc_bias:
            bashCmds.extend(["\npython3", "-W", "ignore",
                             os.path.join(installDir, "python_plotting/gcBias.py"),
                             inputDir + "/gcbias_detail.txt",
                             inputDir + "/gcbias_summary.txt",
                             inputDir + "/gcbias.pdf",
                             "100"])
        scriptName = "/tmp/" + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8)) + "_run.sh"
        with open(scriptName, "w") as bashscript:
          bashscript.write("#!/bin/bash\n\n")
          bashscript.write(' '.join(bashCmds) + "\n")
        subprocess.call(["chmod", "+x", scriptName])
        RunBinary([scriptName], installDir, printCmd=True)


def AddLogfile(commandArgs, runArgs, append=None):
  '''
  If runArgs has a non-null logfile, add '--logfile filename.ext' to commandArgs.
  If we have a log file AND we should append to it, then note that as well.
  Appending should only happen in a pipeline.

  @param commandArgs: list(str) with the individual tokens that make up the command line to be run.
  @param runArgs:  PBRun object (?) with the name of the log file and whether or not to append.
  @param append: If true, overrides a False in runArgs.append.

  if runArgs.logfile is empty then I don't have a log file.

  If runArgs.logfile is not empty then I should be logging, and all I have to
  figure out is whether I open for append or overwrite.  If pbrun/pb_compose
  have added the "--append" command line argument then I append.  They communicate
  that by setting runArgs.append to True.  If it's false but I *do* have a logfile
  then I need to open the logfile for overwrite the 1st time, but open it for
  append the rest of the time.  The append parameter to this function tells me
  whether I should 'force' appending in this manner.  This is used for the 2nd and
  subsequent calls in a given tool.
  '''
  if runArgs.logfile is not None:
    # If you define the --logfile argument with nargs=1 then the parameter to
    # logfile shows up as a single-element list.
    commandArgs.extend(["--logfile", runArgs.logfile])
    if runArgs.append or append:
      commandArgs.extend(["--append"])


def SetupOptions(runArgs):
  #Setup pbOpts.txt for BWA-mem
  numBQSRGPUs = 1
  numZipper = "8"
  numFthreads = "4"
  isReaderMT = "1"
  if runArgs.num_gpus > 1:
    numBQSRGPUs = 2
  if runArgs.num_gpus <= 2:
    numZipper = "4"
    numFthreads = "2"
    isReaderMT = "0"
  retVal = ["g " + str(runArgs.num_gpus),
            "P " + str(runArgs.num_cpu_threads_per_stage),
            "s 1",
            "b 0",
            "m 1",
            "z " + numZipper]

  if runArgs.align_only == True:
    retVal.append("o 1")
  else:
    retVal.append("o 2")
  if runArgs.verbose:
    retVal.append("v 1")
  else:
    retVal.append("v 0")

  if runArgs.no_markdups == True:
    retVal.append("M 0")
  elif runArgs.markdups_picard_version_2182 == True:
    retVal.append("M 1")
  else:
    retVal.append("M 2")

  if runArgs.fix_mate == True:
    retVal.append("X 1")
  else:
    retVal.append("X 0")

  if runArgs.no_warnings == True:
    retVal.append("F")

  if runArgs.monitor_usage == True:
    retVal.append("S")

  bam_name = runArgs.out_bam
  if runArgs.markdups_assume_sortorder_queryname == True:
    bam_name = bam_name[0:-4] + "_mark_assume_coordinate_sort.bam"
    retVal.append("Q dupQueryName.txt")

  retVal.append("name " + bam_name)


  if runArgs.x3 == True:
    print(" ".join(retVal))
    sys.stdout.flush()

  #Write to the pbOpts.txt File
  with open("./pbOpts.txt", 'w') as optsFile:
    for opts in retVal:
      optsFile.write(opts + "\n")

def is_arm_platform():
  ''' 
  Return true if platform is ARM based
  Currently assumes that ARM platforms will always be aarch64
  '''
  arch = platform.machine().lower()

  if arch == "aarch64":
     return True

  return False

def return_model_path_suffix(gputype: str)->str:
  ''' 
  Returns suffix to append to deep learning model paths
  This is necessary because we have different model files
  for different ARM GPU architectues
  '''
  suffix = ''
  if is_arm_platform():
    if gputype == '90': #GH100
      suffix = '-aarch-grace-hopper/80+'
    elif gputype == '103': # DGX Station (B300)
      suffix = '-aarch-dgx-station/80+'
    elif gputype == '121': # DGX Spark
      suffix = '-aarch-dgx-spark/80+'
    else:
      print("Selected GPU not supported for this platform")
      exitFunction()
  else:
    if(int(gputype) < 75):
      print("Selected GPU not supported for this platform")
      exitFunction()
    if gputype == '75':
      suffix = '/75'
    else:
      suffix = '/80+'

  return suffix

def run_postsort(runArgs, installDir, justCommand, isfq2bam_meth=False):
  #postsort
  ref_file = runArgs.ref
  if isfq2bam_meth:
    suffix = ".bwameth.c2t"
    ref_file = runArgs.ref[:-len(suffix)]
  cmdLine = [installDir + "/bin/postsort", ref_file, "-o", runArgs.out_bam, "-sort_unmapped"]
  bqsrthreads = runArgs.num_gpus
  if runArgs.gpuwrite != None:
    # -zt option becomes moot
    cmdLine.extend(["-gpuwrite"])
    if runArgs.num_gpus > 1:
      bqsrthreads = runArgs.num_gpus - 1

  if isfq2bam_meth:
    cmdLine.extend(["-meth-mode"])

  if runArgs.gpuwrite_deflate_algo != None:
    cmdLine.extend(["-nvcomp-deflate-algo", str(runArgs.gpuwrite_deflate_algo)])

  if runArgs.use_gds == True:
    cmdLine.extend(["-use-gds"])

  if runArgs.low_memory == True or (hasattr(runArgs, "low_memory_postsort") and runArgs.low_memory_postsort == True):
    cmdLine.extend(["-low-memory"])

  cmdLine.extend(["-ft", "4",  "-zt", str(max(1, min(20, GetNumCPUs() - 2 * runArgs.num_gpus - 5))), "-bq", str(bqsrthreads),  "-ngpu", str(runArgs.num_gpus), "-gb", str(runArgs.memory_limit)])
  if runArgs.markdups_assume_sortorder_queryname == True:
    cmdLine.extend(["-mark-query"])
  if runArgs.out_qc_metrics_dir != None:
    cmdLine.extend(["--metrics-dir", runArgs.out_qc_metrics_dir])
    cmdLine.extend(["-cmm", "-gc", str(8)])
  if hasattr(runArgs, "interval") and(runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      cmdLine.extend(["-L", newInterval])
  if hasattr(runArgs, "interval_file") and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      cmdLine.extend(["-L", interval_file])
  if hasattr(runArgs, "interval_padding") and runArgs.interval_padding != None:
    cmdLine.extend(["-ip", str(runArgs.interval_padding)])
  if hasattr(runArgs, "monitor_usage") and runArgs.monitor_usage == True:
    cmdLine.extend(["-monitor-usage"])

  if runArgs.verbose:
    cmdLine.extend(["-v"])
  if (hasattr(runArgs, "standalone_bqsr") == False) or (runArgs.standalone_bqsr == None) or (runArgs.standalone_bqsr == False):
    if hasattr(runArgs, "knownSites") and (runArgs.knownSites != None) and (len(runArgs.knownSites) > 0):
      cmdLine.extend(["-a", runArgs.out_recal_file])
      for site in runArgs.knownSites:
        cmdLine.extend([site])
  AddLogfile(cmdLine, runArgs, True)
  
  if justCommand == True:
    return cmdLine

  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
  shutil.copyfile("chrs.txt", runArgs.out_bam[0:runArgs.out_bam.rfind(".")] + "_chrs.txt")

  if runArgs.out_qc_metrics_dir != None:
    createqcimages(runArgs.out_bam, runArgs.out_qc_metrics_dir, installDir, True)

  return []


def runfq2bam(runArgs, installDir, command_str="fq2bam"):

  if (hasattr(runArgs, "in_se_bam") and runArgs.in_se_bam != None):
    OptMesg("Preprocessing BAM/CRAM input with bam2fq")
    commandArgs = [installDir + "/bin/bam2fq", runArgs.in_se_bam, runArgs.tmp_dir + "/", "--ref", runArgs.ref, "--output-suffixS", "/se.fastq.gz"]
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, printCmd=runArgs.x3)
    if os.path.exists(runArgs.tmp_dir + "/se.fastq.gz") == False:
      OptMesg("The generated single-ended fastq file is empty, please make sure you input bam file contains single-ended reads")
      exitFunction()
    #runArgs.in_se_fq = [["se.fastq.gz", check_se_bam(runArgs.in_se_bam, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)]]
    runArgs.in_se_bam = [runArgs.in_se_bam]
    gen_rg_from_bam_input(runArgs.in_se_bam, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
    runArgs.in_se_fq = [["se.fastq.gz", runArgs.in_se_bam[1]]]

  # SetupOptions(runArgs)
  cmdLine = [installDir + "/bin/pbbwa", runArgs.ref]

  readGroups = []
  if runArgs.in_fq != None:
    cmdLine.extend(["--mode", "pair-ended-gpu"])
    for inputFQ in runArgs.in_fq:
      readGroups.append(inputFQ[2])
      cmdLine.extend([inputFQ[0], inputFQ[1]])
    for rg in readGroups:
      cmdLine.extend(["-R", rg])
  elif runArgs.in_se_fq != None:
    cmdLine.extend(["--mode", "single-ended-gpu"])
    for se_input in runArgs.in_se_fq:
      readGroups.append(se_input[1])
      cmdLine.append(se_input[0])
    for rg in readGroups:
      cmdLine.extend(["-R", rg])
  elif runArgs.pe_fq_list != None:
    cmdLine.extend(["--mode", "pair-ended-gpu"])
    cmdLine.extend(["--in-pe-fq-list-verified", str(runArgs.pe_fq_list)])
  elif runArgs.se_fq_list != None:
    cmdLine.extend(["--mode", "single-ended-gpu"])
    cmdLine.extend(["--in-se-fq-list-verified", str(runArgs.se_fq_list)]) 
      
  cmdLine.extend(["--nGPUs", str(runArgs.num_gpus)])
  if runArgs.low_memory == True:
    OptMesg("Using --low-memory sets the number of streams in bwa mem to 1.")
    runArgs.bwa_nstreams = 1
  cmdLine.extend(["--nstreams", str(runArgs.bwa_nstreams)])
  if runArgs.num_cpu_threads_per_stage != None and runArgs.bwa_cpu_thread_pool == getDefaultBwaCPUThreadPool():
    # use this argument if provided cpu thread pool is still default value
    runArgs.bwa_cpu_thread_pool = runArgs.num_cpu_threads_per_stage
  cmdLine.extend(["--cpu-thread-pool", str(runArgs.bwa_cpu_thread_pool)])
  cmdLine.extend(["--normalized-queue-capacity", str(runArgs.bwa_normalized_queue_capacity)])
  if hasattr(runArgs, "bwa_primary_cpus") and runArgs.bwa_primary_cpus != None and runArgs.bwa_primary_cpus != "auto":
    cmdLine.extend(["--primary-cpu-threads", str(runArgs.bwa_primary_cpus)])
  if runArgs.cigar_on_gpu == True:
    cmdLine.append("--cigar-on-gpu")
  if runArgs.bwa_options != None:
    cmdLine.extend(runArgs.bwa_options.split())
  if runArgs.filter_flag != None:
    cmdLine.extend(["-F", str(runArgs.filter_flag)])
  if runArgs.skip_multiple_hits == True:
    # cmdLine.extend(["-q"])
    cmdLine.append("--skip-multiple-hits")
  if runArgs.min_read_length != None:
    cmdLine.extend(["--min-read-size", str(runArgs.min_read_length)])
  if runArgs.max_read_length != None:
    cmdLine.extend(["--max-read-size", str(runArgs.max_read_length)])
  if runArgs.no_markdups != True:
    cmdLine.append("--markdups")
  if runArgs.markdups_single_ended_start_end == True:
    cmdLine.append("--mark-single-ended")
  if runArgs.fix_mate == True:
    cmdLine.append("--fix-mate")
  if runArgs.use_swlib:
    cmdLine.append("--swlib")
  if runArgs.align_only == True:
    cmdLine.extend(["-o", runArgs.out_bam])
  else:
    cmdLine.append("--write-bin")
  if runArgs.verbose:
    cmdLine.append("--verbose")
  if runArgs.monitor_usage == True:
    cmdLine.extend(["--monitor-usage"])

  WriteCmd(runArgs, command_str)
  AddLogfile(cmdLine, runArgs)
  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  if runArgs.align_only == True:
    return

  #sort
  cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-gb", str(runArgs.memory_limit)]
  if runArgs.gpusort != None:    
    cmdLine.extend(["-gpu", str(runArgs.num_gpus)])    
  if runArgs.no_markdups == True:
    cmdLine.extend(["-no-markdup"])
  if runArgs.markdups_single_ended_start_end == True:
    cmdLine.extend(["-mark-single-ended"])
  if runArgs.ignore_rg_markdups_single_ended == True:
    cmdLine.extend(["-ignore-rg-single-ended"])
  if runArgs.markdups_assume_sortorder_queryname == True:
    cmdLine.extend(["-mark-query"])
  if runArgs.out_duplicate_metrics != None:
    cmdLine.extend(["-r", runArgs.out_duplicate_metrics])
  if runArgs.optical_duplicate_pixel_distance != None:
    cmdLine.extend(["-d", str(runArgs.optical_duplicate_pixel_distance)])
  if runArgs.verbose:
    cmdLine.extend(["-v"])
  if runArgs.monitor_usage == True:
    cmdLine.extend(["-monitor-usage"])
  AddLogfile(cmdLine, runArgs, True)
  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  isfq2bam_meth = command_str == "fq2bam_meth"
  if runArgs.no_postsort == True:
    postsort_cmd = run_postsort(runArgs, installDir, True, isfq2bam_meth=isfq2bam_meth)
    with open("postsort_cmd.txt", "w") as cmdFile:
      cmdFile.write(" ".join(postsort_cmd) + "\n")
  else:
    run_postsort(runArgs, installDir, False, isfq2bam_meth=isfq2bam_meth)


def runfq2bam_meth(runArgs, installDir):
  # first add --meth mode and check for other options
  if runArgs.bwa_options is not None:
    runArgs.bwa_options += " -C -M --meth-mode"
  else:
    # there was a major error
    OptError("Error in setting up fq2bam_meth")
  # check for bwa-meth-specific options
  if runArgs.set_as_failed is not None:
    runArgs.bwa_options += f" --set-as-failed {runArgs.set_as_failed}"
  if runArgs.do_not_penalize_chimeras:
    runArgs.bwa_options += " --do-not-penalize-chimeras"
  if runArgs.low_memory == True:
    OptMesg("Using --low-memory reduces the number of reads sent to GPU per batch in fq2bam_meth.")
    runArgs.bwa_options += " --reduce-batch-size"
  # otherwise, defer to fq2bamfast
  runfq2bam(runArgs, installDir, command_str="fq2bam_meth")


def runbam2fq(runArgs, installDir):
    commandArgs = [installDir + "/bin/bam2fq", runArgs.in_bam, runArgs.out_prefix]
    if runArgs.ref != None:
      commandArgs.extend(["--ref", runArgs.ref])
    if runArgs.out_suffixF != None:
      commandArgs.extend(["--output-suffixF", runArgs.out_suffixF])
    if runArgs.out_suffixF2 != None:
      commandArgs.extend(["--output-suffixF2", runArgs.out_suffixF2])
    if runArgs.out_suffixO != None:
      commandArgs.extend(["--output-suffixO", runArgs.out_suffixO])
    if runArgs.out_suffixO2 != None:
      commandArgs.extend(["--output-suffixO2", runArgs.out_suffixO2])
    if runArgs.out_suffixS != None:
      commandArgs.extend(["--output-suffixS", runArgs.out_suffixS])
    commandArgs.extend(["-t", str(runArgs.num_threads)])
    if runArgs.rg_tag != None:
      commandArgs.extend(["--rg-tag", runArgs.rg_tag])
    if runArgs.remove_qc_failure == True:
      commandArgs.extend(["--remove-qc-failure"])
    if runArgs.verbose:
      commandArgs.extend(["-v"])
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, printCmd=runArgs.x3)


def runhaplotypecaller(runArgs, installDir):
  num_gpus = runArgs.num_gpus
  if runArgs.run_partition != True and num_gpus > 6:
    OptMesg("More than 6 GPUs detected, using only 6 for haplotypecaller")
    num_gpus = 6

  commandArgs = [os.path.join(file_directory, "scheduler.py"), installDir + "/bin/htvc", runArgs.ref, runArgs.in_bam, str(num_gpus), "-o", runArgs.out_variants]
  commandArgs.extend(["-nt", str(runArgs.num_htvc_threads)])
  if runArgs.in_recal_file != None:
    commandArgs.extend(["-a", runArgs.in_recal_file])
  if runArgs.ploidy == 1:
    commandArgs.extend(["-p", "1"])
  if runArgs.gvcf == True:
    commandArgs.extend(["-g"])
  if runArgs.verbose:
    commandArgs.extend(["-v"])
  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])
  if (runArgs.exclude_intervals != None) and len(runArgs.exclude_intervals) > 0:
    for excludeInterval in runArgs.exclude_intervals:
      commandArgs.extend(["-XL", excludeInterval])
  if (runArgs.htvc_bam_output != None):
    commandArgs.extend(["-bamout", runArgs.htvc_bam_output])
  if runArgs.interval_padding != None:
    commandArgs.extend(["-ip", str(runArgs.interval_padding)])
  if (runArgs.static_quantized_quals != None) and len(runArgs.static_quantized_quals) > 0:
    for qual in runArgs.static_quantized_quals:
      commandArgs.extend(["-static-quantized-quals", str(qual)])
  if (runArgs.disable_read_filter != None) and len(runArgs.disable_read_filter) > 0:
    for disabled_filter in runArgs.disable_read_filter:
      commandArgs.extend(["-disable-read-filter", disabled_filter])
  if runArgs.max_alternate_alleles != None:
    commandArgs.extend(["--max-alternate-alleles", str(runArgs.max_alternate_alleles)])
  if runArgs.rna == True:
    commandArgs.extend(["-rna"])
  if runArgs.dont_use_soft_clipped_bases == True:
    commandArgs.extend(["--dont-use-soft-clipped-bases"])
  if runArgs.read_from_tmp_dir == True:
    commandArgs.extend(["-read-tmp"])
  if (runArgs.annotation_group != None) and len(runArgs.annotation_group) > 0:
    for annotation_group in runArgs.annotation_group:
      commandArgs.extend(["-G", annotation_group])
  if (runArgs.gvcf_gq_bands != None) and len(runArgs.gvcf_gq_bands) > 0:
    for band in runArgs.gvcf_gq_bands:
      commandArgs.extend(["--gvcf-gq-bands", str(band)])
  if (runArgs.run_partition == True):
    commandArgs.extend(["--run-partition"])
  if (runArgs.no_alt_contigs == True):
    commandArgs.extend(["--no-alt-contigs"])
  if (runArgs.gpu_num_per_partition != None):
    commandArgs.extend(["--gpu-num-per-partition", str(runArgs.gpu_num_per_partition)])
  if runArgs.haplotypecaller_options != None:
    commandArgs.extend(runArgs.haplotypecaller_options.split())
  if runArgs.htvc_low_memory == True:
    commandArgs.extend(["--low-memory"])
  if runArgs.minimum_mapping_quality != None:
    commandArgs.extend(["--minimum-mapping-quality", str(runArgs.minimum_mapping_quality)])
  if runArgs.mapping_quality_threshold_for_genotyping != None:
    commandArgs.extend(["--mapping-quality-threshold-for-genotyping", str(runArgs.mapping_quality_threshold_for_genotyping)])
  if runArgs.enable_dynamic_read_disqualification_for_genotyping == True:
    commandArgs.extend(["--enable-dynamic-read-disqualification-for-genotyping"])
  if runArgs.min_base_quality_score != None:
    commandArgs.extend(["--min-base-quality-score", str(runArgs.min_base_quality_score)])
  if runArgs.adaptive_pruning != None:
    commandArgs.extend(["--adaptive-pruning"])
  if runArgs.htvc_alleles != None:
    commandArgs.extend(["--alleles", runArgs.htvc_alleles])
  if runArgs.force_call_filtered_alleles == True:
    commandArgs.extend(["--force-call-filtered-alleles"])
  if runArgs.filter_reads_too_long == True:
    commandArgs.extend(["--filter-reads-too-long"])


  WriteVcfCmd(runArgs, "haplotypecaller")
  AddLogfile(commandArgs, runArgs)

  postsort_process = None
  postsort_cmd = None
  if runArgs.read_from_tmp_dir == True:
    with open("postsort_cmd.txt") as p:
      postsort_cmd = p.readline().split(" ")
      postsort_process = RunBinaryNoWait(postsort_cmd, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
    os.remove("postsort_cmd.txt")

  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  if (postsort_process != None):
    retVal = postsort_process.wait()
    if retVal != 0:
      handle_return_vals(retVal)
      exitFunction()

    #postsort_cmd[3] is out bam name
    shutil.copyfile("chrs.txt", postsort_cmd[3][0:postsort_cmd[3].rfind(".")] + "_chrs.txt")
    #no --metrics-dir called in pipeline

def runpangenome_aware_deepvariant(runArgs, installDir):
  modelOpt = []
  notTheFirstCall = False # Should logger append?
  if runArgs.pb_model_file != None:
    modelOpt = ["--model", runArgs.pb_model_file]
  else:
    dQueryArgs = [installDir + "/bin/deviceQuery", str(runArgs.num_gpus)]
    if runArgs.x3 == True:
      dQueryArgs.extend(["1"])
    AddLogfile(dQueryArgs, runArgs, notTheFirstCall)
    notTheFirstCall = True
    RunBinary(dQueryArgs, installDir)
    gputype = ""
    with open("gputype.txt") as gpuarchFile:
      gputype = gpuarchFile.readline().rstrip()
      if int(gputype) < 75:
        print("Selected model not supported for this GPU type.")
        exitFunction()
    
    model_path_suffix = return_model_path_suffix(gputype)

    modelOpt = ["--model", installDir + "/model" + model_path_suffix + "/" + runArgs.mode + "/deepvariant_pangenome_aware.eng"]

  commandArgs = [os.path.join(file_directory, "scheduler_deepsomatic.py"), installDir + "/bin/deepsomatic", str(runArgs.num_gpus), str(runArgs.num_streams_per_gpu), "--ref", runArgs.ref, "--reads", runArgs.in_bam, "-o", runArgs.out_variants, "-n", str(runArgs.num_cpu_threads_per_stream), "--pangenome", runArgs.pangenome] + modelOpt
  if runArgs.verbose:
    commandArgs.extend(["-v"])

  #always turn on long_read for pangenome_aware
  commandArgs.extend(["-long_reads"])

  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])

  if (runArgs.run_partition == True):
    commandArgs.extend(["--run-partition"])
  if (runArgs.gpu_num_per_partition != None):
    commandArgs.extend(["--gpu-num-per-partition", str(runArgs.gpu_num_per_partition)])

  if (runArgs.no_channel_insert_size == False):
    commandArgs.extend(["--channel_insert_size"])

  if runArgs.norealign_reads:
    commandArgs.extend(["-norealign_reads"])

  if runArgs.disable_use_window_selector_model == True:
    commandArgs.extend(["-disable-use-window-selector-model"])

  commandArgs.extend(["--keep_legacy_allele_counter_behavior"])
  commandArgs.extend(["--keep_only_window_spanning_haplotypes"])
  commandArgs.extend(["--keep_supplementary_alignments"])
  commandArgs.extend(["--min_mapping_quality", str(runArgs.min_mapping_quality)])

  commandArgs.extend(["--normalize_reads"])
  commandArgs.extend(["--sort_by_haplotypes"])
  commandArgs.extend(["--parse_sam_aux_fields"])

  WriteVcfCmd(runArgs, "pangenome_aware_deepvariant")
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, lib_paths=[installDir + "/deepvariant_libs", installDir + "/trt10.14_libs"], petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

def rundeepsomatic(runArgs, installDir):
  modelOpt = []
  notTheFirstCall = False # Should logger append?
  if runArgs.pb_model_file != None:
    modelOpt = ["--model", runArgs.pb_model_file]
  else:
    dQueryArgs = [installDir + "/bin/deviceQuery", str(runArgs.num_gpus)]
    if runArgs.x3 == True:
      dQueryArgs.extend(["1"])
    AddLogfile(dQueryArgs, runArgs, notTheFirstCall)
    notTheFirstCall = True
    RunBinary(dQueryArgs, installDir)
    gputype = ""
    with open("gputype.txt") as gpuarchFile:
      gputype = gpuarchFile.readline().rstrip()
      if int(gputype) < 75:
        print("Selected model not supported for this GPU type.")
        exitFunction()
    
    model_path_suffix = return_model_path_suffix(gputype)

    if runArgs.use_wes_model:#if use_wes_model, then mode == shortread for sure
      modelOpt = ["--model", installDir + "/model" + model_path_suffix  + "/" + runArgs.mode + "/deepsomatic_wes.eng"]
    else:
      modelOpt = ["--model", installDir + "/model" + model_path_suffix  + "/" + runArgs.mode + "/deepsomatic.eng"]
      
  #commandArgs = [installDir + "/bin/deepsomatic", str(runArgs.num_gpus), str(runArgs.num_streams_per_gpu), "--ref", runArgs.ref, "--reads_tumor", runArgs.in_tumor_bam, "--reads_normal", runArgs.in_normal_bam, "-o", runArgs.out_variants, "-n", str(runArgs.num_cpu_threads_per_stream), "--deepsomatic", "--process_somatic"] + modelOpt
  commandArgs = [os.path.join(file_directory, "scheduler_deepsomatic.py"), installDir + "/bin/deepsomatic", str(runArgs.num_gpus), str(runArgs.num_streams_per_gpu), "--ref", runArgs.ref, "--reads_tumor", runArgs.in_tumor_bam, "--reads_normal", runArgs.in_normal_bam, "-o", runArgs.out_variants, "-n", str(runArgs.num_cpu_threads_per_stream), "--deepsomatic", "--process_somatic"] + modelOpt

  if runArgs.verbose:
    commandArgs.extend(["-v"])
  if runArgs.mode != "shortread":
    commandArgs.extend(["-long_reads"])
  
  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])
  
  if (runArgs.run_partition == True):
    commandArgs.extend(["--run-partition"])
  if (runArgs.gpu_num_per_partition != None):
    commandArgs.extend(["--gpu-num-per-partition", str(runArgs.gpu_num_per_partition)])

  if (runArgs.no_channel_insert_size == False):
    commandArgs.extend(["--channel_insert_size"])
  if runArgs.norealign_reads:
    commandArgs.extend(["-norealign_reads"])
  if runArgs.add_hp_channel:
    commandArgs.extend(["--add_hp_channel"])
  if runArgs.sort_by_haplotypes:
    commandArgs.extend(["--sort_by_haplotypes"])
  if runArgs.parse_sam_aux_fields:
    commandArgs.extend(["--parse_sam_aux_fields"])
  if runArgs.phase_reads == True:
    commandArgs.extend(["--phase_reads"])
  if runArgs.track_ref_reads == True:
    commandArgs.extend(["--track_ref_reads"])
  if runArgs.disable_use_window_selector_model == True:
    commandArgs.extend(["-disable-use-window-selector-model"])
#   if runArgs.realign_all == True:
#     commandArgs.extend(["--realign_all"])
#   if runArgs.create_complex_alleles == True:
#     commandArgs.extend(["--create_complex_alleles"])
#   if runArgs.max_read_length_to_realign != None:
#     commandArgs.extend(["--max_read_length_to_realign", str(runArgs.max_read_length_to_realign)])
  
  commandArgs.extend(["--pileup_image_width", str(runArgs.pileup_image_width)])
  commandArgs.extend(["--partition_size", str(runArgs.partition_size)])
  commandArgs.extend(["--vsc_min_count_snps", str(runArgs.vsc_min_count_snps), "--vsc_min_count_indels", str(runArgs.vsc_min_count_indels)])
  commandArgs.extend(["--vsc_min_fraction_snps", str(runArgs.vsc_min_fraction_snps), "--vsc_min_fraction_indels", str(runArgs.vsc_min_fraction_indels)])
  commandArgs.extend(["--min_mapping_quality", str(runArgs.min_mapping_quality), "--min_base_quality", str(runArgs.min_base_quality)])
  commandArgs.extend(["--alt_aligned_pileup", str(runArgs.alt_aligned_pileup)])
  commandArgs.extend(["--vsc_max_fraction_indels_for_non_target_sample", str(runArgs.vsc_max_fraction_indels_for_non_target_sample), "--vsc_max_fraction_snps_for_non_target_sample", str(runArgs.vsc_max_fraction_snps_for_non_target_sample)])

  WriteVcfCmd(runArgs, "deepsomatic")
  AddLogfile(commandArgs, runArgs, notTheFirstCall)

  RunBinary(commandArgs, installDir, lib_paths=[installDir + "/deepvariant_libs", installDir + "/trt10.14_libs"], petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

def rundeepvariant(runArgs, installDir):
  modelOpt = []
  notTheFirstCall = False # Should logger append?
  gputype = ""
  
  ## Extract GPU type. Needed for model selection
  dQueryArgs = [installDir + "/bin/deviceQuery", str(runArgs.num_gpus)]
  if runArgs.x3 == True:
    dQueryArgs.extend(["1"])
  AddLogfile(dQueryArgs, runArgs, notTheFirstCall)
  notTheFirstCall = True
  RunBinary(dQueryArgs, installDir)
  with open("gputype.txt") as gpuarchFile:
    gputype = gpuarchFile.readline().rstrip()
    if int(gputype) < 75:
      print("Selected model not supported for this GPU type.")
      exitFunction()
  
  
  model_path_suffix = return_model_path_suffix(gputype)
  cnn_model_path_suffix = model_path_suffix

  if runArgs.pb_model_file != None:
    modelOpt = ["--model", runArgs.pb_model_file]
  else:
    if runArgs.use_tf32 and gputype != "75":
      cnn_model_path_suffix = cnn_model_path_suffix + "_TF32"
    
    if runArgs.use_wes_model:#if use_wes_model, then mode == shortread for sure
      modelOpt = ["--model", installDir + "/model" + cnn_model_path_suffix + "/" + runArgs.mode + "/deepvariant_wes.eng"]
    else:
      modelOpt = ["--model", installDir + "/model" + cnn_model_path_suffix + "/" + runArgs.mode + "/deepvariant.eng"]
  
  smallModelOpt = []
  if runArgs.enable_small_model != True and runArgs.pb_small_model_file is not None:
    OptMesg("Small model is not enabled, but --pb-small-model-file is provided. Ignoring --pb-small-model-file.")
  
  if runArgs.enable_small_model == True:
    if runArgs.pb_small_model_file is not None:
      smallModelOpt = ["--small_model", runArgs.pb_small_model_file]
    else:
      smallModelOpt = ["--small_model", installDir + "/smallmodel" + model_path_suffix + "/" + runArgs.mode + "/deepvariant_sm.eng"]
  
  if runArgs.use_tf32 and runArgs.enable_small_model == True:
    OptMesg("Small model currently does not support TF32. Only CNN will use TF32.")
  
  smallModelParametersOpt = []
  if runArgs.enable_small_model == True:
    smallModelParametersOpt = ["--call_small_model_examples"]
    smallModelParametersOpt.extend(["--small_model_call_multiallelics"])
    if runArgs.mode == "shortread":
      smallModelParametersOpt.extend(["--small_model_snp_gq_threshold", "20"])
      smallModelParametersOpt.extend(["--small_model_indel_gq_threshold", "28"])
      smallModelParametersOpt.extend(["--small_model_vaf_context_window_size", "51"])
    elif runArgs.mode == "pacbio":
      smallModelParametersOpt.extend(["--small_model_snp_gq_threshold", "15"])
      smallModelParametersOpt.extend(["--small_model_indel_gq_threshold", "16"])
      smallModelParametersOpt.extend(["--small_model_vaf_context_window_size", "51"])
    elif runArgs.mode == "ont":
      smallModelParametersOpt.extend(["--small_model_snp_gq_threshold", "9"])
      smallModelParametersOpt.extend(["--small_model_indel_gq_threshold", "17"])
      smallModelParametersOpt.extend(["--small_model_vaf_context_window_size", "51"])

#   commandArgs = [os.path.join(file_directory, "scheduler_deepvariant.py"), installDir + "/bin/deepvariant", runArgs.ref, runArgs.in_bam, str(runArgs.num_gpus), str(runArgs.num_streams_per_gpu), "-o", runArgs.out_variants, "-n", str(runArgs.num_cpu_threads_per_stream)] + modelOpt
  commandArgs = [os.path.join(file_directory, "scheduler_deepsomatic.py"), installDir + "/bin/deepsomatic", str(runArgs.num_gpus), str(runArgs.num_streams_per_gpu), "--ref", runArgs.ref, "--reads", runArgs.in_bam, "-o", runArgs.out_variants, "-n", str(runArgs.num_cpu_threads_per_stream)] + modelOpt
  if runArgs.enable_small_model == True:
    commandArgs.extend(smallModelOpt)
    commandArgs.extend(smallModelParametersOpt)

  if runArgs.verbose:
    commandArgs.extend(["-v"])
  if runArgs.gvcf == True:
    commandArgs.extend(["-g"])
  if runArgs.disable_use_window_selector_model == True:
    commandArgs.extend(["-disable-use-window-selector-model"])
  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])
  #New things from DV1.0
  if runArgs.mode != "shortread":
    commandArgs.extend(["-long_reads"])
  if runArgs.mode == "pacbio":
    commandArgs.extend(["--parse_base_methylation"])
  if runArgs.keep_duplicates == True:
    commandArgs.extend(["-keep_duplicates"])
  if runArgs.keep_legacy_allele_counter_behavior == True:
    commandArgs.extend(["--keep_legacy_allele_counter_behavior"])
  if runArgs.sort_by_haplotypes == True:
    commandArgs.extend(["--sort_by_haplotypes"])
  if runArgs.add_hp_channel == True:
    commandArgs.extend(["--add_hp_channel"])
  if runArgs.parse_sam_aux_fields == True:
    commandArgs.extend(["--parse_sam_aux_fields"])
  if runArgs.norealign_reads == True:
    commandArgs.extend(["-norealign_reads"])
  if runArgs.max_read_size_512 == True:
    commandArgs.extend(["--max_read_size_512"])
  if runArgs.prealign_helper_thread == True:
    commandArgs.extend(["--prealign_helper_thread"])
  if runArgs.vsc_min_fraction_indels != None:
    commandArgs.extend(["--vsc_min_fraction_indels", str(runArgs.vsc_min_fraction_indels)])
  if runArgs.track_ref_reads == True:
    commandArgs.extend(["--track_ref_reads"])
  if runArgs.phase_reads == True:
    commandArgs.extend(["--phase_reads"])
  if runArgs.include_med_dp == True:
    commandArgs.extend(["--include_med_dp"])
  if runArgs.normalize_reads == True:
    commandArgs.extend(["--normalize_reads"])
  if runArgs.channel_insert_size == True:
    commandArgs.extend(["--channel_insert_size"])

  commandArgs.extend(["--pileup_image_width", str(runArgs.pileup_image_width)])
  commandArgs.extend(["--max_reads_per_partition", str(runArgs.max_reads_per_partition)])
  commandArgs.extend(["--partition_size", str(runArgs.partition_size)])
  commandArgs.extend(["--vsc_min_count_snps", str(runArgs.vsc_min_count_snps), "--vsc_min_count_indels", str(runArgs.vsc_min_count_indels)])
  commandArgs.extend(["--vsc_min_fraction_snps", str(runArgs.vsc_min_fraction_snps)])
  commandArgs.extend(["--min_mapping_quality", str(runArgs.min_mapping_quality), "--min_base_quality", str(runArgs.min_base_quality)])
  commandArgs.extend(["--alt_aligned_pileup", str(runArgs.alt_aligned_pileup), "--variant_caller", str(runArgs.variant_caller)])
  if runArgs.proposed_variants != None:
    commandArgs.extend(["--proposed_variants", runArgs.proposed_variants])

  if (runArgs.dbg_min_base_quality != None):
    commandArgs.extend(["--dbg_min_base_quality", str(runArgs.dbg_min_base_quality)])
  if (runArgs.ws_min_windows_distance != None):
    commandArgs.extend(["--ws_min_windows_distance", str(runArgs.ws_min_windows_distance)])
  if (runArgs.channel_gc_content == True):
    commandArgs.extend(["--channel_gc_content"])
  if (runArgs.channel_hmer_deletion_quality == True):
    commandArgs.extend(["--channel_hmer_deletion_quality"])
  if (runArgs.channel_hmer_insertion_quality == True):
    commandArgs.extend(["--channel_hmer_insertion_quality"])
  if (runArgs.channel_non_hmer_insertion_quality == True):
    commandArgs.extend(["--channel_non_hmer_insertion_quality"])
  if (runArgs.skip_bq_channel == True):
    commandArgs.extend(["--skip_bq_channel"])
  if (runArgs.aux_fields_to_keep != None):
    commandArgs.extend(["--aux_fields_to_keep", runArgs.aux_fields_to_keep])
  if (runArgs.vsc_min_fraction_hmer_indels != None):
    commandArgs.extend(["--vsc_min_fraction_hmer_indels", str(runArgs.vsc_min_fraction_hmer_indels)])
  if (runArgs.vsc_turn_on_non_hmer_ins_proxy_support == True):
    commandArgs.extend(["--vsc_turn_on_non_hmer_ins_proxy_support"])
  if (runArgs.consider_strand_bias == True):
    commandArgs.extend(["--consider_strand_bias"])
  if (runArgs.p_error != None):
    commandArgs.extend(["--p_error", str(runArgs.p_error)])
  if (runArgs.channel_ins_size == True):
    commandArgs.extend(["--channel_ins_size"])
  if (runArgs.max_ins_size != None):
    commandArgs.extend(["--max_ins_size", str(runArgs.max_ins_size)])
  if (runArgs.disable_group_variants == True):
    commandArgs.extend(["--disable_group_variants"])
  if (runArgs.filter_reads_too_long == True):
    commandArgs.extend(["--filter_reads_too_long"])
  if (runArgs.haploid_contigs != None):
    commandArgs.extend(["--haploid_contigs", runArgs.haploid_contigs])
#   if(runArgs.realign_all != None):
#     commandArgs.extend(["--realign_all"])
#   if(runArgs.create_complex_alleles != None):
#     commandArgs.extend(["--create_complex_alleles"])
#   if(runArgs.max_read_length_to_realign != None):
#     commandArgs.extend(["--max_read_length_to_realign", str(runArgs.max_read_length_to_realign)])
  if runArgs.enable_small_model == True and runArgs.track_ref_reads != True:
    print("Warning: --enable-small-model requires --track-ref-reads to be enabled. Enabling --track-ref-reads.", flush=True)
    commandArgs.extend(["--track_ref_reads"])
  
  if runArgs.read_from_tmp_dir == True:
    commandArgs.extend(["-read-tmp"])
  if (runArgs.run_partition == True):
    commandArgs.extend(["--run-partition"])
  if (runArgs.gpu_num_per_partition != None):
    commandArgs.extend(["--gpu-num-per-partition", str(runArgs.gpu_num_per_partition)])
  
  WriteVcfCmd(runArgs, "deepvariant")
  AddLogfile(commandArgs, runArgs, notTheFirstCall)
  postsort_process = None
  postsort_cmd = None
  if runArgs.read_from_tmp_dir == True:
    with open("postsort_cmd.txt") as p:
      postsort_cmd = p.readline().split(" ")
      postsort_process = RunBinaryNoWait(postsort_cmd, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
    os.remove("postsort_cmd.txt")

  RunBinary(commandArgs, installDir, lib_paths=[installDir + "/deepvariant_libs", installDir + "/trt10.14_libs"], petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  if (postsort_process != None):
    retVal = postsort_process.wait()
    if retVal != 0:
      handle_return_vals(retVal)
      exitFunction()

    #postsort_cmd[3] is out bam name
    shutil.copyfile("chrs.txt", postsort_cmd[3][0:postsort_cmd[3].rfind(".")] + "_chrs.txt")
    #no --metrics-dir called in pipeline


def runminimap2(runArgs, installDir):
  commandArgs = [installDir + "/bin/minimap2"]

  # reduce mem usage for splice runs if not used
  splice_alignment = "splice" in runArgs.preset
  splice_sr_preset = runArgs.preset == "splice:sr"
  if runArgs.max_queue_chunks == None and splice_alignment and not splice_sr_preset:
    runArgs.max_queue_chunks = 1

  if runArgs.in_bam != None:
    commandArgs.extend(["-B", runArgs.in_bam[0], "-R", runArgs.in_bam[1]])
  else:
    for idx in range(0, len(runArgs.in_fq) - 1):
      commandArgs.extend(["-q", runArgs.in_fq[idx]])
    commandArgs.extend(["-R", runArgs.in_fq[-1]])

  if runArgs.index != None:
    commandArgs.extend(["-r", runArgs.index])
  else:
    commandArgs.extend(["-r", runArgs.ref])

  if runArgs.jump_bed != None:
    commandArgs.extend(["--input-jump-bed", runArgs.jump_bed])

  if runArgs.junc_bed != None:
    commandArgs.extend(["--input-junc-bed", runArgs.junc_bed])

  commandArgs.extend(["-O", runArgs.out_bam])
  commandArgs.extend(["-c"]) # force run chaining on CPU
  commandArgs.extend(["--preset", runArgs.preset])
  if runArgs.pbmm2 != None:
    commandArgs.extend(["-f"])
  if runArgs.pbmm2_unmapped != None:
    commandArgs.extend(["-u"])
  if runArgs.minimizer_kmer_len != None:
    commandArgs.extend(["-k", str(runArgs.minimizer_kmer_len)])
  if runArgs.both_strands != None:
    commandArgs.extend(["--both-strands"])
  if runArgs.forward_transcript_strand != None:
    commandArgs.extend(["--forward-transcript-strand"])
  if runArgs.md != None:
    commandArgs.extend(["--md"])
  if runArgs.copy_comment != None:
    commandArgs.extend(["--copy-comment"])
  if runArgs.eqx != None:
    commandArgs.extend(["-e"])
  commandArgs.extend(["-g", str(runArgs.num_gpus)])
  commandArgs.extend(["-t", str(runArgs.num_threads)])
  commandArgs.extend(["--stage4-stage4-instances-per-gpu", str(runArgs.nstreams)])
  commandArgs.extend(["--chunk-size", str(runArgs.chunk_size)])
  commandArgs.extend(["--mem-pool-buf-size", str(runArgs.mem_pool_buf_size)])
  commandArgs.extend(["--free-queue-batch-size", str(runArgs.free_queue_batch_size)])
  if runArgs.max_queue_chunks != None:
    commandArgs.extend(["--max-queue-chunks", str(runArgs.max_queue_chunks)])
  commandArgs.extend(["--max-queue-reads", str(runArgs.max_queue_reads)])
  commandArgs.extend(["--stage4-max-cpu-workers-per-instance", str(runArgs.num_alignment_workers_per_thread)])
  if runArgs.alignment_thread_num_divisor != None:
    commandArgs.extend(["--stage4-min-alignments-per-worker", str(runArgs.alignment_thread_num_divisor)])
  if runArgs.alignment_large_pair_size != None:
    commandArgs.extend(["--stage4-large-alignment-pair-size", str(runArgs.alignment_large_pair_size)])
  if runArgs.alignment_midsize_pair_size != None:
    commandArgs.extend(["--stage4-midsize-alignment-pair-size", str(runArgs.alignment_midsize_pair_size)])
  if runArgs.process_large_alignments_on_gpu == None:
    commandArgs.extend(["--stage4-process-large-alignments-on-cpu"])
  if runArgs.no_balancing_large_alignments != None:
    commandArgs.extend(["--stage4-no-balancing-large-alignments"])
  if runArgs.process_all_alignments_on_cpu_threshold != None:
    commandArgs.extend(["--stage4-process-all-alignments-on-cpu-threshold", str(runArgs.process_all_alignments_on_cpu_threshold)])
  if runArgs.num_alignment_device_mem_buffers != None:
    commandArgs.extend(["--stage4-num-device-mem-buffers", str(runArgs.num_alignment_device_mem_buffers)])
  else:
    commandArgs.extend(["--stage4-num-device-mem-buffers", str(runArgs.nstreams)]) # argument not used, match it to specified gpu streams
  if runArgs.alignment_on_cpu != None:
    commandArgs.extend(["-a"])
  if runArgs.verbose:
    commandArgs.extend(["-v"])

  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  #sort
  cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-gb", str(runArgs.memory_limit)]
  if runArgs.gpusort != None:    
    cmdLine.extend(["-gpu", str(runArgs.num_gpus)])    
  if runArgs.no_markdups == True:
    cmdLine.extend(["-no-markdup"])
  if runArgs.markdups_assume_sortorder_queryname == True:
    cmdLine.extend(["-mark-query"])
  if runArgs.out_duplicate_metrics != None:
    cmdLine.extend(["-r", runArgs.out_duplicate_metrics])
  if runArgs.optical_duplicate_pixel_distance != None:
    cmdLine.extend(["-d", str(runArgs.optical_duplicate_pixel_distance)])
  if runArgs.verbose:
    cmdLine.extend(["-v"])
  AddLogfile(cmdLine, runArgs, True)
  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  #postsort
  if runArgs.no_postsort == True:
    postsort_cmd = run_postsort(runArgs, installDir, True)
    with open("postsort_cmd.txt", "w") as cmdFile:
      cmdFile.write(" ".join(postsort_cmd) + "\n")
  else:
    run_postsort(runArgs, installDir, False)


def rungiraffe(runArgs, installDir):
  commandArgs = [installDir + "/bin/pbgiraffe"]

  if runArgs.no_markdups == True:
    OptMesg("Marking Duplicates will not be run")
  else:
    OptMesg("Marking Duplicates will be run during sorting stages")

  # add read group info
  if runArgs.read_group:  # rg ID
    commandArgs.extend(["--read-group", runArgs.read_group])
  if runArgs.sample:  # rg sample
    commandArgs.extend(["--sample", runArgs.sample])
  if runArgs.read_group_library:  # read group library tag (LB)
    commandArgs.extend(["--read-group-library", runArgs.read_group_library])
  if runArgs.read_group_platform:  # read group platform tag ("PL")
    commandArgs.extend(["--read-group-platform", runArgs.read_group_platform])
  if runArgs.read_group_pu:  # read group platform unit tag (PU)
    commandArgs.extend(["--read-group-pu", runArgs.read_group_pu])

  # input
  if runArgs.in_se_fq and (len(runArgs.in_se_fq) > 0):
    commandArgs.extend(["--fastq-in", runArgs.in_se_fq[0][0]])
  elif runArgs.in_fq and (len(runArgs.in_fq) > 0):
    commandArgs.extend(["--fastq-in-r1", runArgs.in_fq[0][0]])
    commandArgs.extend(["--fastq-in-r2", runArgs.in_fq[0][1]])
  if runArgs.min_read_length != None:
    commandArgs.extend(["--min-read-size", str(runArgs.min_read_length)])
  if runArgs.max_read_length != None:
    commandArgs.extend(["--max-read-size", str(runArgs.max_read_length)])
  if runArgs.pe_fq_list != None:
    commandArgs.extend(["--in-pe-fq-list-verified", str(runArgs.pe_fq_list)])
  if runArgs.se_fq_list != None:
    commandArgs.extend(["--in-se-fq-list-verified", str(runArgs.se_fq_list)])

  # index files
  commandArgs.extend(["-Z", runArgs.gbz_name])
  commandArgs.extend(["-d", runArgs.dist_name])
  commandArgs.extend(["-m", runArgs.minimizer_name])
  commandArgs.extend(["-z", runArgs.zipcodes_name])
  if (runArgs.xg_name != None):
    commandArgs.extend(["-x", runArgs.xg_name])
  if (runArgs.graph_name != None):
    OptMesg("WARNING: -g/--graph is deprecated and will be ignored. The GBZ file contains the graph information.")
  if (runArgs.gbwt_name != None):
    OptMesg("WARNING: -H/--gbwt is deprecated and will be ignored. The GBZ file contains the GBWT information.")
  
  # output
  if runArgs.align_only == True:
    commandArgs.extend(["-o", runArgs.out_bam])
  else:
    commandArgs.extend(["--write-bin"])

  # other
  if runArgs.prune_low_cplx:
    commandArgs.extend(["--prune-low-cplx"])
  if runArgs.max_fragment_length:
    commandArgs.extend(["--max-fragment-length", str(runArgs.max_fragment_length)])
  if runArgs.fragment_mean:
    commandArgs.extend(["--fragment-mean", str(runArgs.fragment_mean)])
  if runArgs.fragment_stdev:
    commandArgs.extend(["--fragment-stdev", str(runArgs.fragment_stdev)])
  if runArgs.testing_options != None:
    commandArgs.extend(runArgs.testing_options.split())
  if runArgs.copy_comment != None and runArgs.copy_comment == True:
    commandArgs.extend(["--copy-comment"])
  if runArgs.ref_paths != None:
    commandArgs.extend(["--ref-paths", str(runArgs.ref_paths)])
  if runArgs.no_markdups != True:
    commandArgs.append("--mark-duplicates")
  if runArgs.markdups_single_ended_start_end == True:
    commandArgs.append("--mark-single-ended")

  # performance
  if runArgs.num_primary_cpus_per_gpu is not None:
    runArgs.num_cpu_threads_per_gpu = runArgs.num_primary_cpus_per_gpu
  if runArgs.low_memory == True:
    runArgs.nstreams = 1
    runArgs.batch_size = 5000 # reduced batch size
    runArgs.work_queue_capacity = 10 # reduced work queue capacity
    runArgs.minimizers_gpu = False # minimizers on GPU are disabled in low-memory mode
    runArgs.dozeu_gpu = False # dozeu is disabled in low-memory mode
    OptMesg("Using --low-memory sets the number of streams to 1, reduces work queue capacity to 10, decreases the batch size to 5000, and computes `Minimizer and Seeds` and `Finalize Mappings` on CPU.")
  commandArgs.extend(["--num-primary-cpus-per-gpu", str(runArgs.num_cpu_threads_per_gpu)])
  commandArgs.extend(["--nGPUs", str(runArgs.num_gpus)])
  commandArgs.extend(["--nstreams", str(runArgs.nstreams)])
  commandArgs.extend(["--batch-size", str(runArgs.batch_size)])
  if getattr(runArgs, 'work_queue_capacity', None) is not None:
    commandArgs.extend(["--work-queue-capacity", str(runArgs.work_queue_capacity)])
  commandArgs.extend(["--write-threads", str(runArgs.write_threads)])
  commandArgs.extend(["--monitor"])
  if runArgs.monitor_usage and runArgs.monitor_usage == True:
    commandArgs.extend(["--monitor-usage"])
  if runArgs.minimizers_gpu == True:
    commandArgs.append("--minimizers-seeds-gpu")
  if runArgs.dozeu_gpu == True:
    commandArgs.extend(["--dozeu-gpu"])

  WriteCmd(runArgs, "giraffe")
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, lib_paths=[installDir + "/giraffe_libs"], petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  # no sorting if we're only aligning
  if runArgs.align_only == True:
    return

  #sort
  cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-gb", str(runArgs.memory_limit)]
  if runArgs.gpusort != None:    
    cmdLine.extend(["-gpu", str(runArgs.num_gpus)])    
  if runArgs.no_markdups == True:
    cmdLine.extend(["-no-markdup"])
  if runArgs.markdups_single_ended_start_end == True:
    cmdLine.append("-mark-single-ended")
  if runArgs.ignore_rg_markdups_single_ended == True:
    cmdLine.append("-ignore-rg-single-ended")
  if runArgs.markdups_assume_sortorder_queryname == True:
    cmdLine.extend(["-mark-query"])
  if hasattr(runArgs, "out_duplicate_metrics") and runArgs.out_duplicate_metrics != None:
    cmdLine.extend(["-r", runArgs.out_duplicate_metrics])
  if hasattr(runArgs, "optical_duplicate_pixel_distance") and runArgs.optical_duplicate_pixel_distance != None:
    cmdLine.extend(["-d", str(runArgs.optical_duplicate_pixel_distance)])
  if runArgs.verbose:
    cmdLine.extend(["-v"])
  if runArgs.monitor_usage and runArgs.monitor_usage == True:
    cmdLine.extend(["-monitor-usage"])
  AddLogfile(cmdLine, runArgs, True)
  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  runArgs.ref = "/dev/null"  # we don't have a linear reference so ignore
  run_postsort(runArgs, installDir, False, isfq2bam_meth=False)



def runmutectcaller(runArgs, installDir):
  commandArgs = [os.path.join(file_directory, "scheduler_mutect.py"), installDir + "/bin/mutect", runArgs.ref, runArgs.in_tumor_bam, str(runArgs.num_gpus), "-o", runArgs.out_vcf, "-tumorsample", runArgs.tumor_name]
  commandArgs.extend(["-nt", str(runArgs.num_htvc_threads)])
  if runArgs.in_normal_bam != None:
    commandArgs.extend(["-normalbam", runArgs.in_normal_bam, "-normalsample", runArgs.normal_name])
  if runArgs.in_tumor_recal_file != None:
    commandArgs.extend(["-tumorbqsr", runArgs.in_tumor_recal_file])
    if runArgs.in_normal_recal_file != None:
      commandArgs.extend(["-normalbqsr", runArgs.in_normal_recal_file])
  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])
  if runArgs.interval_padding != None:
    commandArgs.extend(["-ip", str(runArgs.interval_padding)])
  if runArgs.max_mnp_distance != None:
    commandArgs.extend(["-max-mnp-distance", str(runArgs.max_mnp_distance)])
  if runArgs.pon != None:
    commandArgs.extend(["-pon", runArgs.pon])
  if runArgs.mutectcaller_options != None:
    commandArgs.extend(runArgs.mutectcaller_options.split())
  if runArgs.mutect_low_memory == True:
    commandArgs.extend(["--low-memory"])
  if (runArgs.run_partition == True):
    commandArgs.extend(["--run-partition"])
  if (runArgs.no_alt_contigs == True):
    commandArgs.extend(["--no-alt-contigs"])
  if (runArgs.gpu_num_per_partition != None):
    commandArgs.extend(["--gpu-num-per-partition", str(runArgs.gpu_num_per_partition)])
  if runArgs.verbose:
    commandArgs.extend(["-v"])

  if runArgs.mutect_bam_output is not None:
    commandArgs.extend(["-bamout", runArgs.mutect_bam_output])
  if runArgs.initial_tumor_lod is not None:
    commandArgs.extend(["--initial-tumor-lod", str(runArgs.initial_tumor_lod)])
  if runArgs.tumor_lod_to_emit is not None:
    commandArgs.extend(["--tumor-lod-to-emit", str(runArgs.tumor_lod_to_emit)])
  if runArgs.pruning_lod_threshold is not None:
    commandArgs.extend(["--pruning-lod-threshold", str(runArgs.pruning_lod_threshold)])
  if runArgs.active_probability_threshold is not None:
    commandArgs.extend(["--active-probability-threshold", str(runArgs.active_probability_threshold)])
  if runArgs.genotype_germline_sites == True:
    commandArgs.extend(["--genotype-germline-sites"])
  if runArgs.genotype_pon_sites == True:
    commandArgs.extend(["--genotype-pon-sites"])
  if runArgs.mutect_germline_resource != None:
    commandArgs.extend(["--germline-resource", runArgs.mutect_germline_resource])
  if runArgs.mutect_alleles != None:
    commandArgs.extend(["--alleles", runArgs.mutect_alleles])
  if runArgs.force_call_filtered_alleles == True:
    commandArgs.extend(["--force-call-filtered-alleles"])
  if runArgs.filter_reads_too_long == True:
    commandArgs.extend(["--filter-reads-too-long"])
  if runArgs.mutect_f1r2_tar_gz != None:
    commandArgs.extend(["--f1r2-tar-gz", runArgs.mutect_f1r2_tar_gz])

  if runArgs.minimum_mapping_quality != None:
    commandArgs.extend(["--minimum-mapping-quality", str(runArgs.minimum_mapping_quality)])
  if runArgs.min_base_quality_score != None:
    commandArgs.extend(["--min-base-quality-score", str(runArgs.min_base_quality_score)])
  if runArgs.f1r2_median_mq != None:
    commandArgs.extend(["--f1r2-median-mq", str(runArgs.f1r2_median_mq)])
  if runArgs.base_quality_score_threshold != None:
    commandArgs.extend(["--base-quality-score-threshold", str(runArgs.base_quality_score_threshold)])
  if runArgs.normal_lod != None:
    commandArgs.extend(["--normal-lod", str(runArgs.normal_lod)])
  if runArgs.allow_non_unique_kmers_in_ref == True:
    commandArgs.extend(["--allow-non-unique-kmers-in-ref"])
  if runArgs.enable_dynamic_read_disqualification_for_genotyping == True:
      commandArgs.extend(["--enable-dynamic-read-disqualification-for-genotyping"])
  if runArgs.recover_all_dangling_branches == True:
      commandArgs.extend(["--recover-all-dangling-branches"])
  if runArgs.pileup_detection == True:
      commandArgs.extend(["--pileup-detection"])
  if runArgs.mitochondria_mode == True:
      commandArgs.extend(["--mitochondria-mode"])




  WriteVcfCmd(runArgs, "mutectcaller")
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runbqsr(runArgs, installDir):
  commandArgs = [installDir + "/bin/bqsr", runArgs.ref, runArgs.in_bam, str(runArgs.num_gpus), "-o", runArgs.out_recal_file]
  if (runArgs.interval != None) and len(runArgs.interval) > 0:
    for newInterval in runArgs.interval:
      commandArgs.extend(["-L", newInterval])
  if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      commandArgs.extend(["-L", interval_file])
  if runArgs.interval_padding != None:
    commandArgs.extend(["-ip", str(runArgs.interval_padding)])
  if runArgs.verbose:
    commandArgs.extend(["-v"])
  commandArgs.extend(runArgs.knownSites)

  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def rundbsnp(runArgs, installDir):
  commandArgs = [installDir + "/bin/dbsnp", runArgs.in_vcf, "-o", runArgs.out_vcf, "-dbsnp", runArgs.in_dbsnp_file]
  WriteVcfCmd(runArgs, "dbsnp")
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runprepon(runArgs, installDir):
  commandArgs = [installDir + "/bin/prepon", runArgs.in_pon_file]
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runpostpon(runArgs, installDir):
  commandArgs = [installDir + "/bin/postpon", runArgs.in_vcf, "-o", runArgs.out_vcf, "-pon", runArgs.in_pon_file]
  WriteVcfCmd(runArgs, "postpon")
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runapplybqsr(runArgs, installDir):
    commandArgs = [installDir + "/bin/applyBQSR", runArgs.in_bam, runArgs.ref, runArgs.in_recal_file, runArgs.out_bam, str(runArgs.num_gpus), "-n", str(runArgs.num_threads)]
    if (runArgs.interval != None) and len(runArgs.interval) > 0:
        for newInterval in runArgs.interval:
            commandArgs.extend(["-L", newInterval])
    if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
        for interval_file in runArgs.interval_file:
            commandArgs.extend(["-L", interval_file])
    if runArgs.interval_padding != None:
        commandArgs.extend(["-ip", str(runArgs.interval_padding)])
    if runArgs.verbose:
        commandArgs.extend(["-v"])
    WriteCmd(runArgs, "applybqsr")
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runbammetrics(runArgs, installDir):
    commandArgs = [installDir + "/bin/coverage", runArgs.ref, runArgs.bam, str(runArgs.num_threads), "-o", runArgs.out_metrics_file, "-Q", str(runArgs.minimum_base_quality), "-MQ", str(runArgs.minimum_mapping_quality), "-CAP", str(runArgs.coverage_cap)]
    if (runArgs.interval != None) and len(runArgs.interval) > 0:
        for newInterval in runArgs.interval:
            commandArgs.extend(["-L", newInterval])
    if (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
        for interval_file in runArgs.interval_file:
            commandArgs.extend(["-L", interval_file])
    if runArgs.count_unpaired == True:
        commandArgs.extend(["-COUNT_UNPAIRED"])
    if runArgs.verbose:
        commandArgs.extend(["-v"])
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

def runmarkdup(runArgs, installDir):
    WriteCmd(runArgs, "markdup")
    if runArgs.num_zip_threads is None:
      runArgs.num_zip_threads = 10

    if runArgs.num_worker_threads is None:
      runArgs.num_worker_threads = 10

    cmdLine = [installDir + "/bin/premarkdup", runArgs.ref, runArgs.in_bam, "-z", str(runArgs.num_zip_threads), "-n", str(runArgs.num_worker_threads)]
    if runArgs.markdups_single_ended_start_end == True:
      cmdLine.extend(["-mark-single-ended"])
    if runArgs.verbose:
      cmdLine.extend(["-v"])
    AddLogfile(cmdLine, runArgs)
    RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

      #sort
    cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-gb", str(runArgs.mem_limit)]
  
    if runArgs.markdups_assume_sortorder_queryname == True:
      cmdLine.extend(["-mark-query"])
    if runArgs.out_duplicate_metrics != None:
      cmdLine.extend(["-r", runArgs.out_duplicate_metrics])
    if runArgs.optical_duplicate_pixel_distance != None:
      cmdLine.extend(["-d", str(runArgs.optical_duplicate_pixel_distance)])
    if runArgs.markdups_single_ended_start_end == True:
      cmdLine.extend(["-mark-single-ended"])
    if runArgs.ignore_rg_markdups_single_ended == True:
      cmdLine.extend(["-ignore-rg-single-ended"])
    if runArgs.gpusort == True:
      gpu_num = GetNumGPUs()
      cmdLine.extend(["-gpu", str(gpu_num)])
    if runArgs.verbose:
      cmdLine.extend(["-v"])
    AddLogfile(cmdLine, runArgs, True)
    RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

    #postsort
    cmdLine = [installDir + "/bin/postsort", runArgs.ref, "-o", runArgs.out_bam, "-sort_unmapped"]

    cmdLine.extend(["-ft", "4",  "-zt", str(max(1, min(20, GetNumCPUs() - 7))), "-bq", "1", "-gb", str(runArgs.mem_limit)])
    if runArgs.markdups_assume_sortorder_queryname == True:
      cmdLine.extend(["-mark-query"])
    if runArgs.gpuwrite == True:
      gpu_num = GetNumGPUs()#make sure gpu(s) available
      cmdLine.extend(["-gpuwrite"])
    if runArgs.gpuwrite_deflate_algo != None:
      cmdLine.extend(["-nvcomp-deflate-algo", str(runArgs.gpuwrite_deflate_algo)])
    if runArgs.verbose:
      cmdLine.extend(["-v"])

    AddLogfile(cmdLine, runArgs, True)
    RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

def runbamsort(runArgs, installDir, suffix=""):
    WriteCmd(runArgs, "bamsort" + suffix)

    # set default thread counts; heuristic from testing on m5.8xlarge instances
    if runArgs.num_zip_threads is None:
      if str(runArgs.sort_order) == "coordinate":
        runArgs.num_zip_threads = 16
      else:
        runArgs.num_zip_threads = 10
    if runArgs.num_sort_threads is None:
      if str(runArgs.sort_order) == "coordinate":
        runArgs.num_sort_threads = 10
      else:
        runArgs.num_sort_threads = 16

    # bamsort binary
    commandArgs = [installDir + "/bin/bamsort"]
    commandArgs.extend(["--input-file", str(runArgs.in_bam)])
    #always pass out bam file name to decide if handle long cigar
    commandArgs.extend(["--output-file", str(runArgs.out_bam)])
    if runArgs.ref != None:
      commandArgs.extend(["--reference-file", str(runArgs.ref)])
    commandArgs.extend(["--sort-order", str(runArgs.sort_order)])
    if str(runArgs.sort_order) == "queryname":
      # extsort comparator only matters for queryname inside the bamsort binary
      # for coordinate this comes into play in the `sort` binary
      commandArgs.extend(["--extsort-comparator", str(runArgs.sort_compatibility)])
    commandArgs.extend(["--max-rec-in-ram", str(runArgs.max_records_in_ram)])
    commandArgs.extend(["--nzipthreads", str(runArgs.num_zip_threads)])
    commandArgs.extend(["--nsortthreads", str(runArgs.num_sort_threads)])
    if runArgs.verbose:
        commandArgs.extend(["--verbose"])
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
  
    # coordinate sort uses bin sorting so requires `sort` and `postsort`
    if str(runArgs.sort_order) == "coordinate":
      # sort - note that sort *must* use the -standalone option for standalone bamsort
      cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-no-markdup", "-standalone", "-gb", str(runArgs.mem_limit)]
      if str(runArgs.sort_compatibility) == "fgbio":
        cmdLine.extend(["-fgbio"])
      if runArgs.gpusort == True:
        gpu_num = GetNumGPUs()
        cmdLine.extend(["-gpu", str(gpu_num)])
      if runArgs.verbose:
        cmdLine.extend(["-v"])
      AddLogfile(cmdLine, runArgs, True)  # append because this will always be run after `bamsort`
      RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
       
      # postsort
      cmdLine = [installDir + "/bin/postsort", runArgs.ref, "-o", runArgs.out_bam, "-sort_unmapped"]
      cmdLine.extend(["-ft", "4", "-zt", str(max(1, min(20, GetNumCPUs() - 7))), "-bq", "1", "-gb", str(runArgs.mem_limit)])
      
      if runArgs.gpuwrite == True:
        gpu_num = GetNumGPUs()#make sure gpu(s) available
        cmdLine.extend(["-gpuwrite"])
      if runArgs.gpuwrite_deflate_algo != None:
        cmdLine.extend(["-nvcomp-deflate-algo", str(runArgs.gpuwrite_deflate_algo)])
      
      if runArgs.verbose:
        cmdLine.extend(["-v"])
      AddLogfile(cmdLine, runArgs, True)  # append because this will always be run after `sort`
      RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runcollectmultiplemetrics(runArgs, installDir):
  commandArgs = [installDir + "/bin/collectmultiplemetrics", runArgs.ref, runArgs.bam, runArgs.out_qc_metrics_dir]
  if runArgs.gen_all_metrics:
    commandArgs.extend(["--alignment", "--qualityscore", "--insertsize", "--meanqualitybycycle", "--basedistributionbycycle", "--gcbias", "--seqartifact", "--qualityyield"])
  else:
    if runArgs.gen_alignment:
      commandArgs.extend(["--alignment"])
    if runArgs.gen_quality_score:
      commandArgs.extend(["--qualityscore"])
    if runArgs.gen_insert_size:
      commandArgs.extend(["--insertsize"])
    if runArgs.gen_mean_quality_by_cycle:
      commandArgs.extend(["--meanqualitybycycle"])
    if runArgs.gen_base_distribution_by_cycle:
      commandArgs.extend(["--basedistributionbycycle"])
    if runArgs.gen_gc_bias:
      commandArgs.extend(["--gcbias"])
    if runArgs.gen_seq_artifact:
      commandArgs.extend(["--seqartifact"])
    if runArgs.gen_quality_yield != None:
      commandArgs.extend(["--qualityyield"])

  commandArgs.extend(["-n", str(runArgs.num_gpus)])
  bam_threads = 3
  if runArgs.num_gpus >= 4:
    bam_threads = 8
  if runArgs.bam_decompressor_threads != None:
    bam_threads = runArgs.bam_decompressor_threads
  commandArgs.extend(["-b", str(bam_threads)])
  commandArgs.extend(["-g", str(8)])
  if runArgs.verbose:
    commandArgs.extend(["-v"])

  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)
  createqcimages(runArgs.bam, runArgs.out_qc_metrics_dir, installDir, runArgs.gen_all_metrics, runArgs.gen_quality_score, runArgs.gen_insert_size, runArgs.gen_mean_quality_by_cycle, runArgs.gen_base_distribution_by_cycle, runArgs.gen_gc_bias)


def runindexgvcf(runArgs, installDir):
    commandArgs = [installDir + "/bin/indexgvcf", runArgs.input]
    if runArgs.verbose:
        commandArgs.extend(["-v"])
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def rungenotypegvcf(runArgs, installDir):
    commandArgs = [installDir + "/bin/genotypegvcf", runArgs.ref]
    if runArgs.in_gvcf != None:
        commandArgs.extend(["-V", runArgs.in_gvcf])

    commandArgs.extend(["-o", runArgs.out_vcf, "-n", str(runArgs.num_threads)])
    if runArgs.verbose:
        commandArgs.extend(["-v"])
    WriteVcfCmd(runArgs, "genotypegvcf")
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def runrna_fq2bam(runArgs, installDir):
  #
  # In low-memory mode, force using 1 stream.
  #
  streams = runArgs.num_streams_per_gpu
  if (runArgs.low_memory):
    streams = 1
  #
  # The number of threads has to be at least 1.
  # The number of helpers is at most the number of threads minus 1.
  #
  nthreads = runArgs.num_threads
  if nthreads < 1:
    nthreads = 1
  nhelpers = runArgs.enable_gpu_helper_threads
  if nhelpers >= nthreads:
    nhelpers = nthreads - 1
  commandArgs = [installDir + "/bin/star", "--runGPUNum", str(runArgs.num_gpus)]
  commandArgs.extend(["--runStreamsPerGPU", str(streams)])
  commandArgs.extend(["--noMarkDup", str(runArgs.no_markdups)])
  commandArgs.extend(["--runCPUHelpersN", str(nhelpers)])
  commandArgs.extend(["--runThreadN", str(nthreads)])
  commandArgs.extend(["--twopassMode", runArgs.two_pass_mode])
  commandArgs.extend(["--genomeSAindexNbases", str(runArgs.num_sa_bases)])
  commandArgs.extend(["--alignIntronMax", str(runArgs.max_intron_size)])
  commandArgs.extend(["--alignIntronMin", str(runArgs.min_intron_size)])
  commandArgs.extend(["--outFilterMatchNmin", str(runArgs.min_match_filter)])
  commandArgs.extend(["--outFilterMatchNminOverLread", str(runArgs.min_match_filter_normalized)])
  commandArgs.extend(["--outFilterIntronMotifs", runArgs.out_filter_intron_motifs])
  commandArgs.extend(["--outFilterMismatchNmax", str(runArgs.max_out_filter_mismatch)])
  commandArgs.extend(["--outFilterMismatchNoverLmax", str(runArgs.max_out_filter_mismatch_ratio)])
  commandArgs.extend(["--outFilterMultimapNmax", str(runArgs.max_out_filter_multimap)])
  commandArgs.extend(["--outReadsUnmapped", runArgs.out_reads_unmapped])
  commandArgs.extend(["--outSAMunmapped"])
  if runArgs.out_sam_unmapped == "Within_KeepPairs":
    commandArgs.extend(["Within", "KeepPairs"])
  else:
    commandArgs.extend([runArgs.out_sam_unmapped])
  commandArgs.extend(["--outSAMattributes"])
  for attr in runArgs.out_sam_attributes:
    commandArgs.extend([attr])
  commandArgs.extend(["--outSAMstrandField", runArgs.out_sam_strand_field])
  commandArgs.extend(["--outSAMmode", runArgs.out_sam_mode])
  commandArgs.extend(["--outSAMmapqUnique", str(runArgs.out_sam_mapq_unique)])
  if runArgs.read_files_command != None:
    commandArgs.extend(["--readFilesCommand", runArgs.read_files_command])
  commandArgs.extend(["--outFilterScoreMinOverLread", str(runArgs.min_score_filter)])
  commandArgs.extend(["--alignSplicedMateMapLminOverLmate", str(runArgs.min_spliced_mate_length)])
  commandArgs.extend(["--alignSJstitchMismatchNmax"])
  for mismatch in runArgs.max_junction_mismatches:
    commandArgs.extend([str(mismatch)])
  commandArgs.extend(["--limitOutSAMoneReadBytes", str(runArgs.max_out_read_size)])
  commandArgs.extend(["--alignTranscriptsPerReadNmax", str(runArgs.max_alignments_per_read)])
  commandArgs.extend(["--scoreGap", str(runArgs.score_gap)])
  commandArgs.extend(["--seedSearchStartLmax", str(runArgs.seed_search_start)])
  commandArgs.extend(["--limitBAMsortRAM", str(runArgs.max_bam_sort_memory)])
  commandArgs.extend(["--alignEndsType", runArgs.align_ends_type])
  commandArgs.extend(["--alignInsertionFlush", runArgs.align_insertion_flush])
  commandArgs.extend(["--alignMatesGapMax", str(runArgs.max_align_mates_gap)])
  commandArgs.extend(["--alignSplicedMateMapLmin", str(runArgs.min_align_spliced_mate_map)])
  commandArgs.extend(["--limitOutSJcollapsed", str(runArgs.max_collapsed_junctions)])
  commandArgs.extend(["--alignSJoverhangMin", str(runArgs.min_align_sj_overhang)])
  commandArgs.extend(["--alignSJDBoverhangMin", str(runArgs.min_align_sjdb_overhang)])
  commandArgs.extend(["--sjdbOverhang", str(runArgs.sjdb_overhang)])
  commandArgs.extend(["--chimJunctionOverhangMin", str(runArgs.min_chim_overhang)])
  commandArgs.extend(["--chimSegmentMin", str(runArgs.min_chim_segment)])
  commandArgs.extend(["--chimMultimapNmax", str(runArgs.max_chim_multimap)])
  commandArgs.extend(["--chimMultimapScoreRange", str(runArgs.chim_multimap_score_range)])
  commandArgs.extend(["--chimScoreJunctionNonGTAG", str(runArgs.chim_score_non_gtag)])
  commandArgs.extend(["--chimNonchimScoreDropMin", str(runArgs.min_non_chim_score_drop)])
  commandArgs.extend(["--chimOutJunctionFormat", str(runArgs.out_chim_format)])

  if runArgs.out_chim_type != None:
    commandArgs.extend(["--chimOutType"])
    for out_chim_type_single in runArgs.out_chim_type:
      if out_chim_type_single == "WithinBAM_HardClip":
        commandArgs.extend(["WithinBAM", "HardClip"])
      elif out_chim_type_single == "WithinBAM_SoftClip":
        commandArgs.extend(["WithinBAM", "SoftClip"])
      else:
        commandArgs.extend([out_chim_type_single])

  # Add SOLO parameters if specified
  if hasattr(runArgs, 'soloType') and runArgs.soloType != "None":
    commandArgs.extend(["--soloType", runArgs.soloType])
    
    if hasattr(runArgs, 'soloBarcodeReadLength') and runArgs.soloBarcodeReadLength > -1:
      commandArgs.extend(["--soloBarcodeReadLength", str(runArgs.soloBarcodeReadLength)])
    
    if hasattr(runArgs, 'soloCBwhitelist') and runArgs.soloCBwhitelist is not None:
      commandArgs.extend(["--soloCBwhitelist", runArgs.soloCBwhitelist])
    
    if hasattr(runArgs, 'soloCBstart'):
      commandArgs.extend(["--soloCBstart", str(runArgs.soloCBstart)])
    
    if hasattr(runArgs, 'soloCBlen'):
      commandArgs.extend(["--soloCBlen", str(runArgs.soloCBlen)])
    
    if hasattr(runArgs, 'soloUMIstart'):
      commandArgs.extend(["--soloUMIstart", str(runArgs.soloUMIstart)])
    
    if hasattr(runArgs, 'soloUMIlen'):
      commandArgs.extend(["--soloUMIlen", str(runArgs.soloUMIlen)])
    
    if hasattr(runArgs, 'soloFeatures') and runArgs.soloFeatures is not None:
      commandArgs.extend(["--soloFeatures"])
      # soloFeatures can be a single string or a list
      if isinstance(runArgs.soloFeatures, list):
        for feature in runArgs.soloFeatures:
          commandArgs.extend([feature])
      else:
        commandArgs.extend([runArgs.soloFeatures])
    
    if hasattr(runArgs, 'soloStrand'):
      commandArgs.extend(["--soloStrand", runArgs.soloStrand])

  # Process quantMode parameter (validation done in pbargs_check.py)
  if hasattr(runArgs, 'quantMode') and runArgs.quantMode is not None:
    commandArgs.extend(["--quantMode"])
    
    for mode in runArgs.quantMode:
      # Split by comma and strip whitespace
      for subMode in mode.split(','):
        subMode = subMode.strip()
        if subMode:  # Only process non-empty values
          commandArgs.extend([subMode])

  commandArgs.extend(["--outFileNamePrefix", runArgs.output_dir + "/" + runArgs.out_prefix])
  commandArgs.extend(["--genomeDir", runArgs.genome_lib_dir])

  #
  # Read FastQ files
  #
  fq1 = []
  fq2 = []
  RGs = []
  if runArgs.in_fq != None:
    for inputFQ in runArgs.in_fq:
      fq1.append(inputFQ[0])
      fq2.append(inputFQ[1])
      line =[]
      for attr in inputFQ[2][5:].split("\\t"):
        line.append(attr)
      RGs.append(line)
  elif runArgs.in_se_fq != None:
    for inputFQ in runArgs.in_se_fq:
      fq1.append(inputFQ[0])
      line = []
      for attr in inputFQ[1][5:].split("\\t"):
        line.append(attr)
      RGs.append(line);
  elif runArgs.in_fq_list != None:
    for inputFQ in runArgs.fastqGroups:
      fq1.append(inputFQ[0])
      fq2.append(inputFQ[1])
      line = []
      for attr in inputFQ[2][5:].split("\\t"):
        line.append(attr)
      RGs.append(line)
  elif runArgs.in_se_fq_list != None:
    for inputFQ in runArgs.fastqGroups:
      fq1.append(inputFQ[0])
      line = []
      for attr in inputFQ[1][5:].split("\\t"):
        line.append(attr)
      RGs.append(line)

  # format the arguments in a way that STAR likes
  if len(fq1) == 1:   # map a single (or a pair of) fastq file
    if len(fq2) == 0:
      commandArgs.extend(["--readFilesIn", fq1[0]])
    else:
      commandArgs.extend(["--readFilesIn", fq1[0], fq2[0]])
    commandArgs.extend(["--outSAMattrRGline"])
    for attr in RGs[0]:
      commandArgs.extend([attr])
  else:               # map a batch of fastq files
    fq1Line = ""
    for fq in fq1:
      fq1Line += fq + ","
    fq2Line = ""
    for fq in fq2:
      fq2Line += fq + ","
    if not fq2Line: # fq2Line empty
      commandArgs.extend(["--readFilesIn", fq1Line[:-1]])
    else:
      commandArgs.extend(["--readFilesIn", fq1Line[:-1], fq2Line[:-1]])
    commandArgs.extend(["--outSAMattrRGline"])
    for attr in RGs[0]:
      commandArgs.extend([attr])
    for attrLine in RGs[1:]:
      commandArgs.extend([","])
      for attr in attrLine:
        commandArgs.extend([attr])
  #
  # Finish reading FastQ files
  #

  commandArgs.extend(["--outSAMtype", "BAM", "SortedByCoordinate"])
  commandArgs.extend(["--readNameSeparator"])
  for separator in runArgs.read_name_separator:
    commandArgs.extend([separator])
  AddLogfile(commandArgs, runArgs)
  RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  #sort
  cmdLine = [installDir + "/bin/sort", "-sort_unmapped", "-ft", "10", "-gb", str(runArgs.memory_limit)]
  if runArgs.gpusort != None:    
    cmdLine.extend(["-gpu", str(runArgs.num_gpus)])    
  if runArgs.no_markdups == True:
    cmdLine.extend(["-no-markdup"])
  if runArgs.markdups_assume_sortorder_queryname == True:
    cmdLine.extend(["-mark-query"])
  if runArgs.out_duplicate_metrics != None:
    cmdLine.extend(["-r", runArgs.out_duplicate_metrics])
  if runArgs.optical_duplicate_pixel_distance != None:
    cmdLine.extend(["-d", str(runArgs.optical_duplicate_pixel_distance)])
  if runArgs.verbose:
    cmdLine.extend(["-v"])
  AddLogfile(cmdLine, runArgs, True)
  RunBinary(cmdLine, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)

  #postsort
  run_postsort(runArgs, installDir, False, isfq2bam_meth=False)


def runstarfusion(runArgs, installDir):
    commandArgs = [installDir + "/bin/starfusion", runArgs.chimeric_junction, runArgs.genome_lib_dir, runArgs.output_dir + "/" + runArgs.out_prefix, str(max(runArgs.num_threads, 1))]
    AddLogfile(commandArgs, runArgs)
    RunBinary(commandArgs, installDir, petaGenePath=runArgs.with_petagene_dir, printCmd=runArgs.x3)


def run_pb_main():
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  argsObj = pbargs.getArgs()
  pbargs_check.pbargs_check(argsObj)
  if argsObj.command == "version":
    print("pbrun version: " + pbversion.versionNumber)
    pbExit(0)

  runArgs = argsObj.runArgs # runArgs is a PBRun object (parsed arguments)
  if not runArgs.dev_mode:
    installDir = os.path.join(file_directory, "binaries")
  else:
    installDir = os.path.realpath(os.path.join(file_directory, "..", "..", "binaries"))
  os.chdir(GetFullDirPath(runArgs.tmp_dir))
  if argsObj.command == "fq2bam":
    runfq2bam(runArgs, installDir)
  elif argsObj.command == "fq2bam_meth":
    runfq2bam_meth(runArgs, installDir)
  elif argsObj.command == "bam2fq":
    runbam2fq(runArgs, installDir)
  elif argsObj.command == "haplotypecaller":
    runhaplotypecaller(runArgs, installDir)
  elif argsObj.command == "bqsr":
    runbqsr(runArgs, installDir)
  elif argsObj.command == "applybqsr":
    runapplybqsr(runArgs, installDir)
  elif argsObj.command == "deepvariant":
    rundeepvariant(runArgs, installDir)
  elif argsObj.command == "deepsomatic":
    rundeepsomatic(runArgs, installDir)
  elif argsObj.command == "bammetrics":
    runbammetrics(runArgs, installDir)
  elif argsObj.command == "collectmultiplemetrics":
    runcollectmultiplemetrics(runArgs, installDir)
  elif argsObj.command == "minimap2":
    runminimap2(runArgs, installDir)
  elif argsObj.command == "mutectcaller":
    runmutectcaller(runArgs, installDir)
  elif argsObj.command == "indexgvcf":
    runindexgvcf(runArgs, installDir)
  elif argsObj.command == "genotypegvcf":
    rungenotypegvcf(runArgs, installDir)
  elif argsObj.command == "dbsnp":
    rundbsnp(runArgs, installDir)
  elif argsObj.command == "prepon":
    runprepon(runArgs, installDir)
  elif argsObj.command == "postpon":
    runpostpon(runArgs, installDir)
  elif argsObj.command == "rna_fq2bam":
    runrna_fq2bam(runArgs, installDir)
  elif argsObj.command == "starfusion":
    runstarfusion(runArgs, installDir)
  elif argsObj.command == "bamsort":
    runbamsort(runArgs, installDir)
  elif argsObj.command == "markdup":
    runmarkdup(runArgs, installDir)
  elif argsObj.command == "giraffe":
    rungiraffe(runArgs, installDir)
  elif argsObj.command == "pangenome_aware_deepvariant":
    runpangenome_aware_deepvariant(runArgs, installDir)

  return 0

if __name__ == '__main__':
    run_pb_main()
