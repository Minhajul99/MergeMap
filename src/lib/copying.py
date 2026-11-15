"""Vertex copying in merges (Topic 5-5): does a new merge reuse the parent list
of an earlier merge?

For every merge, in order of creation, find the earlier merge whose parent set
overlaps most with its own, measured by the Jaccard similarity
    J(A, B) = |A and B| / |A or B|.
Only earlier merges that share at least two parents count, because sharing one
popular base model is not copying a recipe. A merge "copies" if its best
J is at least 0.5, and "repeats" a recipe if J = 1 (the same parent set).

Merges created at exactly the same time are not compared with each other.
Used by 5_rq2.py (observed merges) and 8_baseline.py (shuffled merges).
"""

from collections import Counter, defaultdict

COPY_THRESHOLD = 0.5


def best_earlier_match(merges, parents_of, created):
    """Return [(merge, best Jaccard, earlier merge or None)] in creation order."""
    ordered = sorted(merges, key=lambda v: (created[v], v))
    index = defaultdict(list)            # parent -> earlier merges that list it
    result = []
    i = 0
    while i < len(ordered):
        j = i
        while j < len(ordered) and created[ordered[j]] == created[ordered[i]]:
            j += 1
        batch = ordered[i:j]
        for v in batch:
            mine = set(parents_of[v])
            shared = Counter()
            for p in mine:
                for earlier in index[p]:
                    shared[earlier] += 1
            best, best_merge = 0.0, None
            for earlier, s in shared.items():
                if s >= 2:
                    jac = s / (len(mine) + len(set(parents_of[earlier])) - s)
                    if jac > best or (jac == best and best_merge is not None and earlier < best_merge):
                        best, best_merge = jac, earlier
            result.append((v, best, best_merge))
        for v in batch:                  # only now: same-time merges are not "earlier"
            for p in set(parents_of[v]):
                index[p].append(v)
        i = j
    return result


def copying_summary(matches, author=None):
    """Shares of merges that copy, repeat, or share two parents with an earlier merge."""
    total = len(matches)
    copies = [(v, m) for v, j, m in matches if j >= COPY_THRESHOLD]
    summary = {
        "merges": total,
        "share_copying": len(copies) / total,
        "share_exact_repeat": sum(1 for _, j, _ in matches if j == 1.0) / total,
        "share_two_shared_parents": sum(1 for _, j, _ in matches if j > 0) / total,
    }
    if author is not None and copies:
        same = sum(1 for v, m in copies if author[v] == author[m])
        summary["copies_by_same_author"] = same / len(copies)
        summary["share_copying_another_author"] = (len(copies) - same) / total
    return summary
