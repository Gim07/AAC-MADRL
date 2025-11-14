from typing import Any, Mapping, List, Union
from citylearn.agents.base import Agent
from citylearn.citylearn import CityLearnEnv
from citylearn.building import Building

class RBC(Agent):
    r"""Base rule based controller class.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    
    Other Parameters
    ----------------
    **kwargs : Any
        Other keyword arguments used to initialize super class.
    """
    
    def __init__(self, env: CityLearnEnv, **kwargs: Any):
        super().__init__(env, **kwargs)

class HourRBC(RBC):
    r"""A hour-of-use rule-based controller.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    action_map: Union[Mapping[int, float], Mapping[str, Mapping[int, float]], List[Mapping[str, Mapping[int, float]]]], optional
        A 24-hour action map for each controlled device where the key is the hour between 1-24 and the value is the action.
        For storage systems, the value is negative for discharge and positive for charge where it ranges between [0, 1]. 
        Whereas, for cooling or heating devices, the value is positive for proportion of nominal power to make available and 
        ranges between [0, 1]. The action map can be parsed as a dictionary of hour keys mapped to action values 
        (:code:`Mapping[int, float]`). Alternatively, it can be parsed as a dictionary of devices 
        (:code:`Mapping[str, Mapping[int, float]]`) with their specific hour key to action value mapping 
        (:code:`Mapping[int, float]`). Finally, the action map can be defined for each agent especially in decentralized 
        setup as a list of device dictionary where each device dictionary (:code:`Mapping[str, Mapping[int, float]]`) 
        is for a specific decentralized (or centralized) agent. The HourRBC will return random actions if no map is provided.
    
    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """
    
    
    def __init__(self, env: CityLearnEnv, action_map: Union[List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[int, float]] = None, **kwargs: Any):
        super().__init__(env, **kwargs)
        self.action_map = action_map

    @property
    def action_map(self) -> List[Mapping[str, Mapping[int, float]]]:
        return self.__action_map
    
    @action_map.setter
    def action_map(self, action_map: Union[List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[int, float]]):
        if isinstance(action_map, list):
            assert len(action_map) == len(self.action_dimension), f'List of action maps must have same length as number of agents: {len(self.action_dimension)}.'

            for i, (m, n) in enumerate(zip(action_map, self.action_names)):
                n = list(set(n))
                self.__verify_action_map(n, m, index=i)
        
        elif isinstance(action_map, dict):
            if isinstance(list(action_map.values())[0], dict):
                action_names = [a_ for a in self.action_names for a_ in a]
                action_names = list(set(action_names))
                self.__verify_action_map(action_names, action_map)
                action_map = [{n_: action_map[n_] for n_ in list(set(n))} for n in self.action_names]

            else:
                action_map = [{n_: action_map for n_ in list(set(n))} for n in self.action_names]
        
        else:
            pass

        self.__action_map = action_map

    def predict(self, observations: List[List[float]], deterministic: bool = None) -> List[List[float]]:
        """Provide actions for current time step.

        Parameters
        ----------
        observations: List[List[float]]
            Environment observations
        deterministic: bool, default: False
            Wether to return purely exploitatative deterministic actions.

        Returns
        -------
        actions: List[List[float]]
            Action values
        """

        actions = []

        if self.action_map is None:
            actions = super().predict(observations, deterministic=deterministic)
        
        else:
            for m, a, n, o in zip(self.action_map, self.action_names, self.observation_names, observations):
                hour = o[n.index('hour')]
                actions_ = []

                for a_ in a:
                    actions_.append(m[a_][hour]) 
                
                actions.append(actions_)

            self.actions = actions
            self.next_time_step()
        
        return actions
    
    def __verify_action_map(self, action_names: List[str], action_map: Mapping[str, Mapping[int, float]], index: int = None):
        missing_actions = [a for a in action_names if a not in list(action_map.keys())]
        message = f'Undefined maps for actions: {missing_actions}'
        message += '.' if index is None else f' in building with index: {index}.'
        assert len(missing_actions) == 0, message

class BasicRBC(HourRBC):
    r"""A hour-of-use rule-based controller for heat-pump charged thermal energy storage systems that charges when COP is high.

    The actions are designed such that the agent charges the controlled storage system(s) by 9.1% of its maximum capacity every
    hour between 10:00 PM and 08:00 AM, and discharges 8.0% of its maximum capacity at every other hour. Cooling device is set
    to 40.0% of nominal power between between 10:00 PM and 08:00 AM and 80.0% at every other hour. Heating device is to 80.0% 
    of nominal power between between 10:00 PM and 08:00 AM and 40.0% at every other hour.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    
    Other Parameters
    ----------------
    **kwargs : Any
        Other keyword arguments used to initialize super class.
    """
    
    def __init__(self, env: CityLearnEnv, **kwargs: Any):
        super().__init__(env, **kwargs)

    @HourRBC.action_map.setter
    def action_map(self, action_map: Union[List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[int, float]]):
        if action_map is None:
            action_map = {}
            action_names = [a_ for a in self.action_names for a_ in a]
            action_names = list(set(action_names))

            for n in action_names:
                action_map[n] = {}
                
                if 'storage' in n:
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 9 <= hour <= 21:
                            value = -0.08
                        elif (1 <= hour <= 8) or (22 <= hour <= 24):
                            value = 0.091
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'cooling_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 9 <= hour <= 21:
                            value = 0.8
                        elif (1 <= hour <= 8) or (22 <= hour <= 24):
                            value = 0.4
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 9 <= hour <= 21:
                            value = 0.4
                        elif (1 <= hour <= 8) or (22 <= hour <= 24):
                            value = 0.8
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'cooling_or_heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if hour < 7:
                            value = 0.4
                        
                        elif hour < 21:
                            value = -0.4

                        else:
                            value = 0.8

                        action_map[n][hour] = value
                
                else:
                    raise ValueError(f'Unknown action name: {n}')

        HourRBC.action_map.fset(self, action_map)

