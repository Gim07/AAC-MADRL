# MESLearn: Multi-Energy Systems Learning Framework

## 🌟 Overview

**MESLearn** (Multi-Energy Systems CityLearn) is an advanced extension of CityLearn 2.3.1 that enables **multi-energy system control** for district-scale demand-side management. This repository provides training and deployment scripts for multiple advanced controllers with support for **dual energy sources** (electricity and fuel).

### Available Controllers

- **AAC-MADRL** — *Actor-Attention-Critic Multi-Agent DRL*: Attention-based multi-agent actor–critic method for district-scale DSM
- **SAC** — *Soft Actor-Critic*: State-of-the-art model-free deep RL algorithm
- **Stable Baselines 3 SAC** — *SAC controller from stable-baseliunes3 library, tested only fo the centralized case*
- **RBC** — *PI Controller*: Integration of a new baseline proportional-integral control for temperature regulation

### What's New in MESLearn?

MESLearn extends the original AAC-MADRL framework (published in Applied Energy, 2025) with **multi-energy system capabilities**:

#### **Key Enhancements**:

1. **🔥 4th Control Action: `heating_fuel_device`**
   - Adds gas boiler control alongside electric heating
   - Expands action space from 21³ to 21⁴ per building
   - Enables fuel-electric switching strategies

2. **📊 Fuel Pricing Signals**
   - Real-time and 3-hour ahead fuel price forecasts
   - Enables cost-aware multi-energy decisions
   - Schema enhancement: `fuel_pricing`, `fuel_pricing_predicted_1/2/3`

3. **⚖️ Enhanced Reward Functions**
   - Multi-objective optimization: comfort + cost + emissions
   - Dual-energy cost tracking: electricity + fuel
   - District-level coordination with fuel consideration

4. **📈 Comprehensive Tracking**
   - Separate electricity and fuel consumption metrics
   - Independent cost and emission accounting
   - Multi-energy KPI evaluation

**Note**: Features like `hvac_mode`, `comfort_band`, and `carbon_intensity` were already available in CityLearn 2.3.1. The core MESLearn contribution is adding **fuel pricing signals** and the **heating_fuel_device control action** to enable multi-energy optimization.

---

## 🚀 New Features in MESLearn

### 1. **Dual Energy Source Support** ⚡🔥

MESLearn introduces comprehensive support for **multi-energy systems** with two distinct energy carriers:

#### **Electricity Network**
- Grid import/export capabilities
- Solar PV generation
- Electrical storage systems (batteries)
- Heat pumps and electrical heating devices
- Real-time electricity pricing and carbon intensity signals

#### **Fuel Network (Natural Gas)**
- Natural gas supply for heating
- Fuel-based heating devices (gas boilers)
- Independent fuel pricing structure
- Separate carbon emission factors
- Complementary operation with electric systems

#### **Key Advantages**
✅ **Flexibility**: Choose optimal energy source based on cost and availability  
✅ **Resilience**: Fallback to alternative energy during outages or price spikes  
✅ **Efficiency**: Leverage both networks for optimal building performance  
✅ **Realism**: Represents actual multi-energy building infrastructure  

### 2. **Enhanced Schema Configuration** 📋

The schema has been expanded to support multi-energy systems with the addition of **heating_device** as a new action and
of **fuel pricing signals** in the obervations section.

#### **New Fuel Pricing Observations**
Addition of **fuel pricing signals** to enable cost-aware control decisions between electricity and gas.

```json
{
  "fuel_pricing": {
    "active": true,
    "shared_in_central_agent": true,
    "description": "Real-time natural gas pricing ($/kWh)"
  },
  "fuel_pricing_predicted_1": {
    "active": true,
    "shared_in_central_agent": true,
    "description": "1-hour ahead fuel price forecast"
  },
  "fuel_pricing_predicted_2": {
    "active": true,
    "shared_in_central_agent": true,
    "description": "2-hour ahead fuel price forecast"
  },
  "fuel_pricing_predicted_3": {
    "active": true,
    "shared_in_central_agent": true,
    "description": "3-hour ahead fuel price forecast"
  }
}
```


#### **Schema Enhancements Summary**

| Category    | Feature                    | Status    | Description                           |
|-------------|----------------------------|-----------|---------------------------------------|
| **Pricing** | `fuel_pricing`             | **NEW**   | Real-time natural gas pricing         |
| **Pricing** | `fuel_pricing_predicted_*` | **NEW**   | 1-3 hour ahead fuel price forecasts   |
| **Energy**  | `net_fuel_consumption`     | **NEW**   | Total fuel consumption tracking       |
| **Energy**  | `heating_fuel_consumption` | **NEW**   | Heat output from gas boiler           |
| **Energy**  | `dhw_fuel_consumption`     | **NEW**   | Heat output from gas boiler           |
| **Devices** | `heating_fuel_device`      | **NEW**   | Gas boiler control action             |
| **Devices** | `dhw_device`               | **NEW**  | DHW device could be also a gas boiler |


