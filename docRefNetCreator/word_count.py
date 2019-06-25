#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


ignoreList = [
    *',.;/\\|?:~^`´[{(<>)}]=+-_&¨¬%$#@!"\'\r\n\b',
]


def list_cos_sim(a, b):
    return cosine_similarity(np.array([a]), np.array([b]))


class WordCounter:
    def __init__(self, text, ignore=ignoreList):
        wf = dict()
        self._wordFreq = wf
        for exp in ignoreList:
            text = text.replace(exp, ' ')
        for word in text.split(' '):
            if len(word) <= 0:
                continue
            lc = word.lower()
            if lc not in wf:
                wf[lc] = 0
            wf[lc] += 1

    def unionKeySets(self, other):
        return sorted(list(set(list(self._wordFreq.keys())+list(other._wordFreq.keys()))))

    def populateFrequency(self, word_vector):
        return [self._wordFreq.get(word, 0) for word in word_vector]

    def vectorSimilarity(self, other, function=list_cos_sim):
        resultingVectorKeys = self.unionKeySets(other)
        thisVector = self.populateFrequency(resultingVectorKeys)
        thatVector = other.populateFrequency(resultingVectorKeys)
        return function(thisVector, thatVector)
