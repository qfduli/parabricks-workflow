#!/usr/bin/env python3

import os
import sys
import subprocess
import heapq
import shutil
import time
from exclude_contig import *
from pbutils import handle_return_vals, handle_signal_vals


def signal_handler(signal, _):
	handle_signal_vals(signal)


def wait_until_finish(processes):
	if_terminate = False
	for process in processes:
		if if_terminate == True:
			process.terminate()
		
		try:
			retVal = process.wait()
			if retVal > 128:
				# since these subprocesses are run with shell=True, refer to bash docs on how the signal is handled with the shell
				# https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
				# > When a command terminates on a fatal signal whose number is N, Bash uses the value 128+N as the exit status.
				handle_signal_vals(retVal - 128)
				if_terminate = True
			elif retVal != 0:
				handle_return_vals(retVal)
				if_terminate = True

		except Exception as e:
			print("Exit with exception")
			if_terminate = True

	if if_terminate == True:
		sys.exit(1)

def write_header(output_file, filename):
	with open(filename) as f:
		while True:
			line = f.readline()
			if (len(line) == 0 or line[0] != '#'):
				return
			output_file.write(line)

def get_sorted_chr_from_header(bam):
	#check samtools
	if shutil.which('samtools') == None:
		print("samtools not detected. Please install first")
		exit(1)
	cmd1 = "samtools view " + bam + " -H | grep \"^@SQ\" | cut -d '\t' -f 2 | cut -d : -f 2-"
	cmd2 = "samtools view " + bam + " -H | grep \"^@SQ\" | cut -d '\t' -f 3 | cut -d : -f 2-"
	chr_name = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	chr_len = subprocess.run(cmd2, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	if (chr_name.returncode != 0 or chr_name.stdout == ""):
		print("Reading header from " + bam + " failed, the input might be corrupted or missing SQ info, exit...")
		exit(1)
	if (chr_len.returncode != 0 or chr_len.stdout == ""):
		print("Reading header from " + bam + " failed, the input might be corrupted or missing SQ info, exit...")
		exit(1)
	all_chr = chr_name.stdout.split('\n')
	all_len = chr_len.stdout.split('\n')
	name_len = []
	name_idx = {}

	for i in range(0, len(all_chr)):
		if (len(all_chr[i])) and (all_chr[i] not in exclude_contigs):
			name_len.append((all_chr[i], int(all_len[i])))
			name_idx[all_chr[i]] = i

	
	return name_len, name_idx


def get_sorted_chr_from_header_txt():
	cmd1 = "cat header.txt | grep \"^@SQ\" | cut -d '\t' -f 2 | cut -d : -f 2-"
	cmd2 = "cat header.txt | grep \"^@SQ\" | cut -d '\t' -f 3 | cut -d : -f 2-"
	chr_name = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	chr_len = subprocess.run(cmd2, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	if (chr_name.returncode != 0 or chr_name.stdout == ""):
		print("Reading header from " + bam + " failed, the input might be corrupted or missing SQ info, exit...")
		exit(1)
	if (chr_len.returncode != 0 or chr_len.stdout == ""):
		print("Reading header from " + bam + " failed, the input might be corrupted or missing SQ info, exit...")
		exit(1)
	all_chr = chr_name.stdout.split('\n')
	all_len = chr_len.stdout.split('\n')
	name_len = []
	name_idx = {}

	for i in range(0, len(all_chr)):
		if (len(all_chr[i])):
			name_len.append((all_chr[i], int(all_len[i])))
			name_idx[all_chr[i]] = i

	
	return name_len, name_idx

def get_sorted_chr_from_vcf_header(vcf):
	#check bcftools
	if shutil.which('bcftools') == None:
		print("bcftools not detected. Please install first")
		exit(1)
	cmd1 = "bcftools index " + vcf + " -s | cut -d '\t' -f 1"
	cmd2 = "bcftools index " + vcf + " -s | cut -d '\t' -f 3"
	output1 = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	output2 = subprocess.run(cmd2, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	#here all_len is actually the number of reads for each chr, instead of the length
	all_chr = output1.stdout.split('\n')
	all_len = output2.stdout.split('\n')

	name_len = []
	name_idx = {}
	for i in range(0, len(all_chr)):
		if (len(all_chr[i])) and (all_chr[i] not in exclude_contigs):
			name_len.append((all_chr[i], int(all_len[i])))
			name_idx[all_chr[i]] = i

	
	return name_len, name_idx


def get_sorted_chr_from_postsort():

	name_len = []
	name_idx = {}

	chr_idx = 0
	with open("chrs.txt") as f:
		while True:
			line = f.readline()
			if len(line) == 0:
				break
			[chr_name, read_num] = line.split('\t')
			if chr_name not in exclude_contigs:
				name_idx[chr_name] = chr_idx
				name_len.append((chr_name, int(read_num)))
			chr_idx += 1

	return name_len, name_idx

def get_chr_prefix_and_bases_per_bin(name_len):
	nBins = 1000
	totalGenomeSize = 0
	chrLenPrefix = []
	for i in range(0, len(name_len)):
		chrLenPrefix.append(totalGenomeSize)
		totalGenomeSize += name_len[i][1]
	
	nBasesPerBin = (totalGenomeSize + nBins) // nBins
	return chrLenPrefix, nBasesPerBin

def merge_all_files_tmp(all_tmp_files, outfile_name, bin_boundary_idx):
	output_file = open(outfile_name, 'w')
	write_header(output_file, all_tmp_files[0])

	name_len, name_idx = get_sorted_chr_from_header_txt()
	chrLenPrefix, nBasesPerBin = get_chr_prefix_and_bases_per_bin(name_len)

	for i in range(0, len(all_tmp_files)):
		start_boundary_base = bin_boundary_idx[i] * nBasesPerBin
		end_boundary_base = bin_boundary_idx[i + 1] * nBasesPerBin
		file = open(all_tmp_files[i], 'r')
		while True:
			line = file.readline()
			if (len(line) == 0):
				break
			if (line[0] != '#'):
				tmp_idx = line.find('\t')
				cur_chr = line[0: tmp_idx]
				cur_pos = int(line[tmp_idx + 1: line.find('\t', tmp_idx + 1)])
				cur_base = chrLenPrefix[name_idx[cur_chr]] + int(cur_pos)
				if (cur_base > start_boundary_base and cur_base <= end_boundary_base):
					output_file.write(line)
				else:
					pass
		file.close()
	output_file.close()

def merge_all_files(all_tmp_files, outfile_name, name_idx):
	output_file = open(outfile_name, 'w')
	write_header(output_file, all_tmp_files[0])

	all_input_files = []
	priority_q = []
	#for i in range(0, int(partition)):
	for filename in all_tmp_files:
		file = open(filename, 'r')
		all_input_files.append(file)
	#ingore header and get the first chr in each file
	for file in all_input_files:
		while True:
			line = file.readline()
			if (len(line) == 0):
				break
			if (line[0] != '#'):
				chrName = line[0 : line.find('\t')]
				priority_q.append((name_idx[chrName], file, line, chrName))
				break

	heapq.heapify(priority_q)
	while len(priority_q):
		head = heapq.heappop(priority_q)
		output_file.write(head[2])
		cur_chr = head[3]
		while True:
			line = head[1].readline()
			if len(line) == 0:
				break
			new_chr = line[0 : line.find('\t')]
			if (new_chr != cur_chr):
				heapq.heappush(priority_q, (name_idx[new_chr], head[1], line, new_chr))
				break
			output_file.write(line)

	output_file.close()

def run_scheduler_tmp(ref, bam, outfile_name, partition, gpus_per_partition, streams_per_gpu, run_partition, alt_contigs, binary, imported_vcf, gvcf_output, htvc_para):
	if run_partition == False:
		rest_arg = ""
		#if alt_contigs == False:
		#	for chr_name in name_len:
		#		rest_arg += " -L \"" + chr_name[0] + "\""
		cmd = ' '.join(sys.argv[1:]) + rest_arg
		# print(cmd)
		process = subprocess.Popen(cmd, shell=True)
		wait_until_finish([process])
		return

	total_bin_num = 1000
	bin_per_partition = (total_bin_num + int(partition) - 1) // int(partition)
	bin_idx = 0
	
	all_processes = []
	all_tmp_files = []
	bin_boundary_idx = [0]
	device_idx = 0
	for i in range(0, int(partition)):
		devices = ""
		for j in range (0, int(gpus_per_partition)):
			if (j > 0):
				devices += ","
			devices += str(device_idx)
			device_idx += 1
		tmp_file = ""
		if gvcf_output == True:
			tmp_file = str(i) + ".g.vcf"
		else:
			tmp_file = str(i) + ".vcf"
		#we do bin_per_partition + 1 to overlap 1 bin between 2 partitions
		start_bin = bin_idx
		end_bin = start_bin + bin_per_partition - 1
		all_interval_arg = "-tmp-bin-start " + str(max(0, start_bin - 1)) + " -tmp-bin-num " + str(min(end_bin + 1, total_bin_num - 1) - max(0, start_bin - 1) + 1)
		bin_idx += bin_per_partition
		htvc_cmd = "CUDA_VISIBLE_DEVICES=" + devices + " " + binary + " " + str(gpus_per_partition) + " " + str(streams_per_gpu) + " --ref " + ref + " --reads " + bam + " -o " + tmp_file + " " +  all_interval_arg + " " + htvc_para
		# print(htvc_cmd)
		bin_boundary_idx.append(min(bin_idx, total_bin_num))
		process = subprocess.Popen(htvc_cmd, shell=True)
		all_processes.append(process)
		all_tmp_files.append(tmp_file)

	wait_until_finish(all_processes)

	
	#if partition == 1:
	#	os.rename('0.vcf', outfile_name)
	#	return
	merge_all_files_tmp(all_tmp_files, outfile_name, bin_boundary_idx)
	#no gvcf mode


def run_scheduler(deepsomatic_mode, ref, tumor_bam, normal_bam, outfile_name, partition, gpus_per_partition, streams_per_gpu, run_partition, alt_contigs, binary, imported_vcf, gvcf_output, htvc_para):
	
	if imported_vcf == "":
		name_len, name_idx = get_sorted_chr_from_header(tumor_bam)
	else:
		name_len, name_idx = get_sorted_chr_from_vcf_header(imported_vcf)
	#name_len, name_idx = get_sorted_chr_from_postsort()

	if run_partition == False:
		rest_arg = ""
		#if alt_contigs == False:
		#	for chr_name in name_len:
		#		rest_arg += " -L \"" + chr_name[0] + "\""
		cmd = ' '.join(sys.argv[1:]) + rest_arg
		# print(cmd)
		process = subprocess.Popen(cmd, shell=True)
		wait_until_finish([process])
		return

	sort_name_len = sorted(name_len, key=lambda x:x[1], reverse=True)

	all_interval_arg = []
	q = []

	for i in range(0, int(partition)):
		q.append((0, i))
		all_interval_arg.append("")
	
	heapq.heapify(q)

	for i in range(0, len(sort_name_len)):
		pair = sort_name_len[i]
		head = heapq.heappop(q)
		new_head = (head[0] + pair[1], head[1])
		all_interval_arg[head[1]] += " -L \"" + pair[0] + "\""
		heapq.heappush(q, new_head)

	all_processes = []
	all_tmp_files = []
	device_idx = 0
	for i in range(0, len(all_interval_arg)):
		if len(all_interval_arg[i]) > 0:
			devices = ""
			for j in range (0, int(gpus_per_partition)):
				if (j > 0):
					devices += ","
				devices += str(device_idx)
				device_idx += 1
			tmp_file = ""
			if gvcf_output == True:
				tmp_file = str(i) + ".g.vcf"
			else:
				tmp_file = str(i) + ".vcf"
			if deepsomatic_mode:
				htvc_cmd = "CUDA_VISIBLE_DEVICES=" + devices + " " + binary + " " + str(gpus_per_partition) + " " + str(streams_per_gpu) + " --ref " + ref + " --reads_tumor " + tumor_bam + " --reads_normal " + normal_bam + " -o " + tmp_file + " " +  all_interval_arg[i] + " " + htvc_para
			else:
				htvc_cmd = "CUDA_VISIBLE_DEVICES=" + devices + " " + binary + " " + str(gpus_per_partition) + " " + str(streams_per_gpu) + " --ref " + ref + " --reads " + tumor_bam + " -o " + tmp_file + " " +  all_interval_arg[i] + " " + htvc_para
			# print(htvc_cmd)
			process = subprocess.Popen(htvc_cmd, shell=True)
			all_processes.append(process)
			all_tmp_files.append(tmp_file)

	wait_until_finish(all_processes)

	
	#if partition == 1:
	#	os.rename('0.vcf', outfile_name)
	#	return
	merge_all_files(all_tmp_files, outfile_name, name_idx)
	#merge vcf output for gvcf mode
	if gvcf_output == True:
		outfile_name = outfile_name.replace(".g.vcf", ".vcf")
		all_tmp_vcf_files = [tmp.replace(".g.vcf", ".vcf") for tmp in all_tmp_files]
		merge_all_files(all_tmp_vcf_files, outfile_name, name_idx)


if __name__ == "__main__":

	time_start = time.time()
	if (len(sys.argv) < 18):
		print("run ./scheduler deepsomatic_binary numberOfGPUS streamsPerGPU --ref ref_file --reads_tumor tumor_bam --reads_normal normal_bam -o output_file -n CPU_threads_per_GPU --deepsomatic --process_somatic --model model_file other_htvc_parameters")
		exit(1)

	user_interval = False
	alt_contigs = True
	gpus_per_partition = 2
	gpu_num = int(sys.argv[2])
	streams_per_gpu = int(sys.argv[3])
	run_partition = False
	gvcf_output = False
	imported_vcf = ""
	read_tmp = False
	deepsomatic_mode = False
	pangenome_mode = False

	for i in range(12, len(sys.argv)):
		if (sys.argv[i] == "-L"):
			user_interval = True
			i = i + 1

		elif (sys.argv[i] == "--gpu-num-per-partition"):
			gpus_per_partition = int(sys.argv[i + 1]) 
			sys.argv[i] = ""
			sys.argv[i + 1] = ""
			i = i + 1

		elif (sys.argv[i] == "--run-partition"):
			run_partition = True
			sys.argv[i] = ""

		elif (sys.argv[i] == "--proposed_variants"):
			if (i + 1 == len(sys.argv)):
				print("missing proposed variants file name. Exiting...")
			imported_vcf = sys.argv[i + 1]

		elif (sys.argv[i] == "-g"):
			gvcf_output = True

		elif (sys.argv[i] == "-read-tmp"):
			read_tmp = True

		elif (sys.argv[i] == "--deepsomatic"):
			deepsomatic_mode = True
		
		elif (sys.argv[i] == "--pangenome"):
			pangenome_mode = True

	#if user_interval == True and alt_contigs == False:
	#	print("-L and --no-alt-contigs cannot be passed together")
	#	exit(1)

	#if (alt_contigs == True):
	#	exclude_contigs.clear()

	if (run_partition == True and len(imported_vcf) > 0 and gvcf_output == True):
		print("--run-partition cannot work with --proposed_variants in gvcf mode, turn off partition")
		run_partition = False

	partition_num = gpu_num // gpus_per_partition
	tumor_bam = None
	normal_bam = None
	outfile_name = None
	ref = sys.argv[5]
	num_positional_args = 0
	if deepsomatic_mode:
		tumor_bam = sys.argv[7]
		normal_bam = sys.argv[9]
		outfile_name = sys.argv[11]
		num_positional_args = 12
	else:
		tumor_bam = sys.argv[7]
		normal_bam = None
		outfile_name = sys.argv[9]
		num_positional_args = 10
	
	if run_partition:
		if (gpu_num % gpus_per_partition != 0):
			print("--run-partition cannot work with " + str(gpu_num) + " gpus, make gpu number multiple of " + str(gpus_per_partition))
			exit(1)
		if user_interval:
			print("--run-partition cannot work with intervals, exit...")
			exit(1)
		if (outfile_name.endswith('.gz')):
			print("--run-partition cannot work with .gz output, exit...")
			exit(1)
		if gvcf_output == True:
			if (outfile_name.endswith('.g.vcf') != True):
				print("output file name should end with .g.vcf in partition mode, exit...")
				exit(1)
		if (read_tmp == True and gvcf_output == True):
			print("Reading from tmp files cannot work with gvcf output in partition mode, exit...")
			exit(1)

	if (read_tmp == True):
		if user_interval:
			print("--read-from-tmp-dir cannot work with intervals, exit...")
			exit(1)


	if read_tmp == True:
		if deepsomatic_mode:
			print("Read from temp not supported for deepsomatic mode!")
			exit(1)
		run_scheduler_tmp(ref, tumor_bam, outfile_name, partition_num, gpus_per_partition, streams_per_gpu, run_partition, alt_contigs, sys.argv[1], imported_vcf, gvcf_output, ' '.join(sys.argv[num_positional_args:]))
	else:
		if deepsomatic_mode:
			run_scheduler(deepsomatic_mode, ref, tumor_bam, normal_bam, outfile_name, partition_num, gpus_per_partition, streams_per_gpu, run_partition, alt_contigs, sys.argv[1], imported_vcf, gvcf_output, ' '.join(sys.argv[num_positional_args:]))
		else: 
			run_scheduler(deepsomatic_mode, ref, tumor_bam, normal_bam, outfile_name, partition_num, gpus_per_partition, streams_per_gpu, run_partition, alt_contigs, sys.argv[1], imported_vcf, gvcf_output, ' '.join(sys.argv[num_positional_args:]))
	total_run_time = (time.time() - time_start) / 60
	if pangenome_mode:
		print("Pangenome Aware Deepvariant done, total time: {:.1f} min".format(total_run_time))
	elif deepsomatic_mode:
		print("Deepsomatic done, total time: {:.1f} min".format(total_run_time))
	else:
		print("Deepvariant done, total time: {:.1f} min".format(total_run_time))
	sys.stdout.flush()