#### **Building Device Configuration**
Buildings now specify **dual-source heating systems**:
- **Electric heating device**: Heat pump, electric resistance heating
- **Fuel heating device**: Gas boiler
- **Control strategy**: Agents decide which device to activate and at what capacity

### 3. **Advanced Rule-Based Controller (RBC)** 🎛️

A sophisticated **PI (Proportional-Integral) Controller** has been implemented as a robust baseline that demonstrates intelligent multi-energy system operation without machine learning.

#### **Overview**

The PI Controller (`PIController` class) is a **hierarchical control strategy** that combines:
1. **Solar-aware energy source selection**: Automatically switches between electric and fuel heating
2. **PI temperature control**: Precise temperature regulation using proportional-integral feedback
3. **Intelligent storage management**: Optimizes thermal and electrical storage based on solar availability
4. **Anti-windup mechanisms**: Prevents integral saturation for stable long-term operation

#### **Control Strategy**

The RBC uses classic feedback control theory with modern enhancements:

```
Control Signal = K_p × error(t) + K_i × ∫error(t)dt
```

Where:
- `error(t) = T_setpoint - T_current` (for heating)
- `K_p`: Proportional gain (immediate response to current error)
- `K_i`: Integral gain (eliminates steady-state error over time)

**Key Innovation**: The same PI control signal is used for **both** heating devices (electric heat pump and gas boiler), but the controller intelligently routes it to the appropriate device based on solar availability and battery state.

#### **Hierarchical Heating Decision Logic**

The controller implements a **solar-aware hierarchical strategy** for choosing between electric and fuel heating:

```python
def _determine_heating_mode(solar_gen, electrical_storage_action):
    """
    Decision tree:
    1. Solar available (solar_gen > 0.05 kWh) → Use electrical heating
       Rationale: Leverage free solar energy
    
    2. Battery discharging (action < 0) → Use electrical heating
       Rationale: Consume stored solar energy
    
    3. Battery charging (action > 0) → Use fuel heating
       Rationale: Preserve electrical energy for storage, use cheaper fuel
    
    Returns: 'electrical' or 'fuel'
    """
    if electrical_storage_action < 0 or solar_gen > 0.05:
        return 'electrical'  # Use heat pump
    else:
        return 'fuel'  # Use gas boiler
```

**Benefits of this approach**:
- ✅ Maximizes solar self-consumption
- ✅ Prioritizes efficient heat pump when renewable energy available
- ✅ Falls back to fuel during grid charging periods (cost optimization)
- ✅ Simple, interpretable rules that perform well

#### **Features**

- **Adaptive temperature control**: Responds to deviations from setpoint with proportional urgency
- **Separate storage control**: Independent management of heating/cooling/DHW/electrical storage
- **Deadband logic**: Avoids unnecessary cycling (±0.5-1.0°C around setpoint)
- **Anti-windup mechanisms**: Limits integral accumulation to prevent overshoot
- **Stateful operation**: Maintains integral error history across time steps
- **Baseline performance**: Provides interpretable benchmark for learning-based methods

#### **Temperature Control (PI Algorithm)**

```python
def _calculate_pi_action(error, integral_key):
    """
    Proportional-Integral control for precise temperature regulation.
    
    Parameters:
    -----------
    error: float
        Temperature error (setpoint - current)
        Positive = need heating, Negative = too warm
    
    Returns:
    --------
    action: float (0.0-1.0)
        Device power setpoint
    
    Logic:
    ------
    1. If |error| ≤ deadband (e.g., 0.5°C):
       - Reset integral term to 0
       - Return action = 0.0 (no heating/cooling needed)
    
    2. If error > deadband:
       - P-term = K_p × error (immediate response)
       - I-term = K_i × Σ(error) (accumulated error correction)
       - Apply anti-windup: limit integral to ±10.0
       - Combine: action = P-term + I-term
       - Clamp to [min_power, max_power] range
    
    3. If error < -deadband:
       - Return action = 0.0 (setpoint exceeded)
       - Continue accumulating integral (for cooling logic)
    """
    if abs(error) <= temp_deadband:
        integral_errors[integral_key] = 0.0
        return 0.0
    
    if error > 0.0:
        # Need heating/cooling
        p_term = K_p × error
        integral_errors[integral_key] += error
        integral_errors[integral_key] = clamp(integral_errors[integral_key], 
                                               -integral_limit, +integral_limit)
        i_term = K_i × integral_errors[integral_key]
        
        action = p_term + i_term
        return clamp(action, min_power, max_power)
    else:
        return 0.0
```

