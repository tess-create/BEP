import pandas as pd
from scoring import edit_identification, compute_edit_distances, select_desired, variants
#data loader
invoicing_3way_feat = pd.read_pickle("invoicing_3way_feat_filtered.pkl")

#Desired paths
shares = invoicing_3way_feat["path"].value_counts(normalize=True)

#Deciding which tau to use for desired paths
for tau in [0.1, 0.05, 0.01, 0.005]:
    selected = select_desired(shares, tau, verbose=False)
    print(tau, len(selected), round(shares[selected].sum(), 3))

selected = select_desired(shares, 0.01, verbose=False)
for p in selected:
    print(round(shares[p], 4), p)
print("NEXT")
selected = select_desired(shares, 0.05, verbose=False)
for p in selected:
    print(round(shares[p], 4), p)