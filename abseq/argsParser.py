'''
    Short description: Quality Control Analysis of Immunoglobulin Repertoire NGS (Paired-End MiSeq)    
    Author: Monther Alhamdoosh    
    Python Version: 2.7
    Changes log: check git commits. 
'''
from __future__ import print_function
import os
import sys
import argparse
import yaml

from numpy import Inf
from Bio import SeqIO
from os.path import abspath

from abseq.IgRepertoire.igRepUtils import inferSampleName, detectFileFormat, safeOpen
from abseq.config import VERSION, DEFAULT_MERGER, DEFAULT_TOP_CLONE_VALUE, DEFAULT_TASK


def parseArgs(arguments=None):
    """
    Parses sys.argv's arguments and sanitize them. Checks the logic of arguments so calling program does not have
    to do any logic checking after this call.
    :param arguments: custom arguments or sys.argv (default)
    :return: argparse namespace object, using dot notation to retrieve value: args.value
    """

    parser, args = parseCommandLineArguments(arguments)

    # --------------------------------------------------------------------------------------------------------
    #                                       Canonicalize all values
    # --------------------------------------------------------------------------------------------------------
    args.task = args.task.lower()
    args.seqtype = args.seqtype.lower()
    args.chain = args.chain.lower()
    args.merger = args.merger.lower() if args.merger is not None else args.merger

    # --------------------------------------------------------------------------------------------------------
    #                              Check for -f1, -f2 file existence and expand path
    # --------------------------------------------------------------------------------------------------------
    # we CANNOT allow f1 to be missing if arguments is not None (i.e. it's parsing from a YAML file)
    # otherwise, it could be missing if -y/--yaml was provided
    if args.f1 is None or not os.path.exists(args.f1):
        if arguments is not None:
            parser.error("-f1 file not found!")
        elif args.yaml is None:
            parser.error("Either one of -f1/--file1 or -y/--yaml must be specified!")
    else:
        args.f1 = abspath(args.f1)
    if args.f2 is not None and not os.path.exists(args.f2):
        parser.error("-f2 file not found!")
    elif args.f2 is not None:
        args.f2 = abspath(args.f2)

    # parse arguments if args.f1 is a file, if it's a directory, allow IgMultiRepertoire to handle file pairings
    if args.f1 is not None and os.path.isfile(args.f1):
        # detect file format (either fastq or fasta); both should be the same type
        fmt = detectFileFormat(args.f1)
        if args.f2 is not None and detectFileFormat(args.f2) != fmt:
            parser.error("Detected mismatch in file extensions --file1 and --file2!"
                         " Both should be either FASTA or FASTQ.")
        args.fmt = fmt

        # check logic between f1, f2 and merger, setting default merger
        if args.merger is not None and args.f2 is None:
            parser.error("The merger requires two sequence files (use both -f1 and -f2 option)")
        if args.merger is None and args.f2 is not None:
            args.merger = DEFAULT_MERGER

        # automatically infer sample name from F1
        if args.name is None:
            args.name = inferSampleName(args.f1, args.merger, args.task.lower() == 'fastqc')

    # --------------------------------------------------------------------------------------------------------
    #                                    Parse clone limit option
    # --------------------------------------------------------------------------------------------------------
    if args.clonelimit is None:
        args.clonelimit = DEFAULT_TOP_CLONE_VALUE
    elif args.clonelimit.lower() == 'inf':
        args.clonelimit = float('inf')
    else:
        args.clonelimit = int(args.clonelimit)

    # MISC
    # setting default values for upstream
    if args.task in ['secretion', '5utr']:
        args.upstream = [1, Inf] if args.upstream is None else extractRanges(args.upstream, 1)[0]

    # confirm that file to sites is provided
    if args.task in ['rsa', 'rsasimple']:
        if args.sites is None:
            parser.error("Restriction sites should be provided if --task rsa or --task rsasimple was specified")
        args.sites = abspath(args.sites)

    if args.actualqstart is not None:
        if args.actualqstart >= 1:
            args.actualqstart = args.actualqstart - 1
        else:
            parser.error("ActualQStart parameter expects 1-based index."
                         " The provided index has an unexpected value of {}.".format(args.actualqstart))
    else:
        args.actualqstart = -1

    # --------------------------------------------------------------------------------------------------------
    #                                noFR4Cut, Trim5 and Trim3 logic check
    # --------------------------------------------------------------------------------------------------------

    if args.trim5 < 0:
        parser.error("--trim5 cannot be a negative value")

    # args.trim3 is a little more complicated
    if args.trim3 is None:
        # default, don't cut anything
        args.trim3 = 0
    else:
        if type(args.trim3) == str:
            args.fr4cut = False
            try:
                # user provided int
                args.trim3 = int(args.trim3)
                if args.trim3 < 0:
                    parser.error('--trim3 cannot be a negative value')
            except ValueError:
                # user provided sequence file
                if not os.path.exists(args.trim3):
                    parser.error("Can't find file {} for --trim3 argument".format(args.trim3))
                else:
                    trim3file = os.path.abspath(args.trim3)
                    with safeOpen(trim3file) as fp:
                        args.trim3 = [str(seq.seq) for seq in SeqIO.parse(fp, 'fasta')]

        else:
            parser.error("Unrecognized option for --trim3 {}".format(args.trim3))

    # --------------------------------------------------------------------------------------------------------
    #                                   Primer task check
    # --------------------------------------------------------------------------------------------------------

    # retrieve filenames for primer analysis on 5' and 3' end
    if args.task == 'primer':
        if args.primer3end is None and args.primer5end is None:
            parser.error("At least ond primer file (-p5 or -p3) must be specified for -t primer")
    args.primer5end = abspath(args.primer5end) if args.primer5end is not None else None
    args.primer3end = abspath(args.primer3end) if args.primer3end is not None else None
    if args.primer5end and not os.path.exists(args.primer5end):
        parser.error("{} file not found!".format(args.primer5end))
    if args.primer3end and not os.path.exists(args.primer3end):
        parser.error("{} file not found!".format(args.primer3end))

    # --------------------------------------------------------------------------------------------------------
    #                      Ranges for query, subject start / bitscore / align len filters
    # --------------------------------------------------------------------------------------------------------
    # setting default value of ranges if not provided, else extract the string ranges provided
    args.sstart = [1, Inf] if args.sstart is None else extractRanges(args.sstart)[0]
    args.qstart = [1, Inf] if args.qstart is None else extractRanges(args.qstart)[0]
    args.alignlen = [0, Inf] if args.alignlen is None else extractRanges(args.alignlen)[0]
    args.bitscore = [0, Inf] if args.bitscore is None else extractRanges(args.bitscore)[0]

    args.database = abspath(args.database) if args.database is not None else "$IGBLASTDB"

    # done
    return args


