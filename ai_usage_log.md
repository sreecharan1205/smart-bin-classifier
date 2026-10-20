# AI usage log

| Date | Tool | What I used it for | How I checked it |
|---|---|---|---|
| 19 Oct | Claude (free) | Planned the timeline; set up Python, Git, VS Code and project folder | Ran each command and checked output |
| 19 Oct | Claude (free) | Git branch was "master" instead of "main"; renamed with git branch -m main | Checked with git log --oneline |
| 19 Oct | Claude (free) | Claude assumed bins 1–9999 appeared twice (1.jpg and 00001.jpg). Running the check gave KeyError '5000.jpg', showing the guess was wrong: 1.jpg–1200.jpg are a separate 1,200-image set | Tested the claim in code instead of trusting it; decided to exclude the 1,200 extra rows |
| 19 Oct | Claude (free) | Wrote prepare_data.py from the cleaning rules we agreed | Claude tested it on fake data; I ran it on the real data and all built-in checks passed |
| 19 Oct | Claude (free) | My idea: keep multi-product bins for multi-item orders; Claude updated the script to put all of them in train | Rerun showed only 1 such bin (276483) exists; split stayed 70/10/10/10 | 
20 Oct | Claude | Drafted clarifying questions from my data findings | I cut and edited them before sending
| 20 Oct | Claude (free) | Wrote the training notebook (3 approaches) | Claude tested it end to end; the test caught a model-saving bug that was fixed; I ran it on Kaggle's GPU |