#!/usr/bin/env python3


import os, stat, shutil
import os.path
import re
import sys
import textwrap
import signal
import subprocess
import gzip
import multiprocessing
import common_err_mesg
import typing

runTempDir = None


def rreplace(s, old, new, numOccurence):
  ''' In the string s, replace the last numOccurence occurrences of old with new. '''
  li = s.rsplit(old, numOccurence)
  return new.join(li)


def deleteTmpDir():
  if runTempDir == None:
    return
  if os.path.exists(runTempDir):
    try:
      shutil.rmtree(runTempDir, ignore_errors=True)
    except OSError as e:
      print("Could not delete " + runTempDir)


def pbExit(retVal = 0):
  sys.stdout.flush()
  sys.stderr.flush()
  os._exit(retVal)


def ConfigError(errStr):
  print(textwrap.fill("[Parabricks Options Error]: " + errStr, 120))
  print(textwrap.fill("[Parabricks Options Error]: Please reinstall the software\n" + common_err_mesg.common_err_mesg, 120))
  print(textwrap.fill("[Parabricks Options Error]: There is a forum for Q&A as well at https://forums.developer.nvidia.com/c/healthcare/Parabricks/290", 120))
  print(textwrap.fill("[Parabricks Options Error]: Exiting...", 120))
  pbExit(-1)


def OptError(errStr):
  print(textwrap.fill("[Parabricks Options Error]: " + errStr, 120))
  print(textwrap.fill("[Parabricks Options Error]: Run with -h to see help", 120))
  deleteTmpDir()
  pbExit(-1)


def OptMesg(mesgStr):
  print(textwrap.fill("[Parabricks Options Mesg]: " + mesgStr, 120))
  sys.stdout.flush()


def GetDefaultMemoryLimit():
  try:
    with open('/proc/meminfo') as f:
      meminfo = f.read().split("\n")
      for line in meminfo:
        if "MemTotal" in line:
          splitLine = line.split(" ")
          for i in range(1, len(splitLine)):
            if splitLine[i] != '':
              mem_total_kb = int(splitLine[i])
              print("")
              mem_total_gb = mem_total_kb / 1048576.0
              return int(mem_total_gb / 2)
  except:
    return 20 #/proc/meminfo does not exist, go with initial default value


def getDefaultBwaCPUThreadPool() -> int:
  return 16


def GetNumCPUs():
  return multiprocessing.cpu_count()


