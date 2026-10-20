# Smart Bin Classifier

Checks whether a warehouse bin photo holds the items and quantities in an order.
Built for the Brainwave Nextgen Technologies *Applied AI Engineer Intern* live-project assignment.

**Live app:** https://smart-bin-classifier-charan.streamlit.app

---

## What it does

A user builds an order (catalogue products and a quantity for each). The app shows a bin photo, and a
fine-tuned ResNet-18 looks **only at the photo** and estimates how many units of each of the 10 catalogue products
are in the bin. The rule from the brief is then applied:

- an **item PASSES** if the bin holds at least the ordered quantity;
- the **order PASSES** only if every item passes; otherwise it **FAILS**, with the reason per item
  (*item not found* or *fewer units found than ordered*);
- items in the bin that are not in the order are ignored.

## Results (untouched test set: 200 bins, 400 orders)

| | Majority baseline | Frozen features + logistic regression | **Fine-tuned ResNet-18 (chosen)** |
|---|---|---|---|
| Presence F1 (macro, 10 products) | 0.00 | 0.60 | **0.79** |
| Presence precision / recall | 0.00 / 0.00 | 0.58 / 0.63 | **0.84 / 0.77** |
| Count exact-match (product present) | 0.00 | 0.48 | **0.65** |
| MAE (product present) | 1.27 | 0.62 | **0.42** |
| Order PASS/FAIL accuracy | 0.50 | 0.75 | **0.83** |
| Bad orders caught (FAIL recall) | 1.00 | 0.96 | **0.965** |
| Bad orders that would ship (of 200) | 0 | 8 | **7** |
| Good orders sent for re-check (of 200) | 200 | 93 | **61** |

**Metric that matters most:** the share of bad orders caught (FAIL recall). A wrong PASS ships a wrong parcel
(refund, return, unhappy customer); a wrong FAIL only costs a worker a few seconds to re-check the bin. It must be
read together with the wrong-FAIL count: the majority baseline "catches" every bad order only by failing every order.

Validation presence F1 was 0.84; the test score (0.79) is lower because thresholds and the best epoch were chosen
on validation. Labels are noisy (items sometimes sit in the wrong bin) and photos have tape, blur and hidden items,
so there is a ceiling on accuracy. Five-plus wrong predictions are explained in `notebooks/03_evaluate.ipynb`.

## Run it locally

Requires Python 3.13 and the data pack.

