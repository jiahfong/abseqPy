'''
    Short description: Quality Control Analysis of Immunoglobulin Repertoire NGS (Paired-End MiSeq)    
    Author: Monther Alhamdoosh    
    Python Version: 2.7
    Changes log: check git commits. 
'''

import sys
import os
import gzip

from collections import Counter

from abseq.IgRepAuxiliary.SeqUtils import createAlphabet, generateMotif
from abseq.IgRepertoire.igRepUtils import writeClonoTypesToFile
from abseq.IgRepReporting.igRepPlots import plotSeqLenDist, \
    generateCumulativeLogo, plotSeqDuplication, plotSeqRarefaction, \
    plotSeqRecapture, plotSeqRecaptureNew
from abseq.logger import LEVEL, printto


def generateDiversityReport(spectraTypes, clonoTypes, name, outDir, topClonotypes, stream=None):
    generateSpectraTypePlots(spectraTypes,  name, outDir, stream=stream)

    writeClonoTypesToFiles(clonoTypes, name, outDir, topClonotypes, stream=stream)

    estimateDiversity(clonoTypes, name, outDir, stream=stream)
#     generateCDRandFRLogos()


def writeClonoTypesToFiles(clonoTypes, name, outDir, topClonotypes=100, stream=None):
    printto(stream, "Clonotype files are being written out ... ")
    cloneFolder = os.path.join(outDir, "clonotypes")

    if not os.path.exists(cloneFolder):
        os.makedirs(cloneFolder)

    for k in clonoTypes.keys():
        # check if the required topClonotypes went overboard, if so, cap to the max length
        if topClonotypes != float('inf') and len(clonoTypes[k]) < topClonotypes:
            stringTopClonotypes = str(len(clonoTypes[k]))
        else:
            stringTopClonotypes = 'all' if topClonotypes == float('inf') else str(topClonotypes)

        # descending order
        filename = os.path.join(cloneFolder, name + ("_{}_clonotypes_{}_over.csv".format(k, stringTopClonotypes)))
        writeClonoTypesToFile(clonoTypes[k], filename, topClonotypes, overRepresented=True)

        # ascending order
        filename = os.path.join(cloneFolder, name + ("_{}_clonotypes_{}_under.csv".format(k, stringTopClonotypes)))
        writeClonoTypesToFile(clonoTypes[k], filename, topClonotypes, overRepresented=False)


def generateSpectraTypePlots(spectraTypes, name, outDir, stream=None):
    specFolder = os.path.join(outDir, "spectratypes")

    if not os.path.exists(specFolder):
        os.makedirs(specFolder)

    for k in spectraTypes.keys():
        filename = os.path.join(specFolder, name + ('_{}_spectratype.png'.format(k)))
        plotSeqLenDist(spectraTypes[k], name, filename, dna=False,
                       seqName=k.upper(), normed=True, maxbins=40, stream=stream)
        if k == 'cdr3':
            filename = os.path.join(specFolder, name + ('_{}_spectratype_no_outliers.png'.format(k)))
            plotSeqLenDist(spectraTypes[k], name, filename, dna=False,
                           seqName=k.upper(), normed=True, maxbins=40,
                           removeOutliers=True, stream=stream)


def estimateDiversity(clonoTypes, name, outDir, stream=None):
    generateSeqLogosMotifs(clonoTypes, name, outDir, "protein", stream=stream)
    generateRarefactionPlots(clonoTypes, name, outDir, stream=stream)
    printto(stream, "The diversity of the library is being estimated ... ")
    calcDiversity(clonoTypes, name, outDir)


# todo: diversity indices
def calcDiversity(clonoTypes, name, outDir):
    regions = clonoTypes.keys()
    regions.sort()
    rarenessCounts = {}
    for region in regions:
        rarenessCounts[region] = Counter(clonoTypes[region].values())


