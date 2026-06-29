# Pincode Coverage Intelligence — Quick-Commerce (2026-06-29)

> **Source:** one-time FULL per-pincode coverage run (EXCEPTION pass) in `/opt/ecom-intel`,
> 2026-06-29. Physically scraped ground truth across all **1,885 pincodes** of the 25
> priority cities — **not** anchor extrapolation. The daily cron remains on the anchor model;
> this was a manual deep pass. See ecom-intel `docs/coverage-runs/2026-06-29-EXCEPTION-full-coverage.md`.

## Headline
- **935 / 1,885 pincodes (50%)** reachable by at least one quick-com platform (was 234 / 12% on the anchor model the same morning — a ~4× real increase).
- **806 / 1,885 (43%)** have Jivo actually on sale.
- **Blinkit delivers to 902 pincodes but stocks Jivo in only 486 → 416 delivers-but-no-Jivo pincodes.** Distribution opportunity, quantified.

## Per platform (each a distinct surface — never summed)
| Platform | Run ID | Delivers to (serviceable) | Jivo on sale | SKUs | Price rows |
|---|---|--:|--:|--:|--:|
| **Zepto** | `2026-06-29-1319` | 693 | 693 | 23 | 14,835 |
| **Blinkit** | `2026-06-29-1203` | 902 | 486 | 9 | 1,898 |
| **Flipkart Minutes** | `2026-06-29-1605` | 340 | 340 | 16 | 568 |

- Zepto & Flipkart-minutes stock Jivo in **every** pincode they serve; Blinkit is the leaky one.
- Avg discounts: Zepto 37.4% · Blinkit 48.2% · Flipkart 34.5%.

## Coverage by city (serviceable pincodes)
| City | Universe | Zepto | Blinkit | Flipkart-min |
|---|--:|--:|--:|--:|
| Delhi | 97 | 70 | 88 | 47 |
| Mumbai | 89 | 82 | 83 | 23 |
| Bengaluru | 117 | 79 | 88 | 9 |
| Chennai | 83 | 61 | 58 | 49 |
| Kolkata | 74 | 48 | 57 | 16 |
| Pune | 145 | 37 | 53 | 14 |
| Hyderabad | 60 | 40 | 36 | 21 |
| Ahmedabad | 81 | 28 | 41 | 27 |
| Coimbatore | 107 | 30 | 39 | 19 |
| Kochi | 143 | 33 | 46 | 0 |
| Lucknow | 43 | 27 | 28 | 22 |
| Jaipur | 84 | 23 | 29 | 24 |
| Mysuru | 68 | 29 | 34 | 5 |
| Gurugram | 29 | 20 | 28 | 16 |
| Chandigarh | 25 | 18 | 21 | 15 |
| Nagpur | 63 | 21 | 26 | 0 |
| Surat | 79 | 12 | 19 | 2 |
| Visakhapatnam | 41 | 0 | 27 | 4 |
| Bhubaneswar | 69 | 0 | 31 | 0 |
| Vadodara | 61 | 4 | 16 | 9 |
| Nashik | 77 | 6 | 13 | 9 |
| Indore | 30 | 13 | 11 | 1 |
| Noida | 28 | 7 | 9 | 5 |
| Vijayawada | 59 | 5 | 11 | 3 |
| Thiruvananthapuram | 133 | 0 | 10 | 0 |


## Method
The 25 cities hold 1,885 distinct pincodes (of India's 19,300), per the India Post directory.
Every pincode was checked on each platform and logged as Jivo-priced / serviceable-no-Jivo /
not-serviceable. No proxies, no extrapolation. Amazon (Fresh 259 + Now 520, kept strictly
separate) is being added under Wave 2.

_Generated 2026-06-29 from ecom-intel `data/coverage/ledger.csv`._
