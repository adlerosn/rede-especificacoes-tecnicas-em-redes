#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import sqlite3
import graphviz
from pathlib import Path

from .documents import fromFile as DocumentFromFile
from .document_finder import classes as docClasses
from .document_finder import find_references as referenceFinder


def generate_graph():
    rootsrc, rootname = Path("rootdoc.txt").read_text().splitlines()
    analyzedDocPaths = list()
    pendingDocCchMgr = [docClasses[rootsrc](rootname)]
    graph = dict()
    while len(pendingDocCchMgr) > 0:
        docCchMgr, *pendingDocCchMgr = pendingDocCchMgr
        docPath = docCchMgr.cached()
        currName = f"{docCchMgr.__class__.__name__}: {docCchMgr._identifier}"
        if docPath is not None:
            currName = str(docPath)[6:]
        if currName not in graph:
            graph[currName] = {
                'name': currName,
                'type': docCchMgr.__class__.__name__,
                'doc_id': docCchMgr._identifier,
                'monitored': False if docPath is None else docPath.exists(),
                'pub_date': docCchMgr.publication_date(docPath),
                'in_force': docCchMgr.is_in_force(docPath),
                'mention_freq': dict(),
            }
        if docPath in analyzedDocPaths:
            continue
        analyzedDocPaths.append(docPath)
        docFF = DocumentFromFile(str(docPath))
        print(f"Document @ {currName}")
        if docFF is None:
            continue
        doc = docFF.parse()
        newReferences = referenceFinder(doc, docCchMgr.context(docPath))
        for newReference in newReferences:
            newDocPath = newReference.cached()
            newName = f"{newReference.__class__.__name__}: {newReference._identifier}"
            if newDocPath is not None:
                newName = str(newDocPath)[6:]
            graph[currName]['mention_freq'][newName] = graph[currName]['mention_freq'].get(newName, 0) + 1
        pendingDocCchMgr = sorted(
            [*pendingDocCchMgr, *newReferences],
            key=lambda dcm: (not dcm.is_cached(), dcm.slowness(), dcm._identifier)
        )
    Path('graph.json').write_text(json.dumps(graph))


def main():
    if not Path('graph.json').exists():
        generate_graph()
    graph = json.loads(Path('graph.json').read_text())
    # to_sqlite
    if Path('graph.db').exists():
        Path('graph.db').unlink()
    sqldb = sqlite3.connect('graph.db')
    cur = sqldb.cursor()
    cur.execute('''CREATE TABLE node (
        name VARCHAR(255),
        type VARCHAR(255),
        doc_id VARCHAR(255),
        monitored bool,
        pub_date VARCHAR(255),
        in_force bool)''')
    cur.execute('''CREATE TABLE edge (
        node_src INTEGER,
        node_dst INTEGER,
        mentions INTEGER,
        FOREIGN KEY(node_src) REFERENCES node(rowid) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY(node_dst) REFERENCES node(rowid) ON UPDATE CASCADE ON DELETE CASCADE)''')
    node_name_to_id = dict()
    for node in graph.values():
        cur.execute(
            '''INSERT INTO node(name,type,doc_id,monitored,pub_date,in_force) VALUES(?,?,?,?,?,?)''',
            (node['name'], node['type'], node['doc_id'], node['monitored'], node['pub_date'], node['in_force'])
        )
        node_name_to_id[node['name']] = cur.lastrowid
    for node in graph.values():
        node_src_nm = node['name']
        node_src = node_name_to_id[node_src_nm]
        for node_dst_nm, frequency in node['mention_freq'].items():
            node_dst = node_name_to_id[node_dst_nm]
            cur.execute(
                '''INSERT INTO edge(node_src,node_dst,mentions) VALUES(?,?,?)''',
                (node_src, node_dst, frequency)
            )
    cur.close()
    sqldb.commit()
    Path('graph.sql').write_text('\n'.join(sqldb.iterdump()))
    sqldb.close()
    # to_graphviz
    gv = graphviz.Digraph()
    for node in graph.values():
        gv.node(
            str(node_name_to_id[node['name']]),
            label='\n'.join(list(map(str, filter(
                lambda a: a is not None,
                [node['type'], node['doc_id'], node['pub_date']]
            ))))
        )
    for node in graph.values():
        node_src_nm = node['name']
        node_src = node_name_to_id[node_src_nm]
        for node_dst_nm, frequency in node['mention_freq'].items():
            node_dst = node_name_to_id[node_dst_nm]
            gv.edge(str(node_src), str(node_dst), str(frequency))
    gv.save('graph.gv')  # takes "forever" to render, "never" finishes
