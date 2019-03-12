#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import sys
import json
import msgpack

from pathlib import Path

import spacy
from spacy import displacy

import en_core_web_lg
import en_vectors_web_lg
import en_coref_lg

from .documents import fromFile as DocumentFromFile
from .documents import fromExtension as DocumentParserFromExtension
from .string_enumerator import StringListEnumerator
from .corpora import Corpus


def wrap_token(token, enums, vecDoc):
    wrapped = {
        'text': enums['words'][str(token.text)],
        'index': token.i,
        'parent': token.head.i,
        'is_root': token.i == token.head.i,
        'ent_type': enums['enttype'][token.ent_type_],
        'ent_iob': enums['entiob'][token.ent_iob_],
        'lemma': enums['lemma'][token.lemma_],
        'norm': enums['norm'][token.norm_],
        'pos': enums['posgen'][token.pos_],
        'tag': enums['posspc'][token.tag_],
        'is_oov': token.is_oov,
        'prob': token.prob,
        'sentiment': token.sentiment,
        'vector': None if not vecDoc[token.i].has_vector else vecDoc[token.i].vector.tolist(),
    }
    return wrapped


def wrap_noun_chunk(noun_chunk, vecDoc):
    vi = vecDoc[noun_chunk[0].i: noun_chunk[-1].i+1]
    nc = {
        'token_range': list(range(noun_chunk[0].i, noun_chunk[-1].i+1)),
        'vector': None if not vi.has_vector else vi.vector.tolist(),
        'sentiment': vi.sentiment,
    }
    return nc


def create_enums():
    return {
        'words': StringListEnumerator(),
        'lemma': StringListEnumerator(),
        'norm': StringListEnumerator(),
        'enttype': StringListEnumerator(),
        'entiob': StringListEnumerator(),
        'posgen': StringListEnumerator(),
        'posspc': StringListEnumerator(),
        'correfcluster': StringListEnumerator(),
    }


def process_files(files=list()):
    if len(files) <= 0:
        return
    else:
        print('There are %d files to process.' % (len(files),), file=sys.stderr)
    print('Loading libraries...', file=sys.stderr)
    nlp = en_core_web_lg.load()
    vec = en_vectors_web_lg.load()
    crf = en_coref_lg.load()
    for seq, file in enumerate(files):
        print("[%02d of %02d] %s" % (seq+1, len(files), str(file)), file=sys.stderr)
        print('Loading the document...', file=sys.stderr)
        pdfDocument = DocumentFromFile(str(file)).parse(' ')
        print('Processing document...', file=sys.stderr)
        nlpDoc = nlp(pdfDocument)
        vecDoc = vec(pdfDocument)
        crfDoc = crf(pdfDocument)
        print('Converting results...', file=sys.stderr)
        enums = create_enums()
        text = {
            'source': str(file),
            'tokens': list(),
            'vector': None,
            'sentiment': 0.0,
            'sentences': list(),
            'noun_chunks': list(),
            'coref_cluster': list(),
        }
        for token in nlpDoc:
            text['tokens'].append(wrap_token(token, enums, vecDoc))
        text['vector'] = None if not vecDoc.has_vector else vecDoc.vector.tolist(),
        text['sentiment'] = nlpDoc.sentiment
        for noun_chunk in nlpDoc.noun_chunks:
            text['noun_chunks'].append(wrap_noun_chunk(noun_chunk, vecDoc))
        for coref_cluster in crfDoc._.coref_clusters:
            text['coref_cluster'].append({
                'main': list(range(coref_cluster.main[0].i, coref_cluster.main[-1].i+1)),
                'mentions': [list(range(mention[0].i, mention[-1].i+1)) for mention in coref_cluster.mentions],
            })
        for sentence in nlpDoc.sents:
            nlpSentTokens = list(sentence)
            vecSentTokens = vecDoc[nlpSentTokens[0].i:nlpSentTokens[-1].i+1]
            wrapped = {
                'tokens': [token.i for token in sentence],
                'vector': None if not vecSentTokens.has_vector else vecSentTokens.vector.tolist(),
                'sentiment': sentence.sentiment,
                'noun_chunks': list(),
                'coref_cluster': list()
            }
            for noun_chunk in sentence.noun_chunks:
                wnc = wrap_noun_chunk(noun_chunk, vecDoc)
                for ndx, known in enumerate(text['noun_chunks']):
                    if wnc == known:
                        wrapped['noun_chunks'].append(ndx)
            sentRange = set(range(nlpSentTokens[0].i, nlpSentTokens[-1].i+1))
            for ndx, coref_cluster in enumerate(text['coref_cluster']):
                for mention in coref_cluster['mentions']:
                    if len(sentRange.intersection(mention)) > 0:
                        wrapped['coref_cluster'].append(ndx)
            text['sentences'].append(wrapped)
        print('Outputting results...', file=sys.stderr)
        Path(str(file)+'.nlp').write_text(json.dumps({
            'enums': dict([(k, v.as_tuple) for k, v in enums.items()]),
            'compressed': text,
        }))
    del nlp
    del vec
    del crf