def GetNumGPUs(allow_no_gpus: bool = False) -> int:
  NO_GPUS_HELP_RET = 0
  try:
    output = subprocess.call(["which", "nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    if output != 0:
      if allow_no_gpus:
        return NO_GPUS_HELP_RET
      OptError("Could not find accessible GPUs. Please make sure the container options enable GPUs")
  except subprocess.CalledProcessError as e:
    if allow_no_gpus:
      return NO_GPUS_HELP_RET
    OptError("Could not find accessible GPUs. Please make sure the container options enable GPUs")

  try:
    output = subprocess.check_output(["nvidia-smi", "-L"], universal_newlines=True)
    return output.count('\n')
  except subprocess.CalledProcessError as e:
    if allow_no_gpus:
      return NO_GPUS_HELP_RET
    OptError("Could not find accessible GPUs. Please check the output of nvidia-smi -L")


def GetDevicesAvailableMemory() -> typing.List[int]:
  try:
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader,nounits"], universal_newlines=True)
  except subprocess.CalledProcessError as e:
    OptError("Could not find accessible GPUs. Please check the output of nvidia-smi --query-gpu=index,name,memory.total")
  deviceInfo = output.strip().split('\n')
  memMiB = []
  for line in deviceInfo:
    try:
      # it's possible for nvidia-smi to return [N/A] for igpu systems
      memory_int = int(line.split(",")[2])
    except ValueError:
      # default to 24GB for unified memory systems such as GB10
      memory_int = 24_000
    memMiB.append(memory_int)
  return memMiB


def IsFileStreamWritable(outputName):
  if outputName[0:5] == "gs://":
    return IsGFileWriteable(outputName)
  elif outputName[0:5] == "s3://":
    return IsS3FileWriteable(outputName)
  else:
    return IsFileWriteable(outputName)


def IsFileWriteable(outputName):
  if (outputName[0:5] == "gs://") or (outputName[0:5] == "s3://"):
    OptError("Streaming support not enabled for this file type. Please use a local file and then upload it")
  outputName = outputName.rstrip('/')
  outDir = GetHostFolder(outputName)
  if os.path.isdir(outDir) == False:
    OptError("Output " + outputName + " cannot be written. Directory doesn't exist. Exiting...")
  elif os.access(outDir, os.W_OK) == False:
    OptError("Output directory for " + outputName + " does not have write permission. Exiting...")
  finalOutName = GetHostFile(outputName)
  return finalOutName

def IsDirWriteable(outputDir):
  outputDir = outputDir.rstrip('/')
  fullOutputDir = GetFullDirPath(outputDir)
  outDir = GetHostFolder(fullOutputDir)
  if os.path.exists(fullOutputDir):
    outDir = fullOutputDir
  if os.path.isdir(outDir) == False:
    if not os.path.exists(outDir):
      try:
        os.makedirs(outDir)
      except OSError as e:
        OptError("Could not create directory " + outDir + ". Exiting ...")
    else:
      OptError("Output " + outputDir + " cannot be written. A file with same name exists. Exiting...")
  elif os.access(outDir, os.W_OK) == False:
    OptError("Output directory at " + outputDir + " does not have write permission. Exiting...")
  if not os.path.exists(outputDir):
    try:
      os.makedirs(outputDir)
    except OSError as e:
      OptError("Could not create directory " + outputDir + ". Exiting ...")
  return fullOutputDir


def IsDirWriteableNoCreate(outputDir):
  fullOutputDir = GetFullDirPath(outputDir)
  outDir = GetHostFolder(fullOutputDir)
  if os.path.exists(fullOutputDir):
    outDir = fullOutputDir
  if os.path.isdir(outDir) == False:
    OptError("Output " + outputDir + " cannot be written. A file with same name exists. Exiting...")
  elif os.access(outDir, os.W_OK) == False:
    OptError("Output directory at " + outputDir + " does not have write permission. Exiting...")
  return fullOutputDir


def IsBamValid(inputName):
  if os.path.isdir(inputName):
    inName = GetFullDirPath(inputName)
    return inName
  else:
    return IsFileStreamReadable(inputName)


def IsOutVarValid(outputName):
  if os.path.isdir(outputName):
    outName = GetFullDirPath(outputName)
    return outName
  else:
    return IsFileStreamWritable(outputName)


def IsFileStreamReadable(inputName):
  if inputName[0:5] == "gs://":
    return IsGFileReadable(inputName)
  elif inputName[0:5] == "s3://":
    return IsS3FileReadable(inputName)
  else:
    return IsFileReadable(inputName)


def IsFileReadable(inputName):
  if inputName[0:5] == "gs://":
    OptError("Streaming support not enabled for this file type (" + inputName + "). Please download the file locally first")
  preserveFileSymlinks = False  # default behavior is to resolve symlinks
  if "--preserve-file-symlinks" in sys.argv:
    preserveFileSymlinks = True
  inFile = GetHostFile(inputName, _preserveFileSymlinks=preserveFileSymlinks)
  if os.path.exists(inFile) == False:
    if "--with-petagene-dir" in sys.argv:
      OptError("Input file " + inputName + " not found. Please check that the file exists and that you have preloaded the PetaLink library by setting the LD_PRELOAD environment variable. Exiting...")
    OptError("Input file " + inputName + " not found. Exiting...")
  if os.path.isfile(inFile) == False:
    if stat.S_ISFIFO(os.stat(inFile).st_mode) == False:
      OptError("Input file " + inputName + " not found. Exiting...")
  if os.access(inFile, os.R_OK) == False:
    OptError("Input file " + inputName + " does not have read permissions. Exiting...")
  return inFile


def IsMethylReferenceReadable(inputName):
  '''
  Is the fq2bam_meth methylation reference readable
  Based off of IsFileReadable
  '''
  inputNameOrig = inputName
  # check that original reference is readable (needs to be if using CRAM output)
  _ = IsFileReadable(inputNameOrig)
  inputName = inputName + ".bwameth.c2t"
  if inputName[0:5] == "gs://":
    OptError("Streaming support not enabled for this file type (" + inputName + "). Please download the file locally first")
  preserveFileSymlinks = False  # default behavior is to resolve symlinks
  if "--preserve-file-symlinks" in sys.argv:
    preserveFileSymlinks = True
  inFile = GetHostFile(inputName, _preserveFileSymlinks=preserveFileSymlinks)
  if os.path.exists(inFile) == False:
    OptError(f"Input file {inputName} not found. First run `python bwameth.py index {inputNameOrig}` using baseline bwa-meth and baseline bwa mem. Exiting...")
  if os.path.isfile(inFile) == False:
    if stat.S_ISFIFO(os.stat(inFile).st_mode) == False:
      OptError(f"Input file {inputName} not found. First run `python bwameth.py index {inputNameOrig}` using baseline bwa-meth and baseline bwa mem. Exiting...")
  if os.access(inFile, os.R_OK) == False:
    OptError("Input file " + inputName + " does not have read permissions. Exiting...")
  return inFile


def IsDirReadable(inputName):
  if inputName[0:5] == "gs://":
    OptError("Streaming support not enabled for this file type (" + inputName + "). Please download the file locally first")
  inputName = inputName.rstrip('/')
  inDirName = GetFullDirPath(inputName)
  if os.path.exists(inDirName) == False:
    OptError("Input Directory " + inputName + " not found. Exiting...")
  if os.path.isdir(inDirName) == False:
    OptError("Input Directory " + inputName + " not found. Exiting...")
  return inDirName


def IsResourceValid(resource):
  #Parse set name
  resourceCopy = resource
  try:
    pos = resourceCopy.index(",")
  except ValueError:
    OptError("Resource " + resource + " is missing at least one comma. Exiting...")
  name = resourceCopy[:pos]
  resourceCopy = resource[pos + 1:]

  #Parse set known
  try:
    pos = resourceCopy.index("known=")
  except ValueError:
    OptError("Resource " + resource + " does not contain known flag or is improperly formatted. Exiting...")
  resourceCopy = resourceCopy[pos + 6:]
  try:
    pos = resourceCopy.index(",")
  except ValueError:
    OptError("Resource " + resource + " is missing at least one comma. Exiting...")
  known = resourceCopy[:pos]
  if known != "true" and known != "false":
    OptError("Resource " + resource + " has invalid known boolean assignment \"" + known + "\". Exiting...")
  resourceCopy = resourceCopy[pos + 1:]

  #Parse set training
  try:
    pos = resourceCopy.index("training=")
  except ValueError:
    OptError("Resource " + resource + " does not contain training flag or is improperly formatted. Exiting...")
  resourceCopy = resourceCopy[pos + 9:]
  try:
    pos = resourceCopy.index(",")
  except ValueError:
    OptError("Resource " + resource + " is missing at least one comma. Exiting...")
  training = resourceCopy[:pos]
  if training != "true" and training != "false":
    OptError("Resource " + resource + " has invalid training boolean assignment \"" + training + "\". Exiting...")
  resourceCopy = resourceCopy[pos + 1:]

  #Parse set truth
  try:
    pos = resourceCopy.index("truth=")
  except ValueError:
    OptError("Resource " + resource + " does not contain truth flag or is improperly formatted. Exiting...")
  resourceCopy = resourceCopy[pos + 6:]
  try:
    pos = resourceCopy.index(",")
  except ValueError:
    OptError("Resource " + resource + " is missing at least one comma. Exiting...")
  truth = resourceCopy[:pos]
  if truth != "true" and truth != "false":
    OptError("Resource " + resource + " has invalid truth boolean assignment \"" + truth + "\". Exiting...")
  resourceCopy = resourceCopy[pos + 1:]

  #Parse set prior
  try:
    pos = resourceCopy.index("prior=")
  except ValueError:
    OptError("Resource " + resource + " does not contain prior value or is improperly formatted. Exiting...")
  resourceCopy = resourceCopy[pos + 6:]
  try:
    pos = resourceCopy.index(":")
  except ValueError:
    OptError("Resource " + resource + " is missing colon after prior value. Exiting...")
  prior = resourceCopy[:pos]
  try:
    prior = float(prior)
  except ValueError:
    OptError("Resource " + resource + " has invalid prior value \"" + prior + "\". Exiting...")
  resourceCopy = resourceCopy[pos + 1:]

  #Check that it is not gzipped
  if len(resourceCopy) <= 3:
    OptError("Resource " + resource + " has invalid file name \"" + resourceCopy + "\". Exiting...")
  if resourceCopy[-3:] == ".gz":
    OptError("Resource vcf " + resourceCopy + " cannot be in gzipped format. Exiting...")

  #Test vcf file name
  fullPath = IsFileReadable(resourceCopy)
  resource = resource[0:resource.index(":") + 1] + fullPath
  #resourceInfo = resource[:resource.index(":")]
  return resource


def GetHostFolder(inputName):
  if inputName == None:
    OptError("A required folder name cannot be empty")
  inputName = os.path.realpath(inputName)
  if os.path.isabs(inputName):
    return os.path.abspath(os.path.dirname(inputName))
  else:
    return os.path.abspath(os.path.dirname(os.getcwd() + '/' + inputName))


def GetUnmappedHostFolder(inputName):
  if inputName == None:
    OptError("A required folder name cannot be empty")
  if os.path.isabs(inputName):
    return os.path.abspath(os.path.dirname(inputName))
  else:
    return os.path.abspath(os.path.dirname(os.getcwd() + '/' + inputName))


def GetUnmappedDir(inputName):
  if inputName == None:
    OptError("A required folder name cannot be empty")
  if os.path.isabs(inputName):
    return inputName
  else:
    return os.path.abspath(os.getcwd() + '/' + inputName)


def GetHostFile(inputName, _preserveFileSymlinks=False):
  if inputName == None:
    OptError("A required file name cannot be empty")
  inName = inputName
  if not _preserveFileSymlinks:
    inName = os.path.realpath(inputName)
  if os.path.isabs(inName):
    return inName
  else:
    return os.path.abspath(os.getcwd() + '/' + inName)


def GetFullDirPath(dirName):
  if dirName == None:
    OptError("A required directory name cannot be empty")
  dirName = os.path.realpath(dirName.rstrip('/'))
  dirName = dirName.rstrip('/') + "/"
  if os.path.isabs(dirName):
    return os.path.abspath(os.path.dirname(dirName))
  else:
    return os.path.abspath(os.path.dirname(os.getcwd() + '/' + dirName))


def IsInFQList(fqName):
  if fqName[0] == '@':
    return fqName
  return IsFileStreamReadable(fqName)


def GetRGInfo(rgString):
  fields = rgString.split('\\t')
  rgID = ""
  sampleName = ""
  rgPU = ""
  rgLB = ""
  for rgField in fields:
    if len(rgField) > 3:
      if rgField[0:3] == "ID:":
        rgID = rgField[3:]
      if rgField[0:3] == "SM:":
        sampleName = rgField[3:]
      if rgField[0:3] == "PU:":
        rgPU = rgField[3:]
      if rgField[0:3] == "LB:":
        rgLB = rgField[3:]
  if rgID == "":
    OptError("Read group information must have ID field")
  if rgPU == "":
    OptError("Read group information must have PU field")
  if sampleName == "":
    OptError("Read group information must have SM field")
  if rgLB == "":
    OptError("Read group information must have LB field")
  return sampleName, rgID, rgPU, rgLB


def CheckReadGroups(fqFiles):
  #Check all fq groups have sample name
  sampleName, rgID, rgPU, rgLB = GetRGInfo(fqFiles[0][2])
  RGIDs = {rgID}
  RGPUs = {rgPU}
  for fqGroup in fqFiles[1:]:
    newSampleName, newRGID, newRGPU, newRGLB = GetRGInfo(fqGroup[2])
    if sampleName != newSampleName:
      OptError("User provided read groups should have same sample name for all read groups. Two sample names found " + sampleName + " and " + newSampleName)
    #if rgLB != newRGLB:
    #  OptError("User provided read groups should have same LB for all read groups. Two LB found " + rgLB + " and " + newRGLB)
    if newRGID in RGIDs:
      OptError("Different set of fastq files in same fastq group cannot have same read group ID. ID: " + newRGID + " repeats multiple times" )
    if newRGPU in RGPUs:
      OptError("Different set of fastq files in same fastq group cannot have same read group PU. PU: " + newRGPU + " repeats multiple times" )
  return sampleName


def CheckSEReadGroups(fqFiles):
  #Check all fq groups have sample name
  sampleName, rgID, rgPU, rgLB = GetRGInfo(fqFiles[0][1])
  RGIDs = {rgID}
  RGPUs = {rgPU}
  for fqGroup in fqFiles[1:]:
    newSampleName, newRGID, newRGPU, newRGLB = GetRGInfo(fqGroup[1])
    if sampleName != newSampleName:
      OptError("User provided read groups should have same sample name for all read groups. Two sample names found " + sampleName + " and " + newSampleName)
    #if rgLB != newRGLB:
    #  OptError("User provided read groups should have same LB for all read groups. Two LB found " + rgLB + " and " + newRGLB)
    if newRGID in RGIDs:
      OptError("Different set of fastq files in same fastq group cannot have same read group ID. ID: " + newRGID + " repeats multiple times" )
    if newRGPU in RGPUs:
      OptError("Different set of fastq files in same fastq group cannot have same read group PU. PU: " + newRGPU + " repeats multiple times" )
  return sampleName

def GetIDPrefixFromBam(bamFile):
  rgID = None
  OptMesg("Automatically generating ID prefix")
  cmd1 = "samtools view " + bamFile + " | head -n 1"
  fqGroup = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
  if (fqGroup.returncode != 0):
    OptError("Cannot read from input se bam file:" + bamFile)
  rgLine = fqGroup.stdout.split('\t')[0]
  infoFields = rgLine.split(":")
  if len(infoFields[0]) < 2:
    rgID="DefRG"
  if len(infoFields) != 7:
    rgID = infoFields[0]
    if len(rgID) > 30:
      rgID = rgID[0:30]
  else:
    rgID = infoFields[2]
  return rgID

def GetIDPrefixFromFastq(fastqFileName):
  rgID = None
  OptMesg("Automatically generating ID prefix")
  firstLine = ""

  if fastqFileName[-3:] == ".gz":
    try:
      fastqFile = gzip.open(fastqFileName, "rb")
      # error check here that it is a valid file
      # note: decode using "replace" for errors so that we will not raise an exception
      # if it is an invalid unicode sequence we will catch it when trying to decode the FASTQ
      # see: https://docs.python.org/3/library/stdtypes.html#bytes.decode and
      # https://docs.python.org/3/library/codecs.html#error-handlers
      firstLine = fastqFile.readline().decode(encoding="utf-8", errors="replace")
      fastqFile.close()
    except (OSError, ValueError):
      OptError(fastqFileName + " is not a valid gzip file. Please check it.")
  else:
    # errors param refers to what the file obj should do if there are errors decoding the text file
    # Ref in docs: https://docs.python.org/3/library/functions.html#open
    # replacing invalid utf-8 characters with the ? character so that it then gets caught later
    # and we do not produce an exception here
    fastqFile = open(fastqFileName, "r", errors="replace")
    firstLine = fastqFile.readline()
    fastqFile.close()

  if len(firstLine) == 0:
    OptError("First line empty in fastq file")
  if firstLine[0] != "@":
    file_descriptor_str = "fastq file"
    if fastqFileName[-3:] == ".gz":
      file_descriptor_str = "decompressed fastq gzip file"
    OptError(f"First line of {file_descriptor_str} does not start with '@'. Please check the fastq file: {fastqFileName}")


  firstLine = firstLine.rstrip('\n')
  infoFields = firstLine.split(" ")[0].split(":")
  if len(infoFields[0]) < 2:
    rgID="DefRG"
  if len(infoFields) != 7:
    rgID = infoFields[0].strip("@")
    if len(rgID) > 30:
      rgID = rgID[0:30]
  else:
    rgID = infoFields[2]
  return rgID


def GetCounterFromFastq(fastqFileName, counter):
  firstLine = ""

  if fastqFileName[-3:] == ".gz":
    fastqFile = gzip.open(fastqFileName, "rb")
    firstLine = fastqFile.readline().decode('utf-8')
    fastqFile.close()
  else:
    fastqFile = open(fastqFileName, "r")
    firstLine = fastqFile.readline()
    fastqFile.close()

  if firstLine[0] != "@":
    OptError("First Line of fastq file does not start with @.\n" + firstLine + "\nPlease check the fastq file: " + fastqFileName)

  infoFields = firstLine.split(" ")[0].split(":")
  rgCounter = -1
  if len(infoFields) == 5:
    rgCounter = infoFields[1]
  elif len(infoFields) == 7:
    rgCounter = infoFields[3]
  else:
    OptError("Could not find counter for ID")
  return rgCounter


def GetVolumesFromFastqList(fastq_list):
  #Read in the list of fastq files
  f = open(fastq_list, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  volumes = []
  for fastqFiles in fq_list:
    fqGroup = fastqFiles.split(' ')
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")

    #Check if file exists and get full file names
    newVolume1 = IsFileStreamReadable(fqGroup[0])
    newVolume2 = IsFileStreamReadable(fqGroup[1])
    if newVolume1 not in volumes:
      volumes.append(newVolume1)
    if newVolume2 not in volumes:
      volumes.append(newVolume2)

  return volumes


def check_fastq_files(fastqFiles, rgSM, rgLB, rgPL, rgIDPrefix):
  #Check if user has provided read groups
  maxLen = len(fastqFiles[0])
  for fqGroup in fastqFiles:
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every --in-fq option can only have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"")

  #Check if file exists and get full file names
  for idx in range(0, len(fastqFiles)):
    fastqFiles[idx][0] = IsFileStreamReadable(fastqFiles[idx][0])
    fastqFiles[idx][1] = IsFileStreamReadable(fastqFiles[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 3:
    rgSM = CheckReadGroups(fastqFiles)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqFiles:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqFiles:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])
  return rgSM

def check_se_bam(bamFile, rgSM, rgLB, rgPL, rgIDPrefix):
  cmd1 = "samtools view " + bamFile + " -H | grep \"^@RG\" | head -n 1"
  fqGroup = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
  if (fqGroup.returncode != 0):
      OptError("Cannot read from input se bam file:" + bamFile)

  rgLine = fqGroup.stdout
  if len(rgLine) == 0:
    if rgSM == None:
      rgSM = "sample"
    if rgLB== None:
      rgLB = "lib1"
    if rgPL == None:
      rgPL = "bar"
    if rgIDPrefix == None:
      rgIDPrefix = GetIDPrefixFromBam(bamFile)
    rgLine = "@RG\\tID:%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s" % (rgIDPrefix, rgLB, rgPL, rgSM, rgIDPrefix)
  return rgLine

def check_fastq_list(fastq_list, rgSM, rgLB, rgPL, rgIDPrefix): # UNUSED, see line 815
  #Read in the list of fastq files
  f = open(fastq_list, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups
  fastqFiles = []
  maxLen = len(fq_list[0].split(' '))
  for line in fq_list:
    fqGroup = line.split(' ')
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"").strip("\'")

    fastqFiles.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqFiles)):
    fastqFiles[idx][0] = IsFileStreamReadable(fastqFiles[idx][0])
    fastqFiles[idx][1] = IsFileStreamReadable(fastqFiles[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 3:
    rgSM = CheckReadGroups(fastqFiles)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqFiles:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqFiles:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])
    fqGroup[2] = "\"" + fqGroup[2] + "\""

  #Create a new verified text file name
  checked_file = fastq_list
  is_txt = (fastq_list[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqFiles:
    output_file.write(" ".join(fqGroup) + "\n")
  output_file.close()
  return checked_file

def check_se_fastq_files_minimap2(fastqFiles, rgSM, rgLB, rgPL, rgIDPrefix):
  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"
  if rgIDPrefix == None:
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0])

  fastqFiles.append("@RG\\tID:%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s" % (rgIDPrefix, rgLB, rgPL, rgSM, rgIDPrefix))

  OptMesg("Read group created for " + fastqFiles[0])
  OptMesg(fastqFiles[-1])

