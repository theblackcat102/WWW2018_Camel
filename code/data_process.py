import string
import re
import numpy
import cPickle as pkl
import six.moves.cPickle as pickle
from collections import OrderedDict
import glob
import os
import sys
import random
from subprocess import Popen, PIPE
import argparse
from tqdm import tqdm


# input arguments
parser = argparse.ArgumentParser(description='data process for Camel')
parser.add_argument('--author_num', type = int, default = 28649,
				   help = 'max id of author')
parser.add_argument('--paper_num', type = int, default = 21046,
				   help = 'max id of paper')
parser.add_argument('--venue_num', type = int, default = 18,
				   help = 'max id of venue')
parser.add_argument('--paperT', type = int, default = 2012,
				   help = 'split time of train/test data')
parser.add_argument('--walk_n', type = int, default = 5,
				   help = 'number of walk per node')
parser.add_argument('--walk_l', type = int, default = 20,
				   help = 'walk len')
parser.add_argument('--data_path', type=str, default='../data/Aminer-T-2010',
				   help='path to data')


args = parser.parse_args()
print(args)

# tokenizer.perl is from Moses: https://github.com/moses-smt/mosesdecoder/tree/master/scripts/tokenizer
tokenizer_cmd = ['../tokenizer.pl', '-l', 'en', '-q', '-']
A_max = args.author_num
P_max = args.paper_num
V_max = args.venue_num
split_T = args.paperT
data_path = args.data_path
walk_n = args.walk_n
walk_l = args.walk_l


class Paper:
	def __init__(self, title, author_list, time, venue, index, reference, abstract):
		self.title = title
		self.author_list = author_list
		self.time = time
		self.venue = venue
		self.index = index
		self.reference = reference
		self.abstract = abstract

	def __cmp__(self,other):
		return cmp(self.index,other.index) 


