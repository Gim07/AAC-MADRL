# MESLearn: Multi-Energy Systems Learning Framework

## 🌟 Overview

**MESLearn** (Multi-Energy Systems CityLearn) is an advanced extension of CityLearn 2.3.1 that enables **multi-energy system control** for district-scale demand-side management. This repository provides training and deployment scripts for multiple advanced controllers with support for **dual energy sources** (electricity and fuel).

### Available Controllers

- **AAC-MADRL** — *Actor-Attention-Critic Multi-Agent DRL*: Attention-based multi-agent actor–critic method for district-scale DSM
- **SAC** — *Soft Actor-Critic*: State-of-the-art model-free deep RL algorithm
- **MARLISA** — *Multi-Agent RL with Iterative Sequential Action selection*
- **RBC (Rule-Based Controller)** — *PI Controller*: Traditional baseline using proportional-integral control

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
- Fuel-based heating devices (e.g., gas boilers, furnaces)
- Independent fuel pricing structure
- Separate carbon emission factors
- Complementary operation with electric systems

#### **Key Advantages**
✅ **Flexibility**: Choose optimal energy source based on cost and availability  
✅ **Resilience**: Fallback to alternative energy during outages or price spikes  
✅ **Efficiency**: Leverage both networks for optimal building performance  
✅ **Realism**: Represents actual multi-energy building infrastructure  

### 2. **Enhanced Schema Configuration** 📋

The schema has been significantly expanded to support multi-energy systems:

#### **New Observations**
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
  },
  "carbon_intensity": {
    "active": true,
    "shared_in_central_agent": true,
    "description": "Grid electricity carbon emission factor (kg CO₂/kWh)"
  },
  "hvac_mode": {
    "active": true,
    "shared_in_central_agent": false,
    "description": "HVAC operating mode: 0=off, 1=cooling, 2=heating, 3=auto"
  },
  "comfort_band": {
    "active": false,
    "shared_in_central_agent": false,
    "description": "Acceptable temperature deviation from setpoint (°C)"
  }
}
```

#### **Key Schema Enhancements**

| Category | Feature | Description |
|----------|---------|-------------|
| **Pricing** | `fuel_pricing` | Real-time natural gas pricing |
| **Pricing** | `fuel_pricing_predicted_*` | 1-3 hour ahead fuel price forecasts |
| **Carbon** | `carbon_intensity` | Grid electricity carbon emission factor |
| **Energy** | `net_fuel_consumption` | Total fuel consumption tracking |
| **Devices** | `heating_fuel_device` | Gas boiler/furnace control action |
| **HVAC** | `hvac_mode` | 0=off, 1=cooling, 2=heating, 3=auto |
| **Comfort** | `comfort_band` | Acceptable temperature deviation (°C) |

#### **Building Device Configuration**
Buildings now specify **dual-source heating systems**:
- **Electric heating device**: Heat pump, electric resistance heating
- **Fuel heating device**: Gas boiler, furnace
- **Control strategy**: Agents decide which device to activate and at what capacity

### 3. **Advanced Rule-Based Controller (RBC)** 🎛️

A sophisticated **PI (Proportional-Integral) Controller** has been implemented as a robust baseline:

#### **Control Strategy**
The RBC uses classic feedback control theory:

```
Control Signal = K_p × error(t) + K_i × ∫error(t)dt
```

Where:
- `error(t) = T_setpoint - T_current`
- `K_p`: Proportional gain (immediate response)
- `K_i`: Integral gain (eliminates steady-state error)

#### **Features**
- **Adaptive control**: Responds to temperature deviations from setpoint
- **Separate storage control**: Independent management of heating/cooling/DHW storage
- **Fuel device activation**: Rule-based logic for gas boiler operation
- **Anti-windup mechanisms**: Prevents integral saturation
- **Baseline performance**: Provides benchmark for learning-based methods

#### **Storage Charging Logic**
```python
# Heating storage
if T_indoor < T_setpoint - band:
    charge_heating_storage = K_p × (T_setpoint - T_indoor) + K_i × ∫error dt
    
