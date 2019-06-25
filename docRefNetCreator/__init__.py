#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import queue
import sqlite3
import networkx
import graphviz
import multiprocessing
from pathlib import Path
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

from .documents import PlainCachedDocument
from .documents import fromExtension as DocumentFromExtension
from .document_finder import classes as docClasses
from .document_finder import find_references as referenceFinder
from .word_count import WordCounter

INFINITY = float('inf')
EMPTY_ITER = iter(list())
QUADRANT_COLOR = ['#7DB643', '#43B5B5', '#7C43B5', '#B54343']


def find_rootdoc(rootdoc='rootdoc.txt'):
    rootsrc, rootname = Path(rootdoc).read_text().splitlines()
    docCchMgr = docClasses[rootsrc](rootname)
    docPath = docCchMgr.cached()
    currName = f"{docCchMgr.__class__.__name__}: {docCchMgr._identifier}"
    if docPath is not None:
        currName = str(docPath)[6:]
    return {
        'name': currName,
        'generic_name': str(docCchMgr),
        'type': docCchMgr.__class__.__name__,
        'doc_id': docCchMgr._identifier,
        'filepath': str(docPath),
        'object': docCchMgr,
    }


def generate_graph(rootdoc='rootdoc.txt', grapfn='graph.json', keep_temporal_context=True):
    rootsrc, rootname = Path(rootdoc).read_text().splitlines()
    analyzedDocPaths = set()
    pendingDocCchMgr = queue.Queue()
    pendingDocCchMgr.put(docClasses[rootsrc](rootname))
    graph = dict()
    while not pendingDocCchMgr.empty():
        docCchMgr = pendingDocCchMgr.get_nowait()
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
        analyzedDocPaths.add(docPath)
        docFFcls = DocumentFromExtension(str(docPath).split('.')[-1])
        print(f"Document @ {currName}")
        if docFFcls is None:
            continue
        docFF = PlainCachedDocument(str(docPath)[6:], docFFcls, docPath)
        doc = docFF.parsed_from_cache()
        newReferences = referenceFinder(str(docPath)[6:], doc, docCchMgr.context(docPath))
        if not keep_temporal_context:
            newReferences = list(map(lambda a: a.whithout_temporal_context(), newReferences))
        for newReference in newReferences:
            newDocPath = newReference.cached()
            newName = f"{newReference.__class__.__name__}: {newReference._identifier}"
            if newDocPath is not None:
                newName = str(newDocPath)[6:]
            graph[currName]['mention_freq'][newName] = graph[currName]['mention_freq'].get(newName, 0) + 1
        for item in sorted(
            newReferences,
            key=lambda dcm: (not dcm.is_cached(), dcm.slowness(), dcm._identifier)
        ):
            pendingDocCchMgr.put_nowait(item)
        print(f"Queue size: {pendingDocCchMgr.qsize()} // Processed: {len(analyzedDocPaths)}")
    Path(grapfn).write_text(json.dumps(graph))


def dijkstra(graph, initial, hops_mode=False):
    visited = {initial: 0}
    path = dict()

    nodes = set(graph.keys())
    mentions = {node: list(graph[node]['mention_freq'].items()) for node in nodes}

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

        for edge, possible_weight in mentions[min_node]:
            weight = current_weight + (1 if hops_mode else possible_weight)
            if edge not in visited or weight < visited[edge]:
                visited[edge] = weight
                path[edge] = min_node
    return visited, path


class Dijkstra:
    def __init__(self, graph, hops_mode=False):
        self._graph = graph
        self._hops_mode = hops_mode

    def __call__(self, initial):
        return dijkstra(self._graph, initial, self._hops_mode)


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
    metrics['matrix_labels'] = list(graph.keys())
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
    return metrics


def embed_metrics_distance(graph, metrics):
    distance = dict()
    matrix_labels = metrics['matrix_labels']
    tpe = ProcessPoolExecutor(multiprocessing.cpu_count())
    print("Slow Dijkstra: Hops")
    dj = Dijkstra(graph, True)
    dijkstra = list(tpe.map(dj, matrix_labels))
    distance['distance_matrix_hops'] = [[
        dijkstra[pos][0].get(target, -1)
        for target in matrix_labels
    ] for pos, initial in enumerate(matrix_labels)]
    del dijkstra
    del dj
    print("Slow Dijkstra: Weight")
    dj = Dijkstra(graph, False)
    dijkstra = list(tpe.map(dj, matrix_labels))
    distance['distance_matrix_weight'] = [[
        dijkstra[pos][0].get(target, -1)
        for target in matrix_labels
    ] for pos, initial in enumerate(matrix_labels)]
    del dijkstra
    del dj
    tpe.shutdown()
    return distance