def read_paper_data():
	p_time = [0] * P_max
	p_venue = [0] * P_max
	p_list = []

	title_s = ''
	author_s = ''
	year_s = ''
	venue_s = 0
	index_s = 0
	reference_s = ''
	abstract_s = ''

	data_file = open(data_path + "/small_data_with_map_id.txt", "r") 
	print(data_file)
	for line in tqdm(data_file):
		line=line.strip()

		if line[0:2] == "#*":
			title_s = line[2:]
		elif line[0:2] == "#@":
			author_s = line[2:-1]
		elif line[0:2] == "#t":
			year_s = int(line[2:])
		elif line[0:2] == "#c":
			venue_s = int(line[2:])
		elif line[0:6] == "#index":
			index_s = int(line[6:])
		elif line[0:2] == "#%":
			reference_s = line[2:-1]
		elif line[0:2] == "#!":
			abstract_s = line[2:]
		elif line.strip() == '':
			p_temp = Paper(title_s, author_s, year_s, venue_s, index_s, reference_s, abstract_s)
			p_list.append(p_temp)
			p_time[index_s] = year_s
			p_venue[index_s] = venue_s
			title_s = ''
			author_s = ''
			year_s = ''
			venue_s = 0
			index_s = 0
			reference_s = ''
			abstract_s = ''

	data_file.close()
	print('Number of papers %d' % len(p_list))
	p_list = sorted(p_list)

	a_p_list_train = [[] for k in range(A_max)]
	a_p_list_test = [[] for k in range(A_max)]
	p_a_list_train = [[] for k in range(P_max)]
	p_a_list_test = [[] for k in range(P_max)]
	p_cite_p_list = [[] for k in range(P_max)]
	v_p_list_train =[[] for k in range(V_max)]

	unique_index = []
	for p in p_list:
		unique_index.append(p.index)
	print('Unique index %d\n' % len(set(unique_index)))

	count = 0
	appended_index = []
	for i in range(len(p_list)):
		paper = p_list[i]

		if p_time[paper.index] < split_T:
			v_p_list_train[int(paper.venue)].append(paper.index)

		if len(paper.reference) and p_time[paper.index] < split_T:
			reference_s = re.split(':', paper.reference)
			for k in range(len(reference_s)):
				p_cite_p_list[paper.index].append(int(reference_s[k]))
		elif len(paper.reference) and p_time[paper.index] >= split_T:
			reference_s = re.split(':', paper.reference)
			for k in range(len(reference_s)):
				if p_time[int(reference_s[k])] < split_T:
					p_cite_p_list[paper.index].append(int(reference_s[k]))

		author_s = [ a for a in paper.author_list.split(':') if len(a) >  0]

		for author in author_s:
			if p_time[paper.index] < split_T:
				count += 1
				appended_index.append(paper.index)
				p_a_list_train[paper.index].append(int(author))
				a_p_list_train[int(author)].append(paper.index)
			else:
				p_a_list_test[paper.index].append(int(author))
				a_p_list_test[int(author)].append(paper.index)
	print(len(set(appended_index)))
	print(count)

	p_a_list_train_f = open(data_path + "/paper-author-list-train.txt", "w")
	p_a_list_test_f = open(data_path + "/paper-author-list-test.txt", "w")
	a_p_list_train_f = open(data_path + "/author-paper-list-train.txt", "w")
	p_cite_p_list_f = open(data_path + "/paper-citation-list.txt", "w")
	p_v_f = open(data_path + "/paper-venue.txt", "w")
	v_p_list_train_f = open(data_path + "/venue-paper-list-train.txt", "w")
	train_count = 0

	for i in range(len(p_a_list_train)):
		if len(p_a_list_train[i]) != 0:
			train_count += 1
			p_a_list_train_f.write(str(i) + ":")
			for j in range(len(p_a_list_train[i])-1):
				p_a_list_train_f.write(str(p_a_list_train[i][j])+",")
			p_a_list_train_f.write(str(p_a_list_train[i][-1]))
			p_a_list_train_f.write("\n")
	test_count = 0
	for i in range(len(p_a_list_test)):
		if len(p_a_list_test[i]) != 0:
			test_count += 1
			p_a_list_test_f.write(str(i) + ":")
			for j in range(len(p_a_list_test[i])-1):
				p_a_list_test_f.write(str(p_a_list_test[i][j])+",")
			p_a_list_test_f.write(str(p_a_list_test[i][-1]))
			p_a_list_test_f.write("\n")
	for i in range(len(p_cite_p_list)):
		if len(p_cite_p_list[i]) != 0:
			p_cite_p_list_f.write(str(i)+":")
			for k in range(len(p_cite_p_list[i])-1):
				p_cite_p_list_f.write(str(p_cite_p_list[i][k])+",")
			p_cite_p_list_f.write(str(p_cite_p_list[i][-1]))
			p_cite_p_list_f.write("\n")

	for i in tqdm(range(len(p_list))):
		p_v_f.write(str(i) + "," + str(p_list[i].venue))
		p_v_f.write("\n")

	print(count)
	for t in range(A_max):
		if(len(a_p_list_train[t])):
			a_p_list_train_f.write(str(t)+":")
			for tt in range(len(a_p_list_train[t])-1):
				a_p_list_train_f.write(str(a_p_list_train[t][tt])+",")
			a_p_list_train_f.write(str(a_p_list_train[t][-1]))
			a_p_list_train_f.write("\n")

	p_a_neg = [[] for k in range(P_max)]
	p_a_neg_train_f = open(data_path + "/paper_author_neg_ids.txt", 'w')
	P_train = train_count
	for t in tqdm(range(P_max)):
		if len(p_a_list_train[t]):
			negative_authors = []
			while len(negative_authors) < 95:
				random_idx = random.randint(0, P_train)
				if random_idx == t or len(p_a_list_train[random_idx]) == 0:
					continue
				author = random.choice(p_a_list_train[random_idx])
				if author not in p_a_list_train[t]:
					negative_authors.append(author)
			p_a_neg[t] = negative_authors

		if len(p_a_list_test[t]):
			negative_authors = []
			while len(negative_authors) < 95:
				random_idx = random.randint(0, P_train)
				if random_idx == t or len(p_a_list_test[random_idx]) == 0:
					continue
				author = random.choice(p_a_list_test[random_idx])
				if author not in p_a_list_test[t]:
					negative_authors.append(author)
			p_a_neg[t] = negative_authors

	for t in range(P_max):
		if len(p_a_neg[t]):
			p_a_neg_train_f.write(str(t)+":")
			for tt in range(len(p_a_neg[t])-1):
				p_a_neg_train_f.write(str(p_a_neg[t][tt])+",")
			p_a_neg_train_f.write(str(p_a_neg[t][-1]))
			p_a_neg_train_f.write("\n")

	venue_count = 0
	for t in range(V_max):
		if(len(v_p_list_train[t])):
			venue_count += 1
			v_p_list_train_f.write(str(t)+":")
			for tt in range(len(v_p_list_train[t])-1):
				v_p_list_train_f.write(str(v_p_list_train[t][tt])+",")
			v_p_list_train_f.write(str(v_p_list_train[t][-1]))
			v_p_list_train_f.write("\n")
	print("Total venue : ", venue_count)
	print('Test cnt: ', test_count)

	p_a_list_train_f.close()
	p_a_list_test_f.close()
	a_p_list_train_f.close()
	p_cite_p_list_f.close()
	p_v_f.close()
	v_p_list_train_f.close()

	del a_p_list_train[:]
	del a_p_list_test[:]
	del p_a_list_train[:]
	del p_a_list_test[:]
	del p_cite_p_list[:]
	del v_p_list_train[:]

	return p_list


