import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, DateFormatter
from matplotlib.ticker import MaxNLocator
from pathlib import Path
from math import ceil
from typing import Optional, List, Dict, Tuple
from matplotlib.lines import Line2D
from matplotlib.dates import DayLocator, DateFormatter
from matplotlib.ticker import MaxNLocator

# -------------------- CONFIG --------------------
DATA_DIR = Path.cwd()
N_BUILDINGS = 20
ALGOS = [
    # 'P_RBC',
    'PI_RBC',
    # 'PID_RBC',
    # 'GB_PID_RBC',
    'SAC',
    'SAC_CENTRALIZED',
    'AAC-MADRL',
]  # <-- Indoor T con colori diversi + legenda
district = 'CA'
dataset_key = f"{district}_{N_BUILDINGS}_dynamics"
beta = 0.2
gamma = 2.0
lr = 0.0003
season = 'winter'

# Pattern cartelle (aggiungi/varia se necessario)
ALGO_PATTERNS: Dict[str, List[str]] = {
    'P_RBC': [
        f"outputs/data/{dataset_key}/schema.json/obs/P_rbc/obs_building" + "_{i}.csv",
    ],
    'PI_RBC': [
        f"outputs/data/{dataset_key}/schema.json/obs/PI_rbc/obs_building" + "_{i}.csv",
    ],
    'PID_RBC': [
        f"outputs/data/{dataset_key}/schema.json/obs/PID_rbc/obs_building" + "_{i}.csv",
    ],
    'GB_PID_RBC': [
        f"outputs/data/{dataset_key}/schema.json/obs/GB_PID_rbc/obs_building" + "_{i}.csv",
    ],
    'SAC': [
        f"outputs/data/{dataset_key}/schema.json/obs/sac/beta={beta}_gamma={gamma}/lr={lr}/obs_building" + "_{i}.csv",
    ],
    'SAC_CENTRALIZED': [
        f"outputs/data/{dataset_key}/schema.json/obs/sac_centralized/beta={beta}_gamma={gamma}/lr={lr}/obs_building" + "_{i}.csv",
    ],
    'AAC-MADRL': [
        f"outputs/data/{dataset_key}/schema.json/obs/aac_madrl/beta={beta}_gamma={gamma}/lr={lr}/obs_building" + "_{i}.csv",
    ],
}

# Dataset orario a partire da:
START_DATE = pd.Timestamp("2023-07-01 00:00:00") if season == "summer" else pd.Timestamp("2023-01-01 00:00:00")

# Layout figura
COLS = 2
FIGWIDTH = 14
ROW_HEIGHT = 3.1

# Colonne attese
CAND_COLS = {
    "tin": ["indoor_temperature"],
    "tout": ["outdoor_dry_bulb_temperature", "outdoor_temperature"],
    "sp": ["cooling_sp", "cooling_setpoint", "setpoint"],
    "band": ["comfort_band"],
    # NEW:
    "cool_demand": ["cooling demand", "cooling_demand", "cool_dmd", "cooling_power", "cooling_energy"],
    "heat_demand": ["heating demand", "heating_demand", "heat_demand", "heating_power", "heating_energy"],
}


# -------------------- UTILS --------------------
def find_first_existing(patterns: List[str], i: int) -> Optional[Path]:
    for pat in patterns:
        p = DATA_DIR / pat.format(i=i)
        if p.exists():
            return p
    return None


def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    low = {"".join(str(c).split()).lower(): c for c in df.columns}
    for cand in candidates:
        key = "".join(cand.split()).lower()
        if key in low:
            return low[key]
    return None


