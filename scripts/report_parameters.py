"""Complete parameter explanations for the team PDF, independent of PDF libraries."""

# Each tuple contains the exact JSON key, its units and its implemented meaning.
COMMUNITY = [
    ("simulation.household_count", "building meters", "Number of aggregate participants, not flats. More meters enlarge the community. Must divide evenly into group_count."),
    ("simulation.group_count", "groups", "Number of P2P neighborhoods. Group size = meter count / group count. Changes which meters can trade directly."),
    ("simulation.battery_household_count", "owners", "Exact number of battery-owning meters. IDs are selected with the seed and spread evenly across groups. C/D disable operation, not ownership."),
    ("simulation.hours", "one-hour steps", "Length of the run. 24 covers one day; 168 covers a week and exposes weekend effects. Longer runs do not add holiday logic."),
    ("simulation.timestep_hours", "hours per step", "This implementation supports exactly 1. Do not change it to 0.5: the hourly input generator rejects other durations."),
    ("simulation.random_seed", "integer", "Controls randomized ownership, type positions, building attributes, cloud factors, demand variation and encounter order through separate seeded streams."),
    ("simulation.log_level", "logging level", "Console verbosity: DEBUG, INFO, WARNING, ERROR or CRITICAL. Does not change energy or prices."),
    ("buildings.enabled", "boolean", "true selects the mixed-building model. false selects the original individual-house model; type geometry and type battery scales are then unused."),
    ("buildings.pv_density_kw_m2", "kW per usable m2", "Installed PV power per usable roof area. Higher density raises capacity until the type PV limit is reached. It does not multiply roof area by floors."),
]
GEOMETRY = [
    ("share", "fraction", "Requested type fraction. All four shares must sum to 1. Counts use largest-remainder rounding separately in each neighborhood."),
    ("roof_min_m2", "m2", "Lower bound of the sampled single roof footprint; higher area permits more PV and increases the area-based commercial/school load basis."),
    ("roof_max_m2", "m2", "Upper bound of that roof draw. One roof per building, regardless of floor count."),
    ("floors_min", "floors", "Lower bound of the integer floor draw. Raises block dwelling counts and school floor area, without adding PV roofs."),
    ("floors_max", "floors", "Upper floor-count bound. Total floor area = roof footprint x sampled floors."),
    ("units_per_floor_min", "flats per floor", "Lower integer bound, used to calculate block flats. Small houses always have one dwelling; schools/shops have zero residential dwellings."),
    ("units_per_floor_max", "flats per floor", "Upper bound for block flats per floor. More flats increase aggregate residential demand, not roof size."),
    ("roof_usable_fraction_min", "fraction", "Lower bound of the usable roof share for PV. Excludes the rest of the roof from installed-panel area."),
    ("roof_usable_fraction_max", "fraction", "Upper usable-share bound. Capacity = min(roof x usable share x density, pv_limit_kw)."),
    ("pv_limit_kw", "kW", "Upper installed-PV limit for one building. Raising it matters only where the roof-based capacity would exceed the old limit."),
    ("battery_scale", "multiplier", "For owners, multiplies base storage capacity and both power limits. Does not change owner count, SOC fractions or efficiency."),
]
TYPE_LOAD = [
    ("daily_energy_min", "basis-dependent", "Lower base energy draw: kWh/dwelling/day for per_dwelling, or kWh/m2/day for per_floor_area. Before weekend/day multipliers."),
    ("daily_energy_max", "basis-dependent", "Upper energy draw. Multiply by dwelling count or total floor area to obtain the building weekday daily baseline."),
    ("energy_basis", "enum", "per_dwelling uses dwelling count; per_floor_area uses roof x floors. Keep houses/blocks on dwelling basis and nonresidential buildings on area basis."),
    ("profile", "enum", "residential uses morning/evening peaks. commercial and school use a base plus an opening-hour load. Type name alone does not override this field."),
    ("opening_hour", "local hour", "Start of operating activity, inclusive. Used by nonresidential profiles; ignored by residential profiles."),
    ("closing_hour", "local hour", "End of operating activity, exclusive. A school closing at 17 has no operating component in the 17:00-18:00 step."),
    ("base_load_weight", "relative weight", "Positive all-hour load weight. It sets profile shape relative to peaks/operation; hourly weights are normalized to the daily energy, so this is not a kW value."),
    ("operating_load_weight", "relative weight", "Additional weight while operating. Used by commercial/school profiles; ignored by residential profiles. Changes hourly distribution, not the daily baseline total."),
    ("weekend_multiplier", "fraction/multiplier", "Saturday/Sunday daily energy relative to the weekday baseline. 0.15 means 15%, not a 15% reduction. Daily random variation still applies."),
    ("weekend_open", "boolean", "Whether the nonresidential operating component remains active on weekends. false removes operating activity but does not remove the base load."),
    ("daily_variation_fraction", "fraction", "Seeded per-building, per-date variation. 0.08 samples a multiplier between 0.92 and 1.08, shared by all hours of that building's day."),
]
BATTERY = [
    ("simulation.battery.capacity_kwh", "kWh", "Base nominal stored-energy capacity. Each owning building multiplies this by its battery_scale."),
    ("simulation.battery.max_charge_power_kw", "kW", "Base AC charging power limit. Maximum step energy = scaled power x hours, also limited by PV surplus and SOC headroom."),
    ("simulation.battery.max_discharge_power_kw", "kW", "Base AC power delivered from storage. Also limited by owner demand and stored energy above minimum SOC."),
    ("simulation.battery.charge_efficiency", "fraction", "Fraction of AC charging energy retained in storage. 0.95 stores 0.95 kWh for every 1 kWh entering; the remainder is a loss."),
    ("simulation.battery.discharge_efficiency", "fraction", "Fraction of removed stored energy delivered to demand. Delivering 1 kWh removes 1 / efficiency kWh from storage."),
    ("simulation.battery.initial_soc", "fraction of capacity", "Starting inventory, not a charging transaction. 0.20 starts at 20% of each building's scaled nominal capacity."),
    ("simulation.battery.min_soc", "fraction of capacity", "Lower stored-energy reserve. Raising it reduces energy available for discharge."),
    ("simulation.battery.max_soc", "fraction of capacity", "Upper stored-energy bound. Lowering it reduces charging room. min <= initial <= max is required."),
    ("simulation.battery.strategy", "enum", "Engine default: self_consumption_first or p2p_priority. Named experiments override it: A/B select the first; E/F select the second. C/D disable storage."),
]
FORECAST = [
    ("forecast.start_timestamp", "ISO datetime + offset", "First hour of the run and the strict historical-price cutoff. Its weekday chooses school/weekend demand behavior. Offset is fixed; no named-zone DST calendar."),
    ("forecast.sunrise_hour", "local hour", "Start boundary of synthetic daylight. Generation is zero at and before this hour; configure for the modeled season."),
    ("forecast.sunset_hour", "local hour", "End boundary of synthetic daylight. Generation is zero at and after this hour; supplied weather is checked against these bounds."),
    ("forecast.peak_irradiance_w_m2", "W per m2", "Peak of the synthetic daylight curve before cloud scaling. Higher values raise PV energy, not installed PV capacity."),
    ("forecast.performance_factor", "fraction", "Converts irradiance and installed power to PV output, representing aggregate system losses. Applied to both synthetic and CSV weather."),
    ("forecast.cloud_factor_min", "fraction", "Lower synthetic hourly multiplier on clear-day irradiance. Unused when weather_csv is supplied."),
    ("forecast.cloud_factor_max", "fraction", "Upper synthetic cloud multiplier. Both cloud factors lie between 0 and 1; the default never exceeds the clear-day curve."),
    ("forecast.historical_days", "days", "Number of synthetic pre-start price days. Unused when a historical price CSV is supplied; not a rolling actual-data update during simulation."),
    ("forecast.price_base_eur_kwh", "EUR per kWh", "Level of synthetic historical prices before the hourly sine component and random noise. Unused with a price CSV."),
    ("forecast.price_amplitude_eur_kwh", "EUR per kWh", "Amplitude of the synthetic hourly price pattern around its base. The forecast then averages earlier observations by clock hour."),
    ("forecast.historical_price_noise_eur_kwh", "EUR per kWh", "Symmetric +/- noise for synthetic historical prices. A seeded draw, not a measured forecast error or uncertainty interval."),
    ("forecast.weather_csv", "path or null", "Optional timestamp,irradiance_w_m2 forecast file. null uses synthetic weather. Must cover the run and represent information available at issuance."),
    ("forecast.demand_csv", "path or null", "Optional timestamp,household_id,demand_kwh file covering every meter/hour. Replaces all synthetic load shapes, calendar and daily variation."),
    ("forecast.historical_prices_csv", "path or null", "Optional timestamp,price_eur_kwh file. Only observations strictly before start can affect hourly averages; all 24 clock hours need earlier coverage."),
]
BEHAVIOR = [
    ("households.bid_multiplier_min", "multiplier", "Lower household-specific bid-factor draw. Original maximum willingness to pay = reference forecast x drawn bid factor, clipped to market offer bounds."),
    ("households.bid_multiplier_max", "multiplier", "Upper bid-factor bound. Higher bids can accept more asks, but do not create shortage or available generation."),
    ("households.ask_multiplier_min", "multiplier", "Lower seller ask-factor draw applied to the reference forecast before offer clipping. Lower asks can improve compatibility."),
    ("households.ask_multiplier_max", "multiplier", "Upper ask-factor bound. A higher range can make offers incompatible with buyers; prices are still limited by market bounds."),
    ("households.morning_peak_weight", "relative weight", "Height of the residential morning peak relative to base/evening load. Normalized to daily energy, not an extra daily kWh allowance."),
    ("households.morning_peak_hour", "local hour", "Center of the residential morning Gaussian peak before each building's seeded timing shift."),
    ("households.morning_peak_width_hours", "hours", "Width in exp(-((hour-center)/width)^2). Larger values spread the same normalized daily energy across a broader morning peak."),
    ("households.evening_peak_weight", "relative weight", "Relative height of the residential evening peak. Higher weight reallocates energy toward evening after normalization."),
    ("households.evening_peak_hour", "local hour", "Center of the residential evening peak before the building timing shift."),
    ("households.evening_peak_width_hours", "hours", "Width of the evening Gaussian profile component. Does not change the configured daily energy draw."),
    ("households.profile_shift_max_hours", "hours", "Maximum +/- building timing shift for residential peaks. A shift is drawn for other profiles but is not used by their fixed opening schedule."),
    ("households.profile_noise_fraction", "fraction", "Seeded hourly weight variation. 0.25 multiplies weights by draws from 0.75 to 1.25, then renormalizes the daily total."),
]
ECONOMICS = [
    ("market.grid_import_tariff_eur_kwh", "EUR per kWh", "Price paid to the external grid for residual shortages, before a regulated grid fee."),
    ("market.grid_export_tariff_eur_kwh", "EUR per kWh", "Revenue from the grid for residual surplus, before the export-side regulated fee."),
    ("market.minimum_offer_eur_kwh", "EUR per kWh", "Lower bound for original/guided offers. It must be at least the export tariff. Guidance leaves headroom for a guaranteed reward discount."),
    ("market.maximum_offer_eur_kwh", "EUR per kWh", "Upper offer bound, at most the import tariff. Import >= maximum >= minimum >= export is required."),
    ("regulator.initial_budget_eur", "EUR", "Opening reward fund, recorded as external initial funding if nonzero. It is not fee revenue. Defaults to zero."),
    ("regulator.grid_fee_eur_kwh", "EUR per kWh", "Fee on each grid import and export when regulated, collected after trading. No fee is charged on internal trades."),
    ("regulator.lower_tier_budget_eur", "EUR", "Opening-fund threshold for the lower positive reward tier. At exactly this threshold the lower rate applies."),
    ("regulator.upper_tier_budget_eur", "EUR", "Opening-fund threshold for the upper reward tier. At exactly this threshold the upper rate applies."),
    ("regulator.lower_reward_eur_kwh", "EUR per P2P kWh", "Reward to successful P2P sellers in the lower tier, conditional on full funding of the proposed trade quantity."),
    ("regulator.upper_reward_eur_kwh", "EUR per P2P kWh", "Upper-tier reward. The rate remains fixed for the hour, but reservations cannot exceed remaining available funds."),
    ("regulator.reward_discount_fraction", "fraction of rate", "Share of the guaranteed reward rate subtracted from guided ask. 0.50 gives buyers half the rate as a price reduction; sellers still receive the full reward."),
    ("regulator.guidance_strength", "fraction", "Blend weight: guided = (1-strength) x original + strength x target, then clipped. Zero removes the blend, but leaves reward rules active."),
    ("regulator.guided_bid_multiplier", "multiplier", "Buyer guidance target = reference forecast x this value. Higher targets can make bids more compatible."),
    ("regulator.guided_ask_multiplier", "multiplier", "Seller guidance target = reference forecast x this value. Lower targets can make asks more compatible."),
]
LEGACY_AND_CHAIN = [
    ("blockchain.miner_count", "simulated miners", "Number of round-robin nonce-search participants in one process. No physical servers, network or miner compensation are modeled."),
    ("blockchain.hash_prefix", "hexadecimal text", "Required hash beginning. A longer prefix increases expected mining work; it does not change trades, prices or energy balances."),
    ("blockchain.max_nonce_attempts", "attempts per block", "Guard against unbounded mining. If exhausted, mining raises an error rather than appending an invalid block."),
    ("households.pv_capacity_min_kw", "kW; legacy only", "Lower per-house PV draw only when buildings.enabled=false. It does not control roof-based PV in the mixed model."),
    ("households.pv_capacity_max_kw", "kW; legacy only", "Upper legacy PV draw. Edit buildings geometry, usable fractions, density or limits for the mixed model instead."),
    ("households.daily_demand_min_kwh", "kWh/day; legacy only", "Lower daily demand draw in the old house model. Mixed-model baselines use each type's daily_energy_min/max and energy_basis."),
    ("households.daily_demand_max_kwh", "kWh/day; legacy only", "Upper daily demand draw in the old model. No effect on mixed-building daily energy."),
    ("households.base_demand_weight", "weight; legacy only", "Base hourly profile weight in the old model. Mixed profiles use buildings.types.<type>.base_load_weight instead."),
]
SCALAR_GROUPS = [COMMUNITY, BATTERY, FORECAST, BEHAVIOR, ECONOMICS, LEGACY_AND_CHAIN]
TYPE_KEYS = GEOMETRY + TYPE_LOAD


