# Assumptions

Written down where the brief left a choice open. Items marked (confirmed) were asked by email on 20 Oct 2026 and
confirmed by Satwik the same day.

1. **Extra 1,200-image set excluded.** Records `1.jpg`–`1200.jpg` are the only ones with `image_fname` filled in and
   their quantities are exactly 200 bins each of 0–4 units, so they look added rather than real warehouse bins.
2. **Bin id = the record's `name` column** (the photo file name without `.jpg`), because `image_fname` is missing in
   535,234 of the original records.
3. **The 1–5 units rule applies to all 2,000 selected bins**, not only the blind set, with per-product
   quantities checked against `EXPECTED_QUANTITY`. (confirmed)
4. **Inconsistent records are excluded:** per-product quantities must add up to `EXPECTED_QUANTITY`, and every product
   entry must have a whole-number quantity of at least 1 and an `asin` equal to its key.
5. **Catalogue = the 10 most frequent products**, about 200 bins each (198–203), rather than 20 products at about 100,
   so the model has more photos per product. There is no fixed size; each ASIN must be in at least 100 of the
   2,000 bins. (confirmed)
6. **Every selected bin holds at least one catalogue product;** other products in the bin are ignored and never
   predicted.
7. **Multi-item orders:** only one clean bin (276483) holds two catalogue products, so most multi-item orders have no
   matching bin. The app then shows the closest bin (the order is expected to FAIL) and the user can pick
   another bin. PASS/FAIL comes only from the model's
   predictions against the ordered quantities, never from how closely the bin matches. (confirmed)
8. **Blind mode:** the bins validated in the session come from my blind folder. The bin id is the photo name without
   `.jpg`; leading zeros are optional.
9. **Test orders:** one PASS order per test bin (its catalogue products at their true quantities) and one FAIL order
   (add a catalogue product that is absent, or raise one quantity by one; chosen at random, seed 42).
10. **Python 3.13** locally and on Streamlit Community Cloud.