class OptimizedRBC(BasicRBC):
    r"""A hour-of-use rule-based controller that is an optimized version of :py:class:`citylearn.agents.P_rbc.BasicRBC`
    where control actions have been selected through a search grid.

    The actions are designed such that the agent discharges the controlled storage system(s) by 2.0% of its 
    maximum capacity every hour between 07:00 AM and 03:00 PM, discharges by 4.4% of its maximum capacity 
    between 04:00 PM and 06:00 PM, discharges by 2.4% of its maximum capacity between 07:00 PM and 10:00 PM, 
    charges by 3.4% of its maximum capacity between 11:00 PM to midnight and charges by 5.532% of its maximum 
    capacity at every other hour.

    Cooling device makes available 70.0% of its nominal power every hour between 07:00 AM and 03:00 PM, 60.0% between 
    04:00 PM and 06:00 PM, 80.0% between 07:00 PM and 10:00 PM, 40.0% between 11:00 PM to midnight and 20.0% other hour.

    Heating device makes available 30.0% of its nominal power every hour between 07:00 AM and 03:00 PM, 40.0% between 
    04:00 PM and 06:00 PM, 60.0% between 07:00 PM and 10:00 PM, 70.0% between 11:00 PM to midnight and 80.0% other hour.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    
    Other Parameters
    ----------------
    **kwargs : Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv, **kwargs: Any):
        super().__init__(env, **kwargs)

    @HourRBC.action_map.setter
    def action_map(self, action_map: Union[List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[int, float]]):
        if action_map is None:
            action_map = {}
            action_names = [a_ for a in self.action_names for a_ in a]
            action_names = list(set(action_names))

            for n in action_names:
                action_map[n] = {}
                
                if 'storage' in n:
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 7 <= hour <= 15:
                            value = -0.02
                        elif 16 <= hour <= 18:
                            value = -0.044
                        elif 19 <= hour <= 22:
                            value = -0.024
                        elif 23 <= hour <= 24:
                            value = 0.034
                        elif 1 <= hour <= 6:
                            value = 0.05532
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'cooling_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 7 <= hour <= 15:
                            value = 0.7
                        elif 16 <= hour <= 18:
                            value = 0.6
                        elif 19 <= hour <= 22:
                            value = 0.8
                        elif 23 <= hour <= 24:
                            value = 0.4
                        elif 1 <= hour <= 6:
                            value = 0.2
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 7 <= hour <= 15:
                            value = 0.3
                        elif 16 <= hour <= 18:
                            value = 0.4
                        elif 19 <= hour <= 22:
                            value = 0.6
                        elif 23 <= hour <= 24:
                            value = 0.7
                        elif 1 <= hour <= 6:
                            value = 0.8
                        else:
                            value = 0.0

                        action_map[n][hour] = value

                elif n == 'cooling_or_heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if hour < 7:
                            value = 0.4
                        
                        elif hour < 21:
                            value = -0.4

                        else:
                            value = 0.8

                        action_map[n][hour] = value
                
                else:
                    raise ValueError(f'Unknown action name: {n}')

        HourRBC.action_map.fset(self, action_map)

class BasicBatteryRBC(BasicRBC):
    r"""A hour-of-use rule-based controller that is designed to take advantage of solar generation for charging.

    The actions are optimized for electrical storage (battery) such that the agent charges the controlled
    storage system(s) by 11.0% of its maximum capacity every hour between 06:00 AM and 02:00 PM, 
    and discharges 6.7% of its maximum capacity at every other hour. Cooling device is set
    to 70.0% of nominal power between between 06:00 AM and 02:00 PM and 30.0% at every other hour. 
    Heating device is to 30.0% of nominal power between between 06:00 AM and 02:00 PM and 70.0% at every other hour

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    
    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv, **kwargs: Any):
        super().__init__(env, **kwargs)

    @HourRBC.action_map.setter
    def action_map(self, action_map: Union[List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[int, float]]):
        if action_map is None:
            action_map = {}
            action_names = [a_ for a in self.action_names for a_ in a]
            action_names = list(set(action_names))

            for n in action_names:
                action_map[n] = {}
                
                if 'storage' in n:
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 6 <= hour <= 14:
                            value = 0.11
                        else:
                            value = -0.067

                        action_map[n][hour] = value

                elif n == 'cooling_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 6 <= hour <= 14:
                            value = 0.7
                        else:
                            value = 0.3

                        action_map[n][hour] = value

                elif n == 'heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if 6 <= hour <= 14:
                            value = 0.3
                        else:
                            value = 0.7

                        action_map[n][hour] = value

                elif n == 'cooling_or_heating_device':
                    for hour in Building.get_periodic_observation_metadata()['hour']:
                        if hour < 7:
                            value = 0.4
                        
                        elif hour < 21:
                            value = -0.4

                        else:
                            value = 0.8

                        action_map[n][hour] = value
                
                else:
                    raise ValueError(f'Unknown action name: {n}')

        HourRBC.action_map.fset(self, action_map)

