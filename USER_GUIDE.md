# Smart Bin Classifier – User guide

**What it does:** you enter an order; the app checks, from one photo of a warehouse bin, whether the bin holds
every ordered item in at least the ordered quantity.

**Open it:** https://smart-bin-classifier-charan.streamlit.app (if it shows a "wake up" button, click it and wait
about a minute). To run it on your own computer, see *Run it locally* in the README.

---

## Check an order against a matching bin

1. **Mode** (left panel): keep **Order + matching bin**.
2. **1. Build the order:** choose one or more products from the list, and set a quantity (1–5) for each.
3. **2. Bin photo:** the app shows a bin photo from its records that holds your order.
   - **Show another matching bin** picks a different one.
   - **Choose a different bin** lets you pick any bin by its id, for example to see a FAIL.
   - When no bin holds the whole order (most orders with two or more products), the closest bin is shown.
   - *What the warehouse records say* shows the recorded contents. These are **not** used by Validate.
4. **3. Validate:** the model looks only at the photo and reports, for each ordered item, the ordered quantity,
   the quantity it found, and PASS or FAIL.

## Check an order against a blind bin

1. **Mode:** choose **Blind mode**.
2. Type a bin id from the blind folder, for example `103072` or `2575` (leading zeros and `.jpg` are optional).
3. Build the order and click **Validate**. Blind bins have no records in the app; the answer comes from the photo alone.

## Reading the result

| You see | It means |
|---|---|
| ✅ PASS on an item | The model found at least the ordered quantity |
| ❌ FAIL: item not found | The model found none of this item |
| ❌ FAIL: fewer units found than ordered (x of y) | The model found some, but fewer than ordered |
| **Order PASS** (green) | Every item passed |
| **Order FAIL** (red) | At least one item failed; the table shows which and why |

Other products in the bin that are not in the order are ignored.

## Messages instead of a result

| Message | What to do |
|---|---|
| Select at least one product for the order | Choose a product in step 1 |
| '…' is not a bin id | Blind mode: type digits only |
| Bin … is not in the blind folder | Blind mode: use an id from the blind folder |

## The validation log

Every Validate click is recorded (time, order, photo, model output, result, seconds taken). Open **Validation log**
at the bottom of the page to see the latest entries or **Download the full log**. On the free cloud host the log is
cleared when the app restarts, so download it to keep it.

## Good to know

- The model knows only the 10 catalogue products, and only from these warehouse photos.
- It is right about 4 times in 5 per product. It struggles with items hidden behind others or under tape, blurry
  photos, and counting stacked identical items. Treat a FAIL as "please check this bin".