def gen_rg_from_bam_input(bamFile, rgSM, rgLB, rgPL, rgIDPrefix):
  #Check for samtools
  if shutil.which('samtools') == None:
    print("samtools not detected. Please install first")
    exit(1)

  #Run samtools to extract RG line
  rgExtractionCmd = "samtools view " + bamFile[0] + " -H | grep -m 1 \"^@RG\""
  rgLine = subprocess.run(rgExtractionCmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)

  #Change RG values to user specified
  constructedRG = []
  if rgLine.returncode != 0 or rgLine.stdout == None:
    #No RG line or samtools failed, contruct new RG line
    if rgSM == None:
      rgSM = "sample"
    if rgLB == None:
      rgLB = "lib1"
    if rgPL == None:
      rgPL = "bar"
    if rgIDPrefix == None:
      #extract ID from first record
      recExtractionCmd = "samtools view " + bamFile[0] + " | grep -m 1 \"^[^#]\" | awk '{print $1}'"
      recLine = subprocess.run(recExtractionCmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
      if recLine.returncode != 0 or recLine.stdout == None:
        print("Reading from " + bamFile[0] + " failed, the input might be corrupted, exiting...")
        exit(1)
      rgIDPrefix = recLine.stdout.split(":")[0].strip('\n')
    bamFile.append("@RG\\tID:%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s" % (rgIDPrefix, rgLB, rgPL, rgSM, rgIDPrefix))
  else:
    for entry in rgLine.stdout.split('\t'):
      if entry[0:2] == "SM" and rgSM != None:
        constructedRG.append("SM:" + rgSM)
      elif entry[0:2] == "LB" and rgLB != None:
        constructedRG.append("LB:" + rgLB)
      elif entry[0:2] == "PL" and rgPL != None:
        constructedRG.append("PL:" + rgPL)
      elif entry[0:2] == "ID" and rgIDPrefix != None:
        constructedRG.append("ID:" + rgIDPrefix)
      elif entry[0:2] == "PU" and rgIDPrefix != None:
        constructedRG.append("PU:" + rgIDPrefix)
      else:
        constructedRG.append(entry)
    bamFile.append("\\t".join(constructedRG).strip('\n'))

  OptMesg("Read group created for " + bamFile[0])
  OptMesg(bamFile[1])

def check_se_fastq_files(fastqFiles, rgSM, rgLB, rgPL, rgIDPrefix, isRNA=False):
  #Check if user has provided read groups
  maxLen = len(fastqFiles[0])
  for fqGroup in fastqFiles:
    fqlen = len(fqGroup)
    if (fqlen != 1) and (fqlen != 2):
      OptError("Every --in-se-fq option can only have 1 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 2:
      fqGroup[1] = fqGroup[1].strip("\"")
    if fqlen == 1 and "--with-petagene-dir" in sys.argv:
      OptError("Must specify read group for petagene input")


  #Check if file exists and get full file names
  for idx in range(0, len(fastqFiles)):
    fastqFiles[idx][0] = IsFileStreamReadable(fastqFiles[idx][0])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 2:
    rgSM = CheckSEReadGroups(fastqFiles)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])

  #Automatically add read group if not provided
  if (maxLen == 1):
    counter = 0
    for fqGroup in fastqFiles:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqFiles:
    OptMesg("Read group created for " + fqGroup[0])
    OptMesg(fqGroup[1])
  return rgSM

