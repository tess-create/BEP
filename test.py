#Data generation
import numpy as np, pandas as pd
import pm4py
rng = np.random.default_rng(0)

desired = ["Submit", "Review", "Interview", "Decision", "Enroll"]
rows = []
for i in range(2000):
    program = rng.choice(["CS", "Data Science", "Business"])
    channel = rng.choice(["online", "agent"])
    trace = desired.copy()

    # planted subgroup: Business via agent often skips the review
    p_dev = 0.6 if (program == "Business" and channel == "agent") else 0.1
    if rng.random() < p_dev:
        kind = rng.choice(["missing", "extra", "swap"])
        if kind == "missing":
            trace.remove("Review")
        elif kind == "extra":
            trace.insert(1, "Request documents")
        else:
            trace[1], trace[2] = trace[2], trace[1]

    t = pd.Timestamp("2026-01-01") + pd.Timedelta(days=int(rng.integers(0, 200)))
    for act in trace:
        t += pd.Timedelta(days=int(rng.integers(1, 5)))
        rows.append({"case:concept:name": f"app{i}", "concept:name": act,
                     "time:timestamp": t, "case:program": program,
                     "case:channel": channel})

log = pd.DataFrame(rows)
#print(log["case:concept:name"].nunique(), "cases")

log.to_csv("admissions_log.csv", index=False)

#Table with row per case and column with a path
log = log.sort_values(by=["case:concept:name", "time:timestamp"], kind="stable")
logGrouped = log.groupby("case:concept:name").agg(
    path=("concept:name", tuple),
    program=("case:program", "first"),
    channel=("case:channel", "first")
).reset_index()
#print(logGrouped.head())

#Desired paths
shares = logGrouped["path"].value_counts(normalize=True)
#print(shares)
def select_desired(path, tau):
        desired = []
        for path, share in shares.items():
             if share >= tau:
                 desired.append(path)
             else:
                print("dropped:", path, share)
        return desired
desired = select_desired(shares, 0.1)
print("Desired paths:", desired)

#Edit diastance function
def edit_distance(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]

#tests
"""
#0
print(edit_distance(["a","b","c"], ["a","b","c"]))
#1
print(edit_distance(["a","c"], ["a","b","c"]))
#1
print(edit_distance(["a","c","b"], ["a","b","c"]))
"""
# Compute edit distances

def compute_edit_distances(paths, desired):
    distances = []
    closest_paths = []                     
    for path in paths:
        min_distance = float('inf')
        closest = None
        for desired_path in desired:
            distance = edit_distance(path, desired_path)
            if distance < min_distance:
                min_distance = distance
                closest = desired_path
        distances.append(min_distance)
        closest_paths.append(closest)
    return distances, closest_paths

logGrouped["score"], logGrouped["closest_path"] = compute_edit_distances(logGrouped["path"], desired)
#print(logGrouped["score"].value_counts())