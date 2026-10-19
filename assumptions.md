# Assumptions (to confirm by email)

1. 
2. Catalogue = the most frequent ASINs, each appearing in at least 100 of the 2,000 selected bins.
3. Every selected bin contains at least one catalogue ASIN; other items are ignored.
4. Bins whose per-item quantities do not add up to EXPECTED_QUANTITY are excluded.
5. Blind-mode bin id = image file number (e.g. 523 for 523.jpg).
6. If no train/validation bin matches an order, the app shows a "no matching bin" message.
7. FAIL test orders use only catalogue products (add an absent product, or raise a quantity).
8. Python 3.13 locally and on the cloud host.
9.The 1–5 units rule appears under ‘Splits and the blind set.’ I’ve assumed it applies to all 2,000 selected bins, not only the blind set. Is that right?”