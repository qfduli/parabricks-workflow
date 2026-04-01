#!/usr/bin/env python3

import os
import sys
import subprocess
import heapq
import shutil
import time
from exclude_contig import *
from pbutils import handle_return_vals

def wait_until_finish(processes):
	if_terminate = False
	for process in processes:
		if if_terminate == True:
			process.terminate()
		
		try:
			retVal = process.wait()
			if retVal != 0:
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
	name_len = []
	name_idx = {}
	#if (bam.endswith(".bam") == False):
	#	return name_len, name_idx
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

def check_header_consistency(name_len, name_idx, name_len2, name_idx2):
	if len(name_len) != len(name_len2):
		print("tumor and normal file headers contain different number of chromosomes, exit...")
		exit(1)

	for i in range(0, len(name_len)):
		if (name_len[i] != name_len2[i]):
			print("tumor and normal file headers are not consistent with each other, exit...")
			exit(1)

	for name in name_len:
		if name_idx[name[0]] != name_idx2[name[0]]:
			print("tumor and normal file headers are not consistent with each other, exit...")
			exit(1)


def merge_stats_files(all_tmp_files, outfile_name):
	total_callable = 0
	for tmp_file_name in all_tmp_files:
		file = open(tmp_file_name + ".stats", 'r')
		file.readline()
		total_callable = total_callable + int(file.readline().split()[-1])

	output_stat_file = open(outfile_name + ".stats", 'w')
	output_stat_file.write("statistic\tvalue\n")
	output_stat_file.write("callable\t" + str(total_callable))
	output_stat_file.close()

def run_scheduler(ref, bam, outfile_name, normal_bam, partition, gpus_per_partition, run_partition, alt_contigs, binary, bamout_name, htvc_para):
	

	name_len, name_idx = get_sorted_chr_from_header(bam)
	name_len2 = []
	name_idx2 = {}
	if (len(normal_bam) > 0):
		name_len2, name_idx2 = get_sorted_chr_from_header(normal_bam)
		#check if tumor-normal header consistent
		check_header_consistency(name_len, name_idx, name_len2, name_idx2)
	#name_len, name_idx = get_sorted_chr_from_postsort()


	if run_partition == False:
		rest_arg = ""
		if alt_contigs == False:
			for chr_name in name_len:
				rest_arg += " -L \"" + chr_name[0] + "\""
		cmd = ' '.join(sys.argv[1:]) + rest_arg
		if len(bamout_name) > 0:
			cmd += " -bamout " + bamout_name
		print(cmd)
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
			bamout_arg = ""
			if len(bamout_name) > 0:
				bamout_arg = " -bamout " + '.'.join(bamout_name.split('.')[0:-1]) + "_" + str(i) + "." + bamout_name.split('.')[-1]
			htvc_cmd = "CUDA_VISIBLE_DEVICES=" + devices + " " + binary + " " + ref + " " + bam + " " + str(gpus_per_partition) + " -o " + str(i) + ".vcf " +  all_interval_arg[i] + " " + bamout_arg + " " + htvc_para
			#print(htvc_cmd)
			process = subprocess.Popen(htvc_cmd, shell=True)
			all_processes.append(process)
			all_tmp_files.append(str(i) + ".vcf")

	wait_until_finish(all_processes)

	
	#if partition == 1:
	#	os.rename('0.vcf', outfile_name)
	#	return
	
	#merge all vcfs
	#time1 = time.perf_counter()
	output_file = open(outfile_name, 'w')
	write_header(output_file, all_tmp_files[0])

	all_input_files = []
	priority_q = []
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

	#merge all stats files
	merge_stats_files(all_tmp_files, outfile_name)

	#time2 = time.perf_counter()
	#print("vcf merge time", time2 - time1)

if __name__ == "__main__":

	time_start = time.time()
	if (len(sys.argv) < 7):
		print("run ./scheduler_mutect.py mutect_binary ref bam numberOfGPUS -o outfile  other_mutect_parameters")
		exit(1)

	user_interval = False
	alt_contigs = True
	gpus_per_partition = 2
	gpu_num = int(sys.argv[4])
	run_partition = False
	use_pon = False
	normal_bam = ""
	bamout_name = ""
	for i in range(7, 7 + len(sys.argv[7:])):
		if (sys.argv[i] == "-L"):
			user_interval = True
			i = i + 1

		elif (sys.argv[i] == "--no-alt-contigs"):
			alt_contigs = False
			sys.argv[i] = ""

		elif (sys.argv[i] == "--gpu-num-per-partition"):
			gpus_per_partition = int(sys.argv[i + 1]) 
			sys.argv[i] = ""
			sys.argv[i + 1] = ""
			i = i + 1

		elif (sys.argv[i] == "--run-partition"):
			run_partition = True

		elif (sys.argv[i] == "-pon"):
			use_pon = True

		elif (sys.argv[i] == "-normalbam"):
			normal_bam = sys.argv[i + 1]
			i = i + 1

		elif (sys.argv[i] == "-bamout"):
			bamout_name = sys.argv[i + 1]
			sys.argv[i] = ""
			sys.argv[i + 1] = ""
			i = i + 1

	if user_interval == True and alt_contigs == False:
		print("-L and --no-alt-contigs cannot be passed together")
		exit(1)

	if (alt_contigs == True):
		exclude_contigs.clear()

	if (len(bamout_name) > 0 and bamout_name.endswith('.bam') != True):
		print("Wrong file type passed to --htvc-bam-output, expecting a .bam file, exit...")
		exit(1)

	partition_num = gpu_num // gpus_per_partition
	
	if run_partition:
		if (gpu_num % gpus_per_partition != 0):
			print("--run-partition cannot work with " + str(gpu_num) + " gpus, make gpu number multiple of " + str(gpus_per_partition))
			exit(1)
		if user_interval:
			print("--run-partition cannot work with intervals, exit...")
			exit(1)
		if use_pon:
			print("--run-partition cannot work with --pon, exit...")
			exit(1)


	run_scheduler(sys.argv[2], sys.argv[3], sys.argv[6], normal_bam, partition_num, gpus_per_partition, run_partition, alt_contigs, sys.argv[1], bamout_name, ' '.join(sys.argv[7:]))

	total_run_time = (time.time() - time_start) / 60
	print("Variant caller done, total time: {:.1f} min".format(total_run_time))
	sys.stdout.flush()
