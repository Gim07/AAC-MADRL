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
        """
        Valid values of hvac mode are 0, 1, 2, 3 to indicate off, cooling mode, heating mode, and automatic mode.
        """
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

    Reward = (1-β) * (alpha*comfort + cost) - β * (gamma*district_peak + district_carbon_emission)

    Parameters
    ----------
    env_metadata: Mapping[str, Any]:
        General static information about the environment.

    alpha: float
        Weight for comfort cost in the reward function.
    beta: float
        Weight balancing between local and district-level objectives.
    gamma: float
        Exponent for scaling district-level penalties.
    """

    def __init__(self, env_metadata: Mapping[str, Any], beta: float, gamma: float, band: Optional[float] = None):
        super().__init__(env_metadata)
        self.beta = float(beta)
        self.band = band  # se None, usa o['comfort_band']
        self.gamma = float(gamma)

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
        elif hvac_mode == 3: # automatic mode
            sp_c = float(o['indoor_dry_bulb_temperature_cooling_set_point'])
            sp_h = float(o['indoor_dry_bulb_temperature_heating_set_point'])

            assert sp_c == sp_h, "Set point di riscaldamento e raffreddamento devono essere uguali in modalità automatica"
            sp = sp_c
            band_high = sp + band
            band_low = sp - band

            # # Within comfort range
            # if band_low <= Tin <= band_high:
            #     return 0.0

            # Outside comfort range
            if Tin < band_low:
                delta = band_low - Tin
            elif Tin > band_high:
                delta = band_high - Tin
            else:
                delta = 0.0

            return -(delta ** 2)

        else:
            sp_c = float(o['indoor_dry_bulb_temperature_cooling_set_point'])
            sp_h = float(o['indoor_dry_bulb_temperature_heating_set_point'])
            assert sp_c == sp_h, "Set point di riscaldamento e raffreddamento devono essere uguali in modalità off"

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

    def _cost_term(self, o: Mapping[str, Union[int, float]]) -> float:
        """
        Calculate electricity cost penalty.

        Returns negative electricity cost.
        """
        electrical_pricing = float(o['electricity_pricing'])
        net_electricity_consumption = float(o['net_electricity_consumption'])
        electrical_cost = electrical_pricing * net_electricity_consumption

        fuel_pricing = float(o.get('fuel_pricing', 0.0))
        net_fuel_consumption = float(o.get('net_fuel_consumption', 0.0))
        fuel_cost = fuel_pricing * net_fuel_consumption

        return -(electrical_cost + fuel_cost)

    def _emission_term(self, o: Mapping[str, Union[int, float]]) -> float:
        """
        Calculate carbon emission penalty.

        Returns carbon emissions.
        """
        electrical_carbon_intensity = float(o['carbon_intensity'])
        net_electricity_consumption = float(o['net_electricity_consumption'])
        electrical_emission = electrical_carbon_intensity * net_electricity_consumption

        fuel_carbon_intensity = float(o.get('fuel_carbon_intensity', 1.95 / (13.889 * 0.671)))
        net_fuel_consumption = float(o.get('net_fuel_consumption', 0.0))
        fuel_emission = fuel_carbon_intensity * net_fuel_consumption

        return -(electrical_emission + fuel_emission)

    def _electricity_consumption_term(self, o: Mapping[str, Union[int, float]]) -> float:
        """
        Calculate total energy consumption penalty.

        Returns negative total energy consumption.
        """
        net_electricity_consumption = float(o['net_electricity_consumption'])

        return - net_electricity_consumption

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        r"""Calculates reward.

        Parameters
        ----------
        observations: List[Mapping[str, Union[int, float]]]
            List of all building observations at current :py:attr:`citylearn.citylearn.CityLearnEnv.
            time_step` that are got from calling :py:meth:`citylearn.building.Building.observations`.

        Returns
        -------
        reward: List[float]
            Reward for transition to current timestep.
        """

        term_rescaler = 10e-4

        comfort = [self._comfort_term(o) for o in observations]
        cost = [self._cost_term(o) for o in observations]
        emission = [self._emission_term(o) for o in observations]
        # electricity_consumption = [self._electricity_consumption_term(o) for o in observations]

        # district_compsumption = sum(electricity_consumption) / term_rescaler
        district_emission = sum(emission) / term_rescaler

        n_agents = len(observations)
        # district_compsumption /= (n_agents ** self.gamma)
        district_emission /= (n_agents ** self.gamma)

        # print("District consumption term:", district_compsumption)
        # print("District emission term:", district_emission)
        # print("Avg comfort:", np.mean(comfort))
        # print("Avg cost:", np.mean(cost))

        rewards = [((1 - self.beta) * (comfort[i] + cost[i]) +
                   self.beta * district_emission)
                   for i in range(n_agents)]

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
