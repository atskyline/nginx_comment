# -*- coding:utf-8 -*-

import os
import subprocess
import glob
from pprint import pprint
import json

def get_files(dir):
    """递归获取目录下的文件"""
    files = []
    for root, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if filename.endswith('.h') or filename.endswith('.c'):
                files.append(os.path.join(root[len(dir) + 1:], filename))
    return files

def get_symbols(file):
    """获取文件中定义的符号列表"""
    cmd = 'global -f ' + file
    out = subprocess.getoutput(cmd)
    symbols = []
    for line in out.splitlines():
        symbol = line.split(' ', 1)[0]
        # 发现 函数内定义的枚举类型，也会被列入到symbol中，不合理
        if symbol.startswith('ngx_'):
            symbols.append(symbol)
    return symbols

def get_references(symbol):
    """获取引用了符号的文件列表"""
    cmd = 'global -r ' + symbol
    out = subprocess.getoutput(cmd)
    return out.splitlines()

def gen_fileinfo(file):
    def print_depend(symbol, new_references, a, b):
        if file == b and a in new_references:
            print("%s->%s:%s"%(a, b, symbol))
    def remove_depend(new_references, a, b):
        if file == b and a in new_references:
            new_references.remove(a)

    symbols = get_symbols(file)
    references = set()
    for symbol in symbols:
        new_references = get_references(symbol)
        # 有一些global程序分析不合理的依赖手动删除掉
        remove_depend(new_references, 'core/ngx_thread_pool.h', 'http/ngx_http_core_module.h')
        remove_depend(new_references, 'core/ngx_thread_pool.c', 'http/ngx_http_core_module.h')
        remove_depend(new_references, 'http/modules/ngx_http_split_clients_module.c', 'stream/ngx_stream_split_clients_module.c')
        remove_depend(new_references, 'stream/ngx_stream_split_clients_module.c', 'http/modules/ngx_http_split_clients_module.c')
        # 调试打印一些特殊的依赖关系
        print_depend(symbol, new_references, 'core/ngx_string.c', 'http/ngx_http_request.c')
        print_depend(symbol, new_references, 'http/modules/ngx_http_split_clients_module.c', 'stream/ngx_stream_split_clients_module.c')
        print_depend(symbol, new_references, 'stream/ngx_stream_split_clients_module.c', 'http/modules/ngx_http_split_clients_module.c')

        references |= set(new_references)

    if file in references:
        references.remove(file)
    return {
        'path' : file,
        'symbols': symbols,
        'references' : list(references),
    }

def get_var_references(symbol):
    """查找不再GTAGS中的符号的引用"""
    cmd = 'global -s ' + symbol
    out = subprocess.getoutput(cmd)
    return out.splitlines()

# nm nginx --defined-only -l > nm.txt
# global无法将全局变量放在symbol中，所以利用编译后的nginx导出符号表分析其中的全局变量
# 由于编译参数的问题，通过bin文件导出的全局变量是不够完整的，但当前也没有更简单的方式
# 通过分析object文件获得依赖关系，无法处理宏定义、头文件等问题。
def parse_nm_txt(nm_txt, src_dir):
    result = {}
    with open(nm_txt) as f:
        lines = f.readlines()
    for line in lines:
        tokens = line.split()
        if tokens[1] != 'D' and tokens[1] != 'B' or len(tokens) != 4:
            continue
        symbol = tokens[2]
        file = tokens[3][len(src_dir):].split(':')[0]
        if file in result:
            result[file]['symbols'].append(symbol)
        else:
            result[file] ={
                'path' : file,
                'symbols': [symbol],
             }
    return result

def gen_var_references(vars):
    for file, var in vars.items():
        references = set()
        for symbol in var['symbols']:
            references |= set(get_var_references(symbol))
        if file in references:
            references.remove(file)
        var['references'] = list(references)
    return vars

