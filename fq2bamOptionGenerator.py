import argparse
from PBOption import PBOption
from pbutils import GetDefaultMemoryLimit, getDefaultBwaCPUThreadPool


class fq2bamfastOptionGenerator():
    def __init__(self, is_somatic_pipeline=False, is_deepvariant_pipeline=False, is_human_par=False):
        option_category = "fq2bamOption"
        self.allOptions = [
            # bwalib-specific options
            PBOption(category=option_category, name="--use-swlib", helpStr=argparse.SUPPRESS, action="store_true"),  # use Smith-Waterman library
            PBOption(category=option_category, name="--max-read-length", helpStr="Maximum read length/size (i.e., sequence length) used for bwa and filtering FASTQ input.", typeName=int, default=480),
            PBOption(category=option_category, name="--min-read-length", helpStr="Minimum read length/size (i.e., sequence length) used for bwa and filtering FASTQ input.", typeName=int, default=1),
        ]
        self.perfOptions = [
            PBOption(category=option_category, name="--bwa-nstreams", helpStr="Number of streams per GPU to use; note: more streams increases device memory usage. Default is auto which will try to use an optimal amount of device memory.", typeName=str, default="auto"),
            PBOption(category=option_category, name="--bwa-cpu-thread-pool", helpStr="Number of threads to devote to CPU thread pool *per GPU*.", typeName=int, default=getDefaultBwaCPUThreadPool()),
            PBOption(category=option_category, name="--num-cpu-threads-per-stage", helpStr=" (Same as above) Number of threads to devote to CPU thread pool *per GPU*.", typeName=int),
            PBOption(category=option_category, name="--bwa-normalized-queue-capacity", helpStr="Normalized capacity for alignment work queues, use a lower value if CPU memory is low; final value will be <number of GPUs> * <normalized capacity>.", typeName=int, default=10),
            PBOption(category=option_category, name="--bwa-primary-cpus", default="auto", typeName=str, helpStr="Number of primary CPU threads driving its associated thread pool. Default is auto which will use 1 primary thread with its associated thread pool per GPU."),
            PBOption(category=option_category, name="--cigar-on-gpu", action="store_true", helpStr="Run CIGAR generation on GPU. Helpful in CPU bound conditions. (default is on CPU)."),
           
        ]

        self.allOptions.extend([
            PBOption(category=option_category, name="--interval", short_name="-L", action='append', helpStr="Interval within which to call bqsr from the input reads. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            PBOption(category=option_category, name="--bwa-options", helpStr="Pass supported bwa mem options as one string. The current original bwa mem supported options are: -M, -Y, -C, -T, -B, -U, -L, -I, and -K (e.g. --bwa-options=\"-M -Y\").", default=None),
            PBOption(category=option_category, name="--no-warnings", helpStr="Suppress warning messages about system thread and memory usage.", action="store_true"),
            PBOption(category=option_category, name="--filter-flag", helpStr="Don't generate SAM entries in the output if the entry's flag's meet this criteria. Criteria: (flag & filter != 0).", default=0, typeName=int),
            PBOption(category=option_category, name="--skip-multiple-hits", helpStr="Filter SAM entries whose length of SA is not 0.", action="store_true"),
            # PBOption(category=option_category, name="--min-read-length", typeName=int, helpStr="Skip reads below minimum read length. They will not be part of output."),
            PBOption(category=option_category, name="--align-only", action="store_true", helpStr="Generate output BAM after bwa-mem. The output will not be co-ordinate sorted or duplicates will not be marked."),
            PBOption(category=option_category, name="--pe-fq-list", helpStr=argparse.SUPPRESS), # value asigned when checking --in-fq-list
            PBOption(category=option_category, name="--se-fq-list", helpStr=argparse.SUPPRESS),  # value asigned when checking --in-se-fq-list
            PBOption(category=option_category, name="--no-postsort", action="store_true", helpStr=argparse.SUPPRESS),
            # PBOption(category=option_category, name="--num-cpu-threads-per-stage", default=8, typeName=int, helpStr="Number of CPU threads to use per stage."),
            PBOption(category=option_category, name="--no-markdups", action="store_true", helpStr="Do not perform the Mark Duplicates step. Return BAM after sorting."),
            PBOption(category=option_category, name="--markdups-single-ended-start-end", action="store_true", helpStr="Mark duplicate on single-ended reads by 5' and 3' end."),
            PBOption(category=option_category, name="--ignore-rg-markdups-single-ended", action="store_true", helpStr="Ignore read group info in marking duplicates on single-ended reads. This option must be used with `--markdups-single-ended-start-end`."),
            PBOption(category=option_category, name="--fix-mate", action="store_true", helpStr="Add mate cigar (MC) and mate quality (MQ) tags to the output file."),
            PBOption(category=option_category, name="--markdups-assume-sortorder-queryname", helpStr="Assume the reads are sorted by queryname for marking duplicates. This will mark secondary, supplementary, and unmapped reads as duplicates as well. This flag will not impact variant calling while increasing processing times.", action="store_true"),
            PBOption(category=option_category, name="--markdups-picard-version-2182", helpStr="Assume marking duplicates to be similar to Picard version 2.18.2.", action="store_true"),
            PBOption(category=option_category, name="--monitor-usage", action="store_true", helpStr="Monitor approximate CPU utilization and host memory usage during execution."),
            PBOption(category=option_category, name="--optical-duplicate-pixel-distance", helpStr="The maximum offset between two duplicate clusters in order to consider them optical duplicates. Ignored if --out-duplicate-metrics is not passed.", typeName=int, default=None)
        ])
        self.perfOptions.extend([
            PBOption(category=option_category, name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category=option_category, name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None).", typeName=int),
            PBOption(category=option_category, name="--gpusort", helpStr="Use GPUs to accelerate sorting and marking.", action="store_true"),
            PBOption(category=option_category, name="--use-gds", helpStr="Use GPUDirect Storage (GDS) to enable a direct data path for direct memory access (DMA) transfers between GPU memory and storage. Must be used concurrently with `--gpuwrite`. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.", action="store_true"),
            PBOption(category=option_category, name="--memory-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr="System memory limit in GBs during sorting and postsorting. By default, the limit is half of the total system memory."),
            PBOption(category=option_category, name="--low-memory", helpStr="Use low memory mode; will lower the number of streams per GPU.", action="store_true")
        ])
        if not is_somatic_pipeline:
            self.allOptions.extend([
                #PBOption(category=option_category, name="--mba", helpStr="Run MergeBAMAlignment after alignment", action="store_true"),
                PBOption(category=option_category, name="--read-group-sm", helpStr="SM tag for read groups in this run.", default=None),
                PBOption(category=option_category, name="--read-group-lb", helpStr="LB tag for read groups in this run.", default=None),
                PBOption(category=option_category, name="--read-group-pl", helpStr="PL tag for read groups in this run.", default=None),
                PBOption(category=option_category, name="--read-group-id-prefix", helpStr="Prefix for the ID and PU tags for read groups in this run. This prefix will be used for all pairs of FASTQ files in this run. The ID and PU tags will consist of this prefix and an identifier, that will be unique for a pair of FASTQ files.", default=None)
            ])
        if not is_deepvariant_pipeline:
            self.allOptions.extend([
                PBOption(category=option_category, name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including.")
            ])
        if is_human_par:
            self.allOptions.extend([
                PBOption(category=option_category, name="--standalone-bqsr", action="store_true", helpStr="Run standalone BQSR after generating sorted BAM. This option requires both --knownSites and --out-recal-file input parameters.")
            ])
        else:
            self.allOptions.extend([
                PBOption(category=option_category, name="--standalone-bqsr", action="store_true", helpStr="Run standalone BQSR.")
            ])
