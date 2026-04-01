#!/usr/bin/env python3

import os
import os.path
import sys
import subprocess
from pbutils import OptMesg, OptError, check_fastq_files, check_fastq_list, check_fastq_list_se_giraffe, check_fastq_list_pe_giraffe, check_se_fastq_input_giraffe, check_pe_fastq_input_giraffe, check_se_fastq_files, check_fastq_list_se_bwalib, check_fastq_list_pe_bwalib, check_se_bam, check_se_fastq_files_minimap2, gen_rg_from_bam_input, check_and_add_bwameth_option, find_bwa_opt_matches, IsFileStreamReadable, check_fastq_list_pe_rna_fq2bam, check_fastq_list_se_rna_fq2bam, GetDevicesAvailableMemory, GetDefaultMemoryLimit
import pbutils
import typing


def GetInFqFiles(filename):
  with open(filename, "rt") as f:
    lines = f.readlines()
  lines = map(lambda x: x.rstrip("\n\r"), lines)
  result = []
  for line in lines:
    result.append(line.split())
  return result


def check_arg_compatibility(runArgs):
  OptMesg("Checking argument compatibility")

  if runArgs.num_gpus == 0:
    OptError("--num-gpus cannot be set to 0")

  if os.path.isdir(runArgs.tmp_dir) == False:
    OptError("Temporary files directory " + runArgs.tmp_dir + " not found. Exiting...")
  elif os.access(runArgs.tmp_dir, os.W_OK) == False:
    OptError("Temporary files directory " + runArgs.tmp_dir + " does not have write permission. Exiting...")

def GetDeviceModefq2bam(memMiB: int, runArgs: typing.Any):
  """
  Modifies runArgs.low_memory and runArgs.bwa_nstreams based on the total memory of the smallest GPU
  """
  MIN_FOR_1_STREAM = 16_000
  MIN_FOR_2_STREAMS = 22_750
  MIN_FOR_3_STREAMS = 31_000
  MIN_FOR_4_STREAMS = 39_750
  if memMiB < MIN_FOR_1_STREAM:
    runArgs.low_memory = True
    runArgs.bwa_nstreams = 1
  elif MIN_FOR_1_STREAM <= memMiB < MIN_FOR_2_STREAMS:
    runArgs.bwa_nstreams = 1
  elif MIN_FOR_2_STREAMS <= memMiB < MIN_FOR_3_STREAMS:
    runArgs.bwa_nstreams = 2
  elif MIN_FOR_3_STREAMS <= memMiB < MIN_FOR_4_STREAMS:
    runArgs.bwa_nstreams = 3
  else:
    runArgs.bwa_nstreams = 4


def GetDeviceModefq2bam_meth(memMiB: int, runArgs: typing.Any):
  """
  Modifies runArgs.low_memory and runArgs.bwa_nstreams based on the total memory of the smallest GPU
  """
  MIN_FOR_1_STREAM = 21_000
  MIN_FOR_2_STREAMS = 29_000
  MIN_FOR_3_STREAMS = 37_000
  MIN_FOR_4_STREAMS = 45_000
  if memMiB < MIN_FOR_1_STREAM:
    runArgs.low_memory = True
    runArgs.bwa_nstreams = 1
  elif MIN_FOR_1_STREAM <= memMiB < MIN_FOR_2_STREAMS:
    runArgs.bwa_nstreams = 1
  elif MIN_FOR_2_STREAMS <= memMiB < MIN_FOR_3_STREAMS:
    runArgs.bwa_nstreams = 2
  elif MIN_FOR_3_STREAMS <= memMiB < MIN_FOR_4_STREAMS:
    runArgs.bwa_nstreams = 3
  else:
    runArgs.bwa_nstreams = 4


def GetDeviceModeSTAR(gpuMemMiB: int, cpuMemGB: int, numGpus: int, user_threads: typing.Optional[int] = None) -> typing.Tuple[int, int]:
  """
  Determines optimal STAR num_streams_per_gpu and num_threads based on GPU memory, CPU memory, and number of GPUs.
  Returns a tuple of (streams, threads).

  This function is only called when --num-streams-per-gpu and/or --num-threads are set to "auto".
  Users can override these defaults by explicitly passing integer values.

  Args:
    gpuMemMiB: Minimum GPU memory in MiB across all GPUs
    cpuMemGB: Total system CPU memory in GB
    numGpus: Number of GPUs to use
    user_threads: If user specified threads, pass here for accurate memory estimation

  Configuration:
    - Threads: 4 (default for all configurations)
    - Streams: Based on GPU memory
      - T4 (~16GB): 1 stream
      - L4 (~24GB): 2 streams
      - A100 40GB/80GB, H100 80GB (>=40GB): 3 streams
    - If estimated CPU memory exceeds 85% of available, reduce streams to fit

  CPU Memory Requirements (based on regression testing):
    - Minimum: 192GB recommended
    - Streams reduced if estimated peak memory exceeds 85% of available CPU RAM
  """
  # GPU memory thresholds (in MiB)
  GPU_MEM_T4_CLASS = 15_000      # T4 has 15360 MiB (~15GB)
  GPU_MEM_L4_CLASS = 23_000      # L4 has ~23GB
  GPU_MEM_A100_CLASS = 40_000    # A100 40GB/80GB, H100 80GB

  # Default threads, but use user-specified value if provided for memory estimation
  threads = 4
  threads_for_mem_calc = user_threads if user_threads is not None else threads

  # Determine streams based on GPU memory
  if gpuMemMiB < GPU_MEM_T4_CLASS:
    # Very low GPU memory
    streams = 1
  elif gpuMemMiB < GPU_MEM_L4_CLASS:
    # T4-class GPU (16GB): 1 stream
    streams = 1
  elif gpuMemMiB < GPU_MEM_A100_CLASS:
    # L4-class GPU (~24GB): 2 streams
    streams = 2
  else:
    # A100 40GB/80GB, H100 80GB (>=40GB): 3 streams
    streams = 3

  # Adjust streams based on CPU memory constraints (use actual thread count for estimation)
  estimated_peak_mem_gb = estimate_star_peak_memory(numGpus, streams, threads_for_mem_calc)
  max_allowed_mem_gb = cpuMemGB * 0.85  # Leave 15% headroom

  if estimated_peak_mem_gb > max_allowed_mem_gb:
    OptMesg(f"Adjusting STAR streams due to CPU memory constraints ({cpuMemGB}GB available)")
    # Reduce streams until memory fits or we reach minimum (1 stream)
    while estimated_peak_mem_gb > max_allowed_mem_gb and streams > 1:
      streams -= 1
      estimated_peak_mem_gb = estimate_star_peak_memory(numGpus, streams, threads_for_mem_calc)

  return (streams, threads)


def estimate_star_peak_memory(numGpus: int, streams: int, threads: int) -> float:
  """
  Estimate peak memory usage for STAR based on configuration.
  Based on regression test data from Jan 23-24, 2026.

  Actual measured data points (1 stream, 4 threads):
    - 2 GPUs: ~85 GB
    - 4 GPUs: ~138 GB

  Formula: base_mem + (total_streams * per_stream_mem)
    - base_mem = 32 GB
    - per_stream_mem = 27 GB (for 4 threads)
  """
  base_mem = 32.0  # Base memory overhead

  # Per-stream memory based on thread count
  if threads <= 2:
    per_stream_mem = 25.0
  elif threads <= 4:
    per_stream_mem = 27.0
  else:  # 8+ threads
    per_stream_mem = 35.0

  # Total streams across all GPUs
  total_streams = numGpus * streams

  # Total estimate
  estimated = base_mem + (total_streams * per_stream_mem)

  return estimated