def tokenize(sentences):
	#print('Tokenizing...')
	text = "\n".join(sentences)
	tokenizer = Popen(tokenizer_cmd, stdin=PIPE, stdout=PIPE, shell=True)
	tok_text, _ = tokenizer.communicate(text)
	toks = tok_text.split('\n')[:-1]
	#print('Tokenizing done')
	return toks


def build_dict(p_list):
	abstracts = []
	for i in range(len(p_list)):
		abstracts.append(p_list[i].abstract)
	abstracts = tokenize(abstracts)

	print('Building dictionary...')
	wordcount = dict()
	for ss in abstracts:
		words = ss.strip().lower().split()
		for w in words:
			if w not in wordcount:
				wordcount[w] = 1
			else:
				wordcount[w] += 1

	counts = wordcount.values()
	keys = wordcount.keys()

	sorted_idx = numpy.argsort(counts)[::-1]

	worddict = dict()

	for idx, ss in enumerate(sorted_idx):
		worddict[keys[ss]] = idx+2  # leave 0 and 1 (UNK)

	print(numpy.sum(counts), ' total words ', len(keys), ' unique words')

	return worddict


def pickle_paper_content(p_list):
	dictionary = build_dict(p_list)

	abstracts = []
	for i in range(len(p_list)):
		abstracts.append(p_list[i].abstract)
	abstracts = tokenize(abstracts)

	paper_content = [None] * len(abstracts)
	for idx, ss in enumerate(abstracts):
		words = ss.strip().lower().split()
		paper_content[idx] = [dictionary[w] if w in dictionary else 1 for w in words]
	print('Content size %d' % len(paper_content))
	paper_index = []
	for i in range(len(p_list)):
		paper_index.append(p_list[i].index)

	dict_pikle_file = open(data_path + '/content.dict.pkl', 'w')
	pkl.dump(dictionary, dict_pikle_file, -1)
	dict_pikle_file.close()

	content_pikle_file = open(data_path + '/content.pkl', 'w')
	pkl.dump((paper_content, paper_index), content_pikle_file, -1)
	content_pikle_file.close()