def generateRarefactionPlots(clonoTypes, name, outDir, stream=None):
    regions = clonoTypes.keys()
    regions.sort()
    printto(stream, "Rarefaction plots are being generated .... ")
    # select CDR regions only  
    cdrWeights = []
    cdrSeqs = []
    cdrRegions = []
    for region in regions:
        if not region.startswith("cdr"):
            continue
        cdrRegions.append(region.upper())
        cdrSeqs.append(clonoTypes[region].keys())
        cdrWeights.append(map(lambda x: clonoTypes[region][x], cdrSeqs[-1]))
    filename = os.path.join(outDir, name + "_cdr_duplication.png")
    printto(stream, "\tThe duplication levels plot is being generated for CDRs .... ")
    plotSeqDuplication(cdrWeights,
                       cdrRegions,
                       filename,
                       'Duplication of CDR Sequences', stream=stream)
    printto(stream, "\tThe rarefaction plot is being generated for CDRs .... ")
    filename = os.path.join(outDir, name + "_cdr_rarefaction.png")
    plotSeqRarefaction(cdrSeqs,
                       cdrRegions,
                       filename,
                       cdrWeights,
                       'Rarefaction of CDR Sequences', stream=stream)
    printto(stream, " \tThe percent recapture plot is being generated for CDRs .... ")
    filename = os.path.join(outDir, name + "_cdr_recapture.png")
    plotSeqRecaptureNew(cdrSeqs,
                        cdrRegions,
                        filename,
                        'Percent Recapture of CDR Sequences', stream=stream)
    # select FR regions only
    frWeights = []
    frSeqs = []
    frRegions = []
    for region in regions:
        if not region.startswith("fr"):
            continue
        frRegions.append(region.upper())
        frSeqs.append(clonoTypes[region].keys())
        frWeights.append(map(lambda x: clonoTypes[region][x], frSeqs[-1]))
    filename = os.path.join(outDir, name + "_fr_duplication.png")
    printto(stream, "\tThe duplication levels plot is being generated for FRs .... ")
    plotSeqDuplication(frWeights,
                       frRegions,
                       filename,
                       'Duplication of FR Sequences', stream=stream)
    printto(stream, "\tThe rarefaction plot is being generated for FRs .... ")
    filename = os.path.join(outDir,  name + "_fr_rarefaction.png")
    plotSeqRarefaction(frSeqs,
                       frRegions,
                       filename,
                       frWeights,
                       'Rarefaction of FR Sequences', stream=stream)
    printto(stream, "\tThe percent recapture plot is being generated for FRs .... ")
    filename = os.path.join(outDir, name + "_fr_recapture.png")
    plotSeqRecaptureNew(frSeqs,
                        frRegions,
                        filename,
                        'Percent Recapture of FR Sequences', stream=stream)
    # select CDR and V domain 
    cdrWeights = []
    cdrSeqs = []
    cdrRegions = []
    for region in regions:
        if region.startswith("fr"):
            continue
        cdrRegions.append(region.upper())
        cdrSeqs.append(clonoTypes[region].keys())
        cdrWeights.append(map(lambda x: clonoTypes[region][x], cdrSeqs[-1]))
    filename = os.path.join(outDir, name + "_cdr_v_duplication.png")
    printto(stream, "\tThe duplication levels plot is being generated for CDRs and V domains .... ")
    plotSeqDuplication(cdrWeights,
                       cdrRegions,
                       filename,
                       'Duplication of CDRs and V Domains', stream=stream)
    printto(stream, "\tThe rarefaction plot is being generated for CDRs and V domains .... ")
    filename = os.path.join(outDir, name + "_cdr_v_rarefaction.png")
    plotSeqRarefaction(cdrSeqs,
                       cdrRegions,
                       filename,
                       cdrWeights,
                       'Rarefaction of CDRs and V Domains', stream=stream)
    printto(stream, "\tThe percent recapture plot is being generated for CDRs and V domains .... ")
    filename = os.path.join(outDir, name + "_cdr_v_recapture.png")
    plotSeqRecaptureNew(cdrSeqs,
                        cdrRegions,
                        filename,
                        'Percent Recapture of CDRs and V Domains', stream=stream)


