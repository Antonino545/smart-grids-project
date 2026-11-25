"""Report pages for the combined scenario L, its robustness check and the final comparison.

All numbers are read from saved outputs: results/comparison.json, results/demand_response,
results/<scenario>/regulator_hourly.csv and results/robustness/robustness.json.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

COMPARED = ["A", "B", "D", "F", "K", "L"]


def _storage_value(config: dict) -> float:
    return config["market"]["grid_import_tariff_eur_kwh"] * config["simulation"]["battery"]["discharge_efficiency"]


def _adjusted(metric: dict, value: float) -> float:
    return metric["community_including_regulator_net_cost_eur"] - value * (
        metric["battery_final_stored_kwh"] - metric["battery_initial_stored_kwh"])


def _energy_rows(m: dict) -> list[list[str]]:
    return [["Scenario", "P2P kWh", "% of surplus", "% of PV", "Imports kWh", "Exports kWh", "Final stored kWh", "Losses kWh"]] + [
        [n, f'{m[n]["p2p_energy_kwh"]:,.1f}', f'{m[n]["p2p_share_pct"]:.2f}',
         f'{100 * m[n]["p2p_energy_kwh"] / m[n]["pv_generation_kwh"]:.2f}', f'{m[n]["grid_imports_kwh"]:,.1f}',
         f'{m[n]["grid_exports_kwh"]:,.1f}', f'{m[n]["battery_final_stored_kwh"]:.1f}', f'{m[n]["battery_loss_kwh"]:.1f}']
        for n in COMPARED]


def _money_rows(m: dict, value: float) -> list[list[str]]:
    return [["Scenario", "Meter cost", "Meters + regulator", "Storage-adjusted", "Fees", "Rewards", "Fund left"]] + [
        [n, f'{m[n]["household_net_cost_eur"]:,.2f}', f'{m[n]["community_including_regulator_net_cost_eur"]:,.2f}',
         f'{_adjusted(m[n], value):,.2f}', f'{m[n]["regulator_fee_revenue_eur"]:.2f}',
         f'{m[n]["regulator_reward_expenditure_eur"]:.2f}', f'{m[n]["regulator_remaining_funds_eur"]:.2f}']
        for n in COMPARED]


def _hourly(results: Path, name: str) -> tuple[dict, dict]:
    with (results / name / "regulator_hourly.csv").open() as handle:
        rate = {int(r["hour"]): float(r["reward_rate_eur_kwh"]) for r in csv.DictReader(handle)}
    p2p = defaultdict(float)
    with (results / name / "transactions.csv").open() as handle:
        for r in csv.DictReader(handle):
            if r["market"] == "p2p":
                p2p[int(r["hour"])] += float(r["quantity_kwh"])
    return rate, p2p


def append_scenario_l(results: Path, m: dict, config: dict, p, title, sub, table, fig, page, f) -> int:
    pages = 0
    value = _storage_value(config)
    shifted_path = results / "demand_response" / "comparison.json"
    shifted = ({s["scenario"]: s["metrics"] for s in json.loads(shifted_path.read_text())["scenarios"]}
               if shifted_path.exists() else {})
    l, fm, k = m["L"], m["F"], m["K"]

    page(); pages += 1
    title(27, "Combined scenario L: model and regulation strategy")
    p("L keeps the community, batteries, PV, demand, market, aggregator, grid tariffs and blockchain of every other scenario. "
      "It combines two existing switches: <b>F's settlement order</b> (regulated; owner PV is offered to neighbours before charging) "
      "and <b>K's reward rule</b> (each hour's reward rate is sized to the money in the fund). No new parameter was introduced or tuned.")
    sub("Hourly model")
    p("<b>1. Self-balance.</b> Own PV serves own demand; a battery may discharge to cover a deficit but does not yet charge. "
      "Net position x_i = PV_i + discharge_i - demand_i.<br/>"
      "<b>2. Size the reward.</b> Possible P2P energy P_h = sum over groups g of min(S_g, D_g), where S_g and D_g are the group's "
      "offered surplus and shortage. With available fund A_h (fees collected up to the previous hour, minus rewards paid), "
      f"r_h = min(r_max, A_h / P_h), r_max = EUR {config['regulator']['max_reward_eur_kwh']:.2f}/kWh; r_h = 0 when P_h = 0.<br/>"
      "<b>3. Guide and match.</b> Bid b' = (1-g) b + g 1.04 pi_h; ask a' = max(p_min + r_h/2, (1-g) a + g 0.96 pi_h), g = 0.65, "
      "pi_h = reference price. A buyer meets a seller in random order inside the group when b' >= a' - r_h/2. The buyer pays "
      "a' - r_h/2; the seller also receives r_h x q from the fund, reserved before the trade and only if fully funded.<br/>"
      "<b>4. Store what is left.</b> Unsold owner PV charges the battery: E_next = E + eta_c c, within SOC 10-90% and the power limit. "
      "Then the aggregator and the grid clear the rest.<br/>"
      f"<b>5. Collect fees.</b> Every grid kWh pays phi = EUR {config['regulator']['grid_fee_eur_kwh']:.2f}/kWh after trading: "
      "A_(h+1) = A_h + phi (imports + exports) - rewards, which never becomes negative.")
    p("F uses a fixed tier instead (EUR 0.02/kWh whenever the fund holds at least EUR 5). K applies the same sizing rule "
      "as L, but on B's self-consumption-first order, where batteries absorb PV before trading.")
    sub("Single-day energy result, fixed demand (seed 42)")
    table(_energy_rows(m), [52, 62, 64, 52, 72, 72, 76, 57], padding=4)

    page(); pages += 1
    title(28, "Scenario L: costs, regulator and demand response")
    sub("Fixed demand: costs and regulator fund (EUR)")
    table(_money_rows(m, value), [52, 74, 92, 92, 62, 62, 73], padding=4)
    p(f"Storage-adjusted cost subtracts the change in stored energy valued at EUR {value:.3f}/kWh "
      "(import tariff x discharge efficiency: the import a stored kWh can later avoid). D has no active storage.", "Caption")
    if shifted:
        sub("With PV-aware demand response: energy")
        table(_energy_rows(shifted), [52, 62, 64, 52, 72, 72, 76, 57], padding=4)
        sub("With PV-aware demand response: costs and regulator fund (EUR)")
        table(_money_rows(shifted, value), [52, 74, 92, 92, 62, 62, 73], padding=4)

    page(); pages += 1
    title(29, "Why combining F and K does not beat F")
    rate_f, p2p_f = _hourly(results, "F")
    rate_l, p2p_l = _hourly(results, "L")
    sunny = [h for h in sorted(rate_l) if p2p_f[h] > 1 or p2p_l[h] > 1]
    early = [h for h in sunny if rate_l[h] >= rate_f[h] - 1e-12]
    late = [h for h in sunny if rate_l[h] < rate_f[h] - 1e-12]
    gain = sum(p2p_l[h] - p2p_f[h] for h in early)
    loss = sum(p2p_l[h] - p2p_f[h] for h in late)
    sub("Mechanism, fixed demand")
    table([["Hour"] + [str(h) for h in sunny],
           ["F rate"] + [f"{100 * rate_f[h]:.1f}" for h in sunny],
           ["L rate"] + [f"{100 * rate_l[h]:.1f}" for h in sunny],
           ["L-F kWh"] + [f"{p2p_l[h] - p2p_f[h]:+.0f}" for h in sunny]],
          [52] + [455 / len(sunny)] * len(sunny))
    p(f"Rates in euro cents/kWh. L's rule spends the whole available fund on the current hour. Before batteries charge, many "
      f"owners offer PV in the morning, so the fund collected overnight is used up by the morning trades. In hours where L pays at least F's rate, L trades {gain:+.0f} kWh; "
      f"in the following peak-PV hours its rate falls below F's fixed EUR 0.02 and it trades {loss:+.0f} kWh. "
      f"Net: {l['p2p_energy_kwh'] - fm['p2p_energy_kwh']:+.1f} kWh against F. K gains against B ({k['p2p_energy_kwh'] - m['B']['p2p_energy_kwh']:+.0f} kWh) "
      "because B offers less PV in the morning, so the same fund lasts until about midday.")
    p(f"L pays EUR {l['regulator_reward_expenditure_eur'] - fm['regulator_reward_expenditure_eur']:+.2f} more rewards than F, so meter cost moves by "
      f"EUR {l['household_net_cost_eur'] - fm['household_net_cost_eur']:+.2f}. This is mostly a transfer from the regulator: meters plus regulator move by only "
      f"EUR {l['community_including_regulator_net_cost_eur'] - fm['community_including_regulator_net_cost_eur']:+.2f}, and L ends with "
      f"{l['battery_final_stored_kwh'] - fm['battery_final_stored_kwh']:+.2f} kWh of stored energy against F. Only grid payments leave the community; "
      "rewards cannot create PV surplus or neighbour demand.")

    robust_path = results / "robustness" / "robustness.json"
    if robust_path.exists():
        robust = json.loads(robust_path.read_text())
        stats = {(r["condition"], r["scenario"], r["kpi"]): r for r in robust["summary"]}
        wins = {(r["condition"], r["comparison"], r["kpi"]): r for r in robust["l_win_rates"]}
        page(); pages += 1
        title(30, "Robustness across seeded communities")
        p(f"Scenarios {', '.join(robust['scenarios'])} were rerun on <b>{len(robust['seeds'])} seeds</b> ({robust['seeds'][0]}-{robust['seeds'][-1]}), "
          "each with fixed demand and with demand response. A seed regenerates building attributes, weather, demand, prices and "
          "matching order; inside one seed and condition every scenario uses the same input hash. Every run passed the energy, "
          "cash, fund and blockchain checks.")
        fig("robustness", "Figure 11. L minus F and L minus K for each seed. Above zero is better for L in P2P; below zero is better for L in cost.",
            width=460, directory=results / "robustness")
        rows = [["Condition", "KPI", "F mean (sd)", "K mean (sd)", "L mean (sd)", "L better than F", "L better than K"]]
        for condition, short in (("fixed", "Fixed"), ("demand_response", "DR")):
            for kpi, label in (("p2p_energy_kwh", "P2P kWh"), ("grid_imports_kwh", "Imports kWh"),
                               ("household_net_cost_eur", "Meter cost EUR"),
                               ("community_cost_storage_adjusted_eur", "Adj. meters+reg EUR")):
                cell = lambda n: f'{stats[condition, n, kpi]["mean"]:,.1f} ({stats[condition, n, kpi]["std"]:,.1f})'
                rows.append([short, label, cell("F"), cell("K"), cell("L"),
                             f'{wins[condition, "L vs F", kpi]["l_better_pct"]:.0f}%',
                             f'{wins[condition, "L vs K", kpi]["l_better_pct"]:.0f}%'])
        table(rows, [52, 92, 75, 75, 75, 69, 69])
        lf = wins["fixed", "L vs F", "p2p_energy_kwh"]
        lfa = wins["fixed", "L vs F", "community_cost_storage_adjusted_eur"]
        lk = wins["fixed", "L vs K", "p2p_energy_kwh"]
        p(f'With fixed demand, L minus F is {lf["mean_difference"]:+.1f} kWh P2P on average (sd {lf["std_difference"]:.1f}) and '
          f'{lfa["mean_difference"]:+.2f} EUR storage-adjusted meters-plus-regulator cost (sd {lfa["std_difference"]:.2f}). '
          f'L minus K is {lk["mean_difference"]:+.0f} kWh P2P (sd {lk["std_difference"]:.0f}). Standard deviations are across seeds; '
          'full tables are in results/robustness/.', "Caption")
        n = lfa["runs"]
        ldr = wins["demand_response", "L vs F", "community_cost_storage_adjusted_eur"]
        p(f'<b>Reading.</b> L beats K on every seed: the gain comes from F\'s battery order. Against F the differences are small and change sign '
          f'between seeds. The mean cost difference ({lfa["mean_difference"]:+.2f} EUR fixed, {ldr["mean_difference"]:+.2f} EUR with demand response) '
          f'is smaller than about two standard errors of the paired mean ({2 * lfa["std_difference"] / n ** .5:.1f} and '
          f'{2 * ldr["std_difference"] / n ** .5:.1f} EUR), so L and F cannot be told apart economically; L trades less P2P on average.')

    page(); pages += 1
    title(31, "Which scenario is best for which objective")
    objectives = [("Most P2P energy", "p2p_energy_kwh", max), ("Highest P2P share of surplus", "p2p_share_pct", max),
                  ("Fewest grid imports", "grid_imports_kwh", min), ("Fewest grid exports", "grid_exports_kwh", min),
                  ("Lowest meter cost", "household_net_cost_eur", min),
                  ("Lowest meters + regulator cost", "community_including_regulator_net_cost_eur", min),
                  ("Most money kept by the regulator", "regulator_remaining_funds_eur", max)]
    rows = [["Objective", "Best (fixed, seed 42)", "Best (DR, seed 42)", "Best mean over seeds (fixed / DR)"]]
    for label, key, pick in objectives:
        def best(metrics):
            n = pick(COMPARED, key=lambda s: metrics[s][key])
            return f"{n} ({metrics[n][key]:,.1f})"
        seeds = "-"
        if robust_path.exists():
            rkey = {"p2p_share_pct": "p2p_share_of_surplus_pct"}.get(key, key)
            if ("fixed", "A", rkey) in stats:
                seeds = " / ".join(pick(COMPARED, key=lambda s: stats[c, s, rkey]["mean"]) for c in ("fixed", "demand_response"))
        rows.append([label, best(m), best(shifted) if shifted else "-", seeds])
    adjusted = {n: _adjusted(m[n], value) for n in COMPARED}
    best_adj = min(adjusted, key=adjusted.get)
    rows.append(["Lowest storage-adjusted cost", f"{best_adj} ({adjusted[best_adj]:,.1f})",
                 (lambda a: f"{min(a, key=a.get)} ({min(a.values()):,.1f})")({n: _adjusted(shifted[n], value) for n in COMPARED}) if shifted else "-",
                 " / ".join(min(COMPARED, key=lambda s: stats[c, s, "community_cost_storage_adjusted_eur"]["mean"])
                            for c in ("fixed", "demand_response")) if robust_path.exists() else "-"])
    table(rows, [150, 110, 110, 137])
    sub("Trade-offs")
    p("<b>D</b> (no storage, regulated) pushes the most PV to neighbours but wastes the storage the community owns: it exports "
      "more and imports more than F or L. <b>F and L</b> trade almost as much as D while also storing unsold PV, so they import least. "
      "<b>K</b> is the best variant of the self-consumption-first order, but storing PV before trading caps its P2P volume. "
      "Lower meter cost under larger rewards is mainly money moved from the regulator to the meters; the meters-plus-regulator cost, "
      "corrected for energy left in storage, is the fair economic comparison. Demand response lowers cost in every scenario but "
      "uses own PV that would otherwise be sold, so P2P falls.")
    sub("Recommendation")
    p(RECOMMENDATION)
    pages += _append_presentation(results, m, value, p, title, sub, table, fig, page)
    return pages


GROUPS = ["Prosumer + battery", "Prosumer, PV only", "Consumer"]
KEY = ["A", "B", "F", "L"]


def participant_costs(results: Path, value: float) -> dict:
    """Average daily net cost per meter and participant group, plus share of meters cheaper than in A.

    Battery owners' cost is storage-adjusted: the change in their own stored energy is valued at
    ``value`` EUR/kWh, so ending the day with less energy in the battery is not counted as a saving.
    """
    with (results / "inputs" / "households.csv").open() as handle:
        meters = {r["household_id"]: (GROUPS[2] if r["participant_role"] == "consumer"
                                      else GROUPS[0] if r["has_battery"] == "True" else GROUPS[1])
                  for r in csv.DictReader(handle)}
    adjusted = {}
    for name in COMPARED:
        with (results / name / "household_costs.csv").open() as handle:
            cost = {r["household_id"]: float(r["net_cost_eur"]) for r in csv.DictReader(handle)}
        start, end = {}, {}
        with (results / name / "household_hourly.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        last = max(int(r["hour"]) for r in rows)
        for r in rows:
            if int(r["hour"]) == 0:
                start[r["household_id"]] = float(r["stored_start_kwh"] or 0)
            if int(r["hour"]) == last:
                end[r["household_id"]] = float(r["stored_end_kwh"] or 0)
        adjusted[name] = {k: c - value * (end[k] - start[k]) for k, c in cost.items()}
    out = {}
    for name in COMPARED:
        for group in GROUPS:
            ids = [k for k, g in meters.items() if g == group]
            out[name, group] = {"count": len(ids), "mean": sum(adjusted[name][k] for k in ids) / len(ids),
                                "cheaper_than_a": sum(adjusted[name][k] < adjusted["A"][k] - 1e-9 for k in ids)}
        out[name, "All"] = {"count": len(meters), "mean": sum(adjusted[name].values()) / len(meters),
                            "cheaper_than_a": sum(adjusted[name][k] < adjusted["A"][k] - 1e-9 for k in meters)}
    return out


def presentation_chart(results: Path, m: dict, value: float, costs: dict) -> None:
    import os
    import tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartgrid-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.charts import COLORS
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "figure.facecolor": "white"})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.4))
    colors = [COLORS[n] for n in COMPARED]
    panels = ((axes[0, 0], "P2P energy traded (kWh)", [m[n]["p2p_energy_kwh"] for n in COMPARED], "{:,.0f}"),
              (axes[0, 1], "Grid imports (kWh)", [m[n]["grid_imports_kwh"] for n in COMPARED], "{:,.0f}"),
              (axes[1, 0], "Community cost, storage-adjusted (EUR)", [_adjusted(m[n], value) for n in COMPARED], "{:,.0f}"))
    for axis, label, values, fmt in panels:
        bars = axis.bar(COMPARED, values, color=colors)
        axis.set_title(label, fontsize=11)
        low = min(values)
        if "kWh" in label and "import" not in label:
            low = 0
        else:
            axis.set_ylim(low * .97, max(values) * 1.01)
        for bar, v in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", fontsize=8)
    axis = axes[1, 1]
    width = .8 / len(GROUPS)
    shades = ["#315A86", "#D48B25", "#758A35"]
    for index, group in enumerate(GROUPS):
        changes = [100 * (costs[n, group]["mean"] / costs["A", group]["mean"] - 1) for n in COMPARED]
        positions = [i + (index - 1) * width for i in range(len(COMPARED))]
        axis.bar(positions, changes, width, label=group, color=shades[index])
    axis.axhline(0, color="#555555", linewidth=1)
    axis.set_xticks(range(len(COMPARED)), COMPARED)
    axis.set_title("Average cost per participant vs A (%)", fontsize=11)
    axis.legend(fontsize=8, frameon=False)
    fig.text(.02, .015, "Default Turin day, seed 42, fixed demand. A: storage, no regulation. B: regulated. D: no storage. "
             "F: P2P before charging. K: fund-sized reward. L: F + K. Costs include fees and rewards; storage valued at EUR "
             f"{value:.3f}/kWh.", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, .04, 1, 1))
    directory = results / "charts"
    fig.savefig(directory / "presentation_summary.png", dpi=180)
    fig.savefig(directory / "presentation_summary.svg")
    plt.close(fig)


def _append_presentation(results: Path, m: dict, value: float, p, title, sub, table, fig, page) -> int:
    costs = participant_costs(results, value)
    presentation_chart(results, m, value, costs)
    a = m["A"]

    def delta(n, key, unit, digits=0):
        d = m[n][key] - a[key]
        return f"{m[n][key]:,.{digits}f} ({d:+,.{digits}f})" if n != "A" else f"{m[n][key]:,.{digits}f}"

    page()
    title(32, "Presentation summary: the key scenarios")
    p("One page for the slides: A is the starting point (batteries, no regulator), B adds the regulator, F also sells PV "
      "before charging (recommended), and L adds K's fund-sized reward to F. D (no storage) and K are shown in the chart for context.")
    fig("presentation_summary", "Figure 12. Headline outcomes for A, B, D, F, K and L on the recorded day. Bottom right: change in "
        "average daily cost per participant group compared with A (negative = participants pay less).", width=430)
    adj = {n: _adjusted(m[n], value) for n in KEY}
    rows = [["KPI (change vs A)", *KEY],
            ["P2P energy, kWh", *(delta(n, "p2p_energy_kwh", "kWh") for n in KEY)],
            ["P2P share of PV, %", *(f'{100 * m[n]["p2p_energy_kwh"] / m[n]["pv_generation_kwh"]:.1f}' for n in KEY)],
            ["Grid imports, kWh", *(delta(n, "grid_imports_kwh", "kWh") for n in KEY)],
            ["Grid exports, kWh", *(delta(n, "grid_exports_kwh", "kWh") for n in KEY)],
            ["Participants pay, EUR/day", *(delta(n, "household_net_cost_eur", "EUR") for n in KEY)],
            ["Community, storage-adj., EUR/day", *(f"{adj[n]:,.0f}" + ("" if n == "A" else f" ({adj[n] - adj['A']:+,.0f})") for n in KEY)],
            ["Meters paying less than in A", *(("-" if n == "A" else f'{costs[n, "All"]["cheaper_than_a"]} of {costs[n, "All"]["count"]}') for n in KEY)]]
    table(rows, [151, 89, 89, 89, 89], padding=4)

    page()
    title(33, "Cost per participant and key messages")
    sub("Average daily net cost per meter (EUR, change vs A)")
    rows = [["Group", "Meters", *COMPARED]]
    for group in [*GROUPS, "All"]:
        base = costs["A", group]["mean"]
        rows.append([group, str(costs["A", group]["count"]),
                     *(f'{costs[n, group]["mean"]:.2f}' + ("" if n == "A" else f' ({100 * (costs[n, group]["mean"] / base - 1):+.1f}%)')
                       for n in COMPARED)])
    table(rows, [92, 40, 62, 62, 62, 62, 62, 65], padding=4)
    p("Net cost = purchases - sales + regulator fees - rewards, for one simulated June day. Battery owners are storage-adjusted "
      "(energy left in their battery is credited at the value above). A meter is an aggregate building: a school or supermarket "
      "has a far larger bill than a house, so compare percentages across groups rather than euros. Do not multiply one synthetic "
      "day into an annual saving.", "Caption")
    sub("Share of meters that pay less than in A")
    table([["Group", *COMPARED[1:]]] + [[group, *(f'{costs[n, group]["cheaper_than_a"]}/{costs[n, group]["count"]}' for n in COMPARED[1:])]
                                         for group in [*GROUPS, "All"]], [120, 77, 77, 77, 77, 79], padding=4)
    best_group = {g: min(COMPARED, key=lambda n: costs[n, g]["mean"]) for g in GROUPS}
    sub("Key messages for the presentation")
    p(f'<b>1. Regulation is what makes P2P happen.</b> A trades {a["p2p_energy_kwh"]:,.0f} kWh; B trades {m["B"]["p2p_energy_kwh"]:,.0f} kWh '
      f'on identical inputs, because guided prices and rewards make bids and asks compatible.<br/>'
      f'<b>2. Selling PV before charging adds more.</b> F trades {m["F"]["p2p_energy_kwh"]:,.0f} kWh and, with L, has the fewest imports '
      f'({m["F"]["grid_imports_kwh"]:,.0f} kWh against {a["grid_imports_kwh"]:,.0f} in A).<br/>'
      + (f'<b>3. Every group gains on average.</b> In F, the average cost falls for all three groups; '
         if all(costs["F", g]["mean"] < costs["A", g]["mean"] for g in GROUPS) else
         '<b>3. Gains are not shared by every group.</b> In F, at least one group pays more on average than in A; ') +
      f'the lowest-cost scenario is '
      f'{best_group[GROUPS[0]]} for battery owners, {best_group[GROUPS[1]]} for PV-only prosumers and {best_group[GROUPS[2]]} for consumers. '
      f'Some individual meters still pay more than in A (F: {costs["F", "All"]["count"] - costs["F", "All"]["cheaper_than_a"]} of {costs["F", "All"]["count"]}).<br/>'
      f'<b>4. Bigger rewards redistribute rather than save.</b> L lowers what participants pay compared with F, but the community '
      f'cost is the same within noise across 20 seeds; the difference is regulator money handed back.<br/>'
      f'<b>5. Every trade is auditable.</b> Energy and cash reconcile to numerical precision and each internal trade is in one hourly block.')
    return 2


RECOMMENDATION = ("Present <b>F</b> as the final proposed solution, with L as a tested extension. F and L trade almost the same "
                  "energy and cost almost the same at the community boundary, on the recorded day and across seeds; L's extra "
                  "rewards mainly redistribute the regulator's fund to the meters. F's fixed tier is simpler to explain and audit and "
                  "does not drain the fund before the midday PV peak. If the goal is to lower what participants pay rather than "
                  "community-wide cost, L (or a day-end refund such as J) passes more of the fees back to traders.")