**Example**: 
- Current temp: 18°C, Setpoint: 21°C, Deadband: 0.5°C
- Error = 21 - 18 = 3°C (outside deadband)
- P-term = 0.2 × 3 = 0.6
- I-term = 0.01 × 15 = 0.15 (assuming accumulated error of 15)
- Action = 0.6 + 0.15 = 0.75 (75% heating power)

#### **Thermal Storage Management**

The controller uses **error-proportional discharge** and **solar-based charging**:

```python
def _calculate_storage_action(storage_soc, heating_error):
    """
    Smart thermal storage control with hysteresis.
    
    Charging Logic:
    ---------------
    Conditions:
    - heating_error < 0.01 (no heating demand)
    - storage_soc < (1.0 - charge_threshold) (not full, e.g., < 90%)
    
    Action: Charge at maximum rate (1.0)
    Rationale: Store excess solar when not needed for heating
    
    Discharging Logic:
    ------------------
    Conditions:
    - heating_error > temp_deadband (need heat, e.g., error > 0.5°C)
    - storage_soc > discharge_threshold (have charge, e.g., > 30%)
    
    Action: Discharge proportional to error
    - discharge = K_p × (error - deadband)
    - Capped by max_discharge_rate (e.g., 0.10)
    - Tapered by available SOC to prevent over-discharge
    
    Rationale: Use stored energy when heating needed, proportional to urgency
    
    Idle:
    -----
    Otherwise: action = 0.0 (hold current state)
    """
    # Charging
    if heating_error < 0.01 and storage_soc < 0.9:
        return 1.0  # Full charge
    
    # Discharging (proportional to error)
    if heating_error > temp_deadband and storage_soc > 0.3:
        discharge = K_p × (heating_error - temp_deadband)
        discharge = min(discharge, max_discharge_rate)
        
        # Taper by available SOC
        available_factor = (storage_soc - 0.3) / (1.0 - 0.3)
        discharge = min(discharge, max_discharge_rate × available_factor)
        
        return -discharge  # Negative = discharge
    
    # Idle
    return 0.0
```

**Key Features**:
- **Proportional discharge**: More discharge when error is larger (emergency heating)
- **SOC tapering**: Discharge rate decreases as storage depletes (prevents deep discharge)
- **Hysteresis**: Separate thresholds for charging (90%) and discharging (30%) prevent oscillation

#### **Electrical Battery Control**

Simple time-of-use strategy (can be customized with `battery_action_map`):

```python
def battery_control(hour):
    """
    Default battery strategy:
    - 9:00-21:00 (day): Discharge at -0.08 (support daytime loads)
    - 1:00-8:00, 22:00-24:00 (night): Charge at +0.091 (store cheap/solar energy)
    """
    if 9 <= hour <= 21:
        return -0.08  # Discharge during day
    elif (1 <= hour <= 8) or (22 <= hour <= 24):
        return 0.091  # Charge during night
    else:
        return 0.0
```

**Integration with heating mode**:
- When battery charging → Use fuel heating (preserve electrical energy)
- When battery discharging → Use electrical heating (consume stored solar)

#### **Complete Control Flow**

```
For each time step:

1. Read Observations
   ├─ Indoor temperature
   ├─ Heating/cooling setpoints
   ├─ Solar generation
   ├─ Storage SOC (thermal, electrical)
   └─ Hour of day

2. Calculate PI Control Signal (ONCE)
   ├─ heating_error = T_setpoint - T_indoor
   ├─ heating_action = PI_control(heating_error)
   └─ [Same signal used for both electric and fuel devices]

3. Determine Heating Mode
   ├─ Get battery action (charge/discharge)
   ├─ Check solar availability
   └─ mode = 'electrical' or 'fuel'

4. Calculate Storage Actions
   ├─ Electrical battery: Time-of-use schedule
   ├─ Thermal storage: Error-proportional + solar-based
   └─ Cooling storage: Simple schedule

5. Route Actions to Devices
   ├─ IF mode == 'electrical':
   │  ├─ heating_device = heating_action
   │  └─ heating_fuel_device = 0.0
   │
   └─ IF mode == 'fuel':
      ├─ heating_device = 0.0
      └─ heating_fuel_device = heating_action

6. Apply Actions to Environment
   └─ Return all device actions

Key: The SAME PI control signal is calculated once and routed
     to the appropriate device based on solar/battery state.
     This ensures consistent temperature control regardless
     of which energy source is active.
```

#### **Tunable Parameters**

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `kp` | 0.2 | 0.1-0.5 | Proportional gain (responsiveness) |
| `ki` | 0.01 | 0.001-0.05 | Integral gain (steady-state accuracy) |
| `temp_deadband` | 1.0°C | 0.5-2.0°C | Temperature tolerance before action |
| `integral_limit` | 10.0 | 5.0-20.0 | Anti-windup threshold |
| `storage_charge_threshold` | 0.1 | 0.0-0.3 | SOC margin for charging (90% = 1.0-0.1) |
| `storage_discharge_threshold` | 0.3 | 0.2-0.5 | Minimum SOC before discharge stops |
| `storage_charge_rate` | 0.15 | 0.1-0.3 | Maximum charge power |
| `storage_discharge_rate` | 0.10 | 0.05-0.2 | Maximum discharge power |