def embed_metrics_connectivity(graph, metrics, g, namefield):
    connectivity = dict()
    print('connectivity_edge')
    connectivity['connectivity_edge'] = networkx.edge_connectivity(g)
    print('connectivity_node')
    connectivity['connectivity_node'] = networkx.node_connectivity(g)
    return connectivity


def get_transition_map(graph):
    transitions = [(source, target) for source, nd in graph.items() for target in nd['mention_freq'].keys()]
    transmap = dict()
    for s, t in transitions:
        if t not in transmap:
            transmap[t] = list()
        transmap[t].append(s)
    return transmap


def find_all_paths(tm, initial, target, accumulator=None):
    if accumulator is None:
        accumulator = list()
    accumulator = [*accumulator, initial]
    if initial == target:
        yield accumulator
    else:
        for intermediate in tm[initial]:
            if intermediate not in accumulator:
                yield from find_all_paths(tm, intermediate, target, accumulator)
        yield from EMPTY_ITER


def find_all_loopy_paths(graph, node):
    tm = get_transition_map(graph)
    accumulator = [node]
    for intermediate in tm[node]:
        yield from find_all_paths(tm, intermediate, node, accumulator)
    yield from EMPTY_ITER


def get_reverse_transition_map(graph, sequential):
    transitions = [
        (sequential.index(source), sequential.index(target))
        for source, nd in graph.items() for target in nd['mention_freq'].keys()
    ]
    revtransmap = [list() for _ in sequential]
    for s, t in transitions:
        revtransmap[t].append(s)
    return tuple([tuple(i) for i in revtransmap])


def find_all_loopy_paths_reversedly(graph, node, sequential):
    revtransmap = get_reverse_transition_map(graph, sequential)
    accumulator = [sequential.index(node)]
    for intermediate in revtransmap[accumulator[0]]:
        yield from find_all_paths_reversedly(revtransmap, intermediate, accumulator[0], accumulator)
    yield from EMPTY_ITER


def find_all_paths_reversedly(revtransmap, initial, target, accumulator=None):
    if accumulator is None:
        accumulator = list()
    accumulator = [initial, *accumulator]
    if initial == target:
        yield accumulator
    else:
        for intermediate in revtransmap[initial]:
            if intermediate not in accumulator:
                yield from find_all_paths_reversedly(revtransmap, intermediate, target, accumulator)
        yield from EMPTY_ITER


def find_related_to_root(graph, root, sequential=None):
    print(root)
    lst = list()
    if sequential is None:
        sequential = list(graph.keys())
    sequential = tuple(sequential)
    for item in find_all_loopy_paths_reversedly(graph, root['name'], sequential):
        item = [sequential[i] for i in item]
        print(item)
        lst.append(item)
    print()
    print(lst)
    print()
    return lst


def get_quadrant(x, y, lx, ly):
    if x < lx and y < ly:
        return 3
    elif x >= lx and y < ly:
        return 4
    elif x >= lx and y >= ly:
        return 1
    else:
        return 2


