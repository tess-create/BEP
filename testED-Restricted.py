#Data generation
import numpy as np, pandas as pd
rng = np.random.default_rng(0)
import pysubgroup as ps
from severity import collapse_redos, is_subsequence, conformance_severity
from scoring import edit_identification, compute_edit_distances, select_desired, variants


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
desired = select_desired(shares, 0.1)
print("Desired paths:", desired)


logGrouped["score"], logGrouped["closest_path"] = compute_edit_distances(logGrouped["path"], desired)
logGrouped["edits"] = [edit_identification(p, c) for p, c in zip(logGrouped["path"], logGrouped["closest_path"])]
print(logGrouped["score"].value_counts())
#print((logGrouped["edits"].apply(len) == logGrouped["score"]).all())  
print(logGrouped[logGrouped["score"] > 0][["path", "edits"]])

for kind in ["extra", "missing", "replaced", "swapped"]:
    logGrouped["n_" + kind] = logGrouped["edits"].apply(lambda ops: sum(1 for op in ops if op[0] == kind))


for name, setting in variants.items():
    logGrouped["score_" + name], logGrouped["closest_" + name] = compute_edit_distances(
        logGrouped["path"], desired, **setting)
#for col in ["score_osa", "score_levenshtein", "score_indel"]:
    #print(col, logGrouped[col].value_counts().sort_index())

#Adding Alignment Cost column
logGrouped["alignment_cost"], _ = compute_edit_distances(logGrouped["path"], [desired[0]], **variants["indel"])
print(logGrouped["alignment_cost"].value_counts().sort_index())

#severity score from OG paper
hp = desired[0]
hp_set = set(hp)

logGrouped["has_hp_act_inc"] = logGrouped["path"].apply(lambda p: hp_set.issubset(set(p)))
logGrouped["has_hp_act_exc"] = logGrouped["path"].apply(lambda p: set(p) == hp_set)
logGrouped["hp_order_inc"] = logGrouped["path"].apply(lambda p: is_subsequence(hp, p))
logGrouped["hp_order_redo_exc"] = logGrouped["path"].apply(lambda p: collapse_redos(p) == hp)
logGrouped["hp_order_exact"] = logGrouped["path"].apply(lambda p: p == hp)

logGrouped["conformance_severity"] = logGrouped.apply(conformance_severity, axis=1)
print(logGrouped["conformance_severity"].value_counts().sort_index())

#Comparison tables

cols = ["score_osa", "score_levenshtein", "score_indel", "alignment_cost", "conformance_severity"]
print(logGrouped[cols].corr(method="spearman"))
print(pd.crosstab(logGrouped["conformance_severity"], logGrouped["score_osa"]))
print(pd.crosstab(logGrouped["conformance_severity"], logGrouped["alignment_cost"]))


#EMM
data = logGrouped.copy()
ignore = [c for c in data.columns if c not in ("program", "channel")]

searchspace = ps.create_selectors(data, ignore=ignore)
qf = ps.AUCQFNumeric(a=0.5, comparison="complement", direction="less_compliant",
                     min_sg_coverage=0.02, max_sg_coverage=0.8)

score_cols = ["score_osa", "score_levenshtein", "alignment_cost", "conformance_severity"]
results = {}

for col in score_cols:
    target = ps.ConformanceTarget(col)
    task = ps.SubgroupDiscoveryTask(data, target, searchspace,
                                    result_set_size=10, depth=2, qf=qf)
    results[col] = ps.BeamSearch(beam_width_adaptive=True).execute(task).to_dataframe()
    print(col)
    print(results[col][["quality", "subgroup"]])