def get_value(config: dict, path: str):
    result = config
    for component in path.split("."):
        result = result[component]
    return result


def parameter_paths(config: dict) -> set[str]:
    """Check coverage of every configurable leaf, excluding scenario experiment metadata."""
    actual = set()
    def walk(value, prefix):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{prefix}.{key}" if prefix else key)
        else:
            actual.add(prefix)
    walk({key:value for key,value in config.items() if key != "experiment"}, "")
    documented = {key for group in SCALAR_GROUPS for key,_,_ in group}
    documented |= {f"buildings.types.{kind}.{key}" for kind in config["buildings"]["types"]
                   for key,_,_ in TYPE_KEYS}
    if actual != documented:
        raise ValueError(f"Parameter documentation mismatch: missing={sorted(actual-documented)}, stale={sorted(documented-actual)}")
    return documented


def format_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value,bool):
        return "true" if value else "false"
    if isinstance(value,float):
        return f"{value:g}"
    return str(value)


def append_parameter_guide(config, p, title, sub, table, page):
    """Append a team-oriented reference using values from the saved run configuration."""
    paths = parameter_paths(config)
    kinds = ("small_house", "apartment_block", "supermarket", "school")

    def scalar_rows(entries):
        return [["Exact JSON key", "Value used / units", "Meaning and effect of changing it"]] + [
            [key, f"{format_value(get_value(config,key))} ({units})", meaning]
            for key,units,meaning in entries]

    def type_rows(entries):
        return [["Key under each type", "House", "Block", "Market", "School", "Units and meaning"]] + [
            [key, *[format_value(config["buildings"]["types"][kind][key]) for kind in kinds],
             f"{units}. {meaning}"] for key,units,meaning in entries]

    page()
    title(11,"Team guide: how to read the simulation")
    p(f"The next pages explain <b>all {len(paths)} configurable values</b> in the recorded experiment. Values come from scenario A's saved configuration in results/comparison.json, not from a possibly edited live JSON file. Other scenarios reuse the same base inputs and differ in their recorded storage/regulation switches.")
    table([["Read first", "Purpose"], ["Pages 1-5", "Community, building types, physical models and trading rules."],
           ["Pages 6-10", "Actual outcomes and numerical verification."],
           ["Pages 12-20", "Exact parameter names, values, units and implemented effects."],
           ["Page 21", "Worked shared-roof example and steps for a controlled team experiment."]],[125,382])
    sub("Units and terms")
    table([["Term", "What it means in this simulator"],
           ["kW", "Power: an energy rate. A 3 kW charger can draw at most 3 kWh during one hour, before other limits."],
           ["kWh", "Energy accumulated over a step or stored in a battery. Sum hourly energy to obtain a daily total."],
           ["EUR/kWh", "Price per energy unit. Quantity x price gives the trading payment. EUR/MWh source data must be divided by 1000."],
           ["SOC", "Stored energy / nominal battery capacity. 0.20 means 20%, not 0.20 kWh."],
           ["Building / meter", "One trading participant. A block aggregates its flats at one meter and shares one roof."],
           ["Dwelling unit", "One residential flat/home inside a building. It is not automatically a separate P2P participant."]],[125,382])
    sub("Fixed properties versus dynamic values")
    p("Roof area, floors, flat count, PV capacity, offer factors and battery ownership are drawn once per experiment and stay fixed. Hourly PV, demand, SOC, trades, cash and regulator funds evolve through time. Shape weights redistribute a fixed daily energy baseline; they are not independently added kWh.")
    p("Synthetic inputs and sizing ranges are teaching assumptions. A valid conservation check proves accounting consistency, not empirical realism or a guarantee of better economics.")

    page()
    title(12,"Parameters: community, time and randomness")
    p("JSON sections: simulation and buildings. Historical keys containing household now count building meters in the mixed model. A report value is not applied to new runs until it is saved in the chosen configuration.")
    table(scalar_rows(COMMUNITY),[145,105,257])
    p("Constraints: equal neighborhood sizes; battery owners between zero and meter count; positive duration; currently one-hour steps only. Shares are rounded separately within each group, so small custom groups may not reproduce exact requested type percentages.")
    p("The seed is held fixed across scenarios. Changing it creates a different realization and should be recorded as a new experiment, rather than interpreted as the effect of one policy switch.")

    page()
    title(13,"Parameters: building geometry and composition")
    p("Prefix: buildings.types.&lt;type&gt;., where type is small_house, apartment_block, supermarket or school. The four value columns show the actual settings used; H001-H100 are the resulting seeded realizations, not these range endpoints.")
    table(type_rows(GEOMETRY),[116,38,38,45,43,227])
    p("Roof and floor area are different quantities. Type PV limits constrain the single roof; floors never create duplicate roofs. Battery scale changes equipment sizes only for existing owners, preserving the selected 55 owner IDs in this run.")

    page()
    title(14,"Parameters: building demand and schedules")
    p("Prefix: buildings.types.&lt;type&gt;. Daily energy is drawn first, then distributed over 24 hours. The realized total may differ after weekend and per-date variation. Operating hours use the configured fixed local offset.")
    table(type_rows(TYPE_LOAD),[116,38,38,45,43,227])
    p("Example: a school's weekday baseline of 400 kWh becomes a 60 kWh weekend baseline at multiplier 0.15, then receives its seeded daily factor. This is an illustration of the rule, not an observed or reported school measurement.")

    page()
    title(15,"Parameters: batteries and energy losses")
    p("Prefix: simulation.battery. Type battery_scale multiplies the three sizing values; fractions and strategy are not scaled. Storage cannot use purchased electricity or discharge beyond owner demand.")
    table(scalar_rows(BATTERY),[145,105,257])
    scales = ", ".join(f"{kind}: x{format_value(config['buildings']['types'][kind]['battery_scale'])}" for kind in kinds)
    p("Equipment multipliers used: "+scales+". Min/initial/max SOC must be ordered and efficiencies must lie in (0,1]. Named A-F scenarios override the engine strategy field as shown on page 1.")
    sub("Worked AC-side example")
    efficiency=config["simulation"]["battery"]["charge_efficiency"]
    discharge_efficiency=config["simulation"]["battery"]["discharge_efficiency"]
    p(f"If headroom and surplus allow a 3 kWh charge, storage gains {3*efficiency:.3f} kWh and loses {3*(1-efficiency):.3f} kWh. Delivering 1 kWh to demand removes {1/discharge_efficiency:.4f} kWh from storage, with {1/discharge_efficiency-1:.4f} kWh lost. Power and SOC limits may reduce these illustrative quantities.")

    page()
    title(16,"Parameters: weather, prices and input files")
    p("Prefix: forecast. CSV paths replace only the corresponding synthetic input. null means use the fallback. All input types remain explicitly labeled in hourly_inputs.csv.")
    table(scalar_rows(FORECAST),[145,105,257])
    p("Past-price forecasting requires earlier observations for every clock hour. Never insert future actual data into a weather/demand file and call it an available forecast. The code cannot infer that provenance from column names alone.")

    page()
    title(17,"Parameters: offers and residential profile shape")
    p("Prefix: households, retained for compatibility. Offer factors apply to all building meters. Morning/evening shape parameters apply only to residential profiles. A single building's bid/ask factors stay fixed while reference prices vary hourly.")
    table(scalar_rows(BEHAVIOR),[145,105,257])
    p("For residential weights, the code combines type base_load_weight with Gaussian morning/evening components, multiplies hourly noise weights, then normalizes to the drawn daily energy. A larger peak weight shifts energy toward that peak; it does not raise the configured daily total.")

    page()
    title(18,"Parameters: grid prices and offer bounds")
    p("Prefix: market. These prices set the outside option and restrict bids/asks. P2P transactions pay the seller ask; aggregator transactions pay the bid-ask midpoint. Buying and selling are limited by remaining energy, not only by prices.")
    table(scalar_rows(ECONOMICS[:4]),[145,105,257])
    sub("Worked original-offer example")
    p("Illustration: reference price EUR 0.20/kWh, buyer factor 1.10 and seller factor 1.00 produce a bid of EUR 0.22 and ask of EUR 0.20 before guidance. With sufficient energy, a 2 kWh P2P transaction costs EUR 0.40 at the seller ask. An aggregator match at those offers instead uses EUR 0.21/kWh, costing EUR 0.42.")
    sub("Costs need an accounting boundary")
    p("Meter net cost includes grid and internal purchases minus sales, plus fees minus rewards. Internal trading payments cancel over all meters. Regulator fees/rewards also cancel when the regulator is included. Therefore meters-plus-regulator net cost equals net external-grid payments, while meter-only cost can move differently.")
    p("Changing import/export tariffs changes grid settlement. Changing offer bounds changes compatibility in internal markets as well. A high PV surplus alone does not imply P2P trade: an eligible buyer must have demand and a compatible bid in the same group.")

    page()
    title(19,"Parameters: regulator guidance and funding")
    p("Prefix: regulator. All rules apply only when regulation is enabled by the selected scenario. The opening balance chooses one tier for the hour; the remaining fund still constrains each guarantee.")
    table(scalar_rows(ECONOMICS[4:]),[145,105,257])
    sub("Worked funded-reward example")
    rate=config["regulator"]["upper_reward_eur_kwh"]
    fraction=config["regulator"]["reward_discount_fraction"]
    p(f"Illustration: opening fund EUR 5, guided ask EUR 0.20/kWh, trade 2 kWh and reward rate EUR {rate:.2f}/kWh. Reserve EUR {2*rate:.2f}. Adjusted ask is EUR {0.20-fraction*rate:.2f}/kWh. The buyer pays EUR {2*(.20-fraction*rate):.2f}; the seller also receives EUR {2*rate:.2f} from the fund. The full reward must be affordable before the discount is guaranteed.")
    p("Below the lower budget threshold there is no reward, but guided/ordinary trading can still occur. Fees collected at hour end cannot retroactively finance that hour's quotes.")

    page()
    title(20,"Parameters: blockchain and legacy-only fields")
    p("The first three fields configure the transaction record, independently of energy matching. The remaining fields are deliberately retained for the original house model and have no sizing effect in the mixed-building model.")
    table(scalar_rows(LEGACY_AND_CHAIN),[145,105,257])
    p("Use buildings geometry and type energy parameters for current experiments. Setting households.pv_capacity_max_kw while buildings.enabled=true does not alter installed PV. Use config/residential_baseline.json when intentionally reproducing the old model.")
    p("Proof-of-work difficulty is computational work, not a reward paid to miners or an electrical load in the community. Miner count does not represent the number of neighborhoods, even though both happen to be 10 in the current defaults.")

    page()
    title(21,"Team workflow and controlled experiments")
    sub("1. Start from a recorded baseline")
    p("Keep the default saved result and record the scientific question. Change one mechanism at a time when estimating its effect. Compare policies on the same buildings, weather, demand, price inputs and seeds. For sensitivity to seed, use several separately recorded realizations rather than selecting a favorable one.")
    sub("2. Save a partial JSON override")
    p('Example for a seven-day school-weekend experiment, saved as config/team_experiment.json:',"Body")
    p('{<br/>  "simulation": {"hours": 168},<br/>  "buildings": {"types": {<br/>    "school": {"weekend_multiplier": 0.10}<br/>  }}<br/>}',"Code")
    p("Partial overrides retain unspecified defaults. Type shares must still sum to 1, and base battery fields remain under simulation.battery. There is no --hours command-line option: duration is changed in JSON.")
    sub("3. Run, inspect and preserve separate outputs")
    p("python main.py --config config/team_experiment.json<br/>  --include-priority --output results/team_experiment<br/>python scripts/verify_results.py results/team_experiment","Code")
    p("The simulation command above is shown across two lines for readability: enter it as one command. A-F retain their named scenario rules. --no-charts skips graphs; --scenario B runs only B. The PDF builder requires all six scenarios and chart files, and warns if the saved validation record uses a different input hash.")
    sub("Shared-roof sizing example")
    p("Illustration: one block has a 250 m2 roof, usable share 0.50 and density 0.20 kW/m2. PV capacity is 25 kW if its type limit permits. At 4 floors and 3 flats per floor it has 12 flats; at 8 floors it has 24. At an illustrative 10 kWh per flat/day, baseline demand rises from 120 to 240 kWh/day while PV remains 25 kW. These are example values, not extra measurements.")
    sub("4. Read the outputs before drawing conclusions")
    p("Check comparison.csv for P2P kWh, its surplus denominator, imports/exports, costs at both boundaries, fees, rewards, closing funds and final storage. Join household_hourly.csv with inputs/households.csv by meter ID for type-specific behavior. Keep the exact saved configuration and input hash; a new community is not a pure policy comparison.")
    return 21