#### **Advantages as Baseline**

✅ **Interpretable**: Every decision has clear logic  
✅ **No training required**: Works immediately out-of-the-box  
✅ **Stable**: Proven control theory with anti-windup  
✅ **Solar-aware**: Automatically optimizes for renewable energy  
✅ **Multi-energy**: Demonstrates fuel-electric switching  
✅ **Benchmark**: Provides performance target for RL methods  

### 4. **Multi-Objective Custom Reward Functions** 🎯

MESLearn provides two advanced reward functions that balance multiple competing objectives:

#### **A. ComfortCostCarbonReward** (Primary)

Balances thermal comfort, economic cost, and environmental impact:

```python
reward = (1-β) × (α×comfort + cost) - β × (γ×district_peak + district_carbon)
```

**Components**:

1. **Comfort Term** (α × comfort):
   ```python
   comfort = {
       0,              if T_setpoint - band ≤ T_indoor ≤ T_setpoint + band
       -(ΔT)²,         otherwise
   }
   ```
   - Zero penalty within comfort zone
   - Quadratic penalty for temperature violations
   - HVAC mode-aware (different logic for cooling/heating/auto)

2. **Cost Term** (cost):
   ```python
   cost = price_elec × net_elec_consumption + price_fuel × net_fuel_consumption
   ```
   - Combined electricity and fuel expenses
   - Encourages consumption during low-price periods
   - Incentivizes fuel switching when economical

3. **District Peak Penalty** (γ × district_peak):
   ```python
   district_peak = (Σ net_consumption_i)² / n_buildings^γ
   ```
   - Penalizes simultaneous high consumption across buildings
   - Encourages load balancing and coordination
   - Scaled by number of buildings to maintain consistent magnitude

4. **Carbon Emission Term** (district_carbon):
   ```python
   district_carbon = carbon_elec × Σ net_elec_i + carbon_fuel × Σ net_fuel_i
   ```
   - Total district-level emissions
   - Promotes cleaner energy usage
   - Considers both electricity and fuel carbon factors

**Parameters**:
- **α (alpha)**: Weight for comfort vs cost tradeoff (typically 0.5-2.0)
- **β (beta)**: Balance between local and district objectives (0.0-1.0)
  - `β = 0.0`: Purely local optimization (each building independent)
  - `β = 0.5`: Equal weight to local and district objectives
  - `β = 1.0`: Purely district-level optimization
- **γ (gamma)**: District penalty scaling exponent (typically 1.0-3.0)
  - Higher values increase coordination pressure

**Use Cases**:
- **Comfort priority**: `α=2.0, β=0.2, γ=1.0`
- **Cost priority**: `α=0.5, β=0.3, γ=2.0`
- **Environmental priority**: `α=1.0, β=0.8, γ=2.0`
- **Balanced**: `α=1.0, β=0.5, γ=2.0`

#### **B. ComfortConsumptionDistrictRewardFixed** (Simplified)

Focuses on comfort and consumption without explicit cost/carbon terms:

```python
reward = (1-β) × (comfort + consumption) + β × district_penalty
```

**Components**:

1. **Comfort Term**: Same as ComfortCostCarbonReward

2. **Consumption Term**:
   ```python
   consumption = min((-net_total_consumption)³, 0)
   ```
   - Cubic penalty on energy import (electricity + fuel)
   - Only penalizes import (export is neutral)
   - Steeper penalty for higher import levels

3. **District Penalty**:
   ```python
   district_penalty = -(Σ net_consumption_i)² / n_buildings^γ
   ```
   - Quadratic penalty on total district consumption
   - Encourages collective load reduction

**Parameters**:
- **β (beta)**: Single parameter balancing local vs district (0.0-1.0)
- **γ (gamma)**: District scaling exponent (typically 1.0-2.0)

**Advantages**:
- Simpler to tune (fewer parameters)
- Implicit cost minimization through consumption reduction
- Good for scenarios without price signals

#### **HVAC Mode-Aware Comfort Calculation**

Both reward functions intelligently handle different HVAC operating modes:

| HVAC Mode | Value | Description | Comfort Zone |
|-----------|-------|-------------|--------------|
| Off | 0 | No active heating/cooling | `setpoint ± band` |
| Cooling | 1 | Active cooling only | Below `setpoint_cooling + band` |
| Heating | 2 | Active heating only | Above `setpoint_heating - band` |
| Auto | 3 | Automatic mode switching | Between heating and cooling bands |

