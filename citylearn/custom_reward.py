from typing import Any, List, Mapping, Union, Optional
import numpy as np
from citylearn.reward_function import RewardFunction


class ComfortConsumptionDistrictRewardFixed(RewardFunction):
    """
    Reward = (1 - beta) * (comfort_i + consumption_i) + beta * district
    - comfort_i: 0 dentro banda; fuori banda = -|Δ|^2
    - consumption_i: min(((-1)*net_i)^3, 0)  # penalizza solo import
    - district: -(sum_i net_i)^2              # penalità quadratica sul distretto
    """

    def __init__(self, env_metadata: Mapping[str, Any], beta: float, gamma: float, band: Optional[float] = None):
        super().__init__(env_metadata)
        self.beta = float(beta)
        self.band = band  # se None, usa o['comfort_band']
        self.gamma = float(gamma)

    # ---------- comfort helper ----------
    def _comfort_term(self, o: Mapping[str, Union[int, float]]) -> float:
        hvac_mode = int(o.get('hvac_mode', 0))
        Tin = float(o['indoor_dry_bulb_temperature'])
        band = self.band if self.band is not None else float(o['comfort_band'])
        if hvac_mode in (1, 2):
            sp = float(
                o['indoor_dry_bulb_temperature_cooling_set_point'] if hvac_mode == 1
                else o['indoor_dry_bulb_temperature_heating_set_point']
            )
            lo, hi = sp - band, sp + band
            if lo <= Tin <= hi:
                return 0.0
            delta = Tin - sp
            return -(delta ** 2)
        else:
            sp_c = float(o['indoor_dry_bulb_temperature_cooling_set_point'])
            sp_h = float(o['indoor_dry_bulb_temperature_heating_set_point'])
            assert sp_c == sp_h, "Set point di riscaldamento e raffreddamento devono essere uguali in modalità off"
            sp = sp_c
            lo, hi = sp - band, sp + band
            if lo <= Tin <= hi:
                return 0.0
            else:
                delta_above = max(Tin - hi, 0)
                delta_below = max(lo - Tin, 0)
                delta = delta_above + delta_below
            return -(delta ** 2)

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        nets_el = [float(o['net_electricity_consumption']) for o in observations]
        nets_fuel = [float(o['net_fuel_consumption']) for o in observations]
        nets = [nets_el[i] + nets_fuel[i] for i in range(len(observations))]

        comforts = [self._comfort_term(o) for o in observations]
        consumptions = [min(((-1.0) * net) ** 3, 0.0) for net in nets]

        district_net = sum(nets)
        district = district_net ** 2
        n_agents = len(observations)
        district /= (n_agents ** self.gamma)  # normalizza per il numero di agenti
        district *= -1.0  # penalità
        rewards = [10 * ((1.0 - self.beta) * (comforts[i] + consumptions[i]) + self.beta * district)
                   for i in range(n_agents)]

        if self.central_agent:
            return [float(sum(rewards))]
        else:
            return rewards

