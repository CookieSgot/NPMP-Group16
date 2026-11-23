"""Slike in vrednosti za tabele poglavja Skupina16 (iz datotek v results/).

Uporaba (iz korenskega direktorija repozitorija):
    python slike.py
Shrani PDF-je v porocilo/Skupina16/img/ in izpise vrednosti za tabele.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
IMG = ROOT / "porocilo" / "Skupina16" / "img"
IMG.mkdir(exist_ok=True)

MAIN = "20261122-184732"                                  # glavni zagon (vsi dvojcki enako zgrajeni)
RUNS = {"20261122-012230": "zagon 1", "20261122-015016": "zagon 2", MAIN: "zagon 3"}

plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "legend.fontsize": 7,
                     "font.family": "serif", "pdf.fonttype": 42})

main = pd.read_csv(RES / f"{MAIN}_summary.csv", dtype={"target": str})
qpu = pd.concat([pd.read_csv(RES / f"{t}_summary.csv", dtype={"target": str}).assign(run=r)
                 for t, r in RUNS.items()], ignore_index=True)
opts = sorted(main["opt"].unique())
ns = sorted(main["n"].unique())

TW = {  # stolpec -> (oznaka, slog)
    "P_twin_csv": ("dvojček (CSV = živa kal.)", dict(color="tab:blue", marker="^", ls="-")),
    "P_twin_csv_noidle": ("dvojček brez čakanja", dict(color="tab:orange", marker="v", ls="--")),
    "P_twin_fake": ("dvojček FakeMarrakesh", dict(color="tab:green", marker="s", ls=":")),
}
QM = {"zagon 1": "o", "zagon 2": "D", "zagon 3": "*"}

# --- slika 1: P(oznaceno) v odvisnosti od n --------------------------------------
fig, axs = plt.subplots(1, len(opts), figsize=(4.8, 2.3), sharey=True)
for ax, opt in zip(axs, opts):
    g = main[main["opt"] == opt]
    ax.plot(g["n"], g["ideal_theory"], color="gray", lw=1, label="idealno")
    ax.plot(g["n"], 2 * g["random"], color="tab:red", ls="--", lw=1, label=r"prag $2/2^n$")
    ax.plot(g["n"], g["random"], color="gray", ls=":", lw=1, label=r"naključno $1/2^n$")
    for c, (lab, st) in TW.items():
        ax.plot(g["n"], g[c], lw=1, ms=3.5, label=lab, **st)
    for run, mk in QM.items():
        q = qpu[(qpu["opt"] == opt) & (qpu["run"] == run)]
        ax.scatter(q["n"], q["P_qpu"], marker=mk, s=18 if mk != "*" else 40, color="black",
                   zorder=5, label=f"QPU, {run}")
    ax.set(yscale="log", xticks=ns, xlabel="$n$", title=f"optimizacijska stopnja {opt}")
    ax.grid(alpha=0.3, which="both")
axs[0].set_ylabel("$P$(označeno stanje)")
handles, labels = axs[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.24, 1, 1))
fig.savefig(IMG / "prag.pdf", bbox_inches="tight")

# --- slika 2: P * 2^n v odvisnosti od stevila CZ ---------------------------------
fig, axs = plt.subplots(1, len(opts), figsize=(4.8, 2.2), sharey=True, sharex=True)
for ax, opt in zip(axs, opts):
    g = main[main["opt"] == opt]
    ax.axhline(2, color="tab:red", ls="--", lw=1, label=r"prag $2\times$ naključno")
    ax.axhline(1, color="gray", ls=":", lw=1, label="naključno")
    st = TW["P_twin_csv"][1]
    ax.scatter(g["two_q"], g["P_twin_csv"] * 2 ** g["n"], marker="^", color=st["color"], s=18,
               label=TW["P_twin_csv"][0])
    for run, mk in QM.items():
        q = qpu[(qpu["opt"] == opt) & (qpu["run"] == run)]
        ax.scatter(q["two_q"], q["P_qpu"] * 2 ** q["n"], marker=mk, s=18 if mk != "*" else 40,
                   color="black", zorder=5, label=f"QPU, {run}")
    for n, gg in g.groupby("n"):
        ax.text(gg["two_q"].iloc[0], 1.02, f"$n={n}$", transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=6.5, color="gray")
    ax.set(xscale="log", yscale="log", xlabel="število vrat CZ po prevajanju")
    ax.set_title(f"optimizacijska stopnja {opt}", pad=11)
    ax.grid(alpha=0.3, which="both")
axs[0].set_ylabel(r"$P \cdot 2^n$")
axs[0].set_yticks([1, 2, 4, 8], ["1", "2", "4", "8"])
axs[0].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
handles, labels = axs[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.17, 1, 1))
fig.savefig(IMG / "vrata.pdf", bbox_inches="tight")

# --- slika 3: vpliv cakanja (razmerje dvojcek/QPU in Jaccard) --------------------
fig, axs = plt.subplots(1, 2, figsize=(4.8, 2.3))
for c in ["P_twin_csv", "P_twin_csv_noidle", "P_twin_fake"]:
    lab, st = TW[c]
    for opt, fill in zip(opts, ("full", "none")):
        g = main[(main["opt"] == opt) & (main["n"] <= 5)]
        axs[0].plot(g["n"], g[c] / g["P_qpu"], lw=1, ms=4, fillstyle=fill,
                    label=lab if opt == opts[0] else None, **st)
        j = "J_" + c[2:]
        g = main[main["opt"] == opt]
        axs[1].plot(g["n"], g[j], lw=1, ms=4, fillstyle=fill, **st)
for opt, fill in zip(opts, ("full", "none")):
    g = main[main["opt"] == opt]
    axs[1].plot(g["n"], g["J_baseline"], color="black", lw=1, marker="o", ms=3.5, fillstyle=fill,
                label="meja vzorčenja" if opt == opts[0] else None)
axs[0].axhline(1, color="black", lw=0.8)
axs[0].set(xlabel="$n$", ylabel=r"$P_\mathrm{dvojček} / P_\mathrm{QPU}$", xticks=ns[:-1])
axs[1].set(xlabel="$n$", ylabel="uteženi Jaccard z QPU", xticks=ns, ylim=(0.6, 1.0))
for ax in axs:
    ax.grid(alpha=0.3)
h0, l0 = axs[0].get_legend_handles_labels()
h1, l1 = axs[1].get_legend_handles_labels()
fig.legend(h0 + h1, l0 + l1, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.17, 1, 1))
fig.savefig(IMG / "cakanje.pdf", bbox_inches="tight")

# --- vrednosti za tabele ---------------------------------------------------------
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
print("== glavni zagon", MAIN)
cols = ["n", "opt", "two_q", "depth", "ideal_theory", "P_qpu", "P_twin_csv", "P_twin_csv_noidle",
        "P_twin_fake", "J_twin_csv", "J_twin_csv_noidle", "J_twin_fake", "J_baseline"]
print(main[cols].round(3).to_string(index=False))
print("== P_qpu po zagonih")
print(qpu.pivot_table(index=["n", "opt"], columns="run", values="P_qpu").round(3))
print("== klasicna primerjava (zagon 3): (k+1)/P")
for _, r in main.iterrows():
    print(f"n={r.n} opt={r.opt} klasicno={(2**r.n + 1) / 2:.1f} idealno={(r.k + 1) / r.ideal_theory:.1f} "
          f"QPU={(r.k + 1) / r.P_qpu:.1f}")
meta = json.load(open(RES / f"{MAIN}_meta.json"))
print("== kalibracija:", meta["csv"], meta["live_time"])

# --- slika 4 in 5: koraki prevajanja (ena vrata CCZ; stevilo vrat po korakih za vse n) ----
import sys                                                # noqa: E402
import numpy as np                                        # noqa: E402
from qiskit import QuantumCircuit, qpy, transpile         # noqa: E402
from qiskit.circuit.library import ZGate                  # noqa: E402
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh  # noqa: E402
sys.path.insert(0, str(ROOT))
from grover_ibm import grover_circuit                     # noqa: E402
NAT = ["cz", "rz", "sx", "x"]
be = FakeMarrakesh()

# --- (A) ena vrata CCZ skozi korake --------------------------------------------
c = QuantumCircuit(3)
c.append(ZGate().control(2), range(3))
s1 = transpile(c, basis_gates=["cx", "h", "t", "tdg"], optimization_level=1)
s2 = transpile(c, basis_gates=NAT, optimization_level=3, seed_transpiler=1)
s3 = transpile(c, backend=be, optimization_level=3, seed_transpiler=1, initial_layout=[52, 54, 53])


def label(x):
    o = x.count_ops()
    parts = [f"{o[g]} {n}" for g, n in (("cz", "CZ"), ("cx", "CNOT"), ("sx", "√X"), ("rz", "R_Z"),
                                          ("t", "T"), ("tdg", "T†")) if g in o]
    return ", ".join(parts)


steps = [(c, "1) vrata CCZ"),
         (s1, f"2) razstavitev: {label(s1)}"),
         (s2, f"3) osnovna vrata procesorja, povezljivost vsak z vsakim: {label(s2)}"),
         (s3, f"4) na procesorju, kubiti 52–53–54 v verigi: {label(s3)}")]
fig = plt.figure(figsize=(7.0, 3.6))
gs = fig.add_gridspec(3, 2, width_ratios=[1, 3.2], height_ratios=[1, 1, 1], wspace=0.25, hspace=0.35)
axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]),
       fig.add_subplot(gs[1, :]), fig.add_subplot(gs[2, :])]
for ax, (qc, title) in zip(axs, steps):
    qc = qc.copy(); qc.global_phase = 0          # globalna faza je za meritev nepomembna
    qc.draw("mpl", ax=ax, idle_wires=False, fold=-1, scale=0.55)
    ax.set_title(title, loc="left", fontsize=8)
fig.tight_layout()
fig.savefig(IMG / "kaskada_ccz.pdf", bbox_inches="tight")

# --- (B) stevilo vrat po korakih za celotna vezja ------------------------------
meta = json.load(open(RES / f"{MAIN}_meta.json"))
isa = qpy.load(open(RES / f"{MAIN}_circuits.qpy", "rb"))
rows = []
for it, q in zip(meta["items"], isa):
    if it["opt"] != 3:
        continue
    qc, k = grover_circuit(it["n"], it["target"])
    mcz = sum(v for g, v in qc.count_ops().items() if g in ("cz", "ccz", "c3z", "c4z", "c5z"))
    cx = transpile(qc, basis_gates=["cx", "u"], optimization_level=0).count_ops().get("cx", 0)
    dev = q.count_ops().get("cz", 0)
    rows.append((it["n"], mcz, cx, dev))
ns, mcz, cx, dev = map(np.array, zip(*rows))
fig, ax = plt.subplots(figsize=(4.8, 2.4))
w = 0.26
for off, vals, lab, col in [(-w, mcz, "večkrat kontrolirana vrata Z", "tab:gray"),
                            (0, cx, "CNOT (vsak z vsakim)", "tab:blue"),
                            (w, dev, "CZ na procesorju (s SWAP)", "tab:red")]:
    b = ax.bar(ns + off, vals, w, label=lab, color=col)
    ax.bar_label(b, fontsize=6, padding=1)
ax.set(yscale="log", xlabel="$n$", ylabel="število dvokubitnih vrat", xticks=ns, ylim=(1, 6000))
ax.legend(frameon=False, fontsize=7, loc="upper left")
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(IMG / "kaskada_n.pdf", bbox_inches="tight")
print("== stevilo dvokubitnih vrat po korakih (n, MCZ, CNOT, CZ na procesorju):", rows)