def generateSeqLogosMotifs(clonoTypes, name, outDir, seqType="protein", stream=None):

    logosFolder = os.path.join(outDir, 'composition_logos')
    if not os.path.isdir(logosFolder):
        os.makedirs(logosFolder)

    motifsFolder = os.path.join(outDir, 'motifs')

    if not os.path.isdir(motifsFolder):
        os.makedirs(motifsFolder)

    regions = clonoTypes.keys()
    regions.sort()

    printto(stream, seqType + " sequence logos are being generated .... ")

    for region in regions:
        if region == 'v':
            continue
        printto(stream, "\t" + region.upper())

        clonoType = clonoTypes[region]
        seqs = filter(lambda x: x != "None", clonoType.keys())
        weights = map(lambda x: clonoType[x], seqs)

        # Generate cumulative sequence logos using Toby's approach
        # TODO: generate composition logos by IGV family
        filename = os.path.join(logosFolder, name + ("_{}_cumulative_logo.png".format(region)))
        generateCumulativeLogo(seqs, weights, region, filename, stream=stream)

        # Generate sequence motif logos using weblogo

        # generate logos without alignment
        filename = os.path.join(motifsFolder, name + ("_{}_motif_logo.png".format(region)))
        alphabet = createAlphabet(align=False, protein=True, extendAlphabet = True)
        m = generateMotif(seqs, region, alphabet, filename,  align=False,
                          protein=True, weights=weights, outDir=outDir, stream=stream)

        # generate  logos after alignment
        filename = os.path.join(motifsFolder, name + ("_{}_motif_aligned_logo.png".format(region)))
        alphabet = createAlphabet(align=True, protein=True, extendAlphabet=True)
        m = generateMotif(seqs, region, alphabet, filename,  align=True,
                          protein=True, weights=weights, outDir=outDir, stream=stream)


def writeClonotypeDiversityRegionAnalysis(clonoTypes, sampleName, outDir, stream=None):
    """
    For a given set of similar CDR3 clonotypes, it may be classified as a different clonotype if the entire V region
    is considered. This writes the unique counts of other region aside form CDR3s to see if the clonotype will differ
    if the entire V region is considered. Consequently, it's possible to learn which region is (mostly)
    the one responsible of changing the clonotype if it was included.
    :param clonoTypes: DataFrame of clonotypes per read. Requires the CDRs and FRs columns
    :param sampleName: Sample name for output file
    :param outDir: Out directory for output file
    :param stream: debug stream
    :return: None. Produces an output gzipped csv file
    """
    fname = os.path.join(outDir, sampleName + "_clonotype_diversity_region_analysis.csv.gz")
    if os.path.exists(fname):
        printto(stream, "\t File found {}".format(fname), LEVEL.WARN)
        return

    # regions of analysis
    cols = ["cdr1", "cdr2", "fr1", "fr2", "fr3", "fr4"]

    def regionCounts(selectedRows):
        """ returns a list of numbers that corresponds to the frequency of *UNIQUE* "CDR1", "CDR2", .. "FR4"
        (in the order of cols as defined above)
        :param selectedRows: this "DataFrame" of rows should have the same CDR3 region
        :return: a list of numbers, each representing the number of unique region in the order of
        COLS as defined above
        """
        return [str(len(set(selectedRows[region]))) for region in cols]

    # obtain all CDR3s
    cdr3s = set(clonoTypes['cdr3'])

    with gzip.open(fname, "wb") as fp:
        writeBuffer = ""
        # write csv header
        writeBuffer += "cdr3,count," + ','.join(cols) + "\n"
        # for each unique CDR3, find all rows(reads) that have the same CDR3
        for cdr3 in cdr3s:
            rows = clonoTypes[clonoTypes['cdr3'] == cdr3]
            writeBuffer += cdr3 + "," + str(len(rows)) + "," + ','.join(regionCounts(rows)) + '\n'
            if len(writeBuffer) > 4e9:
                fp.write(writeBuffer)
                writeBuffer = ""
        fp.write(writeBuffer)




# quantify CDR sequence diversity