class TemperatureBasedRBC(RBC):
    r"""A temperature-responsive rule-based controller that adjusts cooling/heating based on temperature difference.

    This controller dynamically adjusts the cooling and heating device power based on the real-time difference
    between indoor temperature and setpoint temperature. The control intensity is proportional to the
    temperature deviation, providing more responsive control than fixed hourly schedules.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    temp_deadband: float, optional
        Temperature deadband in degrees. No action is taken if temperature difference is within this range.
        Default is 0.5 degrees.
    max_temp_diff: float, optional
        Maximum expected temperature difference for scaling. Differences beyond this will be clamped.
        Default is 5.0 degrees.
    min_power: float, optional
        Minimum power output when device is active (0.0-1.0). Default is 0.1.
    max_power: float, optional
        Maximum power output (0.0-1.0). Default is 1.0.
    storage_action_map: Union[Mapping[int, float], Mapping[str, Mapping[int, float]], List[Mapping[str, Mapping[int, float]]]], optional
        Optional action map for storage devices following HourRBC format. If None, uses BasicRBC storage strategy.

    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv, temp_deadband: float = 2.0, max_temp_diff: float = 5.0,
                 min_power: float = 0.0, max_power: float = 1.0,
                 storage_action_map: Union[
                     List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[
                         int, float]] = None,
                 **kwargs: Any):
        super().__init__(env, **kwargs)
        self.temp_deadband = temp_deadband
        self.max_temp_diff = max_temp_diff
        self.min_power = min_power
        self.max_power = max_power
        self.storage_action_map = storage_action_map

    def predict(self, observations: List[List[float]], deterministic: bool = None) -> List[List[float]]:
        """Provide actions for current time step based on temperature difference.

        Parameters
        ----------
        observations: List[List[float]]
            Environment observations
        deterministic: bool, default: False
            Whether to return purely exploitative deterministic actions.

        Returns
        -------
        actions: List[List[float]]
            Action values
        """

        actions = []

        for a, n, o in zip(self.action_names, self.observation_names, observations):
            actions_ = []

            # Get current indoor temperature and setpoints if available
            indoor_temp = None
            cooling_setpoint = None
            heating_setpoint = None
            hour = None

            for i, obs_name in enumerate(n):
                if obs_name == 'indoor_dry_bulb_temperature':
                    indoor_temp = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_cooling_set_point':
                    cooling_setpoint = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_heating_set_point':
                    heating_setpoint = o[i]
                elif obs_name == 'hour':
                    hour = o[i]

            # Use default setpoints if not available in observations
            if cooling_setpoint is None:
                cooling_setpoint = 24.0  # Default cooling setpoint in Celsius
            if heating_setpoint is None:
                heating_setpoint = 20.0  # Default heating setpoint in Celsius

            for action_name in a:
                if 'storage' in action_name:
                    # Use storage action map if provided, otherwise use BasicRBC logic
                    if self.storage_action_map is not None:
                        if isinstance(self.storage_action_map, dict) and action_name in self.storage_action_map:
                            if hour is not None:
                                action_value = self.storage_action_map[action_name].get(hour, 0.0)
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0
                    else:
                        # Default BasicRBC storage logic
                        if hour is not None:
                            if 9 <= hour <= 21:
                                action_value = -0.08
                            elif (1 <= hour <= 8) or (22 <= hour <= 24):
                                action_value = 0.091
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_device':
                    if indoor_temp is not None and cooling_setpoint is not None:
                        temp_diff = indoor_temp - cooling_setpoint
                        if temp_diff > self.temp_deadband:
                            # Need cooling - scale power based on temperature difference
                            power_ratio = min(temp_diff / self.max_temp_diff, 1.0)
                            action_value = self.min_power + power_ratio * (self.max_power - self.min_power)
                        else:
                            action_value = 0.0
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'heating_device':
                    if indoor_temp is not None and heating_setpoint is not None:
                        temp_diff = heating_setpoint - indoor_temp
                        if temp_diff > self.temp_deadband:
                            # Need heating - scale power based on temperature difference
                            power_ratio = min(temp_diff / self.max_temp_diff, 1.0)
                            action_value = self.min_power + power_ratio * (self.max_power - self.min_power)
                        else:
                            action_value = 0.0
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_or_heating_device':
                    if indoor_temp is not None and cooling_setpoint is not None and heating_setpoint is not None:
                        cooling_diff = indoor_temp - cooling_setpoint
                        heating_diff = heating_setpoint - indoor_temp

                        if cooling_diff > self.temp_deadband:
                            # Need cooling (negative value)
                            power_ratio = min(cooling_diff / self.max_temp_diff, 1.0)
                            action_value = -(self.min_power + power_ratio * (self.max_power - self.min_power))
                        elif heating_diff > self.temp_deadband:
                            # Need heating (positive value)
                            power_ratio = min(heating_diff / self.max_temp_diff, 1.0)
                            action_value = self.min_power + power_ratio * (self.max_power - self.min_power)
                        else:
                            action_value = 0.0
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                else:
                    # For any unknown action types, default to 0
                    actions_.append(0.0)

            actions.append(actions_)

        self.actions = actions
        self.next_time_step()

        return actions

class PITemperatureController(RBC):
    r"""A PI (Proportional-Integral) controller for temperature regulation.

    This controller uses both proportional and integral control actions to maintain
    indoor temperature at setpoint. The integral term accumulates temperature error
    over time to eliminate steady-state offset.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    kp: float, optional
        Proportional gain. Higher values increase response to current error.
        Default is 0.2.
    ki: float, optional
        Integral gain. Higher values increase response to accumulated error.
        Default is 0.05.
    temp_deadband: float, optional
        Temperature deadband in degrees. No action is taken if temperature difference is within this range.
        Default is 0.5 degrees.
    max_temp_diff: float, optional
        Maximum expected temperature difference for proportional term scaling.
        Default is 5.0 degrees.
    integral_limit: float, optional
        Anti-windup limit for integral term. Prevents integral from growing too large.
        Default is 10.0.
    min_power: float, optional
        Minimum power output when device is active (0.0-1.0). Default is 0.0.
    max_power: float, optional
        Maximum power output (0.0-1.0). Default is 1.0.
    storage_action_map: Union[Mapping[int, float], Mapping[str, Mapping[int, float]], List[Mapping[str, Mapping[int, float]]]], optional
        Optional action map for storage devices following HourRBC format. If None, uses BasicRBC storage strategy.

    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv, kp: float = 0.2, ki: float = 0.005,
                 temp_deadband: float = 0.5,
                 integral_limit: float = 10.0,
                 min_power: float = 0.0, max_power: float = 1.0,
                 storage_action_map: Union[
                     List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[
                         int, float]] = None,
                 **kwargs: Any):
        super().__init__(env, **kwargs)
        self.kp = kp
        self.ki = ki
        self.temp_deadband = temp_deadband
        self.integral_limit = integral_limit
        self.min_power = min_power
        self.max_power = max_power
        self.storage_action_map = storage_action_map

        # Initialize integral error accumulators for each building and device type
        self.integral_errors = {}

    def reset(self):
        """Reset the controller state, including integral errors."""
        super().reset()
        self.integral_errors = {}

    def _get_integral_key(self, building_idx: int, device_type: str) -> str:
        """Generate a unique key for storing integral error."""
        return f"{building_idx}_{device_type}"

    def _calculate_pi_action(self, error: float, integral_key: str) -> float:
        """Calculate PI control action.

        Parameters
        ----------
        error: float
            Current temperature error (setpoint - actual for heating, actual - setpoint for cooling)
        integral_key: str
            Unique key for this device's integral error accumulator

        Returns
        -------
        action: float
            Control action value (0.0-1.0)
        """
        if abs(error) <= self.temp_deadband:
            # Within deadband - reset integral and return zero
            self.integral_errors[integral_key] = 0.0
            return 0.0

        # Initialize integral error if not exists
        if integral_key not in self.integral_errors:
            self.integral_errors[integral_key] = 0.0

        # Proportional term
        p_term = self.kp * error

        # Update integral error with anti-windup
        self.integral_errors[integral_key] += error
        self.integral_errors[integral_key] = max(min(self.integral_errors[integral_key],
                                                     self.integral_limit),
                                                 -self.integral_limit)

        # Integral term
        i_term = self.ki * self.integral_errors[integral_key]

        # Combined PI output
        pi_output = p_term + i_term

        # Scale to power range and clamp
        if pi_output > 0:
            action_value = self.min_power + pi_output * (self.max_power - self.min_power)
            action_value = max(min(action_value, self.max_power), self.min_power)
        else:
            action_value = 0.0

        return action_value

    def predict(self, observations: List[List[float]], deterministic: bool = None) -> List[List[float]]:
        """Provide actions for current time step using PI control.

        Parameters
        ----------
        observations: List[List[float]]
            Environment observations
        deterministic: bool, default: False
            Whether to return purely exploitative deterministic actions.

        Returns
        -------
        actions: List[List[float]]
            Action values
        """

        actions = []

        for building_idx, (a, n, o) in enumerate(zip(self.action_names, self.observation_names, observations)):
            actions_ = []

            # Get current indoor temperature and setpoints if available
            indoor_temp = None
            cooling_setpoint = None
            heating_setpoint = None
            hour = None
            heating_delta = None
            cooling_delta = None

            for i, obs_name in enumerate(n):
                if obs_name == 'indoor_dry_bulb_temperature':
                    indoor_temp = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_cooling_set_point':
                    cooling_setpoint = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_heating_set_point':
                    heating_setpoint = o[i]
                elif obs_name == 'hour':
                    hour = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_heating_delta':
                    heating_delta = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_cooling_delta':
                    cooling_delta = o[i]

            # Use default setpoints if not available in observations
            if cooling_setpoint is None:
                cooling_setpoint = 24.0  # Default cooling setpoint in Celsius
            if heating_setpoint is None:
                heating_setpoint = 20.0  # Default heating setpoint in Celsius

            for action_name in a:
                if 'electrical_storage' in action_name:
                    # Use storage action map if provided, otherwise use BasicRBC logic
                    if self.storage_action_map is not None:
                        if isinstance(self.storage_action_map, dict) and action_name in self.storage_action_map:
                            if hour is not None:
                                action_value = self.storage_action_map[action_name].get(hour, 0.0)
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0
                    else:
                        # Default BasicRBC storage logic
                        if hour is not None:
                            if 9 <= hour <= 21:
                                action_value = -0.08
                            elif (1 <= hour <= 8) or (22 <= hour <= 24):
                                action_value = 0.091
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0

                    actions_.append(action_value)

                if 'heating_storage' in action_name:
                    # Use storage action map if provided, otherwise use BasicRBC logic
                    if self.storage_action_map is not None:
                        if isinstance(self.storage_action_map, dict) and action_name in self.storage_action_map:
                            if hour is not None:
                                action_value = self.storage_action_map[action_name].get(hour, 0.0)
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0
                    else:
                        # Default BasicRBC storage logic
                        if hour is not None:
                            if 9 <= hour <= 21:
                                action_value = -0.08
                            elif (1 <= hour <= 8) or (22 <= hour <= 24):
                                action_value = 0.091
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_device':
                    if indoor_temp is not None and cooling_setpoint is not None:
                        error = indoor_temp - cooling_setpoint  # Positive when too hot
                        integral_key = self._get_integral_key(building_idx, 'cooling')
                        action_value = self._calculate_pi_action(error, integral_key)
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'heating_device':
                    if indoor_temp is not None and heating_setpoint is not None:
                        error = heating_setpoint - indoor_temp  # Positive when too cold
                        integral_key = self._get_integral_key(building_idx, 'heating')
                        action_value = self._calculate_pi_action(error, integral_key)
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'heating_fuel_device':
                    if indoor_temp is not None and heating_setpoint is not None:
                        error = heating_setpoint - indoor_temp  # Positive when too cold
                        integral_key = self._get_integral_key(building_idx, 'heating_fuel')
                        action_value = self._calculate_pi_action(error, integral_key)
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_or_heating_device':
                    if indoor_temp is not None and cooling_setpoint is not None and heating_setpoint is not None:
                        cooling_error = indoor_temp - cooling_setpoint
                        heating_error = heating_setpoint - indoor_temp

                        if cooling_error > self.temp_deadband:
                            # Need cooling (negative value)
                            integral_key = self._get_integral_key(building_idx, 'cooling_or_heating_cool')
                            # Reset heating integral when switching to cooling
                            heating_key = self._get_integral_key(building_idx, 'cooling_or_heating_heat')
                            self.integral_errors[heating_key] = 0.0

                            action_value = -self._calculate_pi_action(cooling_error, integral_key)

                        elif heating_error > self.temp_deadband:
                            # Need heating (positive value)
                            integral_key = self._get_integral_key(building_idx, 'cooling_or_heating_heat')
                            # Reset cooling integral when switching to heating
                            cooling_key = self._get_integral_key(building_idx, 'cooling_or_heating_cool')
                            self.integral_errors[cooling_key] = 0.0

                            action_value = self._calculate_pi_action(heating_error, integral_key)
                        else:
                            # Within deadband
                            action_value = 0.0
                            # Reset both integrals
                            cool_key = self._get_integral_key(building_idx, 'cooling_or_heating_cool')
                            heat_key = self._get_integral_key(building_idx, 'cooling_or_heating_heat')
                            self.integral_errors[cool_key] = 0.0
                            self.integral_errors[heat_key] = 0.0
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                else:
                    # For any unknown action types, default to 0
                    actions_.append(0.0)

            actions.append(actions_)

        self.actions = actions
        self.next_time_step()

        return actions

