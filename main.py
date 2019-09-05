from __future__ import absolute_import

import ast
import sys
import os
import sys
import git
from analyzer import Analyzer


def get_files(path, ext='.py'):
    filteredFiles = []
    for root, dirs, files in os.walk(path):
        filteredFiles += map(lambda f: os.path.join(root, f),
                             (filter(lambda x: x.strip().endswith(ext), files)))
    return filteredFiles


def process_file(file):
    with open(file, "r") as source:
        text = os.linesep.join(
            [s for s in source.read().splitlines() if s.strip()])

        tree = ast.parse(text)
        for node in ast.walk(tree):
            node.depth = 0
            for child in ast.iter_child_nodes(node):
                child.parent = node
                child.depth = 0

        analyzer = Analyzer()
        analyzer.visit(tree)
        analyzer.get_dups(file)
        return analyzer.stats()


def clone():
    git.Git().clone('https://github.com/jaspernbrouwer/powerline-gitstatus', './zip-bomb')


def main():
    # clone()
    files = get_files('./')
    stats = {'lines': 1}
    global_stats = []
    for file in files:
        try:
            stats = process_file('./analyzer.py')
        except Exception as e:
            print(e)
            print(file + ' => to python 3')

        global_stats.append(stats)
        break
    print(global_stats)


main()
