import argparse
from PBOption import PBOption
from pbutils import GetNumGPUs, IsFileStreamWritable
import sys


class sysOptionGenerator():
    def __init__(self, sys_options=True):
        self.allOptions = [
            # We used to have x2, x4 and x5 but they aren't used anymore.  x5 was
            # to run valgrind inside the container, don't know what x2 & x4 were for.
            PBOption(category="sysOption", name="--verbose", action="store_true", helpStr="Enable verbose output."),
            PBOption(category="sysOption", name="--x3", action="store_true", helpStr="Show full command line arguments."),
            PBOption(category="sysOption", name="--logfile", typeName=IsFileStreamWritable, helpStr="Path to the log file. If not specified, messages will only be written to the standard error output."),
            PBOption(category="sysOption", name="--append", action="store_true", helpStr=argparse.SUPPRESS), # Only used in a pipeline for 2nd & subsequent stages.
            PBOption(category="sysOption", name="--tmp-dir", helpStr="Full path to the directory where temporary files will be stored.", default="."),
            PBOption(category="sysOption", name="--with-petagene-dir", helpStr="Full path to the PetaGene installation directory. By default, this should have been installed at /opt/petagene. Use of this option also requires that the PetaLink library has been preloaded by setting the LD_PRELOAD environment variable. Optionally set the PETASUITE_REFPATH and PGCLOUD_CREDPATH environment variables that are used for data and credentials. Optionally set the PetaLinkMode environment variable that is used to further configure PetaLink, notably setting it to \"+write\" to enable outputting compressed BAM and .fastq files."),
            PBOption(category="sysOption", name="--keep-tmp", action="store_true", helpStr="Do not delete the directory storing temporary files after completion."),
            PBOption(category="sysOption", name="--no-seccomp-override", action="store_true", helpStr="Do not override seccomp options for docker."),
            PBOption(category="sysOption", name="--version", action="store_true", helpStr="View compatible software versions."),
            PBOption(category="sysOption", name="--preserve-file-symlinks", action="store_true", helpStr="Override default behavior to keep file symlinks intact and *not* resolve the symlink."),
            PBOption(category="sysOption", name="--dev-mode", action="store_true", helpStr=argparse.SUPPRESS)  # used for running wrapper without building a container
        ]
        if sys_options is True:
            using_help_mode = "--help" in sys.argv or "-h" in sys.argv
            ngpus = GetNumGPUs(allow_no_gpus=using_help_mode)
            ngpus_help_msg = "Number of GPUs to use for a run."
            if ngpus == 0:
                ngpus_help_msg += " WARNING: Could not find accessible GPUs. Please make sure the container options enable GPUs."
            self.allOptions.extend([
                PBOption(category="sysOption", name="--num-gpus", default=ngpus, typeName=int, helpStr=ngpus_help_msg)
            ])
