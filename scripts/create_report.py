"""Build the mixed-building PDF from saved simulation outputs (optional report dependencies)."""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

try:
    from scripts.report_parameters import append_parameter_guide
except ModuleNotFoundError:
    from report_parameters import append_parameter_guide

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABELS = {"small_house":"Small house", "apartment_block":"Apartment block", "school":"School", "supermarket":"Supermarket"}


def create_report(results: Path, output: Path, validation_path: Path) -> None:
    comparison = json.loads((results / "comparison.json").read_text())
    if comparison.get("community", {}).get("participant_unit") != "aggregated_building_meter":
        raise ValueError("This report describes the mixed-building model; run that experiment first.")
    summaries = {s["scenario"]: s for s in comparison["scenarios"]}
    if set(summaries) != set("ABCDEF"):
        raise ValueError("Run all six scenarios with --include-priority before building this report.")
    validation = json.loads(validation_path.read_text())
    validation_matches = validation["input_sha256"] == comparison["input_sha256"]
    m = {name:s["metrics"] for name,s in summaries.items()}
    config = summaries["A"]["configuration"]
    community = comparison["community"]
    with (results / "charts/data/building_type_summary.csv").open() as handle:
        type_rows = list(csv.DictReader(handle))
    navy, gold, gray = (colors.HexColor(c) for c in ("#19364F", "#B17922", "#4C5A65"))
    styles = getSampleStyleSheet()
    for name, font, size, leading, color, after in (
        ("Title", "Helvetica-Bold", 28, 33, navy, 15),
        ("Heading", "Helvetica-Bold", 19, 23, navy, 13),
        ("Sub", "Helvetica-Bold", 11.5, 15, gold, 7),
        ("Body", "Helvetica", 10, 14.4, navy, 9),
        ("Caption", "Helvetica", 8.2, 11, gray, 10),
        ("Cell", "Helvetica", 8.8, 11.8, navy, 0),
        ("Code", "Courier", 8.7, 13.5, navy, 12),
    ):
        styles.add(ParagraphStyle(name="Report"+name,fontName=font,fontSize=size,leading=leading,textColor=color,spaceAfter=after))
    content = []
    def p(text, style="Body"):
        content.append(Paragraph(text,styles["Report"+style]))
    def title(number,text): p(f"{number:02d}  {text}","Heading")
    def sub(text):
        content.append(Spacer(1,5))
        p(text,"Sub")
    def table(rows,widths,padding=7):
        cells = [[Paragraph(escape(str(v)),styles["ReportCell"]) for v in row] for row in rows]
        t = Table(cells,colWidths=widths,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EEF2F5")),
                              ("LINEBELOW",(0,0),(-1,0),.8,navy),
                              ("LINEBELOW",(0,1),(-1,-1),.3,colors.HexColor("#D7DFE5")),
                              ("TOPPADDING",(0,0),(-1,-1),padding),("BOTTOMPADDING",(0,0),(-1,-1),padding),
                              ("VALIGN",(0,0),(-1,-1),"TOP")]))
        content.extend([t,Spacer(1,9)])
    def fig(name,caption,width=507):
        from PIL import Image as PILImage
        path=results/"charts"/f"{name}.png"
        w,h=PILImage.open(path).size
        content.append(Image(str(path),width=width,height=width*h/w))
        p(caption,"Caption")
    def page(): content.append(PageBreak())
    def f(value): return f"{value:,.3f}"

    p("SMART GRIDS / MIXED BUILDING COMMUNITY","Sub")
    p("Prosumer community simulator<br/>with heterogeneous buildings","Title")
    p(datetime.now(ZoneInfo("Europe/Rome")).strftime("%d %B %Y"),"Caption")
    p(f'The design contains <b>{community["participant_count"]} aggregate building meters: {community["prosumer_count"]} prosumers and {community["consumer_count"]} consumers</b>. The original PV-equipped buildings remain unchanged; the added consumers have no PV or batteries. There are 75 small houses, 45 blocks, 15 supermarkets and 15 schools, including <b>{community["dwelling_count"]} residential dwelling units</b>. Exactly 55 prosumers own batteries. Each block shares one roof and one meter.')
    p("<b>For the team:</b> pages 11-22 explain every parameter. The demand-response comparison, hourly behavior, worked example and limitations are explained on pages 23-25 when that experiment is present.","Caption")
    sub("Objective and experiment")
    p("Encourage neighborhood P2P electricity trading using price guidance and funded seller rewards, then evaluate storage priority and financial outcomes. Self-balancing, P2P, aggregator and grid settlement preserve energy and cash. Every completed internal trade appears in an hourly Proof-of-Work block.")
    table([["Scenario","Storage","Regulation","Charging priority"],
           ["A","55 owners","Off","Self-consumption first"],["B","55 owners","On","Self-consumption first"],
           ["C","Disabled","Off","Counterfactual"],["D","Disabled","On","Counterfactual"],
           ["E","55 owners","Off","P2P before charging"],["F","55 owners","On","P2P before charging"]],[55,100,90,262])
    sub("Actual result for the new community")
    p(f'With storage, regulation changes P2P energy from <b>{f(m["A"]["p2p_energy_kwh"])} to {f(m["B"]["p2p_energy_kwh"])} kWh</b>, and its share from {m["A"]["p2p_share_pct"]:.3f}% to {m["B"]["p2p_share_pct"]:.3f}%. Cost effects differ by scenario and accounting boundary; all values below come from the recorded execution.')
    p("<b>Evidence boundary:</b> geometry, demand profiles, weather and price history are synthetic engineering assumptions. They are not measured building data. This mixed community is a new experiment and cannot be treated as a like-for-like improvement over the previous residential-only community.")
    page()

    title(2,"Neighborhood layout and building types")
    p("Every row contains 10 original prosumers and 5 new consumers: all ten neighborhoods are mixed. H001-H100 retain their original groups, PV, profiles and battery ownership; H101-H150 are consumer-only meters. The additions comprise 25 houses, 15 blocks, 5 supermarkets and 5 schools, shuffled across groups with five consumers per group.")
    fig("community_map","Figure 1. Seeded community schematic: blue = PV + battery, gold = PV only, pale green and CONSUMER label = no PV/storage. Shapes show building type; F denotes floors. Display columns are shuffled independently of trading order. These are not geographic coordinates or feeder connections.",width=507)
    p("Every neighborhood has five or six battery owners. IDs, types and ownership stay fixed in all scenarios, including C/D where operation is disabled. The map is generated automatically by simulation runs with charts enabled, together with exact cell and group CSV exports.")
    page()

    title(3,"Building geometry and physical sizing")
    p("Type ranges are configurable in <b>config/buildings.py</b> and the buildings section of JSON. The following are proposed engineering defaults, not professor requirements or calibrated building-stock data.")
    table([["Type","Count","Single roof m2","Floors","Daily energy basis"],
           ["Small house",75,"70-150","1-2","8-24 kWh per dwelling"],
           ["Apartment block",45,"180-360","4-10","8-20 kWh per dwelling"],
           ["Supermarket",15,"600-1400","1","0.5-1.1 kWh per m2"],
           ["School",15,"700-1600","2-3","0.08-0.18 kWh per m2"]],[105,42,100,60,200])
    sub("One roof, regardless of height")
    p("Total floor area = roof footprint x floors. Blocks contain 2-4 dwelling units per floor. Their demand basis scales with the total number of units. Commercial/school demand scales with total floor area. Small houses represent one dwelling even when they have two floors.")
    p("Prosumers: PV kW = min(roof m2 x usable share x density, type PV limit). Consumers: PV = 0; battery = none.","Code")
    p("Usable roof fraction is 35-65% and PV density is 0.20 kW/m2. Installed limits are 12 kW for houses, 100 kW for blocks, and 300 kW for supermarkets/schools. Floors and flats do not appear in the PV formula. Adding floors increases the demand basis without creating extra roof area.")
    sub("Actual seeded attributes, averaged per building")
    table([["Type","Battery owners","Dwellings","Mean roof m2","Mean PV kW"]]+[
        [LABELS[r["building_type"]],r["battery_count"],r["dwelling_units"],f(float(r["mean_roof_m2"])),f(float(r["mean_pv_kw"]))]
        for r in type_rows],[125,90,80,110,102])
    p("Battery capacity and charge/discharge power scale by type: 10 kWh / 3 kW for a house, 40 / 12 for a block, 100 / 30 for a supermarket and 60 / 18 for a school. Efficiency and SOC constraints remain identical. These scales can be overridden without changing ownership.")
    page()

    title(4,"Dynamic demand and solar forecasts")
    fig("building_type_profiles","Figure 2. Mean hourly energy per building type, including prosumers and consumers (whose PV is zero). These are not type totals. All scenarios reuse the same inputs; a lower mean PV than the old community does not mean original panels were removed.")
    sub("Hourly activity and weekday/weekend behavior")
    p("Houses and blocks have morning/evening peaks with building-specific timing and hourly variation. Supermarkets retain a base load overnight and add operating load during 07:00-22:00. Schools operate during 08:00-17:00 on weekdays. Weekend daily energy is 105% of weekday baseline for residential types, 90% for supermarkets and 15% for schools; school operating load is disabled on weekends.")
    p("Each building receives a seeded daily multiplier within +/-8%. Geometry stays fixed during the experiment; consumption changes by hour and date. A supplied aggregate demand CSV replaces this synthetic model. Weekends are modeled, but school terms, public holidays and weather-sensitive HVAC loads are not. Weekday school operation in June is an explicit simplification.")
    sub("PV and reference prices")
    p("PV kWh = installed kW x irradiance / 1000 x performance factor x hourly duration, capped at installed capacity. Nighttime production is zero. The default illustrative day starts 15 June 2026 at UTC+02:00, using a daylight curve and seeded cloud factors. Reference prices use only pre-start hourly observations; the default 14-day price history is synthetic. Forecast adapters reject missing coverage, duplicate keys and non-finite inputs.")
    page()

    title(5,"Trading, regulation and transaction record")
    sub("Settlement sequence")
    p("<b>Self-balancing:</b> owner PV serves demand, with eligible battery operations. Consumers have demand only.<br/><b>P2P:</b> seeded buyer/seller encounters within each 15-member mixed group, at the seller ask.<br/><b>Aggregator:</b> lowest asks and highest bids across groups, at midpoint prices.<br/><b>External grid:</b> remaining demand imports at EUR 0.30/kWh and surplus exports at EUR 0.06/kWh. Consumers can buy but never supply electricity. Each trade updates remaining energy.")
    sub("Guidance and funded rewards")
    table([["Opening regulator funds","P2P seller reward"],["Below EUR 1","EUR 0/kWh"],
           ["EUR 1 to below EUR 5","EUR 0.01/kWh"],["EUR 5 or above","EUR 0.02/kWh"]],[280,227])
    p("The fund starts at EUR 0. Guidance blends original offers toward 1.04 x reference for bids and 0.96 x reference for asks, with strength 0.65. Only P2P receives guidance. A full reward reservation is required before a discounted quote. Adjusted ask = guided ask - 50% of reward rate. A successful seller receives trading payment plus full reward. Unaffordable quotes retry original offers without reward; rejected reservations are released.")
    p("Regulated grid purchases and sales each pay EUR 0.01/kWh, collected after trading. New fees become available in the following hour. Opening funds fix that hour's reward tier. There are no internal fees or aggregator/grid seller rewards.")
    sub("Blockchain and conservation")
    p("Ten simulated miners take turns testing SHA-256 nonces inside one process. One block per hour records all completed P2P and aggregator trades exactly once. Each hash begins 000 and references its predecessor; the first references 64 zeros. Validation checks hashes, linkage, transaction contents and journal coverage. The blockchain does not choose energy quantities or prices.")
    p("PV + discharge + purchases = demand + charge + sales.<br/>Stored energy evolves as E_next = E_start + efficiency_c x charge - discharge / efficiency_d. Storage cannot charge and discharge simultaneously, charge from grid/P2P or sell stored energy.")
    page()

    title(6,"P2P results for the mixed community")
    fig("p2p_comparison","Figure 3. Shared-input P2P outcomes. A/B use storage first; C/D disable it; E/F prioritize P2P before charging. B/D/F are regulated.")
    table([["Scenario","P2P kWh","Share %","Available surplus kWh","P2P trades"]]+[
        [n,f(m[n]["p2p_energy_kwh"]),f(m[n]["p2p_share_pct"]),f(m[n]["surplus_available_after_self_balancing_kwh"]),m[n]["p2p_transaction_count"]]
        for n in "ABCDEF"],[55,95,80,180,97])
    p("Primary KPI = 100 x P2P energy / surplus offered after self-balancing. In E/F the denominator includes PV subsequently stored after P2P, so compare absolute energy and raw PV surplus as well as shares. Zero denominators are undefined, not fabricated zeros.")
    for base,reg in (("A","B"),("C","D"),("E","F")):
        delta=m[reg]["p2p_energy_kwh"]-m[base]["p2p_energy_kwh"]
        p(f"{reg} minus {base}: P2P energy difference <b>{delta:+.3f} kWh</b>.")
    p("These differences describe the selected day and heuristic. Guidance cannot create surplus or demand, and no improvement is forced for other settings.")
    page()

    title(7,"Grid exchanges and financial results")
    fig("energy_comparison","Figure 4. Grid settlement and aggregator energy use separate scales to retain visibility of internal volumes.")
    fig("financial_comparison","Figure 5. Building-meter net payments versus building meters plus the regulator, alongside fees, rewards and remaining funds.")
    p("Meter net cost = purchases - sale revenue + fees - rewards. Internal P2P/aggregator payments cancel over meters. Including the regulator subtracts the change in retained funds and equals net external-grid payments. Battery capital, aging, taxes and inventory valuation are excluded.")
    p(f'A to B: meter cost EUR {m["A"]["household_net_cost_eur"]:.2f} to {m["B"]["household_net_cost_eur"]:.2f}; meters plus regulator EUR {m["A"]["community_including_regulator_net_cost_eur"]:.2f} to {m["B"]["community_including_regulator_net_cost_eur"]:.2f}. C to D: meter cost EUR {m["C"]["household_net_cost_eur"]:.2f} to {m["D"]["household_net_cost_eur"]:.2f}. Cost effects need not have the same sign in every pair.')
    page()

    title(8,"Battery operation and available surplus")
    fig("battery_and_surplus","Figure 6. Aggregate storage and surplus denominators. A/B charge before P2P; E/F charge remaining PV after P2P. C/D have no active storage.")
    fig("battery_soc","Figure 7. End-of-hour SOC of the 55 owners in scenario A. Capacity and power differ by building type, while allowed SOC remains 10-90%.")
    p(f'In A, AC charging is {f(m["A"]["battery_charge_kwh"])} kWh, discharge {f(m["A"]["battery_discharge_kwh"])} kWh and conversion losses {f(m["A"]["battery_loss_kwh"])} kWh. Initial stored energy is {f(m["A"]["battery_initial_stored_kwh"])} kWh and final storage {f(m["A"]["battery_final_stored_kwh"])} kWh. Initial inventory is exogenous; final inventory is reported without a monetary valuation.')
    p("The global identity includes PV, demand, imports/exports, initial/final storage and explicit losses. It is checked independently of internal trading payments.")
    page()

    title(9,"Regulator budget and accounting boundary")
    fig("regulator_budget","Figure 8. Closing funds across the day. An hour's opening balance selects the reward tier before that hour's new grid fees are collected.")
    table([["Scenario","Fees EUR","Rewards EUR","Closing fund EUR"]]+[
        [n,f(m[n]["regulator_fee_revenue_eur"]),f(m[n]["regulator_reward_expenditure_eur"]),f(m[n]["regulator_remaining_funds_eur"])] for n in "BDF"],[65,140,140,162])
    p("Closing fund = opening fund + grid fees - eligible P2P rewards. Every movement has a payer and payee. Reservations, releases, reward payments and hourly fund histories are exported. The ledger reconciles with the regulator's fund after each hour.")
    p("Retained fees are a transfer from building meters to the regulator, not money destruction or an external resource cost. They can offset savings from better matching at the meter boundary. Accounts may pay for energy without a starting-cash restriction; only regulator guarantees are constrained by available funding.")
    p("No end-of-day rebate is assumed. Changes to fees, reward tiers or guidance require a separately recorded configuration and rerun. The mixed-building outcomes cannot be attributed solely to regulation by comparing them with the old, physically different residential community.")
    page()

    title(10,"Verification, reproduction and limits")
    sub("Recorded checks")
    if validation_matches:
        p(f'The recorded full suite passed <b>{validation["automated_tests"]["passed"]} tests</b> on {escape(validation["recorded_on"])}. All six saved scenarios passed independent energy, cash and blockchain verification. Tests include unchanged battery ownership, type allocation, one-roof sizing, increased block demand with floors, school weekend reduction, commercial night load, losses/SOC, rewards and forecast cutoff.')
    else:
        p("The validation record does not match these inputs. Rerun tests and exported-result verification before relying on this new report.")
    p(f'Maximum absolute community energy residual: {max(abs(v["energy_reconciliation_error_kwh"]) for v in m.values()):.3g} kWh. Maximum financial residual: {max(abs(v["financial_reconciliation_error_eur"]) for v in m.values()):.3g} EUR. Numerical residuals are checked at explicit tolerances.')
    sub("Run and rebuild")
    p("python -m pip install -r requirements.txt<br/>python -m pytest -q<br/>python main.py --include-priority<br/>python scripts/verify_results.py<br/>python -m pip install -r requirements-report.txt<br/>python scripts/create_report.py","Code")
    p("The simulator requires Python 3.11+ and was exercised on Python 3.14.7. PDF dependencies are optional. Use --config for JSON overrides, --output for separate experiment folders and --no-charts to skip visual exports. The historical residential model remains available through config/residential_baseline.json.")
    sub("Scope and evidence")
    p("The model has no physical feeder limits, voltage/power-flow equations, land parcels, weather-sensitive HVAC, holiday/term calendar, battery aging or investment analysis. Hourly energy settlement and aggregate building meters are simplifying choices. A single synthetic day supports a demonstration, not a statistical or real-world performance claim. Presentations and ZIP packaging remain deferred.")
    p("Sources: supplied project brief and accepted building-meter revision; config/default.json; docs/building_model.md; results/comparison.json and saved chart data; docs/current_validation.json. The original residential comparison and report are preserved as a separate baseline.","Caption")
    p("Input SHA-256: "+comparison["input_sha256"],"Caption")

    def parameter_table(rows, widths):
        table(rows, widths, padding=5)

    expected_pages = append_parameter_guide(config, p, title, sub, parameter_table, page)
    response_path = results / "demand_response_comparison.json"
    if response_path.exists():
        paired = json.loads(response_path.read_text())
        if paired["fixed_input_sha256"] != comparison["input_sha256"]:
            raise ValueError("Demand-response comparison does not match the fixed-demand report inputs.")
        page()
        title(23,"Fixed demand versus PV-aware flexibility")
        p("Only the original 45 PV prosumers without batteries are eligible. Consumers and battery owners retain their hourly loads. C/D keep the ownership-based eligibility even with storage disabled. This is a day-ahead forecast heuristic, not an appliance-level optimizer or a measured behavioral response.")
        fig("demand_response_comparison","Figure 9. Paired scenarios hold PV, buildings, daily energy and market seeds fixed. Load timing changes only. Direct self-consumption excludes battery flows; meter cost includes fees/rewards. Synthetic simulation outputs.",width=380)
        p(f'Shifted energy: <b>{paired["demand_response"]["shifted_energy_kwh"]:.3f} kWh</b> across {paired["demand_response"]["shifted_meter_count"]} meters. All daily demand is retained; unused flexibility stays at its original time.')
        pairs = {(r["scenario"],r["condition"]):r for r in paired["rows"]}
        table([["Scenario", "P2P fixed kWh", "P2P shifted kWh", "Change kWh"]]+[
            [n,f(pairs[n,"Fixed demand"]["p2p_energy_kwh"]),f(pairs[n,"Shifted demand"]["p2p_energy_kwh"]),
             f(pairs[n,"Shifted demand"]["p2p_energy_kwh"]-pairs[n,"Fixed demand"]["p2p_energy_kwh"])]
            for n in summaries],[65,145,145,152])
        decreases = sum(pairs[n,"Shifted demand"]["p2p_energy_kwh"] < pairs[n,"Fixed demand"]["p2p_energy_kwh"]-1e-9 for n in summaries)
        p(f"P2P volume falls in {decreases} of {len(summaries)} recorded pairs. Direct own-PV use rises by the shifted energy. Better self-consumption and maximum P2P are different objectives. Run: python main.py --include-priority --compare-demand-response", "Caption")
        expected_pages += 1
        page()
        title(24,"Team guide: what changes in daily behavior")
        p("Fixed demand follows building use, regardless of sunshine. With demand response, an eligible prosumer plans a limited part of its electricity use around its own PV forecast. Examples might include flexible laundry or controllable cooling, but these are interpretations: the code moves divisible energy rather than scheduling identified appliances.")
        fig("demand_response_hourly","Figure 10. Aggregated forecasts for the 45 eligible prosumers. Both demand curves have the same daily area. The blue curve is unchanged PV. Matching is performed separately for each owner, so surplus in one building cannot justify shifting load in another.")
        sub("How the day-ahead rule works")
        p("<b>1. Select eligible meters.</b> Only PV-equipped prosumers with no battery ownership participate. The 50 consumer-only meters and all 55 battery owners retain their demand. The same 45-meter eligibility applies to every A-F scenario; disabling storage in C/D does not silently add eligible meters.")
        p("<b>2. Find flexible demand and own surplus.</b> For each complete local day, rank permitted source hours by forecast PV deficit. At a source hour, removable energy is the smaller of flexible_fraction x original demand and original demand minus PV. This protects fixed demand and electricity already covered by PV.")
        p("<b>3. Find a receiving hour.</b> Search hours no more than six hours earlier or later, on the same date and inside the allowed schedule. Prefer the largest remaining own-PV surplus. A receiving hour is limited by both unused PV and a maximum 50% increase over its original demand.")
        p("<b>4. Move what fits.</b> Record the source, target and quantity. Subtract and add exactly the same kWh. Any portion without a feasible destination stays at its original time. No cross-day transfers, electricity storage, grid charging or demand cancellation are introduced.")
        expected_pages += 1
        page()
        title(25,"Team guide: worked example and interpretation")
        sub("Example: a house without a battery")
        table([["Quantity", "Illustrative value", "Consequence"],
               ["19:00 demand / PV", "10 / 0 kWh", "At 20% flexibility, at most 2 kWh can leave this hour."],
               ["13:00 demand / PV", "2 / 10 kWh", "Own surplus is 8 kWh, but the 50% rebound limit permits only 1 extra kWh."],
               ["Time distance", "6 hours", "The target is permitted, provided both hours lie inside the configured window."],
               ["Actual transfer", "1 kWh", "Demand becomes 9 kWh at 19:00 and 3 kWh at 13:00; daily energy is unchanged."]],[135,110,262])
        p("The other 1 kWh of potential flexibility stays at 19:00 if no other destination is feasible. Direct own-PV use rises by 1 kWh; available PV surplus falls by 1 kWh. This example explains the algorithm and is not a measurement from a particular simulated building.")
        sub("Building-type assumptions")
        table([["Type", "Flexible fraction", "Allowed hours", "Meaning"],
               ["Small house", "20%", "06:00-23:00", "Most load stays fixed; a bounded share can move."],
               ["Apartment block", "15%", "06:00-23:00", "Aggregate flexibility across flats; no individual appliance model."],
               ["Supermarket", "5%", "07:00-22:00", "Most load remains fixed; refrigeration is not freely rescheduled."],
               ["School", "10%", "08:00-17:00", "Only permitted operating periods; closed weekends do not shift."]],[120,90,110,187])
        p("All percentages are proposed engineering defaults. Actual building-type opening/closing times further constrain nonresidential windows. They require calibration before making claims about real users; comfort, thermal dynamics, task deadlines, occupant consent and device-level minimum run times are not modeled.")
        sub("How to interpret and audit the result")
        p("Higher direct self-consumption can leave less PV for neighbors, reducing P2P kWh even when household imports fall. Always compare absolute P2P volume, its changing surplus denominator, direct own-PV use, grid flows and both cost boundaries. Do not compare a shifted regulated run with an unshifted unregulated run and attribute both changes to regulation.")
        p("Fixed outputs remain in results/; shifted outputs are in results/demand_response/. The paired CSV/JSON is demand_response_comparison. Inspect inputs/demand_shifts.csv and hourly_inputs_baseline.csv in the shifted folder to trace each transfer. The model uses supplied forecasts, not future actual measurements; incomplete calendar days remain unchanged.")
        expected_pages += 1

    def frame(canvas,doc):
        canvas.setStrokeColor(colors.HexColor("#D6DEE5"));canvas.setLineWidth(.5)
        canvas.line(44,45,A4[0]-44,45)
        canvas.setFillColor(gray);canvas.setFont("Helvetica",8)
        canvas.drawString(44,31,"SMART GRIDS / SYNTHETIC MIXED-BUILDING EXPERIMENT")
        canvas.drawRightString(A4[0]-44,31,str(doc.page))
        if doc.page>1:
            canvas.drawString(44,A4[1]-30,"PROSUMER COMMUNITY SIMULATOR")
    output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=52,bottomMargin=58,
                      title="Smart Grids - Mixed Building Community",author="Smart Grids Project").build(content,onFirstPage=frame,onLaterPages=frame)
    reader=PdfReader(str(output))
    if len(reader.pages)!=expected_pages:
        raise ValueError(f"Unexpected layout overflow: {len(reader.pages)} pages, expected {expected_pages}.")
    for index,page_obj in enumerate(reader.pages,1):
        print(f"Page {index}: {len(page_obj.extract_text())} text characters")
    print(f"Report written: {output}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results",type=Path,default=PROJECT_ROOT/"results")
    parser.add_argument("--output",type=Path,default=PROJECT_ROOT/"output/pdf/smart_grids_project_report.pdf")
    parser.add_argument("--validation",type=Path,default=PROJECT_ROOT/"docs/current_validation.json")
    args=parser.parse_args()
    create_report(args.results,args.output,args.validation)
