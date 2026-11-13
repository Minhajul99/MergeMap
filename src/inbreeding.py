"""Inbreeding search: how closely related are the parents of a merge?

Definition (fixed before any result was computed)
    For a model X, its "closed neighbourhood within d generations" is X itself
    plus every ancestor reachable in at most d steps along child -> parent edges.

    Two parents A and B of a merge are RELATED WITHIN d if their closed
    neighbourhoods within d generations share at least one model.

        d = 1   A is a parent of B (or B of A), or they share a parent (siblings)
        d = 2   grandparent / first-cousin level
        d = 3   great-grandparent / second-cousin level
        any     they share any ancestor at all (equivalently, a common root)

    A related pair is of ANCESTOR type if one parent lies in the other's
    neighbourhood (one is an ancestor of the other); otherwise it is of
    COMMON-ANCESTOR type (siblings, cousins).

    A merge is INBRED WITHIN d if at least one pair of its parents is related
    within d.

The search is a breadth-first search (Topic 5) going up from each parent,
stopped at depth 3. Results for each parent are remembered, because the same
model is often a parent of many merges.
"""

from collections import deque
from itertools import combinations

MAX_DEPTH = 3
ANY = "any"
LEVELS = [1, 2, 3, ANY]


def ancestors_within(v, parents_of, max_depth):
    """BFS upwards from v. Return {model: distance} for v and its ancestors.

    max_depth=None means no limit.
    """
    distance = {v: 0}
    queue = deque([v])
    while queue:
        x = queue.popleft()
        if max_depth is not None and distance[x] == max_depth:
            continue
        for p in parents_of.get(x, ()):
            if p not in distance:
                distance[p] = distance[x] + 1
                queue.append(p)
    return distance


class InbreedingSearch:
    """Answers "how closely are A and B related?" for many merges on one graph."""

    def __init__(self, parents_of):
        self.parents_of = parents_of
        self._near = {}     # model -> {ancestor: distance}, up to MAX_DEPTH
        self._all = {}      # model -> set of all ancestors (including itself)

    def near(self, v):
        if v not in self._near:
            self._near[v] = ancestors_within(v, self.parents_of, MAX_DEPTH)
        return self._near[v]

    def all_ancestors(self, v):
        if v not in self._all:
            self._all[v] = set(ancestors_within(v, self.parents_of, None))
        return self._all[v]

    def pair(self, a, b):
        """Return (closeness, is_ancestor_type) for two different models.

        closeness is 1, 2, 3, "any" or None (not related at all).
        """
        near_a, near_b = self.near(a), self.near(b)
        # Smallest d such that some model is within d of both a and b.
        best = None
        for x in near_a.keys() & near_b.keys():
            d = max(near_a[x], near_b[x])
            if best is None or d < best:
                best = d
        if best is not None:
            ancestor_type = (a in near_b and near_b[a] <= best) or (b in near_a and near_a[b] <= best)
            return best, ancestor_type
        # Not related within MAX_DEPTH: look at all ancestors.
        all_a, all_b = self.all_ancestors(a), self.all_ancestors(b)
        if a in all_b or b in all_a:
            return ANY, True
        if all_a & all_b:
            return ANY, False
        return None, False

    def merge(self, parents):
        """Closest relation among all pairs of parents of one merge.

        Returns (closeness, is_ancestor_type). Ancestor type wins a tie.
        """
        rank = {1: 0, 2: 1, 3: 2, ANY: 3}
        best = (None, False)
        for a, b in combinations(parents, 2):
            closeness, ancestor_type = self.pair(a, b)
            if closeness is None:
                continue
            key = (rank[closeness], not ancestor_type)
            if best[0] is None or key < (rank[best[0]], not best[1]):
                best = (closeness, ancestor_type)
        return best


def inbreeding_rates(merge_parent_lists, parents_of):
    """Cumulative inbreeding rates over a list of merges.

    Returns {level: {"ancestor": share, "common_ancestor": share, "total": share}}
    where level is 1, 2, 3 or "any" and each share is cumulative: a merge that
    is inbred within 1 is also counted within 2, within 3 and at "any".
    """
    search = InbreedingSearch(parents_of)
    exact = {level: {"ancestor": 0, "common_ancestor": 0} for level in LEVELS}
    for parents in merge_parent_lists:
        closeness, ancestor_type = search.merge(parents)
        if closeness is not None:
            exact[closeness]["ancestor" if ancestor_type else "common_ancestor"] += 1

    total = len(merge_parent_lists)
    rates = {}
    running = {"ancestor": 0, "common_ancestor": 0}
    for level in LEVELS:
        for kind in running:
            running[kind] += exact[level][kind]
        rates[level] = {
            "ancestor": running["ancestor"] / total,
            "common_ancestor": running["common_ancestor"] / total,
            "total": (running["ancestor"] + running["common_ancestor"]) / total,
        }
    return rates
