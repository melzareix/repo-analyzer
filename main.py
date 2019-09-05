from __future__ import absolute_import
from analyzer import Analyzer
import string
import git
import json
import sys
import random
import os
import re
import ast


rgx = re.compile(r'print ([/s]?(?! e)(.)+)')


def get_files(path, ext='.py'):
    filteredFiles = []
    for root, dirs, files in os.walk(path):
        filteredFiles += map(lambda f: os.path.join(root, f),
                             (filter(lambda x: x.strip().endswith(ext), files)))
    return filteredFiles


def process_file(file):
    with open(file, "r") as source:
        lines = rgx.sub(r'print(\1)', source.read())
        text = os.linesep.join(
            [s for s in lines.splitlines() if s.strip()])
        if (len(text) <= 0):
            return None
        tree = ast.parse(text)
        for node in ast.walk(tree):
            node.depth = 0
            for child in ast.iter_child_nodes(node):
                child.parent = node
                child.depth = 0

        analyzer = Analyzer()
        analyzer.visit(tree)
        analyzer.calc_duplicates(text)
        return analyzer.stats()


def clone(repo):
    repo_path = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for _ in range(20))
    repo_path = './repos/%s' % (repo_path)
    git.Git().clone(repo.strip(), repo_path)
    return repo_path


def merge_stats(repo, stats):
    result = {
        'repository_url': repo,
        'number of lines': 0,
        'libraries': [],
        'nesting factor': 0,
        'code duplication': 0,
        'average parameters': 0,
        'average variables': 0
    }

    num_of_files = len(stats)

    if num_of_files == 0:
        return json.dumps(result)

    sum_funcs = 0
    sum_func_params = 0
    sum_vars = 0
    sum_dup_ratio = 0
    sum_loop_depth = 0
    sum_num_loops = 0

    for stat in stats:
        result['number of lines'] += stat['num_lines']
        result['libraries'] += stat['libraries']

        sum_vars += stat['num_vars']

        sum_funcs += stat['funcs']['num_funcs']
        sum_func_params += stat['funcs']['num_params']

        sum_dup_ratio += stat['duplicate_code']['ratio']

        sum_num_loops += stat['loop_depth']['number_of_loops']
        sum_loop_depth += stat['loop_depth']['sum_of_loops']

    result['average variables'] = sum_vars / num_of_files
    result['libraries'] = list(set(result['libraries']))

    if sum_funcs == 0:
        result['average parameters'] = 0
    else:
        result['average parameters'] = sum_func_params / sum_funcs

    result['code duplication'] = sum_dup_ratio / num_of_files

    if sum_num_loops == 0:
        result['nesting factor'] = 0
    else:
        result['nesting factor'] = sum_loop_depth / sum_num_loops

    return json.dumps(result)


def analyze_repo(repo):
    try:
        path = clone(repo)
    except expression as identifier:
        return merge_stats(repo, [])

    files = get_files(path)
    stats = {}
    global_stats = []
    print('processing', repo)
    failed_files = 0
    for file in files:
        try:
            stats = process_file(file)
        except Exception as e:
            failed_files += 1
            # print('Failed to process', e, file)

        if stats is not None and len(stats.keys()) > 0:
            global_stats.append(stats)
    print('done ..', len(files) - failed_files, 'out of', len(files))
    return merge_stats(repo, global_stats)


if __name__ == "__main__":
    print(analyze_repo('https://github.com/BugScanTeam/DNSLog/'))
