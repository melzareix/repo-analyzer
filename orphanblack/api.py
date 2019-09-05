# TODO: This file needs to allow explicitly the following:
# Run a scan on a particular path with any file selection criteria
# Load results of any previous scan
# Automatically find canidate results to load.

# TODO: Do apis take filenames or file objects?


import sys
import manifest
from ast_suppliers import abstract_syntax_tree_suppliers
from clone_detection_algorithm import *
from parameters import Parameters
from report import Report, CloneSummary, Snippet, save_report, load_report


def find_dups(source_file_names, language='python'):
    supplier = abstract_syntax_tree_suppliers[language]

    # TODO: Configuration files!
    parameters = Parameters()
    parameters.distance_threshold = supplier.distance_threshold
    parameters.size_threshold = supplier.size_threshold

    source_files = []

    report = Report(parameters)

    def parse_file(file_name):
        try:
            source_file = supplier(file_name, parameters)
            source_file.getTree().propagateCoveredLineNumbers()
            source_file.getTree().propagateHeight()
            source_files.append(source_file)
            report.addFileName(file_name)
        except Exception as e:
            print(e)

    for file_name in source_file_names:
        parse_file(file_name)

    duplicates = findDuplicateCode(
        source_files, report)

    res = 0
    for d in duplicates:
        res += d.calcSize()
    return res
