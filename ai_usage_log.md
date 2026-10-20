# AI usage log

| Date | Tool | What I used it for | How I checked it |
|---|---|---|---|
| 19 Oct | Claude (free) | Planned the timeline; set up Python, Git, VS Code and the project folder | Ran each command and checked the output |
| 19 Oct | Claude (free) | Git branch was "master" instead of "main"; renamed it with `git branch -m main` | Checked with `git log --oneline` |
| 19 Oct | Claude (free) | **AI was wrong:** Claude assumed bins 1–9999 appeared twice (`1.jpg` and `00001.jpg`). Running the check gave `KeyError: '5000.jpg'`, showing the guess was wrong: `1.jpg`–`1200.jpg` are a separate 1,200-image set | Tested the claim in code instead of trusting it; decided to exclude the 1,200 extra rows |
| 19 Oct | Claude (free) | Wrote `prepare_data.py` from the cleaning rules we agreed | Claude tested it on a stand-in dataset; I ran it on the real data and all built-in checks passed |
| 19 Oct | Claude (free) | My idea: keep multi-product bins for multi-item orders; Claude updated the script to put all of them in train | The rerun showed only 1 such bin (276483) exists; the split stayed 70/10/10/10 |
| 20 Oct | Claude (free) | Drafted clarifying questions from my data findings | I cut and edited them before sending |
| 20 Oct | Claude (free) | Wrote the EDA notebook (charts, leakage and near-duplicate checks) | Ran it top to bottom; all checks passed; read each finding against the charts |
| 20 Oct | Claude (free) | Wrote the training notebook (3 approaches) | Claude tested it end to end; the test caught a model-saving bug that was fixed; I ran it on Kaggle's GPU |
| 20 Oct | Claude (free) | Wrote the evaluation notebook and the shared PASS/FAIL rule (`smartbin.py`) | The rule was checked against the worked example in the brief; I ran the evaluation once on the test set |
| 20 Oct | Claude (free) | Wrote the Streamlit app with logging | Clicked through PASS, FAIL, bad input and blind mode locally |
| 20 Oct | Claude (free) | **AI was wrong:** the deployed app showed 0 bins. The data zip made on Windows stored paths with backslashes, which Linux treats as file names; Claude fixed the unzip and the empty-index crash | Read the cloud error trace; reproduced it with a Windows-style zip in a test; checked the live app shows 1,600 bins |
| 20 Oct | Claude (free) | Drafted the README and the failure-case explanations | Compared each explanation with the photos; checked every number against `results/test_metrics.json` |
