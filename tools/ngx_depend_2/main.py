# -*- coding:utf-8 -*-

import os
import subprocess
import glob
import json
from pprint import pprint

def get_file_info(file_path):
    """通过nm程序获取object文件定义和使用的符号"""
    cmd = 'nm -g ' + file_path
    out = subprocess.getoutput(cmd)
    info = {
        "defines" : [],
        "uses" : [],
    }
    for line in out.splitlines():
        txt = line.split()
        if txt[-2] == 'U':
            info["uses"].append(txt[-1])
        else:
            info["defines"].append(txt[-1])
    # pprint(info)
    return info

def build_data(objs_dir):
    data = {}
    objs_dir = os.path.abspath(objs_dir)
    for file_path in glob.glob(objs_dir + '/**/*.o', recursive=True):
        name = os.path.basename(file_path)
        if name in data:
            raise Exception("duplicate name '%s'" % name)
        data[name] = get_file_info(file_path)
        data[name]['name'] = name
    # pprint(data)
    return data

def analysis_depends(data):
    symbol_define = {}
    for name, info in data.items():
        for symbol in info['defines']:
            if symbol in symbol_define:
                raise Exception("'%s' redefined in '%s' and '%s'" %
                        (symbol, symbol_define[symbol], name))
            else:
                symbol_define[symbol] = name
    # pprint(symbol_define)
    for _, info in data.items():
        info['depends'] = []
        for symbol in info['uses']:
            if symbol in symbol_define:
                info['depends'].append(symbol_define[symbol])
        info['depends'] = list(set(info['depends']))
    # pprint(data)
    return data

def analysis_class_depend(class_db, file_db):
    """按分类计算依赖"""
    # 在file_db中标记文件的归属类
    for class_name in class_db:
        for file_name in class_db[class_name]['files']:
            file_db[file_name]['class'] = class_name

    # 将未在class_db中定义的文件，每个文件单独设在为一类
    for file_name in file_db:
        if 'class' not in file_db[file_name]:
            file_db[file_name]['class'] = file_name
            class_db[file_name] = {
                "files" : [file_name]
            }
    if '_' in class_db:
        del class_db['_']
    for class_name in class_db:
        class_depends = set()
        for file_name in class_db[class_name]['files']:
            for depend_file in file_db[file_name]['depends']:
                depend = file_db[depend_file]['class']
                if depend == '_': continue
                class_depends.add(depend)
                #调试打印一些特殊的依赖关系
                # if class_name == 'core' and depend == 'ngx_http_upstream_hash_module.o':
                #     print('core->ngx_http_upstream_hash_module.o : %s->%s' %(file_name, depend_file))
        if class_name in class_depends:
            class_depends.remove(class_name)
        class_db[class_name]['depends'] = list(class_depends)
    return class_db

def save_data(data, path):
    with open(path, 'w') as fp:
        json.dump(data, fp, indent=4)

def load_data(path):
    with open(path, 'r') as fp:
        return json.load(fp)

def dfs(data, head, node, path):
    for subname in node['depends']:
        subnode = data[subname]
        if subname == head:
            print("->".join(path))
        elif subnode['visit'] == False and subname not in path:
            path.append(subname)
            dfs(data, head, subnode, path)
            path.pop()

def print_loop(data):
    for _, node in data.items():
        node['visit'] = False
    # 手动排除一部分文件，不参与依赖检查
    data['ngx_modules.o']['visit'] = True
    for head, node in data.items():
        if node['visit'] == False:
            print("----%s--" % head)
            dfs(data, head, node, [head])
            node['visit'] = True

def dfs_check(data, node, path):
    for subname in node['depends']:
        subnode = data[subname]
        if subname in path:
            idx = path.index(subname)
            print("->".join(path[idx:]))
        elif subnode['visit'] == False:
            path.append(subname)
            dfs_check(data, subnode, path)
            path.pop()
    node['visit'] = True

def check_loop(data):
    for _, node in data.items():
        node['visit'] = False
    # 手动排除一部分文件，不参与依赖检查
    data['ngx_modules.o']['visit'] = True
    data['ngx_log.o']['visit'] = True
    data['ngx_cycle.o']['visit'] = True
    for head, node in data.items():
        if node['visit'] == False:
            dfs_check(data, node, [head])

def gen_dot_graph(dot_path, db):
    with open(dot_path, 'w') as f:
        f.write("digraph G {\n")
        for name, data in db.items():
            for depend in data['depends']:
                f.write('"%s" -> "%s"\n'%(name, depend))
        f.write("}")

def gen_img_file(dot_path, img_path):
    cmd = "dot %s -Tsvg -o %s" %(dot_path, img_path)
    subprocess.call(cmd, shell=True)

# file_data = build_data('/data/nginx/nginx_comment/objs')
# file_data = analysis_depends(file_data)
file_data_path = 'data.json'
# save_data(file_data, file_data_path)
file_data = load_data(file_data_path)

class_define_path ='class_define.json'
class_data = load_data(class_define_path)
class_data = analysis_class_depend(class_data, file_data)
class_data_path = 'class_data.json'
save_data(class_data, class_data_path)

# class_data = load_data(class_data_path)
# print_loop(file_data)
# check_loop(file_data)

dot_file = 'class_depend.dot'
gen_dot_graph(dot_file, class_data)

svg_file = 'class_depend.svg'
gen_img_file(dot_file, svg_file)
# dot class_depend.dot -Tpng -o class_depend.png