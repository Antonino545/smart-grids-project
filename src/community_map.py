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
                "homes": household.homes,
            })
    return cells


def draw_building(axis, kind: str, x: float, y: float, fill: str, text_color: str, label: str, floors: int) -> None:
    """Draw one building with a silhouette and details unique to its type (cell spans x..x+1, y..y+1).

    House: pitched roof and chimney. Block: tall flat-roofed tower with one balcony per floor on
    each side, a door and a roof antenna. Shop: wide hall under a red-and-white striped awning. School: classical pediment,
    edge columns and a bell tower with a flag. The middle of each body stays free for ID and PV text.
    """
    from matplotlib.patches import Circle, Polygon, Rectangle
    edge = {"facecolor": fill, "edgecolor": INK_COLOR, "linewidth": .7}
    detail = {"facecolor": "white", "edgecolor": INK_COLOR, "linewidth": .4}
    if kind == "apartment_block":
        height = min(.74, .50 + .025 * floors)
        top = y + .10 + height
        axis.add_patch(Rectangle((x + .20, y + .10), .60, height, **edge))
        axis.add_patch(Rectangle((x + .17, top), .66, .035, **edge))  # flat roof parapet
        # One balcony per floor sticking out on both sides (outside the text), a door and a roof antenna.
        shown = max(1, min(floors, 8))
        for floor in range(shown):
            level = y + .13 + floor * (height - .06) / shown
            for left in (x + .14, x + .80):
                axis.add_patch(Rectangle((left, level), .06, .018, **detail))
        axis.add_patch(Rectangle((x + .45, y + .10), .10, .08, **detail))
        axis.plot([x + .70, x + .70], [top + .035, top + .13], color=INK_COLOR, linewidth=.8)
        axis.plot([x + .66, x + .74], [top + .10, top + .10], color=INK_COLOR, linewidth=.8)
        axis.text(x + .5, top - .07, f"BLOCK {floors}F", ha="center", va="center",
                  color=text_color, fontsize=6.6, fontweight="bold")
    elif kind == "supermarket":
        axis.add_patch(Rectangle((x + .03, y + .10), .94, .46, **edge))
        stripes = 8
        for index in range(stripes):
            left = x + .01 + index * .98 / stripes
            axis.add_patch(Polygon([(left, y + .66), (left + .98 / stripes, y + .66),
                                    (left + .98 / stripes, y + .56), (left, y + .56)], closed=True,
                                   facecolor="#C0392B" if index % 2 == 0 else "white", edgecolor=INK_COLOR, linewidth=.4))
        axis.add_patch(Rectangle((x + .20, y + .66), .60, .15, **edge))  # roof sign
        axis.text(x + .5, y + .735, label, ha="center", va="center", color=text_color, fontsize=6.8, fontweight="bold")
    elif kind == "school":
        axis.add_patch(Rectangle((x + .04, y + .10), .92, .46, **edge))
        for left in (x + .07, x + .15, x + .80, x + .88):  # columns at both ends
            axis.add_patch(Rectangle((left, y + .12), .05, .40, **detail))
        axis.add_patch(Polygon([(x + .01, y + .56), (x + .50, y + .78), (x + .99, y + .56)], closed=True, **edge))
        axis.add_patch(Rectangle((x + .44, y + .78), .12, .08, **edge))  # bell tower
        axis.add_patch(Circle((x + .50, y + .82), .022, facecolor="white", edgecolor=INK_COLOR, linewidth=.4))
        axis.plot([x + .50, x + .50], [y + .86, y + .98], color=INK_COLOR, linewidth=.8)
        axis.add_patch(Polygon([(x + .50, y + .98), (x + .62, y + .955), (x + .50, y + .93)],
                               facecolor="#C0392B", edgecolor=INK_COLOR, linewidth=.4))
        axis.text(x + .5, y + .625, label, ha="center", va="center", color=text_color, fontsize=6.2, fontweight="bold")
    else:
        axis.add_patch(Rectangle((x + .66, y + .66), .08, .20, **edge))  # chimney behind the roof
        axis.add_patch(Rectangle((x + .16, y + .10), .68, .52, **edge))
        axis.add_patch(Polygon([(x + .08, y + .62), (x + .50, y + .92), (x + .92, y + .62)], **edge))
        axis.text(x + .5, y + .72, label, ha="center", va="center", color=text_color, fontsize=6.6, fontweight="bold")


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
                 "homes": sum(cell["homes"] for cell in members)}
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
        draw_building(axis, kind, x, y, fill, text_color, label, cell["floors"])
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
    fig.text(.5, .09, "Shapes: HOUSE = pitched roof + chimney   BLOCK = tall tower, balconies + antenna (F = floors)   "
             "SHOP = wide hall + red/white striped awning   SCHOOL = columns, pediment, bell tower and flag",
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
