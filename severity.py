
def is_subsequence(sub, path):
    it = iter(path)
    return all(a in it for a in sub)

def collapse_redos(path):
    out = ()
    for a in path:
        if not out or out[-1] != a:
            out += (a,)
    return out

def conformance_severity(row):
    if row["hp_order_exact"]:
        return 0
    if row["hp_order_redo_exc"]:
        return 1
    if row["has_hp_act_exc"] and row["hp_order_inc"]:
        return 2
    if row["hp_order_inc"]:
        return 3
    if row["has_hp_act_exc"]:
        return 4
    return 5