# Cooling storage  
if T_indoor > T_setpoint + band:
    charge_cooling_storage = K_p × (T_indoor - T_setpoint) + K_i × ∫error dt
    
# DHW storage
charge_dhw = constant_level  # Maintain hot water availability
```

#### **Fuel Device Activation**
```python
# Activate gas boiler when:
# 1. Temperature below setpoint
# 2. Electric heating insufficient
# 3. Fuel price favorable vs electricity

if (T_indoor < T_setpoint - threshold) and (fuel_price < elec_price × COP):
    activate_fuel_device()
```

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

**Note**: The paper's case study was conducted on an earlier version of CityLearn without building temperature dynamics. This repository uses the updated CityLearn API with **building dynamics and multi-energy system support**.

### Key Characteristics

AAC-MADRL is an **attention-driven, discrete-action, multi-agent actor–critic algorithm** for district-scale energy control.

- **Paradigm**: **Centralized Training with Decentralized Execution (CTDE)**
  - Training: Centralized critic with full observability
  - Execution: Decentralized actors using only local information

- **Actors (πᵢ)**: One per building
  - Discrete probability distribution over actions
  - 4 devices per building: DHW storage, electrical storage, heating device, **fuel device**
  - 21 discretized action classes per device
  - Total action space: 21⁴ = 194,481 combinations per building

- **Centralized Critic (Q)**: Single critic for all agents
  - Evaluates joint state–action tuples: Q(s, a₁, …, aₙ)
  - **Multi-head attention mechanism**: Dynamically weights inter-agent dependencies
  - Learns which buildings' actions matter most for each agent
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

### Action Space for AAC-MADRL

Each building agent controls **4 devices** with discrete action classes:

| Device | Action Classes | Range | Description |
|--------|---------------|-------|-------------|
| **DHW Storage** | 21 | [-1, 1] | Hot water tank charge/discharge |
| **Electrical Storage** | 21 | [-1, 1] | Battery charge/discharge |
| **Heating/Cooling Device** | 21 | [-1, 1] | Heat pump / AC modulation |
| **Heating Fuel Device** | 21 | [-1, 1] | Gas boiler operation level |

**Action Encoding**:
```
Action class:  0    5    10   15   20
Setpoint:     -1.0 -0.5  0.0  0.5  1.0
```

- `-1.0`: Maximum discharge / off
- `0.0`: Standby / neutral
- `+1.0`: Maximum charge / full power

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

The agent learns to make strategic decisions:

#### 1. **Energy Source Selection**
Choose between electric and fuel heating based on:

```python
Decision factors:
├─ Current prices: elec_price vs fuel_price
├─ Price forecasts: next 3 hours
├─ Device efficiency: COP_heat_pump vs efficiency_boiler
├─ Carbon intensity: grid_carbon vs fuel_carbon
├─ Storage states: Can we use stored energy?
└─ Demand forecast: How much heating needed?

Example decision:
if (fuel_price < elec_price / COP) and (carbon_weight < cost_weight):
    use_fuel_device()
else:
    use_electric_device()
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

**Example Multi-Objective Decision**:
```
Scenario: Cold winter evening
├─ Temperature: 18°C (setpoint: 21°C) → COMFORT PRIORITY
├─ Electricity price: HIGH ($0.25/kWh)
├─ Fuel price: LOW ($0.08/kWh)
├─ Carbon intensity: Medium (0.5 kg/kWh)
└─ District load: Already high

Decision:
1. ✓ Use fuel device (cheap, addresses comfort)
2. ✓ Charge heating storage from fuel (prepare for later)
3. ✗ Don't use electric heat pump (expensive, would increase district peak)
4. ✓ Discharge electrical battery (help with peak demand elsewhere)

Result: Comfort restored, cost minimized, district peak not worsened
```

---

## 🎓 Training Examples

### AAC-MADRL (Multi-Energy)
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
  --sim-start 0 \
  --sim-end 8759 \
  --wandb off
```

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
# Optimal discretization (from paper)
DHW_storage: 21 classes
Electrical_storage: 21 classes
Heating_device: 21 classes
Fuel_device: 21 classes

# Alternative (faster training, slightly worse performance)
All_devices: 11 classes
```

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

