#    Copyright 2008 Peter Bulychev
#
#    This file is part of Clone Digger.
#
#    Clone Digger is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Clone Digger is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Clone Digger.  If not, see <http://www.gnu.org/licenses/>.

# TODO: JESUS. How many files like this are there?

import sys
import logging

import suffix_tree
from anti_unification import *
from abstract_syntax_tree import *


def findDuplicateCode(source_files, report):
    statement_sequences = []
    statement_count = 0
    sequences_lengths = []
    for source_file in source_files:
        sequences = source_file.getTree().getAllStatementSequences()
        statement_sequences.extend(sequences)
        sequences_lengths.extend([len(s) for s in sequences])
        statement_count += sum([len(s) for s in sequences])

    if not sequences_lengths:
        return []
        # logging.error('Input is empty or the size of the input is below the size threshold')
        # sys.exit(0)

    n_sequences = len(sequences_lengths)
    avg_seq_length = sum(sequences_lengths)/float(n_sequences)
    max_seq_length = max(sequences_lengths)

    logging.info('%d sequences' % (n_sequences,))
    logging.info('average sequence length: %f' % (avg_seq_length,))
    logging.info('maximum sequence length: %d' % (max_seq_length,))
    sequences_without_restriction = statement_sequences
    sequences = []
    if not report.parameters.force:
        for sequence in sequences_without_restriction:
            if len(sequence) > 1000:
                first_statement = sequence[0]
                logging.warn('-----------------------------------------'
                             + 'sequences of statements, consists of %d elements is too long.' % (len(sequence),)
                             + 'It starts at %s:%d.' % (first_statement.getSourceFile(
                             ).getFileName(), min(first_statement.getCoveredLineNumbers()))
                             + 'It will be ignored. Use --force to override this restriction.'
                             # TODO: Move this link over to proper orphanblack documentation.
                             + 'Please refer to http://clonedigger.sourceforge.net/documentation.html'
                             + '-----------------------------------------')
            else:
                sequences.append(sequence)

    def calc_statement_sizes():
        for sequence in statement_sequences:
            for statement in sequence:
                statement.storeSize()

    def build_hash_to_statement(dcup_hash=True):
        hash_to_statement = {}
        for statement_sequence in statement_sequences:
            for statement in statement_sequence:
                if dcup_hash:
                    # 3 - CONSTANT HERE!
                    h = statement.getDCupHash(report.parameters.hashing_depth)
                else:
                    h = statement.getFullHash()
                if not h in hash_to_statement:
                    hash_to_statement[h] = [statement]
                else:
                    hash_to_statement[h].append(statement)
        return hash_to_statement

    def build_unifiers(hash_to_statement):
        processed_statements_count = 0
        clusters = []
        ret = {}
        for h in hash_to_statement.keys():
            local_clusters = []
            statements = hash_to_statement[h]
            for statement in statements:
                processed_statements_count += 1
                if ((processed_statements_count % 1000) == 0):
                    logging.info('%d statements processed...' %
                                 (processed_statements_count,))
                bestcluster = None
                mincost = sys.maxint
                for cluster in local_clusters:
                    cost = cluster.getAddCost(statement)
                    if cost < mincost:
                        mincost = cost
                        bestcluster = cluster
                assert(local_clusters == [] or bestcluster)
                if mincost < 0:
                    pdb.set_trace()
                assert(mincost >= 0)
                if bestcluster is None or mincost > report.parameters.clustering_threshold:
                    newcluster = Cluster(statement)
                    local_clusters.append(newcluster)
                else:
                    bestcluster.unify(statement)
            ret[h] = local_clusters
            clusters.extend(local_clusters)
        return ret

    def clusterize(hash_to_statement, clusters_map):
        processed_statements_count = 0
        # clusters_map contain hash values for statements, not unifiers
        # therefore it will work correct even if unifiers are smaller than hashing depth value
        for h in hash_to_statement.keys():
            clusters = clusters_map[h]
            for statement in hash_to_statement[h]:
                processed_statements_count += 1
                if ((processed_statements_count % 1000) == 0):
                    logging.info('%d statements processed...' %
                                 (processed_statements_count,))
                mincost = sys.maxint
                for cluster in clusters:
                    new_u = Unifier(cluster.getUnifierTree(), statement)