def GetPostsortMode(memMiB: int, runArgs: typing.Any):
  """
  Adds new attribute to runArgs (low_memory_postsort) based on the total memory of the smallest GPU
  and the output mode
  """
  # if we are using bqsr, we need to add the memory needed for bqsr to the memory needed for postsort
  BQSR_MEM_NEEDED = 0  # default is no bqsr
  if (hasattr(runArgs, "standalone_bqsr") == False) or (runArgs.standalone_bqsr == None) or (runArgs.standalone_bqsr == False):
    if hasattr(runArgs, "knownSites") and (runArgs.knownSites != None) and (len(runArgs.knownSites) > 0):
      BQSR_MEM_NEEDED = 3500  #MiB
  if runArgs.low_memory == True:
    # already accomplished
    return
  # give an initial value to low_memory_postsort
  runArgs.low_memory_postsort = False
  if runArgs.gpuwrite != None and runArgs.out_bam.endswith(".bam"):
    # default nvcompDeflateAlgo in postsort binary is 1 so for `None` that is equivalent to setting `1`
    if (runArgs.gpuwrite_deflate_algo is None or runArgs.gpuwrite_deflate_algo == 1) and memMiB < (22_000 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True
    if runArgs.gpuwrite_deflate_algo != None and runArgs.gpuwrite_deflate_algo == 2 and memMiB < (27_000 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True
    if runArgs.gpuwrite_deflate_algo != None and runArgs.gpuwrite_deflate_algo == 4 and memMiB < (34_000 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True
  elif runArgs.gpuwrite != None and runArgs.out_bam.endswith(".cram"):
    # default nvcompDeflateAlgo in postsort binary is 1 so for `None` that is equivalent to setting `1`
    if (runArgs.gpuwrite_deflate_algo is None or runArgs.gpuwrite_deflate_algo == 1) and memMiB < (17_000 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True
    if runArgs.gpuwrite_deflate_algo != None and runArgs.gpuwrite_deflate_algo == 2 and memMiB < (17_000 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True
    if runArgs.gpuwrite_deflate_algo != None and runArgs.gpuwrite_deflate_algo == 4 and memMiB < (20_500 + BQSR_MEM_NEEDED):
      runArgs.low_memory_postsort = True


def get_auto_msg(toolname: str) -> str:
  return (
      "Auto mode: Setting --bwa-nstreams and device memory parameters automatically "
      "based on available GPU memory. These settings are optimized for the "
      "GRCh38 reference genome and may need manual adjustment for other "
      "references or optimal performance. For manual configuration guidance, "
      f"see the {toolname} documentation."
  )


def GetDeviceModeGiraffe(memMiB: int, runArgs: typing.Any, is_paired_end: bool):
  """
  Sets giraffe alignment options from GPU memory. Unified for SE and PE.
  SE (is_paired_end=False): sets streams, dozeu_gpu, minimizers_gpu.
  PE (is_paired_end=True): only extension on GPU; sets streams; minimizers/dozeu set to False.
  """
  # Memory thresholds (same bands for SE and PE; optionally use different for PE)
  MIN_SUPPORTED_DEVICE_MEMORY = 15_000
  MIN_FOR_1_STREAM = 22_000 # minimum for running with 1 stream, larger batch size, and dozeu on GPU
  MIN_FOR_2_STREAMS = 32_000
  MIN_FOR_3_STREAMS = 40_000
  MIN_FOR_4_STREAMS = 80_000
  MIN_FOR_5_STREAMS = 120_000
  if memMiB < MIN_SUPPORTED_DEVICE_MEMORY:
    runArgs.low_memory = True
    runArgs.nstreams = 1
  elif MIN_SUPPORTED_DEVICE_MEMORY <= memMiB < MIN_FOR_1_STREAM:
    runArgs.low_memory = True
    runArgs.nstreams = 1
  elif MIN_FOR_1_STREAM <= memMiB < MIN_FOR_2_STREAMS:
    runArgs.nstreams = 1
    runArgs.batch_size = 8000
    runArgs.minimizers_gpu = False
    runArgs.dozeu_gpu = True
  elif MIN_FOR_2_STREAMS <= memMiB < MIN_FOR_3_STREAMS:
    runArgs.nstreams = 2
    runArgs.batch_size = 10000
    runArgs.minimizers_gpu = False
    runArgs.dozeu_gpu = True
  elif MIN_FOR_3_STREAMS <= memMiB < MIN_FOR_4_STREAMS:
    runArgs.nstreams = 3
    runArgs.batch_size = 10000
    runArgs.minimizers_gpu = False
    runArgs.dozeu_gpu = True
  elif MIN_FOR_4_STREAMS <= memMiB < MIN_FOR_5_STREAMS:
    runArgs.nstreams = 4
    runArgs.batch_size = 10000
    runArgs.minimizers_gpu = True
    runArgs.dozeu_gpu = True
  else:
    runArgs.nstreams = 5
    runArgs.batch_size = 10000
    runArgs.minimizers_gpu = True
    runArgs.dozeu_gpu = True
  if is_paired_end:
    # PE: set all SE specific options to False, retain number of streams and batch size
    runArgs.minimizers_gpu = False
    runArgs.dozeu_gpu = False


def ApplyHostMemoryThresholdsGiraffe(hostMemGB: float, runArgs: typing.Any, is_paired_end: bool):
  """
  Applies host memory thresholds for giraffe automode.
  """
  # Memory thresholds for the default batch size and queue depth
  MIN_HOST_MEM_GB_FOR_DEFAULT_BATCH_SIZE = 80
  MIN_HOST_MEM_GB_FOR_DEFAULT_QUEUE_DEPTH = 80
  REDUCED_BATCH_SIZE = 5000
  REDUCED_WORK_QUEUE_CAPACITY = 10
  # Thresholds for the minimizers on GPU
  MEM_HOST_HEADROOM_GB= 64
  MEM_HOST_INDEX_GB = 60
  MEM_HOST_MINIMIZER_GPU_GB = 20
  MEM_HOST_PER_STREAM_GB = 4
  if getattr(runArgs, "nstreams", "auto") == "auto":
    # should have already been set to an integer value by now
    runArgs.nstreams = 1
  elif type(getattr(runArgs, "nstreams", 1)) != int:
    OptError(f"Invalid --nstreams value: {getattr(runArgs, 'nstreams', 1)}. Must be a positive integer or 'auto'.")
  total_streams = int(getattr(runArgs, "num_gpus", 1)) * int(getattr(runArgs, "nstreams", 1))
  min_host_gb_minimizers_gpu = MEM_HOST_INDEX_GB + MEM_HOST_MINIMIZER_GPU_GB + (total_streams * MEM_HOST_PER_STREAM_GB) + MEM_HOST_HEADROOM_GB
  # Apply thresholds
  if hostMemGB < min_host_gb_minimizers_gpu:
    runArgs.minimizers_gpu = False
  if hostMemGB < MIN_HOST_MEM_GB_FOR_DEFAULT_BATCH_SIZE:
    runArgs.batch_size = REDUCED_BATCH_SIZE
  if hostMemGB < MIN_HOST_MEM_GB_FOR_DEFAULT_QUEUE_DEPTH:
    runArgs.work_queue_capacity = REDUCED_WORK_QUEUE_CAPACITY


def check_fq2bam(runArgs, check_auto_streams: bool):
  check_arg_compatibility(runArgs)

  # if running fq2bammeth then we don't want to do this on the first try
  if check_auto_streams and runArgs.bwa_nstreams == "auto":
    if runArgs.low_memory != True:
      # only print auto-mode message if low_memory is not set or else it can be confusing for the user
      OptMesg(get_auto_msg("fq2bam"))
    memories = GetDevicesAvailableMemory()
    min_memory = min(memories)
    GetDeviceModefq2bam(min_memory, runArgs)
    GetPostsortMode(min_memory, runArgs)
  elif check_auto_streams:
    try:
      runArgs.bwa_nstreams = int(runArgs.bwa_nstreams)
      if runArgs.bwa_nstreams < 1:
        OptError(f"--bwa-nstreams must be greater than 0, user provided {runArgs.bwa_nstreams}")
    except:
      OptError(f"Invalid --bwa-nstreams value: {runArgs.bwa_nstreams}. Must be a positive integer or 'auto'.")

  if runArgs.bwa_primary_cpus == "auto":
    runArgs.bwa_primary_cpus = runArgs.num_gpus
  else:
    try:
      runArgs.bwa_primary_cpus = int(runArgs.bwa_primary_cpus)
      if runArgs.bwa_primary_cpus < 1:
        OptError(f"--bwa-primary-cpus must be greater than 0, user provided {runArgs.bwa_primary_cpus}")
    except:
      OptError(f"Invalid --bwa-primary-cpus value: {runArgs.bwa_primary_cpus}. Must be a positive integer or 'auto'.")

  if hasattr(runArgs, "in_fq_file"):
    for fqFileList in runArgs.in_fq_file:
      for fqFile in GetInFqFiles(fqFileList[0]):
        runArgs.in_fq.append(fqFile)

  if runArgs.use_gds == True:
    if runArgs.gpuwrite == None:
      OptError("The option --use-gds must be used concurrently with --gpuwrite.")
    try:
      gdsoutput = subprocess.run(["/usr/local/cuda/gds/tools/gdscheck", "-p"], check=True, capture_output=True)
      # check that at least one GDS driver configuration is supported
      hasOneGDSSupport = ": Supported" in gdsoutput.stdout.decode()
      if not hasOneGDSSupport:
        OptError("With --use-gds, at least one driver configuration must be supported. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.")
    except:
      # if this exception happens then there was probably something wrong with the docker image
      OptError("With --use-gds, unable to run `gdscheck`. Please ensure that GDS is available.")

  if runArgs.gpuwrite_deflate_algo != None:
    if runArgs.gpuwrite == None:
      OptError("Using `--gpuwrite-deflate-algo #` only has an effect when --gpuwrite is used.")
    if runArgs.gpuwrite_deflate_algo not in (1, 2, 4):
      extramsg = ""
      if runArgs.gpuwrite_deflate_algo in (0, 3):
        extramsg = " Note: as of >= version 4.4 options 0 and 3 have been replaced, see documentation."
      OptError("With --gpuwrite-deflate-algo, only options 1, 2, and 4 are valid." + extramsg)

  if (runArgs.knownSites != None) and (runArgs.out_recal_file == None):
    OptError("With --knownSites option, recalibration file will be generated. Please specify output recalibration file.")

  if (runArgs.knownSites == None) and (runArgs.out_recal_file != None):
    OptError("Without --knownSites option, recalibration file will not be generated. Please remove output recalibration file or add --knownSites file")

  if (runArgs.no_markdups == True):
    if (runArgs.out_duplicate_metrics != None):
      OptError("No metrics file will be generated with --no-markdups. Please remove --out-duplicate-metrics or --no-markdups")
    if runArgs.markdups_assume_sortorder_queryname == True:
      OptError("Cannot use --markdups-assume-sortorder-queryname with --no-markdups")
    if runArgs.markdups_single_ended_start_end == True:
      OptError("Cannot use --markdups-single-ended-start-end with --no-markdups")

  if (runArgs.ignore_rg_markdups_single_ended == True) and (runArgs.markdups_single_ended_start_end != True):
   OptError("Cannot use --ignore-rg-markdups-single-ended without --markdups-single-ended-start-end")
  
  if (runArgs.out_duplicate_metrics == None):
    if (runArgs.optical_duplicate_pixel_distance != None):
      OptMesg("No --out-duplicate_metrics specified, --optical_duplicate_pixel_distance will be ignored")

  # check if pair ended alignment and if -K was specified
  opt_matches = find_bwa_opt_matches(runArgs.bwa_options, "-K")
  isPe = (runArgs.in_fq != None) or (runArgs.in_fq_list != None)  
  if isPe and len(opt_matches) == 0:
    # -K not specified
    OptMesg("Set --bwa-options=\"-K #\" to produce compatible pair-ended results with previous versions of fq2bam or BWA MEM.")

  input_method = int(runArgs.in_fq != None) + int(runArgs.in_se_fq != None) + int(runArgs.in_fq_list != None) + int(runArgs.in_se_fq_list != None) + (int(hasattr(runArgs, 'in_se_bam') and runArgs.in_se_bam != None))
  if (input_method == 0) or (input_method > 1):
    if not hasattr(runArgs, 'in_se_bam'):
      OptError("Please specifiy one input from --in-fq, --in-fq-list, --in-se-fq, --in-se-fq-list, or --in-se-bam") 
    else:
      OptError("Please specifiy one input from --in-fq, --in-fq-list, --in-se-fq, or --in-se-fq-list") 
  
  if runArgs.in_fq != None:
    check_fastq_files(runArgs.in_fq, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_se_fq != None:
    check_se_fastq_files(runArgs.in_se_fq, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_fq_list != None:
    runArgs.pe_fq_list = check_fastq_list_pe_bwalib(runArgs.in_fq_list, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_se_fq_list != None:
    runArgs.se_fq_list = check_fastq_list_se_bwalib(runArgs.in_se_fq_list, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)  

def check_fq2bam_meth(runArgs):
  '''
  Check fq2bam_meth specific options
  '''
  if runArgs.bwa_nstreams == "auto":
    if runArgs.low_memory != True:
      # only print auto-mode message if low_memory is not set or else it can be confusing for the user
      OptMesg(get_auto_msg("fq2bam_meth"))
    memories = GetDevicesAvailableMemory()
    min_memory = min(memories)
    GetDeviceModefq2bam_meth(min_memory, runArgs)
    GetPostsortMode(min_memory, runArgs)
  else:
    try:
      runArgs.bwa_nstreams = int(runArgs.bwa_nstreams)
      if runArgs.bwa_nstreams < 1:
        OptError(f"--bwa-nstreams must be greater than 0, user provided {runArgs.bwa_nstreams}")
    except:
      OptError(f"Invalid --bwa-nstreams value: {runArgs.bwa_nstreams}. Must be a positive integer or 'auto'.")
  # check bwa-options to see if they conflict
  # default bwa-meth options: -T 40 -B 2 -L 10 -CM -U 100
  runArgs.bwa_options = check_and_add_bwameth_option(runArgs.bwa_options, "-T", 40)
  runArgs.bwa_options = check_and_add_bwameth_option(runArgs.bwa_options, "-B", 2)
  runArgs.bwa_options = check_and_add_bwameth_option(runArgs.bwa_options, "-L", 10)
  if runArgs.in_se_fq == None:
    # then running in pair ended mode!
    runArgs.bwa_options = check_and_add_bwameth_option(runArgs.bwa_options, "-U", 100)
  # check that only r or f are passed
  if runArgs.set_as_failed is not None:
    if runArgs.set_as_failed != "r" and runArgs.set_as_failed != "f":
      OptError("Valid options for --set-as-failed are the one character strings 'f' or 'r'")

def check_haplotypecaller(runArgs, initial_pipeline_check=False):
  if runArgs.run_partition == True:
    gpu_num_per_partition = 2
    if runArgs.gpu_num_per_partition != None:
      gpu_num_per_partition = runArgs.gpu_num_per_partition
      if runArgs.gpu_num_per_partition < 1:
        OptError("--gpu-num-per-partition cannot be less than 1")

    if runArgs.num_gpus % gpu_num_per_partition != 0:
      OptError("Cannot run partition with " + str(runArgs.num_gpus) + " gpus, make gpu number mulitple of " + str(gpu_num_per_partition))
    if (hasattr(runArgs, "out_variants") and  runArgs.out_variants.endswith(".gz")):
      OptError("--run-partition cannot work with .gz output")
    if runArgs.read_from_tmp_dir == True and runArgs.gvcf == True:
      OptError("Reading from tmp files cannot work with gvcf output in partition mode")
    if runArgs.htvc_bam_output != None and runArgs.read_from_tmp_dir == True:
      OptError("--htvc-bam-output, --run-partition and --read-from-tmp-dir cannot be passed together")

  if (hasattr(runArgs, "interval") and (runArgs.interval != None) and len(runArgs.interval) > 0) or (hasattr(runArgs, "interval_file") and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0):
    if hasattr(runArgs, "no_alt_contigs") and runArgs.no_alt_contigs == True:
      OptError("--interval and --no-alt-contigs cannot be passed together")
    if runArgs.run_partition == True:
      OptError("--run-partition cannot work with intervals")
    if runArgs.read_from_tmp_dir == True:
      OptError("--read-from-tmp-dir cannot work with intervals")

  # Check for exclude intervals with partition mode
  if hasattr(runArgs, "exclude_intervals") and runArgs.exclude_intervals != None and len(runArgs.exclude_intervals) > 0:
    if runArgs.run_partition == True:
      OptError("--run-partition cannot work with --exclude-intervals (-XL).")

  if runArgs.read_from_tmp_dir == True:
    if hasattr(runArgs, "no_alt_contigs") and runArgs.no_alt_contigs == True:
      OptError("--read-from-tmp-dir cannot work with --no-alt-contigs")
    if hasattr(runArgs, "knownSites") and runArgs.knownSites != None:
      OptError("--read-from-tmp-dir cannot work with bqsr")


  if runArgs.ploidy > 2:
    OptError("Currently only ploidy 1 or 2 is supported")

  if runArgs.max_alternate_alleles != None and runArgs.max_alternate_alleles <= 0:
    OptError("--max-alternate-alleles must be greater than 0")

  if runArgs.disable_read_filter != None:
    supported_filters = ["MappingQualityAvailableReadFilter", "MappingQualityReadFilter", "NotSecondaryAlignmentReadFilter", "WellformedReadFilter"]
    for disabled_filter in runArgs.disable_read_filter:
      if disabled_filter not in supported_filters:
        OptError("Unsupported --disable-read-filter value \"%s\"" %(disabled_filter))

  if runArgs.annotation_group != None:
    supported_groups = ["StandardAnnotation", "StandardHCAnnotation", "AS_StandardAnnotation"]
    for annotation_group in runArgs.annotation_group:
      if annotation_group not in supported_groups:
        OptError("Unsupported --annotation-group value \"%s\"" %(annotation_group))

  if runArgs.gvcf_gq_bands != None:
    prev_band = 0
    for band in runArgs.gvcf_gq_bands:
      if band < 1 or band > 100:
        OptError("--gvcf-gq-bands values cannot be less than 1 or greater than 100")
      elif band < prev_band:
        OptError("--gvcf-gq-bands values must be specified in increasing order (%d provided after %d)" %(band, prev_band))
      prev_band = band

  if initial_pipeline_check == True:
    # Don't want to check for in_bam or human_par yet
    return

  if runArgs.sample_sex != None or runArgs.range_male != None or runArgs.range_female != None:
    check_human_par(runArgs)

def check_mutect_common(runArgs):
  if runArgs.run_partition == True:
    gpu_num_per_partition = 2
    if runArgs.gpu_num_per_partition != None:
      gpu_num_per_partition = runArgs.gpu_num_per_partition
      if runArgs.gpu_num_per_partition < 1:
        OptError("--gpu-num-per-partition cannot be less than 1")
      
    if runArgs.num_gpus % gpu_num_per_partition != 0:
      OptError("Cannot run partition with " + str(runArgs.num_gpus) + " gpus, make gpu number mulitple of " + str(gpu_num_per_partition))

    if runArgs.mutect_germline_resource != None:
      OptError("--mutect-germline-resource cannot work in partition mode")

    if runArgs.mutect_f1r2_tar_gz != None:
      OptError("--mutect-f1r2-tar-gz cannot work with partition mode")
    
    if (hasattr(runArgs, "out_vcf") and  runArgs.out_vcf.endswith(".gz")):
      OptError("--run-partition cannot work with .gz output")

  if runArgs.mutect_f1r2_tar_gz != None:
    if (runArgs.mutect_f1r2_tar_gz.endswith(".tar.gz") != True):
      OptError("--mutect-f1r2-tar-gz file should end with .tar.gz")
    


def check_mutect(runArgs):

  check_mutect_common(runArgs)

  if (hasattr(runArgs, "interval") and (runArgs.interval != None) and len(runArgs.interval) > 0) or (hasattr(runArgs, "interval_file") and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0):
    if hasattr(runArgs, "no_alt_contigs") and runArgs.no_alt_contigs == True:
      OptError("--interval and --no-alt-contigs cannot be passed together")
    if runArgs.run_partition == True:
      OptError("--run-partition cannot work with intervals")

  if runArgs.tumor_name == None:
    OptError("Tumor name should be set. See --tumor-name option in --help")

  if (runArgs.normal_name != None) or (runArgs.in_normal_recal_file != None):
    if runArgs.in_normal_bam == None:
      OptError("Must specify --in-normal-bam to process normal samples")

  if runArgs.in_normal_bam != None:
    if runArgs.normal_name == None:
      OptError("Normal name needed for normal BAM in mutectcaller")
    if runArgs.in_tumor_bam == runArgs.in_normal_bam:
      OptError("Both tumor and normal BAM cannot be the same file")

  if runArgs.in_normal_bam != None:
    if runArgs.tumor_name == runArgs.normal_name:
      OptError("Both tumor and normal name cannot be same")
    if (runArgs.in_tumor_recal_file != None) ^ (runArgs.in_normal_recal_file != None):
      OptError("Either tumor and normal both have recal file or none should have recal file")
    else:
      if runArgs.in_tumor_recal_file != None:
        if runArgs.in_tumor_recal_file == runArgs.in_normal_recal_file:
          OptError("Both tumor and normal recalibration file cannot be the same file")

def parse_num_streams_per_gpu_DV_DS(runArgs, is_deep_somatic: bool):
  if runArgs.num_streams_per_gpu == "auto":
    OptMesg("Setting --num-streams-per-gpu based on available device memory.")
    memories = GetDevicesAvailableMemory()
    min_memory = min(memories)

    # memory limit shows the actual device memory usage. Need to update if code changes
    STREAM_4_MEMORY_LIMIT = 24_000
    STREAM_2_MEMORY_LIMIT = 13_000


    if runArgs.num_gpus > 2:
      if min_memory < STREAM_2_MEMORY_LIMIT:
        runArgs.num_streams_per_gpu = 1
      else:
        runArgs.num_streams_per_gpu = 2

    else:
      if is_deep_somatic:
        if min_memory < STREAM_2_MEMORY_LIMIT:
          runArgs.num_streams_per_gpu = 1
          # 2 streams with <40GB based on performance benchmark.
        elif min_memory < 40_000:
          runArgs.num_streams_per_gpu = 2
        else:
          if (min_memory < STREAM_4_MEMORY_LIMIT):
            OptError("Memory check failed. Please pass --num-streams-per-gpu manually")
          runArgs.num_streams_per_gpu = 4
      else:  # else deepvariant
        if min_memory < STREAM_2_MEMORY_LIMIT:
          runArgs.num_streams_per_gpu = 1
        elif min_memory < STREAM_4_MEMORY_LIMIT:
          runArgs.num_streams_per_gpu = 2
        else:
          runArgs.num_streams_per_gpu = 4
  else:
    try:
      runArgs.num_streams_per_gpu = int(runArgs.num_streams_per_gpu)
      if runArgs.num_streams_per_gpu < 1:
        OptError(f"--num-streams-per-gpu must be greater than 0, user provided {runArgs.num_streams_per_gpu}")
    except:
      OptError(f"Invalid --num-streams-per-gpu value: {runArgs.num_streams_per_gpu}. Must be a positive integer or 'auto'.")

def check_somatic(runArgs):
  check_mutect_common(runArgs)

  if runArgs.in_tumor_fq == None and runArgs.in_se_tumor_fq == None:
    OptError("Must specify input tumor FASTQ using either --in-tumor-fq or --in-se-tumor-fq")
  
  if runArgs.in_normal_fq != None or runArgs.in_se_normal_fq != None:
    if runArgs.out_normal_bam == None:
      OptError("Must specify the --out-normal-bam if given --in-normal-fq or --in-se-normal-fq")
    if runArgs.out_normal_bam == runArgs.out_tumor_bam:
      OptError("--out-normal-bam and --out-tumor-bam cannot have the same name")
    if (runArgs.knownSites != None):
      if (runArgs.out_normal_recal_file == None):
        OptError("With --knownSites option, recalibration file will be generated. Please specify output recalibration file --out-normal-recal-file.")
      if (runArgs.out_tumor_recal_file == runArgs.out_normal_recal_file):
        OptError("--out-tumor-recal-file and --out-normal-recal-file cannot have the same name")
    if (runArgs.knownSites == None) and (runArgs.out_normal_recal_file != None):
      OptError("Without --knownSites option, recalibration file will not be generated. Please remove output recalibration file or add --knownSites file")

def check_pangenome_aware_deepvariant(runArgs, initial_pipeline_check=False):
  parse_num_streams_per_gpu_DV_DS(runArgs, True)

  if runArgs.num_gpus > 2 and runArgs.run_partition != True:
    OptMesg("Please consider using --run-partition for best performance with more than 2 GPUs")

  if (hasattr(runArgs, "interval_file")) and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      values = interval_file.split(".")
      if len(values) < 2 or values[len(values) - 1] != "bed":
        OptError("--interval-file must be in BED format (.bed).")
  
  if runArgs.run_partition == True:
    if (hasattr(runArgs, "out_variants") and  runArgs.out_variants.endswith(".gz")):
      OptError("--run-partition cannot work with .gz output")
  
  #runArgs.channel_insert_size = True
  #if runArgs.no_channel_insert_size == True:
  #  runArgs.channel_insert_size = False

  if runArgs.mode not in ["shortread"]:
    OptError("--mode can only be set to one of [shortread]")
  
  if runArgs.mode == "shortread":
    
    if runArgs.pileup_image_width == None:
      runArgs.pileup_image_width=221
    
    if runArgs.min_mapping_quality == None:
      runArgs.min_mapping_quality = 0
    


def check_deepsomatic(runArgs, initial_pipeline_check=False):
  parse_num_streams_per_gpu_DV_DS(runArgs, True)

  if runArgs.num_gpus > 2 and runArgs.run_partition != True:
    OptMesg("Please consider using --run-partition for best performance with more than 2 GPUs")
    
  if (hasattr(runArgs, "interval_file")) and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      values = interval_file.split(".")
      if len(values) < 2 or values[len(values) - 1] != "bed":
        OptError("--interval-file must be in BED format (.bed).")
  
  if runArgs.run_partition == True:
    if (hasattr(runArgs, "out_variants") and  runArgs.out_variants.endswith(".gz")):
      OptError("--run-partition cannot work with .gz output")
  
  #runArgs.channel_insert_size = True
  #if runArgs.no_channel_insert_size == True:
  #  runArgs.channel_insert_size = False

  if runArgs.mode not in ["shortread", "pacbio", "ont"]:
    OptError("--mode can only be set to one of [shortread, pacbio, ont]")
  
  if runArgs.mode == "shortread":
    if runArgs.vsc_min_fraction_indels == None:
      runArgs.vsc_min_fraction_indels = 0.05000000074505806

    if runArgs.vsc_min_fraction_snps == None:
      runArgs.vsc_min_fraction_snps = 0.029

    if runArgs.vsc_min_count_indels == None:
      runArgs.vsc_min_count_indels = 2

    if runArgs.vsc_min_count_snps == None:
      runArgs.vsc_min_count_snps = 2
    
    if runArgs.pileup_image_width == None:
      runArgs.pileup_image_width=221
    
    if runArgs.min_mapping_quality == None:
      runArgs.min_mapping_quality = 5
    
    if runArgs.partition_size == None:
      runArgs.partition_size = 1000
    
    if runArgs.alt_aligned_pileup == "diff_channels":
      OptError("--alt-aligned-pileup cannot be set to diff_channels in shortread mode")
    else:
      runArgs.alt_aligned_pileup = "none"
    
    runArgs.phase_reads = False
    runArgs.track_ref_reads = False
    runArgs.add_hp_channel = False
    runArgs.sort_by_haplotypes = False
    runArgs.parse_sam_aux_fields = False
    runArgs.norealign_reads = False
    runArgs.min_base_quality = 10
    runArgs.no_channel_insert_size = False
    runArgs.vsc_max_fraction_indels_for_non_target_sample = 0.5
    runArgs.vsc_max_fraction_snps_for_non_target_sample = 0.5
    
  elif runArgs.mode == "pacbio":
    
    if runArgs.pileup_image_width == None:
      runArgs.pileup_image_width = 147
    
    if runArgs.min_mapping_quality == None:
      runArgs.min_mapping_quality = 5
    
    if runArgs.partition_size == None:
      runArgs.partition_size = 25000

    if runArgs.vsc_min_count_indels == None:
      runArgs.vsc_min_count_indels = 2

    if runArgs.vsc_min_count_snps == None:
      runArgs.vsc_min_count_snps = 1
    
    if runArgs.vsc_min_fraction_indels == None:
      runArgs.vsc_min_fraction_indels = 0.10000000149011612 #adjusting to correct precision errors

    if runArgs.vsc_min_fraction_snps == None:
      runArgs.vsc_min_fraction_snps = 0.02
    
    if runArgs.alt_aligned_pileup == None:
      runArgs.alt_aligned_pileup = "diff_channels"

    runArgs.norealign_reads = True
    runArgs.add_hp_channel = True
    runArgs.sort_by_haplotypes = True
    runArgs.parse_sam_aux_fields = True
    runArgs.no_channel_insert_size = True
    runArgs.phase_reads = True
    runArgs.track_ref_reads = True
    runArgs.min_base_quality = 10
    runArgs.disable_window_selector_model = False
    runArgs.vsc_max_fraction_indels_for_non_target_sample = 0.5
    runArgs.vsc_max_fraction_snps_for_non_target_sample = 0.5
  
  elif runArgs.mode == "ont":
    if runArgs.pileup_image_width == None:
      runArgs.pileup_image_width = 99
    
    if runArgs.min_mapping_quality == None:
      runArgs.min_mapping_quality = 5
    
    if runArgs.partition_size == None:
      runArgs.partition_size = 25000

    if runArgs.vsc_min_count_indels == None:
      runArgs.vsc_min_count_indels = 2

    if runArgs.vsc_min_count_snps == None:
      runArgs.vsc_min_count_snps = 2
    
    if runArgs.vsc_min_fraction_indels == None:
      runArgs.vsc_min_fraction_indels = 0.10000000149011612 #adjusting to correct precision errors

    if runArgs.vsc_min_fraction_snps == None:
      runArgs.vsc_min_fraction_snps = 0.05000000074505806 #adjusting to correct precision errors
    
    if runArgs.alt_aligned_pileup == None:
      runArgs.alt_aligned_pileup = "diff_channels"

    runArgs.norealign_reads = True
    runArgs.add_hp_channel = True
    runArgs.sort_by_haplotypes = True
    runArgs.parse_sam_aux_fields = True
    runArgs.no_channel_insert_size = True
    runArgs.phase_reads = True
    runArgs.track_ref_reads = True
    runArgs.min_base_quality = 10
    runArgs.disable_window_selector_model = False
    runArgs.vsc_max_fraction_indels_for_non_target_sample = 0.6
    runArgs.vsc_max_fraction_snps_for_non_target_sample = 0.6
    
def check_deepvariant(runArgs, initial_pipeline_check=False):

  parse_num_streams_per_gpu_DV_DS(runArgs, False)
  
  if runArgs.num_gpus > 2 and runArgs.run_partition != True:
    OptMesg("Please consider using --run-partition for best performance with more than 2 GPUs")
  if runArgs.run_partition == True:
    gpu_num_per_partition = 2
    if runArgs.gpu_num_per_partition != None:
      gpu_num_per_partition = runArgs.gpu_num_per_partition
      if runArgs.gpu_num_per_partition < 1:
        OptError("--gpu-num-per-partition cannot be less than 1")

    if runArgs.num_gpus % gpu_num_per_partition != 0:
      OptError("Cannot run partition with " + str(runArgs.num_gpus) + " gpus, make gpu number mulitple of " + str(gpu_num_per_partition))

    if (hasattr(runArgs, "out_variants") and  runArgs.out_variants.endswith(".gz")):
      OptError("--run-partition cannot work with .gz output")
    if runArgs.read_from_tmp_dir == True and runArgs.gvcf == True:
      OptError("Reading from tmp files cannot work with gvcf output in partition mode")
    if runArgs.gvcf == True and (hasattr(runArgs, "out_variants") and runArgs.out_variants.endswith(".g.vcf") == False):
      OptError("Output file name should end with .g.vcf in partition mode")

  if (hasattr(runArgs, "interval") and (runArgs.interval != None) and len(runArgs.interval) > 0) or (hasattr(runArgs, "interval_file") and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0):
    if runArgs.run_partition == True:
      OptError("--run-partition cannot work with intervals")
    if runArgs.read_from_tmp_dir == True:
      OptError("--read-from-tmp-dir cannot work with intervals")

  if (hasattr(runArgs, "interval_file")) and (runArgs.interval_file != None) and len(runArgs.interval_file) > 0:
    for interval_file in runArgs.interval_file:
      values = interval_file.split(".")
      if len(values) < 2 or values[len(values) - 1] != "bed":
        OptError("--interval-file must be in BED format (.bed).")
  if runArgs.mode not in ["shortread", "pacbio", "ont"]:
    OptError("--mode can only be set to one of [shortread, ont, pacbio]")


  if (hasattr(runArgs, "use_wes_model")) and runArgs.use_wes_model == True:
    if runArgs.mode != "shortread":
      OptError("--use-wes-model can only work with shortread mode")

  if runArgs.no_channel_insert_size == True and runArgs.channel_insert_size == True:
      OptError("--channel-insert-size and --no-channel-insert-size cannot be specified together.")

  if runArgs.read_from_tmp_dir == True:
    if hasattr(runArgs, "knownSites") and runArgs.knownSites != None:
      OptError("--read-from-tmp-dir cannot work with bqsr")


  if initial_pipeline_check == True:
    return

  if runArgs.mode == "shortread":
    runArgs.channel_insert_size = True
    if runArgs.alt_aligned_pileup == None:
      runArgs.alt_aligned_pileup = "none"
    if runArgs.variant_caller == None:
      runArgs.variant_caller = "VERY_SENSITIVE_CALLER"

  elif runArgs.mode == "pacbio":
    runArgs.norealign_reads = True
    if runArgs.vsc_min_fraction_indels == None:
      runArgs.vsc_min_fraction_indels = 0.12
    if runArgs.alt_aligned_pileup == None:
      runArgs.alt_aligned_pileup = "diff_channels"
    if runArgs.variant_caller == None:
      runArgs.variant_caller = "VERY_SENSITIVE_CALLER"
    runArgs.add_hp_channel = True
    runArgs.sort_by_haplotypes = True
    runArgs.parse_sam_aux_fields = True
    runArgs.pileup_image_width = 147
    runArgs.max_reads_per_partition = 600
    runArgs.min_mapping_quality = 1
    runArgs.partition_size = 25000
    runArgs.phase_reads = True
    runArgs.track_ref_reads = True

  elif runArgs.mode == "ont":
    runArgs.norealign_reads = True
    if runArgs.variant_caller == "VCF_CANDIDATE_IMPORTER":
      if runArgs.alt_aligned_pileup == None:
        runArgs.alt_aligned_pileup = "none"
    else:
      runArgs.vsc_min_fraction_indels = 0.12
      runArgs.vsc_min_fraction_snps = 0.08
      runArgs.alt_aligned_pileup = "diff_channels"
      runArgs.variant_caller = "VERY_SENSITIVE_CALLER"
      runArgs.add_hp_channel = True
      runArgs.max_reads_per_partition = 600
      runArgs.min_mapping_quality = 5
      runArgs.parse_sam_aux_fields = True
      runArgs.partition_size = 25000
      runArgs.phase_reads = True
      runArgs.pileup_image_width = 99
      runArgs.sort_by_haplotypes = True
      runArgs.track_ref_reads = True

  if runArgs.no_channel_insert_size == True:
    runArgs.channel_insert_size = False


def check_genotypegvcf(runArgs):
  if (runArgs.in_gvcf == None):
    OptError("--in-gvcf must be specified for genotypegvcf")


def check_applybqsr(runArgs):
  if runArgs.num_gpus > 2:
    OptError("Please run applybqsr with 1 or 2 GPUs only")


def check_collectmultiplemetrics(runArgs):
  if runArgs.gen_all_metrics:
    if runArgs.gen_alignment  or runArgs.gen_quality_score  or runArgs.gen_insert_size  or \
       runArgs.gen_mean_quality_by_cycle  or runArgs.gen_base_distribution_by_cycle  or \
       runArgs.gen_gc_bias  or runArgs.gen_seq_artifact  or runArgs.gen_quality_yield :
      OptError("--gen-all-metrics is already specified. No other metric is required")

  if runArgs.gen_all_metrics != True:
    if runArgs.gen_alignment != True and runArgs.gen_quality_score != True and runArgs.gen_insert_size != True and \
       runArgs.gen_mean_quality_by_cycle != True and runArgs.gen_base_distribution_by_cycle != True and \
       runArgs.gen_gc_bias != True and runArgs.gen_seq_artifact != True and runArgs.gen_quality_yield != True:
      OptError("--gen-all-metrics or no other metric is specified. Please rerun")


def check_rna_fq2bam(runArgs, initial_pipeline_check=False):

  if runArgs.out_prefix == None:
    runArgs.out_prefix = ""
  if '/' in runArgs.out_prefix:
    OptError("--out-prefix cannot contain forward slashes")

  twoPassModeOptions = ["None", "Basic"]
  if runArgs.two_pass_mode not in twoPassModeOptions:
    OptError("Unrecognized --two-pass-mode value \"%s\"" %(runArgs.two_pass_mode))

  # Handle auto-configuration for STAR streams and threads
  # Users can override one or both values - we only auto-configure values set to "auto"
  streams_is_auto = (runArgs.num_streams_per_gpu == "auto")
  threads_is_auto = (runArgs.num_threads == "auto")

  # Validate and convert user-provided values first
  if not streams_is_auto:
    try:
      runArgs.num_streams_per_gpu = int(runArgs.num_streams_per_gpu)
      if runArgs.num_streams_per_gpu < 1:
        OptError(f"--num-streams-per-gpu must be greater than 0, user provided {runArgs.num_streams_per_gpu}")
    except ValueError:
      OptError(f"Invalid --num-streams-per-gpu value: {runArgs.num_streams_per_gpu}. Must be a positive integer or 'auto'.")

  if not threads_is_auto:
    try:
      runArgs.num_threads = int(runArgs.num_threads)
      if runArgs.num_threads < 1:
        OptError("--num-threads must be greater than 0")
    except ValueError:
      OptError(f"Invalid --num-threads value: {runArgs.num_threads}. Must be a positive integer or 'auto'.")

  # Auto-configure only the values that are set to "auto"
  if streams_is_auto or threads_is_auto:
    memories = GetDevicesAvailableMemory()
    min_gpu_memory = min(memories)
    cpu_memory_gb = GetDefaultMemoryLimit() * 2

    # Get auto-configured values
    # Pass user-specified threads for accurate memory estimation when only streams is auto
    user_threads = runArgs.num_threads if not threads_is_auto else None
    auto_streams, auto_threads = GetDeviceModeSTAR(min_gpu_memory, cpu_memory_gb, runArgs.num_gpus, user_threads)

    # Apply auto values only for parameters set to "auto", preserve user overrides
    if streams_is_auto and threads_is_auto:
      runArgs.num_streams_per_gpu = auto_streams
      runArgs.num_threads = auto_threads
      OptMesg(f"STAR auto-configuration: {runArgs.num_gpus} GPUs, {auto_streams} streams/GPU, {auto_threads} threads/stream")
    elif streams_is_auto:
      runArgs.num_streams_per_gpu = auto_streams
      OptMesg(f"STAR auto-configuration: {auto_streams} streams/GPU (user specified {runArgs.num_threads} threads)")
    else:  # threads_is_auto
      runArgs.num_threads = auto_threads
      OptMesg(f"STAR auto-configuration: {auto_threads} threads/stream (user specified {runArgs.num_streams_per_gpu} streams)")

    OptMesg(f"  GPU memory: {min_gpu_memory}MiB, CPU memory: {cpu_memory_gb}GB")
    
    # Auto-configure postsort mode based on GPU memory
    GetPostsortMode(min_gpu_memory, runArgs)

  if runArgs.use_gds == True:
    if runArgs.gpuwrite == None:
      OptError("The option --use-gds must be used concurrently with --gpuwrite.")
    try:
      gdsoutput = subprocess.run(["/usr/local/cuda/gds/tools/gdscheck", "-p"], check=True, capture_output=True)
      # check that at least one GDS driver configuration is supported
      hasOneGDSSupport = ": Supported" in gdsoutput.stdout.decode()
      if not hasOneGDSSupport:
        OptError("With --use-gds, at least one driver configuration must be supported. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.")
    except:
      # if this exception happens then there was probably something wrong with the docker image
      OptError("With --use-gds, unable to run `gdscheck`. Please ensure that GDS is available.")

  if runArgs.gpuwrite_deflate_algo != None:
    if runArgs.gpuwrite == None:
      OptError("Using `--gpuwrite-deflate-algo #` only has an effect when --gpuwrite is used.")
    if runArgs.gpuwrite_deflate_algo not in (1, 2, 4):
      extramsg = ""
      if runArgs.gpuwrite_deflate_algo in (0, 3):
        extramsg = " Note: as of >= version 4.4 options 0 and 3 have been replaced, see documentation."
      OptError("With --gpuwrite-deflate-algo, only options 1, 2, and 4 are valid." + extramsg)

  if initial_pipeline_check == False:
    outSamAttributesOptions = ["NH", "HI", "AS", "nM", "NM", "MD", "jM", "jI", "XS", "MC", "ch"]
    outSamAttributesSetOptions = ["None", "Standard", "All"]
    if not isinstance(runArgs.out_sam_attributes, list):
      runArgs.out_sam_attributes = [runArgs.out_sam_attributes]
    SAMattributes = runArgs.out_sam_attributes
    if len(SAMattributes) == 1:
      if SAMattributes[0] not in outSamAttributesOptions and SAMattributes[0] not in outSamAttributesSetOptions:
        OptError("Unrecognized --out-sam-attributes value \"%s\"" %(SAMattributes[0]))
    else:
      for attr in SAMattributes:
        if attr in outSamAttributesSetOptions:
          OptError("--out-sam-attributes value \"%s\" should not be passed with any other values" %(attr))
        if attr not in outSamAttributesOptions:
          OptError("Unrecognized --out-sam-attributes value \"%s\"" %(attr))

    outFilterIntronMotifsOptions = ["None", "RemoveNoncanonical", "RemoveNoncanonicalUnannotated"]
    if runArgs.out_filter_intron_motifs not in outFilterIntronMotifsOptions:
      OptError("Unrecognized --out-filter-intron-motifs value \"%s\"" %(runArgs.out_filter_intron_motifs))

    outReadsUnmappedOptions = ["None", "Fastx"]
    if runArgs.out_reads_unmapped not in outReadsUnmappedOptions:
      OptError("Unrecognized --out-reads-unmapped value \"%s\"" %(runArgs.out_reads_unmapped))

    outSamUnmappedOptions = ["None", "Within", "Within_KeepPairs"]
    if runArgs.out_sam_unmapped not in outSamUnmappedOptions:
      OptError("Unrecognized --out-sam-unmapped value \"%s\"" %(runArgs.out_sam_unmapped))

    outSamStrandFieldOptions = ["None", "intronMotif"]
    if runArgs.out_sam_strand_field not in outSamStrandFieldOptions:
      OptError("Unrecognized --out-sam-strand-field value \"%s\"" %(runArgs.out_sam_strand_field))

    outSamModeOptions = ["None", "Full", "NoQS"]
    if runArgs.out_sam_mode not in outSamModeOptions:
      OptError("Unrecognized --out-sam-mode value \"%s\"" %(runArgs.out_sam_mode))

    alignInsertionFlushOptions = ["None", "Right"]
    if runArgs.align_insertion_flush not in alignInsertionFlushOptions:
      OptError("Unrecognized --align-insertion-flush value \"%s\"" %(runArgs.align_insertion_flush))

    alignEndsTypeOptions = ["Local", "EndToEnd"]
    if runArgs.align_ends_type not in alignEndsTypeOptions:
      OptError("Unrecognized --align-ends-type value \"%s\"" %(runArgs.align_ends_type))

    outChimTypeOptions = ["Junctions", "WithinBAM", "WithinBAM_HardClip", "WithinBAM_SoftClip"]
    if runArgs.out_chim_type != None:
      for out_chim_type_single in runArgs.out_chim_type:
        if out_chim_type_single not in outChimTypeOptions:
          OptError("Unrecognized --out-chim-type value \"%s\"" %(runArgs.out_chim_type))

    if runArgs.out_sam_mapq_unique < 0 or runArgs.out_sam_mapq_unique > 255:
      OptError("--out-sam-mapq-unique value cannot be less than 0 or greater than 255")

    if runArgs.max_bam_sort_memory < 0:
      OptError("--max-bam-sort-memory must be greater than or equal to 0")

    if runArgs.min_align_spliced_mate_map < 0:
      OptError("--min-align-spliced-mate-map must be greater than or equal to 0")

    if runArgs.max_collapsed_junctions <= 0:
      OptError("--max-collapsed-junctions must be greater than 0")

    if runArgs.min_align_sj_overhang <= 0:
      OptError("--min-align-sj-overhang must be greater than 0")

    if runArgs.min_align_sjdb_overhang <= 0:
      OptError("--min-align-sjdb-overhang must be greater than 0")

    if runArgs.sjdb_overhang <= 0:
      OptError("--sjdb_overhang be greater than 0")

    if runArgs.min_chim_overhang < 0:
      OptError("--min-chim-overhang must be greater than or equal to 0")

    if runArgs.min_chim_segment < 0:
      OptError("--min-chim-segment must be greater than or equal to 0")

    if runArgs.max_chim_multimap < 0:
      OptError("--max-chim-multimap must be greater than or equal to 0")

    if runArgs.chim_multimap_score_range < 0:
      OptError("--chim-multimap-score-range must be greater than or equal to 0")

    if runArgs.min_non_chim_score_drop < 0:
      OptError("--min-non-chim-score-drop must be greater than or equal to 0")

    if runArgs.out_chim_format < 0 or runArgs.out_chim_format > 1:
      OptError("--out-chim-format must be 0 or 1")

    for mismatch in runArgs.max_junction_mismatches:
      if mismatch < -1:
        OptError("--max-junction-mismatches cannot contain values less than -1")

    if runArgs.min_spliced_mate_length < 0:
      OptError("--min-spliced-mate-length must be greater than or equal to 0")

    if runArgs.max_out_read_size <= 0:
      OptError("--max-out-read-size must be greater than 0")

    if runArgs.max_alignments_per_read <= 0:
      OptError("--max-alignments-per-read must be greater than 0")

    if runArgs.seed_search_start <= 0:
      OptError("--seed-search-start must be greater than 0")

  if runArgs.in_fq == None and runArgs.in_se_fq == None and runArgs.in_fq_list == None and runArgs.in_se_fq_list == None:
    OptError("Fastq files required. Please specify FASTQ files using one of the following: " +
             "--in-fq, --in-se-fq, --in-fq-list, or --in-se-fq-list")

  # Validate quantMode parameter
  if hasattr(runArgs, 'quantMode') and runArgs.quantMode is not None:
    valid_quant_modes = ["TranscriptomeSAM", "GeneCounts"]
    
    for mode in runArgs.quantMode:
      # Split by comma and strip whitespace
      for subMode in mode.split(','):
        subMode = subMode.strip()
        if subMode:  # Only process non-empty values
          if subMode not in valid_quant_modes:
            OptError(f"EXITING because of fatal INPUT error: unrecognized option in --quantMode={subMode}")
            OptError("SOLUTION: use one of the allowed values of --quantMode : TranscriptomeSAM or GeneCounts.")

  if runArgs.in_se_fq != None:
    check_se_fastq_files(runArgs.in_se_fq, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_fq != None:
    check_fastq_files(runArgs.in_fq, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_fq_list != None:
    runArgs.fastqGroups = check_fastq_list_pe_rna_fq2bam(runArgs.in_fq_list, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  elif runArgs.in_se_fq_list != None:
    runArgs.fastqGroups = check_fastq_list_se_rna_fq2bam(runArgs.in_se_fq_list, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)


def check_starfusion(runArgs):
  if runArgs.out_prefix == None:
    runArgs.out_prefix = ""
  if '/' in runArgs.out_prefix:
    OptError("--out-prefix cannot contain forward slashes")


def check_bamsort(runArgs):
  sort_orders = ["coordinate", "queryname", "templatecoordinate"]
  if runArgs.sort_order not in sort_orders:
    OptError("Unrecognized --sort-order value \"{runArgs.sort_order}\"")
  compatibilities = ["picard", "fgbio"]
  if runArgs.sort_compatibility not in compatibilities:
    OptError("Unrecognized --sort-compatibility value \"{runArgs.sort_compatibility}\"")


def check_bam2fq(runArgs):
  if runArgs.ref == None and (len(runArgs.in_bam) <= 4 or runArgs.in_bam[-4:] == "cram"):
      OptError("--ref is required for CRAM input. Exiting...")

  if runArgs.out_suffixF != None:
    if len(runArgs.out_suffixF) <= 3 or runArgs.out_suffixF[-3:] != ".gz":
      OptError("--out-suffixF \"" + runArgs.out_suffixF + "\" is invalid. Suffix must end with \".gz\". Exiting...")
  if runArgs.out_suffixF2 != None:
    if len(runArgs.out_suffixF2) <= 3 or runArgs.out_suffixF2[-3:] != ".gz":
      OptError("--out-suffixF2 \"" + runArgs.out_suffixF2 + "\" is invalid. Suffix must end with \".gz\". Exiting...")
  if runArgs.out_suffixO != None:
    if len(runArgs.out_suffixO) <= 3 or runArgs.out_suffixO[-3:] != ".gz":
      OptError("--out-suffixO \"" + runArgs.out_suffixO + "\" is invalid. Suffix must end with \".gz\". Exiting...")
  if runArgs.out_suffixO2 != None:
    if len(runArgs.out_suffixO2) <= 3 or runArgs.out_suffixO2[-3:] != ".gz":
      OptError("--out-suffixO2 \"" + runArgs.out_suffixO2 + "\" is invalid. Suffix must end with \".gz\". Exiting...")
  if runArgs.out_suffixS != None:
    if len(runArgs.out_suffixS) <= 3 or runArgs.out_suffixS[-3:] != ".gz":
      OptError("--out-suffixS \"" + runArgs.out_suffixS + "\" is invalid. Suffix must end with \".gz\". Exiting...")

  if runArgs.rg_tag != None:
    if runArgs.rg_tag != "PU" and runArgs.rg_tag != "ID":
      OptError("Unrecognized --rg-tag value \"" + runArgs.rg_tag + "\". Must be \"PU\" or \"ID\". Exiting...")

  #prevent writer threads from trying to write to the same file
  if runArgs.out_suffixF2 != None:
    if runArgs.out_suffixF != None and runArgs.out_suffixF == runArgs.out_suffixF2:
      OptError("--out-suffixF and --out-suffixF2 cannot be the same. Exiting...")
    if runArgs.out_suffixS != None and runArgs.out_suffixS == runArgs.out_suffixF2:
      OptError("--out-suffixS and --out-suffixF2 cannot be the same. Exiting...")
    if runArgs.out_suffixO != None and runArgs.out_suffixO == runArgs.out_suffixF2:
      OptError("--out-suffixO and --out-suffixF2 cannot be the same. Exiting...")
  if runArgs.out_suffixO2 != None:
    if runArgs.out_suffixF != None and runArgs.out_suffixF == runArgs.out_suffixO2:
      OptError("--out-suffixF and --out-suffixO2 cannot be the same. Exiting...")
    if runArgs.out_suffixS != None and runArgs.out_suffixS == runArgs.out_suffixO2:
      OptError("--out-suffixS and --out-suffixO2 cannot be the same. Exiting...")
    if runArgs.out_suffixO != None and runArgs.out_suffixO == runArgs.out_suffixO2:
      OptError("--out-suffixO and --out-suffixO2 cannot be the same. Exiting...")

def check_minimap2(runArgs):
  if (runArgs.in_fq == None) and (runArgs.in_bam == None):
    OptError("No input file detected. Must use either --in-fq or --in-bam.")

  if (runArgs.in_fq != None) and (runArgs.in_bam != None):
    OptError("Cannot use multiple input files. Must use either --in-fq or --in-bam.")

  if runArgs.preset not in ["map-pbmm2", "map-hifi", "map-ont", "lr:hq", "splice", "splice:hq", "splice:sr"]:
    OptError("Unrecognized --preset value \"%s\", should be set to one of [map-pbmm2, map-hifi, map-ont, lr:hq, splice, splice:hq, splice:sr]" %(runArgs.preset))

  if runArgs.pbmm2_unmapped == True and runArgs.pbmm2 == None:
    OptError("The option --pbmm2-unmapped must be used concurrently with --pbmm2.")

  if runArgs.pbmm2 == True and runArgs.preset == "map-ont":
    OptError("Cannot use \"map-ont\" --preset value with --pbmm2.")

  if runArgs.both_strands == True and runArgs.forward_transcript_strand == True:
    OptError("--both-strands and --forward-transcript-strand cannot be used together. Only one way can be used to find canonical splicing sites.")

  if runArgs.use_gds == True:
    if runArgs.gpuwrite == None:
      OptError("The option --use-gds must be used concurrently with --gpuwrite.")
    try:
      gdsoutput = subprocess.run(["/usr/local/cuda/gds/tools/gdscheck", "-p"], check=True, capture_output=True)
      # check that at least one GDS driver configuration is supported
      hasOneGDSSupport = ": Supported" in gdsoutput.stdout.decode()
      if not hasOneGDSSupport:
        OptError("With --use-gds, at least one driver configuration must be supported. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.")
    except:
      # if this exception happens then there was probably something wrong with the docker image
      OptError("With --use-gds, unable to run `gdscheck`. Please ensure that GDS is available.")

  if runArgs.gpuwrite_deflate_algo != None:
    if runArgs.gpuwrite == None:
      OptError("Using `--gpuwrite-deflate-algo #` only has an effect when --gpuwrite is used.")
    if runArgs.gpuwrite_deflate_algo not in (1, 2, 4):
      extramsg = ""
      if runArgs.gpuwrite_deflate_algo in (0, 3):
        extramsg = " Note: as of >= version 4.4 options 0 and 3 have been replaced, see documentation."
      OptError("With --gpuwrite-deflate-algo, only options 1, 2, and 4 are valid." + extramsg)

  if (runArgs.knownSites != None) and (runArgs.out_recal_file == None):
    OptError("With --knownSites option, recalibration file will be generated. Please specify output recalibration file.")

  if (runArgs.knownSites == None) and (runArgs.out_recal_file != None):
    OptError("Without --knownSites option, recalibration file will not be generated. Please remove output recalibration file or add --knownSites file.")
  
  if (runArgs.no_markdups == True):
    if (runArgs.out_duplicate_metrics != None):
      OptError("No metrics file will be generated with --no-markdups. Please remove --out-duplicate-metrics or --no-markdups.")
    if runArgs.markdups_assume_sortorder_queryname == True:
      OptError("Cannot use --markdups-assume-sortorder-queryname with --no-markdups.")

  if (runArgs.out_duplicate_metrics == None):
    if (runArgs.optical_duplicate_pixel_distance != None):
      OptMesg("No --out-duplicate_metrics specified, --optical_duplicate_pixel_distance will be ignored.")

  if (runArgs.max_queue_reads < 2 * runArgs.chunk_size):
    OptError("--max-queue-reads cannot be smaller than twice the size of --chunk-size.")


  # Generate RG line from either fastq or BAM input
  if runArgs.in_bam != None:
    runArgs.in_bam = [runArgs.in_bam]
    gen_rg_from_bam_input(runArgs.in_bam, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)
  else:
    runArgs.in_fq = sum(runArgs.in_fq, [])
    check_se_fastq_files_minimap2(runArgs.in_fq, runArgs.read_group_sm, runArgs.read_group_lb, runArgs.read_group_pl, runArgs.read_group_id_prefix)

def check_giraffe(runArgs):
  input_method = int(runArgs.in_fq != None) + int(runArgs.in_se_fq != None) + int(runArgs.in_se_fq_list != None) + int(runArgs.in_fq_list != None)
  if (input_method == 0) or (input_method > 1):
      OptError("Please only specifiy one input from --in-fq, --in-fq-list, --in-se-fq, or --in-se-fq-list")

  # Automode: only when --nstreams is auto. Will set streams, batch, low_memory, minimizers, dozeu, work-queue
  if runArgs.nstreams == "auto" and not runArgs.low_memory:
    memories = GetDevicesAvailableMemory()
    min_memory = min(memories)
    host_mem_gb = GetDefaultMemoryLimit() * 2 # * 2 because GetDefaultMemoryLimit() is half of the total system memory
    is_paired_end = runArgs.in_fq is not None or runArgs.in_fq_list is not None
    GetDeviceModeGiraffe(min_memory, runArgs, is_paired_end)
    ApplyHostMemoryThresholdsGiraffe(host_mem_gb, runArgs, is_paired_end)
    GetPostsortMode(min_memory, runArgs)
    if getattr(runArgs, "verbose", False):
      mode_str = "PE" if is_paired_end else "SE"
      OptMesg(f"Giraffe auto-configuration:")
      OptMesg(f"\tMode:\t\t\t{mode_str}")
      OptMesg(f"\tGPU memory:\t\t{min_memory} MiB, Host memory: {host_mem_gb} GiB")
      if runArgs.low_memory:
        OptMesg(f"\tLow-memory:\t\tenabled (GPU memory below threshold)")
      else:
        OptMesg(f"\tStreams/GPU:\t\t{runArgs.nstreams}")
        OptMesg(f"\tBatch size:\t\t{runArgs.batch_size}")
        OptMesg(f"\tWork queue capacity:\t{getattr(runArgs, 'work_queue_capacity', 40)}")
      OptMesg(f"\tMinimizers on GPU:\t{runArgs.minimizers_gpu}")
      OptMesg(f"\tDozeu on GPU:\t\t{runArgs.dozeu_gpu}")
    else:
      if runArgs.low_memory:
        OptMesg(f"Giraffe auto-configuration: low-memory mode (1 stream, batch 5000).")
      else:
        OptMesg(f"Giraffe auto-configuration: {runArgs.nstreams} streams/GPU, batch size {runArgs.batch_size}, work queue {getattr(runArgs, 'work_queue_capacity', 40)}, minimizers on GPU (SE only): {runArgs.minimizers_gpu}, dozeu on GPU (SE only): {runArgs.dozeu_gpu}.")
    OptMesg("To override: set --nstreams to the desired number and use the individual flags (--batch-size, --low-memory, --minimizers-gpu, and --work-queue-capacity) as needed. Note Dozeu on GPU is always enabled (for SE only) unless --low-memory is set.")
  elif runArgs.nstreams == "auto":
    # User passed --low-memory; use low-memory defaults (run_pb.py will set the rest)
    runArgs.nstreams = 1
  else:
    try:
      runArgs.nstreams = int(runArgs.nstreams)
      if runArgs.nstreams < 1:
        OptError("--nstreams must be greater than 0, user provided %s" % runArgs.nstreams)
    except (ValueError, TypeError):
      OptError("Invalid --nstreams value: %s. Must be a positive integer or 'auto'." % runArgs.nstreams)

  # if runArgs.parameter_preset and (runArgs.parameter_preset not in ["fast", "default"]):
  #   OptError("Unrecognized --parameter-preset value \"%s\", should be set to one of [fast, default]" %(runArgs.parameter_preset))
  if (runArgs.fragment_mean != None) and (runArgs.fragment_stdev == None):
    OptError("--fragment-mean requires setting --fragment-stdev also.")
  if (runArgs.fragment_mean == None) and (runArgs.fragment_stdev != None):
    OptError("--fragment-stdev requires setting --fragment-mean also.")
  if (hasattr(runArgs, "out_bam") and  runArgs.out_bam.endswith(".cram")):
    OptError("--out-bam for pbrun giraffe does not support CRAM output.")
  if runArgs.in_se_fq != None and (len(runArgs.in_se_fq) > 0):
    if (len(runArgs.in_se_fq)) > 1:
        OptError("Only one FASTQ input is supported with --in-se-fq. Please consider using --in-se-fq-list for multiple FASTQ input.")
    if len(runArgs.in_se_fq[0]) == 0:
      OptError("--in-se-fq requires a valid file path to be provided.")
    if len(runArgs.in_se_fq[0]) != 1:
      OptError("--in-se-fq option must have only have 1 FASTQ file. Please consider using --in-se-fq-list for multiple FASTQ input.")
    runArgs.in_se_fq[0][0] = IsFileStreamReadable(runArgs.in_se_fq[0][0])
  if runArgs.in_fq != None and (len(runArgs.in_fq) > 0):
    if (len(runArgs.in_fq)) > 1:
        OptError("Only one FASTQ pair input is supported at a time. Please consider using --in-fq-list for multiple FASTQ input pairs.")
    if len(runArgs.in_fq[0]) == 0:
      OptError("--in-fq requires valid file paths to be provided.")
    if len(runArgs.in_fq[0]) != 2:
      OptError("--in-fq option must have exactly 2 FASTQ files. Please consider using --in-fq-list for multiple FASTQ input pairs.")
    # runArgs.in_fq[0][0] = IsFileStreamReadable(runArgs.in_fq[0][0])
    # runArgs.in_fq[0][1] = IsFileStreamReadable(runArgs.in_fq[0][1])

  if runArgs.in_fq != None:
    runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group, runArgs.read_group_pu = check_pe_fastq_input_giraffe(runArgs.in_fq,  runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group, runArgs.read_group_pu)
  elif runArgs.in_se_fq != None:
    runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group, runArgs.read_group_pu = check_se_fastq_input_giraffe(runArgs.in_se_fq, runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group, runArgs.read_group_pu)
  elif runArgs.in_fq_list != None:
    runArgs.pe_fq_list = check_fastq_list_pe_giraffe(runArgs.in_fq_list, runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group)
  elif runArgs.in_se_fq_list != None:
    runArgs.se_fq_list = check_fastq_list_se_giraffe(runArgs.in_se_fq_list, runArgs.sample, runArgs.read_group_library, runArgs.read_group_platform, runArgs.read_group)

  # GDS is used by postsort when --gpuwrite is set; same checks as fq2bam
  if runArgs.use_gds == True:
    if runArgs.gpuwrite == None:
      OptError("The option --use-gds must be used concurrently with --gpuwrite.")
    try:
      gdsoutput = subprocess.run(["/usr/local/cuda/gds/tools/gdscheck", "-p"], check=True, capture_output=True)
      hasOneGDSSupport = ": Supported" in gdsoutput.stdout.decode()
      if not hasOneGDSSupport:
        OptError("With --use-gds, at least one driver configuration must be supported. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.")
    except:
      OptError("With --use-gds, unable to run `gdscheck`. Please ensure that GDS is available.")

  if runArgs.gpuwrite_deflate_algo != None:
    if runArgs.gpuwrite == None:
      OptError("Using `--gpuwrite-deflate-algo #` only has an effect when --gpuwrite is used.")
    if runArgs.gpuwrite_deflate_algo not in (1, 2, 4):
      extramsg = ""
      if runArgs.gpuwrite_deflate_algo in (0, 3):
        extramsg = " Note: as of >= version 4.4 options 0 and 3 have been replaced, see documentation."
      OptError("With --gpuwrite-deflate-algo, only options 1, 2, and 4 are valid." + extramsg)

  # no bqsr right now so these two checks are not needed
  # if (runArgs.knownSites != None) and (runArgs.out_recal_file == None):
  #   OptError("With --knownSites option, recalibration file will be generated. Please specify output recalibration file.")

  # if (runArgs.knownSites == None) and (runArgs.out_recal_file != None):
  #   OptError("Without --knownSites option, recalibration file will not be generated. Please remove output recalibration file or add --knownSites file")

  if (runArgs.no_markdups == True):
    if hasattr(runArgs, 'out_duplicate_metrics') and runArgs.out_duplicate_metrics is not None:
      OptError("No metrics file will be generated with --no-markdups. Please remove --out-duplicate-metrics or --no-markdups")
    if runArgs.markdups_assume_sortorder_queryname == True:
      OptError("Cannot use --markdups-assume-sortorder-queryname with --no-markdups")
    if runArgs.markdups_single_ended_start_end == True:
      OptError("Cannot use --markdups-single-ended-start-end with --no-markdups")

  if (runArgs.ignore_rg_markdups_single_ended == True) and (runArgs.markdups_single_ended_start_end != True):
   OptError("Cannot use --ignore-rg-markdups-single-ended without --markdups-single-ended-start-end")


  if not hasattr(runArgs, 'out_duplicate_metrics') or runArgs.out_duplicate_metrics is None:
    if (runArgs.optical_duplicate_pixel_distance != None):
      OptMesg("No --out-duplicate_metrics specified, --optical_duplicate_pixel_distance will be ignored")
  
  # --graph-name and --gbwt-name have to be passed together, and when they are passed --xg-name is required as well
  graph_name = runArgs.graph_name if hasattr(runArgs, 'graph_name') else None
  gbwt_name = runArgs.gbwt_name if hasattr(runArgs, 'gbwt_name') else None
  if (graph_name is None and gbwt_name is not None) or (graph_name is not None and gbwt_name is None):
    OptError("--gbwt-name and --graph-name need to be passed together.")
  xg_name = runArgs.xg_name if hasattr(runArgs, 'xg_name') else None
  if (graph_name is not None or gbwt_name is not None) and (xg_name is None):
    OptError("--xg-name is required when passing --gbwt-name and --graph-name")
  
  # check num cpu threads per gpu
  if runArgs.num_primary_cpus_per_gpu is not None:
    if runArgs.num_primary_cpus_per_gpu < 1:
      OptError("--num-primary-cpus-per-gpu must be a positive integer.")
  if runArgs.num_cpu_threads_per_gpu is not None:
    if runArgs.num_cpu_threads_per_gpu < 1:
      OptError("--num-cpu-threads-per-gpu must be a positive integer.")

def pbargs_check(runArgs):
  pbutils.runTempDir = runArgs.runArgs.tmp_dir
  if runArgs.command == "fq2bam":
    check_fq2bam(runArgs.runArgs, True)
  elif runArgs.command == "fq2bam_meth":
    # call the same argument checker for now; no divergence in needs
    check_fq2bam(runArgs.runArgs, False)
    check_fq2bam_meth(runArgs.runArgs)
  elif runArgs.command == "haplotypecaller":
    check_haplotypecaller(runArgs.runArgs)
  elif runArgs.command == "mutectcaller":
    check_mutect(runArgs.runArgs)
  elif runArgs.command == "deepvariant":
    check_deepvariant(runArgs.runArgs)
  elif runArgs.command == "deepsomatic":
    check_deepsomatic(runArgs.runArgs)
  elif runArgs.command == "pangenome_aware_deepvariant":
    check_pangenome_aware_deepvariant(runArgs.runArgs)
  elif runArgs.command == "genotypegvcf":
    check_genotypegvcf(runArgs.runArgs)
  elif runArgs.command == "applybqsr":
    check_applybqsr(runArgs.runArgs)
  elif runArgs.command == "collectmultiplemetrics":
    check_collectmultiplemetrics(runArgs.runArgs)
  elif runArgs.command == "rna_fq2bam":
    check_rna_fq2bam(runArgs.runArgs)
  elif runArgs.command == "starfusion":
    check_starfusion(runArgs.runArgs)
  elif runArgs.command == "bamsort":
    check_bamsort(runArgs.runArgs)
  elif runArgs.command == "bam2fq":
    check_bam2fq(runArgs.runArgs)
  elif runArgs.command == "minimap2":
    check_minimap2(runArgs.runArgs)
  elif runArgs.command == "giraffe":
    check_giraffe(runArgs.runArgs)
  elif runArgs.command in ["bammetrics", "bqsr", "indexgvcf",  "dbsnp", "prepon", "postpon", "markdup"]:
    return
  else:
    sys.exit(-1)


def check_fastq_input(runArgs):
  if runArgs.in_fq == None and runArgs.in_se_fq == None:
    OptError("Must specify input FASTQ using either --in-fq or --in-se-fq")


def check_pangenome_germline(runArgs):
  check_giraffe(runArgs)
  check_pangenome_aware_deepvariant(runArgs, initial_pipeline_check=True)


def pbargs_pipeline_check(runArgs):
  if runArgs.command == "germline":
    check_fastq_input(runArgs.runArgs)
    check_haplotypecaller(runArgs.runArgs, initial_pipeline_check=True)
  elif runArgs.command == "rna_gatk":
    check_splitncigar(runArgs.runArgs)
    check_rna_fq2bam(runArgs.runArgs, initial_pipeline_check=True)
    check_haplotypecaller(runArgs.runArgs, initial_pipeline_check=True)
  elif runArgs.command == "deepvariant_germline":
    check_fastq_input(runArgs.runArgs)
    check_deepvariant(runArgs.runArgs, initial_pipeline_check=True)
  elif runArgs.command == "pacbio_germline" or runArgs.command == "ont_germline":
    check_minimap2(runArgs.runArgs)
    check_deepvariant(runArgs.runArgs, initial_pipeline_check=True)
  elif runArgs.command == "pangenome_germline":
    check_pangenome_germline(runArgs.runArgs)
  elif runArgs.command == "somatic":
    check_somatic(runArgs.runArgs)
  else:
    return
