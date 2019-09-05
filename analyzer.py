"""
Visitor Pattern for the genrated AST.
"""
from __future__ import division
import ast
from orphanblack import api


class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.lines = set()
        self.depths = {}
        self.imports = set()
        self.loopsInside = set()
        self.variablesCount = 0

        self.funcs = 0
        self.funcsParams = 0
        self.duplicate_code = 0

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.loopsInside.add(node)
        node.depth += 1
        self.generic_visit(node)

    def visit_While(self, node):
        for _node in node.body:
            self.visit(_node)
            node.depth = max(_node.depth, node.depth)

        for _node in node.orelse:
            self.visit(_node)
            node.depth = max(_node.depth, node.depth)

    def visit_If(self, node):
        for _node in node.body:
            self.visit(_node)
            node.depth = max(_node.depth, node.depth)

        for _node in node.orelse:
            self.visit(_node)
            node.depth = max(_node.depth, node.depth)

    def visit_For(self, node):
        self.loopsInside.add(node)
        dp = []
        for _node in node.body:
            self.visit(_node)
            if _node.depth > 0:
                if not isinstance(_node, ast.Assign):
                    dp.append(_node.depth)
            node.depth = max(_node.depth, node.depth)

        node.depth += 1
        newDepth = self.depths.get(node.depth, 0) + 1
        self.depths[node.depth] = newDepth
        # Remove the innerloops depths
        for d in dp:
            self.depths[d] -= 1

    def visit_Call(self, node):
        for _node in node.args:
            self.visit(_node)
        self.generic_visit(node)
        node.parent.depth = max(node.parent.depth, node.depth)

    def visit_AnnAssign(self, node):
        self.variablesCount += 1
        self.generic_visit(node)
        node.parent.depth = max(node.parent.depth, node.depth)

    def visit_AugAssign(self, node):
        self.variablesCount += 1
        self.generic_visit(node)
        node.parent.depth = max(node.parent.depth, node.depth)

    def visit_Assign(self, node):
        for _node in node.targets:
            if isinstance(_node, ast.Tuple):
                self.variablesCount += len(_node.elts)
            else:
                self.variablesCount += 1
        self.generic_visit(node)
        node.parent.depth = max(node.parent.depth, node.depth)

    def visit_FunctionDef(self, node):
        self.funcsParams += len(node.args.args)
        self.funcs += 1

        for _node in node.body:
            self.visit(_node)
            node.depth = max(_node.depth, node.depth)
        node.parent.depth = max(node.parent.depth, node.depth)

    def generic_visit(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        _node = node
        while hasattr(_node, 'parent'):
            _node.parent.depth = max(_node.parent.depth, _node.depth)
            _node = _node.parent

    def calc_depth(self):
        """
        Calculate the depth using depth map where key is the depth and value
        is the number of loops with that depth. Delete all depths that have value of
        zero of less.
        """
        keys = self.depths.keys()
        for k in keys:
            if self.depths[k] <= 0:
                self.depths.pop(k)
        sm = 0
        for k, v in self.depths.items():
            sm += k * v

        res = {
            'sum_of_loops': sm,
            'number_of_loops': len(self.depths.keys()),
            'average': max(1, len(self.depths.keys()))
        }

        # If no nested loops
        if sm == 0:
            print(self.loopsInside)
            res = {
                'sum_of_loops': len(self.loopsInside),
                'number_of_loops': len(self.loopsInside),
                'average': 1
            }

        return res

    def visit(self, node):
        super(Analyzer, self).visit(node)
        if hasattr(node, 'lineno'):
            self.lines.add(node.lineno)

    def get_dups(self, file):
        try:
            self.duplicate_code = api.find_dups([file])
        except:
            pass

    def stats(self):
        depth_sum_length_mean = self.calc_depth()
        return {
            'loop_depth': depth_sum_length_mean,
            'num_lines': len(self.lines),
            'libraries': list(self.imports),
            'funcs': {
                'num_funcs': self.funcs,
                'num_params': self.funcsParams
            },
            'num_vars': self.variablesCount,
            'duplicate_code': {
                'size': self.duplicate_code,
                'ratio': min(1, self.duplicate_code / len(self.lines))
            }
        }
