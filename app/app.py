"""
Smart Bin Classifier - Streamlit app (M4 + M5).

Run from the project root:   streamlit run app/app.py

Where metadata is used: ONLY to choose a bin photo that matches the order (train/validation bins).
Validate reads only the photo and the order (see smartbin.validate) - in every mode.
Every Validate click is logged to logs/validation_log.csv.
"""
import csv
import json
import os
import random
import time
import zipfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from smartbin import BinModel, validate, MAX_UNITS

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("SBC_DATA_DIR", ROOT / "data"))
MODEL_PATH = ROOT / "models" / "smartbin_resnet18.pt"
LOG_PATH = ROOT / "logs" / "validation_log.csv"
LOG_FIELDS = ["timestamp_utc", "mode", "split", "bin_id", "photo", "order", "model_output",
              "result", "failed_items", "seconds"]

st.set_page_config(page_title="Smart Bin Classifier", page_icon="📦", layout="wide")


# ------------------------------------------------------------------ data and model (loaded once)
def secret(name):
    """Read a setting from the environment or Streamlit secrets; None if not set."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets[name]
    except Exception:
        return None


@st.cache_resource(show_spinner="Getting the app's bin photos…")
def ensure_data():
    """On the cloud host the data pack is not in the repo: download it once from APP_DATA_URL."""
    if (DATA / "catalogue.csv").exists():
        return True
    url = secret("APP_DATA_URL")
    if not url:
        return False
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = DATA / "_download.zip"
    urllib.request.urlretrieve(url, tmp)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(DATA)
    tmp.unlink()
    return (DATA / "catalogue.csv").exists()


@st.cache_resource(show_spinner="Loading the model…")
def load_model():
    return BinModel(MODEL_PATH)


@st.cache_data
def load_catalogue():
    cat = pd.read_csv(DATA / "catalogue.csv", dtype={"asin": str})
    return dict(zip(cat["asin"], cat["name"]))


@st.cache_data
def load_bin_index(catalogue_asins):
    """
    From the train/validation METADATA files: which catalogue products, and how many, each bin holds.
    This is the only place metadata is read, and it is used only to choose a photo for an order.
    """
    index = {}
    for split in ["train", "validation"]:
        for f in sorted((DATA / split / "metadata").glob("*.json")):
            items = json.loads(f.read_text()).get("BIN_FCSKU_DATA") or {}
            index[f.stem] = {"split": split,
                             "items": {a: int(v.get("quantity", 0)) for a, v in items.items() if a in catalogue_asins}}
    return index


def short(name, n=60):
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


# ------------------------------------------------------------------ choosing a bin for an order
def matching_bins(order, index):
    """
    Bins that hold every ordered item in at least the ordered quantity (these should PASS).
    If none exists, the closest bins: those satisfying the most ordered items. Returns (bin ids, exact?).
    """
    def satisfied(b):
        return sum(index[b]["items"].get(a, 0) >= q for a, q in order.items())

    full = [b for b in index if satisfied(b) == len(order)]
    if full:
        return sorted(full), True
    best = max(satisfied(b) for b in index)
    return sorted(b for b in index if satisfied(b) == best and best > 0), False


def photo_path(split, bin_id):
    return DATA / split / "images" / f"{bin_id}.jpg"


def find_blind_photo(text):
    """Accept '523', '00523' or '00523.jpg'. Returns (bin_id, path) or raises ValueError."""
    raw = text.strip().removesuffix(".jpg")
    if not raw:
        raise ValueError("Type a bin id from the blind folder, for example the number of a photo there.")
    if not raw.isdigit():
        raise ValueError(f"'{text.strip()}' is not a bin id: use digits only, e.g. 01234.")
    for candidate in [raw, raw.zfill(5)]:
        p = DATA / "blind" / "images" / f"{candidate}.jpg"
        if p.exists():
            return candidate, p
    raise ValueError(f"Bin {raw} is not in the blind folder.")


# ------------------------------------------------------------------ logging (M5)
def log_request(mode, split, bin_id, order, found, result, seconds):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": mode, "split": split, "bin_id": bin_id, "photo": f"{bin_id}.jpg",
            "order": json.dumps(order), "model_output": json.dumps(found),
            "result": result["result"],
            "failed_items": json.dumps([i["asin"] for i in result["items"] if i["result"] == "FAIL"]),
            "seconds": f"{seconds:.3f}",
        })


# ------------------------------------------------------------------ page
st.title("📦 Smart Bin Classifier")
st.caption("Build an order, pick a bin photo, and check whether the bin holds the order. "
           "The model looks only at the photo.")

if not ensure_data():
    st.error("The data pack was not found. Unzip data_pack.zip into the project's data/ folder "
             "(or set APP_DATA_URL on the cloud host).")
    st.stop()
if not MODEL_PATH.exists():
    st.error(f"Model file not found: {MODEL_PATH.relative_to(ROOT)}. Download it from the Kaggle training run.")
    st.stop()

model = load_model()
NAMES = load_catalogue()
INDEX = load_bin_index(tuple(model.catalogue))

mode = st.sidebar.radio("Mode", ["Order + matching bin", "Blind mode"],
                        help="Blind mode: type a bin id from the blind folder; there is no metadata for these bins.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Catalogue:** {len(model.catalogue)} products  \n"
                    f"**Bins the app can show:** {len(INDEX)} (train + validation)  \n"
                    f"**Blind bins:** {len(list((DATA / 'blind' / 'images').glob('*.jpg')))}")

# 1. Build the order --------------------------------------------------
st.subheader("1. Build the order")
chosen = st.multiselect("Catalogue products", options=model.catalogue,
                        format_func=lambda a: short(NAMES.get(a, a)),
                        placeholder="Choose one or more products")
order = {}
if chosen:
    cols = st.columns(min(len(chosen), 3))
    for i, asin in enumerate(chosen):
        order[asin] = int(cols[i % len(cols)].number_input(
            short(NAMES[asin], 45), min_value=1, max_value=MAX_UNITS, value=1, step=1, key=f"q_{asin}"))

# 2. The bin photo ----------------------------------------------------
st.subheader("2. Bin photo")
image, bin_id, split = None, None, None

if mode == "Order + matching bin":
    if not order:
        st.info("Choose at least one product to see a matching bin.")
    else:
        bins, exact = matching_bins(order, INDEX)
        how = st.radio("Which bin?", ["Matching bin chosen by the app", "Choose a different bin"], horizontal=True)
        if how == "Matching bin chosen by the app":
            if not bins:
                st.warning("No bin holds any of these products.")
            else:
                key = "match_" + json.dumps(order, sort_keys=True)
                if st.button("Show another matching bin") or key not in st.session_state:
                    st.session_state[key] = random.choice(bins)
                bin_id = st.session_state[key]
                if not exact:
                    st.warning("No bin holds the whole order (in this data almost no bin holds two catalogue "
                               "products). Showing the closest bin, so this order is expected to FAIL.")
                else:
                    st.caption(f"{len(bins)} bins hold this order; one is shown.")
        else:
            all_bins = sorted(INDEX)
            bin_id = st.selectbox("Bin id (train or validation)", all_bins, index=0)
        if bin_id:
            split = INDEX[bin_id]["split"]
            image = Image.open(photo_path(split, bin_id))
else:
    typed = st.text_input("Blind bin id", placeholder="e.g. 01234")
    if typed:
        try:
            bin_id, path = find_blind_photo(typed)
            split = "blind"
            image = Image.open(path)
        except ValueError as e:
            st.error(str(e))

if image is not None:
    left, right = st.columns([1, 2])
    left.image(image, caption=f"Bin {bin_id} ({split})", width=320)
    if split != "blind":
        with right.expander("What the warehouse records say (metadata, NOT used by Validate)"):
            recorded = INDEX[bin_id]["items"]
            st.write({short(NAMES[a], 45): q for a, q in recorded.items()} or "no catalogue products")

# 3. Validate ---------------------------------------------------------
st.subheader("3. Validate")
if st.button("Validate", type="primary"):
    try:
        start = time.perf_counter()
        result, found = validate(image, order, model)          # photo + order only
        seconds = time.perf_counter() - start
    except ValueError as e:
        st.error(str(e))
    else:
        log_request(mode, split, bin_id, order, found, result, seconds)
        rows = [{"Item": short(NAMES[i["asin"]], 55), "Ordered": i["ordered"], "Found": i["found"],
                 "Result": ("✅ PASS" if i["result"] == "PASS" else f"❌ FAIL: {i['reason']}")}
                for i in result["items"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if result["result"] == "PASS":
            st.success(f"**Order PASS** – {result['reason']}.")
        else:
            st.error(f"**Order FAIL** – {result['reason']}.")
        st.caption(f"Checked in {seconds:.2f} s. Logged.")
        with st.expander("Model output for every catalogue product"):
            st.write({short(NAMES[a], 45): q for a, q in found.items()})

# Log -----------------------------------------------------------------
st.markdown("---")
with st.expander("Validation log"):
    if LOG_PATH.exists():
        log = pd.read_csv(LOG_PATH, dtype=str)
        st.dataframe(log.tail(10).iloc[::-1], hide_index=True, width="stretch")
        st.download_button("Download the full log (CSV)", LOG_PATH.read_bytes(),
                           file_name="validation_log.csv", mime="text/csv")
        st.caption("On the free cloud host this file is wiped when the app restarts; download it to keep it.")
    else:
        st.write("No validations yet.")