#         if (not exists(self.outputDir + self.name +
#                  '_Vdomain_diversity.png')):
#     #         i = 0
#             VH = []
#             for (id, f1, c1, f2, c2, f3, c3, f4) in zip(self.cloneSeqs.index.tolist(),
#                                                         self.cloneSeqs['fr1'].tolist(),
#                                                           self.cloneSeqs['cdr1'].tolist(),
#                                                           self.cloneSeqs['fr2'].tolist(),
#                                                           self.cloneSeqs['cdr2'].tolist(),
#                                                           self.cloneSeqs['fr3'].tolist(),
#                                                           self.cloneSeqs['cdr3'].tolist(),
#                                                           self.cloneSeqs['fr4'].tolist()):
#                 try:
#                     VH += [''.join([f1, c1, f2, c2, f3, c3, f4])]
#                 except:
#                     if (f4 is None or isnan(f4)):  # or c3 is None or isnan(c3):
#                         VH += [''.join([f1, c1, f2, c2, f3, c3])]
#                     else:
#                         print(id, f1, c1, f2, c2, f3, c3, f4)
# #                 i += 1
# #         print(i)
# #         sys.exit()
#             plotSeqDuplication([self.cloneSeqs['cdr1'].tolist(),
#                               self.cloneSeqs['cdr2'].tolist(),
#                               self.cloneSeqs['cdr3'].tolist(),
#                               VH],
#                              self.outputDir + self.name +
#                      '_Vdomain__Vdomain_ication.png',
#                              ['CDR1', 'CDR2', 'CDR3', 'V Domain'],
#                              'Duplication of V Domain Sequences')
#             plotSeqRarefaction([self.cloneSeqs['cdr1'].tolist(),
#                           self.cloneSeqs['cdr2'].tolist(),
#                           self.cloneSeqs['cdr3'].tolist(),
#                           VH],
#                          self.outputDir + self.name +
#                  '_Vdomain_diversity.png',
#                          ['CDR1', 'CDR2', 'CDR3', 'V Domain'],
#                          'Diversity of V Domain Sequences')
#         gc.collect()
#
#         plotSeqDuplication([self.cloneSeqs['cdr1'].tolist(),
#                           self.cloneSeqs['cdr2'].tolist(),
#                           self.cloneSeqs['cdr3'].tolist()
#                           ],
#                          self.outputDir + self.name +
#                  '_cdr_duplication.png',
#                          ['CDR1', 'CDR2', 'CDR3'],
#                          'Duplication of CDR Sequences')
#
#         plotSeqRarefaction([self.cloneSeqs['cdr1'].tolist(),
#                           self.cloneSeqs['cdr2'].tolist(),
#                           self.cloneSeqs['cdr3'].tolist()
#                         ],
#                          self.outputDir + self.name +
#                  '_cdr_diversity.png',
#                          ['CDR1', 'CDR2', 'CDR3'],
#                          'Diversity of CDR Sequences')
#         gc.collect()


# Quantify FR sequence diversity
#         plotSeqDuplication([self.cloneSeqs['fr1'].tolist(),
#                           self.cloneSeqs['fr2'].tolist(),
#                           self.cloneSeqs['fr3'].tolist(),
#                           self.cloneSeqs['fr4'].tolist()],
#                          self.outputDir + self.name +
#                  '_fr_duplication.png',
#                          ['FR1', 'FR2', 'FR3', 'FR4'],
#                          'Duplication of FR Sequences')
#         gc.collect()
#         plotSeqRarefaction([self.cloneSeqs['fr1'].tolist(),
#                           self.cloneSeqs['fr2'].tolist(),
#                           self.cloneSeqs['fr3'].tolist(),
#                           self.cloneSeqs['fr4'].tolist()],
#                          self.outputDir + self.name +
#                  '_fr_diversity.png',
#                          ['FR1', 'FR2', 'FR3', 'FR4'],
#                          'Diversity of FR Sequences')


# quantify V domain sequence diversity
#         if (not exists(self.outputDir + self.name +
#                  '_Vdomain_duplication_family.png')):
#             print("Grouping V domain sequences per family ...")
#             VH = {}
#     #         i = 0
#             ighvs = map(lambda x : x.split('-')[0].split('/')[0], self.cloneSeqs['germline'].tolist())
#             for ighv in set(ighvs):
#                 VH[ighv] = []
#             for (ighv, f1, c1, f2, c2, f3, c3, f4) in zip(ighvs,
#                                                         self.cloneSeqs['fr1'].tolist(),
#                                                           self.cloneSeqs['cdr1'].tolist(),
#                                                           self.cloneSeqs['fr2'].tolist(),
#                                                           self.cloneSeqs['cdr2'].tolist(),
#                                                           self.cloneSeqs['fr3'].tolist(),
#                                                           self.cloneSeqs['cdr3'].tolist(),
#                                                           self.cloneSeqs['fr4'].tolist()):
#                 try:
#                     VH[ighv].append(''.join([f1, c1, f2, c2, f3, c3, f4]))
#                 except:
#                     if (f4 is None or isnan(f4)):  # or c3 is None or isnan(c3):
#                         VH += [''.join([f1, c1, f2, c2, f3, c3])]
#                     else:
#                         print(id, f1, c1, f2, c2, f3, c3, f4)
#             ighvs = VH.keys()
#             ighvs.sort()
#
#             plotSeqDuplication(map(lambda x:VH[x], ighvs),
#                              self.outputDir + self.name +
#                      '_Vdomain_duplication_family.png',
#                              ighvs,
#                              'Duplication of V Domain Sequences Per Family', True)
#             gc.collect()