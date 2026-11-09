#!/usr/bin/env python3
"""Extract source PMX geometry, preserving original vertices and material faces.

Coordinates remain PMX units: +Y up, -Z front. No conversion to doll mm occurs.
"""
import argparse
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


class Reader:
    def __init__(self, data):
        self.data, self.offset, self.encoding = data, 0, 'utf-8'

    def take(self, n):
        if n < 0 or self.offset + n > len(self.data):
            raise ValueError('Truncated PMX')
        data = self.data[self.offset:self.offset+n]
        self.offset += n
        return data

    def read(self, fmt):
        values = struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))
        return values[0] if len(values) == 1 else values

    def text(self):
        return self.take(self.read('i')).decode(self.encoding)

    def index(self, size):
        return self.read({1:'b', 2:'h', 4:'i'}[size])


def load_pmx(path):
    r = Reader(Path(path).read_bytes())
    if r.take(4) != b'PMX ':
        raise ValueError('Not PMX')
    version = r.read('f')
    h = list(r.take(r.read('B')))
    r.encoding = 'utf-16-le' if h[0] == 0 else 'utf-8'
    metadata = dict(zip(('name', 'name_en', 'comment', 'comment_en'), (r.text() for _ in range(4))))
    vs, ns, uvs, bi, bw = [], [], [], [], []
    for _ in range(r.read('i')):
        vs.append(r.read('3f')); ns.append(r.read('3f')); uvs.append(r.read('2f'))
        r.take(16*h[1]); t = r.read('B')
        if t == 0:
            ids, weights = [r.index(h[5])], [1.0]
        elif t in (1, 3):
            ids = [r.index(h[5]) for j in range(2)]
            w = r.read('f'); weights = [w, 1-w]
            if t == 3: r.take(36)
        elif t in (2, 4):
            ids = [r.index(h[5]) for j in range(4)]
            weights = list(r.read('4f'))
        else:
            raise ValueError('Unknown deform '+str(t))
        bi.append(ids+[-1]*(4-len(ids))); bw.append(weights+[0.0]*(4-len(weights)))
        r.take(4)
    count = r.read('i')
    faces = np.frombuffer(r.take(count*h[2]), dtype={1:'u1',2:'<u2',4:'<u4'}[h[2]]).reshape(-1,3).copy()
    textures = [r.text() for _ in range(r.read('i'))]
    mats, offset = [], 0
    for _ in range(r.read('i')):
        name, en = r.text(), r.text()
        diffuse = r.read('4f')
        r.take(12+4+12+1+16+4)
        texture = r.index(h[3]); r.index(h[3]); r.take(1)
        shared = r.read('B'); r.take(1 if shared else h[3]); memo=r.text()
        count = r.read('i')//3
        mats.append(dict(name=name, name_en=en, start=offset, end=offset+count,
                         count=count, texture_index=texture, diffuse=diffuse, memo=memo))
        offset += count
    bones = []
    for _ in range(r.read('i')):
        name, en = r.text(), r.text()
        pos = r.read('3f'); parent=r.index(h[5]); layer=r.read('i'); flags=r.read('H')
        if flags & 1: r.index(h[5])
        else: r.take(12)
        if flags & 0x0300: r.index(h[5]); r.take(4)
        if flags & 0x0400: r.take(12)
        if flags & 0x0800: r.take(24)
        if flags & 0x2000: r.take(4)
        if flags & 0x0020:
            r.index(h[5]); r.take(4+4)
            for j in range(r.read('i')):
                r.index(h[5]); lim=r.read('B')
                if lim: r.take(24)
        bones.append(dict(name=name, name_en=en, position=pos, parent=parent, layer=layer, flags=flags))
    return dict(vertices=np.array(vs), normals=np.array(ns), uvs=np.array(uvs),
                faces=faces, bone_indices=np.array(bi), bone_weights=np.array(bw),
                materials=mats, textures=textures, metadata=metadata, bones=bones, version=version)