def check_fastq_list(fastq_list, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastq_list, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups
  fastqFiles = []
  maxLen = len(fq_list[0].split(' '))
  for line in fq_list:
    fqGroup = line.split(' ')
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"").strip("\'")
    fastqFiles.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqFiles)):
    fastqFiles[idx][0] = IsFileStreamReadable(fastqFiles[idx][0])
    fastqFiles[idx][1] = IsFileStreamReadable(fastqFiles[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 2:
    rgSM = CheckReadGroups(fastqFiles)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqFiles:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqFiles:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])
    fqGroup[2] = "\"" + fqGroup[2] + "\""

  #Create a new verified text file name
  checked_file = fastq_list
  is_txt = (fastq_list[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqFiles:
    output_file.write(" ".join(fqGroup) + "\n")
  output_file.close()
  return checked_file

def check_pe_fastq_input_giraffe(fastqFiles, rgSM, rgLB, rgPL, rgIDPrefix, rgPU):
  #Check if file exists and get full file names
  fastqFiles[0][0] = IsFileStreamReadable(fastqFiles[0][0])
  fastqFiles[0][1] = IsFileStreamReadable(fastqFiles[0][1])
  #Do default assignment for SM
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"
  #Generate Read Group if not provided
  if rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])
    counter = 1
    rgIDPrefix = "%s.%s" % (rgIDPrefix, counter)
  if rgPU == None:
    rgPU = rgIDPrefix
  OptMesg("Read group for " + fastqFiles[0][0] + ":")
  OptMesg("@RG\\tID:%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s" % (rgIDPrefix, rgLB, rgPL, rgSM, rgPU))
  return rgSM, rgLB, rgPL, rgIDPrefix, rgPU