def gen_depends(database, path):
    """在database的references中反向查找依赖"""
    depends = []
    for file in database:
        if path in database[file]['references']:
            depends.append(database[file]['path'])
    return depends

def gen_database(src_dir, vars):
    """ vars的设计不好，但先保留着，需要合并2份数据"""
    database = {}
    for file in get_files(src_dir):
        database[file] = gen_fileinfo(file)
        if file in vars:
            database[file]['symbols'].extend(vars[file]['symbols'])
            database[file]['symbols'] = list(set(database[file]['symbols']))
            database[file]['references'].extend(vars[file]['references'])
            database[file]['references'] = list(set(database[file]['references']))
    for file in database:
        database[file]['depends'] = gen_depends(database, file)
    return database

def save_database(database, path):
    with open(path, 'w') as fp:
        json.dump(database, fp, indent=4)

def load_database(path):
    with open(path, 'r') as fp:
        return json.load(fp)

def gen_dot_graph(dot_path, db):
    with open(dot_path, 'w') as f:
        f.write("digraph G {\n")
        for name, data in db.items():
            for depend in data['depends']:
                f.write('"%s" -> "%s"\n'%(name, depend))
        f.write("}")

def analysis_class_depend(class_db, file_db):
    """按分类计算依赖"""
    # 在file_db中标记文件的归属类
    for class_name in class_db:
        for file_name in class_db[class_name]['files']:
            file_db[file_name]['class'] = class_name
    for class_name in class_db:
        class_depends = set()
        for file_name in class_db[class_name]['files']:
            for depend_file in file_db[file_name]['depends']:
                if 'class' in file_db[depend_file]:
                    depend = file_db[depend_file]['class']
                    class_depends.add(depend)
                    #调试打印一些特殊的依赖关系
                    if class_name == 'core' and depend == 'http':
                        print('core->http : %s->%s' %(file_name, depend_file))
                    if class_name == 'http' and depend == 'stream':
                        print('http->stream : %s->%s' %(file_name, depend_file))
                    if class_name == 'stream' and depend == 'http':
                        print('stream->http : %s->%s' %(file_name, depend_file))
                    # if class_name == 'core' and depend == 'event':
                    #     print('core->event : %s->%s' %(file_name, depend_file))
                    if class_name == 'os' and depend == 'event':
                        print('os->event : %s->%s' %(file_name, depend_file))
        if class_name in class_depends:
            class_depends.remove(class_name)
        class_db[class_name]['depends'] = list(class_depends)
    return class_db


data_dir = os.path.abspath(os.path.join(__file__, '../'))
src_dir = os.path.abspath(os.path.join(__file__, '../../../src'))
# 执行分析前需要在src目录中执行gtags，生成好GTAGS数据库
os.chdir(src_dir)

# files = get_files(src_dir)
# pprint(files)
# symbols = get_symbols('core/ngx_array.c')
# print(symbols)
# references = get_references('ngx_array_push')
# print(references)
# file_info = gen_fileinfo('stream/ngx_stream_split_clients_module.c')
# pprint(file_info)

# nm_txt = os.path.join(data_dir, 'nm.txt')
# vars = parse_nm_txt(nm_txt, src_dir)
# vars = gen_var_references(vars)
# # pprint(vars)
# db_file = os.path.join(data_dir, 'data.json')
# data = gen_database(src_dir, vars)
# save_database(data, db_file)

db_file = os.path.join(data_dir, 'data.json')
file_db = load_database(db_file)
# pprint(db['http/ngx_http_upstream.c'])
class_define_file = os.path.join(data_dir, 'class_define.json')
class_db = load_database(class_define_file)
class_db_file = os.path.join(data_dir, 'class_data.json')
class_db = analysis_class_depend(class_db, file_db)
save_database(class_db, class_db_file)

# dot_file = os.path.join(data_dir, 'class_depend.dot')
# gen_dot_graph(dot_file, class_db)

# dot depend.dot -Tsvg -o depend.svg
# if __name__ == '__main__':