**Example Comfort Calculation**:
```python
# Mode 2 (Heating)
T_setpoint = 20°C
band = 2°C
T_indoor = 17°C

comfort_zone = [18°C, 22°C]
ΔT = 20 - 17 = 3°C
comfort_penalty = -(3²) = -9

# Mode 1 (Cooling)
T_setpoint = 22°C
T_indoor = 25°C

comfort_zone = [20°C, 24°C]
ΔT = 25 - 22 = 3°C
comfort_penalty = -(3²) = -9
```

### 5. **Comprehensive Energy Tracking** 📊

MESLearn provides detailed tracking of all energy flows:

#### **Electricity Metrics**
- `net_electricity_consumption`: Grid import (positive) or export (negative)
- `positive_net_electricity_consumption`: Only grid import (export = 0)
- `cooling_electricity_consumption`: Power for cooling systems
- `heating_electricity_consumption`: Electric heating power
- `dhw_electricity_consumption`: Hot water heating power
- `electrical_storage_electricity_consumption`: Battery charging power
- `solar_generation`: PV production
- `electricity_pricing`: Real-time grid price ($/kWh)
- `carbon_intensity`: Electricity emission factor (kg CO₂/kWh)

#### **Fuel Metrics**
- `net_fuel_consumption`: Natural gas usage (kWh)
- `energy_from_heating_fuel_device`: Heat output from gas boiler
- `fuel_pricing`: Natural gas price ($/kWh)
- `fuel_cost`: Total fuel expenses ($)
- `fuel_emissions`: CO₂ from gas combustion (kg)

#### **Combined Metrics**
- `total_energy = net_electricity + net_fuel`
- `total_cost = electricity_cost + fuel_cost`
- `total_emissions = electricity_emissions + fuel_emissions`

#### **Example Energy Flow**
```
Building Energy Balance at time t:

INPUTS:
├─ Grid electricity import: 5.2 kWh
├─ Solar generation: 3.1 kWh
└─ Fuel consumption: 8.5 kWh

USES:
├─ Cooling demand: 2.0 kWh (from electricity)
├─ Heating demand: 10.0 kWh (3.0 from heat pump, 7.0 from boiler)
├─ DHW demand: 1.5 kWh (from fuel)
├─ Non-shiftable load: 2.0 kWh (from electricity)
├─ Storage charging: 1.5 kWh electrical, 1.0 kWh heating
└─ Grid export: 0.8 kWh (excess solar)

NET RESULT:
├─ Net electricity: 5.2 - 0.8 = 4.4 kWh import
├─ Net fuel: 8.5 kWh consumption
└─ Total cost: 4.4 × $0.12 + 8.5 × $0.08 = $1.21
```

### 6. **Enhanced Storage Systems** 🔋

Support for multiple storage technologies with dual energy sources:

#### **Heating Storage**
- **Dual charging sources**: 
  - Electric device (heat pump): `energy_to_heating_storage_electric`
  - Fuel device (gas boiler): `energy_to_heating_storage_fuel`
- **Separate accounting**: Track electric vs fuel contributions
- **State of charge (SOC)**: Normalized capacity 0-1
- **Discharge**: `energy_from_heating_storage` for space heating
- **Efficiency losses**: Realistic charge/discharge losses

**Control Example**:
```python
# Agent chooses how much to charge from each source
action_heating_storage = 0.6  # Charge at 60% capacity

# System decides split based on price/efficiency
if elec_price × COP_heat_pump < fuel_price:
    charge_from_electric = 0.6 × capacity
    charge_from_fuel = 0.0
else:
    charge_from_electric = 0.3 × capacity
    charge_from_fuel = 0.3 × capacity
```

#### **Electrical Storage (BESS)**
- Battery energy storage systems
- Charge/discharge control: `energy_to_electrical_storage`, `energy_from_electrical_storage`
- Round-trip efficiency modeling (typically 85-95%)
- SOC tracking and constraints (0.1 ≤ SOC ≤ 0.9)
- Depth of discharge limits
- Cycle counting for degradation

#### **DHW (Domestic Hot Water) Storage**
- Hot water tank with thermal stratification
- Electric heating element: `energy_to_dhw_storage_electric`
- Fuel heating element: `energy_to_dhw_storage_fuel`  
- Temperature-based control (typically 50-60°C)
- Demand satisfaction tracking
- Thermal losses modeled

---

## 📚 AAC-MADRL Framework

The AAC-MADRL framework is described in:

