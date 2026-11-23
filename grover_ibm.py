"""Groverjev algoritem: pomozne funkcije za zvezek grover_ibm.ipynb.

Vezje: Grover z oraclom za znano oznaceno stanje (X + MCZ, brez pomoznih kubitov).
Dvojcki: vsi uporabljajo NoiseModel.from_backend (Qiskit Aer) in cakanje kubitov kot `delay`,
razlikujejo se le po kalibraciji: posnetek zive kalibracije ob gradnji vezij, CSV s platforme
IBM ali FakeMarrakesh. Metrike: P(oznaceno stanje) in utezeni Jaccard.

Pricakuje (neobvezno) .env z IBM_KEY (API kljuc IBM Quantum). Zahteva: qiskit, qiskit-aer, qiskit-ibm-runtime.
"""
import csv
import glob
import math
import os

from qiskit import QuantumCircuit
from qiskit.circuit.library import ZGate

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ----------------------------------------------------------------------------- vezje
def grover_circuit(n, target):
    """Groverjevo vezje za en oznacen element. target: niz bitov, target[0] = kubit n-1."""
    N = 2 ** n
    k = max(1, math.floor(math.pi / 4 * math.sqrt(N)))
    qc = QuantumCircuit(n, name=f"grover_n{n}")
    qc.h(range(n))
    zeros = [i for i in range(n) if target[n - 1 - i] == "0"]
    for _ in range(k):
        if zeros:                      # oracle: X na kubitih, kjer ima target ničlo
            qc.x(zeros)                # (qc.x([]) vrze CircuitError, zato pogoj)
        qc.append(ZGate().control(n - 1), list(range(n)))
        if zeros:
            qc.x(zeros)
        qc.h(range(n))                 # difuzija
        qc.x(range(n))
        qc.append(ZGate().control(n - 1), list(range(n)))
        qc.x(range(n))
        qc.h(range(n))
    qc.measure_all()
    return qc, k


def ideal_probability(n, k):
    N = 2 ** n
    return math.sin((2 * k + 1) * math.asin(1 / math.sqrt(N))) ** 2


def two_qubit_count(qc):
    ops = qc.count_ops()
    return sum(v for name, v in ops.items() if name in ("cz", "ecr", "cx"))


# ----------------------------------------------------------------------------- metrike
def normalize(counts):
    s = sum(counts.values())
    return {k: v / s for k, v in counts.items()}


def weighted_jaccard(p, q):
    keys = set(p) | set(q)
    num = sum(min(p.get(x, 0.0), q.get(x, 0.0)) for x in keys)
    den = sum(max(p.get(x, 0.0), q.get(x, 0.0)) for x in keys)
    return num / den if den else 0.0


# ----------------------------------------------------------------------------- dvojcki
#
# Vsi dvojcki uporabljajo isto standardno konstrukcijo (NoiseModel.from_backend iz Qiskit Aer)
# in se razlikujejo le po izvoru kalibracijskih podatkov: posnetek zive kalibracije ob gradnji
# vezij, CSV s platforme IBM, ali FakeMarrakesh (star posnetek v qiskit_ibm_runtime).
# NoiseModel.from_backend:
#   - depolarizacijo izbere tako, da je skupna napaka (relaksacija + depolarizacija) enaka
#     sporoceni napaki vrat (relaksacija ni steta dvakrat),
#   - doda termicno relaksacijo na ukaze `delay` (cakanje kubitov), ce so vezja razporejena
#     (schedule_alap).
CSV_COLUMNS = ["Qubit", "T1 (us)", "T2 (us)", "Readout assignment error", "Prob meas0 prep1",
               "Prob meas1 prep0", "Readout length (ns)", "ID error", "Single-qubit gate length (ns)",
               "√x (sx) error", "Pauli-X error", "CZ error", "Gate length (ns)"]


