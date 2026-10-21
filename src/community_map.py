"""Schematic household layout: each row is a trading group, not a geographic street."""

from collections import defaultdict
from pathlib import Path
import os
import tempfile
from random import Random

from src.households import Household
from src.building_profiles import TYPE_SHORT_LABELS
from src.output import write_csv


BATTERY_COLOR = "#315A86"
PV_ONLY_COLOR = "#E8BD70"
CONSUMER_COLOR = "#D6DFD3"
INK_COLOR = "#19364F"


def community_layout(households: list[Household]) -> list[dict]:
    """Assign display cells without changing group membership, identity or ownership."""
    if not households or len({h.household_id for h in households}) != len(households):
        raise ValueError("The map requires a nonempty community with unique household IDs.")
    groups = defaultdict(list)
    for household in households:
        groups[household.group_id].append(household)
    cells = []
    for row, group_id in enumerate(sorted(groups)):
        members = sorted(groups[group_id], key=lambda h: h.household_id)
        Random(42 + group_id).shuffle(members)  # Display only; never changes market order.
        for column, household in enumerate(members):
            cells.append({
                "row": row, "column": column, "household_id": household.household_id,
                "group_id": group_id, "has_battery": household.has_battery,
                "participant_role": household.participant_role,
                "pv_capacity_kw": household.pv_capacity_kw,
                "daily_demand_kwh": sum(household.demand_profile_kwh),
                "battery_capacity_kwh": household.battery.capacity_kwh if household.battery else 0.0,
                "building_type": household.building_type, "floors": household.floors,
                "roof_area_m2": household.roof_area_m2, "floor_area_m2": household.floor_area_m2,
                "dwelling_units": household.dwelling_units,
            })
    return cells