def draw_degree_quadrants(graph, degrees, key):
    quadrants = dict()
    points = [
        (degree[f'{key}_in'], degree[f'{key}_out'])
        for degree in degrees.values()
    ]
    xs, ys = list(zip(*points))
    maxx = max(xs)
    minx = min(xs)
    maxy = max(ys)
    miny = min(ys)
    avgx = sum(xs)/len(xs)
    avgy = sum(ys)/len(ys)
    midx = (maxx-minx)/2
    midy = (maxy-miny)/2
    quads = [0, 0, 0, 0]
    for point in points:
        quads[get_quadrant(*point, midx, midy)-1] += 1
    plt.figure(figsize=(12, 9), dpi=300)
    plt.scatter(*list(zip(*points)), color='blue', alpha=.1)
    plt.plot([minx, maxx], [avgy, avgy], color='red', alpha=.5)
    plt.plot([avgx, avgx], [miny, maxy], color='red', alpha=.5)
    plt.plot([minx, maxx], [midy, midy], color='green', alpha=.5)
    plt.plot([midx, midx], [miny, maxy], color='green', alpha=.5)
    plt.text(1.5*midx, 1.5*midy, str(quads[0]), color='green')
    plt.text(0.5*midx, 1.5*midy, str(quads[1]), color='green')
    plt.text(0.5*midx, 0.5*midy, str(quads[2]), color='green')
    plt.text(1.5*midx, 0.5*midy, str(quads[3]), color='green')
    plt.text(0, -maxy/9, 'x=%.2f; y=%.2f' % (avgx, avgy), color='red')
    plt.text(1.5*midx, -maxy/9, 'x=%.2f; y=%.2f' % (midx, midy), color='green')
    plt.xlabel(f"{key} in")
    plt.ylabel(f"{key} out")
    quadrants['centroid'] = {'x': avgx, 'y': avgy}
    quadrants['halfrange'] = {'x': midx, 'y': midy}
    quadrants['halfrange_quadrants'] = quads
    return quadrants


