#Variants Dictionary
variants = {
    "osa": {"c_ins": 1, "c_del": 1, "c_rep": 1, "c_swap": 1},
    "levenshtein": {"c_ins": 1, "c_del": 1, "c_rep": 1, "c_swap": None},
    "indel": {"c_ins": 1, "c_del": 1, "c_rep": 2, "c_swap": None},
}
    
#Desired paths
def select_desired(shares, tau, verbose=True):
        desired = []
        for path, share in shares.items():
             if share >= tau:
                 desired.append(path)
             else:
                if verbose:
                     print("dropped:", path, share)
        return desired



def edit_dtable(a, b, c_ins=1, c_del=1, c_rep=1, c_swap=1):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        d[i][0] = i * c_del
    for j in range(1, len(b) + 1):
        d[0][j] = j * c_ins
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            rep = 0 if a[i - 1] == b[j - 1] else c_rep
            d[i][j] = min(d[i - 1][j] + c_del, d[i][j - 1] + c_ins, d[i - 1][j - 1] + rep)
            if c_swap is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + c_swap)
    return d

def edit_distance(a, b, **costs):
    d = edit_dtable(a, b, **costs)
    return d[len(a)][len(b)]


def edit_identification(a, b, c_ins=1, c_del=1, c_rep=1, c_swap=1):
    d = edit_dtable(a, b, c_ins, c_del, c_rep, c_swap)
    i, j = len(a), len(b)
    operations = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            i -= 1
            j -= 1
        elif (c_swap is not None and i > 1 and j > 1
              and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]
              and d[i][j] == d[i - 2][j - 2] + c_swap):
            operations.append(("swapped", a[i - 2], a[i - 1]))
            i -= 2
            j -= 2
        elif i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + c_rep:
            operations.append(("replaced", a[i - 1], b[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + c_del:
            operations.append(("extra", a[i - 1]))
            i -= 1
        elif j > 0 and d[i][j] == d[i][j - 1] + c_ins:
            operations.append(("missing", b[j - 1]))
            j -= 1
        else:
            break
    return operations[::-1]


#tests
"""
#0
print(edit_dtable(["a","b","c"], ["a","b","c"]))
#1
print(edit_dtable(["a","c"], ["a","b","c"]))
#1
print(edit_dtable(["a","c","b"], ["a","b","c"]))

#missing b
print(edit_identification(["a","c"], ["a","b","c"]))    
#extra x    
print(edit_identification(["a","x","b","c"], ["a","b","c"])) 
#swapped c b
print(edit_identification(["a","c","b"], ["a","b","c"]))   
"""

# Compute edit distances

def compute_edit_distances(paths, desired, **costs):
    distances, closest_paths = [], []
    for path in paths:
        min_distance = float('inf')
        closest = None
        for desired_path in desired:
            distance = edit_distance(path, desired_path, **costs)
            if distance < min_distance:
                min_distance = distance
                closest = desired_path
        distances.append(min_distance)
        closest_paths.append(closest)
    return distances, closest_paths