class ComfortCostCarbonReward(RewardFunction):
    """
    Multi-objective reward function balancing thermal comfort, electricity cost, and carbon emissions.

    Reward = alpha * comfort + beta * cost + gamma * carbon + delta * district_penalty

    Where:
    - comfort: Penalty for temperature deviation from comfort band
    - cost: Penalty for electricity consumption (import from grid)
    - carbon: Penalty based on carbon intensity and net consumption
    - district_penalty: Coordination term for grid stability

    Parameters
    ----------
    env_metadata : Mapping[str, Any]
        General static information about the environment
    alpha : float, default=0.3
        Weight for comfort term (0-1)
    beta : float, default=0.3
        Weight for cost/consumption term (0-1)
    gamma : float, default=0.3
        Weight for carbon emission term (0-1)
    delta : float, default=0.1
        Weight for district coordination term (0-1)
    band : Optional[float], default=None
        Comfort band around setpoint. If None, uses building's comfort_band
    consumption_exponent : float, default=3.0
        Exponent for consumption penalty (higher = more aggressive)
    carbon_exponent : float, default=2.0
        Exponent for carbon penalty
    normalize_agents : float, default=1.0
        Exponent for normalizing district penalty by number of agents
    """

    def __init__(
            self,
            env_metadata: Mapping[str, Any],
            alpha: float = 0.3,
            beta: float = 0.3,
            gamma: float = 0.3,
            delta: float = 0.1,
            band: Optional[float] = None,
            consumption_exponent: float = 3.0,
            carbon_exponent: float = 2.0,
            normalize_agents: float = 1.0
    ):
        super().__init__(env_metadata)

        # Validate weights sum approximately to 1
        total = alpha + beta + gamma + delta
        if not (0.99 <= total <= 1.01):
            print(f"Warning: Weights sum to {total:.3f}, not 1.0. Normalizing...")
            alpha, beta, gamma, delta = alpha / total, beta / total, gamma / total, delta / total

        self.alpha = float(alpha)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.delta = float(delta)
        self.band = band
        self.consumption_exponent = float(consumption_exponent)
        self.carbon_exponent = float(carbon_exponent)
        self.normalize_agents = float(normalize_agents)

    def _comfort_term(self, o: Mapping[str, Union[int, float]]) -> float:
        """
        Calculate comfort penalty based on temperature deviation from setpoint.

        Returns 0 if within comfort band, negative quadratic penalty otherwise.
        """
        hvac_mode = int(o.get('hvac_mode', 0))
        Tin = float(o['indoor_dry_bulb_temperature'])
        band = self.band if self.band is not None else float(o.get('comfort_band', 2.0))

        if hvac_mode in (1, 2):  # Cooling or Heating mode
            sp = float(
                o['indoor_dry_bulb_temperature_cooling_set_point'] if hvac_mode == 1
                else o['indoor_dry_bulb_temperature_heating_set_point']
            )
            lo, hi = sp - band, sp + band

            if lo <= Tin <= hi:
                return 0.0

            delta = abs(Tin - sp)
            return -(delta ** 2)

        else:  # HVAC off (mode 0)
            sp_c = float(o['indoor_dry_bulb_temperature_cooling_set_point'])
            sp_h = float(o['indoor_dry_bulb_temperature_heating_set_point'])
            band_c = sp_c + band
            band_h = sp_h - band

            # Within comfort range
            if band_h <= Tin <= band_c:
                return 0.0

            # Outside comfort range
            if Tin > band_c:
                delta = Tin - band_c
            else:
                delta = band_h - Tin

            return -(delta ** 2)

    def _cost_term(self, net_consumption: float) -> float:
        """
        Calculate cost penalty based on electricity consumption.

        Only penalizes import from grid (positive consumption).
        Export to grid (negative consumption) is not penalized.
        """
        if net_consumption > 0:
            return -(net_consumption ** self.consumption_exponent)
        else:
            # Optionally reward export (but keep it small to avoid gaming)
            return min(((-1.0) * net_consumption) ** self.consumption_exponent, 0.0)

    def _carbon_term(self, o: Mapping[str, Union[int, float]]) -> float:
        """
        Calculate carbon emission penalty.

        Carbon emissions = net_consumption * carbon_intensity
        Only penalize when importing from grid (positive net consumption)
        """
        net_consumption = float(o['net_electricity_consumption'])
        carbon_intensity = float(o.get('carbon_intensity', 0.5))  # kg CO2/kWh

        if net_consumption > 0:
            # Importing from grid - penalize based on carbon intensity
            carbon_emissions = net_consumption * carbon_intensity
            return -(carbon_emissions ** self.carbon_exponent)
        elif net_consumption < 0:
            # Exporting to grid - small reward for avoiding carbon
            # (assumes exported energy displaces grid carbon)
            carbon_avoided = abs(net_consumption) * carbon_intensity
            return min((carbon_avoided ** self.carbon_exponent) * 0.1, 0.5)
        else:
            return 0.0

    def _district_term(self, observations: List[Mapping[str, Union[int, float]]]) -> float:
        """
        Calculate district-level coordination penalty.

        Penalizes high aggregate grid demand to encourage load shifting.
        """
        nets = [float(o['net_electricity_consumption']) for o in observations]
        district_net = sum(nets)

        # Normalize by number of agents to make comparable across different scales
        n_agents = len(observations)
        normalized_district = district_net / (n_agents ** self.normalize_agents)

        # Quadratic penalty on positive district consumption
        if normalized_district > 0:
            return -(normalized_district ** 2)
        else:
            # Light penalty even for net export to encourage stability
            return -(abs(normalized_district) ** 2) * 0.1

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        """
        Calculate the multi-objective reward for each building/agent.

        Parameters
        ----------
        observations : List[Mapping[str, Union[int, float]]]
            List of building observations at current timestep

        Returns
        -------
        List[float]
            Reward for each agent (or single reward if central_agent=True)
        """
        n_agents = len(observations)
        nets = [float(o['net_electricity_consumption']) for o in observations]

        # Calculate individual terms for each building
        comfort_terms = [self._comfort_term(o) for o in observations]
        cost_terms = [self._cost_term(net) for net in nets]
        carbon_terms = [self._carbon_term(o) for o in observations]

        # Calculate shared district term
        district_term = self._district_term(observations)

        # Combine weighted terms
        rewards = [
            self.alpha * comfort_terms[i] +
            self.beta * cost_terms[i] +
            self.gamma * carbon_terms[i] +
            self.delta * district_term
            for i in range(n_agents)
        ]

        # Optional: Scale rewards for better learning
        # Multiply by 10 to make rewards more significant
        rewards = [r * 10.0 for r in rewards]

        if self.central_agent:
            return [float(sum(rewards))]
        else:
            return rewards


