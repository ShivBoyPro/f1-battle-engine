"""
Advanced F1 Telemetry Battle Engine v2 (Optimized)
====================================================
Performance improvements:
  - Vectorized numpy operations
  - Optimized interpolation with numpy
  - Cached interpolation for reuse
  - Reduced data copies
  - Better memory management
"""
import time
import fastf1 as ff1
import numpy as np
import pandas as pd
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("TelemetryEngine")


# ── Custom Exceptions ─────────────────────────────────────────────────────────
class DriverNotFoundError(ValueError):
    pass

class InsufficientTelemetryError(RuntimeError):
    pass


# ── Result container ──────────────────────────────────────────────────────────
@dataclass
class BattleResult:
    telemetry: pd.DataFrame
    sectors: pd.DataFrame
    summary: dict = field(default_factory=dict)


# ── Engine ────────────────────────────────────────────────────────────────────
class TelemetryEngine:
    """
    Loads F1 session data and produces a fully synchronised, physics-enriched
    telemetry comparison between two drivers.
    """

    MIN_POINTS = 200

    def __init__(self, cache_dir: str = "data/", n_sectors: int = 20):
        os.makedirs(cache_dir, exist_ok=True)
        ff1.Cache.enable_cache(cache_dir)
        self.n_sectors = n_sectors
        log.info("TelemetryEngine initialised (cache=%s, sectors=%d)", cache_dir, n_sectors)

    # ── Public API ────────────────────────────────────────────────────────────
    def compare(
        self,
        year: int,
        gp: str,
        session_type: str,
        d1: str,
        d2: str,
        lap_selector: str = "fastest",
    ) -> BattleResult:
        """Main entry point. Returns BattleResult with telemetry, sectors, summary."""
        log.info("Loading %d %s %s …", year, gp, session_type)
        session = ff1.get_session(year, gp, session_type)
        session.load(telemetry=True, laps=True, weather=False)

        l1 = self._pick_lap(session, d1, lap_selector)
        l2 = self._pick_lap(session, d2, lap_selector)

        t1 = self._enrich_telemetry(l1, d1)
        t2 = self._enrich_telemetry(l2, d2)

        telem = self._sync_and_compare(t1, t2, d1, d2)
        sectors = self._mini_sectors(telem, d1, d2)
        summary = self._build_summary(telem, l1, l2, d1, d2)

        log.info("Battle analysis complete — %d data points", len(telem))
        return BattleResult(telemetry=telem, sectors=sectors, summary=summary)

    # ── Private helpers ───────────────────────────────────────────────────────
    def _pick_lap(self, session, driver: str, selector):
        """Select lap for driver."""
        laps = session.laps.pick_driver(driver)
        if laps.empty:
            raise DriverNotFoundError(f"Driver '{driver}' not found in session.")
        if selector == "fastest":
            lap = laps.pick_fastest()
        elif isinstance(selector, int):
            lap = laps[laps["LapNumber"] == selector].iloc[0]
        else:
            raise ValueError(f"Unknown lap_selector: {selector!r}")
        log.info("  %s lap %s  |  compound: %s  |  time: %s",
                 driver, lap["LapNumber"], lap.get("Compound", "?"), lap["LapTime"])
        return lap

    def _enrich_telemetry(self, lap, driver: str) -> pd.DataFrame:
        """Add distance, lateral G, DRS flag, throttle, brake (vectorized)."""
        t = lap.get_telemetry().add_distance()
        if len(t) < self.MIN_POINTS:
            raise InsufficientTelemetryError(
                f"Only {len(t)} points for {driver} — lap may be incomplete."
            )

        # ── Smooth speed (vectorized rolling window) ──────────────────────
        t["Speed_smooth"] = t["Speed"].rolling(5, center=True, min_periods=1).mean()

        # ── Longitudinal G (Gx) ────────────────────────────────────────────
        v_ms = t["Speed_smooth"].values / 3.6
        time_s = t["Time"].dt.total_seconds().values
        # Vectorized gradient
        dv = np.gradient(v_ms)
        dt = np.gradient(time_s)
        t["Gx"] = dv / dt / 9.81

        # ── Lateral G (Gy) via curvature ───────────────────────────────────
        if "X" in t.columns and "Y" in t.columns:
            try:
                x = t["X"].values
                y = t["Y"].values
                
                # Vectorized: compute heading angle from position deltas
                dx = np.gradient(x)
                dy = np.gradient(y)
                heading = np.arctan2(dy, dx)
                heading = np.unwrap(heading)
                
                # Curvature = dθ/ds, Gy = κ * v²
                ds = np.gradient(t["Distance"].values)
                ds = np.maximum(ds, 1e-6)  # Avoid divide by zero
                curvature = np.gradient(heading) / ds
                t["Gy"] = curvature * (v_ms ** 2) / 9.81
            except Exception as e:
                log.warning("  Gy computation failed for %s: %s", driver, e)
                t["Gy"] = np.nan
        else:
            log.warning("  X/Y position data unavailable for %s — Gy will be NaN", driver)
            t["Gy"] = np.nan

        # ── DRS heuristic ──────────────────────────────────────────────────
        if "DRS" in t.columns:
            t["DRS_active"] = t["DRS"].isin([10, 12, 14]).astype(int)
        else:
            t["DRS_active"] = 0

        # ── Throttle & Brake ───────────────────────────────────────────────
        t["Throttle"] = t.get("Throttle", pd.Series(np.nan, index=t.index))
        t["Brake"] = t.get("Brake", pd.Series(np.nan, index=t.index))

        return t

    def _sync_and_compare(self, t1: pd.DataFrame, t2: pd.DataFrame,
                           d1: str, d2: str) -> pd.DataFrame:
        """Interpolate both drivers onto shared 1m distance grid (vectorized)."""
        max_dist = min(t1["Distance"].max(), t2["Distance"].max())
        grid = np.linspace(0, max_dist, int(max_dist))

        # ── Vectorized interpolation ──────────────────────────────────────
        def interp_col(df, col):
            """Fast numpy interp."""
            return np.interp(grid, df["Distance"].values, df[col].values, left=np.nan, right=np.nan)

        # Build output in one pass
        out = pd.DataFrame({"Distance": grid})
        
        # Interpolate common columns
        for col in ["Speed_smooth", "Gx", "Gy", "DRS_active", "Throttle", "Brake"]:
            if col in t1.columns:
                out[f"{col}_{d1}"] = interp_col(t1, col)
            if col in t2.columns:
                out[f"{col}_{d2}"] = interp_col(t2, col)

        # Time-based delta
        time1 = interp_col(t1, "Time_s") if "Time_s" in t1.columns else \
                np.interp(grid, t1["Distance"].values, t1["Time"].dt.total_seconds().values)
        time2 = np.interp(grid, t2["Distance"].values, t2["Time"].dt.total_seconds().values)

        out[f"Time_{d1}"] = time1
        out[f"Time_{d2}"] = time2
        out["Delta"] = time1 - time2  # positive = d1 ahead

        return out

    def _mini_sectors(self, telem: pd.DataFrame, d1: str, d2: str) -> pd.DataFrame:
        """Divide lap into n equal-distance sectors (vectorized)."""
        telem = telem.copy()
        telem["Sector"] = pd.cut(telem["Distance"], bins=self.n_sectors, labels=False)

        # Vectorized aggregation
        grouped = telem.groupby("Sector", observed=True)
        
        records = []
        for sec, grp in grouped:
            rec = {
                "Sector": int(sec) + 1,
                "Dist_start": grp["Distance"].iloc[0],
                "Dist_end": grp["Distance"].iloc[-1],
                f"AvgSpeed_{d1}": grp[f"Speed_smooth_{d1}"].mean(),
                f"AvgSpeed_{d2}": grp[f"Speed_smooth_{d2}"].mean(),
                f"PeakBrake_{d1}": grp[f"Gx_{d1}"].min(),
                f"PeakBrake_{d2}": grp[f"Gx_{d2}"].min(),
                "Delta_entry": grp["Delta"].iloc[0],
                "Delta_exit": grp["Delta"].iloc[-1],
                "Delta_gained": grp["Delta"].iloc[-1] - grp["Delta"].iloc[0],
            }
            records.append(rec)

        return pd.DataFrame(records)

    def _build_summary(self, telem, l1, l2, d1: str, d2: str) -> dict:
        """Build headline statistics (vectorized aggregations)."""
        def fmt(td):
            return str(td) if pd.notna(td) else "N/A"

        # Safe max with NaN handling
        def safe_max(series):
            return round(series.max(), 1) if series.notna().any() else 0.0

        def safe_abs_max(series):
            return round(series.abs().max(), 2) if series.notna().any() else None

        return {
            "drivers": [d1, d2],
            "lap_times": {d1: fmt(l1["LapTime"]), d2: fmt(l2["LapTime"])},
            "compounds": {d1: l1.get("Compound", "?"), d2: l2.get("Compound", "?")},
            "top_speed": {
                d1: safe_max(telem[f"Speed_smooth_{d1}"]),
                d2: safe_max(telem[f"Speed_smooth_{d2}"]),
            },
            "max_lat_g": {
                d1: safe_abs_max(telem[f"Gy_{d1}"]) if f"Gy_{d1}" in telem else None,
                d2: safe_abs_max(telem[f"Gy_{d2}"]) if f"Gy_{d2}" in telem else None,
            },
            "max_long_g": {
                d1: round(telem[f"Gx_{d1}"].max(), 2),
                d2: round(telem[f"Gx_{d2}"].max(), 2),
            },
            "max_brake_g": {
                d1: round(telem[f"Gx_{d1}"].min(), 2),
                d2: round(telem[f"Gx_{d2}"].min(), 2),
            },
            "cumulative_delta_s": round(telem["Delta"].iloc[-1], 3),
            "data_points": len(telem),
        }