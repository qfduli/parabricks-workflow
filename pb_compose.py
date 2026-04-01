#!/usr/bin/env python3

import os
import os.path
import signal
import sys
import subprocess
import pbutils
import time
from pbargs import standaloneTools, PBRun
from pbargs_check import pbargs_pipeline_check
from run_pb import AddLogfile, SetUpEnv


class PBTool(object):
    """
    Everything we need to run one (standalone) tool.  Includes the command line arguments,
    but none of the Docker values.  A pipeline (such as germline) is built out of two
    or more PBTools.
    """

    def __init__(self, myBasecmd, myInitCmdLine, myArgs, myEnviron, tmp_dir,
                 parentCmd=None, verbosity=False, logfile=None, append=False):
        self.basecmd = myBasecmd
        self.parentcmd = parentCmd
        self.initCmds = myInitCmdLine
        self.cmdArgs = myArgs
        self.environ = myEnviron
        self.verbosity = verbosity
        self.tmp_dir = tmp_dir
        self.logfile = logfile
        self.append = append
        self.errorHint = None

    def clearFunction(self):
        if (self.basecmd == "fq2bam" or self.basecmd == "minimap2") and ("--keep-tmp" not in self.cmdArgs):
            pbutils.deleteTmpDir()
            os.makedirs(self.tmp_dir)

    def exitFunction(self, errorString, sleep=False):
        self.clearFunction()
        pbutils.deleteTmpDir()
        if sleep:
            time.sleep(0.2)  # Child and parent will both print exit messages nicely
        if self.errorHint:
            print("%s\n%s\nExiting pbrun ..." % (errorString, self.errorHint))
        else:
            print("%s\nExiting pbrun ..." % errorString)
        pbutils.pbExit(-1)

    def signal_handler(self, signal, frame):
        self.exitFunction("", sleep=True)

    def dispatch(self):
        """
        Run the docker command in a subprocess.  The Docker command may, in turn, invoke more
        than one executable. For example, "bwa" runs bwa-mem, sort and postsort.
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        try:
            fullCmdLine = []
            if self.parentcmd is not None:
                fullCmdLine = ["pbrun", self.basecmd] + self.cmdArgs
                newRun = PBRun(fullCmdLine)
                # At this point fullCmdLine looks like ["pbrun", "toolname", "--tool-args", etc...]
            fullCmdLine = self.initCmds + [self.basecmd] + self.cmdArgs
            if self.verbosity:
                print(" ".join(fullCmdLine))
                sys.stdout.flush()
            subprocess.check_call(fullCmdLine, env=self.environ)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            errorString = "\nCould not run %s" % self.basecmd
            if self.parentcmd is not None:
                errorString += " as part of %s" % self.parentcmd
            self.exitFunction(errorString)
        self.clearFunction()


def addSystemOptions(cmdline, pipelineArgs, addGPUOption=True):
    """
    @param cmdline: A list(str) that will become the command line. ['docker', 'run', '-v', etc...]
    @param pipelineArgs:  A PBRun object, containing system-level options (--logfile filename.log, --append, etc) to add to this command line.
    @param addGPUOption: If true, add '# of GPUs to use' option.

    For the error logger, pipelineArgs.logfile is the name of the log file.  If the name
    is empty then no log file is created and pinelineArgs.append is ignored.

    If we have a log file then pipelineArgs.append is set to False for the 1st PBTool
    in a pipeline and True for the rest of the PBTools in that pipeline.  If PB.pyx
    if given a log file but told NOT to append it will open the log file for overwrite
    in the 1st executable it runs (it runs one OR MORE executables for a give PBTool)
    and for append in all the rest.  Otherwise we'd only have to log output from the
    last executable run, not from all the executables that make up a given PBTool.
    """
    cmdline.extend(["--tmp-dir", pipelineArgs.tmp_dir])
    if addGPUOption:
        cmdline.extend(["--num-gpus", str(pipelineArgs.num_gpus)])
    if pipelineArgs.verbose is not None:
        cmdline.extend(["--verbose"])
    if pipelineArgs.x3 is not None:
        cmdline.extend(["--x3"])
    if pipelineArgs.with_petagene_dir is not None:
        cmdline.extend(["--with-petagene-dir", pipelineArgs.with_petagene_dir])
    # If --logfile is not specified or is the empty string, then the error logger will only
    # write to std::cerr.  Otherwise it will write to both std::cerr and the named file.
    # We need to open the log file for overwrite in the 1st stage of a pipeline and
    # for append on all subsequent stages.  For standalone it's always overwrite.
    if pipelineArgs.logfile is not None:
        cmdline.extend(["--logfile", pipelineArgs.logfile])
        if pipelineArgs.append:
            cmdline.extend(["--append"])
    if pipelineArgs.dev_mode == True:
        cmdline.extend(["--dev-mode"])



class germline(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)

        self.runCmds = []
        pipelineArgs = runArgs.runArgs
        alignmentCmd = ["--ref", pipelineArgs.ref]
        if pipelineArgs.in_se_fq is not None:
            pbutils.check_se_fastq_files(pipelineArgs.in_se_fq, pipelineArgs.read_group_sm, pipelineArgs.read_group_lb,
                                         pipelineArgs.read_group_pl, pipelineArgs.read_group_id_prefix)
            for fq_se in pipelineArgs.in_se_fq:
                alignmentCmd.extend(["--in-se-fq"] + fq_se)
        else:
            pbutils.check_fastq_files(pipelineArgs.in_fq, pipelineArgs.read_group_sm, pipelineArgs.read_group_lb,
                                      pipelineArgs.read_group_pl, pipelineArgs.read_group_id_prefix)
            for fq_pairs in pipelineArgs.in_fq:
                alignmentCmd.extend(["--in-fq"] + fq_pairs)

        if pipelineArgs.knownSites is not None:
            for knownSite in pipelineArgs.knownSites:
                alignmentCmd.extend(["--knownSites", knownSite])

        alignmentCmd.extend(["--out-bam", pipelineArgs.out_bam])

        if pipelineArgs.out_recal_file is not None:
            alignmentCmd.extend(["--out-recal-file", pipelineArgs.out_recal_file])

        if pipelineArgs.no_markdups:
            alignmentCmd.extend(["--no-markdups"])

        if pipelineArgs.markdups_single_ended_start_end == True:
            alignmentCmd.extend(["--markdups-single-ended-start-end"])

        if pipelineArgs.ignore_rg_markdups_single_ended == True:
            alignmentCmd.extend(["--ignore-rg-markdups-single-ended"])

        if pipelineArgs.out_duplicate_metrics is not None:
            alignmentCmd.extend(["--out-duplicate-metrics", pipelineArgs.out_duplicate_metrics])

        if pipelineArgs.optical_duplicate_pixel_distance is not None:
            alignmentCmd.extend(
                ["--optical-duplicate-pixel-distance", str(pipelineArgs.optical_duplicate_pixel_distance)])

        if pipelineArgs.no_warnings:
            alignmentCmd.extend(["--no-warnings"])

        alignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

        if hasattr(pipelineArgs, 'interval') and pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                alignmentCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                alignmentCmd.extend(["--interval-file", interval_file])

        if hasattr(pipelineArgs, 'interval_padding') and pipelineArgs.interval_padding is not None:
            alignmentCmd.extend(["--interval-padding", str(pipelineArgs.interval_padding)])

        if pipelineArgs.read_from_tmp_dir is not None:
            alignmentCmd.extend(["--keep-tmp"])
            alignmentCmd.extend(["--no-postsort"])

        if pipelineArgs.bwa_options is not None:
            alignmentCmd.extend(["--bwa-options=" + pipelineArgs.bwa_options])

        if pipelineArgs.gpuwrite is not None:
            alignmentCmd.extend(["--gpuwrite"])

        if pipelineArgs.gpusort is not None:
            alignmentCmd.extend(["--gpusort"])

        if pipelineArgs.low_memory is not None:
            alignmentCmd.extend(["--low-memory"])

        if pipelineArgs.filter_flag is not None:
            alignmentCmd.extend(["--filter-flag", str(pipelineArgs.filter_flag)])

        if pipelineArgs.skip_multiple_hits is not None:
            alignmentCmd.extend(["--skip-multiple-hits"])

        if pipelineArgs.align_only is not None:
            alignmentCmd.extend(["--align-only"])

        if pipelineArgs.num_cpu_threads_per_stage is not None:
            alignmentCmd.extend(["--num-cpu-threads-per-stage", str(pipelineArgs.num_cpu_threads_per_stage)])

        alignmentCmd.extend([
            "--bwa-nstreams", str(pipelineArgs.bwa_nstreams),
            "--bwa-cpu-thread-pool", str(pipelineArgs.bwa_cpu_thread_pool),
            "--bwa-primary-cpus", str(pipelineArgs.bwa_primary_cpus),
            "--max-read-length", str(pipelineArgs.max_read_length),
            "--min-read-length", str(pipelineArgs.min_read_length),
            "--bwa-normalized-queue-capacity", str(pipelineArgs.bwa_normalized_queue_capacity)
        ])

        #CIGAR on GPU
        if pipelineArgs.cigar_on_gpu is not None:
            alignmentCmd.extend(["--cigar-on-gpu"])
        # suppressed argument
        if pipelineArgs.use_swlib:
            alignmentCmd.append("--use-swlib")

        pipelineArgs.append = False
        addSystemOptions(alignmentCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("fq2bam", list(defaultCmdline), alignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                parentCmd="germline pipeline", verbosity=pipelineArgs.x3))

        htvcCmd = ["--ref", pipelineArgs.ref, "--in-bam", pipelineArgs.out_bam, "--out-variants",
                   pipelineArgs.out_variants, "--ploidy", str(pipelineArgs.ploidy), "--num-htvc-threads",
                   str(pipelineArgs.num_htvc_threads)]

        if pipelineArgs.haplotypecaller_options is not None:
            htvcCmd.extend(["--haplotypecaller-options=" + pipelineArgs.haplotypecaller_options])

        if pipelineArgs.out_recal_file is not None:
            htvcCmd.extend(["--in-recal-file", pipelineArgs.out_recal_file])

        if pipelineArgs.gvcf is not None:
            htvcCmd.extend(["--gvcf"])

        if pipelineArgs.disable_read_filter is not None:
            for disabled_filter in pipelineArgs.disable_read_filter:
                htvcCmd.extend(["--disable-read-filter", disabled_filter])

        if pipelineArgs.static_quantized_quals is not None:
            for qual in pipelineArgs.static_quantized_quals:
                htvcCmd.extend(["--static-quantized-quals", str(qual)])

        if hasattr(pipelineArgs, 'interval') and pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                htvcCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                htvcCmd.extend(["--interval-file", interval_file])

        if pipelineArgs.htvc_bam_output is not None:
            htvcCmd.extend(["--htvc-bam-output", pipelineArgs.htvc_bam_output])

        if hasattr(pipelineArgs, 'interval_padding') and pipelineArgs.interval_padding is not None:
            htvcCmd.extend(["--interval-padding", str(pipelineArgs.interval_padding)])

        if hasattr(pipelineArgs, 'exclude_intervals') and pipelineArgs.exclude_intervals is not None:
            for exclude_interval in pipelineArgs.exclude_intervals:
                htvcCmd.extend(["--exclude-intervals", exclude_interval])

        if pipelineArgs.max_alternate_alleles is not None:
            htvcCmd.extend(["--max-alternate-alleles", str(pipelineArgs.max_alternate_alleles)])

        if pipelineArgs.rna:
            htvcCmd.extend(["--rna"])

        if pipelineArgs.dont_use_soft_clipped_bases:
            htvcCmd.extend(["--dont-use-soft-clipped-bases"])

        if pipelineArgs.read_from_tmp_dir:
            htvcCmd.extend(["--read-from-tmp-dir"])
            #hacky way
            with open(pipelineArgs.out_bam, "w") as tmp_file:
                pass

        if pipelineArgs.annotation_group is not None:
            for group in pipelineArgs.annotation_group:
                htvcCmd.extend(["--annotation-group", group])

        if pipelineArgs.gvcf_gq_bands is not None:
            for band in pipelineArgs.gvcf_gq_bands:
                htvcCmd.extend(["--gvcf-gq-bands", str(band)])
        if pipelineArgs.run_partition:
            htvcCmd.extend(["--run-partition"])
        if pipelineArgs.no_alt_contigs:
            htvcCmd.extend(["--no-alt-contigs"])
        if pipelineArgs.gpu_num_per_partition is not None:
            htvcCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])

        if pipelineArgs.low_memory is not None or pipelineArgs.htvc_low_memory is not None:
            htvcCmd.extend(["--htvc-low-memory"]) 
        if pipelineArgs.minimum_mapping_quality != None:
            htvcCmd.extend(["--minimum-mapping-quality", str(pipelineArgs.minimum_mapping_quality)])
        if pipelineArgs.mapping_quality_threshold_for_genotyping != None:
            htvcCmd.extend(["--mapping-quality-threshold-for-genotyping", str(pipelineArgs.mapping_quality_threshold_for_genotyping)])
        if pipelineArgs.enable_dynamic_read_disqualification_for_genotyping == True:
            htvcCmd.extend(["--enable-dynamic-read-disqualification-for-genotyping"])
        if pipelineArgs.min_base_quality_score != None:
            htvcCmd.extend(["--min-base-quality-score", str(pipelineArgs.min_base_quality_score)])
        if pipelineArgs.adaptive_pruning != None:
            htvcCmd.extend(["--adaptive-pruning"])
        if pipelineArgs.htvc_alleles is not None:
            htvcCmd.extend(["--htvc-alleles", pipelineArgs.htvc_alleles])
        if pipelineArgs.force_call_filtered_alleles == True:
            htvcCmd.extend(["--force-call-filtered-alleles"])
        if pipelineArgs.filter_reads_too_long == True:
            htvcCmd.extend(["--filter-reads-too-long"])


        pipelineArgs.append = True
        addSystemOptions(htvcCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("haplotypecaller", list(defaultCmdline), htvcCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="germline pipeline", verbosity=pipelineArgs.x3, append=True))


#deepvariant germline doesn't include arguments for ultima
class deepvariant_germline(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)
        self.runCmds = []
        pipelineArgs = runArgs.runArgs

        # alignmentCmd = list(defaultCmdline)
        alignmentCmd = ["--ref", pipelineArgs.ref]
        if pipelineArgs.in_se_fq is not None:
            pbutils.check_se_fastq_files(pipelineArgs.in_se_fq, pipelineArgs.read_group_sm, pipelineArgs.read_group_lb,
                                         pipelineArgs.read_group_pl, pipelineArgs.read_group_id_prefix)
            for fq_se in pipelineArgs.in_se_fq:
                alignmentCmd.extend(["--in-se-fq"] + fq_se)
        else:
            pbutils.check_fastq_files(pipelineArgs.in_fq, pipelineArgs.read_group_sm, pipelineArgs.read_group_lb,
                                      pipelineArgs.read_group_pl, pipelineArgs.read_group_id_prefix)
            for fq_pairs in pipelineArgs.in_fq:
                alignmentCmd.extend(["--in-fq"] + fq_pairs)

        if pipelineArgs.knownSites is not None:
            for knownSite in pipelineArgs.knownSites:
                alignmentCmd.extend(["--knownSites", knownSite])

        alignmentCmd.extend(["--out-bam", pipelineArgs.out_bam])

        if pipelineArgs.out_recal_file is not None:
            alignmentCmd.extend(["--out-recal-file", pipelineArgs.out_recal_file])

        if pipelineArgs.no_markdups:
            alignmentCmd.extend(["--no-markdups"])

        if pipelineArgs.markdups_single_ended_start_end == True:
            alignmentCmd.extend(["--markdups-single-ended-start-end"])

        if pipelineArgs.ignore_rg_markdups_single_ended == True:
            alignmentCmd.extend(["--ignore-rg-markdups-single-ended"])

        if pipelineArgs.out_duplicate_metrics is not None:
            alignmentCmd.extend(["--out-duplicate-metrics", pipelineArgs.out_duplicate_metrics])

        if pipelineArgs.optical_duplicate_pixel_distance is not None:
            alignmentCmd.extend(
                ["--optical-duplicate-pixel-distance", str(pipelineArgs.optical_duplicate_pixel_distance)])

        if pipelineArgs.no_warnings:
            alignmentCmd.extend(["--no-warnings"])

        alignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

        if pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                alignmentCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                alignmentCmd.extend(["--interval-file", interval_file])

        if pipelineArgs.bwa_options is not None:
            alignmentCmd.extend(["--bwa-options=" + pipelineArgs.bwa_options])

        if pipelineArgs.gpuwrite is not None:
            alignmentCmd.extend(["--gpuwrite"])

        if pipelineArgs.gpusort is not None:
            alignmentCmd.extend(["--gpusort"])

        if pipelineArgs.low_memory is not None:
            alignmentCmd.extend(["--low-memory"])

        if pipelineArgs.filter_flag is not None:
            alignmentCmd.extend(["--filter-flag", str(pipelineArgs.filter_flag)])

        if pipelineArgs.skip_multiple_hits is not None:
            alignmentCmd.extend(["--skip-multiple-hits"])

        if pipelineArgs.read_from_tmp_dir is not None:
            alignmentCmd.extend(["--keep-tmp"])
            alignmentCmd.extend(["--no-postsort"])
        
        if pipelineArgs.num_cpu_threads_per_stage is not None:
            alignmentCmd.extend(["--num-cpu-threads-per-stage", str(pipelineArgs.num_cpu_threads_per_stage)])

        alignmentCmd.extend([
            "--bwa-nstreams", str(pipelineArgs.bwa_nstreams),
            "--bwa-cpu-thread-pool", str(pipelineArgs.bwa_cpu_thread_pool),
            "--bwa-primary-cpus", str(pipelineArgs.bwa_primary_cpus),
            "--max-read-length", str(pipelineArgs.max_read_length),
            "--min-read-length", str(pipelineArgs.min_read_length),
            "--bwa-normalized-queue-capacity", str(pipelineArgs.bwa_normalized_queue_capacity)
        ])
        #CIGAR on GPU
        if pipelineArgs.cigar_on_gpu is not None:
            alignmentCmd.extend(["--cigar-on-gpu"])

        # suppressed argument
        if pipelineArgs.use_swlib:
            alignmentCmd.append("--use-swlib")


        pipelineArgs.append = False
        addSystemOptions(alignmentCmd, pipelineArgs)
        #if pipelineArgs.fq2bam:
        self.runCmds.append(
            PBTool("fq2bam", list(defaultCmdline), alignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                parentCmd="deepvariant_germline pipeline", verbosity=pipelineArgs.x3))

        # deepvariant
        deepvarCmd = ["--ref", pipelineArgs.ref]
        deepvarCmd.extend(["--in-bam", pipelineArgs.out_bam])

        if pipelineArgs.pb_model_file is not None:
            deepvarCmd.extend(["--pb-model-file", pipelineArgs.pb_model_file])

        if pipelineArgs.enable_small_model == True:
            deepvarCmd.extend(["--enable-small-model"])

        if pipelineArgs.pb_small_model_file is not None:
            deepvarCmd.extend(["--pb-small-model-file", pipelineArgs.pb_small_model_file])

        if pipelineArgs.use_tf32 == True:
            deepvarCmd.extend(["--use-tf32"])

        if pipelineArgs.gvcf:
            deepvarCmd.extend(["--gvcf"])

        if pipelineArgs.disable_use_window_selector_model:
            deepvarCmd.extend(["--disable-use-window-selector-model"])

        if pipelineArgs.interval is not None and len(pipelineArgs.interval) > 0:
            for interval in pipelineArgs.interval:
                deepvarCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None and len(pipelineArgs.interval_file) > 0:
            for interval_file in pipelineArgs.interval_file:
                deepvarCmd.extend(["--interval-file", interval_file])

            # New things from DV1.0
        if pipelineArgs.mode is not None:
            deepvarCmd.extend(["--mode", pipelineArgs.mode])
        if pipelineArgs.keep_legacy_allele_counter_behavior == True:
            deepvarCmd.extend(["--keep-legacy-allele-counter-behavior"])
        if pipelineArgs.keep_duplicates is not None:
            deepvarCmd.extend(["--keep-duplicates"])
        if pipelineArgs.sort_by_haplotypes:
            deepvarCmd.extend(["--sort-by-haplotypes"])
        if pipelineArgs.add_hp_channel:
            deepvarCmd.extend(["--add-hp-channel"])
        if pipelineArgs.parse_sam_aux_fields:
            deepvarCmd.extend(["--parse-sam-aux-fields"])
        if pipelineArgs.norealign_reads:
            deepvarCmd.extend(["--norealign-reads"])
        if pipelineArgs.vsc_min_fraction_indels is not None:
            deepvarCmd.extend(["--vsc-min-fraction-indels", str(pipelineArgs.vsc_min_fraction_indels)])
        deepvarCmd.extend(["--vsc-min-count-snps", str(pipelineArgs.vsc_min_count_snps), "--vsc-min-count-indels",
                           str(pipelineArgs.vsc_min_count_indels)])
        deepvarCmd.extend(["--vsc-min-fraction-snps", str(pipelineArgs.vsc_min_fraction_snps)])
        deepvarCmd.extend(["--min-mapping-quality", str(pipelineArgs.min_mapping_quality), "--min-base-quality",
                           str(pipelineArgs.min_base_quality)])
        if pipelineArgs.alt_aligned_pileup is not None:
            deepvarCmd.extend(["--alt-aligned-pileup", str(pipelineArgs.alt_aligned_pileup)])
        if pipelineArgs.variant_caller is not None:
            deepvarCmd.extend(["--variant-caller", str(pipelineArgs.variant_caller)])
        if pipelineArgs.proposed_variants is not None:
            deepvarCmd.extend(["--proposed-variants", pipelineArgs.proposed_variants])
        if pipelineArgs.use_wes_model is not None:
            deepvarCmd.extend(["--use-wes-model"])
        if pipelineArgs.max_read_size_512:
            deepvarCmd.extend(["--max-read-size-512"])
        if pipelineArgs.prealign_helper_thread:
            deepvarCmd.extend(["--prealign_helper_thread"])

        if pipelineArgs.track_ref_reads:
            deepvarCmd.extend(["--track-ref-reads"])
        if pipelineArgs.phase_reads:
            deepvarCmd.extend(['--phase-reads'])
        if pipelineArgs.include_med_dp:
            deepvarCmd.extend(["--include-med-dp"])
        if pipelineArgs.normalize_reads:
            deepvarCmd.extend(["--normalize-reads"])
        if pipelineArgs.pileup_image_width is not None:
            deepvarCmd.extend(["--pileup-image-width", str(pipelineArgs.pileup_image_width)])
        if pipelineArgs.channel_insert_size:
            deepvarCmd.extend(["--channel-insert-size"])
        if pipelineArgs.no_channel_insert_size:
            deepvarCmd.extend(["--no-channel-insert-size"])
        if pipelineArgs.disable_group_variants:
            deepvarCmd.extend(["--disable-group-variants"])
        if pipelineArgs.filter_reads_too_long:
            deepvarCmd.extend(["--filter-reads-too-long"])
        if pipelineArgs.haploid_contigs is not None:
            deepvarCmd.extend(["--haploid-contigs", pipelineArgs.haploid_contigs])

        if pipelineArgs.run_partition:
            deepvarCmd.extend(["--run-partition"])

        if pipelineArgs.gpu_num_per_partition is not None:
            deepvarCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])

        deepvarCmd.extend(["--num-cpu-threads-per-stream", str(pipelineArgs.num_cpu_threads_per_stream)])
        deepvarCmd.extend(["--num-streams-per-gpu", str(pipelineArgs.num_streams_per_gpu)])

        deepvarCmd.extend(["--out-variants", pipelineArgs.out_variants])
        if pipelineArgs.read_from_tmp_dir:
            deepvarCmd.extend(["--read-from-tmp-dir"])
            #hacky way
            with open(pipelineArgs.out_bam, "w") as tmp_file:
                pass

        pipelineArgs.append = True
        addSystemOptions(deepvarCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("deepvariant", list(defaultCmdline), deepvarCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="deepvariant_germline pipeline", verbosity=pipelineArgs.x3))


def _run_verify_step(pipelineArgs):
    """Invoke pbgiraffe_verify binary directly to check reference FASTA
    consistency against the GBZ graph before alignment begins."""
    wrapper_dir = os.path.dirname(os.path.realpath(__file__))
    if not getattr(pipelineArgs, 'dev_mode', False):
        installDir = os.path.join(wrapper_dir, "binaries")
    else:
        installDir = os.path.realpath(os.path.join(wrapper_dir, "..", "..", "binaries"))

    num_threads = getattr(pipelineArgs, 'num_cpu_threads_per_gpu', 16) * getattr(pipelineArgs, 'num_gpus', 1)
    verifyCmd = [os.path.join(installDir, "bin", "pbgiraffe_verify"),
                 "--gbz-name", pipelineArgs.gbz_name,
                 "--ref", pipelineArgs.ref,
                 "--ref-paths", pipelineArgs.ref_paths,
                 "--num-threads", str(num_threads), "--progress"]
    AddLogfile(verifyCmd, pipelineArgs)
    myEnv = SetUpEnv(verifyCmd, installDir,
                     lib_paths=[installDir + "/giraffe_libs"],
                     petaGenePath=None,
                     printCmd=getattr(pipelineArgs, 'x3', False))

    try:
        retVal = subprocess.call(verifyCmd, env=myEnv, shell=False)
        if retVal != 0:
            print("\nReference verification failed (exit code %d). "
                  "Remove --run-ref-verification to bypass this check. "
                  "The resulting variants may be incorrect and the run may fail. "
                  "See message above for details on how to fix the issue." % retVal)

            pbutils.pbExit(retVal)
    except (subprocess.CalledProcessError, KeyboardInterrupt, OSError) as e:
        print("\nCould not run pbgiraffe_verify as part of pangenome_germline pipeline: %s" % str(e))
        pbutils.pbExit(-1)


class pangenome_germline(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)
        self.runCmds = []
        pipelineArgs = runArgs.runArgs

        # Step 0: Verify reference FASTA consistency against GBZ graph
        if getattr(pipelineArgs, 'run_ref_verification', False):
            _run_verify_step(pipelineArgs)

        # Step 1: Giraffe (pangenome alignment to BAM)
        alignmentCmd = ["--gbz-name", pipelineArgs.gbz_name, "--dist-name", pipelineArgs.dist_name,
                        "--minimizer-name", pipelineArgs.minimizer_name, "--zipcodes-name", pipelineArgs.zipcodes_name,
                        "--ref-paths", pipelineArgs.ref_paths, "--out-bam", pipelineArgs.out_bam]
        if getattr(pipelineArgs, 'xg_name', None) is not None:
            alignmentCmd.extend(["--xg-name", pipelineArgs.xg_name])
        if pipelineArgs.in_se_fq is not None and len(pipelineArgs.in_se_fq) > 0:
            alignmentCmd.extend(["--in-se-fq"] + pipelineArgs.in_se_fq[0])
        elif pipelineArgs.in_fq is not None and len(pipelineArgs.in_fq) > 0:
            alignmentCmd.extend(["--in-fq"] + pipelineArgs.in_fq[0])
        if pipelineArgs.in_fq_list is not None:
            alignmentCmd.extend(["--in-fq-list", pipelineArgs.in_fq_list])
        if pipelineArgs.in_se_fq_list is not None:
            alignmentCmd.extend(["--in-se-fq-list", pipelineArgs.in_se_fq_list])
        if pipelineArgs.sample is not None:
            alignmentCmd.extend(["--sample", pipelineArgs.sample])
        if pipelineArgs.read_group is not None:
            alignmentCmd.extend(["--read-group", pipelineArgs.read_group])
        if pipelineArgs.read_group_library is not None:
            alignmentCmd.extend(["--read-group-library", pipelineArgs.read_group_library])
        if pipelineArgs.read_group_platform is not None:
            alignmentCmd.extend(["--read-group-platform", pipelineArgs.read_group_platform])
        if pipelineArgs.read_group_pu is not None:
            alignmentCmd.extend(["--read-group-pu", pipelineArgs.read_group_pu])
        if getattr(pipelineArgs, 'prune_low_cplx', None):
            alignmentCmd.append("--prune-low-cplx")
        if getattr(pipelineArgs, 'max_fragment_length', None) is not None:
            alignmentCmd.extend(["--max-fragment-length", str(pipelineArgs.max_fragment_length)])
        if getattr(pipelineArgs, 'fragment_mean', None) is not None:
            alignmentCmd.extend(["--fragment-mean", str(pipelineArgs.fragment_mean)])
        if getattr(pipelineArgs, 'fragment_stdev', None) is not None:
            alignmentCmd.extend(["--fragment-stdev", str(pipelineArgs.fragment_stdev)])
        if getattr(pipelineArgs, 'align_only', None):
            alignmentCmd.append("--align-only")
        if getattr(pipelineArgs, 'copy_comment', None):
            alignmentCmd.append("--copy-comment")
        if getattr(pipelineArgs, 'no_markdups', None):
            alignmentCmd.append("--no-markdups")
        if getattr(pipelineArgs, 'markdups_single_ended_start_end', None):
            alignmentCmd.append("--markdups-single-ended-start-end")
        if getattr(pipelineArgs, 'ignore_rg_markdups_single_ended', None):
            alignmentCmd.append("--ignore-rg-markdups-single-ended")
        if getattr(pipelineArgs, 'markdups_assume_sortorder_queryname', None):
            alignmentCmd.append("--markdups-assume-sortorder-queryname")
        if getattr(pipelineArgs, 'markdups_picard_version_2182', None):
            alignmentCmd.append("--markdups-picard-version-2182")
        if getattr(pipelineArgs, 'optical_duplicate_pixel_distance', None) is not None:
            alignmentCmd.extend(["--optical-duplicate-pixel-distance", str(pipelineArgs.optical_duplicate_pixel_distance)])
        if getattr(pipelineArgs, 'monitor_usage', None):
            alignmentCmd.append("--monitor-usage")
        if getattr(pipelineArgs, 'min_read_length', None) is not None:
            alignmentCmd.extend(["--min-read-length", str(pipelineArgs.min_read_length)])
        if getattr(pipelineArgs, 'max_read_length', None) is not None:
            alignmentCmd.extend(["--max-read-length", str(pipelineArgs.max_read_length)])
        if getattr(pipelineArgs, 'minimizers_gpu', None):
            alignmentCmd.append("--minimizers-gpu")
        if getattr(pipelineArgs, 'low_memory', None):
            alignmentCmd.append("--low-memory")
        if getattr(pipelineArgs, 'num_primary_cpus_per_gpu', None) is not None:
            alignmentCmd.extend(["--num-primary-cpus-per-gpu", str(pipelineArgs.num_primary_cpus_per_gpu)])
        if getattr(pipelineArgs, 'num_cpu_threads_per_gpu', None) is not None:
            alignmentCmd.extend(["--num-cpu-threads-per-gpu", str(pipelineArgs.num_cpu_threads_per_gpu)])
        if getattr(pipelineArgs, 'nstreams', None) is not None:
            alignmentCmd.extend(["--nstreams", str(pipelineArgs.nstreams)])
        if getattr(pipelineArgs, 'batch_size', None) is not None:
            alignmentCmd.extend(["--batch-size", str(pipelineArgs.batch_size)])
        if getattr(pipelineArgs, 'write_threads', None) is not None:
            alignmentCmd.extend(["--write-threads", str(pipelineArgs.write_threads)])
        if getattr(pipelineArgs, 'memory_limit', None) is not None:
            alignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])
        if getattr(pipelineArgs, 'gpusort', None):
            alignmentCmd.append("--gpusort")
        if getattr(pipelineArgs, 'gpuwrite', None):
            alignmentCmd.append("--gpuwrite")
        if getattr(pipelineArgs, 'gpuwrite_deflate_algo', None) is not None:
            alignmentCmd.extend(["--gpuwrite-deflate-algo", str(pipelineArgs.gpuwrite_deflate_algo)])
        if getattr(pipelineArgs, 'use_gds', None):
            alignmentCmd.append("--use-gds")
        if getattr(pipelineArgs, 'work_queue_capacity', None) is not None:
            alignmentCmd.extend(["--work-queue-capacity", str(pipelineArgs.work_queue_capacity)])
        if getattr(pipelineArgs, 'testing_options', None) is not None:
            alignmentCmd.extend(["--testing-options", str(pipelineArgs.testing_options)])
            
        pipelineArgs.append = False
        addSystemOptions(alignmentCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("giraffe", list(defaultCmdline), alignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="pangenome_germline pipeline", verbosity=pipelineArgs.x3))

        # Step 2: Pangenome-aware DeepVariant (BAM to VCF)
        deepvarCmd = ["--ref", pipelineArgs.ref, "--in-bam", pipelineArgs.out_bam,
                      "--out-variants", pipelineArgs.out_variants,
                      "--pangenome", pipelineArgs.gbz_name]
        if getattr(pipelineArgs, 'pb_model_file', None) is not None:
            deepvarCmd.extend(["--pb-model-file", pipelineArgs.pb_model_file])
        # if getattr(pipelineArgs, 'mode', None) is not None: # Giraffe only supports shortread mode
        #     deepvarCmd.extend(["--mode", pipelineArgs.mode])
        if getattr(pipelineArgs, 'disable_use_window_selector_model', None):
            deepvarCmd.append("--disable-use-window-selector-model")
        if getattr(pipelineArgs, 'norealign_reads', None):
            deepvarCmd.append("--norealign-reads")
        if getattr(pipelineArgs, 'min_mapping_quality', None) is not None:
            deepvarCmd.extend(["--min-mapping-quality", str(pipelineArgs.min_mapping_quality)])
        if getattr(pipelineArgs, 'pileup_image_width', None) is not None:
            deepvarCmd.extend(["--pileup-image-width", str(pipelineArgs.pileup_image_width)])
        if getattr(pipelineArgs, 'no_channel_insert_size', None):
            deepvarCmd.append("--no-channel-insert-size")
        if getattr(pipelineArgs, 'sample_name_pangenome', None) is not None:
            deepvarCmd.extend(["--sample-name-pangenome", pipelineArgs.sample_name_pangenome])
        if getattr(pipelineArgs, 'ref_name_pangenome', None) is not None:
            deepvarCmd.extend(["--ref-name-pangenome", pipelineArgs.ref_name_pangenome])
        if getattr(pipelineArgs, 'interval', None) is not None and len(pipelineArgs.interval) > 0:
            for interval in pipelineArgs.interval:
                deepvarCmd.extend(["--interval", interval])
        if getattr(pipelineArgs, 'interval_file', None) is not None and len(pipelineArgs.interval_file) > 0:
            for interval_file in pipelineArgs.interval_file:
                deepvarCmd.extend(["--interval-file", interval_file])
        if getattr(pipelineArgs, 'run_partition', None):
            deepvarCmd.append("--run-partition")
        if getattr(pipelineArgs, 'gpu_num_per_partition', None) is not None:
            deepvarCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])
        deepvarCmd.extend(["--num-cpu-threads-per-stream", str(getattr(pipelineArgs, 'num_cpu_threads_per_stream', 6))])
        deepvarCmd.extend(["--num-streams-per-gpu", str(getattr(pipelineArgs, 'num_streams_per_gpu', 'auto'))])

        pipelineArgs.append = True
        addSystemOptions(deepvarCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("pangenome_aware_deepvariant", list(defaultCmdline), deepvarCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="pangenome_germline pipeline", verbosity=pipelineArgs.x3))

        # If verification was not run, attach a hint to every step so that
        # the user is informed about --run-ref-verification on failure.
        if not getattr(pipelineArgs, 'run_ref_verification', False):
            hint = ("Note: This error may be caused by an inconsistent reference FASTA. "
                    "Re-run with --run-ref-verification to check that the reference "
                    "matches the GBZ graph.")
            for cmd in self.runCmds:
                cmd.errorHint = hint


class pacbio_germline(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)
        self.runCmds = []
        pipelineArgs = runArgs.runArgs

        alignmentCmd = ["--ref", pipelineArgs.ref]

        if pipelineArgs.index is not None:
            alignmentCmd.extend(["--index", pipelineArgs.index])

        if pipelineArgs.in_bam is not None:
            alignmentCmd.extend(["--in-bam", pipelineArgs.in_bam[0]])
        else:
            for idx in range(0, len(pipelineArgs.in_fq) - 1):
                alignmentCmd.extend(["--in-fq", pipelineArgs.in_fq[idx]])

        if pipelineArgs.jump_bed is not None:
            alignmentCmd.extend(["--jump-bed", pipelineArgs.jump_bed])

        if pipelineArgs.junc_bed is not None:
            alignmentCmd.extend(["--junc-bed", pipelineArgs.junc_bed])

        if pipelineArgs.knownSites is not None:
            for knownSite in pipelineArgs.knownSites:
                alignmentCmd.extend(["--knownSites", knownSite])

        alignmentCmd.extend(["--out-bam", pipelineArgs.out_bam])

        if pipelineArgs.out_recal_file is not None:
            alignmentCmd.extend(["--out-recal-file", pipelineArgs.out_recal_file])

        # if pipelineArgs.out_duplicate_metrics is not None:
        #     alignmentCmd.extend(["--out-duplicate-metrics", pipelineArgs.out_duplicate_metrics])

        if pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                alignmentCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                alignmentCmd.extend(["--interval-file", interval_file])

        alignmentCmd.extend(["--preset", pipelineArgs.preset])

        if pipelineArgs.pbmm2 is not None:
            alignmentCmd.extend(["--pbmm2"])
            if pipelineArgs.pbmm2_unmapped is not None:
                alignmentCmd.extend(["--pbmm2-unmapped"])

        if pipelineArgs.minimizer_kmer_len is not None:
            alignmentCmd.extend(["--minimizer-kmer-len", str(pipelineArgs.minimizer_kmer_len)])

        if pipelineArgs.both_strands is not None:
            alignmentCmd.extend(["--both-strands"])

        if pipelineArgs.forward_transcript_strand is not None:
            alignmentCmd.extend(["--forward-transcript-strand"])

        if pipelineArgs.md is not None:
            alignmentCmd.extend(["--md"])

        if pipelineArgs.copy_comment is not None:
            alignmentCmd.extend(["--copy-comment"])

        if pipelineArgs.eqx is not None:
            alignmentCmd.extend(["--eqx"])

        alignmentCmd.extend(["--num-threads", str(pipelineArgs.num_threads)])

        if pipelineArgs.gpuwrite is not None:
            alignmentCmd.extend(["--gpuwrite"])

        if pipelineArgs.gpuwrite_deflate_algo is not None:
            alignmentCmd.extend(["--gpuwrite-deflate-algo", str(pipelineArgs.gpuwrite_deflate_algo)])

        if pipelineArgs.gpusort is not None:
            alignmentCmd.extend(["--gpusort"])

        if pipelineArgs.use_gds is not None:
            alignmentCmd.extend(["--use-gds"])

        alignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

        if pipelineArgs.low_memory is not None:
            alignmentCmd.extend(["--low-memory"])

        alignmentCmd.extend(["--no-markdups"]) #force --no-markdups to prevent sort crash
        # if pipelineArgs.no_markdups is not None:
        #     alignmentCmd.extend(["--no-markdups"])

        # if pipelineArgs.markdups_assume_sortorder_queryname is not None:
        #     alignmentCmd.extend(["--markdups-assume-sortorder-queryname"])

        # if pipelineArgs.optical_duplicate_pixel_distance is not None:
        #     alignmentCmd.extend(["--optical-duplicate-pixel-distance", str(pipelineArgs.optical_duplicate_pixel_distance)])

        alignmentCmd.extend(["--chunk-size", str(pipelineArgs.chunk_size)])

        alignmentCmd.extend(["--mem-pool-buf-size", str(pipelineArgs.mem_pool_buf_size)])

        alignmentCmd.extend(["--free-queue-batch-size", str(pipelineArgs.free_queue_batch_size)])

        if pipelineArgs.max_queue_chunks is not None:
            alignmentCmd.extend(["--max-queue-chunks", str(pipelineArgs.max_queue_chunks)])

        alignmentCmd.extend(["--max-queue-reads", str(pipelineArgs.max_queue_reads)])

        if pipelineArgs.nstreams is not None:
            alignmentCmd.extend(["--nstreams", str(pipelineArgs.nstreams)])

        if pipelineArgs.num_alignment_workers_per_thread is not None:
            alignmentCmd.extend(["--num-alignment-workers-per-thread", str(pipelineArgs.num_alignment_workers_per_thread)])

        if pipelineArgs.alignment_thread_num_divisor is not None:
            alignmentCmd.extend(["--alignment-thread-num-divisor", str(pipelineArgs.alignment_thread_num_divisor)])

        if pipelineArgs.alignment_large_pair_size is not None:
            alignmentCmd.extend(["--alignment-large-pair-size", str(pipelineArgs.alignment_large_pair_size)])

        if pipelineArgs.alignment_midsize_pair_size is not None:
            alignmentCmd.extend(["--alignment-midsize-pair-size", str(pipelineArgs.alignment_midsize_pair_size)])

        if pipelineArgs.process_large_alignments_on_gpu is not None:
            alignmentCmd.extend(["--process-large-alignments-on-gpu"])

        if pipelineArgs.no_balancing_large_alignments is not None:
            alignmentCmd.extend(["--no-balancing-large-alignments"])

        if pipelineArgs.process_all_alignments_on_cpu_threshold is not None:
            alignmentCmd.extend(["--process-all-alignments-on-cpu-threshold", str(pipelineArgs.process_all_alignments_on_cpu_threshold)])

        if pipelineArgs.num_alignment_device_mem_buffers is not None:
            alignmentCmd.extend(["--num-alignment-device-mem-buffers", str(pipelineArgs.num_alignment_device_mem_buffers)])

        if pipelineArgs.alignment_on_cpu is not None:
            alignmentCmd.extend(["--alignment-on-cpu"])

        if pipelineArgs.read_from_tmp_dir is not None:
            alignmentCmd.extend(["--keep-tmp"])
            alignmentCmd.extend(["--no-postsort"])

        pipelineArgs.append = False
        addSystemOptions(alignmentCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("minimap2", list(defaultCmdline), alignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="pacbio_germline pipeline", verbosity=pipelineArgs.x3))

        # deepvariant
        deepvarCmd = ["--ref", pipelineArgs.ref]
        deepvarCmd.extend(["--in-bam", pipelineArgs.out_bam])

        if pipelineArgs.pb_model_file is not None:
            deepvarCmd.extend(["--pb-model-file", pipelineArgs.pb_model_file])
        
        if pipelineArgs.enable_small_model == True:
            deepvarCmd.extend(["--enable-small-model"])
        
        if pipelineArgs.pb_small_model_file is not None:
            deepvarCmd.extend(["--pb-small-model-file", pipelineArgs.pb_small_model_file])
        
        if pipelineArgs.use_tf32 == True:
            deepvarCmd.extend(["--use-tf32"])
        
        if pipelineArgs.gvcf:
            deepvarCmd.extend(["--gvcf"])

        if pipelineArgs.disable_use_window_selector_model:
            deepvarCmd.extend(["--disable-use-window-selector-model"])

        if pipelineArgs.interval is not None and len(pipelineArgs.interval) > 0:
            for interval in pipelineArgs.interval:
                deepvarCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None and len(pipelineArgs.interval_file) > 0:
            for interval_file in pipelineArgs.interval_file:
                deepvarCmd.extend(["--interval-file", interval_file])

        # New things from DV1.0
        deepvarCmd.extend(["--mode", "pacbio"])
        if pipelineArgs.keep_duplicates is not None:
            deepvarCmd.extend(["--keep-duplicates"])
        if pipelineArgs.sort_by_haplotypes:
            deepvarCmd.extend(["--sort-by-haplotypes"])
        if pipelineArgs.add_hp_channel:
            deepvarCmd.extend(["--add-hp-channel"])
        if pipelineArgs.parse_sam_aux_fields:
            deepvarCmd.extend(["--parse-sam-aux-fields"])
        if pipelineArgs.norealign_reads:
            deepvarCmd.extend(["--norealign-reads"])
        if pipelineArgs.vsc_min_fraction_indels is not None:
            deepvarCmd.extend(["--vsc-min-fraction-indels", str(pipelineArgs.vsc_min_fraction_indels)])
        deepvarCmd.extend(["--vsc-min-count-snps", str(pipelineArgs.vsc_min_count_snps), "--vsc-min-count-indels",
                           str(pipelineArgs.vsc_min_count_indels)])
        deepvarCmd.extend(["--vsc-min-fraction-snps", str(pipelineArgs.vsc_min_fraction_snps)])
        deepvarCmd.extend(["--min-mapping-quality", str(pipelineArgs.min_mapping_quality), "--min-base-quality",
                           str(pipelineArgs.min_base_quality)])
        if pipelineArgs.alt_aligned_pileup is not None:
            deepvarCmd.extend(["--alt-aligned-pileup", str(pipelineArgs.alt_aligned_pileup)])
        if pipelineArgs.variant_caller is not None:
            deepvarCmd.extend(["--variant-caller", str(pipelineArgs.variant_caller)])
        if pipelineArgs.proposed_variants is not None:
            deepvarCmd.extend(["--proposed-variants", pipelineArgs.proposed_variants])
        if pipelineArgs.use_wes_model is not None:
            deepvarCmd.extend(["--use-wes-model"])
        if pipelineArgs.max_read_size_512:
            deepvarCmd.extend(["--max-read-size-512"])
        if pipelineArgs.prealign_helper_thread:
            deepvarCmd.extend(["--prealign_helper_thread"])

        if pipelineArgs.track_ref_reads:
            deepvarCmd.extend(["--track-ref-reads"])
        if pipelineArgs.phase_reads:
            deepvarCmd.extend(['--phase-reads'])
        if pipelineArgs.include_med_dp:
            deepvarCmd.extend(["--include-med-dp"])
        if pipelineArgs.normalize_reads:
            deepvarCmd.extend(["--normalize-reads"])
        if pipelineArgs.pileup_image_width is not None:
            deepvarCmd.extend(["--pileup-image-width", str(pipelineArgs.pileup_image_width)])
        if pipelineArgs.channel_insert_size:
            deepvarCmd.extend(["--channel-insert-size"])
        if pipelineArgs.no_channel_insert_size:
            deepvarCmd.extend(["--no-channel-insert-size"])
        if pipelineArgs.disable_group_variants:
            deepvarCmd.extend(["--disable-group-variants"])
        if pipelineArgs.filter_reads_too_long:
            deepvarCmd.extend(["--filter-reads-too-long"])
        if pipelineArgs.haploid_contigs is not None:
            deepvarCmd.extend(["--haploid-contigs", pipelineArgs.haploid_contigs])

        if pipelineArgs.run_partition:
            deepvarCmd.extend(["--run-partition"])

        if pipelineArgs.gpu_num_per_partition is not None:
            deepvarCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])

        deepvarCmd.extend(["--num-cpu-threads-per-stream", str(pipelineArgs.num_cpu_threads_per_stream)])
        deepvarCmd.extend(["--num-streams-per-gpu", str(pipelineArgs.num_streams_per_gpu)])

        deepvarCmd.extend(["--out-variants", pipelineArgs.out_variants])
        if pipelineArgs.read_from_tmp_dir:
            deepvarCmd.extend(["--read-from-tmp-dir"])
            #hacky way
            with open(pipelineArgs.out_bam, "w") as tmp_file:
                pass

        pipelineArgs.append = True
        addSystemOptions(deepvarCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("deepvariant", list(defaultCmdline), deepvarCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="pacbio_germline pipeline", verbosity=pipelineArgs.x3))

class ont_germline(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)
        self.runCmds = []
        pipelineArgs = runArgs.runArgs

        alignmentCmd = ["--ref", pipelineArgs.ref]

        if pipelineArgs.index is not None:
            alignmentCmd.extend(["--index", pipelineArgs.index])

        if pipelineArgs.in_bam is not None:
            alignmentCmd.extend(["--in-bam", pipelineArgs.in_bam[0]])
        else:
            for idx in range(0, len(pipelineArgs.in_fq) - 1):
                alignmentCmd.extend(["--in-fq", pipelineArgs.in_fq[idx]])

        if pipelineArgs.jump_bed is not None:
            alignmentCmd.extend(["--jump-bed", pipelineArgs.jump_bed])

        if pipelineArgs.junc_bed is not None:
            alignmentCmd.extend(["--junc-bed", pipelineArgs.junc_bed])

        if pipelineArgs.knownSites is not None:
            for knownSite in pipelineArgs.knownSites:
                alignmentCmd.extend(["--knownSites", knownSite])

        alignmentCmd.extend(["--out-bam", pipelineArgs.out_bam])

        if pipelineArgs.out_recal_file is not None:
            alignmentCmd.extend(["--out-recal-file", pipelineArgs.out_recal_file])

        # if pipelineArgs.out_duplicate_metrics is not None:
        #     alignmentCmd.extend(["--out-duplicate-metrics", pipelineArgs.out_duplicate_metrics])

        if pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                alignmentCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                alignmentCmd.extend(["--interval-file", interval_file])

        alignmentCmd.extend(["--preset", pipelineArgs.preset])

        if pipelineArgs.pbmm2 is not None:
            alignmentCmd.extend(["--pbmm2"])
            if pipelineArgs.pbmm2_unmapped is not None:
                alignmentCmd.extend(["--pbmm2-unmapped"])

        if pipelineArgs.minimizer_kmer_len is not None:
            alignmentCmd.extend(["--minimizer-kmer-len", str(pipelineArgs.minimizer_kmer_len)])

        if pipelineArgs.both_strands is not None:
            alignmentCmd.extend(["--both-strands"])

        if pipelineArgs.forward_transcript_strand is not None:
            alignmentCmd.extend(["--forward-transcript-strand"])

        if pipelineArgs.md is not None:
            alignmentCmd.extend(["--md"])

        if pipelineArgs.copy_comment is not None:
            alignmentCmd.extend(["--copy-comment"])

        if pipelineArgs.eqx is not None:
            alignmentCmd.extend(["--eqx"])

        alignmentCmd.extend(["--num-threads", str(pipelineArgs.num_threads)])

        if pipelineArgs.gpuwrite is not None:
            alignmentCmd.extend(["--gpuwrite"])

        if pipelineArgs.gpuwrite_deflate_algo is not None:
            alignmentCmd.extend(["--gpuwrite-deflate-algo", str(pipelineArgs.gpuwrite_deflate_algo)])

        if pipelineArgs.gpusort is not None:
            alignmentCmd.extend(["--gpusort"])

        if pipelineArgs.use_gds is not None:
            alignmentCmd.extend(["--use-gds"])

        alignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

        if pipelineArgs.low_memory is not None:
            alignmentCmd.extend(["--low-memory"])

        alignmentCmd.extend(["--no-markdups"]) #force --no-markdups to prevent sort crash
        # if pipelineArgs.no_markdups is not None:
        #     alignmentCmd.extend(["--no-markdups"])

        # if pipelineArgs.markdups_assume_sortorder_queryname is not None:
        #     alignmentCmd.extend(["--markdups-assume-sortorder-queryname"])

        # if pipelineArgs.optical_duplicate_pixel_distance is not None:
        #     alignmentCmd.extend(["--optical-duplicate-pixel-distance", str(pipelineArgs.optical_duplicate_pixel_distance)])

        alignmentCmd.extend(["--chunk-size", str(pipelineArgs.chunk_size)])

        alignmentCmd.extend(["--mem-pool-buf-size", str(pipelineArgs.mem_pool_buf_size)])

        alignmentCmd.extend(["--free-queue-batch-size", str(pipelineArgs.free_queue_batch_size)])

        if pipelineArgs.max_queue_chunks is not None:
            alignmentCmd.extend(["--max-queue-chunks", str(pipelineArgs.max_queue_chunks)])

        alignmentCmd.extend(["--max-queue-reads", str(pipelineArgs.max_queue_reads)])

        if pipelineArgs.nstreams is not None:
            alignmentCmd.extend(["--nstreams", str(pipelineArgs.nstreams)])

        if pipelineArgs.num_alignment_workers_per_thread is not None:
            alignmentCmd.extend(["--num-alignment-workers-per-thread", str(pipelineArgs.num_alignment_workers_per_thread)])

        if pipelineArgs.alignment_thread_num_divisor is not None:
            alignmentCmd.extend(["--alignment-thread-num-divisor", str(pipelineArgs.alignment_thread_num_divisor)])

        if pipelineArgs.alignment_large_pair_size is not None:
            alignmentCmd.extend(["--alignment-large-pair-size", str(pipelineArgs.alignment_large_pair_size)])

        if pipelineArgs.alignment_midsize_pair_size is not None:
            alignmentCmd.extend(["--alignment-midsize-pair-size", str(pipelineArgs.alignment_midsize_pair_size)])

        if pipelineArgs.process_large_alignments_on_gpu is not None:
            alignmentCmd.extend(["--process-large-alignments-on-gpu"])

        if pipelineArgs.no_balancing_large_alignments is not None:
            alignmentCmd.extend(["--no-balancing-large-alignments"])

        if pipelineArgs.process_all_alignments_on_cpu_threshold is not None:
            alignmentCmd.extend(["--process-all-alignments-on-cpu-threshold", str(pipelineArgs.process_all_alignments_on_cpu_threshold)])

        if pipelineArgs.num_alignment_device_mem_buffers is not None:
            alignmentCmd.extend(["--num-alignment-device-mem-buffers", str(pipelineArgs.num_alignment_device_mem_buffers)])

        if pipelineArgs.alignment_on_cpu is not None:
            alignmentCmd.extend(["--alignment-on-cpu"])

        if pipelineArgs.read_from_tmp_dir is not None:
            alignmentCmd.extend(["--keep-tmp"])
            alignmentCmd.extend(["--no-postsort"])

        pipelineArgs.append = False
        addSystemOptions(alignmentCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("minimap2", list(defaultCmdline), alignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="ont_germline pipeline", verbosity=pipelineArgs.x3))

        # deepvariant
        deepvarCmd = ["--ref", pipelineArgs.ref]
        deepvarCmd.extend(["--in-bam", pipelineArgs.out_bam])

        if pipelineArgs.pb_model_file is not None:
            deepvarCmd.extend(["--pb-model-file", pipelineArgs.pb_model_file])

        if pipelineArgs.gvcf:
            deepvarCmd.extend(["--gvcf"])

        if pipelineArgs.disable_use_window_selector_model:
            deepvarCmd.extend(["--disable-use-window-selector-model"])

        if pipelineArgs.interval is not None and len(pipelineArgs.interval) > 0:
            for interval in pipelineArgs.interval:
                deepvarCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None and len(pipelineArgs.interval_file) > 0:
            for interval_file in pipelineArgs.interval_file:
                deepvarCmd.extend(["--interval-file", interval_file])

        # New things from DV1.0
        if pipelineArgs.enable_small_model == True:
            deepvarCmd.extend(["--enable-small-model"])
        
        if pipelineArgs.pb_small_model_file is not None:
            deepvarCmd.extend(["--pb-small-model-file", pipelineArgs.pb_small_model_file])
        
        if pipelineArgs.use_tf32 == True:
            deepvarCmd.extend(["--use-tf32"])
        
        deepvarCmd.extend(["--mode", "ont"])
        if pipelineArgs.keep_duplicates is not None:
            deepvarCmd.extend(["--keep-duplicates"])
        if pipelineArgs.sort_by_haplotypes:
            deepvarCmd.extend(["--sort-by-haplotypes"])
        if pipelineArgs.add_hp_channel:
            deepvarCmd.extend(["--add-hp-channel"])
        if pipelineArgs.parse_sam_aux_fields:
            deepvarCmd.extend(["--parse-sam-aux-fields"])
        if pipelineArgs.norealign_reads:
            deepvarCmd.extend(["--norealign-reads"])
        if pipelineArgs.vsc_min_fraction_indels is not None:
            deepvarCmd.extend(["--vsc-min-fraction-indels", str(pipelineArgs.vsc_min_fraction_indels)])
        deepvarCmd.extend(["--vsc-min-count-snps", str(pipelineArgs.vsc_min_count_snps), "--vsc-min-count-indels",
                           str(pipelineArgs.vsc_min_count_indels)])
        deepvarCmd.extend(["--vsc-min-fraction-snps", str(pipelineArgs.vsc_min_fraction_snps)])
        deepvarCmd.extend(["--min-mapping-quality", str(pipelineArgs.min_mapping_quality), "--min-base-quality",
                           str(pipelineArgs.min_base_quality)])
        if pipelineArgs.alt_aligned_pileup is not None:
            deepvarCmd.extend(["--alt-aligned-pileup", str(pipelineArgs.alt_aligned_pileup)])
        if pipelineArgs.variant_caller is not None:
            deepvarCmd.extend(["--variant-caller", str(pipelineArgs.variant_caller)])
        if pipelineArgs.proposed_variants is not None:
            deepvarCmd.extend(["--proposed-variants", pipelineArgs.proposed_variants])
        if pipelineArgs.use_wes_model is not None:
            deepvarCmd.extend(["--use-wes-model"])
        if pipelineArgs.max_read_size_512:
            deepvarCmd.extend(["--max-read-size-512"])
        if pipelineArgs.prealign_helper_thread:
            deepvarCmd.extend(["--prealign_helper_thread"])

        if pipelineArgs.track_ref_reads:
            deepvarCmd.extend(["--track-ref-reads"])
        if pipelineArgs.phase_reads:
            deepvarCmd.extend(['--phase-reads'])
        if pipelineArgs.include_med_dp:
            deepvarCmd.extend(["--include-med-dp"])
        if pipelineArgs.normalize_reads:
            deepvarCmd.extend(["--normalize-reads"])
        if pipelineArgs.pileup_image_width is not None:
            deepvarCmd.extend(["--pileup-image-width", str(pipelineArgs.pileup_image_width)])
        if pipelineArgs.channel_insert_size:
            deepvarCmd.extend(["--channel-insert-size"])
        if pipelineArgs.no_channel_insert_size:
            deepvarCmd.extend(["--no-channel-insert-size"])
        if pipelineArgs.disable_group_variants:
            deepvarCmd.extend(["--disable-group-variants"])
        if pipelineArgs.filter_reads_too_long:
            deepvarCmd.extend(["--filter-reads-too-long"])
        if pipelineArgs.haploid_contigs is not None:
            deepvarCmd.extend(["--haploid-contigs", pipelineArgs.haploid_contigs])

        if pipelineArgs.run_partition:
            deepvarCmd.extend(["--run-partition"])

        if pipelineArgs.gpu_num_per_partition is not None:
            deepvarCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])

        deepvarCmd.extend(["--num-cpu-threads-per-stream", str(pipelineArgs.num_cpu_threads_per_stream)])
        deepvarCmd.extend(["--num-streams-per-gpu", str(pipelineArgs.num_streams_per_gpu)])

        deepvarCmd.extend(["--out-variants", pipelineArgs.out_variants])
        if pipelineArgs.read_from_tmp_dir:
            deepvarCmd.extend(["--read-from-tmp-dir"])
            #hacky way
            with open(pipelineArgs.out_bam, "w") as tmp_file:
                pass

        pipelineArgs.append = True
        addSystemOptions(deepvarCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("deepvariant", list(defaultCmdline), deepvarCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="ont_germline pipeline", verbosity=pipelineArgs.x3))

class somatic(object):
    def __init__(self, defaultCmdline, runArgs):
        pbargs_pipeline_check(runArgs)
        self.runCmds = []
        pipelineArgs = runArgs.runArgs
        # tumorAlignmentCmd = list(defaultCmdline)
        tumorAlignmentCmd = ["--ref", pipelineArgs.ref]
        tumorSMName = pipelineArgs.tumor_read_group_sm

        if tumorSMName is None:
            tumorSMName = "tumor"
        if pipelineArgs.tumor_read_group_id_prefix is None:
            pipelineArgs.tumor_read_group_id_prefix = "tumor_rg"
        tumorName = ""
        if pipelineArgs.in_se_tumor_fq is not None:
            tumorName = pbutils.check_se_fastq_files(pipelineArgs.in_se_tumor_fq, tumorSMName,
                                                     pipelineArgs.tumor_read_group_lb, pipelineArgs.tumor_read_group_pl,
                                                     pipelineArgs.tumor_read_group_id_prefix)
            for fq_se in pipelineArgs.in_se_tumor_fq:
                tumorAlignmentCmd.extend(["--in-se-fq"] + fq_se)
        else:
            tumorName = pbutils.check_fastq_files(pipelineArgs.in_tumor_fq, tumorSMName,
                                                  pipelineArgs.tumor_read_group_lb, pipelineArgs.tumor_read_group_pl,
                                                  pipelineArgs.tumor_read_group_id_prefix)
            for fq_pair in pipelineArgs.in_tumor_fq:
                tumorAlignmentCmd.extend(["--in-fq"] + fq_pair)

        if pipelineArgs.knownSites is not None:
            for knownSite in pipelineArgs.knownSites:
                tumorAlignmentCmd.extend(["--knownSites", knownSite])

        tumorAlignmentCmd.extend(["--out-bam", pipelineArgs.out_tumor_bam])

        if pipelineArgs.out_tumor_recal_file is not None:
            tumorAlignmentCmd.extend(["--out-recal-file", pipelineArgs.out_tumor_recal_file])

        if pipelineArgs.no_markdups:
            tumorAlignmentCmd.extend(["--no-markdups"])

        if pipelineArgs.markdups_single_ended_start_end == True:
            tumorAlignmentCmd.extend(["--markdups-single-ended-start-end"])

        if pipelineArgs.ignore_rg_markdups_single_ended == True:
            tumorAlignmentCmd.extend(["--ignore-rg-markdups-single-ended"])

        if pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                tumorAlignmentCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                tumorAlignmentCmd.extend(["--interval-file", interval_file])

        if pipelineArgs.interval_padding is not None:
            tumorAlignmentCmd.extend(["--interval-padding", str(pipelineArgs.interval_padding)])

        if pipelineArgs.bwa_options is not None:
            tumorAlignmentCmd.extend(["--bwa-options=" + pipelineArgs.bwa_options])

        if pipelineArgs.gpuwrite is not None:
            tumorAlignmentCmd.extend(["--gpuwrite"])

        if pipelineArgs.gpusort is not None:
            tumorAlignmentCmd.extend(["--gpusort"])

        if pipelineArgs.low_memory is not None:
            tumorAlignmentCmd.extend(["--low-memory"])

        if pipelineArgs.filter_flag is not None:
            tumorAlignmentCmd.extend(["--filter-flag", str(pipelineArgs.filter_flag)])

        if pipelineArgs.skip_multiple_hits is not None:
            tumorAlignmentCmd.extend(["--skip-multiple-hits"])

        if pipelineArgs.num_cpu_threads_per_stage is not None:
            tumorAlignmentCmd.extend(["--num-cpu-threads-per-stage", str(pipelineArgs.num_cpu_threads_per_stage)])

        tumorAlignmentCmd.extend([
            "--bwa-nstreams", str(pipelineArgs.bwa_nstreams),
            "--bwa-cpu-thread-pool", str(pipelineArgs.bwa_cpu_thread_pool),
            "--bwa-primary-cpus", str(pipelineArgs.bwa_primary_cpus),
            "--max-read-length", str(pipelineArgs.max_read_length),
            "--min-read-length", str(pipelineArgs.min_read_length),
            "--bwa-normalized-queue-capacity", str(pipelineArgs.bwa_normalized_queue_capacity)
        ])
        #CIGAR on GPU
        if pipelineArgs.cigar_on_gpu is not None:
            alignmentCmd.extend(["--cigar-on-gpu"])

        # suppressed argument
        if pipelineArgs.use_swlib:
            tumorAlignmentCmd.append("--use-swlib")

        if pipelineArgs.no_warnings:
            tumorAlignmentCmd.extend(["--no-warnings"])

        tumorAlignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

        pipelineArgs.append = False
        addSystemOptions(tumorAlignmentCmd, pipelineArgs)
        pipelineArgs.append = True
        self.runCmds.append(
            PBTool("fq2bam", list(defaultCmdline), tumorAlignmentCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                parentCmd="tumor sample processing for somatic pipeline", verbosity=pipelineArgs.x3))

        if ((pipelineArgs.in_normal_fq is not None) and len(pipelineArgs.in_normal_fq[0]) > 0) or ((pipelineArgs.in_se_normal_fq is not None) and len(pipelineArgs.in_se_normal_fq[0]) > 0):
            # normalAlignmentCmd = list(defaultCmdline)
            normalAlignmentCmd = ["--ref", pipelineArgs.ref]
            normalSMName = pipelineArgs.normal_read_group_sm
            normalName = ""
            if normalSMName is None:
                normalSMName = "normal"
            if pipelineArgs.normal_read_group_id_prefix is None:
                pipelineArgs.normal_read_group_id_prefix = "normal_rg"
            if pipelineArgs.in_se_normal_fq is not None:
                normalName = pbutils.check_se_fastq_files(pipelineArgs.in_se_normal_fq, normalSMName,
                                                       pipelineArgs.normal_read_group_lb,
                                                       pipelineArgs.normal_read_group_pl,
                                                       pipelineArgs.normal_read_group_id_prefix)
                for fq_se in pipelineArgs.in_se_normal_fq:
                    normalAlignmentCmd.extend(["--in-se-fq"] + fq_se)
            else:
                normalName = pbutils.check_fastq_files(pipelineArgs.in_normal_fq, normalSMName,
                                                       pipelineArgs.normal_read_group_lb,
                                                       pipelineArgs.normal_read_group_pl,
                                                       pipelineArgs.normal_read_group_id_prefix)
                for fq_pair in pipelineArgs.in_normal_fq:
                    normalAlignmentCmd.extend(["--in-fq"] + fq_pair)

            if pipelineArgs.knownSites is not None:
                for knownSite in pipelineArgs.knownSites:
                    normalAlignmentCmd.extend(["--knownSites", knownSite])

            if pipelineArgs.out_normal_bam is not None:
                normalAlignmentCmd.extend(["--out-bam", pipelineArgs.out_normal_bam])

            if pipelineArgs.out_normal_recal_file is not None:
                normalAlignmentCmd.extend(["--out-recal-file", pipelineArgs.out_normal_recal_file])

            if pipelineArgs.no_markdups:
                normalAlignmentCmd.extend(["--no-markdups"])

            if pipelineArgs.markdups_single_ended_start_end == True:
                normalAlignmentCmd.extend(["--markdups-single-ended-start-end"])

            if pipelineArgs.ignore_rg_markdups_single_ended == True:
                normalAlignmentCmd.extend(["--ignore-rg-markdups-single-ended"])

            if pipelineArgs.interval is not None:
                for interval in pipelineArgs.interval:
                    normalAlignmentCmd.extend(["--interval", interval])

            if pipelineArgs.interval_file is not None:
                for interval_file in pipelineArgs.interval_file:
                    normalAlignmentCmd.extend(["--interval-file", interval_file])

            if pipelineArgs.interval_padding is not None:
                normalAlignmentCmd.extend(["--interval-padding", str(pipelineArgs.interval_padding)])

            if pipelineArgs.bwa_options is not None:
                normalAlignmentCmd.extend(["--bwa-options=" + pipelineArgs.bwa_options])

            if pipelineArgs.gpuwrite is not None:
                normalAlignmentCmd.extend(["--gpuwrite"])

            if pipelineArgs.gpusort is not None:
                normalAlignmentCmd.extend(["--gpusort"])

            if pipelineArgs.low_memory is not None:
                normalAlignmentCmd.extend(["--low-memory"])

            if pipelineArgs.filter_flag is not None:
                normalAlignmentCmd.extend(["--filter-flag", str(pipelineArgs.filter_flag)])

            if pipelineArgs.skip_multiple_hits is not None:
                normalAlignmentCmd.extend(["--skip-multiple-hits"])

            if pipelineArgs.num_cpu_threads_per_stage is not None:
                normalAlignmentCmd.extend(["--num-cpu-threads-per-stage", str(pipelineArgs.num_cpu_threads_per_stage)])

            normalAlignmentCmd.extend([
                "--bwa-nstreams", str(pipelineArgs.bwa_nstreams),
                "--bwa-cpu-thread-pool", str(pipelineArgs.bwa_cpu_thread_pool),
                "--bwa-primary-cpus", str(pipelineArgs.bwa_primary_cpus),
                "--max-read-length", str(pipelineArgs.max_read_length),
                "--min-read-length", str(pipelineArgs.min_read_length),
                "--bwa-normalized-queue-capacity", str(pipelineArgs.bwa_normalized_queue_capacity)
            ])
            #CIGAR on GPU
            if pipelineArgs.cigar_on_gpu is not None:
                normalAlignmentCmd.extend(["--cigar-on-gpu"])

            # suppressed argument
            if pipelineArgs.use_swlib:
                normalAlignmentCmd.append("--use-swlib")


            if pipelineArgs.no_warnings:
                normalAlignmentCmd.extend(["--no-warnings"])

            normalAlignmentCmd.extend(["--memory-limit", str(pipelineArgs.memory_limit)])

            addSystemOptions(normalAlignmentCmd, pipelineArgs)
            self.runCmds.append(PBTool("fq2bam", list(defaultCmdline), normalAlignmentCmd, os.environ.copy(),
                                    tmp_dir=pipelineArgs.tmp_dir,
                                    parentCmd="normal sample processing for somatic pipeline",
                                    verbosity=pipelineArgs.x3))

        # mutectCmd = list(defaultCmdline)
        mutectCmd = ["--ref", pipelineArgs.ref, "--in-tumor-bam", pipelineArgs.out_tumor_bam, "--tumor-name", tumorName,
                     "--out-vcf", pipelineArgs.out_vcf, "--num-htvc-threads",
                     str(pipelineArgs.num_htvc_threads)]

        if pipelineArgs.out_tumor_recal_file is not None:
            mutectCmd.extend(["--in-tumor-recal-file", pipelineArgs.out_tumor_recal_file])

        if (pipelineArgs.in_normal_fq is not None) and (len(pipelineArgs.in_normal_fq[0]) > 0):
            mutectCmd.extend(["--in-normal-bam", pipelineArgs.out_normal_bam, "--normal-name", normalName])
            if pipelineArgs.out_normal_recal_file is not None:
                mutectCmd.extend(["--in-normal-recal-file", pipelineArgs.out_normal_recal_file])

        if pipelineArgs.interval is not None:
            for interval in pipelineArgs.interval:
                mutectCmd.extend(["--interval", interval])

        if pipelineArgs.interval_file is not None:
            for interval_file in pipelineArgs.interval_file:
                mutectCmd.extend(["--interval-file", interval_file])

        if pipelineArgs.interval_padding is not None:
            mutectCmd.extend(["--interval-padding", str(pipelineArgs.interval_padding)])

        if pipelineArgs.mutectcaller_options is not None:
            mutectCmd.extend(["--mutectcaller-options", pipelineArgs.mutectcaller_options])

        if pipelineArgs.low_memory is not None or pipelineArgs.mutect_low_memory is not None:
            mutectCmd.extend(["--mutect-low-memory"]) 

        if pipelineArgs.run_partition:
            mutectCmd.extend(["--run-partition"])
        if pipelineArgs.no_alt_contigs:
            mutectCmd.extend(["--no-alt-contigs"])
        if pipelineArgs.gpu_num_per_partition is not None:
            mutectCmd.extend(["--gpu-num-per-partition", str(pipelineArgs.gpu_num_per_partition)])

        if pipelineArgs.mutect_bam_output is not None:
            mutectCmd.extend(["--mutect-bam-output", pipelineArgs.mutect_bam_output])

        if pipelineArgs.initial_tumor_lod is not None:
            mutectCmd.extend(["--initial-tumor-lod", str(pipelineArgs.initial_tumor_lod)])
        if pipelineArgs.tumor_lod_to_emit is not None:
            mutectCmd.extend(["--tumor-lod-to-emit", str(pipelineArgs.tumor_lod_to_emit)])
        if pipelineArgs.pruning_lod_threshold is not None:
            mutectCmd.extend(["--pruning-lod-threshold", str(pipelineArgs.pruning_lod_threshold)])
        if pipelineArgs.active_probability_threshold is not None:
            mutectCmd.extend(["--active-probability-threshold", str(pipelineArgs.active_probability_threshold)])
        
        if pipelineArgs.genotype_germline_sites == True:
            mutectCmd.extend(["--genotype-germline-sites"])
        if pipelineArgs.genotype_pon_sites == True:
            mutectCmd.extend(["--genotype-pon-sites"])
        if pipelineArgs.mutect_germline_resource is not None:
            mutectCmd.extend(["--mutect-germline-resource", pipelineArgs.mutect_germline_resource])
        if pipelineArgs.mutect_alleles is not None:
            mutectCmd.extend(["--mutect-alleles", pipelineArgs.mutect_alleles])
        if pipelineArgs.force_call_filtered_alleles == True:
            mutectCmd.extend(["--force-call-filtered-alleles"])
        if pipelineArgs.filter_reads_too_long == True:
            mutectCmd.extend(["--filter-reads-too-long"])
        if pipelineArgs.mutect_f1r2_tar_gz is not None:
            mutectCmd.extend(["--mutect-f1r2-tar-gz", pipelineArgs.mutect_f1r2_tar_gz])

        if pipelineArgs.minimum_mapping_quality != None:
            mutectCmd.extend(["--minimum-mapping-quality", str(pipelineArgs.minimum_mapping_quality)])
        if pipelineArgs.min_base_quality_score != None:
            mutectCmd.extend(["--min-base-quality-score", str(pipelineArgs.min_base_quality_score)])
        if pipelineArgs.f1r2_median_mq != None:
            mutectCmd.extend(["--f1r2-median-mq", str(pipelineArgs.f1r2_median_mq)])
        if pipelineArgs.base_quality_score_threshold != None:
            mutectCmd.extend(["--base-quality-score-threshold", str(pipelineArgs.base_quality_score_threshold)])
        if pipelineArgs.normal_lod != None:
            mutectCmd.extend(["--normal-lod", str(pipelineArgs.normal_lod)])
        if pipelineArgs.allow_non_unique_kmers_in_ref == True:
            mutectCmd.extend(["--allow-non-unique-kmers-in-ref"])
        if pipelineArgs.enable_dynamic_read_disqualification_for_genotyping == True:
            mutectCmd.extend(["--enable-dynamic-read-disqualification-for-genotyping"])
        if pipelineArgs.recover_all_dangling_branches == True:
            mutectCmd.extend(["--recover-all-dangling-branches"])
        if pipelineArgs.pileup_detection == True:
            mutectCmd.extend(["--pileup-detection"])
        if hasattr(pipelineArgs, 'mitochondria_mode') and pipelineArgs.mitochondria_mode == True:
            mutectCmd.extend(["--mitochondria-mode"])


        addSystemOptions(mutectCmd, pipelineArgs)
        self.runCmds.append(
            PBTool("mutectcaller", list(defaultCmdline), mutectCmd, os.environ.copy(), tmp_dir=pipelineArgs.tmp_dir,
                   parentCmd="somatic pipeline", verbosity=pipelineArgs.x3))


def composeRun(defaultCmdLine, runArgs):
    if runArgs.command in standaloneTools:  # runArgs is-a PBRun, runArgs.runArgs is-a argparse.Namespace.
        finalArgs = sys.argv[2:]
        if not "--tmp-dir" in finalArgs:
            finalArgs.extend(["--tmp-dir", runArgs.runArgs.tmp_dir])
        else:
            finalArgs[finalArgs.index("--tmp-dir") + 1] = runArgs.runArgs.tmp_dir

        PBTool(runArgs.command, list(defaultCmdLine), finalArgs, os.environ.copy(),
               tmp_dir=runArgs.runArgs.tmp_dir, parentCmd=None, verbosity=runArgs.runArgs.x3,
               logfile=runArgs.runArgs.logfile, append=runArgs.runArgs.append).dispatch()
    else:
        newPipeline = globals()[runArgs.command](defaultCmdLine, runArgs)
        for cmd in newPipeline.runCmds:  # Each cmd is-a PBTool.
            cmd.logfile = runArgs.runArgs.logfile
            cmd.dispatch()
