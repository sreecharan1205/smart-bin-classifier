"""
prepare_data.py - Build the 2,000-bin working subset for the Smart Bin Classifier.

Where to run it:
    On Kaggle, in a notebook with the dataset
    "Amazon Bin Image Dataset (536,434 images, 224x224)" attached.

What it produces (in /kaggle/working/):
    data_pack/
        train/       images/ + metadata/ (one JSON per bin) + labels.csv
        validation/  images/ + metadata/ + labels.csv
        test/        images/ + metadata/ + labels.csv
        blind/       images/ only (no labels, as the brief requires)
        catalogue.csv   the catalogue products and their details
        splits.csv      which split each bin belongs to (bin ids only, no labels)
    data_pack.zip   the same folder zipped, ready to download

Every decision below is explained in a comment so it can be defended in the interview.
"""

import os
import json
import random
import shutil
import sqlite3
import hashlib
from collections import Counter

import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split

# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
# Paths can be overridden with environment variables (used for testing on fake data).
BASE = os.environ.get(
    "SBC_DATA",
    "/kaggle/input/datasets/williamhyun/amazon-bin-image-dataset-536434-images-224x224",
)
DB_PATH = os.path.join(BASE, "metadata.db")
IMG_DIR = os.path.join(BASE, "bin-images-224x224", "bin-images-224x224")
OUT_DIR = os.environ.get("SBC_OUT", "/kaggle/working/data_pack")

SEED = 42                 # fixed random seed, so the same subset is produced every run
N_CATALOGUE = 10          # catalogue = the 10 most frequent products
BINS_PER_PRODUCT = int(os.environ.get("SBC_PER_PRODUCT", 200))  # target bins per product
N_BINS = int(os.environ.get("SBC_N_BINS", 2000))                # total bins (brief: 2,000)
MIN_BINS = int(os.environ.get("SBC_MIN_BINS", 100))             # brief: each product in >= 100 bins
MAX_UNITS = 5             # brief: 1 to 5 units per bin
SPLITS = ["train", "validation", "test", "blind"]  # 70% / 10% / 10% / 10%


# ------------------------------------------------------------------
# Step 1: read every record and keep only clean bins
# ------------------------------------------------------------------
def open_db():
    """Open metadata.db read-only (the Kaggle input folder cannot be written to)."""
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)


def load_clean_bins():
    """Apply the cleaning rules. Returns the clean bins and a count of why bins were dropped."""
    con = open_db()
    image_files = set(os.listdir(IMG_DIR))
    stats = Counter()
    clean = []

    for name, meta in con.execute("SELECT name, metadata FROM metadata"):
        stats["total records"] += 1
        m = json.loads(meta)

        # Rule 1: skip the extra 1,200-image set. These are the only records with
        # image_fname filled in, and their quantities are artificially balanced.
        if m.get("image_fname") is not None:
            stats["dropped: extra 1,200-image set"] += 1
            continue

        # Rule 2: the photo must exist.
        if name not in image_files:
            stats["dropped: photo missing"] += 1
            continue

        # Rule 3: total units (EXPECTED_QUANTITY) must be a whole number from 1 to 5.
        total = m.get("EXPECTED_QUANTITY")
        if not isinstance(total, int) or not (1 <= total <= MAX_UNITS):
            stats["dropped: total units not 1-5"] += 1
            continue

        # Rule 4: every product entry must be well-formed
        # (its key equals its asin field, and its quantity is a whole number >= 1).
        items = m.get("BIN_FCSKU_DATA") or {}
        qty = {}
        for key, v in items.items():
            q = v.get("quantity")
            if v.get("asin") != key or not isinstance(q, int) or q < 1:
                qty = None
                break
            qty[key] = q
        if qty is None:
            stats["dropped: badly formed product entry"] += 1
            continue

        # Rule 5: per-product quantities must add up to the total.
        if sum(qty.values()) != total:
            stats["dropped: quantities do not add up"] += 1
            continue

        stats["clean bins"] += 1
        clean.append({"name": name, "bin_id": name[:-4], "total": total, "items": qty})

    con.close()
    return clean, stats