#                   assert(new_u.getSubstitutions()[0].getSize() == 0)
                    cost = new_u.getSize()
                    if cost < mincost:
                        mincost = cost
                        statement.setMark(cluster)
                        cluster.addWithoutUnification(statement)

    def filterOutLongEquallyLabeledSequences(statement_sequences):
        # TODO - refactor, combine with the previous warning
        sequences_without_restriction = statement_sequences
        statement_sequences = []
        for sequence in sequences_without_restriction:
            new_sequence = copy.copy(sequence._sequence)
            current_mark = None
            length = 0
            first_statement_index = None
            flag = False
            for i in range(len(sequence)):
                statement = sequence[i]
                if statement.getMark() != current_mark:
                    if flag is True:
                        flag = False
                    current_mark = statement.getMark()
                    length = 0
                    first_statement_index = i
                else:
                    length += 1
                    if length > 10:
                        new_sequence[i] = None
                        if not flag:
                            for i in range(first_statement_index, i):
                                new_sequence[i] = None
                            first_statement = sequence[first_statement_index]
                            logging.warn('-----------------------------------------'
                                         + 'Warning: sequence of statements starting at %s:%d' % (
                                             first_statement.getSourceFile().getFileName(), min(first_statement.getCoveredLineNumbers()))
                                         + 'consists of many similar statements.'
                                         + 'It will be ignored. Use --force to override this restriction.'
                                         + 'Please refer to http://clonedigger.sourceforge.net/documentation.html'
                                         + '-----------------------------------------')
                            flag = True
            new_sequence = new_sequence + [None]
            cur_sequence = StatementSequence(report.parameters)
            for statement in new_sequence:
                if statement is None:
                    if cur_sequence:
                        statement_sequences.append(cur_sequence)
                        cur_sequence = StatementSequence(report.parameters)
                else:
                    cur_sequence.addStatement(statement)
        return statement_sequences

    def mark_using_hash(hash_to_statement):
        for h in hash_to_statement:
            cluster = Cluster()
            for statement in hash_to_statement[h]:
                cluster.addWithoutUnification(statement)
                statement.setMark(cluster)

    def findHugeSequences():
        def f_size(x):
            return x.getMaxCoveredLines()

        def f_elem(x):
            return StatementSequence(report.parameters, x).getCoveredLineNumbersCount()

        def fcode(x):
            return x.getMark()
        f = f_size
        suffix_tree_instance = suffix_tree.SuffixTree(fcode)
        for sequence in statement_sequences:
            suffix_tree_instance.add(sequence)
        return [PairSequences(report.parameters, [StatementSequence(report.parameters, s1), StatementSequence(report.parameters, s2)]) for (s1, s2) in suffix_tree_instance.getBestMaxSubstrings(report.parameters.size_threshold, f, f_elem)]

    def refineDuplicates(pairs_sequences):
        r = []
        flag = False
        while pairs_sequences:
            pair_sequences = pairs_sequences.pop()

            def all_pairsubsequences_size_n_threshold(n):
                lr = []
                for first in range(0, pair_sequences.getLength()-n+1):
                    new_pair_sequences = pair_sequences.subSequence(first, n)
                    size = new_pair_sequences.getMaxCoveredLineNumbersCount()
                    if size >= report.parameters.size_threshold:
                        lr.append((new_pair_sequences, first))
                return lr
            n = pair_sequences.getLength() + 1
            while 1:
                n -= 1
                if n == 0:
                    break
                new_pairs_sequences = all_pairsubsequences_size_n_threshold(n)
                for (candidate_sequence, first) in new_pairs_sequences:
                    distance = candidate_sequence.calcDistance()
                    if (distance < report.parameters.distance_threshold):
                        r.append(candidate_sequence)
                        if first > 0:
                            pairs_sequences.append(
                                pair_sequences.subSequence(0, first-1))
                        if first+n < pair_sequences.getLength():
                            pairs_sequences.append(pair_sequences.subSequence(
                                first+n, pair_sequences.getLength() - first - n))
                        n += 1
                        flag = True
                        break
                if flag:
                    flag = False
                    break
        return r

    def remove_dominated_clones(clones):
        ret_clones = []
