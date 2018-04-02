'''
    Short description: Quality Control Analysis of Immunoglobulin Repertoire NGS (Paired-End MiSeq)    
    Author: Monther Alhamdoosh    
    Python Version: 2.7
    Changes log: check git commits. 
'''
from __future__ import division
import os
import sys
import gc

from multiprocessing import Queue
from collections import Counter
from Bio import SeqIO
from pandas.core.frame import DataFrame
from math import ceil

from abseq.IgRepAuxiliary.IgBlastWorker import analyzeSmallFile, IgBlastWorker
from abseq.IgRepertoire.igRepUtils import splitFastaFile, safeOpen
from abseq.logger import printto, LEVEL


def annotateIGSeqRead(igRep, fastaFile, seqType='dna', outdir="", domainClassification='imgt', stream=None):
        noWorkers = igRep.threads
        seqsPerFile = igRep.seqsPerFile

        if fastaFile is None:
            return Counter()

        # Estimate the IGV diversity in a library from igblast output 
        printto(stream, 'The IGV clones of ' + os.path.basename(fastaFile) + ' are being annotated ...')
        with open(fastaFile) as f:
            noSeqs = sum(1 for line in f if line.startswith(">"))
        totalFiles = int(ceil(noSeqs / seqsPerFile))
        if totalFiles < noWorkers:
            seqsPerFile = int(noSeqs / noWorkers)
            totalFiles = int(ceil(noSeqs / seqsPerFile))
        noSplit = noSeqs <= igRep.seqsPerFile
        printto(stream, "\t{0:,} sequences were found to be distributed into {1:,} file(s)"
                .format(noSeqs, (totalFiles if not noSplit else 1)))
        if igRep.primer > 0:
            with safeOpen(fastaFile) as fp:
                recordsAll = SeqIO.to_dict(SeqIO.parse(fp, 'fasta'))
            records = []
            for id_ in recordsAll:
                rec = recordsAll[id_]
                rec.description = ''
                rec.seq = rec.seq[:igRep.primer]
                records.append(rec)
            filesDir = os.path.join(outdir, "tmp")
            SeqIO.write(records, os.path.join(filesDir, "seqs.fasta"), 'fasta')
            newFastFile = os.path.join(filesDir, "seqs.fasta")
        else:
            newFastFile = fastaFile
        # if we only asked for one worker or if the sequences within the fasta file is smaller than the threshold in
        # in igRep.seqsPerFile, we can just analyze the file without splitting it
        if noWorkers == 1 or noSplit:
            cloneAnnot, filteredIDs = analyzeSmallFile(newFastFile, igRep.chain, igRep.db,
                                                       seqType, noWorkers, outdir,
                                                       domainClassification=domainClassification, stream=stream)
            sys.stdout.flush()
        else:
            # split FASTA file into smaller files
            prefix, ext = os.path.splitext(os.path.basename(fastaFile))
            filesDir = os.path.join(outdir,  "tmp")
            prefix = prefix[prefix.find("_R")+1:prefix.find("_R")+3] + "_" if (prefix.find("_R") != -1) else ""
            splitFastaFile(fastaFile, totalFiles, seqsPerFile, filesDir, prefix, ext, stream=stream)

            # Prepare the multiprocessing queues
            tasks = Queue()    
            outcomes = Queue()   
            exitQueue = Queue()              
            cloneAnnot = DataFrame()
            filteredIDs = []
            workers = []
            try:
                # Initialize workers
                for i in range(noWorkers):
                    w = IgBlastWorker(igRep.chain, igRep.db,
                                      seqType, int(ceil(noWorkers / totalFiles)),
                                      domainClassification=domainClassification, stream=stream)
                    w.tasksQueue = tasks
                    w.resultsQueue = outcomes
                    w.exitQueue = exitQueue      
                    workers.append(w)
                    w.start()       
                    sys.stdout.flush()

                # initialize tasks queue with file names     
                for i in range(totalFiles):
                    tasks.put(os.path.join(filesDir, prefix + "part" + str(i + 1) + ext))

                # Add a poison pill for each worker
                for i in range(noWorkers + 10):
                    tasks.put(None)                  
               
                # Wait all process workers to terminate    
                i = 0 
                while i < noWorkers:    
                    m = exitQueue.get()
                    if m == "exit":
                        i += 1
                
                # Collect results
                printto(stream, "Results are being collated from all workers ...")
                sys.stdout.flush()
                while totalFiles:
                    outcome = outcomes.get()
                    totalFiles -= 1                    
                    if outcome is None:
                        continue                    
                    (cloneAnnoti, fileteredIDsi) = outcome
                    cloneAnnot = cloneAnnot.append(cloneAnnoti)
                    filteredIDs += fileteredIDsi
                    sys.stdout.flush()
                    gc.collect()
                printto(stream, "\tResults were collated successfully.")
                    
            except Exception:
                printto(stream, "Something went wrong during the annotation process!", LEVEL.EXCEPT)
                raise
            finally:
                for w in workers:
                    w.terminate()

            # Clean folders to save space
            # TODO: remove .fasta and .out files
            if (noSeqs > igRep.seqsPerFile and 
                os.path.exists(filesDir + "/" + prefix + "part1" + ext)):
                os.system("rm " + filesDir + "/*" + ext)

        return cloneAnnot, filteredIDs
