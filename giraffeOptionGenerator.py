import argparse
from pbutils import GetDefaultMemoryLimit
from PBOption import PBOption

class giraffeOptionGenerator():
    def __init__(self):
        option_category = "giraffeOption"
        self.allOptions = [
            PBOption(category=option_category, name="--read-group", typeName=str, required=False, helpStr="Read group ID for this run."),
            PBOption(category=option_category, name="--sample", typeName=str, required=False, helpStr="Sample (SM) tag for read group in this run."),
            PBOption(category=option_category, name="--read-group-library", typeName=str, required=False, helpStr="Library (LB) tag for read group in this run."),
            PBOption(category=option_category, name="--read-group-platform", typeName=str, required=False, helpStr="Platform (PL) tag for read group in this run; refers to platform/technology used to produce reads."),
            PBOption(category=option_category, name="--read-group-pu", typeName=str, required=False, helpStr="Platform unit (PU) tag for read group in this run."),
            PBOption(category=option_category, name="--prune-low-cplx", action="store_true", required=False, helpStr="Prune short and low complexity anchors during linear format realignment."),
            PBOption(category=option_category, name="--max-fragment-length", typeName=int, required=False, helpStr="Assume that fragment lengths should be smaller than MAX-FRAGMENT-LENGTH when estimating the fragment length distribution."),
            PBOption(category=option_category, name="--fragment-mean", typeName=float, required=False, helpStr="Force the fragment length distribution to have this mean."),
            PBOption(category=option_category, name="--fragment-stdev", typeName=float, required=False, helpStr="Force the fragment length distribution to have this standard deviation."),
            PBOption(category=option_category, name="--align-only", action="store_true", required=False, helpStr="Generate output BAM after vg-giraffe alignment. The output will not be co-ordinate sorted."),  # and duplicates will not be marked."),
            PBOption(category=option_category, name="--copy-comment", action="store_true", required=False, helpStr="Append FASTQ comment to BAM output via auxiliary tag."),
            # options for sort and postsort
            PBOption(category=option_category, name="--no-markdups", action="store_true", helpStr="Do not perform the Mark Duplicates step. Return BAM after sorting."),
            PBOption(category=option_category, name="--markdups-single-ended-start-end", action="store_true", helpStr="Mark duplicate on single-ended reads by 5' and 3' end."),
            PBOption(category=option_category, name="--ignore-rg-markdups-single-ended", action="store_true", helpStr="Ignore read group info in marking duplicates on single-ended reads. This option must be used with `--markdups-single-ended-start-end`."),
            PBOption(category=option_category, name="--markdups-assume-sortorder-queryname",helpStr="Assume the reads are sorted by queryname for marking duplicates. This will mark secondary, supplementary, and unmapped reads as duplicates as well. This flag will not impact variant calling while increasing processing times.", action="store_true"),
            PBOption(category=option_category, name="--markdups-picard-version-2182", helpStr="Assume marking duplicates to be similar to Picard version 2.18.2.", action="store_true"),
            PBOption(category=option_category, name="--optical-duplicate-pixel-distance", helpStr="The maximum offset between two duplicate clusters in order to consider them optical duplicates. Ignored if --out-duplicate-metrics is not passed.", typeName=int, default=None),
            PBOption(category=option_category, name="--monitor-usage", action="store_true", helpStr="Monitor approximate CPU utilization and host memory usage during execution."),
            # no bqsr yet
            # PBOption(category=option_category, name="--interval", short_name="-L", action='append', helpStr="Interval within which to call bqsr from the input reads. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            # PBOption(category=option_category, name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including."),
            # PBOption(category=option_category, name="--standalone-bqsr", action="store_true", helpStr="Run standalone BQSR after generating sorted BAM. This option requires both --knownSites and --out-recal-file input parameters."),
            PBOption(category=option_category, name="--no-postsort", action="store_true", helpStr=argparse.SUPPRESS),
            PBOption(category=option_category, name="--testing-options", helpStr=argparse.SUPPRESS, default=None),
            PBOption(category=option_category, name="--max-read-length", helpStr="Maximum read length/size (i.e., sequence length) used for giraffe and filtering FASTQ input.", typeName=int, default=480),
            PBOption(category=option_category, name="--min-read-length", helpStr="Minimum read length/size (i.e., sequence length) used for giraffe and filtering FASTQ input.", typeName=int, default=1),
            PBOption(category=option_category, name="--pe-fq-list", helpStr=argparse.SUPPRESS), # value asigned when checking --in-fq-list
            PBOption(category=option_category, name="--se-fq-list", helpStr=argparse.SUPPRESS),  # value asigned when checking --in-se-fq-list

        ]
        self.perfOptions = [
            PBOption(category=option_category, name="--nstreams", default="auto", typeName=str, helpStr="Number of streams per GPU to use; use 'auto' to set from GPU and host memory (may enable low-memory, dozeu/minimizers for SE). Integer overrides. More streams increases device and host memory usage."),
            PBOption(category=option_category, name="--num-primary-cpus-per-gpu", typeName=int, helpStr=argparse.SUPPRESS), # Keep this option for compatibility with old version, if this option is not None --num-cpu-threads-per-gpu is assigned to it in run_pb.py
            PBOption(category=option_category, name="--num-cpu-threads-per-gpu", default=16, typeName=int, helpStr="Number of primary CPU threads to use per GPU."),
            PBOption(category=option_category, name="--batch-size", default=10000, typeName=int, helpStr="Batch size used for processing alignments."),
            PBOption(category=option_category, name="--write-threads", default=4, typeName=int, helpStr="Number of threads used for writing and pre-sorting output."),
            # PBOption(category=option_category, name="--parameter-preset", typeName=str, helpStr="set computational parameters (fast / default)."),
            PBOption(category=option_category, name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category=option_category, name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None).", typeName=int),
            PBOption(category=option_category, name="--gpusort", helpStr="Use GPUs to accelerate sorting and marking.", action="store_true"),
            PBOption(category=option_category, name="--use-gds", helpStr="Use GPUDirect Storage (GDS) to enable a direct data path for direct memory access (DMA) transfers between GPU memory and storage. Must be used concurrently with `--gpuwrite`. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.", action="store_true"),
            PBOption(category=option_category, name="--memory-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr="System memory limit in GBs during sorting and postsorting. By default, the limit is half of the total system memory."),
            PBOption(category=option_category, name="--low-memory", helpStr="Use low memory mode; will lower the number of streams per GPU and decrease the batch size.", action="store_true"),
            # work queue capacity, minimizers_gpu, and dozeu_gpu can be set by automode
            PBOption(category=option_category, name="--minimizers-gpu", helpStr="(SE only) Use GPU for minimizers and seeds.", action="store_true", default=False),
            PBOption(category=option_category, name="--work-queue-capacity", typeName=int, helpStr="Soft limit for the capacity of the work queues in between stages.", default=40),
            PBOption(category=option_category, name="--dozeu-gpu", helpStr=argparse.SUPPRESS, default=True),
        ]
