# -*- coding:utf-8 -*-
import os
import json

def dfs(data, head, node, path):
    for subname in node['depends']:
        subnode = data[subname]
        if subname == head:
            print("->".join(path))
        elif subname not in path and subnode['visit'] == False:
            path.append(subname)
            dfs(data, head, subnode, path)
            path.pop()

work_dir = os.path.abspath(os.path.join(__file__, '../'))
data_file = os.path.join(work_dir, 'data.json')

with open(data_file, 'r') as fp:
    data = json.load(fp)

for _, node in data.items():
    node['visit'] = False

for head, node in data.items():
    dfs(data, head, node, [head])
    node['visit'] = True



