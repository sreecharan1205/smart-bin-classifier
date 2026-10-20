"""
smartbin.py - the model and the PASS/FAIL rule, shared by the app (app.py) and the evaluation notebook.

Keeping both in one file means the app and the reported test numbers always use exactly the same logic.
Nothing in this file reads bin metadata: validation uses only the photo and the order.
"""
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

MAX_UNITS = 5   # a bin holds 1-5 units, so an ordered quantity above 5 can never pass


class CountNet(nn.Module):
    """ResNet-18 backbone; output [batch, products, 6] = scores for counts 0..5 per product."""

    def __init__(self, n_products, n_counts=6):
        super().__init__()
        self.net = models.resnet18(weights=None)          # weights come from our saved file
        self.net.fc = nn.Linear(self.net.fc.in_features, n_products * n_counts)
        self.n_products, self.n_counts = n_products, n_counts

    def forward(self, x):
        return self.net(x).view(-1, self.n_products, self.n_counts)


class BinModel:
    """Loads smartbin_resnet18.pt once and turns a photo into a found quantity per catalogue product."""

    def __init__(self, path):
        ckpt = torch.load(Path(path), map_location="cpu", weights_only=True)
        self.catalogue = list(ckpt["catalogue"])
        self.thresholds = np.asarray(ckpt["thresholds"], dtype=float)
        self.model = CountNet(len(self.catalogue), ckpt["n_counts"])
        self.model.load_state_dict({k: v.float() if v.is_floating_point() else v
                                    for k, v in ckpt["state_dict"].items()})
        self.model.eval()
        self.tf = transforms.Compose([
            transforms.Resize((ckpt["image_size"], ckpt["image_size"])),
            transforms.ToTensor(),
            transforms.Normalize(ckpt["mean"], ckpt["std"]),
        ])

    @torch.no_grad()
    def probabilities(self, images):
        """List of PIL images -> array [n, products, 6] of probabilities for counts 0..5."""
        x = torch.stack([self.tf(im.convert("RGB")) for im in images])
        return torch.softmax(self.model(x), dim=2).numpy()

    def counts_from_probs(self, probs):
        """Decision rule: present if P(count >= 1) >= the product's threshold; then the most likely count 1..5."""
        p_present = 1.0 - probs[:, :, 0]
        count_if_present = probs[:, :, 1:].argmax(axis=2) + 1
        return np.where(p_present >= self.thresholds[None, :], count_if_present, 0)

    def found_quantities(self, image):
        """One PIL image -> {asin: found quantity} for every catalogue product."""
        counts = self.counts_from_probs(self.probabilities([image]))[0]
        return {asin: int(c) for asin, c in zip(self.catalogue, counts)}


def check_order(order, found):
    """
    The assignment's rule.
      order: {asin: ordered quantity}    found: {asin: found quantity}
    An item PASSES if found >= ordered. The order PASSES only if every item passes.
    Items in the bin that are not in the order are ignored.
    Returns {"result": "PASS"/"FAIL", "items": [...], "reason": plain-language text}.
    """
    items = []
    for asin, ordered in order.items():
        got = int(found.get(asin, 0))
        if got >= ordered:
            status, why = "PASS", ""
        elif got == 0:
            status, why = "FAIL", "item not found"
        else:
            status, why = "FAIL", f"fewer units found than ordered ({got} of {ordered})"
        items.append({"asin": asin, "ordered": int(ordered), "found": got, "result": status, "reason": why})
    failed = [i for i in items if i["result"] == "FAIL"]
    if not failed:
        reason = "every item was found in at least the ordered quantity"
    else:
        reason = f"{len(failed)} of {len(items)} item(s) failed"
    return {"result": "FAIL" if failed else "PASS", "items": items, "reason": reason}


def validate(image, order, model):
    """
    Validate an order against a bin photo. Reads ONLY the photo and the order - never metadata.
    Raises ValueError for bad input so the app can show a clear message instead of crashing.
    """
    if not order:
        raise ValueError("Select at least one product for the order.")
    if image is None:
        raise ValueError("No bin photo was given.")
    unknown = [a for a in order if a not in model.catalogue]
    if unknown:
        raise ValueError(f"Not a catalogue product: {', '.join(unknown)}")
    for asin, q in order.items():
        if not isinstance(q, (int, np.integer)) or q < 1 or q > MAX_UNITS:
            raise ValueError(f"Quantity must be a whole number from 1 to {MAX_UNITS}.")
    found = model.found_quantities(image)
    return check_order(order, found), found
