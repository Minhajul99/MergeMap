"""Cocitation network and family mixing, shared by 5_rq2.py and 8_baseline.py."""

from collections import Counter
from itertools import combinations

NOT_NAMED = ("unknown", "mixed")


def cocitation(merge_list, parents_of):
    """Weighted cocitation: weight(a, b) = number of merges that cite both.

    Each merge child points to its parents, so two parents are cocited once
    per merge that lists both. This equals the off-diagonal part of A.A^T
    when A is restricted to merge edges (Topic 2).
    """
    weight = Counter()
    for v in merge_list:
        for a, b in combinations(sorted(parents_of[v]), 2):
            weight[(a, b)] += 1
    return weight


def assortativity_and_modularity(pair_weights, label_of):
    """Assortativity coefficient r and modularity Q from a mixing matrix.

    e[i][j] = fraction of edge ends joining label i to label j, a[i] = row sum.
        Q = sum_i (e_ii - a_i^2)                      (Topic 5-3)
        r = Q / (1 - sum_i a_i^2)                     (Newman [5], eq. 7.80)
    So r is Q divided by the largest value Q could take with these labels.
    """
    e = Counter()
    total = 0
    for (a, b), w in pair_weights.items():
        la, lb = label_of[a], label_of[b]
        e[(la, lb)] += w
        e[(lb, la)] += w
        total += 2 * w
    a_share = Counter()
    for (la, _), w in e.items():
        a_share[la] += w / total
    same_share = sum(w for (la, lb), w in e.items() if la == lb) / total
    expected = sum(s * s for s in a_share.values())
    q = same_share - expected
    return q / (1 - expected), q


def mixing_variants(pair_weights, label_of):
    """r and Q four ways: all labels or named families only, weighted or not."""
    known = {pair: w for pair, w in pair_weights.items()
             if label_of[pair[0]] not in NOT_NAMED and label_of[pair[1]] not in NOT_NAMED}
    unit = {pair: 1 for pair in pair_weights}
    unit_known = {pair: 1 for pair in known}
    report = {}
    for key, data in (("all_labels_weighted", pair_weights), ("all_labels_unweighted", unit),
                      ("named_only_weighted", known), ("named_only_unweighted", unit_known)):
        r, q = assortativity_and_modularity(data, label_of)
        report[key] = {"assortativity": r, "modularity_Q": q, "links": len(data)}
    return report