def topology(vertices, faces):
    used = np.unique(faces)
    local = np.full(len(vertices), -1, dtype=int); local[used]=np.arange(len(used))
    vv = vertices[used]
    # PMX repeats a vertex for normals/UV seams. Weld by position for diagnostics.
    _, unique_indices, inverse = np.unique(np.round(vv, 6), axis=0, return_index=True, return_inverse=True)
    verts = vv[unique_indices]; fs = inverse[local[faces]]
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in fs for a,b in zip(face,np.roll(face,-1)))
    parent=list(range(len(verts)))
    def root(i):
        while parent[i] != i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for a,b in edges:
        aa,bb=root(a),root(b)
        if aa != bb: parent[aa]=bb
    components=defaultdict(list)
    for i in range(len(verts)): components[root(i)].append(i)
    comp_info=[]
    for ids in sorted(components.values(), key=len, reverse=True):
        points=verts[ids]
        comp_info.append(dict(vertex_count=len(ids),bbox_min=points.min(0).tolist(),bbox_max=points.max(0).tolist()))
    boundary=[e for e,c in edges.items() if c == 1]
    adj=defaultdict(list)
    for a,b in boundary: adj[a].append(b); adj[b].append(a)
    seen=set(); loops=[]
    for start in adj:
        if start in seen: continue
        if len(adj[start]) != 2:
            # Still enumerate the connected boundary component, even if branched.
            stack=[start]; ids=[]
            while stack:
                a=stack.pop()
                if a in seen: continue
                seen.add(a); ids.append(a); stack.extend(adj[a])
            closed=False
        else:
            ids=[]; cur=start; prev=-1
            while cur not in seen:
                seen.add(cur); ids.append(cur)
                choices=[x for x in adj[cur] if x != prev]
                if not choices: break
                prev,cur=cur,choices[0]
            closed=cur==start
        points=verts[ids]
        length=sum(float(np.linalg.norm(points[(i+1)%len(points)]-p)) for i,p in enumerate(points))
        loops.append(dict(vertex_count=len(ids),closed=closed,length=length,
                          bbox_min=points.min(0).tolist(),bbox_max=points.max(0).tolist(),
                          center=points.mean(0).tolist(),vertices=points.tolist(),
                          vertex_ids=ids))
    return dict(raw_vertex_count=len(used),welded_vertex_count=len(verts),triangle_count=len(fs),
                boundary_edge_count=len(boundary),nonmanifold_edge_count=sum(c>2 for c in edges.values()),
                components=comp_info,boundary_loops=loops),verts,fs


def write_obj(path, verts, faces):
    with Path(path).open('w') as file:
        file.write('# Original March 7th PMX geometry; +Y up, -Z front; source units, not mm\n')
        for v in verts: file.write('v '+' '.join('%.9g'%x for x in v)+'\n')
        for f in faces: file.write('f '+' '.join(str(int(x)+1) for x in f)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--output',default='/private/tmp/march7-bjd-work');a=p.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    mesh=load_pmx(a.source)
    array_keys=('vertices','normals','uvs','faces','bone_indices','bone_weights')
    np.savez_compressed(out/'extracted_mesh.npz', **{k:mesh[k] for k in array_keys})
    summary={k:v for k,v in mesh.items() if k not in array_keys}
    summary['source']=str(Path(a.source).resolve());summary['units']='PMX original coordinates; not physical measurements'
    summary['topology']={}
    for i,mat in enumerate(mesh['materials']):
        faces=mesh['faces'][mat['start']:mat['end']]
        vs=mesh['vertices'][np.unique(faces)]
        mat['bbox_min']=vs.min(0).tolist();mat['bbox_max']=vs.max(0).tolist()
        if mat['name'] in ('脸','眼白','眼睛','眼睛1','脖子','口腔','眉毛'):
            info,verts,fs=topology(mesh['vertices'],faces)
            summary['topology'][mat['name']]=info
            name={'脸':'face','眼白':'eye_whites','眼睛':'eyes','眼睛1':'eyes1','脖子':'neck','口腔':'mouth','眉毛':'brows'}[mat['name']]
            write_obj(out/(name+'_source.obj'),verts,fs)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='boundary_loops'} for k,v in summary['topology'].items()},ensure_ascii=False,indent=2))
    print('Face boundary loops:')
    for i,loop in enumerate(summary['topology']['脸']['boundary_loops']):
        print(i,{k:v for k,v in loop.items() if k not in ('vertices','vertex_ids')})


if __name__ == '__main__':main()