def generate_metapath_walk():
	a_p_list_train = [[] for k in range(A_max)]
	p_a_list_train = [[] for k in range(P_max)]
	p_cite_p_list = [[] for k in range(P_max)]
	v_p_list_train =[[] for k in range(V_max)]
	p_venue = [0] * P_max
	a_p_list_train_file = data_path + "/author-paper-list-train.txt"
	p_a_list_train_file = data_path + "/paper-author-list-train.txt"
	p_cite_p_list_file = data_path + "/paper-citation-list.txt"
	v_p_list_train_file = data_path + "/venue-paper-list-train.txt"

	data_file = [a_p_list_train_file, p_a_list_train_file,\
	 			p_cite_p_list_file, v_p_list_train_file]

	for i in range(len(data_file)):
		data = open(data_file[i], "r")
		for line in data:
			line=line.strip()
			idx = string.atoi(re.split(':',line)[0])
			neigh_list = re.split(':',line)[1]
			neigh_list_idx = re.split(',',neigh_list)
			if i == 0:
				for j in range(len(neigh_list_idx)):
					a_p_list_train[idx].append('p'+str(neigh_list_idx[j]))
			elif i == 1:
				for j in range(len(neigh_list_idx)):
					p_a_list_train[idx].append('a'+str(neigh_list_idx[j]))
			elif i == 2:
				for j in range(len(neigh_list_idx)):
					p_cite_p_list[idx].append('p'+str(neigh_list_idx[j]))
			elif i == 3:
				for j in range(len(neigh_list_idx)):
					v_p_list_train[idx].append('p'+str(neigh_list_idx[j]))
		data.close()

	p_venue_file = open(data_path + "/paper-venue.txt", "r")
	for line in p_venue_file:
		line = line.strip()
		idx = string.atoi(re.split(',',line)[0])
		venue = string.atoi(re.split(',',line)[1])
		p_venue[idx] = ('v' + str(venue))
	p_venue_file.close()

	# generate APA random walk sequence
	APA_walk_file = open(data_path + "/APA_walk.txt", "w")
	for t in range(walk_n):
		for i in range(A_max):
			if len(a_p_list_train[i]):
				curNode = "a" + str(i)
				APA_walk_file.write(curNode + " ")
				for l in range(walk_l - 1):
					if curNode[0] == "a":
						curNode = int(curNode[1:])
						curNode = random.choice(a_p_list_train[curNode])
						APA_walk_file.write(curNode + " ")
					elif curNode[0] == "p":
						curNode = int(curNode[1:])
						curNode = random.choice(p_a_list_train[curNode])
						APA_walk_file.write(curNode + " ")
				APA_walk_file.write("\n")
	APA_walk_file.close()

	# generate APPA random walk sequence
	APPA_walk_file = open(data_path + "/APPA_walk.txt", "w")
	for t in range(walk_n):
		for i in range(A_max):
			if len(a_p_list_train[i]):
				curNode = "a" + str(i)
				preNode = "a" + str(i)
				APPA_path = []
				APPA_path.append(curNode)
				# APPA_walk_file.write(curNode + " ")
				try:
					for l in range(walk_l - 1):
						if curNode[0] == "a":
							preNode = curNode
							curNode = int(curNode[1:])
							curNode = random.choice(a_p_list_train[curNode])
							# APPA_walk_file.write(curNode + " ")	
							APPA_path.append(curNode)
						elif curNode[0] == "p":
							curNode = int(curNode[1:])
							if preNode[0] == "a" and len(p_cite_p_list[curNode]):
								preNode="p"+str(curNode)
								curNode=random.choice(p_cite_p_list[curNode])
								APPA_walk_file.write(curNode+" ")
								APPA_path.append(curNode)
							elif preNode[0] == "a" and len(p_cite_p_list[curNode]) == 0:
								preNode="p"+str(curNode)
								curNode = random.choice(p_a_list_train[curNode])
								APPA_walk_file.write(curNode+" ")
								APPA_path.append(curNode)
							elif preNode[0] == "p":
								preNode = "p" + str(curNode)
								curNode = random.choice(p_a_list_train[curNode])
								APPA_walk_file.write(curNode+" ")
								APPA_path.append(curNode)
				except IndexError:
					continue
				except TypeError:
					continue

				if len(APPA_path) == walk_l:
					APPA_walk_file.write(" ".join(APPA_path)+"\n")

	APPA_walk_file.close()

	print("generate APVPA random walk sequence")
	APVPA_walk_file = open(data_path + "/APVPA_walk.txt", "w")
	for t in tqdm(range(5)):
		for i in range(A_max):
			if len(a_p_list_train[i]):
				curNode = "a" + str(i)
				preNode = "a" + str(i)
				APVPA_path = []
				APVPA_path.append(curNode)
				# APVPA_walk_file.write(curNode + " ")
				try:
					for l in range(walk_l - 1):
						if curNode[0] == "a":
							preNode = curNode
							curNode = int(curNode[1:])
							curNode = random.choice(a_p_list_train[curNode])
							APVPA_path.append(curNode)
							# APVPA_walk_file.write(curNode + " ")
						elif curNode[0] == "p":
							curNode = int(curNode[1:])
							if preNode[0] == "a":
								preNode = "p" + str(curNode)
								curNode = p_venue[curNode]
								APVPA_path.append(curNode)
								# APVPA_walk_file.write(curNode+" ")
							else:
								preNode = "p" + str(curNode)
								curNode = random.choice(p_a_list_train[curNode])
								APVPA_path.append(curNode)
								# APVPA_walk_file.write(curNode+" ")
						elif curNode[0] == "v":
							preNode = curNode
							curNode = int(curNode[1:])
							curNode = random.choice(v_p_list_train[curNode])
							APVPA_path.append(curNode)
							# APVPA_walk_file.write(curNode+" ")
				except IndexError:
					continue
				except TypeError:
					continue

				if len(APVPA_path) == walk_l:
					APVPA_walk_file.write(" ".join(APVPA_path)+ "\n")
				else:
					print(len(APVPA_path))

	APVPA_walk_file.close()



paper_list = read_paper_data()


pickle_paper_content(paper_list)


generate_metapath_walk()




