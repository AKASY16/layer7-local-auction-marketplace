"""BARISTA bid-arrival model (Shmueli, Russo & Jank 2007, AOAS 1(2):412-441).

Independent re-implementation of the three-stage NHPP in the paper:
  intensity  eq.(1)  lambda(s) = c * k_j * (1 - s/T)^(alpha_j - 1) on stage j
  mean       eq.(2)  m(s) = integral of lambda
  CDF        eq.(3)  F(s) = m(s) / m(T)
  sampling   eq.(6)-(7) inverse CDF of uniforms (section 4.1)
  likelihood eq.(13) conditional on N(T) = n
Stage factors keep lambda continuous at d1 and T - d2:
  k1 = (1 - d1/T)^(a2 - a1), k2 = 1, k3 = (d2/T)^(a2 - a3).
d1 = d2 = 0 gives NHPP1, d1 = 0 gives NHPP2 (section 3.3).

The model describes when bids arrive in a hard-close auction. It says nothing
about who bids, how much, or why; the market simulator does not draw its bids
from here. It is used to fit real bid times and to check simulated ones.
"""
from dataclasses import dataclass, asdict

import numpy as np
from scipy import optimize

EPS = 1e-12


@dataclass
class Barista:
    a1: float
    a2: float
    a3: float
    d1: float  # length of stage 1, same unit as T
    d2: float  # length of stage 3, same unit as T
    T: float = 1.0

    # --- segment layout -------------------------------------------------
    def _segments(self):
        T, d1, d2 = self.T, self.d1, self.d2
        segs = []
        if d1 > 0:
            segs.append((0.0, d1, (1 - d1 / T) ** (self.a2 - self.a1), self.a1))
        segs.append((d1, T - d2, 1.0, self.a2))
        if d2 > 0:
            segs.append((T - d2, T, (d2 / T) ** (self.a2 - self.a3), self.a3))
        return segs

    def _seg_mass(self, s0, s1, k, a):
        T = self.T
        return k * T / a * ((1 - s0 / T) ** a - (1 - s1 / T) ** a)

    def total_mass(self):
        return sum(self._seg_mass(*s) for s in self._segments())

    # --- functions of the paper -----------------------------------------
    def intensity(self, s, c=1.0):
        s = np.asarray(s, float)
        out = np.zeros_like(s)
        for s0, s1, k, a in self._segments():
            m = (s >= s0) & (s <= s1)
            out[m] = c * k * np.maximum(1 - s[m] / self.T, EPS) ** (a - 1)
        return out

    def cdf(self, s):
        s = np.clip(np.asarray(s, float), 0, self.T)
        out = np.zeros_like(s)
        acc = 0.0
        for s0, s1, k, a in self._segments():
            m = (s >= s0) & (s <= s1)
            out[m] = acc + self._seg_mass(s0, s[m], k, a)
            out[s > s1] = acc + self._seg_mass(s0, s1, k, a)
            acc += self._seg_mass(s0, s1, k, a)
        return out / acc

    def ppf(self, u):
        """Inverse CDF, eq.(6)."""
        u = np.asarray(u, float)
        total = self.total_mass()
        target = u * total
        out = np.full_like(u, self.T)
        acc = 0.0
        for s0, s1, k, a in self._segments():
            mass = self._seg_mass(s0, s1, k, a)
            m = (target >= acc) & (target <= acc + mass)
            base = (1 - s0 / self.T) ** a - (target[m] - acc) * a / (k * self.T)
            out[m] = self.T * (1 - np.maximum(base, 0.0) ** (1 / a))
            acc += mass
        return out

    def sample_times(self, n, rng):
        """n bid times by inversion (section 4.1, eq.7)."""
        return np.sort(self.ppf(rng.random(n)))

    def sample_process(self, c, rng):
        """Random N(T) ~ Poisson(m(T)) then times (end of section 4.1)."""
        n = rng.poisson(c * self.total_mass())
        return self.sample_times(n, rng)

    def loglik(self, x):
        """Conditional log-likelihood given N(T)=n, eq.(13) up to the same constant."""
        x = np.clip(np.asarray(x, float), 0, self.T * (1 - 1e-9))
        g = self.intensity(x)
        return float(np.sum(np.log(np.maximum(g, 1e-300))) - len(x) * np.log(self.total_mass()))

    def to_dict(self):
        return asdict(self)


# --- estimation (section 4.2: likelihood over a changepoint grid) ---------
def _fit_alphas(x, T, d1, d2, n_alpha):
    def nll(theta):
        a = np.exp(theta)
        if n_alpha == 1:
            m = Barista(a[0], a[0], a[0], 0.0, 0.0, T)
        elif n_alpha == 2:
            m = Barista(a[0], a[0], a[1], 0.0, d2, T)
        else:
            m = Barista(a[0], a[1], a[2], d1, d2, T)
        return -m.loglik(x)

    best = None
    for start in ([0.0, -1.0, 0.0][:n_alpha], [1.0, -1.2, 0.3][:n_alpha]):
        r = optimize.minimize(nll, np.array(start), method="L-BFGS-B",
                              bounds=[(-4, 3.5)] * n_alpha)
        if best is None or r.fun < best.fun:
            best = r
    a = np.exp(best.x)
    if n_alpha == 1:
        return Barista(a[0], a[0], a[0], 0.0, 0.0, T), -best.fun
    if n_alpha == 2:
        return Barista(a[0], a[0], a[1], 0.0, d2, T), -best.fun
    return Barista(a[0], a[1], a[2], d1, d2, T), -best.fun


def fit(x, T, d1_grid=None, d2_grid=None):
    """Fit NHPP1, NHPP2 and BARISTA by profile likelihood over changepoints.

    x: bid times in [0, T]. Returns dict with each model, log-lik, AIC, BIC
    and the likelihood-ratio choice of section 4.2.3 (p < 0.05 to step up).
    """
    from scipy.stats import chi2

    x = np.asarray(x, float)
    n = len(x)
    if d1_grid is None:
        d1_grid = T * np.arange(0.02, 0.62, 0.02)
    if d2_grid is None:  # assumes T is in days: 6 seconds to 60 minutes
        d2_grid = np.array([0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 40, 60]) / 1440.0
    out = {}
    m1, l1 = _fit_alphas(x, T, 0, 0, 1)
    out["NHPP1"] = (m1, l1, 1)
    best2 = max((_fit_alphas(x, T, 0, d2, 2) for d2 in d2_grid), key=lambda r: r[1])
    out["NHPP2"] = (best2[0], best2[1], 3)
    best3 = None
    for d1 in d1_grid:
        for d2 in d2_grid:
            if d1 >= T - d2:
                continue
            r = _fit_alphas(x, T, d1, d2, 3)
            if best3 is None or r[1] > best3[1]:
                best3 = r
    out["BARISTA"] = (best3[0], best3[1], 5)

    res = {"n": n, "models": {}}
    for k, (m, ll, p) in out.items():
        res["models"][k] = {"params": m.to_dict(), "loglik": ll, "k": p,
                            "aic": 2 * p - 2 * ll, "bic": p * np.log(max(n, 1)) - 2 * ll}
    chosen = "NHPP1"
    if chi2.sf(2 * (out["NHPP2"][1] - out["NHPP1"][1]), 2) < 0.05:
        chosen = "NHPP2"
        if chi2.sf(2 * (out["BARISTA"][1] - out["NHPP2"][1]), 2) < 0.05:
            chosen = "BARISTA"
    res["lrt_choice"] = chosen
    res["chosen"] = out[chosen][0]
    return res
