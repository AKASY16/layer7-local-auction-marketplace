# Independent empirical-shape experiment

This is a research adapter, not a new default simulator or production recommender.
The baseline engine and its frozen datasets remain read-only.

- `activity.py` inherits `audit.simulator.Market`; it changes exogenous weekly
  visit intensity and the corresponding existing availability input only.
  It does not change consideration, WTP, bidding, proxy settlement, sniping,
  substitution, budgets, event priorities or keyrng purposes.
- `policy.py` accepts a declared historical168-cell profile and detached public
  listings. It has no buyer, World, future listing or outcome argument.
- The five policies share valid durations; random and TOP3 recommendations avoid
  00:00–04:59. Manual end times remain the comparison baseline. The three TOP3
  variants share one ranker, a180-minute separation, earlier-time tie breaking,
  and closest-to-manual seller selection.
- Weekly values are constant within an observed hour. Positive phase shifts use
  whole-week rotation, including weekday carry. This differs from converting a
  timestamp to KST and from the existing buyer-specific within-day chronotype.
- `alpha_b = integral(old_effective_activity, active_window) /
  integral(new_activity, active_window)` preserves each buyer's expected organic
  visits at market thickness1. It does not force realized visit counts or
  endogenous market participation to match.
- A shared dominating Poisson pool avoids clipping new profile peaks. Its cap is
  calculated from the prespecified experiment set. No cap/profile is passed to
  the policy. Original-world regression tests use the original pool.
- Seller preference quantiles and original nominal duration/jitter reproduce the
  original supply-generation rule under the new profile. This is an ASSUMED
  coupling, not an observed Retailrocket auction-seller model.
- Native weekly planned availability uses weekday peak; the preserved-legacy
  planned-availability diagnostic distinguishes this assumed mapping from
  organic visit shaping. Both keep the original activity/peak gate and session
  exemption.

See the preregistration, time-transfer note and final report under
`validation/v2_empirical` and `research/activity_20261031`. No model calibration,
policy weight fitting, added collision penalty or production deployment occurs.