class AdaptiveComfortCostCarbonReward(ComfortCostCarbonReward):
    """
    Adaptive version that adjusts weights based on carbon intensity.

    Increases carbon penalty weight during high carbon intensity periods,
    and increases cost penalty during low carbon intensity periods.

    Parameters
    ----------
    env_metadata : Mapping[str, Any]
        General static information about the environment
    alpha : float, default=0.3
        Base weight for comfort term
    beta : float, default=0.3
        Base weight for cost term
    gamma : float, default=0.3
        Base weight for carbon term
    delta : float, default=0.1
        Weight for district term
    carbon_threshold_high : float, default=0.6
        Carbon intensity threshold for "high" (kg CO2/kWh)
    carbon_threshold_low : float, default=0.3
        Carbon intensity threshold for "low" (kg CO2/kWh)
    adaptation_strength : float, default=0.3
        How much to adjust weights (0-1)
    **kwargs : Additional arguments for parent class
    """

    def __init__(
            self,
            env_metadata: Mapping[str, Any],
            alpha: float = 0.3,
            beta: float = 0.3,
            gamma: float = 0.3,
            delta: float = 0.1,
            carbon_threshold_high: float = 0.6,
            carbon_threshold_low: float = 0.3,
            adaptation_strength: float = 0.3,
            **kwargs
    ):
        super().__init__(env_metadata, alpha, beta, gamma, delta, **kwargs)
        self.base_alpha = alpha
        self.base_beta = beta
        self.base_gamma = gamma
        self.carbon_threshold_high = carbon_threshold_high
        self.carbon_threshold_low = carbon_threshold_low
        self.adaptation_strength = adaptation_strength

    def _adjust_weights(self, avg_carbon_intensity: float):
        """Adjust weights based on current carbon intensity."""
        if avg_carbon_intensity >= self.carbon_threshold_high:
            # High carbon - prioritize carbon reduction
            adjust = self.adaptation_strength
            self.gamma = self.base_gamma + adjust
            self.beta = self.base_beta - adjust / 2
            self.alpha = self.base_alpha - adjust / 2

        elif avg_carbon_intensity <= self.carbon_threshold_low:
            # Low carbon - prioritize cost savings
            adjust = self.adaptation_strength
            self.beta = self.base_beta + adjust
            self.gamma = self.base_gamma - adjust / 2
            self.alpha = self.base_alpha - adjust / 2
        else:
            # Normal - use base weights
            self.alpha = self.base_alpha
            self.beta = self.base_beta
            self.gamma = self.base_gamma

        # Normalize weights
        total = self.alpha + self.beta + self.gamma + self.delta
        self.alpha /= total
        self.beta /= total
        self.gamma /= total
        self.delta /= total

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        """Calculate reward with adaptive weights."""
        # Get average carbon intensity across buildings
        carbon_intensities = [float(o.get('carbon_intensity', 0.5)) for o in observations]
        avg_carbon_intensity = np.mean(carbon_intensities)

        # Adjust weights based on carbon intensity
        self._adjust_weights(avg_carbon_intensity)

        # Calculate reward using parent method with adjusted weights
        return super().calculate(observations)