def check_se_fastq_input_giraffe(fastqFiles, rgSM, rgLB, rgPL, rgIDPrefix, rgPU):
  #Check if file exists and get full file names
  fastqFiles[0][0] = IsFileStreamReadable(fastqFiles[0][0])
  #Do default assignment for SM 
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"
  #Generate Read Group if not provided
  if rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqFiles[0][0])
    counter = 1
    rgIDPrefix = "%s.%s" % (rgIDPrefix, counter)
  if rgPU == None:
    rgPU = rgIDPrefix
  OptMesg("Read group for " + fastqFiles[0][0] + ":")
  OptMesg("@RG\\tID:%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s" % (rgIDPrefix, rgLB, rgPL, rgSM, rgPU))
  return rgSM, rgLB, rgPL, rgIDPrefix, rgPU

def check_fastq_list_se_giraffe(fastqListSe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastqListSe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups in the file
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 1) and (fqlen != 2):
      OptError("Every line from --in-se-fq-list must have 1 fastq file and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 2:
      fqGroup[1] = fqGroup[1].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 2:
    rgSM = CheckSEReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 1):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0])
    OptMesg(fqGroup[1])
    fqGroup[1] = "\"" + fqGroup[1] + "\""

  #Check again after generating and before creating the verified file
  CheckSEReadGroups(fastqGroups)

  #Create a new verified text file name
  checked_file = fastqListSe
  is_txt = (fastqListSe[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqGroups:
    output_file.write(" ".join(filter(None, fqGroup)) + "\n") # remove `None` inserted earlier
  output_file.close()
  return checked_file

def check_fastq_list_pe_giraffe(fastqListPe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastqListPe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])
    fastqGroups[idx][1] = IsFileStreamReadable(fastqGroups[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 3:
    rgSM = CheckReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])
    fqGroup[2] = "\"" + fqGroup[2] + "\""

  #Check again after generating and before creating the verified file
  CheckReadGroups(fastqGroups)

  #Create a new verified text file name
  checked_file = fastqListPe
  is_txt = (fastqListPe[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqGroups:
    output_file.write(" ".join(fqGroup) + "\n")
  output_file.close()
  return checked_file

def check_fastq_list_se_bwalib(fastqListSe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastqListSe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups in the file
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 1) and (fqlen != 2):
      OptError("Every line from --in-se-fq-list must have 1 fastq file and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 2:
      fqGroup[1] = fqGroup[1].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 2:
    rgSM = CheckSEReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 1):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0])
    OptMesg(fqGroup[1])
    fqGroup[1] = "\"" + fqGroup[1] + "\""

  #Check again after generating and before creating the verified file
  CheckSEReadGroups(fastqGroups)

  #Create a new verified text file name
  checked_file = fastqListSe
  is_txt = (fastqListSe[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqGroups:
    output_file.write(" ".join(filter(None, fqGroup)) + "\n") # remove `None` inserted earlier
  output_file.close()
  return checked_file

def check_fastq_list_pe_bwalib(fastqListPe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastqListPe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])
    fastqGroups[idx][1] = IsFileStreamReadable(fastqGroups[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 3:
    rgSM = CheckReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])
    fqGroup[2] = "\"" + fqGroup[2] + "\""

  #Check again after generating and before creating the verified file
  CheckReadGroups(fastqGroups)

  #Create a new verified text file name
  checked_file = fastqListPe
  is_txt = (fastqListPe[-4:] == ".txt")
  if is_txt:
    checked_file = checked_file[:-4] + "_verified.txt"
  else:
    checked_file = checked_file + "_verified.txt"

  #Write each fq group to a new line in the text file for fq2bam input
  output_file = open(checked_file, "w+")
  for fqGroup in fastqGroups:
    output_file.write(" ".join(fqGroup) + "\n")
  output_file.close()
  return checked_file


def check_fastq_list_pe_rna_fq2bam(fastqListPe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of pair-ended fastq files
  f = open(fastqListPe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 2) and (fqlen != 3):
      OptError("Every line from --in-fq-list must have 2 fastq files and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide a read group for all sets of fastq files")
    if fqlen == 3:
      fqGroup[2] = fqGroup[2].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])
    fastqGroups[idx][1] = IsFileStreamReadable(fastqGroups[idx][1])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 3:
    rgSM = CheckReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 2):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0] + " and " + fqGroup[1])
    OptMesg(fqGroup[2])

  #Check again after generating and before returning
  CheckReadGroups(fastqGroups)

  return fastqGroups


