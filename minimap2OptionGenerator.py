import argparse
from pbutils import GetDefaultMemoryLimit, GetNumCPUs, GetNumGPUs
from PBOption import PBOption
import sys

class minimap2OptionGenerator():
    def __init__(self, is_ont_germline=False):
        numCPUs = GetNumCPUs()
        using_help_mode = "--help" in sys.argv or "-h" in sys.argv
        numGPUs = GetNumGPUs(allow_no_gpus=using_help_mode)
        numGPUStreams = numGPUs * 4
        self.allOptions = [
            PBOption(category="minimap2Option", name="--preset", default="map-pbmm2", typeName=str, helpStr="Which preset to apply. Possible values are {map-pbmm2,map-hifi,map-ont,lr:hq,splice,splice:hq,splice:sr}. 'map-pbmm2' is a customized preset that uses pbmm2's default values for PacBio HiFi/CCS genomic reads. 'map-hifi' is minimap2's default preset for PacBio HiFi/CCS genomic reads. 'map-ont' is for Oxford Nanopore genomic reads. 'lr:hq' is for Nanopore Q20 genomic reads. 'splice' is for spliced long reads (strand unknown). 'splice:hq' is for Final PacBio Iso-seq or traditional cDNA. 'splice:sr' is for short RNA-seq reads."),
            PBOption(category="minimap2Option", name="--pbmm2", helpStr="Include additional processing to match the format and accuracy of pbmm2. Not compatible with map-ont `--preset` value.", action="store_true"),
            PBOption(category="minimap2Option", name="--pbmm2-unmapped", helpStr="Include unmapped records in output of pbmm2. Must be used concurrently with `--pbmm2`. Not compatible with map-ont `--preset` value.", action="store_true"),
            PBOption(category="minimap2Option", name="--minimizer-kmer-len", short_name="-k", typeName=int, default=None, helpStr="Minimizer k-mer length."),
            PBOption(category="minimap2Option", name="--both-strands", short_name="-ub", helpStr="Force minimap2 to consider both strands when finding canonical splicing sites GT-AG.", action="store_true"),
            PBOption(category="minimap2Option", name="--forward-transcript-strand", short_name="-uf", helpStr="Force minimap2 to consider the forward transcript strand only when finding canonical splicing sites GT-AG.", action="store_true"),
            PBOption(category="minimap2Option", name="--md", helpStr="Output the MD tag.", action="store_true"),
            PBOption(category="minimap2Option", name="--eqx", action="store_true", helpStr="Write =/X CIGAR operators."),
            PBOption(category="minimap2Option", name="--copy-comment", short_name="-y", action="store_true", required=False, helpStr="Append FASTQ comment to BAM output via auxiliary tag."),
            PBOption(category="minimap2Option", name="--no-markdups", action="store_true", default=True, helpStr=argparse.SUPPRESS),#"Do not perform the Mark Duplicates step. Return BAM after sorting."),
            PBOption(category="minimap2Option", name="--markdups-assume-sortorder-queryname", action="store_true", helpStr=argparse.SUPPRESS),#"Assume the reads are sorted by queryname for marking duplicates. This will mark secondary, supplementary, and unmapped reads as duplicates as well. This flag will not impact variant calling while increasing processing times."),
            PBOption(category="minimap2Option", name="--optical-duplicate-pixel-distance", typeName=int, default=None, helpStr=argparse.SUPPRESS),#"The maximum offset between two duplicate clusters in order to consider them optical duplicates. Ignored if --out-duplicate-metrics is not passed."),
            PBOption(category="minimap2Option", name="--interval", short_name="-L", action='append', helpStr="Interval within which to call bqsr from the input reads. All intervals will have a padding of 100 to get read records, and overlapping intervals will be combined. Interval files should be passed using the --interval-file option. This option can be used multiple times (e.g. \"-L chr1 -L chr2:10000 -L chr3:20000+ -L chr4:10000-20000\")."),
            PBOption(category="minimap2Option", name="--interval-padding", short_name="-ip", typeName=int, helpStr="Amount of padding (in base pairs) to add to each interval you are including."),
            PBOption(category="minimap2Option", name="--standalone-bqsr", action="store_true", helpStr="Run standalone BQSR after generating sorted BAM. This option requires both --knownSites and --out-recal-file input parameters."),
            PBOption(category="minimap2Option", name="--no-postsort", action="store_true", helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--read-group-sm", helpStr="SM tag for read groups in this run.", default=None),
            PBOption(category="minimap2Option", name="--read-group-lb", helpStr="LB tag for read groups in this run.", default=None),
            PBOption(category="minimap2Option", name="--read-group-pl", helpStr="PL tag for read groups in this run.", default=None),
            PBOption(category="minimap2Option", name="--read-group-id-prefix", helpStr="Prefix for the ID and PU tags for read groups in this run. This prefix will be used for all pairs of FASTQ files in this run. The ID and PU tags will consist of this prefix and an identifier, that will be unique for a pair of FASTQ files.", default=None)
        ]
        self.perfOptions = [
            PBOption(category="minimap2Option", name="--num-threads", default=(max(1, (numCPUs - numGPUStreams)) if max(1, (numCPUs - numGPUStreams)) < 128 else 128), typeName=int, helpStr="Number of processing threads."),
            PBOption(category="minimap2Option", name="--nstreams", default=2, typeName=int, helpStr="Number of streams to use per GPU."),
            PBOption(category="minimap2Option", name="--gpuwrite", helpStr="Use one GPU to accelerate writing final BAM/CRAM.", action="store_true"),
            PBOption(category="minimap2Option", name="--gpuwrite-deflate-algo", helpStr="Choose the nvCOMP DEFLATE algorithm to use with --gpuwrite. Note these options do not correspond to CPU DEFLATE options. Valid options are 1, 2, and 4. Option 1 is fastest, while options 2 and 4 have progressively lower throughput but higher compression ratios. The default value is 1 when the user does not provide an input (i.e., None).", typeName=int),
            PBOption(category="minimap2Option", name="--gpusort", helpStr="Use GPUs to accelerate sorting.", action="store_true"),
            PBOption(category="minimap2Option", name="--use-gds", helpStr="Use GPUDirect Storage (GDS) to enable a direct data path for direct memory access (DMA) transfers between GPU memory and storage. Must be used concurrently with `--gpuwrite`. Please refer to Parabricks Documentation > Best Performance for information on how to set up and use GPUDirect Storage.", action="store_true"),
            PBOption(category="minimap2Option", name="--max-queue-chunks", default=None, typeName=int, helpStr="Max number of chunks to allow in the pre-alignment processing stage. Increasing this value may result in faster processing, but it will use more host memory. It is not recommended to use this argument for splice presets."),
            PBOption(category="minimap2Option", name="--max-queue-reads", default=500000, typeName=int, helpStr="Max number of reads to allow in the alignment processing stage. Increasing this value may result in faster processing, but it will use more host memory."),
            PBOption(category="minimap2Option", name="--memory-limit", default=GetDefaultMemoryLimit(), typeName=int, helpStr=argparse.SUPPRESS), #used for sort
            PBOption(category="minimap2Option", name="--low-memory", helpStr="Use low memory mode.", action="store_true"),
            PBOption(category="minimap2Option", name="--chunk-size", default=1000, typeName=int, helpStr="Max number of reads in a processing chunk. Increasing this value may result in faster processing, but it will use more host memory."),
            PBOption(category="minimap2Option", name="--mem-pool-buf-size", default=100, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--free-queue-batch-size", default=1000, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--num-alignment-workers-per-thread", default=16, required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--alignment-thread-num-divisor", required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--alignment-large-pair-size", required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--alignment-midsize-pair-size", required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--process-large-alignments-on-gpu", action="store_true", helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--no-balancing-large-alignments", action="store_true", helpStr=argparse.SUPPRESS), # turns off on the fly calculation that turns on/off processing large alignments on cpu based on queue loads
            PBOption(category="minimap2Option", name="--process-all-alignments-on-cpu-threshold", required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--num-alignment-device-mem-buffers", required=False, typeName=int, helpStr=argparse.SUPPRESS),
            PBOption(category="minimap2Option", name="--alignment-on-cpu", action="store_true", helpStr=argparse.SUPPRESS),
        ]
        if is_ont_germline:
            #set the --preset option to "map-ont" and hide it from the user
            for option in self.allOptions:
                if option.name == "--preset":
                    option.default = "map-ont"
                    option.helpStr = argparse.SUPPRESS
                if option.name == "--pbmm2" or option.name == "--pbmm2-unmapped":
                    option.helpStr = argparse.SUPPRESS