def parseCommandLineArguments(arguments=None):
    """
    parses commandline arguments for AbSeq
    :param arguments: sys.argv by default. Pass a list of strings otherwise
    :return: parser object, can be indexed for flag values
    """
    parser = argparse.ArgumentParser(description='AbSeq - antibody library quality control pipeline',
                                     prog="AbSeq", add_help=False)
    # required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('-f1', '--file1', dest="f1", help="path to sequence file 1. "
                                                            "Can only be omitted if -y/--yaml is specified",
                          default=None)
    optional.add_argument('-f2', '--file2', dest="f2", help="path to sequence file 2,"
                                                            " omit this option if sequences are not paired end or if"
                                                            " -f1 is a path to directory of samples",
                          default=None)
    optional.add_argument('-c', '--chain', default="hv", help="chain type [default=hv]",
                          choices=['hv', 'lv', 'kv'])
    optional.add_argument('-t', '--task', default=DEFAULT_TASK, help="analysis task, supported tasks: \
                                                    all, annotate, abundance, \
                                                    diversity, fastqc, productivity, primer, 5utr, rsasimple, rsa, \
                                                    seqlen, secretion, seqlenclass [default={}]".format(DEFAULT_TASK),
                          choices=["all", "annotate", "abundance", "diversity",
                                   "fastqc", "productivity", "primer", "5utr", "rsasimple",
                                   "rsa", "seqlen", "secretion", "seqlenclass"])
    optional.add_argument('-s', '--seqtype', default='dna', help="sequence type, supported seq type: dna or protein \
                                                                    [default=dna]",
                          choices=["dna", "protein"])
    optional.add_argument('-ds', '--domain_system', dest='domainSystem', default='imgt',
                          help="domain system to use. Either one of Kabat or IMGT numbering [default=imgt]",
                          choices=['imgt', 'kabat'])
    optional.add_argument('-m', '--merger', help="choice between different mergers. Omit this if no -f2 option"
                                                 " is specified [default={}]".format(DEFAULT_MERGER),
                          default=None,
                          choices=['leehom', 'flash', 'pear'])
    optional.add_argument('-o', '--outdir', help="output directory [default = current working directory]", default="./")
    optional.add_argument('-n', '--name', help="name of analysis [default = name of -f1]. This option"
                                               " is ignored when -f1 is a directory", default=None)
    optional.add_argument('-cl', '--clonelimit', help="outputs an intermediate file (top N overly expressed clones, "
                                                      "top N under expressed clones) in "
                                                      "./<OUTDIR>/<NAME>/diversity/clonotypes/; Specify"
                                                      " a number or inf to retain all clones [default=100]",
                          default=None)
    # line 173 in IgRepertoire.py, all ranges are inclusive when filtering rows from pandas's df
    optional.add_argument('-b', '--bitscore', help="filtering criterion (V gene bitscore):"
                                                   " Bitscore range (inclusive) to apply on V gene."
                                                   " V genes with bitscores that do not fall within this range"
                                                   " will be filtered out."
                                                   " Accepted format: num1-num2 [default=[0, inf)]", default=None)
    optional.add_argument('-ss', '--sstart', help="filtering criterion (Subject V gene start index):"
                                                  " Filters out sequences with subject start index (of the V gene)"
                                                  " that do not fall within this start range (inclusive)."
                                                  " Accepted format: num1-num2 [default=[1, inf)]",
                          default=None)
    optional.add_argument('-qs', '--qstart', help="filtering criterion (Query V gene start index):"
                                                  " Filters out sequences with query start index (of the V gene)"
                                                  " that do not fall within this start range (inclusive)."
                                                  " Accepted format: num1-num2 [default=[1, inf)]",
                          default=None)
    optional.add_argument('-al', '--alignlen', help="filtering criterion (Sequence alignment length):"
                                                    " Sequences that do not fall within this alignment length range"
                                                    " (inclusive) are filtered."
                                                    " Accepted format: num1-num2 [default=[0, inf)]", default=None)
    optional.add_argument('-qo', '--qoffset', dest="actualqstart",
                          help="query sequence's starting index (1-based indexing). Subsequence before specified "
                               "index is ignored during analysis. By default, each individual sequence's "
                               "offset is inferred automatically. This argument has no effect when aligning"
                               " 5' primer during primer specificity analysis.", default=None, type=int)
    optional.add_argument('-u', '--upstream', help="range of upstream sequences, secretion signal analysis and 5UTR"
                                                   " analysis. Index starts from 1 [default=[1, inf)]", default=None)
    optional.add_argument('-t5', '--trim5', help="number of nucleotides to trim on the 5'end of V domain."
                                                 " This argument has no effect when aligning 5' primer during"
                                                 " primer specificity analysis. [default=0]",
                          default=0, type=int)
    optional.add_argument('-t3', '--trim3', help="number of nucleotides to trim on the 3'end of V domain. "
                                                 " If a (fasta) file was provided instead, AbSeq will use"
                                                 " sequence(s) in the file to determine where to start trimming." 
                                                 " That is, the sequences will be trimmed at the 3' end based"
                                                 " on sequence(s) provided in the file. This argument has no effect "
                                                 " when aligning 3' primer during primer specificity analysis."
                                                 " [default=0]", default=None)
    optional.add_argument('-p5off', '--primer5endoffset', help="number of nucleotides for 5' end offset before aligning"
                                                               " primer sequences. [default=0]",
                          default=0, type=int)
    optional.add_argument('-p', '--primer', help="not implemented yet [default=-1]", default=-1, type=int)
    optional.add_argument('-d', '--database', help="specify fully qualified path to germline database "
                                                   "[default=$IGBLASTDB], type echo $IGBLASTDB in command line"
                                                   " to see your default database used by AbSeq",
                          default=None)
    optional.add_argument('-q', '--threads', help="number of threads to use (spawns separate processes) [default=1]",
                          type=int, default=1)
    optional.add_argument('-y', '--yaml', help="path to yaml file.", required=False, default=None)
    optional.add_argument('-r', '--report-interim', help="specify this flag to generate report."
                                                         " Not implemented yet [default= no report]",
                          dest="report_interim", action='store_true')
    optional.add_argument('-nf4c', '--nofr4cut', help="when specified, the end of sequence (FR4 end) is either "
                                                      "the end of the read if no --trim3 is provided or"
                                                      " trimmed to --trim3 argument if provided. "
                                                      " [default = sequence (FR4 end) ends where J germline ends]",
                          dest='fr4cut', action='store_false')
    optional.add_argument('-st', '--sites', help="path to restriction sites text file, required if"
                                                 " --task rsa or --task rsasimple is specified."
                                                 " The expected table format is: Enzyme <white space> Recognition"
                                                 "Sequence ", default=None)
    optional.add_argument('-p3', '--primer3end', help="path to primer 3' end fasta file.", default=None)
    optional.add_argument('-p5', '--primer5end', help="path to primer 5' end fasta file.", default=None)
    optional.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION)
    optional.add_argument('-h', '--help', action='help', help="show this help message and exit")
    return parser, parser.parse_args() if arguments is None else parser.parse_args(arguments)