def check_fastq_list_se_rna_fq2bam(fastqListSe, rgSM, rgLB, rgPL, rgIDPrefix):
  #Read in the list of fastq files
  f = open(fastqListSe, "r")
  fq_list = f.read().strip("\n").split("\n")
  f.close()

  #Check if user has provided read groups in the file
  fastqGroups = []
  maxLen = len(fq_list[0].split())
  for line in fq_list:
    fqGroup = line.split()
    fqlen = len(fqGroup)
    if (fqlen != 1) and (fqlen != 2):
      OptError("Every line from --in-se-fq-list must have 1 fastq file and an optional read group")
    if fqlen != maxLen:
      OptError("If one set of fastq files has a user provided read group, user should provide " +
               "a read group for all sets of fastq files")
    if fqlen == 2:
      fqGroup[1] = fqGroup[1].strip("\"").strip("\'")
    fastqGroups.append(fqGroup)

  #Check if file exists and get full file names
  for idx in range(0, len(fastqGroups)):
    fastqGroups[idx][0] = IsFileStreamReadable(fastqGroups[idx][0])

  #Do default assignments for LB, SM and PL if they are none
  if rgSM == None:
    rgSM = "sample"
  if rgLB== None:
    rgLB = "lib1"
  if rgPL == None:
    rgPL = "bar"

  #Check if read groups are consistent across groups
  if maxLen == 2:
    rgSM = CheckSEReadGroups(fastqGroups)
  elif rgIDPrefix == None:
    #Generate ID Prefix from fastq file
    rgIDPrefix = GetIDPrefixFromFastq(fastqGroups[0][0])

  #Automatically add read group if not provided
  if (maxLen == 1):
    counter = 0
    for fqGroup in fastqGroups:
      counter += 1
      fqGroup.append("@RG\\tID:%s.%s\\tLB:%s\\tPL:%s\\tSM:%s\\tPU:%s.%s" % (rgIDPrefix, counter, rgLB, rgPL, rgSM, rgIDPrefix, counter))

  #Print read group information
  for fqGroup in fastqGroups:
    OptMesg("Read group created for " + fqGroup[0])
    OptMesg(fqGroup[1])

  #Check again after generating and before creating the verified file
  CheckSEReadGroups(fastqGroups)

  return fastqGroups