def convert_outputs(prefix, temporal_context):
    Path("flavors.json").write_text(
        json.dumps(
            [
                *json.loads(Path("flavors.json").read_text()),
                prefix
            ],
            indent=4
        )
    )
    label_key = 'name' if temporal_context else 'generic_name'
    if not Path(f'{prefix}.json').exists():
        generate_graph(grapfn=f'{prefix}.json', keep_temporal_context=temporal_context)
    graph = json.loads(Path(f'{prefix}.json').read_text())
    if not Path(f'{prefix}_metrics.json').exists():
        Path(f'{prefix}_metrics.json').write_text(json.dumps(embed_metrics(graph), indent=2))
    metrics = json.loads(Path(f'{prefix}_metrics.json').read_text())
    if not Path(f'{prefix}_metrics_distances.json').exists():
        Path(f'{prefix}_metrics_distances.json').write_text(json.dumps(embed_metrics_distance(graph, metrics)))
    # to_networkx
    g = networkx.DiGraph()
    g.add_nodes_from([node[label_key] for node in graph.values()])
    g.add_edges_from([
        (node_source[label_key], graph[target][label_key])
        for node_source in graph.values()
        for target in node_source['mention_freq'].keys()
    ])
    networkx.write_graphml(g, f'{prefix}_unweighted.graphml')
    for src in graph.values():
        srcnm = src[label_key]
        for tgt, w in src['mention_freq'].items():
            tgtnm = graph[tgt][label_key]
            g[srcnm][tgtnm]['weight'] = w
    networkx.write_graphml(g, f'{prefix}_weighted.graphml')
    g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_unweighted.graphml'))
    g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_weighted.graphml'))
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
            {label_key} as label
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
                    graph[node_src_nm][label_key],
                    graph[node_dst_nm][label_key],
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
    # connectivity
    g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_unweighted.graphml'))
    if not Path(f'{prefix}_metrics_connectivity.json').exists():
        Path(f'{prefix}_metrics_connectivity.json').write_text(json.dumps(
            embed_metrics_connectivity(graph, metrics, g, label_key), indent=2))
    # matplotlib rendering
    if not Path(f'{prefix}_unweighted.pdf').exists() or not Path(f'{prefix}_unweighted.png').exists():
        g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_unweighted.graphml'))
        networkx.draw(g)
        plt.savefig(f'{prefix}_unweighted.pdf')
        plt.savefig(f'{prefix}_unweighted.png')
        plt.close()
    if not Path(f'{prefix}_weighted.pdf').exists() or not Path(f'{prefix}_weighted.png').exists():
        g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_weighted.graphml'))
        networkx.draw(g)
        plt.savefig(f'{prefix}_weighted.pdf')
        plt.savefig(f'{prefix}_weighted.png')
        plt.close()
    # Leave root document explicit
    if not Path(f'{prefix}_root.json').exists():
        Path(f'{prefix}_root.json').write_text(json.dumps(
            graph[find_rootdoc()['name']]
        ))
    # Plot quadrants
    for weight in [True, False]:
        desc = ('un'*int(not weight))+'weighted'
        if not Path(f'{prefix}_quads_{desc}.pdf').exists() or not Path(f'{prefix}_quads_{desc}.png').exists():
            key = 'weight' if weight else 'degree'
            dimen_cutoff = draw_degree_quadrants(graph, metrics['degree'], key)
            plt.savefig(f'{prefix}_quads_{desc}.pdf', bbox_inches='tight')
            plt.savefig(f'{prefix}_quads_{desc}.png', bbox_inches='tight')
            Path(f'{prefix}_quads_{desc}.json').write_text(json.dumps(dimen_cutoff, indent=4))
    for weight in [True, False]:
        desc = ('un'*int(not weight))+'weighted'
        if True or not Path(f'{prefix}_quads_{desc}.csv').exists():
            key = 'weight' if weight else 'degree'
            dimen_cutoff = json.loads(Path(f'{prefix}_quads_{desc}.json').read_text())
            with open(f'{prefix}_quads_{desc}.csv', 'w') as file:
                fmt = ','.join(['%s']*(4+int(weight)))+'\n'
                hr = (dimen_cutoff['halfrange']['x'], dimen_cutoff['halfrange']['y'])
                file.write(fmt % ("source", "target", *(["weight"]*int(weight)), "source_color", "target_color"))
                for node in graph.values():
                    node_src_nm = node['name']
                    src_metric = metrics['degree'][node_src_nm]
                    for node_dst_nm, frequency in node['mention_freq'].items():
                        dst_metric = metrics['degree'][node_dst_nm]
                        file.write(fmt % (
                            graph[node_src_nm][label_key],
                            graph[node_dst_nm][label_key],
                            *([frequency]*int(weight)),
                            QUADRANT_COLOR[get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr)-1],
                            QUADRANT_COLOR[get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr)-1],
                        ))
            with open(f'{prefix}_quads_{desc}_nodst3rdquad.csv', 'w') as file:
                fmt = ','.join(['%s']*(4+int(weight)))+'\n'
                hr = (dimen_cutoff['halfrange']['x'], dimen_cutoff['halfrange']['y'])
                file.write(fmt % ("source", "target", *(["weight"]*int(weight)), "source_color", "target_color"))
                for node in graph.values():
                    node_src_nm = node['name']
                    src_metric = metrics['degree'][node_src_nm]
                    for node_dst_nm, frequency in node['mention_freq'].items():
                        dst_metric = metrics['degree'][node_dst_nm]
                        if get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr) == 3:
                            continue
                        file.write(fmt % (
                            graph[node_src_nm][label_key],
                            graph[node_dst_nm][label_key],
                            *([frequency]*int(weight)),
                            QUADRANT_COLOR[get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr)-1],
                            QUADRANT_COLOR[get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr)-1],
                        ))
            with open(f'{prefix}_quads_{desc}_nosrc3rdquad.csv', 'w') as file:
                fmt = ','.join(['%s']*(4+int(weight)))+'\n'
                hr = (dimen_cutoff['halfrange']['x'], dimen_cutoff['halfrange']['y'])
                file.write(fmt % ("source", "target", *(["weight"]*int(weight)), "source_color", "target_color"))
                for node in graph.values():
                    node_src_nm = node['name']
                    src_metric = metrics['degree'][node_src_nm]
                    if get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr) == 3:
                        continue
                    for node_dst_nm, frequency in node['mention_freq'].items():
                        dst_metric = metrics['degree'][node_dst_nm]
                        file.write(fmt % (
                            graph[node_src_nm][label_key],
                            graph[node_dst_nm][label_key],
                            *([frequency]*int(weight)),
                            QUADRANT_COLOR[get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr)-1],
                            QUADRANT_COLOR[get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr)-1],
                        ))
            with open(f'{prefix}_quads_{desc}_no3rdquad.csv', 'w') as file:
                fmt = ','.join(['%s']*(4+int(weight)))+'\n'
                hr = (dimen_cutoff['halfrange']['x'], dimen_cutoff['halfrange']['y'])
                file.write(fmt % ("source", "target", *(["weight"]*int(weight)), "source_color", "target_color"))
                for node in graph.values():
                    node_src_nm = node['name']
                    src_metric = metrics['degree'][node_src_nm]
                    if get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr) == 3:
                        continue
                    for node_dst_nm, frequency in node['mention_freq'].items():
                        dst_metric = metrics['degree'][node_dst_nm]
                        if get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr) == 3:
                            continue
                        file.write(fmt % (
                            graph[node_src_nm][label_key],
                            graph[node_dst_nm][label_key],
                            *([frequency]*int(weight)),
                            QUADRANT_COLOR[get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr)-1],
                            QUADRANT_COLOR[get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr)-1],
                        ))
    if True:
        folder_out = Path(f'{prefix}_quads_unweighted_no2nd3rdquad')
        folder_out.mkdir(parents=True, exist_ok=True)
        for node in graph.values():
            node_src_nm = node['name']
            src_metric = metrics['degree'][node_src_nm]
            if get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr) in [2, 3]:
                continue
            with folder_out.joinpath(f'{node["generic_name"]}.csv').open('w') as file:
                fmt = ','.join(['%s']*5)+'\n'
                hr = (dimen_cutoff['halfrange']['x'], dimen_cutoff['halfrange']['y'])
                file.write(fmt % ("source", "target", "source_color", "target_color", "similarity"))
                srcWC = None
                srcCacheKey = graph[node_src_nm]['filepath'][6:]
                if len(srcCacheKey) > 0:
                    srcDoc = PlainCachedDocument(srcCacheKey, None).parse(' ')
                    srcWC = WordCounter(srcDoc)
                for node_dst_nm, frequency in node['mention_freq'].items():
                    dst_metric = metrics['degree'][node_dst_nm]
                    # if get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr) == 3:
                    #     continue
                    similarity = '?'
                    dstCacheKey = graph[node_dst_nm]['filepath'][6:]
                    if len(dstCacheKey) > 0:
                        dstDoc = PlainCachedDocument(dstCacheKey, None).parse(' ')
                        dstWC = WordCounter(dstDoc)
                        if srcWC is not None:
                            similarity = srcWC.vectorSimilarity(dstWC)
                            similarity = str(similarity[0][0])
                    file.write(fmt % (
                        graph[node_src_nm][label_key],
                        graph[node_dst_nm][label_key],
                        QUADRANT_COLOR[get_quadrant(src_metric[f'{key}_in'], src_metric[f'{key}_out'], *hr)-1],
                        QUADRANT_COLOR[get_quadrant(dst_metric[f'{key}_in'], dst_metric[f'{key}_out'], *hr)-1],
                        similarity,
                    ))
    if True or not Path(f'{prefix}_pagerank.json').exists():
        g = networkx.DiGraph(networkx.read_graphml(f'{prefix}_unweighted.graphml'))
        pr = networkx.pagerank(g)
        Path(f'{prefix}_pagerank.json').write_text(json.dumps(pr, indent=2))
        spr = sorted([
            (k, v) for k, v in pr.items()
        ], key=lambda a: (-a[1], a[0]))
        Path(f'{prefix}_pagerank_ranked.json').write_text(json.dumps(spr, indent=2))
        # dirLink = {k: set(v['mention_freq'].keys()) for k, v in graph.items()}
        revLink = {graph[k][label_key]: set() for k in graph.keys()}
        for ks, v in graph.items():
            ks = graph[ks][label_key]
            for kd in v['mention_freq'].keys():
                kd = graph[kd][label_key]
                revLink[kd].add(ks)
        sptr = {spr[0][0]: spr[0][0]}
        for node, rank in spr[1:]:
            maxNode = sorted([x for x in revLink[node] if x != node], key=lambda a: -pr[a])[0]
            sptr[node] = maxNode
        Path(f'{prefix}_pagerank_ranked_spannedtree.json').write_text(json.dumps(sptr, indent=2))
        table = ["source,target,source_weight,target_weight"]
        for ns, nd in sptr.items():
            ws = "%.32f" % pr[ns]
            wd = "%.32f" % pr[nd]
            table.append(f"{ns},{nd},{ws},{wd}")
        Path(f'{prefix}_pagerank_ranked_spannedtree.csv').write_text('\n'.join(table)+'\n')


def main():
    Path("flavors.json").write_text("[]")
    convert_outputs('graph', True)
    convert_outputs('graph_noctx', False)