> **S. Savino, T. Minella, Z. Nagy, A. Capozzoli (2025)**  
> *A scalable demand-side energy management control strategy for large residential districts based on an attention-driven multi-agent DRL approach*, **Applied Energy**.  
> [https://doi.org/10.1016/j.apenergy.2025.125993]

**Note**: The paper's case study was conducted on an earlier version of CityLearn without building temperature dynamics and with **3 control actions per building** (DHW storage, electrical storage, heating/cooling device). This repository uses the updated CityLearn API with **building dynamics** and adds a **4th control action (`heating_fuel_device`)** to enable multi-energy system optimization.

### Key Enhancement: From 3 to 4 Control Actions

AAC-MADRL is an **attention-driven, discrete-action, multi-agent actor–critic algorithm** for district-scale energy control, now extended to support multi-energy systems.

**Critical Update**: The action space has been expanded from the original 3 to 4 devices per building:

| Version | Devices Controlled | Action Combinations | Capability |
|---------|-------------------|---------------------|------------|
| **Original Paper** | 3 devices (DHW, Electrical, Heating/Cooling) | 21³ = 9,261 | Electric-only control |
| **MESLearn** | 4 devices (+**Heating Fuel Device**) | 21⁴ = 194,481 | **Multi-energy control** |

This **21× expansion** in action space enables agents to learn fuel-electric switching strategies, fundamentally transforming the problem from single-energy to multi-energy optimization.

### Key Characteristics

- **Paradigm**: **Centralized Training with Decentralized Execution (CTDE)**
  - Training: Centralized critic with full observability
  - Execution: Decentralized actors using only local information

- **Actors (πᵢ)**: One per building
  - Discrete probability distribution over actions
  - **4 devices per building**: DHW storage, electrical storage, heating device, **heating fuel device** ← **NEW**
  - 21 discretized action classes per device
  - Total action space per building: 21⁴ = 194,481 combinations

- **Centralized Critic (Q)**: Single critic for all agents
  - Evaluates joint state–action tuples: Q(s, a₁, …, aₙ)
  - **Multi-head attention mechanism**: Dynamically weights inter-agent dependencies
  - Learns which buildings' actions matter most for each agent
  - Handles the expanded 4-action space efficiently
  - Enables scalability to large districts (tested up to 50 buildings)

### Critic Architecture
![Attention-based Critic](docs/critic_architecture.png)

*The centralized critic embeds each agent's state–action pair, applies multi-head attention to extract relevant inter-agent dependencies, and aggregates attended features before Q-value regression.*

### Why Attention Matters

In district energy systems:
- **Spatial coupling**: Buildings share grid infrastructure
- **Temporal coupling**: Actions affect future states of other buildings
- **Heterogeneity**: Different building sizes, occupancy patterns, equipment

The attention mechanism learns:
- Which buildings' actions are correlated
- When coordination is critical (e.g., peak hours)
- How to balance local vs district objectives

---

## 🔧 Multi-Energy System Control Actions

### Critical Enhancement: Heating Fuel Device Action

**The most significant addition to MESLearn is the introduction of the `heating_fuel_device` control action**, which enables agents to control gas-fired heating equipment alongside electric devices. This transforms the framework from electric-only control to true multi-energy system management.

### Action Space for AAC-MADRL

Each building agent now controls **4 devices** (previously 3) with discrete action classes:

| Device | Action Classes | Range | Description | Status |
|--------|---------------|-------|-------------|--------|
| **DHW Storage** | 21 | [-1, 1] | Hot water tank charge/discharge | Existing |
| **Electrical Storage** | 21 | [-1, 1] | Battery charge/discharge | Existing |
| **Heating/Cooling Device** | 21 | [-1, 1] | Heat pump / AC modulation | Existing |
| **Heating Fuel Device** | 21 | [-1, 1] | **Gas boiler operation level** | **NEW** ✨ |

**Action Encoding**:
```
Action class:  0    5    10   15   20
Setpoint:     -1.0 -0.5  0.0  0.5  1.0
```

- `-1.0`: Device off / no operation
- `0.0`: Standby / minimal operation
- `+1.0`: Maximum operation / full power

**Key Impact**: The addition of the 4th action dimension (`heating_fuel_device`) significantly expands the action space:
- **Previous (electric-only)**: 21³ = 9,261 action combinations per building
- **Current (multi-energy)**: 21⁴ = 194,481 action combinations per building
- **Challenge**: 21× larger action space requires more sophisticated exploration and learning strategies
- **Benefit**: Enables true multi-energy optimization with fuel-electric switching

**Discretization Benefits**:
- Improved training stability (vs continuous)
- Realistic device operation (stepped controls)
- Easier exploration in high-dimensional space
- Better final performance (shown empirically)

### Action Space for SAC / MARLISA

Continuous action space with 4 dimensions per building:
- Each action ∈ [-1, 1]
- Directly mapped to device setpoints
- Total: 4 × n_buildings continuous actions

### Multi-Energy Control Strategy

**The core challenge**: With the addition of the `heating_fuel_device` action, agents must learn to make strategic decisions across a significantly larger action space (21× more combinations) while balancing multiple energy sources.

The agent learns to make strategic decisions:

#### 1. **Energy Source Selection** (Enabled by heating_fuel_device)
Choose between electric and fuel heating based on:

```python
Decision factors:
├─ Current prices: elec_price vs fuel_price
├─ Price forecasts: next 3 hours (fuel_pricing_predicted_*)
├─ Device efficiency: COP_heat_pump vs efficiency_boiler
├─ Carbon intensity: grid_carbon vs fuel_carbon
├─ Storage states: Can we use stored energy?
└─ Demand forecast: How much heating needed?

Example decision with heating_fuel_device:
# Agent sets heating_fuel_device action to control gas boiler
if (fuel_price < elec_price / COP) and (carbon_weight < cost_weight):
    action_heating_fuel_device = 0.8  # 80% gas boiler operation
    action_heating_device = 0.0       # Heat pump off
else:
    action_heating_fuel_device = 0.0  # Gas boiler off
    action_heating_device = 0.6       # 60% heat pump operation
```

#### 2. **Storage Optimization**
Decide when to charge/discharge based on:

```python
Storage strategy:
├─ Price arbitrage: Charge when cheap, discharge when expensive
├─ Demand anticipation: Pre-charge before high demand
├─ Solar alignment: Charge when PV production high
├─ Grid coordination: Avoid simultaneous charging across district
└─ SOC constraints: Keep within safe operating range

Example:
if (price_predicted_peak in next_3_hours) and (SOC > 0.5):
    discharge_storage()  # Use stored energy during peak
elif (solar_generation > demand) and (SOC < 0.8):
    charge_storage()  # Store excess solar
```

#### 3. **Multi-Objective Balancing**
Trade-off between competing goals:

```
Objective hierarchy:
1. Maintain comfort (hard constraint)
   → Keep temperature within setpoint ± band
   
2. Minimize cost (economic)
   → Use cheap energy when available
   → Leverage storage for price arbitrage
   → Choose efficient devices
   
3. Reduce emissions (environmental)
   → Prefer low-carbon electricity times
   → Use efficient heat pumps over boilers when grid is clean
   
4. District coordination (system-level)
   → Avoid peak coincidence across buildings
   → Balance aggregate load
   → Enable grid services
```

**Example Multi-Objective Decision with heating_fuel_device**:
```
Scenario: Cold winter evening
├─ Temperature: 18°C (setpoint: 21°C) → COMFORT PRIORITY
├─ Electricity price: HIGH ($0.25/kWh)
├─ Fuel price: LOW ($0.08/kWh)
├─ Carbon intensity: Medium (0.5 kg/kWh)
└─ District load: Already high

Agent Actions (4 control outputs):
1. action_heating_fuel_device = 0.9     ← Use gas boiler at 90% (cheap, fast heating)
2. action_heating_storage = 0.6         ← Charge heating storage from gas
3. action_heating_device = 0.0          ← Keep heat pump off (expensive electricity)
4. action_electrical_storage = -0.4     ← Discharge battery to help other loads

Result: 
✓ Comfort restored quickly (gas boiler high power)
✓ Cost minimized (cheap fuel vs expensive electricity)
✓ District peak not worsened (no electric heating during peak)
✓ Prepared for later (heating storage charged)
```

---

## 🎓 Training Examples

### AAC-MADRL (Multi-Energy with 4 Actions)
```bash
python train_aac_madrl.py \
  --dataset-name data/CA_20_dynamics/schema.json \
  --episodes 12 \
  --lr 1e-3 \
  --dhw-storage 21 \
  --electrical-storage 21 \
  --cooling-or-heating-device 21 \
  --heating-fuel-device 21 \              # ← NEW: 4th action dimension
  --beta 0.2 \
  --gamma 2.0 \
  --sim-start 0 \
  --sim-end 8759 \
  --wandb off
```

**Note**: The `--heating-fuel-device 21` parameter is the key addition that enables multi-energy control. Without this parameter, the agent would only control 3 devices (electric-only mode).

### SAC (Multi-Energy)
```bash
python train_sac.py \
  --dataset-name data/TX_10_dynamics/schema.json \
  --episodes 12 \
  --lr 3e-4 \
  --beta 0.2 \
  --gamma 2.0 \
  --sim-start 3624 \
  --sim-end 4343 \
  --wandb off
```

### MARLISA (Multi-Energy)
```bash
python train_marlisa.py \
  --dataset-name data/VT_10_dynamics/schema.json \
  --episodes 12 \
  --lr 3e-4 \
  --beta 0.3 \
  --gamma 1.5 \
  --sim-start 3624 \
  --sim-end 4343 \
  --wandb off
```

### RBC Baseline (PI Controller)
```bash
python deploy_model.py \
  --dataset-anchor data/CA_20_dynamics/schema.json \
  --model-type PI_RBC \
  --sim-start 0 \
  --sim-end 8759
```

### With Weights & Biases Logging
```bash
python train_aac_madrl.py \
  --dataset-name data/CA_20_dynamics/schema.json \
  --episodes 12 \
  --lr 1e-3 \
  --dhw-storage 21 \
  --electrical-storage 21 \
  --cooling-or-heating-device 21 \
  --heating-fuel-device 21 \
  --beta 0.2 \
  --gamma 2.0 \
  --wandb on \
  --wandb-project "meslearn-district-control" \
  --wandb-run-name "aac-madrl-ca20-beta0.2"
```

---

## 📊 Deployment & Evaluation

### Deploy Trained Model
```bash
python deploy_model.py \
  --dataset-anchor outputs/data/CA_20_dynamics/schema.json \
  --model-type AAC_MADRL \
  --lr 1e-3 \
  --beta 0.2 \
  --gamma 2.0 \
  --sim-start 0 \
  --sim-end 8759
```

### Output Structure
```
outputs/data/<DATASET>/obs/<ALGORITHM>/
├─ district_obs.csv          # Aggregated district metrics
├─ obs_building_0.csv        # Building 0 detailed observations
├─ obs_building_1.csv        # Building 1 detailed observations
├─ ...
├─ action_building_0.csv     # Building 0 control actions
├─ action_building_1.csv     # Building 1 control actions
└─ ...
```

### Key Performance Indicators (KPIs)

The framework automatically calculates comprehensive KPIs:

#### **Comfort KPIs**
- Comfort violations (hours outside setpoint ± band)
- Average temperature deviation
- Comfort violation severity

#### **Energy KPIs**
- Total electricity consumption (kWh)
- Total fuel consumption (kWh)
- Peak electricity demand (kW)
- Solar self-consumption ratio
- Load factor

#### **Economic KPIs**
- Total electricity cost ($)
- Total fuel cost ($)
- Total energy cost ($)
- Cost savings vs baseline (%)

#### **Environmental KPIs**
- Total CO₂ emissions (kg)
- Electricity emissions (kg)
- Fuel emissions (kg)
- Emission reduction vs baseline (%)

#### **District KPIs**
- Peak coincidence factor
- District load variance
- Ramping rate
- Grid export/import ratio

### Evaluation Script
```bash
python evaluate_kpi.py \
  --dataset CA_20_dynamics \
  --algorithms AAC_MADRL SAC MARLISA PI_RBC \
  --output results/kpi_comparison.csv
```

---

## 💡 Hyperparameter Guidelines

### Reward Function Parameters

**For ComfortCostCarbonReward**:
```python
# Comfort-focused (residential buildings)
alpha = 2.0      # High comfort weight
beta = 0.2       # Mostly local optimization
gamma = 1.0      # Moderate district penalty

# Cost-focused (commercial buildings)
alpha = 0.5      # Lower comfort weight
beta = 0.3       # More district coordination
gamma = 2.0      # Stronger peak shaving

# Environmental-focused (green buildings)
alpha = 1.0      # Balanced comfort
beta = 0.8       # Strong district coordination
gamma = 2.0      # Aggressive emission reduction
```

**For ComfortConsumptionDistrictRewardFixed**:
```python
# Balanced approach
beta = 0.2       # 80% local, 20% district
gamma = 2.0      # Quadratic district penalty

# Strong coordination
beta = 0.5       # 50-50 split
gamma = 3.0      # Cubic district penalty
```

### Learning Rates

Based on empirical results:
```python
AAC-MADRL: lr = 1e-3   # Stable with discrete actions
SAC:       lr = 3e-4   # Standard for continuous control
MARLISA:   lr = 3e-4   # Conservative for multi-agent
```

### Action Discretization

```python
# Optimal discretization for multi-energy systems
DHW_storage: 21 classes
Electrical_storage: 21 classes
Heating_device: 21 classes
Fuel_device: 21 classes  # ← NEW: Enables gas boiler control

# Total action space per building: 21^4 = 194,481 combinations

# Alternative (faster training, smaller action space, electric-only)
All_devices: 11 classes
# Only 3 devices controlled (no fuel device)
# Total action space: 11^3 = 1,331 combinations
```

**Impact of 4th Action Dimension**:
- **Exploration challenge**: 194,481 vs 9,261 actions (with 21 classes) or 1,331 (with 11 classes)
- **Learning benefit**: Can discover fuel-electric switching strategies
- **Performance**: Empirically shown to achieve better multi-objective optimization
- **Discretization rationale**: 21 classes provide fine-grained control while maintaining stability

---

## 📖 Citation

If you use MESLearn or reproduce these results, please cite:

```bibtex
@article{savino2025aac,
  title={A scalable demand-side energy management control strategy for large residential districts based on an attention-driven multi-agent DRL approach},
  author={Savino, S. and Minella, T. and Nagy, Z. and Capozzoli, A.},
  journal={Applied Energy},
  year={2025},
  doi={10.1016/j.apenergy.2025.125993}
}
```

---

## 📞 Contact & Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Contact: [Insert contact information]

---

## 📄 License

[Insert license information]

---

**Built with CityLearn 2.3.1 | Enhanced for Multi-Energy Systems**