def generate_community_map(households: list[Household], directory: Path) -> None:
    """Export an annotated map and exact cell/group data using the actual community."""
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartgrid-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Polygon, Rectangle

    cells = community_layout(households)
    rows = max(cell["row"] for cell in cells) + 1
    columns = max(cell["column"] for cell in cells) + 1
    groups = []
    for row in range(rows):
        members = [cell for cell in cells if cell["row"] == row]
        battery_count = sum(cell["has_battery"] for cell in members)
        consumer_count = sum(cell["participant_role"] == "consumer" for cell in members)
        group = {"group_id": members[0]["group_id"], "household_count": len(members),
                       "battery_count": battery_count, "pv_only_count": len(members) - battery_count - consumer_count,
                       "consumer_count": consumer_count, "prosumer_count": len(members) - consumer_count,
                       "pv_capacity_kw": sum(cell["pv_capacity_kw"] for cell in members),
                 "dwelling_units": sum(cell["dwelling_units"] for cell in members)}
        for kind in TYPE_SHORT_LABELS:
            group[f"{kind}_count"] = sum(cell["building_type"] == kind for cell in members)
        groups.append(group)
    directory.mkdir(parents=True, exist_ok=True)
    write_csv(directory / "data" / "community_layout.csv", cells)
    write_csv(directory / "data" / "neighborhood_distribution.csv", groups)
    fig, axis = plt.subplots(figsize=(18, 14))
    fig.suptitle("Community building distribution", fontsize=22, fontweight="bold", color=INK_COLOR, y=.97)
    consumer_count = sum(cell["participant_role"] == "consumer" for cell in cells)
    axis.set_title(f"{len(cells)} meters: {len(cells)-consumer_count} prosumers + {consumer_count} consumers | Each row is one mixed P2P neighborhood", fontsize=13, color=INK_COLOR, pad=18)
    for row, group in enumerate(groups):
        y = rows - 1 - row
        axis.add_patch(Rectangle((-.07, y - .02), columns + .14, 1.0,
                                 facecolor="#F2F5F7" if row % 2 == 0 else "#FFFFFF",
                                 edgecolor="#AEBBC5", linewidth=.7, zorder=0))
        axis.text(-.22, y + .52, f'G{group["group_id"]}', ha="right", va="center",
                  fontsize=12, color=INK_COLOR, fontweight="bold")
        axis.text(-.22, y + .27, f'{group["battery_count"]} batteries', ha="right", va="center",
                  fontsize=9, color=INK_COLOR)
    for cell in cells:
        x, y = cell["column"], rows - 1 - cell["row"]
        battery = cell["has_battery"]
        consumer = cell["participant_role"] == "consumer"
        fill = CONSUMER_COLOR if consumer else BATTERY_COLOR if battery else PV_ONLY_COLOR
        text_color = "#FFFFFF" if battery else INK_COLOR
        kind = cell["building_type"]
        label = TYPE_SHORT_LABELS[kind]
        if kind == "apartment_block":
            height = min(.78, .48 + .03 * cell["floors"])
            axis.add_patch(Rectangle((x + .18, y + .10), .64, height,
                                     facecolor=fill, edgecolor=INK_COLOR, linewidth=.7))
            axis.plot([x + .18, x + .82], [y + .58, y + .58], color=text_color, linewidth=.6)
            axis.text(x + .5, y + .10 + height - .07, f"BLOCK {cell['floors']}F", ha="center", va="center",
                      color=text_color, fontsize=6.8, fontweight="bold")
        elif kind == "supermarket":
            axis.add_patch(Rectangle((x + .05, y + .10), .90, .53,
                                     facecolor=fill, edgecolor=INK_COLOR, linewidth=.7))
            axis.add_patch(Rectangle((x + .04, y + .63), .92, .15,
                                     facecolor=fill, edgecolor=INK_COLOR, linewidth=.7))
            axis.text(x + .5, y + .71, label, ha="center", va="center", color=text_color, fontsize=7.2, fontweight="bold")
        else:
            axis.add_patch(Rectangle((x + .10, y + .10), .80, .52,
                                     facecolor=fill, edgecolor=INK_COLOR, linewidth=.65))
            axis.add_patch(Polygon([(x + .07, y + .62), (x + .50, y + .91), (x + .93, y + .62)],
                                   facecolor=fill, edgecolor=INK_COLOR, linewidth=.65))
            axis.text(x + .5, y + .72, label, ha="center", va="center", color=text_color, fontsize=6.6, fontweight="bold")
        axis.text(x + .5, y + .48, cell["household_id"], ha="center", va="center",
                  color=text_color, fontsize=8.7, fontweight="bold")
        axis.text(x + .5, y + .28, "CONSUMER" if consumer else f'PV {cell["pv_capacity_kw"]:.1f} kW', ha="center", va="center",
                  color=text_color, fontsize=7.0)
        if battery:
            axis.text(x + .88, y + .84, "B", ha="center", va="center", color=BATTERY_COLOR,
                      bbox={"facecolor":"white", "edgecolor":BATTERY_COLOR,"boxstyle":"circle,pad=.15"},
                      fontsize=6.5, fontweight="bold")
    owner_count = sum(cell["has_battery"] for cell in cells)
    handles = [Patch(facecolor=BATTERY_COLOR, edgecolor=INK_COLOR,
                     label=f"PV + battery: {owner_count} buildings (B marker)"),
               Patch(facecolor=PV_ONLY_COLOR, edgecolor=INK_COLOR,
                     label=f"PV only: {len(cells) - owner_count - consumer_count} buildings"),
               Patch(facecolor=CONSUMER_COLOR, edgecolor=INK_COLOR,
                     label=f"Consumer only: {consumer_count} buildings (no PV/storage)")]
    fig.text(.5, .09, "HOUSE = small house   BLOCK = apartment block (F = floors)   SHOP = supermarket   SCHOOL = school",
             ha="center", fontsize=9, color=INK_COLOR)
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.52, .055), ncol=3,
               frameon=False, fontsize=11)
    fig.text(.5, .035, "Schematic only: row/column positions are display choices, not real coordinates or electrical connections.",
             ha="center", fontsize=9, color="#4C5A65")
    fig.text(.5, .017, "Ownership stays fixed across scenarios; C/D disable battery operation without changing this community design.",
             ha="center", fontsize=9, color="#4C5A65")
    axis.set(xlim=(-.12, columns + .12), ylim=(-.08, rows + .04), aspect="equal")
    axis.set_axis_off()
    fig.subplots_adjust(left=.12, right=.97, bottom=.12, top=.90)
    for suffix in ("png", "svg"):
        metadata = {"Date": None} if suffix == "svg" else None
        fig.savefig(directory / f"community_map.{suffix}", dpi=180, metadata=metadata)
    plt.close(fig)