def load_building_algo(i: int, algo: str) -> Optional[pd.DataFrame]:
    fp = find_first_existing(ALGO_PATTERNS[algo], i)
    if fp is None:
        print(f"[MISS] {algo} b{i}: file non trovato")
        return None

    df = pd.read_csv(fp)
    if df.empty:
        print(f"[MISS] {algo} b{i}: file vuoto {fp}")
        return None

    idx = pd.date_range(start=START_DATE, periods=len(df), freq="h")
    df = df.copy()
    df.index = idx


    col_tin = find_col(df, CAND_COLS["tin"])
    col_sp = find_col(df, CAND_COLS["sp"])
    col_bd = find_col(df, CAND_COLS["band"])
    col_cool = find_col(df, CAND_COLS["cool_demand"])
    col_heat = find_col(df, CAND_COLS["heat_demand"])
    col_tout = find_col(df, CAND_COLS["tout"])

    out = pd.DataFrame(index=df.index)
    if col_tin:  out["T_in"] = pd.to_numeric(df[col_tin], errors="coerce")
    if col_sp:   out["Setpoint"] = pd.to_numeric(df[col_sp], errors="coerce")
    if col_bd:   out["Comfort_Band"] = pd.to_numeric(df[col_bd], errors="coerce")
    if col_cool: out["Cooling_Demand"] = pd.to_numeric(df[col_cool], errors="coerce").clip(lower=0)
    if col_heat: out["Heating_Demand"] = pd.to_numeric(df[col_heat], errors="coerce").clip(lower=0)
    if col_tout: out["T_out"] = pd.to_numeric(df[col_tout],
                                              errors="coerce")  # <-- Carichiamo T_out (necessario per plot_week_overlay)

    # bounds (band = semi-ampiezza)
    if "Setpoint" in out.columns and "Comfort_Band" in out.columns:
        out["Comfort_Low"] = out["Setpoint"] - out["Comfort_Band"]
        out["Comfort_High"] = out["Setpoint"] + out["Comfort_Band"]

    if out.dropna(how="all").empty:
        print(f"[MISS] {algo} b{i}: nessuna colonna utile")
        return None
    return out


def gather_all() -> Dict[int, Dict[str, Optional[pd.DataFrame]]]:
    all_data: Dict[int, Dict[str, Optional[pd.DataFrame]]] = {}
    any_found = False
    for i in range(N_BUILDINGS):
        all_data[i] = {}
        for a in ALGOS:
            df = load_building_algo(i, a)
            all_data[i][a] = df
            if df is not None:
                any_found = True
    if not any_found:
        raise RuntimeError("Nessun file trovato (controlla i path in ALGO_PATTERNS).")
    return all_data