def find_bwa_opt_matches(bwa_options: str, option: str):
  pattern = re.compile(option + r" \d+")
  if bwa_options is not None:
    matches = pattern.findall(bwa_options)
  else:
    matches = []
  return matches


def check_and_add_bwameth_option(bwa_options, option, default_value):
  '''
  Checks if a bwa-meth option has been added already. If it has been added once, warn the user.
  Multiple options will fail. If no option is passed then the default is put in.
  '''
  pattern = re.compile(option + r" \d+")
  if bwa_options is not None:
    matches = pattern.findall(bwa_options)
  else:
    matches = []
  if len(matches) > 1:
    OptError(f"Passed more than one instance of `{option}`. Please only use one")
  elif len(matches) > 0:
    OptMesg(f"Warning: overriding default value for `{option}` in fq2bam_meth")
    # leave it in.. don't modify
  else:
    # go with default bwa-meth option
    if bwa_options is not None:
      bwa_options += f" {option} {default_value}"
    else:
      bwa_options = f"{option} {default_value}"
  return bwa_options

def get_signal_name(code: int) -> str:
  try:
    signame = signal.Signals(code).name
  except ValueError:
    signame = "Unknown POSIX signal"
  return f"[{signame}: {code}]"

def handle_signal_vals(signalcode: int):
  signame = get_signal_name(signalcode)
  outstring = f"Process terminated with signal {signame}."
  # special message for SIGKILL and SIGINT
  if signalcode == signal.SIGKILL.value:
    outstring += f" {signal.SIGKILL.name} cannot be caught. A common reason for SIGKILL is running out of host memory. If the user has root access, they may be able to check by running `sudo journalctl -k --since \"<#> minutes ago\" | grep \"Killed process\"` to see the reason why processes were recently killed."
  elif signalcode == signal.SIGINT.value:
    outstring += f" {signal.SIGINT.name} is typically received when the user presses Ctrl+C."
  print(textwrap.fill(outstring, width=120))

def handle_return_vals(retVal: int):
  # https://docs.python.org/3.10/library/subprocess.html#subprocess.Popen.returncode
  # "A negative value -N indicates that the child was terminated by signal N (POSIX only)."
  if retVal < 0:
    retValP = -1 * retVal
    handle_signal_vals(retValP)
  elif retVal == 1:
    # we return with return value 1 from PbError
    print("Process exited with failure. Please check the logs.")
  elif retVal > 0:
    print(f"Process exited with error code: {retVal}.")