class PIController(Agent):
    r"""A hierarchical PI controller that leverages solar generation for optimal heating control.

    This controller implements a sophisticated control strategy:
    1. **Hierarchical Heating**: Uses electrical heating when solar is available or battery discharging,
       switches to fuel heating when battery is charging (to preserve solar energy).
    2. **Smart Storage Management**: Charges thermal storage when excess solar is available,
       discharges during peak demand or when heating is needed without solar.
    3. **PI Control**: Uses proportional-integral control for precise temperature regulation.

    Control Logic:
    - Solar available or battery discharging → Prioritize electrical heating device
    - Battery charging → Use fuel heating device (preserve electrical energy)
    - Thermal storage charging → When solar excess > heating demand
    - Thermal storage discharging → During high demand or low solar periods

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    kp: float, optional
        Proportional gain for temperature control. Default is 0.2.
    ki: float, optional
        Integral gain for temperature control. Default is 0.01.
    temp_deadband: float, optional
        Temperature deadband in degrees. Default is 0.5.
    integral_limit: float, optional
        Anti-windup limit for integral term. Default is 10.0.
    min_power: float, optional
        Minimum device power output (0.0-1.0). Default is 0.0.
    max_power: float, optional
        Maximum device power output (0.0-1.0). Default is 1.0.
    storage_charge_threshold: float, optional
        Solar generation ratio threshold for charging storage (0.0-1.0).
        Charges when solar > heating_demand * (1 + threshold). Default is 0.3.
    storage_discharge_threshold: float, optional
        State of charge threshold for allowing discharge (0.0-1.0). Default is 0.3.
    storage_charge_rate: float, optional
        Maximum charging rate for thermal storage (0.0-1.0). Default is 0.15.
    storage_discharge_rate: float, optional
        Maximum discharging rate for thermal storage (0.0-1.0). Default is 0.10.
    battery_action_map: Mapping[int, float], optional
        Hour-based action map for electrical battery. If None, uses BasicRBC logic.

    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv,
                 kp: float = 0.2,
                 ki: float = 0.01,
                 temp_deadband: float = 1,
                 integral_limit: float = 10.0,
                 min_power: float = 0.0,
                 max_power: float = 1.0,
                 storage_charge_threshold: float = 0.1,
                 storage_discharge_threshold: float = 0.3,
                 storage_charge_rate: float = 0.15,
                 storage_discharge_rate: float = 0.10,
                 battery_action_map: Mapping[int, float] = None,
                 **kwargs: Any):
        super().__init__(env, **kwargs)
        self.kp = kp
        self.ki = ki
        self.temp_deadband = temp_deadband
        self.integral_limit = integral_limit
        self.min_power = min_power
        self.max_power = max_power
        self.storage_charge_threshold = storage_charge_threshold
        self.storage_discharge_threshold = storage_discharge_threshold
        self.storage_charge_rate = storage_charge_rate
        self.storage_discharge_rate = storage_discharge_rate
        self.battery_action_map = battery_action_map

        # Controller state
        self.integral_errors = {}
        # Stores the state for the thermal storage hysteresis
        self._thermal_storage_state_map = {}

    def reset(self):
        """Reset the controller state."""
        super().reset()
        self.integral_errors = {}
        self._thermal_storage_state_map = {}

    def _get_integral_key(self, building_idx: int, device_type: str) -> str:
        """Generate unique key for integral error storage."""
        return f"{building_idx}_{device_type}"

    def _calculate_pi_action(self, error: float, integral_key: str) -> float:
        """Calculate PI control action.

        Parameters
        ----------
        error: float
            Current temperature error (setpoint - actual for heating, actual - setpoint for cooling)
        integral_key: str
            Unique key for this device's integral error accumulator

        Returns
        -------
        action: float
            Control action value (0.0-1.0)
        """
        if abs(error) <= self.temp_deadband:
            # Within deadband - reset integral and return zero
            self.integral_errors[integral_key] = 0.0
            return 0.0

        # Initialize integral error if not exists
        if integral_key not in self.integral_errors:
            self.integral_errors[integral_key] = 0.0
        if error > 0.0:
            # Proportional term
            p_term = self.kp * error

            # Update integral error with anti-windup
            self.integral_errors[integral_key] += error
            self.integral_errors[integral_key] = max(min(self.integral_errors[integral_key],
                                                         self.integral_limit),
                                                     -self.integral_limit)

            # Integral term
            i_term = self.ki * self.integral_errors[integral_key]

            # Combined PI output
            pi_output = p_term + i_term

            # Scale to power range and clamp
            if pi_output > 0:
                action_value = self.min_power + pi_output * (self.max_power - self.min_power)
                action_value = max(min(action_value, self.max_power), self.min_power)
            else:
                action_value = 0.0
        else:
            action_value = 0.0
            self.integral_errors[integral_key] += error

        return action_value

    def _determine_heating_mode(self, solar_gen: float, electrical_storage_action: float) -> str:
        """Determine which heating device to use based on solar/battery state.

        Returns:
        --------
        mode: str
            'electrical' if solar available or battery discharging,
            'fuel' if battery charging (preserve electrical energy)
        """
        # Battery is discharging (negative action) or solar is available
        # *** FIX: Check if solar_gen is greater than a small POSITIVE value ***
        if electrical_storage_action < 0 or solar_gen < -0.05:
            return 'electrical'
        else:
            return 'fuel'

    def _calculate_storage_action(self, storage_soc: float, heating_error: float) -> float:
        """
        Manages thermal storage based on solar and heating error.
        - Charges when: Excess solar is available and storage is not full.
        - Discharges when: Heating is required (error > 0) and storage has charge.
        """

        # --- 1. Define Thresholds & Estimates ---
        # Estimate heating demand (for solar charging logic)
        # This is a simple linear mapping; a 5-degree error is 1.0 demand

        # --- 2. Charging Logic ---
        # Charge only if the heating demand is 0 and the storage_soc is below 0.2
        charge_condition = (
            heating_error < 0.01  # No heating demand
            and storage_soc < (1.0 - self.storage_charge_threshold)  # Not full
        )

        if charge_condition:
            # Charge proportional to excess solar, capped by max rate
            return float(1.0)

        # --- 3. Discharging Logic (Error-Proportional) ---
        discharge_condition = (
                heating_error > self.temp_deadband  # Need heat (outside deadband)
                and storage_soc > self.storage_discharge_threshold  # Have charge
        )

        if discharge_condition:
            # Discharge proportional to the heating error
            # Use the controller's P-gain as the gain for storage discharge
            discharge_magnitude = self.kp * (heating_error - self.temp_deadband)

            # Clamp by max physical discharge rate
            discharge_magnitude = min(discharge_magnitude, self.storage_discharge_rate)

            # Clamp by available energy (don't discharge below threshold)
            # This makes the discharge taper off as SOC gets low
            if self.storage_discharge_threshold < 0.99:
                available_soc_factor = (storage_soc - self.storage_discharge_threshold) / (
                            1.0 - self.storage_discharge_threshold)
                discharge_magnitude = min(discharge_magnitude, self.storage_discharge_rate * available_soc_factor)
            else:
                # Avoid division by zero if threshold is 1.0
                discharge_magnitude = 0.0

            return -max(0, discharge_magnitude)  # Return as negative action

        # --- 4. Idle (Hold) ---
        return 0.0

    def predict(self, observations: List[List[float]], deterministic: bool = None) -> List[List[float]]:
        """Provide actions using solar-aware hierarchical PI control."""
        actions = []

        for building_idx, (a, n, o) in enumerate(
                zip(self.action_names, self.observation_names, observations)
        ):
            actions_ = []

            # --- 1. Extract observations ---
            indoor_temp = None
            heating_setpoint = None
            cooling_setpoint = None
            hour = None
            solar_gen = 0.0
            heating_storage_soc = 0.5
            electrical_storage_soc = 0.5

            for i, obs_name in enumerate(n):
                if obs_name == 'indoor_dry_bulb_temperature':
                    indoor_temp = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_heating_set_point':
                    heating_setpoint = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_cooling_set_point':
                    cooling_setpoint = o[i]
                elif obs_name == 'hour':
                    hour = int(o[i])
                elif obs_name == 'solar_generation':
                    solar_gen = abs(o[i])
                elif obs_name == 'heating_storage_soc' or obs_name == 'dhw_storage_soc':
                    heating_storage_soc = o[i]
                elif obs_name == 'electrical_storage_soc':
                    electrical_storage_soc = o[i]

            # Default setpoints
            if heating_setpoint is None:
                heating_setpoint = 20.0
            if cooling_setpoint is None:
                cooling_setpoint = 24.0
            if hour is None:
                hour = 12

            # --- 2. Calculate Storage and Mode ---
            electrical_storage_action = 0.0
            if self.battery_action_map is not None and hour in self.battery_action_map:
                electrical_storage_action = self.battery_action_map[hour]
            else:
                # Default BasicRBC battery logic
                if 9 <= hour <= 21:
                    electrical_storage_action = -0.08
                elif (1 <= hour <= 8) or (22 <= hour <= 24):
                    electrical_storage_action = 0.091

            heating_mode = self._determine_heating_mode(solar_gen, electrical_storage_action)

            # --- 3. Calculate ONE PI Action for Heating and Cooling ---
            heating_action_value = 0.0
            if indoor_temp is not None and heating_setpoint is not None:
                heating_error = heating_setpoint - indoor_temp
                integral_key = self._get_integral_key(building_idx, 'heating')  # Unified key
                heating_action_value = self._calculate_pi_action(heating_error, integral_key)
                if heating_error < 0.0 and heating_action_value !=0:
                    print('Warning: Heating action calculated when no heating needed!')
            cooling_action_value = 0.0
            if indoor_temp is not None and cooling_setpoint is not None:
                cooling_error = indoor_temp - cooling_setpoint
                # integral_key = self._get_integral_key(building_idx, 'cooling')  # Unified key
                # cooling_action_value = self._calculate_pi_action(cooling_error, integral_key)

            # --- 4. Process Actions *USING* the Calculated Values ---
            for action_name in a:
                if action_name == 'electrical_storage':
                    actions_.append(electrical_storage_action)

                elif action_name == 'heating_storage' or action_name == 'dhw_storage':
                    # Pass building_idx for stateful hysteresis
                    storage_action = self._calculate_storage_action(heating_storage_soc, building_idx)
                    actions_.append(storage_action)

                elif action_name == 'cooling_storage':
                    # Simple cooling storage logic (can be enhanced)
                    if 6 <= hour <= 14:
                        actions_.append(0.08)
                    else:
                        actions_.append(-0.05)

                # ==========================================================
                # THE FIX IS HERE:
                # Use the 'heating_action_value' calculated above.
                # Do NOT recalculate or reset any integrals.
                # ==========================================================
                elif action_name == 'heating_device':
                    # Electrical heating - use only when in electrical mode
                    if heating_mode == 'electrical':
                        actions_.append(heating_action_value)
                    else:
                        actions_.append(0.0)  # Off, but integral is NOT reset

                elif action_name == 'heating_fuel_device':
                    # Fuel heating - use only when in fuel mode
                    if heating_mode == 'fuel':
                        actions_.append(heating_action_value)
                    else:
                        actions_.append(0.0)  # Off, but integral is NOT reset

                elif action_name == 'cooling_device':
                    # Use the 'cooling_action_value' calculated above
                    actions_.append(cooling_action_value)
                # ==========================================================
                # END OF FIX
                # ==========================================================

                else:
                    # Unknown action type
                    actions_.append(0.0)

            actions.append(actions_)

        self.actions = actions
        self.next_time_step()

        return actions

class PIDTemperatureController(RBC):
    r"""A PID (Proportional-Integral-Derivative) controller for temperature regulation.

    This controller uses proportional, integral, and derivative control actions to maintain
    indoor temperature at setpoint. The proportional term responds to current error, the
    integral term eliminates steady-state offset, and the derivative term dampens oscillations
    and improves response time.

    Parameters
    ----------
    env: CityLearnEnv
        CityLearn environment.
    kp: float, optional
        Proportional gain. Higher values increase response to current error.
        Default is 0.2.
    ki: float, optional
        Integral gain. Higher values increase response to accumulated error.
        Default is 0.05.
    kd: float, optional
        Derivative gain. Higher values increase response to rate of change of error.
        Default is 0.1.
    temp_deadband: float, optional
        Temperature deadband in degrees. No action is taken if temperature difference is within this range.
        Default is 0.5 degrees.
    max_temp_diff: float, optional
        Maximum expected temperature difference for proportional term scaling.
        Default is 5.0 degrees.
    integral_limit: float, optional
        Anti-windup limit for integral term. Prevents integral from growing too large.
        Default is 10.0.
    derivative_filter: float, optional
        Low-pass filter coefficient for derivative term (0-1). Higher values = more filtering.
        Helps reduce noise sensitivity. Default is 0.1.
    min_power: float, optional
        Minimum power output when device is active (0.0-1.0). Default is 0.0.
    max_power: float, optional
        Maximum power output (0.0-1.0). Default is 1.0.
    storage_action_map: Union[Mapping[int, float], Mapping[str, Mapping[int, float]], List[Mapping[str, Mapping[int, float]]]], optional
        Optional action map for storage devices following HourRBC format. If None, uses BasicRBC storage strategy.

    Other Parameters
    ----------------
    **kwargs: Any
        Other keyword arguments used to initialize super class.
    """

    def __init__(self, env: CityLearnEnv, kp: float = 0.01, ki: float = 0.005, kd: float = 0.4,
                 temp_deadband: float = 0.5,
                 integral_limit: float = 10.0, derivative_filter: float = 0.15,
                 min_power: float = 0.0, max_power: float = 1.0,
                 storage_action_map: Union[
                     List[Mapping[str, Mapping[int, float]]], Mapping[str, Mapping[int, float]], Mapping[
                         int, float]] = None,
                 **kwargs: Any):
        super().__init__(env, **kwargs)
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.temp_deadband = temp_deadband
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter
        self.min_power = min_power
        self.max_power = max_power
        self.storage_action_map = storage_action_map

        # Initialize state variables for each building and device type
        self.integral_errors = {}
        self.previous_errors = {}
        self.filtered_derivatives = {}

    def reset(self):
        """Reset the controller state, including integral errors and previous errors."""
        super().reset()
        self.integral_errors = {}
        self.previous_errors = {}
        self.filtered_derivatives = {}

    def _get_state_key(self, building_idx: int, device_type: str) -> str:
        """Generate a unique key for storing controller state."""
        return f"{building_idx}_{device_type}"

    def _calculate_pid_action(self, error: float, state_key: str) -> float:
        """Calculate PID control action.

        Parameters
        ----------
        error: float
            Current temperature error (setpoint - actual for heating, actual - setpoint for cooling)
        state_key: str
            Unique key for this device's state variables

        Returns
        -------
        action: float
            Control action value (0.0-1.0)
        """
        if abs(error) <= self.temp_deadband:
            # Within deadband - reset all state and return zero
            self.integral_errors[state_key] = 0.0
            self.previous_errors[state_key] = 0.0
            self.filtered_derivatives[state_key] = 0.0
            return 0.0

        # Initialize state variables if not exists
        if state_key not in self.integral_errors:
            self.integral_errors[state_key] = 0.0
        if state_key not in self.previous_errors:
            self.previous_errors[state_key] = 0.0
        if state_key not in self.filtered_derivatives:
            self.filtered_derivatives[state_key] = 0.0

        # Proportional term
        p_term = self.kp * error

        # Update integral error with anti-windup
        self.integral_errors[state_key] += error
        self.integral_errors[state_key] = max(min(self.integral_errors[state_key],
                                                  self.integral_limit),
                                              -self.integral_limit)

        # Integral term
        i_term = self.ki * self.integral_errors[state_key]

        # Derivative term (rate of change of error)
        raw_derivative = error - self.previous_errors[state_key]

        # Apply low-pass filter to derivative to reduce noise sensitivity
        self.filtered_derivatives[state_key] = (
                self.derivative_filter * self.filtered_derivatives[state_key] +
                (1 - self.derivative_filter) * raw_derivative
        )

        # Derivative term
        d_term = self.kd * self.filtered_derivatives[state_key]

        # Update previous error for next iteration
        self.previous_errors[state_key] = error

        # Combined PID output
        pid_output = p_term + i_term + d_term

        # Scale to power range and clamp
        if pid_output > 0:
            action_value = self.min_power + pid_output * (self.max_power - self.min_power)
            action_value = max(min(action_value, self.max_power), self.min_power)
        else:
            action_value = 0.0

        return action_value

    def predict(self, observations: List[List[float]], deterministic: bool = None) -> List[List[float]]:
        """Provide actions for current time step using PID control.

        Parameters
        ----------
        observations: List[List[float]]
            Environment observations
        deterministic: bool, default: False
            Whether to return purely exploitative deterministic actions.

        Returns
        -------
        actions: List[List[float]]
            Action values
        """

        actions = []

        for building_idx, (a, n, o) in enumerate(zip(self.action_names, self.observation_names, observations)):
            actions_ = []

            # Get current indoor temperature and setpoints if available
            indoor_temp = None
            cooling_setpoint = None
            heating_setpoint = None
            hour = None

            for i, obs_name in enumerate(n):
                if obs_name == 'indoor_dry_bulb_temperature':
                    indoor_temp = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_cooling_set_point':
                    cooling_setpoint = o[i]
                elif obs_name == 'indoor_dry_bulb_temperature_heating_set_point':
                    heating_setpoint = o[i]
                elif obs_name == 'hour':
                    hour = o[i]

            # Use default setpoints if not available in observations
            if cooling_setpoint is None:
                cooling_setpoint = 24.0  # Default cooling setpoint in Celsius
            if heating_setpoint is None:
                heating_setpoint = 20.0  # Default heating setpoint in Celsius

            for action_name in a:
                if 'storage' in action_name:
                    # Use storage action map if provided, otherwise use BasicRBC logic
                    if self.storage_action_map is not None:
                        if isinstance(self.storage_action_map, dict) and action_name in self.storage_action_map:
                            if hour is not None:
                                action_value = self.storage_action_map[action_name].get(hour, 0.0)
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0
                    else:
                        # Default BasicRBC storage logic
                        if hour is not None:
                            if 9 <= hour <= 21:
                                action_value = -0.08
                            elif (1 <= hour <= 8) or (22 <= hour <= 24):
                                action_value = 0.091
                            else:
                                action_value = 0.0
                        else:
                            action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_device':
                    if indoor_temp is not None and cooling_setpoint is not None:
                        error = indoor_temp - cooling_setpoint  # Positive when too hot
                        state_key = self._get_state_key(building_idx, 'cooling')
                        action_value = self._calculate_pid_action(error, state_key)
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'heating_device':
                    if indoor_temp is not None and heating_setpoint is not None:
                        error = heating_setpoint - indoor_temp  # Positive when too cold
                        state_key = self._get_state_key(building_idx, 'heating')
                        action_value = self._calculate_pid_action(error, state_key)
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                elif action_name == 'cooling_or_heating_device':
                    if indoor_temp is not None and cooling_setpoint is not None and heating_setpoint is not None:
                        cooling_error = indoor_temp - cooling_setpoint
                        heating_error = heating_setpoint - indoor_temp

                        if cooling_error > self.temp_deadband:
                            # Need cooling (negative value)
                            state_key = self._get_state_key(building_idx, 'cooling_or_heating_cool')
                            # Reset heating state when switching to cooling
                            heating_key = self._get_state_key(building_idx, 'cooling_or_heating_heat')
                            self.integral_errors[heating_key] = 0.0
                            self.previous_errors[heating_key] = 0.0
                            self.filtered_derivatives[heating_key] = 0.0

                            action_value = -self._calculate_pid_action(cooling_error, state_key)

                        elif heating_error > self.temp_deadband:
                            # Need heating (positive value)
                            state_key = self._get_state_key(building_idx, 'cooling_or_heating_heat')
                            # Reset cooling state when switching to heating
                            cooling_key = self._get_state_key(building_idx, 'cooling_or_heating_cool')
                            self.integral_errors[cooling_key] = 0.0
                            self.previous_errors[cooling_key] = 0.0
                            self.filtered_derivatives[cooling_key] = 0.0

                            action_value = self._calculate_pid_action(heating_error, state_key)
                        else:
                            # Within deadband
                            action_value = 0.0
                            # Reset both states
                            cool_key = self._get_state_key(building_idx, 'cooling_or_heating_cool')
                            heat_key = self._get_state_key(building_idx, 'cooling_or_heating_heat')
                            self.integral_errors[cool_key] = 0.0
                            self.previous_errors[cool_key] = 0.0
                            self.filtered_derivatives[cool_key] = 0.0
                            self.integral_errors[heat_key] = 0.0
                            self.previous_errors[heat_key] = 0.0
                            self.filtered_derivatives[heat_key] = 0.0
                    else:
                        action_value = 0.0

                    actions_.append(action_value)

                else:
                    # For any unknown action types, default to 0
                    actions_.append(0.0)

            actions.append(actions_)

        self.actions = actions
        self.next_time_step()

        return actions