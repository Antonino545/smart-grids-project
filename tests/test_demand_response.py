"""Flexibility must change timing only, never invent PV or remove daily demand."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from config.demand_response import DemandResponseSettings
from config.settings import SimulationSettings
from src.demand_response import shift_demand
from src.forecasting import HourlyInput, generate_inputs
from src.households import generate_households


def example(kind="small_house", day=15):
    h = replace(generate_households(SimulationSettings())[0], household_id="example", battery=None,
                building_type=kind, participant_role="prosumer", pv_capacity_kw=10)
    start = datetime(2026,6,day,tzinfo=timezone.utc)
    rows = [HourlyInput(i,(start+timedelta(hours=i)).isoformat(),h.household_id,0,
                        10 if i==13 else 0, 10 if i==19 else 2 if i==13 else 0,
                        .2,"forecast","forecast","history") for i in range(24)]
    return h, rows


def test_daily_energy_pv_and_hourly_bounds_with_auditable_transfers():
    h, rows = example()
    adjusted, journal = shift_demand([h],rows,DemandResponseSettings(enabled=True))
    assert sum(r.demand_kwh for r in adjusted) == sum(r.demand_kwh for r in rows)
    assert [r.pv_kwh for r in adjusted] == [r.pv_kwh for r in rows]
    assert len(journal)==1 and journal[0]["quantity_kwh"]==pytest.approx(1)
    assert adjusted[19].demand_kwh==9 and adjusted[13].demand_kwh==3
    assert min(r.demand_kwh for r in adjusted)>=0
    assert rows[19].demand_kwh==10  # Inputs are immutable.
    gain=sum(min(r.pv_kwh,r.demand_kwh) for r in adjusted)-sum(min(r.pv_kwh,r.demand_kwh) for r in rows)
    assert gain==pytest.approx(sum(j["quantity_kwh"] for j in journal))
    assert (adjusted,journal)==shift_demand([h],rows,DemandResponseSettings(enabled=True))


@pytest.mark.parametrize("change", [{"participant_role":"consumer","pv_capacity_kw":0},
                                     {"battery":SimulationSettings().battery}, {"pv_capacity_kw":0}])
def test_ownership_and_roles_exclude_ineligible_meters(change):
    h, rows=example()
    assert shift_demand([replace(h,**change)],rows,DemandResponseSettings(enabled=True))==(rows,[])


def test_distance_operating_hours_disabled_and_partial_days():
    h, rows=example()
    assert shift_demand([h],rows,DemandResponseSettings())==(rows,[])
    assert shift_demand([h],rows,DemandResponseSettings(enabled=True,max_shift_hours=5))==(rows,[])
    assert shift_demand([h],rows[:20],DemandResponseSettings(enabled=True))==(rows[:20],[])
    school, school_rows=example("school")
    assert shift_demand([school],school_rows,DemandResponseSettings(enabled=True))==(school_rows,[])
    school, sunday=example("school",day=21)
    sunday=[replace(r,pv_kwh=10 if r.hour==10 else 0,
                    demand_kwh=2 if r.hour==10 else 10 if r.hour==16 else 0) for r in sunday]
    assert shift_demand([school],sunday,DemandResponseSettings(enabled=True))==(sunday,[])
    from config.buildings import BuildingSettings
    buildings=BuildingSettings()
    open_weekend=replace(buildings,types={**buildings.types,"school":replace(buildings.types["school"],weekend_open=True)})
    assert shift_demand([school],sunday,DemandResponseSettings(enabled=True),open_weekend)[1]


def test_all_eligible_meters_preserve_every_calendar_day_and_other_meters():
    settings=SimulationSettings(hours=48)
    hs=generate_households(settings)
    rows=generate_inputs(hs,settings)
    adjusted,journal=shift_demand(hs,rows,DemandResponseSettings(enabled=True))
    assert journal
    lookup={h.household_id:h for h in hs}
    from collections import defaultdict
    totals=defaultdict(lambda:[0.,0.])
    for before,after in zip(rows,adjusted):
        totals[(before.household_id,before.timestamp[:10])][0]+=before.demand_kwh
        totals[(before.household_id,before.timestamp[:10])][1]+=after.demand_kwh
        if lookup[before.household_id].has_battery:
            assert before==after
    assert all(abs(a-b)<1e-8 for a,b in totals.values())


@pytest.mark.parametrize("override", [{"max_shift_hours":-1},{"max_hourly_increase_fraction":float("inf")},
                                        {"flexible_fraction_by_type":{"small_house":1.2}}])
def test_invalid_flexibility_settings_fail(override):
    with pytest.raises(ValueError):
        DemandResponseSettings(**override)


def test_comparison_command_exports_two_valid_conditions_and_shift_audit(tmp_path):
    import csv
    import json
    import subprocess
    import sys
    from pathlib import Path
    from scripts.verify_results import verify_results
    completed = subprocess.run([sys.executable,"main.py","--scenario","A","--compare-demand-response",
                                "--no-charts","--output",str(tmp_path)],
                               cwd=Path(__file__).resolve().parents[1], capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
    assert set(verify_results(tmp_path))==set(verify_results(tmp_path/"demand_response"))=={"A"}
    paired=json.loads((tmp_path/"demand_response_comparison.json").read_text())
    fixed,shifted=paired["rows"]
    assert fixed["demand_kwh"]==pytest.approx(shifted["demand_kwh"])
    assert fixed["pv_generation_kwh"]==shifted["pv_generation_kwh"]
    with (tmp_path/"demand_response/inputs/demand_shifts.csv").open() as handle:
        journal=list(csv.DictReader(handle))
    quantity=sum(float(row["quantity_kwh"]) for row in journal)
    assert quantity>0
    assert shifted["pv_direct_self_consumption_kwh"]-fixed["pv_direct_self_consumption_kwh"]==pytest.approx(quantity)