def extractRanges(strRanges, expNoRanges=2):
    """
    Returns the range given an input

    :param strRanges:
                string range, allowed format: 0-10,23-25 or 0-10 or 0

    :param expNoRanges:
                expected maximum number of allowed ranges, eg: expNoRange=1 implies only 1 range, expNoRange=2
                implies 0-10,20-25 is allowed, and so on. If provided strRanges has lesser number of ranges than
                this argument, it will extend the list. I.e. strRanges="0-9", expNoRanges=2 will return [[0,9],[0,9]]

    :return:
                a nested list of ranges
    """
    numRanges = []
    ranges = strRanges.split(',')
    if len(ranges) > expNoRanges:
        raise Exception("Number of bitScore, alignLen, sstart, and qstart ranges should match the number of files")

    for i in range(len(ranges)):
        scores = ranges[i].split('-')
        if len(scores) == 2:
            numRanges.append([float(scores[0]), float(scores[1])])
            if numRanges[-1][0] >= numRanges[-1][1]:
                raise Exception("Invalid ranges " + strRanges)

        else:
            numRanges.append([float(scores[0]), Inf])

    if len(numRanges) < expNoRanges:
        numRanges = numRanges * expNoRanges

    return numRanges


def printUsage(parser, additional_msg=None):
    parser.print_help()
    if additional_msg is not None:
        print(additional_msg, file=sys.stderr)
    sys.exit(0)


def parseYAML(yamlFile, check=True):
    """
    parses each document within the yaml file and returns either a converted list of list of strings (in tokens) or
    an iterable of yaml dictionary
    :param yamlFile: string. Path to YAML
    :param check: bool. Check for funky arguments (check for recursive yaml key:value)
    :return: list of list of tokens / iterable of dictionaries and a bool indicating if there's a comparison key value
    """
    with open(yamlFile) as fp:
        contents = fp.read()
    output = []
    compare = False
    for doc in yaml.load_all(contents):
        docList = []
        for key, value in doc.items():
            if str(key) == 'yaml' and check:
                raise ValueError("yaml keyword (with value {}) detected in YAML file, not allowed.".format(value))
            docList.append("--" + str(key))
            docList.append(str(value))
            if str(key) == 'compare':
                compare = True
        output.append(docList)
    return output, compare
