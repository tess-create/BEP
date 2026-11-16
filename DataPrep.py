#imports
import numpy as np
from pathlib import Path
import pandas as pd
import pm4py
import pysubgroup as ps_orig
from scipy import stats
from severity import collapse_redos, is_subsequence, conformance_severity

#Data
bpic2019 = pm4py.read_xes("Dataset BPIC 2019/Dataset BPIC 2019/BPI_Challenge_2019.xes")
bpic2019 = bpic2019[["case:concept:name"] + [c for c in bpic2019.columns if c != "case:concept:name"]]
invoicing_3way = bpic2019[(bpic2019["case:Item Category"] == "3-way match, invoice before GR") | (bpic2019["case:Item Category"] == "3-way match, invoice after GR")]

invoicing_3way = invoicing_3way.sort_values("time:timestamp")

def resource_type(r):
    if r == "NONE":
        return "NONE"
    elif str(r).startswith("user_"):
        return "user"
    elif str(r).startswith("batch_"):
        return "batch"

invoicing_3way["_res_type"] = invoicing_3way["org:resource"].apply(resource_type)

invoicing_3way_grouped = invoicing_3way.groupby("case:concept:name")

res_perc = invoicing_3way_grouped["_res_type"].value_counts(normalize=True).unstack(fill_value=0) * 100
res_perc = res_perc.reindex(columns=["NONE", "user", "batch"], fill_value=0)
res_perc.columns = ["resource_NONE_perc", "resource_user_perc", "resource_batch_perc"]

throughput = invoicing_3way_grouped["time:timestamp"].agg(lambda x: (x.max() - x.min()).total_seconds() / 86400)
throughput.name = "throughput"

path = invoicing_3way_grouped["concept:name"].agg(tuple)
path.name = "path"

first_cols = [
    "case:Item Category", "case:Sub spend area text", "case:Spend area text",
    "case:Purch. Doc. Category name", "case:Vendor", "case:Company", "case:Item",
    "Cumulative net worth (EUR)", "case:Item Type", "case:Document Type", "case:Source",
    "case:Purchasing Document", "case:Spend classification text"
]
firsts = invoicing_3way_grouped[first_cols].first()

invoicing_3way_feat = firsts.join(res_perc).join(throughput).join(path).reset_index()

hp = ('Create Purchase Order Item', 'Vendor creates invoice', 'Record Goods Receipt', 'Record Invoice Receipt', 'Clear Invoice')
hp_set = set(hp)

invoicing_3way_feat["has_hp_act_inc"] = invoicing_3way_feat["path"].apply(lambda p: hp_set.issubset(set(p)))
invoicing_3way_feat["has_hp_act_exc"] = invoicing_3way_feat["path"].apply(lambda p: set(p) == hp_set)
invoicing_3way_feat["hp_order_inc"] = invoicing_3way_feat["path"].apply(lambda p: is_subsequence(hp, p))
invoicing_3way_feat["hp_order_redo_exc"] = invoicing_3way_feat["path"].apply(lambda p: collapse_redos(p) == hp)
invoicing_3way_feat["hp_order_exact"] = invoicing_3way_feat["path"].apply(lambda p: p == hp)

invoicing_3way_feat["CPOI_num"] = invoicing_3way_feat["path"].apply(lambda p: p.count('Create Purchase Order Item'))
invoicing_3way_feat["VCI_num"] = invoicing_3way_feat["path"].apply(lambda p: p.count('Vendor creates invoice'))
invoicing_3way_feat["RGR_num"] = invoicing_3way_feat["path"].apply(lambda p: p.count('Record Goods Receipt'))
invoicing_3way_feat["RIR_num"] = invoicing_3way_feat["path"].apply(lambda p: p.count('Record Invoice Receipt'))
invoicing_3way_feat["CI_num"] = invoicing_3way_feat["path"].apply(lambda p: p.count('Clear Invoice'))

majority = invoicing_3way_feat[["resource_NONE_perc", "resource_user_perc", "resource_batch_perc"]].idxmax(axis=1).map({
    "resource_NONE_perc": "NONE",
    "resource_user_perc": "user",
    "resource_batch_perc": "batch"
})
invoicing_3way_feat.insert(invoicing_3way_feat.columns.get_loc("resource_batch_perc") + 1, "resource_majority", majority)

invoicing_3way_feat_filtered = invoicing_3way_feat[(invoicing_3way_feat["CI_num"]>0) & ((invoicing_3way_feat["RGR_num"]>0) | (invoicing_3way_feat["RIR_num"]>0))].copy()
invoicing_3way_feat_filtered["conformance_severity"] = invoicing_3way_feat_filtered.apply(conformance_severity, axis=1)

invoicing_3way_feat_filtered.to_pickle("invoicing_3way_feat_filtered.pkl")

#Checks
print(len(invoicing_3way_feat_filtered), "cases")
print(invoicing_3way_feat_filtered["path"].value_counts(normalize=True).head())
print(invoicing_3way_feat_filtered["conformance_severity"].value_counts(normalize=True).sort_index())