```bash
git clone <this repository>
cd smart-bin-classifier
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Put the data pack in `data/` (it is not in the repository):
- either unzip `data_pack.zip` into `data/`, or
- rebuild it: run `data_prep/prepare_data.py` in a Kaggle notebook with the dataset below attached, then download
  `/kaggle/working/data_pack.zip`. The selection is deterministic (seed 42).

Then:

```bash
streamlit run app/app.py
```

The trained model is in the repository: `models/smartbin_resnet18.pt` (22 MB, weights stored as 16-bit floats).

## Project structure

| Path | What it is |
|---|---|
| `data_prep/prepare_data.py` | Builds the 2,000-bin pack: cleaning, catalogue, stratified split, leakage checks (run on Kaggle) |
| `notebooks/01_eda.ipynb` | M1 – data exploration, split description, leakage and near-duplicate checks |
| `notebooks/02_train.ipynb` | M2 – three approaches trained and compared on validation (run on Kaggle GPU) |
| `notebooks/03_evaluate.ipynb` | M3 – one-time evaluation on the test set, test orders, failure analysis |
| `app/smartbin.py` | The model loader and the PASS/FAIL rule, shared by the app and the evaluation |
| `app/app.py` | Streamlit app (M4) with request logging (M5) |
| `models/` | Saved models and training history |
| `results/` | Test metrics, test orders, wrong predictions, charts |
| `logs/validation_log.csv` | Log of real validation requests from the app |
| `assumptions.md`, `ai_usage_log.md` | Assumptions and a dated record of AI tool use |

## Data and splits

- **Source:** 536,434 records in `metadata.db` (one SQLite table: file name + JSON metadata).
- **Cleaning** (`prepare_data.py`): dropped 184,168 bins outside 1–5 units, an extra set of 1,200 records
  (`1.jpg`–`1200.jpg`, the only rows with `image_fname`, artificially balanced 200 per quantity 0–4),
  109 bins whose per-product quantities do not add up to `EXPECTED_QUANTITY`, and 48 malformed product entries →
  **350,909 clean bins**. Photo files are matched to records by file name; photos are checked to open and are
  fingerprinted (MD5) to drop exact duplicates.
- **Catalogue:** the 10 most frequent products (by number of clean bins containing them). 2,000 bins were selected
  so each product appears in about 200 bins (198–203), well above the 100-bin minimum. Only one clean bin in the whole
  dataset holds two catalogue products (276483); it is placed in train so the app can show a multi-item PASS.
  `catalogue.csv` holds ASIN, name, size, weight and bin counts per split; the script checks the counts against
  the label files.
- **Split:** 70% train / 10% validation / 10% test / 10% blind, seed 42, stratified by each bin's main catalogue
  product. Checks: every bin in exactly one split, no exact duplicate photo, and no near-duplicate photo across
  splits (difference-hash; the closest cross-split pair differs in 35 of 256 bits).
- **Test set** was used only once, in `03_evaluate.ipynb`. **Blind set** is photos only; its metadata is never used.

## Model

ResNet-18 pretrained on ImageNet, fine-tuned end to end with a 10 × 6 output (counts 0–5 per product).
Cross-entropy with class weights (1/√frequency, because 90% of answers are 0), AdamW (backbone 1e-4, head 1e-3),
cosine schedule, light augmentation, best epoch kept by validation F1 (early stopping, patience 6).
Decision rule: a product is present if P(count ≥ 1) is above a per-product threshold tuned on validation;
the count is then the most likely value 1–5. Training takes about 3 minutes on a free Kaggle T4 GPU.

## App and logging

- Order builder (catalogue products only, quantity 1–5); the app picks a matching train/validation bin from the
  metadata (the **only** use of metadata), or the closest bin when no bin holds the whole order; the user can
  choose any other bin.
- **Validate reads only the photo and the order** (`smartbin.validate`), in every mode.
- Blind mode: type a bin id from the blind folder (leading zeros optional).
- Bad input (no product, unknown bin id, non-numeric id) shows a message, not a crash.
- Every validation is appended to `logs/validation_log.csv` (UTC time, mode, bin id, photo, order, model output,
  result, failed items, seconds). **On Streamlit Community Cloud this file is wiped when the app restarts**;
  the app has a *Download the full log* button.
- On the cloud host the photos are not in the repository: the app downloads a zip of the train, validation and
  blind photos (no test set) once at startup from a link stored in Streamlit *Secrets* (`APP_DATA_URL`).
  No passwords, keys or data are in the code.

## Questions asked and assumptions

Questions emailed to Brainwave on 20 Oct 2026:
1. Only one of 350,909 qualifying bins holds two catalogue products, so most multi-item orders have no matching bin.
   Is showing the closest bin (which then correctly FAILs) with a note, and letting the user pick another, acceptable?
2. The 1–5 units rule is listed under "Splits and the blind set". Does it apply to all 2,000 bins?
3. I chose 10 products at about 200 bins each rather than 20 at about 100. Was a catalogue size expected?

Replies: *none received yet (update before submitting).*

Assumptions are listed in [`assumptions.md`](assumptions.md).

## How I used AI tools

I used Claude (free tier) as a pair programmer: to plan the timeline, explain unfamiliar tools (Git, Kaggle,
Streamlit), draft code, and review my ideas. I ran every step myself, checked outputs, and made the design
decisions (for example keeping multi-product bins for multi-item orders). Code was tested before use: the data
script on a stand-in dataset, the notebooks end to end, and the app by scripted clicks.

Cases where the AI was wrong and how they were caught:
- It assumed bins 1–9999 appeared twice (`1.jpg` and `00001.jpg`). Testing the claim in code raised
  `KeyError: '5000.jpg'`, which showed that `1.jpg`–`1200.jpg` are a separate set; those records were excluded.
- The deployed app showed 0 bins: the data zip made on Windows stored paths with backslashes, which Linux treats as
  file names. Found from the cloud error trace and fixed in the unzip code.

The full dated record is in [`ai_usage_log.md`](ai_usage_log.md).

## Dataset citation

Amazon Bin Image Dataset (Amazon, Registry of Open Data on AWS, https://registry.opendata.aws/amazon-bin-imagery/),
224×224 version on Kaggle: *Amazon Bin Image Dataset (536,434 images, 224x224)* by williamhyun,
https://www.kaggle.com/datasets/williamhyun/amazon-bin-image-dataset-536434-images-224x224.
Licensed CC BY-NC-SA 3.0 US (non-commercial). Used only for this assignment.