# ------------------------------------------------------------------
# Step 2: choose the catalogue
# ------------------------------------------------------------------
def choose_catalogue(clean):
    """Catalogue = the N most frequent products, counted as number of bins containing them."""
    counts = Counter(asin for b in clean for asin in b["items"])
    return [asin for asin, _ in counts.most_common(N_CATALOGUE)]


# ------------------------------------------------------------------
# Step 3: check candidate photos (readable, not duplicated)
# ------------------------------------------------------------------
def file_md5(path):
    """Fingerprint of a file: two identical files always give the same fingerprint."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def check_photos(candidates, stats):
    """Drop photos that cannot be opened, and exact duplicate photos."""
    seen, good, sizes = set(), [], Counter()
    for b in candidates:
        path = os.path.join(IMG_DIR, b["name"])
        try:
            with Image.open(path) as im:
                im.load()                  # fully decode, so broken files are caught
                sizes[im.size] += 1
        except Exception:
            stats["dropped: photo cannot be opened"] += 1
            continue
        fingerprint = file_md5(path)
        if fingerprint in seen:
            stats["dropped: duplicate photo"] += 1
            continue
        seen.add(fingerprint)
        b["md5"] = fingerprint
        good.append(b)
    return good, sizes


# ------------------------------------------------------------------
# Step 4: select the 2,000 bins
# ------------------------------------------------------------------
def is_multi(bin_record, catalogue):
    """True if the bin holds 2 or more different catalogue products."""
    return len(set(catalogue) & bin_record["items"].keys()) >= 2


def select_bins(good, catalogue):
    """
    1. Take EVERY bin that holds 2+ catalogue products. These are very rare in the data,
       and the app needs them to show a PASS for a multi-item order.
    2. Give each catalogue product up to BINS_PER_PRODUCT bins, so the products are balanced.
       Rarest products are filled first so they get their full share.
    3. Top up with remaining candidates until there are exactly N_BINS bins.
    """
    rng = random.Random(SEED)
    pool = good[:]
    rng.shuffle(pool)

    selected = [b for b in pool if is_multi(b, catalogue)]
    chosen = {b["name"] for b in selected}
    available = {a: sum(a in b["items"] for b in pool) for a in catalogue}
    for asin in sorted(catalogue, key=lambda a: available[a]):
        have = sum(asin in b["items"] for b in selected)  # bins already chosen for other products
        for b in pool:
            if have >= BINS_PER_PRODUCT:
                break
            if asin in b["items"] and b["name"] not in chosen:
                selected.append(b)
                chosen.add(b["name"])
                have += 1

    rest = [b for b in pool if b["name"] not in chosen]
    selected += rest[: max(0, N_BINS - len(selected))]

    if len(selected) < N_BINS:
        raise ValueError(f"Only {len(selected)} suitable bins found, need {N_BINS}.")
    return selected[:N_BINS]


# ------------------------------------------------------------------
# Step 5: split into train / validation / test / blind (70 / 10 / 10 / 10)
# ------------------------------------------------------------------
def main_product(items, catalogue):
    """The catalogue product with the most units in the bin (used to stratify the split)."""
    in_cat = {a: q for a, q in items.items() if a in catalogue}
    return max(sorted(in_cat), key=lambda a: in_cat[a])


def make_splits(selected, catalogue):
    """
    70% train / 10% validation / 10% test / 10% blind.

    - Multi-product bins (2+ catalogue products) all go to TRAIN, so the app (which may only
      show train/validation bins) has real examples of multi-item orders that PASS.
      Trade-off: the test set has no multi-product bins; this is reported in the results.
    - All other bins are split with stratification: each split gets roughly the same mix
      of catalogue products (grouped by the bin's main catalogue product).
    """
    multi_ids = [b["bin_id"] for b in selected if is_multi(b, catalogue)]
    others = [b for b in selected if not is_multi(b, catalogue)]
    ids = [b["bin_id"] for b in others]
    strata = [main_product(b["items"], catalogue) for b in others]

    n_train = round(0.70 * N_BINS) - len(multi_ids)   # train slots left after the multi bins
    n_each = round(0.10 * N_BINS)                      # validation, test and blind sizes

    train, rest, _, rest_strata = train_test_split(
        ids, strata, train_size=n_train, stratify=strata, random_state=SEED)
    val, rest2, _, rest2_strata = train_test_split(
        rest, rest_strata, train_size=n_each, stratify=rest_strata, random_state=SEED)
    test, blind = train_test_split(
        rest2, train_size=n_each, stratify=rest2_strata, random_state=SEED)

    return {"train": train + multi_ids, "validation": val, "test": test, "blind": blind}


# ------------------------------------------------------------------
# Step 6: write the data pack
# ------------------------------------------------------------------
def fetch_metadata(names):
    """Read the original JSON records for the selected bins only."""
    con = open_db()
    out, names = {}, list(names)
    for i in range(0, len(names), 500):          # SQLite limits how many values fit in one query
        chunk = names[i:i + 500]
        query = f"SELECT name, metadata FROM metadata WHERE name IN ({','.join('?' * len(chunk))})"
        for name, meta in con.execute(query, chunk):
            out[name] = json.loads(meta)
    con.close()
    return out


def dimension(entry, field):
    """Return a size/weight value from a product entry, or None if missing."""
    d = entry.get(field) or {}
    return d.get("value")


def write_pack(selected, splits, catalogue):
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    by_id = {b["bin_id"]: b for b in selected}
    raw = fetch_metadata(b["name"] for b in selected)

    for split, ids in splits.items():
        os.makedirs(os.path.join(OUT_DIR, split, "images"))
        if split != "blind":
            os.makedirs(os.path.join(OUT_DIR, split, "metadata"))
        rows = []
        for bin_id in sorted(ids):
            b = by_id[bin_id]
            shutil.copy(os.path.join(IMG_DIR, b["name"]),
                        os.path.join(OUT_DIR, split, "images", b["name"]))
            if split == "blind":
                continue  # blind = photos only: no metadata, no labels
            with open(os.path.join(OUT_DIR, split, "metadata", f"{bin_id}.json"), "w") as f:
                json.dump(raw[b["name"]], f, indent=1)
            row = {"bin_id": bin_id, "image": b["name"], "total_units": b["total"]}
            row.update({asin: b["items"].get(asin, 0) for asin in catalogue})
            rows.append(row)
        if split != "blind":
            pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, split, "labels.csv"), index=False)

    # splits.csv: bin id -> split (no labels)
    pd.DataFrame([{"bin_id": i, "split": s} for s, ids in splits.items() for i in sorted(ids)]) \
        .to_csv(os.path.join(OUT_DIR, "splits.csv"), index=False)

    # catalogue.csv: product id, name, size/weight (from the first bin it appears in), counts
    cat_rows = []
    for asin in catalogue:
        first = next(raw[b["name"]]["BIN_FCSKU_DATA"][asin]
                     for b in selected if asin in b["items"])
        row = {
            "asin": asin,
            "name": first.get("name", ""),
            "height_in": dimension(first, "height"),
            "length_in": dimension(first, "length"),
            "width_in": dimension(first, "width"),
            "weight_lb": dimension(first, "weight"),
            "bins_in_subset": sum(asin in b["items"] for b in selected),
        }
        for split in ["train", "validation", "test"]:
            row[f"bins_{split}"] = sum(asin in by_id[i]["items"] for i in splits[split])
        cat_rows.append(row)
    pd.DataFrame(cat_rows).to_csv(os.path.join(OUT_DIR, "catalogue.csv"), index=False)


# ------------------------------------------------------------------
# Step 7: checks that prove the pack is correct
# ------------------------------------------------------------------
def run_checks(selected, splits, catalogue):
    by_id = {b["bin_id"]: b for b in selected}
    sets = {s: set(ids) for s, ids in splits.items()}

    # No bin in more than one split, and every bin in exactly one split
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            assert not (sets[a] & sets[b]), f"Leak: bins in both {a} and {b}"
    assert sum(len(s) for s in sets.values()) == len(selected) == N_BINS

    # No duplicate photo anywhere in the pack
    assert len({b["md5"] for b in selected}) == N_BINS, "Duplicate photos in the pack"

    # Every selected bin follows the quantity rules
    for b in selected:
        assert 1 <= b["total"] <= MAX_UNITS and sum(b["items"].values()) == b["total"]

    # Every multi-product bin is in train (so the app can show a multi-item PASS)
    for b in selected:
        if is_multi(b, catalogue):
            assert b["bin_id"] in sets["train"], "A multi-product bin is not in train"

    # Catalogue: unique ids, names present, each product in >= MIN_BINS bins
    cat = pd.read_csv(os.path.join(OUT_DIR, "catalogue.csv"), dtype={"asin": str})
    assert cat["asin"].is_unique and len(cat) == N_CATALOGUE
    assert cat["name"].notna().all() and (cat["name"].str.len() > 0).all()
    assert (cat["bins_in_subset"] >= MIN_BINS).all(), "A product is in fewer than MIN_BINS bins"

    # catalogue.csv counts agree with the labels files (recounted independently)
    for split in ["train", "validation", "test"]:
        labels = pd.read_csv(os.path.join(OUT_DIR, split, "labels.csv"), dtype={"bin_id": str})
        assert len(labels) == len(sets[split])
        for _, row in cat.iterrows():
            assert (labels[row["asin"]] > 0).sum() == row[f"bins_{split}"]

    # Every photo was copied, and blind has photos only
    for split, ids in sets.items():
        files = os.listdir(os.path.join(OUT_DIR, split, "images"))
        assert len(files) == len(ids)
    assert sorted(os.listdir(os.path.join(OUT_DIR, "blind"))) == ["images"]

    print("All checks passed: no leakage, no duplicates, rules met, catalogue verified.")


# ------------------------------------------------------------------
# Run everything
# ------------------------------------------------------------------
if __name__ == "__main__":
    clean, stats = load_clean_bins()
    catalogue = choose_catalogue(clean)
    candidates = [b for b in clean if set(catalogue) & b["items"].keys()]
    good, sizes = check_photos(candidates, stats)
    selected = select_bins(good, catalogue)
    splits = make_splits(selected, catalogue)
    write_pack(selected, splits, catalogue)
    run_checks(selected, splits, catalogue)

    print("\n--- Cleaning summary ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  bins containing a catalogue product: {len(candidates)}")
    multi = [b for b in selected if is_multi(b, catalogue)]
    print(f"  bins with 2+ catalogue products (all placed in train): {len(multi)}")
    for b in multi:
        print(f"      {b['bin_id']}: {b['items']}")
    print(f"  photo sizes among candidates: {dict(sizes)}")

    print("\n--- Split sizes ---")
    for s in SPLITS:
        print(f"  {s}: {len(splits[s])} bins ({len(splits[s]) / N_BINS:.0%})")

    print("\n--- Catalogue ---")
    print(pd.read_csv(os.path.join(OUT_DIR, "catalogue.csv"),
                      dtype={"asin": str})[["asin", "name", "bins_in_subset",
                                            "bins_train", "bins_validation", "bins_test"]]
          .to_string(index=False))

    shutil.make_archive(OUT_DIR, "zip", OUT_DIR)
    print(f"\nZipped to {OUT_DIR}.zip")