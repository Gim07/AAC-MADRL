import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from math import ceil

# --- Parametri dell’esperimento ---
n_buildings = 10
district = "TX"
lr = 0.0003
beta = 0.5
gamma = 3.5

dataset_key = f"{district}_{n_buildings}_dynamics"
outputs_root = Path.cwd() / "outputs" / "data"
kpi_dir = outputs_root / dataset_key / "schema.json" / "kpi" / "test" / f"beta={beta}_gamma={gamma}" / f"lr={lr}"
kpi_dir.mkdir(parents=True, exist_ok=True)

# File KPI (ogni CSV ha colonne: cost_function,District)
kpi_files = {
    # "P_RBC": kpi_dir / f"p_rbc_lr={lr}.csv",
    # "PI_RBC": kpi_dir / f"pi_rbc_lr={lr}.csv",
    "PID_RBC": kpi_dir / f"pid_rbc_lr={lr}.csv",
    "GB_PID_RBC": kpi_dir / f"gb_pid_rbc_lr={lr}.csv",
    # "SAC": kpi_dir / f"sac_lr={lr}.csv",
}

# Ordine desiderato delle KPI
KPI_ORDER = [
    "Import",
    "Variance",
    "Daily Peak Average",
    "Avg Num Comfort Violations",
    "Avg Comfort Violation Above (°C)",
    "Avg Comfort Violation Below (°C)",
    "Avg Num Comfort Violations Above",
    "Avg Num Comfort Violations Below",
]

def read_kpi_csv(file_path: Path, algo_name: str, value_col: str = "District") -> pd.DataFrame:
    if not file_path.exists():
        print(f"[WARN] File non trovato: {file_path}")
        return pd.DataFrame(columns=["cost_function", "value", "Algorithm"])

    df = pd.read_csv(file_path)
    if "cost_function" not in df.columns or value_col not in df.columns:
        raise ValueError(f"Il file {file_path} deve avere le colonne 'cost_function' e '{value_col}'.")
    df = df[["cost_function", value_col]].copy()
    df.rename(columns={value_col: "value"}, inplace=True)
    df["Algorithm"] = algo_name
    return df

def load_all_kpis(kpi_files: dict) -> pd.DataFrame:
    frames = [read_kpi_csv(path, algo) for algo, path in kpi_files.items()]
    df_kpi = pd.concat(frames, ignore_index=True)
    if df_kpi.empty:
        raise FileNotFoundError("Nessun file KPI trovato.")
    # Ordina le KPI secondo la lista e filtra a quelle presenti
    df_kpi["cost_function"] = pd.Categorical(df_kpi["cost_function"], KPI_ORDER, ordered=True)
    df_kpi = df_kpi[~df_kpi["cost_function"].isna()]
    df_kpi.sort_values(["cost_function", "Algorithm"], inplace=True)
    df_kpi.reset_index(drop=True, inplace=True)
    return df_kpi

def plot_kpi_small_multiples(df_kpi: pd.DataFrame, save_dir: Path, cols: int = 2, bar_width: float = 0.6) -> Path:
    """Un’unica figura con un pannello per KPI; Y indipendente per ciascun pannello; colori diversi per algoritmo."""
    algorithms = df_kpi["Algorithm"].unique().tolist()
    kpis = [k for k in KPI_ORDER if k in df_kpi["cost_function"].unique().tolist()]
    n_kpis = len(kpis)
    if n_kpis == 0:
        raise ValueError("Nessuna KPI valida trovata per il plot.")

    rows = ceil(n_kpis / cols)

    # Palette di colori (tab10) – tanti quanti gli algoritmi
    base_colors = plt.rcParams.get("axes.prop_cycle", None)
    if base_colors is not None:
        color_list = base_colors.by_key().get("color", [])
    else:
        color_list = []
    if len(color_list) < len(algorithms):
        # fallback semplice se la rc non fornisce abbastanza colori
        color_list = plt.cm.tab10.colors[:len(algorithms)]
    else:
        color_list = color_list[:len(algorithms)]

    fig_height = max(4.0 * rows, 4.0)
    fig_width = 14 if cols == 2 else 16
    fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height), squeeze=False)

    for idx, kpi in enumerate(kpis):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        sub = df_kpi[df_kpi["cost_function"] == kpi]

        x = np.arange(len(algorithms))
        # Disegna una barra per algoritmo con il suo colore
        for i, algo in enumerate(algorithms):
            val_series = sub.loc[sub["Algorithm"] == algo, "value"]
            v = val_series.values[0] if not val_series.empty else np.nan
            ax.bar(i, v, width=bar_width, color=color_list[i], label=algo if idx == 0 else None)  # legenda solo sul primo pannello
            if np.isfinite(v):
                ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(algorithms, rotation=0)
        ax.set_title(kpi, fontsize=11)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    # Nasconde assi vuoti
    total_axes = rows * cols
    for idx in range(n_kpis, total_axes):
        r, c = divmod(idx, cols)
        axes[r][c].axis("off")

    # Legenda globale (presa dal primo pannello)
    handles, labels = axes[0][0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=len(algorithms), frameon=False, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle(f"KPI Comparison — {dataset_key} (β={beta}, γ={gamma}, lr={lr})", y=0.995, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = save_dir / f"kpi_small_multiples_beta={beta}_gamma={gamma}_lr={lr}.png"
    fig.savefig(out_path, dpi=220)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    df_kpi = load_all_kpis(kpi_files)
    plot_path = plot_kpi_small_multiples(df_kpi, kpi_dir, cols=2)  # cambia cols=3 se preferisci 3 per riga

    print(f"[OK] Figura (small multiples) salvata: {plot_path}")