#       def f_cmp(a, b):
#           return a.getLevel().__cmp__(b.getLevel())
#       clones.sort(f_cmp)
        statement_to_clone = {}
        for clone in clones:
            for sequence in clone:
                for statement in sequence:
                    if statement not in statement_to_clone:
                        statement_to_clone[statement] = []
                    statement_to_clone[statement].append(clone)
        for clone in clones:
            ancestors_2 = clone[1].getAncestors()
            flag = True
            for s1 in clone[0].getAncestors():
                if s1 in statement_to_clone:
                    for clone2 in statement_to_clone[s1]:
                        if s1 in clone2[0]:
                            seq = clone2[1]
                        else:
                            assert(s1 in clone2[1])
                            seq = clone2[0]
                        for s2 in seq:
                            if s2 in ancestors_2:
                                flag = False
                                break
                        if not flag:
                            break
                if not flag:
                    break
            if flag:
                ret_clones.append(clone)
        return ret_clones

    logging.info('Number of statements: %d' % statement_count)
    logging.info('Calculating size for each statement...')
    calc_statement_sizes()
    logging.info('done calculating sizes')

    logging.info('Building statement hash...')
    if report.parameters.clusterize_using_hash:
        hash_to_statement = build_hash_to_statement(dcup_hash=False)
    else:
        hash_to_statement = build_hash_to_statement(dcup_hash=True)
    logging.info('done building statement hash.')
    logging.info('Number of different hash values: %d' %
                 len(hash_to_statement))

    if report.parameters.clusterize_using_dcup or report.parameters.clusterize_using_hash:
        logging.info('Marking each statement with its hash value')
        mark_using_hash(hash_to_statement)
    else:
        logging.info('Building patterns...')
        clusters_map = build_unifiers(hash_to_statement)
        logging.info(str(Cluster.count) + ' patterns were discovered')
        logging.info('Choosing pattern for each statement...')
        clusterize(hash_to_statement, clusters_map)
        logging.info('done')

    if report.parameters.report_unifiers:
        logging.info('Building reverse hash for reporting ...')
        reverse_hash = {}
        for sequence in statement_sequences:
            for statement in sequence:
                mark = statement.getMark()
                if mark not in reverse_hash:
                    reverse_hash[mark] = []
                reverse_hash[mark].append(statement)
        report.setMarkToStatementHash(reverse_hash)
        logging.info('done')

    logging.info('Finding similar sequences of statements...')

    if not report.parameters.force:
        statement_sequences = filterOutLongEquallyLabeledSequences(
            statement_sequences)

    duplicate_candidates = findHugeSequences()
    logging.info(str(len(duplicate_candidates)) + ' sequences were found')
    logging.info('Refining candidates...')

    if report.parameters.distance_threshold != -1:
        clones = refineDuplicates(duplicate_candidates)
    else:
        clones = duplicate_candidates
    logging.info(str(len(clones)) + ' clones were found')
    if report.parameters.distance_threshold != -1:
        logging.info('Removing dominated clones...')
        old_clone_count = len(clones)
        clones = remove_dominated_clones(clones)
        logging.info(str(old_clone_count - len(clones)) +
                     ' clones were removed')

    covered_source_lines = set()
    for clone in clones:
        for sequence in clone:
            covered_source_lines = covered_source_lines.union(
                sequence.getLineNumberHashables())
    source_lines = set()
    for sequence in statement_sequences:
        source_lines = source_lines.union(sequence.getLineNumberHashables())
    report.all_source_lines_count = len(source_lines)
    report.covered_source_lines_count = len(covered_source_lines)

    return clones
