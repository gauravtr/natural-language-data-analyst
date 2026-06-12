"""
eval.py — Evaluation framework for the BI Copilot.
Run with: python eval.py
"""
import json, time
from bi_copilot import BICopilot

EVAL_SET = [
    {"id":"Q01","question":"How many orders are in the database?",
     "check": lambda df: len(df)==1 and df.iloc[0,0]>0},
    {"id":"Q02","question":"How many unique customers have placed at least one order?",
     "check": lambda df: len(df)==1 and df.iloc[0,0]>0},
    {"id":"Q03","question":"Which product category has the most products?",
     "check": lambda df: len(df)>=1 and len(df.columns)>=2},
    {"id":"Q04","question":"What is the average freight cost per order?",
     "check": lambda df: len(df)==1 and df.iloc[0,0]>0},
    {"id":"Q05","question":"List the top 3 countries by number of customers",
     "check": lambda df: len(df)==3},
    {"id":"Q06","question":"Which employee handled the most orders?",
     "check": lambda df: len(df)>=1 and len(df.columns)>=2},
    {"id":"Q07","question":"How many products have zero units in stock?",
     "check": lambda df: len(df)==1 and df.iloc[0,0]>=0},
    {"id":"Q08","question":"What is the total revenue by product category?",
     "check": lambda df: len(df)>=1 and len(df.columns)>=2},
    {"id":"Q09","question":"Show the number of orders placed each month in 2023",
     "check": lambda df: len(df)>=1},
    {"id":"Q10","question":"Which 5 customers placed the most orders?",
     "check": lambda df: len(df)==5},
    {"id":"Q11","question":"What is the most expensive product?",
     "check": lambda df: len(df)>=1 and len(df.columns)>=2},
    {"id":"Q12","question":"How many orders were shipped to Germany?",
     "check": lambda df: len(df)==1 and df.iloc[0,0]>=0},
    {"id":"Q13","question":"What percentage of orders have a discount applied?",
     "check": lambda df: len(df)==1},
    {"id":"Q14","question":"Which product has been ordered the most times?",
     "check": lambda df: len(df)>=1},
    {"id":"Q15","question":"Show total orders per employee with their full name",
     "check": lambda df: len(df)>=1 and len(df.columns)>=2},
]

def run_eval():
    copilot = BICopilot()
    results = []
    print(f"\nRunning evaluation on {len(EVAL_SET)} questions...\n")
    print(f"{'ID':<6} {'Status':<12} {'Att':<5} {'Question'}")
    print("-" * 65)

    for item in EVAL_SET:
        start = time.time()
        try:
            result = copilot.query(item["question"])
            elapsed = time.time() - start
            if result["type"] == "error":
                status, correct, att = "EXEC_FAIL", False, "-"
            elif result["type"] == "clarification":
                status, correct, att = "CLARIFY", False, "-"
            else:
                att = result["attempts"]
                try:
                    correct = bool(item["check"](result["dataframe"]))
                    status = "PASS" if correct else "WRONG"
                except Exception:
                    correct, status = False, "CHECK_ERR"
        except Exception as e:
            elapsed = time.time() - start
            status, correct, att = "EXCEPTION", False, "-"

        results.append({"id":item["id"],"question":item["question"],
                         "status":status,"correct":correct,
                         "attempts":att,"elapsed":round(elapsed,1)})
        print(f"{item['id']:<6} {status:<12} {str(att):<5} {item['question'][:50]}")

    total = len(results)
    executed = sum(1 for r in results if r["status"] not in {"EXEC_FAIL","EXCEPTION"})
    correct  = sum(1 for r in results if r["correct"])
    print("\n" + "="*65)
    print(f"Execution accuracy : {executed}/{total} = {executed/total*100:.1f}%")
    print(f"Result accuracy    : {correct}/{total} = {correct/total*100:.1f}%")
    print(f"Avg latency        : {sum(r['elapsed'] for r in results)/total:.1f}s")
    print("="*65)
    with open("eval_results.json","w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to eval_results.json")

if __name__ == "__main__":
    run_eval()
