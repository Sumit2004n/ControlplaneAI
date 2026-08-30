"""Scenario acceptance check: run every demo scenario through the pipeline and
compare the decision against the scenario's expected decision."""
import asyncio
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./scenario_check.db"
os.environ["DEMO_MODE"] = "true"
sys.path.insert(0, str(Path(__file__).parent))

from app.database.seed import seed_policies
from app.database.session import Base, SessionLocal, engine
from app.services.pipeline import run_analysis
from app.services.scenarios import load_scenarios


async def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_policies(db)
    failures = 0
    for s in load_scenarios():
        history = []
        if s.get("conversation"):
            for turn in s["conversation"][:-1]:
                history.append({"role": "user", "content": turn["prompt"]})
                history.append({"role": "assistant", "content": turn["response"]})
        result = await run_analysis(
            db, application=s["application"], prompt=s["prompt"], response=s["response"],
            history=history, scenario_id=s["id"], persist=False,
        )
        ok = result["decision"] == s["expected_decision"]
        if not ok:
            failures += 1
        mark = "OK  " if ok else "FAIL"
        print(f"{mark} {s['id']:24} expected={s['expected_decision']:13} got={result['decision']:13} "
              f"risk={result['overall_risk']:5}  risks=" +
              ",".join(f"{k[:4]}={v['score']:.0f}" for k, v in result["risks"].items()))
    db.close()
    print(f"\n{failures} mismatches out of {len(load_scenarios())} scenarios")
    sys.exit(1 if failures else 0)


asyncio.run(main())
