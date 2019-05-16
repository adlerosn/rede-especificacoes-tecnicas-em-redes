#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import sqlite3
import graphviz
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from .documents import fromFile as DocumentFromFile
from .document_finder import classes as docClasses
from .document_finder import find_references as referenceFinder

INFINITY = float('inf')


def generate_graph(rootdoc='rootdoc.txt', grapfn='graph.json', keep_temporal_context=True):
    rootsrc, rootname = Path(rootdoc).read_text().splitlines()
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
                'generic_name': str(docCchMgr),
                'type': docCchMgr.__class__.__name__,
                'doc_id': docCchMgr._identifier,
                'monitored': False if docPath is None else docPath.exists(),
                'pub_date': docCchMgr.publication_date(docPath),
                'in_force': docCchMgr.is_in_force(docPath),
                'filepath': str(docPath),
                'mention_freq': dict(),
            }
        if docPath in analyzedDocPaths:
            continue
        analyzedDocPaths.append(docPath)
        docFF = DocumentFromFile(str(docPath))
        print(f"Document @ {currName}")
        if docFF is None:
            continue
        doc = docFF.parsed_from_cache(str(docPath)[6:])
        newReferences = referenceFinder(doc, docCchMgr.context(docPath))
        if not keep_temporal_context:
            newReferences = list(map(lambda a: a.whithout_temporal_context(), newReferences))
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
    Path(grapfn).write_text(json.dumps(graph))


def dijkstra(graph, initial, hops_mode=False):
    visited = {initial: 0}
    path = dict()

    nodes = set(graph.keys())

    while len(nodes) > 0:
        min_node = None
        for node in nodes:
            if node in visited:
                if min_node is None:
                    min_node = node
                elif visited[node] < visited[min_node]:
                    min_node = node

        if min_node is None:
            break

        nodes.remove(min_node)
        current_weight = visited[min_node]

        for edge, possible_weight in graph[min_node]['mention_freq'].items():
            weight = current_weight + (1 if hops_mode else possible_weight)
            if edge not in visited or weight < visited[edge]:
                visited[edge] = weight
                path[edge] = min_node
    return visited, path


def dijkstra_min_path(dijkstra_tuple, initial, target):
    visited, path = dijkstra_tuple
    min_path = list()
    current = target
    if current in path or current == initial:
        while current is not None:
            min_path.append(current)
            current = path.get(current)
        return (list(reversed(min_path)), visited[target])
    return ([], None)


def embed_metrics(graph):
    metrics = dict()
    metrics['basic'] = dict()
    metrics['basic']['node_count'] = len(graph)
    metrics['basic']['vertex_count'] = 0
    metrics['basic']['vertex_weight_sum'] = 0
    for node in graph.values():
        metrics['basic']['vertex_count'] += len(node['mention_freq'])
        metrics['basic']['vertex_weight_sum'] += sum(node['mention_freq'].values())
    matrix_labels = list(graph.keys())
    metrics['matrix_labels'] = matrix_labels
    metrics['degree'] = dict()
    for key, node in graph.items():
        metric = dict()
        metric['degree_out'] = len(node['mention_freq'].values())
        metric['weight_out'] = sum(node['mention_freq'].values())
        metric['degree_in'] = 0
        metric['weight_in'] = 0
        for node2 in graph.values():
            count = node2['mention_freq'].get(key, 0)
            if count > 0:
                metric['degree_in'] += 1
                metric['weight_in'] += count
        metrics['degree'][key] = metric
    tpe = ProcessPoolExecutor(multiprocessing.cpu_count())
    print("Slow Dijkstra: Hops")
    metrics['dijkstra_hops'] = [
        tpe.submit(dijkstra, graph, initial, True)
        for initial in matrix_labels
    ]
    metrics['dijkstra_hops'] = list(map(lambda future: future.result(), metrics['dijkstra_hops']))
    print("Slow Dijkstra: Weight")
    metrics['dijkstra_weight'] = [
        tpe.submit(dijkstra, graph, initial, False)
        for initial in matrix_labels
    ]
    metrics['dijkstra_weight'] = list(map(lambda future: future.result(), metrics['dijkstra_weight']))
    tpe.shutdown()
    del tpe
    metrics['distance_matrix_hops'] = [[
        metrics['dijkstra_hops'][pos][1].get(target, None)
        for target in matrix_labels
    ] for pos, initial in enumerate(matrix_labels)]
    metrics['distance_matrix_weight'] = [[
        metrics['dijkstra_weight'][pos][1].get(target, None)
        for target in matrix_labels
    ] for pos, initial in enumerate(matrix_labels)]
    return metrics


def convert_outputs(prefix, temporal_context):
    if not Path(f'{prefix}.json').exists():
        generate_graph(grapfn=f'{prefix}.json', keep_temporal_context=temporal_context)
    graph = json.loads(Path(f'{prefix}.json').read_text())
    if not Path(f'{prefix}_metrics.json').exists() or True:
        Path(f'{prefix}_metrics.json').write_text(json.dumps(embed_metrics(graph), indent=2))
    metrics = json.loads(Path(f'{prefix}_metrics.json').read_text())
    # to_sqlite
    if Path(f'{prefix}.db').exists():
        Path(f'{prefix}.db').unlink()
    sqldb = sqlite3.connect(f'{prefix}.db')
    cur = sqldb.cursor()
    cur.execute('''CREATE TABLE node (
        name VARCHAR(255),
        generic_name VARCHAR(255),
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
    cur.execute(f'''CREATE VIEW nodes AS
        SELECT
            rowid as id,
            {'name' if temporal_context else 'generic_name'} as label
        FROM node''')
    cur.execute('''CREATE VIEW edges AS
        SELECT
            rowid as id,
            node_src as source,
            node_dst as target,
            mentions as weight
        FROM edge''')
    node_name_to_id = dict()
    for node in graph.values():
        cur.execute(
            '''INSERT INTO node(
                name,
                generic_name,
                type,
                doc_id,
                monitored,
                pub_date,
                in_force
            ) VALUES(?,?,?,?,?,?,?)''',
            (
                node['name'],
                node['generic_name'],
                node['type'],
                node['doc_id'],
                node['monitored'],
                node['pub_date'],
                node['in_force']
            )
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
    Path(f'{prefix}.sql').write_text('\n'.join(sqldb.iterdump()))
    sqldb.close()
    # to_csv
    with open(f'{prefix}.csv', 'w') as file:
        file.write('%s,%s,%s\n' % ("source", "target", "weight"))
        for node in graph.values():
            node_src_nm = node['name']
            for node_dst_nm, frequency in node['mention_freq'].items():
                file.write('%s,%s,%d\n' % (
                    graph[node_src_nm]['name' if temporal_context else 'generic_name'],
                    graph[node_dst_nm]['name' if temporal_context else 'generic_name'],
                    frequency
                ))
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
    gv.save(f'{prefix}.gv')  # takes "forever" to render, "never" finishes


def main():
    convert_outputs('graph', True)
    convert_outputs('graph_noctx', False)