def month_week_ranges(month_start: pd.Timestamp) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Finestre (start, end-excl) di 7 giorni per il mese di month_start."""
    month_start = month_start.normalize().replace(day=1)
    month_end = (month_start + pd.offsets.MonthEnd(1)).normalize() + pd.Timedelta(days=1)  # exclusive
    ranges: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    s = month_start
    while s < month_end:
        e = min(s + pd.Timedelta(days=7), month_end)
        ranges.append((s, e))
        s = e
    return ranges


def _bin_means(x: pd.Series, y: pd.Series, binsize: float = 0.25) -> Tuple[np.ndarray, np.ndarray]:
    """Ritorna (centers, mean_y) su bin uniformi della temperatura."""
    s = pd.DataFrame({"x": x, "y": y}).dropna()
    if s.empty:
        return np.array([]), np.array([])
    xmin, xmax = np.floor(s["x"].min()), np.ceil(s["x"].max())
    edges = np.arange(xmin, xmax + binsize, binsize)
    cats = pd.cut(s["x"], edges, include_lowest=True)
    grp = s.groupby(cats, observed=False)["y"].mean()
    centers = np.array([(iv.left + iv.right) / 2 for iv in grp.index.categories])
    return centers, grp.values


def plot_demand_vs_temperature(
        all_data,
        start,
        end,
        save=True,
        binsize=0.25,
        kind: str = "line",
        include_comfort: bool = False,
        columns: Tuple[str, ...] = ("T_in", "Cooling_Demand", "Heating_Demand"),
):
    """
    Se kind='line': per ogni building disegna serie temporali di T_in (subplot superiore)
    e delle domande (Cooling/Heating) nel subplot inferiore, con colori per algoritmo.

    Se kind='scatter': ripristina lo scatter domanda vs T_in con media binned.

    Ritorna: percorsi file generati (cooling_fig, heating_fig) per 'scatter',
             oppure un singolo percorso (time_fig) per 'line'.
    """
    ws, we = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    present_buildings = [i for i in range(N_BUILDINGS) if any(all_data[i][a] is not None for a in ALGOS)]
    if not present_buildings:
        print("[WARN] Nessun building con dati disponibili per il periodo.")
        return None

    n = len(present_buildings)
    palette = plt.cm.tab10.colors
    algo_colors = {}
    for algo in ALGOS:
        algo_colors[algo] = palette[ALGOS.index(algo)]

    # ============== KIND: LINE (time series) =================
    if kind.lower() == "line":
        total_rows = (ceil(n / COLS)) * 2
        figheight = max(ROW_HEIGHT * (n * 2 / COLS), 6.0)

        fig, axes = plt.subplots(total_rows, COLS, figsize=(FIGWIDTH, figheight), squeeze=False, sharex=False)

        # Riduce lo spazio verticale tra subplot dello stesso building
        fig.subplots_adjust(hspace=0.35)

        band_yellow = "#fff3b0"
        sp_style = (0, (5, 3))

        for idx, bid in enumerate(present_buildings):
            col = idx % COLS
            base_row = (idx // COLS) * 2
            row_temp = base_row
            row_demand = base_row + 1

            ax_temp = axes[row_temp][col]
            ax_demand = axes[row_demand][col]

            # Condivide l'asse X tra i due subplot dello stesso building
            ax_temp.sharex(ax_demand)
            ax_temp.tick_params(labelbottom=False)

            # legenda per questo building
            temp_handles = []
            demand_handles = []

            # opzionale: comfort band e setpoint
            if include_comfort:
                ref_df = None
                for a in ALGOS:
                    df_a = all_data[bid].get(a)
                    if df_a is None:
                        continue
                    sl = df_a.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))]
                    if not sl.empty:
                        ref_df = sl
                        break
                if ref_df is not None:
                    if {"Comfort_Low", "Comfort_High"}.issubset(ref_df.columns):
                        ax_temp.fill_between(ref_df.index, ref_df["Comfort_Low"], ref_df["Comfort_High"],
                                             color=band_yellow, alpha=0.18, linewidth=0, zorder=1)
                    if "Setpoint" in ref_df.columns and not ref_df["Setpoint"].isna().all():
                        ax_temp.plot(ref_df.index, ref_df["Setpoint"], linewidth=1.0, linestyle=sp_style,
                                     color="black", alpha=0.9, zorder=2)

                    # <-- MODIFICA: Rimosso plot T_out da qui -->

            # serie temporali per ciascun algoritmo
            for algo in ALGOS:
                df = all_data[bid].get(algo)
                if df is None:
                    continue
                sl = df.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))]
                if sl.empty:
                    continue

                # T_in (subplot superiore)
                if "T_in" in columns and "T_in" in sl.columns and not sl["T_in"].isna().all():
                    line, = ax_temp.plot(sl.index, sl["T_in"], color=algo_colors[algo], linestyle='-', linewidth=1.0,
                                         alpha=0.95, label=f"{algo}")
                    temp_handles.append(line)

                # Domande (subplot inferiore) - linee continue senza tratteggio
                if "Cooling_Demand" in columns and "Cooling_Demand" in sl.columns and not sl[
                    "Cooling_Demand"].isna().all():
                    line_cool, = ax_demand.plot(sl.index, sl["Cooling_Demand"], color=algo_colors[algo], linestyle='-',
                                                linewidth=1.0, alpha=0.95, label=f"{algo} Cooling")
                    demand_handles.append(line_cool)
                if "Heating_Demand" in columns and "Heating_Demand" in sl.columns and not sl[
                    "Heating_Demand"].isna().all():
                    line_heat, = ax_demand.plot(sl.index, sl["Heating_Demand"], color=algo_colors[algo], linestyle='-',
                                                linewidth=1.0, alpha=0.7, label=f"{algo} Heating")
                    demand_handles.append(line_heat)

            ax_temp.set_title(f"Building {bid}", fontsize=10, pad=8)
            ax_temp.set_ylabel("T [°C]", fontsize=9)
            ax_demand.set_ylabel("Demand", fontsize=9)
            ax_demand.set_xlabel("Date", fontsize=9)

            ax_temp.grid(True, linestyle="--", alpha=0.3, zorder=0)
            ax_demand.grid(True, linestyle="--", alpha=0.3, zorder=0)

            ax_demand.xaxis.set_major_locator(DayLocator(interval=1))
            ax_demand.xaxis.set_major_formatter(DateFormatter("%d-%m"))
            ax_demand.tick_params(axis="x", rotation=0, labelsize=8)

            ax_temp.yaxis.set_major_locator(MaxNLocator(nbins=5))
            ax_demand.yaxis.set_major_locator(MaxNLocator(nbins=5))
            ax_temp.tick_params(labelsize=8)
            ax_demand.tick_params(labelsize=8)

            # Aggiungi legenda in ogni subplot
            if temp_handles:
                ax_temp.legend(handles=temp_handles, loc="upper right", frameon=True, framealpha=0.85,
                               facecolor="white", edgecolor="none", fontsize=7)
            if demand_handles:
                ax_demand.legend(handles=demand_handles, loc="upper right", frameon=True, framealpha=0.85,
                                 facecolor="white", edgecolor="none", fontsize=7)

        # spegni assi vuoti
        for row in range(total_rows):
            for col in range(COLS):
                building_idx = (row // 2) * COLS + col
                if building_idx >= n:
                    axes[row][col].axis("off")

        fig.suptitle(
            f"Time series — T_in & demands — {ws} → {we} | {district} | β={beta}, γ={gamma}, lr={lr}",
            y=0.995, fontsize=13
        )

        out_path = None
        if save:
            out_path = DATA_DIR / f"{dataset_key}_TIMESERIES_T_and_Demands_{ws}_to_{we}_beta={beta}_gamma={gamma}_lr={lr}.png"
            fig.savefig(out_path, dpi=220, bbox_inches="tight", pad_inches=0.1)
            print(f"[OK] Plot (time series) salvato: {out_path}")

        plt.close(fig)
        return out_path

    # ============== KIND: SCATTER (domanda vs T) =================
    rows = ceil(n / COLS)
    figheight = max(ROW_HEIGHT * rows, 3.0)

    # ---------------- COOLING ----------------
    fig_c, axes_c = plt.subplots(rows, COLS, figsize=(FIGWIDTH, figheight), squeeze=False, sharex=False)
    legend_handles = [Line2D([0], [0], marker='o', linestyle='None', color=algo_colors[a], label=a) for a in ALGOS]

    for idx, bid in enumerate(present_buildings):
        r, c = divmod(idx, COLS)
        ax = axes_c[r][c]
        for algo in ALGOS:
            df = all_data[bid].get(algo)
            if df is None or "T_in" not in df.columns or "Cooling_Demand" not in df.columns:
                continue
            sl = df.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))][["T_in", "Cooling_Demand"]].dropna()
            if sl.empty:
                continue
            ax.scatter(sl["T_in"], sl["Cooling_Demand"], s=10, alpha=0.35, edgecolors="none", color=algo_colors[algo])
            cx, cy = _bin_means(sl["T_in"], sl["Cooling_Demand"], binsize=binsize)
            if len(cx) > 0:
                ax.plot(cx, cy, linewidth=1.0, alpha=0.95, color=algo_colors[algo])
        ax.set_title(f"Building {bid}")
        ax.set_xlabel("Indoor temperature [°C]")
        ax.set_ylabel("Cooling demand [u.a.]")
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    for idx in range(n, rows * COLS):
        r, c = divmod(idx, COLS)
        axes_c[r][c].axis("off")

    ax0c = axes_c[0][0]
    legc = ax0c.legend(handles=legend_handles, labels=[h.get_label() for h in legend_handles],
                       loc="upper right", frameon=True, framealpha=0.85, facecolor="white", edgecolor="none",
                       fontsize=9)
    legc.set_zorder(10)
    fig_c.suptitle(f"Cooling demand vs indoor temperature — {ws} → {we} | {district} | β={beta}, γ={gamma}, lr={lr}",
                   y=0.995, fontsize=13)
    fig_c.tight_layout(rect=[0, 0, 1, 0.96])

    out_c = None
    if save:
        out_c = DATA_DIR / f"{dataset_key}_SCATTER_T_vs_CoolingDemand_{ws}_to_{we}_beta={beta}_gamma={gamma}_lr={lr}.png"
        fig_c.savefig(out_c, dpi=220, bbox_inches="tight", pad_inches=0.1)
        print(f"[OK] Plot cooling salvato: {out_c}")
    plt.close(fig_c)

    # ---------------- HEATING ----------------
    fig_h, axes_h = plt.subplots(rows, COLS, figsize=(FIGWIDTH, figheight), squeeze=False, sharex=False)
    for idx, bid in enumerate(present_buildings):
        r, c = divmod(idx, COLS)
        ax = axes_h[r][c]
        for algo in ALGOS:
            df = all_data[bid].get(algo)
            if df is None or "T_in" not in df.columns or "Heating_Demand" not in df.columns:
                continue
            sl = df.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))][["T_in", "Heating_Demand"]].dropna()
            if sl.empty:
                continue
            ax.scatter(sl["T_in"], sl["Heating_Demand"], s=10, alpha=0.35, edgecolors="none", color=algo_colors[algo])
            cx, cy = _bin_means(sl["T_in"], sl["Heating_Demand"], binsize=binsize)
            if len(cx) > 0:
                ax.plot(cx, cy, linewidth=1.0, alpha=0.95, color=algo_colors[algo])

        ax.set_title(f"Building {bid}")
        ax.set_xlabel("Indoor temperature [°C]")
        ax.set_ylabel("Heating demand [u.a.]")
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    for idx in range(n, rows * COLS):
        r, c = divmod(idx, COLS)
        axes_h[r][c].axis("off")

    ax0h = axes_h[0][0]
    legh = ax0h.legend(handles=legend_handles, labels=[h.get_label() for h in legend_handles],
                       loc="upper right", frameon=True, framealpha=0.85, facecolor="white", edgecolor="none",
                       fontsize=9)
    legh.set_zorder(10)
    fig_h.suptitle(f"Heating demand vs indoor temperature — {ws} → {we} | {district} | β={beta}, γ={gamma}, lr={lr}",
                   y=0.995, fontsize=13)
    fig_h.tight_layout(rect=[0, 0, 1, 0.96])

    out_h = None
    if save:
        out_h = DATA_DIR / f"{dataset_key}_SCATTER_T_vs_HeatingDemand_{ws}_to_{we}_beta={beta}_gamma={gamma}_lr={lr}.png"
        fig_h.savefig(out_h, dpi=220, bbox_inches="tight", pad_inches=0.1)
        print(f"[OK] Plot heating salvato: {out_h}")
    plt.close(fig_h)

    return out_c, out_h


def plot_temperature_vs_net_demand_fullperiod(all_data, save=True, binsize=0.5):
    """
    Per ogni building, scatter T_in vs NetDemand = Heating_Demand - Cooling_Demand
    sull'intero periodo disponibile, con media binned per evidenziare la relazione.
    """
    present_buildings = [i for i in range(N_BUILDINGS) if any(all_data[i][a] is not None for a in ALGOS)]
    if not present_buildings:
        print("[WARN] Nessun building con dati disponibili.")
        return None

    n = len(present_buildings)
    rows = ceil(n / COLS)
    figheight = max(ROW_HEIGHT * rows, 3.0)

    palette = plt.cm.tab10.colors
    algo_colors = {}
    for algo in ALGOS:
        algo_colors[algo] = palette[ALGOS.index(algo)]

    fig, axes = plt.subplots(rows, COLS, figsize=(FIGWIDTH, figheight), squeeze=False, sharex=False)
    legend_handles = [Line2D([0], [0], marker='o', linestyle='None', color=algo_colors[a], label=a) for a in ALGOS]

    for idx, bid in enumerate(present_buildings):
        r, c = divmod(idx, COLS)
        ax = axes[r][c]

        for algo in ALGOS:
            df = all_data[bid].get(algo)
            if df is None or "T_in" not in df.columns:
                continue

            T = df["T_in"]
            H = df["Heating_Demand"] if "Heating_Demand" in df.columns else pd.Series(0.0, index=df.index)
            C = df["Cooling_Demand"] if "Cooling_Demand" in df.columns else pd.Series(0.0, index=df.index)
            net = (pd.to_numeric(H, errors="coerce").fillna(0) -
                   pd.to_numeric(C, errors="coerce").fillna(0))

            s = pd.DataFrame({"T": T, "net": net}).dropna()
            if s.empty:
                continue
            ax.scatter(s["T"], s["net"], s=10, alpha=0.30, edgecolors="none", color=algo_colors[algo])

            cx, cy = _bin_means(s["T"], s["net"], binsize=binsize)
            if len(cx) > 0:
                ax.plot(cx, cy, linewidth=1.0, alpha=0.95, color=algo_colors[algo])

        ax.set_title(f"Building {bid}")
        ax.set_xlabel("Indoor temperature [°C]")
        ax.set_ylabel("Net demand [u.a.]  (Heating − Cooling)")
        ax.axhline(0, linewidth=1.0, alpha=0.6)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    for idx in range(n, rows * COLS):
        r, c = divmod(idx, COLS)
        axes[r][c].axis("off")

    ax0 = axes[0][0]
    leg = ax0.legend(handles=legend_handles, labels=[h.get_label() for h in legend_handles],
                     loc="upper right", frameon=True, framealpha=0.85, facecolor="white", edgecolor="none", fontsize=9)
    leg.set_zorder(10)

    fig.suptitle(f"Indoor temperature vs NET demand (H−C) — full period | {district} | β={beta}, γ={gamma}, lr={lr}",
                 y=0.995, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out = None
    if save:
        out = DATA_DIR / f"{dataset_key}_SCATTER_T_vs_NETDemand_fullperiod_beta={beta}_gamma={gamma}_lr={lr}.png"
        fig.savefig(out, dpi=220, bbox_inches="tight", pad_inches=0.1)
        print(f"[OK] Plot NET demand salvato: {out}")
    plt.close(fig)
    return out


# -------------------- PLOT SETTIMANALE --------------------

def plot_week_overlay(all_data, week_start, week_end, save=True):
    ws, we = week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")
    present_buildings = [i for i in range(N_BUILDINGS) if any(all_data[i][a] is not None for a in ALGOS)]
    if not present_buildings:
        print("[WARN] Nessun building con dati disponibili per la settimana.")
        return None

    n = len(present_buildings)
    rows = ceil(n / COLS)
    figheight = max(ROW_HEIGHT * rows, 3.0)
    fig, axes = plt.subplots(rows, COLS, figsize=(FIGWIDTH, figheight), squeeze=False, sharex=False)

    palette = plt.cm.tab10.colors
    algo_colors = {}
    for algo in ALGOS:
        algo_colors[algo] = palette[ALGOS.index(algo)]

    sp_style = (0, (5, 3))  # setpoint: dashed nero
    band_yellow = "#fff3b0"

    # --- MODIFICA 1: Aggiungi T_out alla lista per la legenda ---
    legend_handles = [Line2D([0], [0], color=algo_colors[algo], linewidth=1.0, label=algo) for algo in ALGOS]
    legend_handles.append(
        Line2D([0], [0], color="gray", linewidth=1.2, linestyle=':', label="T_out")
    )
    # --- Fine MODIFICA 1 ---

    for idx, bid in enumerate(present_buildings):
        r, c = divmod(idx, COLS)
        ax = axes[r][c]

        # comfort band + setpoint (una sola volta per pannello, dal primo algo disponibile)
        ref_df = None
        for a in ALGOS:
            df_a = all_data[bid].get(a)
            if df_a is None:
                continue
            sl = df_a.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))]
            if not sl.empty:
                ref_df = sl
                break
        if ref_df is not None:
            if {"Comfort_Low", "Comfort_High"}.issubset(ref_df.columns):
                ax.fill_between(ref_df.index, ref_df["Comfort_Low"], ref_df["Comfort_High"],
                                color=band_yellow, alpha=0.18, linewidth=0, zorder=1)
            if "Setpoint" in ref_df.columns and not ref_df["Setpoint"].isna().all():
                ax.plot(ref_df.index, ref_df["Setpoint"], linewidth=1.0, linestyle=sp_style,
                        color="black", alpha=0.95, zorder=3)

            # --- MODIFICA 2: Plotta T_out dal ref_df ---
            if "T_out" in ref_df.columns and not ref_df["T_out"].isna().all():
                ax.plot(ref_df.index, ref_df["T_out"],
                        linewidth=1.2, linestyle=':',
                        color="gray", alpha=0.9,
                        zorder=2)  # zorder=2 la mette dietro T_in e Setpoint
            # --- Fine MODIFICA 2 ---

        # indoor temperature di tutti gli algoritmi con colori diversi
        for algo in ALGOS:
            df = all_data[bid].get(algo)
            if df is None:
                continue
            sl = df.loc[ws:(pd.Timestamp(we) - pd.Timedelta(seconds=1))]
            if sl.empty or "T_in" not in sl.columns or sl["T_in"].isna().all():
                continue
            ax.plot(sl.index, sl["T_in"], linewidth=1.0, linestyle='-',
                    color=algo_colors[algo], alpha=0.95, zorder=4)

        ax.set_title(f"Building {bid}")
        ax.set_ylabel("°C")
        ax.grid(True, linestyle="--", alpha=0.3, zorder=0)
        ax.xaxis.set_major_locator(DayLocator(interval=1))
        ax.xaxis.set_major_formatter(DateFormatter("%d-%m"))
        ax.tick_params(axis="x", rotation=0)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    # spegni assi vuoti
    for idx in range(n, rows * COLS):
        r, c = divmod(idx, COLS)
        axes[r][c].axis("off")

    # >>> LEGENDA NEL PRIMO PANNELLO (sempre visibile)
    ax0 = axes[0][0]
    leg = ax0.legend(handles=legend_handles, labels=[h.get_label() for h in legend_handles],
                     loc="upper left", frameon=True, framealpha=0.85,
                     facecolor="white", edgecolor="none", fontsize=9)
    leg.set_zorder(10)  # porta la legenda davanti a tutto

    fig.suptitle(
        f"Andamento settimanale — {ws} → {we} | {district} | β={beta}, γ={gamma}, lr={lr}",
        y=0.995, fontsize=13
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = None
    if save:
        out_name = f"{dataset_key}_WEEK_overlay_RBC_SAC_AAC-MADRL_{ws}_to_{we}_beta={beta}_gamma={gamma}_lr={lr}.png"
        out_path = DATA_DIR / out_name
        fig.savefig(out_path, dpi=220, bbox_inches="tight", pad_inches=0.1)
        print(f"[OK] Plot salvato: {out_path}")

    plt.close(fig)
    return out_path


# -------------------- DRIVER: plotti tutte le settimane del mese --------------------
def plot_all_weeks_of_month():
    all_data = gather_all()
    month_start = START_DATE.normalize().replace(day=1)
    week_ranges = month_week_ranges(month_start)

    outputs = []
    for (ws, we) in week_ranges:
        p = plot_week_overlay(all_data, ws, we, save=True)
        outputs.append(p)
    return outputs


def plot_all_weeks_of_month_demand_lines(include_comfort=False):
    all_data = gather_all()
    month_start = START_DATE.normalize().replace(day=1)
    week_ranges = month_week_ranges(month_start)
    outs = []
    for (ws, we) in week_ranges:
        p = plot_demand_vs_temperature(
            all_data, ws, we, kind="line", include_comfort=include_comfort
        )
        outs.append(p)
    return outs


def plot_fullperiod_net_demand_scatter(binsize=0.5):
    all_data = gather_all()
    return plot_temperature_vs_net_demand_fullperiod(all_data, save=True, binsize=binsize)


if __name__ == "__main__":
    plot_all_weeks_of_month()

    # nuove linee (serie temporali) di T_in + domande
    plot_all_weeks_of_month_demand_lines(include_comfort=True)

    # nuovo scatter T_in vs (Heating − Cooling) sull'intero periodo
    plot_fullperiod_net_demand_scatter(binsize=0.5)