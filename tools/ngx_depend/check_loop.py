# -*- coding:utf-8 -*-
import os
import json

work_dir = os.path.abspath(os.path.join(__file__, '../'))
data_file = os.path.join(work_dir, 'class_data.json')

with open(data_file, 'r') as fp:
    data = json.load(fp)

for _, node in data.items():
    node['visit'] = 0

for name, node in data.items():
    if node['visit'] == 0:
        dfs(name, node, [])


def dfs(name, node, path):
    node['visit'] = 1
    path.append(name)
    for subname, subnode in node['depends']:
        if name in path and subnode['visit'] != 2:
            start_idx = path.index(subname)
            path.append(subname)
            print("->".join(path[start_idx:]))
            path.pop()
        dfs(subname, subnode, path)
    path.pop()
    node['visit'] = 2


