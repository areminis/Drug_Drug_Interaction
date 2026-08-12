import json
from agents.pipeline import PIPELINE

def judge(ans: str, gold: str) -> int:
    a = ans.lower()
    tokens = [t.strip() for t in gold.lower().split(";")]
    if "no evidence" in tokens:
        return int("no evidence" in a)
    return int(all(tok in a for tok in tokens))

correct = 0
total = 0

with open("eval/questions.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        total += 1
        obj = json.loads(line)
        output = PIPELINE.answer(obj["q"])
        correct += judge(output, obj["gold"])
        print(f"Q: {obj['q']}")
        print(f"A: {output}")
        print("---")

print({"accuracy": correct / max(1, total)})