def get_pending_files(directory='corpus'):
    pending_files = list()
    parseable_files = list()
    for document in Path(directory).rglob('*'):
        if document.is_file():
            if DocumentParserFromExtension(document.suffix.lstrip('.')) is not None:
                parseable_files.append(document)
    for parseable in parseable_files:
        nlp = Path(str(parseable)+'.nlp')
        if not nlp.exists() or not nlp.is_file() or nlp.stat().st_mtime <= parseable.stat().st_mtime:
            pending_files.append(parseable)
    return pending_files


def get_corpus_cached(directory='corpus'):
    files = sorted(list(filter(lambda a: a.is_file(), Path(directory).rglob('*.nlp'))))
    time_stamps = dict(map(lambda a: (str(a), round(a.stat().st_mtime)), files))
    nlpinfo = Path(directory+'.nlpinfo')
    nlpcache = Path(directory+'.nlpcache')
    if not nlpinfo.exists() or time_stamps != json.loads(nlpinfo.read_text()) or not nlpcache.exists():
        aggregated = aggregate_nlp_caches(list(map(lambda a: json.loads(a.read_text()), files)))
        nlpcache.write_text(json.dumps(aggregated))
        nlpinfo.write_text(json.dumps(time_stamps))
        del aggregated
    return json.loads(nlpcache.read_text())


def aggregate_nlp_caches(individual_caches):
    corpus = {
        'documents': list(),
        'enums': create_enums(),
    }
    token_reenum_pairs = (
        ('text', 'words'),
        ('ent_type', 'enttype'),
        ('ent_iob', 'entiob'),
        ('lemma', 'lemma'),
        ('norm', 'norm'),
        ('pos', 'posgen'),
        ('tag', 'posspc'),
    )
    for cache in individual_caches:
        cached_enums = dict(map(lambda a: (a[0], StringListEnumerator(a[1])), cache['enums'].items()))
        reenumerators = dict()
        for k, v in corpus['enums'].items():
            reenumerators[k] = v.merge(cached_enums[k])
        cacheddata = cache['compressed']
        for token in cacheddata['tokens']:
            for tk, rn in token_reenum_pairs:
                token[tk] = reenumerators[rn][token[tk]]
        corpus['documents'].append(cacheddata)
    corpus['enums'] = dict(map(lambda a: (a[0], a[1].as_list), corpus['enums'].items()))
    return corpus


def main():
    print('Knowledge Base Creator v0.1', file=sys.stderr)
    process_files(get_pending_files())
    print('Reading cached corpus...', file=sys.stderr)
    corpus = get_corpus_cached()
    print('Deserializing corpus...', file=sys.stderr)
    corpus = Corpus(corpus)
    print('Corpus is ready.', file=sys.stderr)
    if len(sys.argv) > 2:
        print('Preparing search...', file=sys.stderr)
        _, left_op, right_op, *_ = sys.argv
        paths = corpus.find_knowledge_source(left_op, right_op)
        print('Printing matches between %r and %r...' % (left_op, right_op), file=sys.stderr)
        for match in paths:
            print(match)