def save_calibration_csv(backend, path):
    """Shrani trenutno kalibracijo backenda v CSV z enakimi stolpci kot CSV s platforme IBM.

    Tako lahko dvojcek iz zive kalibracije kadarkoli ponovno zgradimo s csv_backend.
    Vrne cas zadnje posodobitve kalibracije (last_update_date).
    """
    props = backend.properties()

    def val(fn, *a, scale=1.0):
        try:
            v = fn(*a)
        except Exception:
            return ""
        return "" if v is None else v * scale

    rows = {q: {"Qubit": q} for q in range(backend.num_qubits)}
    for q, row in rows.items():
        qp = props.qubit_property(q)
        row["T1 (us)"] = val(props.t1, q, scale=1e6)
        row["T2 (us)"] = val(props.t2, q, scale=1e6)
        row["Readout assignment error"] = val(props.readout_error, q)
        row["Readout length (ns)"] = val(props.readout_length, q, scale=1e9)
        row["Prob meas0 prep1"] = qp["prob_meas0_prep1"][0] if "prob_meas0_prep1" in qp else ""
        row["Prob meas1 prep0"] = qp["prob_meas1_prep0"][0] if "prob_meas1_prep0" in qp else ""
        row["ID error"] = val(props.gate_error, "id", [q])
        row["√x (sx) error"] = val(props.gate_error, "sx", [q])
        row["Pauli-X error"] = val(props.gate_error, "x", [q])
        row["Single-qubit gate length (ns)"] = val(props.gate_length, "sx", [q], scale=1e9)
        row["CZ error"], row["Gate length (ns)"] = [], []
    seen = set()
    for g in props.gates:                     # kot v CSV IBM: par zapisan v vrstici obeh kubitov
        if g.gate != "cz" or frozenset(g.qubits) in seen:
            continue
        seen.add(frozenset(g.qubits))
        a, b = g.qubits
        err = val(props.gate_error, "cz", [a, b])
        length = val(props.gate_length, "cz", [a, b], scale=1e9)
        for q, other in ((a, b), (b, a)):
            if err != "":
                rows[q]["CZ error"].append(f"{other}:{err}")
            if length != "":
                rows[q]["Gate length (ns)"].append(f"{other}:{length:g}")
    for row in rows.values():
        row["CZ error"] = ";".join(row["CZ error"])
        row["Gate length (ns)"] = ";".join(row["Gate length (ns)"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows.values())
    return props.last_update_date


def csv_backend(path, base=None):
    """Fake backend (privzeto FakeMarrakesh) z lastnostmi, prepisanimi iz kalibracijskega CSV.

    Iz CSV vzame T1, T2, napake in trajanja vrat (sx, x, id, cz) ter odcitavanja (asimetricno:
    P(1|0), P(0|1)). Povezljivost, nabor vrat in manjkajoce vrednosti ostanejo iz `base`.
    """
    from qiskit.providers import QubitProperties
    from qiskit.transpiler import InstructionProperties
    if base is None:
        from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
        base = FakeMarrakesh()
    target = base.target

    def num(r, col):
        try:
            return float(r.get(col, ""))
        except ValueError:
            return None

    def per_pair(r, col):
        return {int(j): float(v) for j, v in (x.split(":") for x in r.get(col, "").split(";") if x)}

    def update(gate, qargs, duration, error, **extra):
        old = target[gate][qargs]
        props = InstructionProperties(duration=old.duration if duration is None else duration,
                                      error=old.error if error is None else error)
        for k, v in extra.items():
            setattr(props, k, v)
        target.update_instruction_properties(gate, qargs, props)

    qprops = list(target.qubit_properties)
    incomplete = set()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        q = int(r["Qubit"])
        if q >= target.num_qubits:
            continue
        t1, t2 = num(r, "T1 (us)"), num(r, "T2 (us)")
        if t1 is None or t2 is None:
            incomplete.add(q)
        old = qprops[q]
        qprops[q] = QubitProperties(t1=old.t1 if t1 is None else t1 * 1e-6,
                                    t2=old.t2 if t2 is None else t2 * 1e-6,
                                    frequency=old.frequency)
        len1 = num(r, "Single-qubit gate length (ns)")
        len1 = None if len1 is None else len1 * 1e-9
        for gate, col in (("sx", "√x (sx) error"), ("x", "Pauli-X error"), ("id", "ID error")):
            err = num(r, col)
            if err is None:
                incomplete.add(q)
            if (q,) in target[gate]:
                update(gate, (q,), len1, err)
        p10, p01 = num(r, "Prob meas1 prep0"), num(r, "Prob meas0 prep1")
        if p10 is None or p01 is None:
            incomplete.add(q)
        else:
            rl = num(r, "Readout length (ns)")
            # Aer ob prisotnosti teh atributov uporabi asimetricno napako odcitavanja
            update("measure", (q,), None if rl is None else rl * 1e-9, (p10 + p01) / 2,
                   prob_meas1_prep0=p10, prob_meas0_prep1=p01)
        errs, lens = per_pair(r, "CZ error"), per_pair(r, "Gate length (ns)")
        for j, e in errs.items():
            for qargs in ((q, j), (j, q)):
                if qargs in target["cz"]:
                    update("cz", qargs, lens[j] * 1e-9 if j in lens else None, e)
    target.qubit_properties = qprops
    if incomplete:
        print(f"[CSV] kubiti z manjkajocimi podatki (manjkajoce vrednosti iz {base.name}): "
              f"{sorted(incomplete)}")
    return base


def schedule_alap(circuits, target):
    """Razporedi (ALAP) ze prevedena vezja: cakanje kubitov postane ukaz `delay`.

    Vrata in postavitev se ne spremenijo; vezja za QPU naj ostanejo nerazporejena.
    """
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDelay
    return PassManager([ALAPScheduleAnalysis(target=target), PadDelay(target=target)]).run(circuits)


def twin_from_backend(backend):
    """Dvojcek iz kalibracije backenda. Vrne (simulator, target); vezja pred zagonom razporedi:

        sim, tgt = twin_from_backend(backend)
        counts = run_counts(sim, schedule_alap(isa_list, tgt), shots, seed)
    """
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel
    return AerSimulator(noise_model=NoiseModel.from_backend(backend)), backend.target


def csv_twin(path, base=None):
    """Dvojcek iz kalibracijskega CSV (s platforme IBM ali iz save_calibration_csv)."""
    return twin_from_backend(csv_backend(path, base))


SOURCES = ["ideal", "twin_backend", "twin_backend_b", "twin_csv", "twin_csv_noidle", "twin_fake", "qpu"]
TWINS = ["twin_backend", "twin_csv", "twin_csv_noidle", "twin_fake"]     # primerjava s QPU (Jaccard)


def find_csv(backend_name):
    files = sorted(glob.glob(f"calibration/{backend_name}_calibrations_*.csv"))
    return files[-1] if files else None


def run_counts(sim, circuits, shots, seed):
    res = sim.run(circuits, shots=shots, seed_simulator=seed).result()
    return [res.get_counts(i) for i in range(len(circuits))]


# ----------------------------------------------------------------------------- procesor
def get_backend(name):
    """Poveze se z IBM Quantum in vrne (service, backend) za procesor z imenom `name`."""
    from qiskit_ibm_runtime import QiskitRuntimeService
    kw = {"instance": "auto"}
    token = os.environ.get("IBM_KEY")    # iz .env; brez njega: racun, shranjen v ~/.qiskit
    if token:
        kw.update(channel="ibm_quantum_platform", token=token)
    service = QiskitRuntimeService(**kw)
    names = [b.name for b in service.backends(simulator=False, operational=True)]
    print("[backendi]", names)
    if name not in names:
        raise RuntimeError(f"{name} ni na voljo; izberi enega od {names}")
    return service, service.backend(name)
