# Assumptions

Written down where the brief left a choice open. Questions sent by email on 20 Oct 2026 are marked (Q);
update with the replies.

1. **Deadline:** 21 Oct 2026, 11:59 PM IST. The brief mentions both 55 and 72 hours; this date is inside both.
2. **Extra 1,200-image set excluded.** Records `1.jpg`–`1200.jpg` are the only ones with `image_fname` filled in and
   their quantities are exactly 200 bins each of 0–4 units, so they look added rather than real warehouse bins.
3. **Bin id = the record's `name` column** (the photo file name without `.jpg`), because `image_fname` is missing in
   535,234 of the original records.
4. **The 1–5 units rule applies to all 2,000 selected bins**, not only the blind set. (Q)
5. **Inconsistent records are excluded:** per-product quantities must add up to `EXPECTED_QUANTITY`, and every product
   entry must have a whole-number quantity of at least 1 and an `asin` equal to its key.
6. **Catalogue = the 10 most frequent products**, about 200 bins each (198–203), rather than 20 products at about 100,
   so the model has more photos per product. (Q)
7. **Every selected bin holds at least one catalogue product;** other products in the bin are ignored and never
   predicted.
8. **Multi-item orders:** only one clean bin (276483) holds two catalogue products, so most multi-item orders have no
   matching bin. The app then shows the closest bin with a note (the order is expected to FAIL) and the user can pick
   another bin. (Q)
9. **Blind mode:** the bins validated in the session come from my blind folder. The bin id is the photo name without
   `.jpg`; leading zeros are optional.
10. **Test orders:** one PASS order per test bin (its catalogue products at their true quantities) and one FAIL order
    (add a catalogue product that is absent, or raise one quantity by one; chosen at random, seed 42).
11. **Python 3.13** locally and on Streamlit Community Cloud.
