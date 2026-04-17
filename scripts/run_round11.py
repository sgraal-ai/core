import os, sys, json
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

CORPUS_PATH = "/Users/zsobrakpeter/core/tests/corpus/round11/round11_corpus.json"
RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/round11_results.json"

with open(CORPUS_PATH) as f:
    corpus = json.load(f)

cases = corpus["cases"]
total = len(cases)
print(f"Round 11 corpus: {total} cases")

strict_block = 0
lenient_non_use = 0
tp_strict = 0
fp_strict = 0
fn_strict = 0
tp_lenient = 0
fp_lenient = 0
fn_lenient = 0

results = []
for i, case in enumerate(cases):
    ms = case["memory_state"]
    try:
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": ms[:20],
            "action_type": case.get("action_type", "irreversible"),
            "domain": case.get("domain", "medical"),
            "dry_run": True,
        })
    except Exception as exc:
        results.append({"case_id": case["case_id"], "status": "error", "error": str(exc)})
        fn_strict += 1
        fn_lenient += 1
        continue
    if r.status_code != 200:
        results.append({"case_id": case["case_id"], "status": "error", "http_status": r.status_code})
        fn_strict += 1
        fn_lenient += 1
        continue

    pred = r.json().get("recommended_action", "UNKNOWN")
    omega = r.json().get("omega_mem_final", -1)
    expected = case.get("expected_decision", "BLOCK")

    is_block_pred = pred == "BLOCK"
    is_non_use_pred = pred != "USE_MEMORY"
    is_block_gt = expected in ("BLOCK", "MANIPULATED")

    # Strict: only BLOCK counts
    if is_block_gt and is_block_pred:
        tp_strict += 1
        strict_block += 1
    elif is_block_pred and not is_block_gt:
        fp_strict += 1
    elif is_block_gt and not is_block_pred:
        fn_strict += 1

    # Lenient: any non-USE_MEMORY counts
    if is_block_gt and is_non_use_pred:
        tp_lenient += 1
        lenient_non_use += 1
    elif is_non_use_pred and not is_block_gt:
        fp_lenient += 1
    elif is_block_gt and not is_non_use_pred:
        fn_lenient += 1

    results.append({
        "case_id": case["case_id"],
        "expected": expected,
        "predicted": pred,
        "omega": omega,
        "strict_match": is_block_pred,
        "lenient_match": is_non_use_pred,
    })

    if (i + 1) % 20 == 0:
        print(f"  Processed {i + 1}/{total}...")

# Compute F1
def f1(tp, fp, fn):
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return 2 * precision * recall / max(precision + recall, 1e-9), precision, recall

f1_strict, prec_strict, rec_strict = f1(tp_strict, fp_strict, fn_strict)
f1_lenient, prec_lenient, rec_lenient = f1(tp_lenient, fp_lenient, fn_lenient)

summary = {
    "round": 11,
    "total_cases": total,
    "strict": {
        "block_count": strict_block,
        "tp": tp_strict, "fp": fp_strict, "fn": fn_strict,
        "precision": round(prec_strict, 4),
        "recall": round(rec_strict, 4),
        "f1": round(f1_strict, 4),
    },
    "lenient": {
        "non_use_count": lenient_non_use,
        "tp": tp_lenient, "fp": fp_lenient, "fn": fn_lenient,
        "precision": round(prec_lenient, 4),
        "recall": round(rec_lenient, 4),
        "f1": round(f1_lenient, 4),
    },
    "cases": results,
}

with open(RESULTS_PATH, "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nResults:")
print(f"  Strict (BLOCK only):  {strict_block}/{total} = {strict_block/total*100:.1f}%  F1={f1_strict:.4f}")
print(f"  Lenient (non-USE):    {lenient_non_use}/{total} = {lenient_non_use/total*100:.1f}%  F1={f1_lenient:.4f}")
print(f"\nSaved to {RESULTS_PATH}")
