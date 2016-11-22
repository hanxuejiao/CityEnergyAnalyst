"""
============================
Hydraulic - thermal network
============================

"""
from __future__ import division
import time
import numpy as np
import pandas as pd
import math
import cea.globalvar as gv

__author__ = "Martin Mosteiro"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Martin Mosteiro" ]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "thomas@arch.ethz.ch"
__status__ = "Production"


def network_matrix_main(locator):
    """
    This function reads the existing node and pipe network from csv files (as provided for the Zug reference case) and
    produces an edge-node incidence matrix (as defined by Oppelt et al. "Dynamic thermo-hydraulic model of district
    cooling networks," Applied Thermal Engineering, 2016) as well as the length of each edge.

    :param locator: locator class

    :return:
        edge_node_matrix: matrix consisting of n rows (number of nodes) and e columns (number of edges)
        csv file stored in locator.pathNtwRes + '//' + EdgeNode_DH

    """

    t0 = time.clock()

    # import properties of distribution
    pipe_data = pd.read_csv(locator.get_pipes_DH_network)
    list_pipes = pipe_data['DC_ID']
    list_nodes = sorted(set(pipe_data['NODE1']).union(set(pipe_data['NODE2'])))
    edge_node_matrix = np.zeros((len(list_nodes),len(list_pipes)))
    for j in range(0, len(list_pipes)):
        for i in range(0,len(list_nodes)):
            if pipe_data['NODE2'][j] == list_nodes[i]:
                edge_node_matrix[i][j] = 1
            elif pipe_data['NODE1'][j] == list_nodes[i]:
                edge_node_matrix[i][j] = -1
    edge_node_df = pd.DataFrame(data=edge_node_matrix, index = list_nodes, columns = list_pipes)

    '''
    ntwk_length = pipes_tot_length.sum() * num_buildings_network / len(building_names) #gv.num_tot_buildings

    # empty vectors
    buildings = []
    substations = []
    Qcdata_netw_total = np.zeros(8760)
    mdotdata_netw_total = np.zeros(8760)
    Ecaf_netw_total = np.zeros(8760)
    Electr_netw_total = np.zeros(8760)
    mdot_heat_netw_all = np.zeros(8760)
    mdot_cool_netw_all = np.zeros(8760)
    Q_DH_building_netw_total = np.zeros(8760)
    Q_DC_building_netw_total = np.zeros(8760)
    sum_tret_mdot_heat = np.zeros(8760)
    sum_tret_mdot_cool = np.zeros(8760)
    mdot_heat_netw_min = np.zeros(8760) + 1E6
    mdot_cool_netw_min = np.zeros(8760) + 1E6
    iteration = 0
    for name in building_names:
        buildings.append(pd.read_csv(locator.get_demand_results_folder() + '//' + name + ".csv", usecols=['mcpdata_kWC',
                                                                                                          'Qcdataf_kWh',
                                                                                                          'Ecaf_kWh']))
        substations.append(pd.read_csv(locator.pathSubsRes + '//' + name + '_result' + ".csv",
                                       usecols=['Electr_array_all_flat', 'mdot_DH_result', 'mdot_DC_result',
                                                'Q_heating',
                                                'Q_dhw', 'Q_cool', 'T_return_DH_result', 'T_return_DC_result',
                                                'T_supply_DH_result']))

        Qcdata_netw_total += buildings[iteration].Qcdataf_kWh.values
        mdotdata_netw_total += buildings[iteration].mcpdata_kWC.values
        Ecaf_netw_total += buildings[iteration].Ecaf_kWh.values
        Electr_netw_total += substations[iteration].Electr_array_all_flat.values
        mdot_heat_netw_all += substations[iteration].mdot_DH_result.values
        mdot_cool_netw_all += substations[iteration].mdot_DC_result.values
        Q_DH_building_netw_total += (substations[iteration].Q_heating.values + substations[iteration].Q_dhw.values)
        Q_DC_building_netw_total += (substations[iteration].Q_cool.values)
        sum_tret_mdot_heat += substations[iteration].T_return_DH_result.values * substations[
            iteration].mdot_DH_result.values
        sum_tret_mdot_cool += substations[iteration].T_return_DC_result.values * substations[
            iteration].mdot_DC_result.values

        # evaluate minimum flows
        mdot_heat_netw_min = np.vectorize(calc_min_flow)(mdot_heat_netw_min,
                                                         substations[iteration].mdot_DH_result.values)
        mdot_cool_netw_min = np.vectorize(calc_min_flow)(mdot_cool_netw_min,
                                                         substations[iteration].mdot_DC_result.values)
        iteration += 1

    # calculate thermal losses of distribution
    T_sst_heat_return_netw_total = np.vectorize(calc_return_temp)(sum_tret_mdot_heat, mdot_heat_netw_all)

    T_sst_heat_supply_netw_total = np.vectorize(calc_supply_temp)(T_sst_heat_return_netw_total,
                                                                  Q_DH_building_netw_total,
                                                                  mdot_heat_netw_all,
                                                                  gv.cp, "DH")

    T_sst_cool_return_netw_total = np.vectorize(calc_return_temp)(sum_tret_mdot_cool,
                                                                  mdot_cool_netw_all)
    T_sst_cool_supply_netw_total = np.vectorize(calc_supply_temp)(T_sst_cool_return_netw_total,
                                                                  Q_DC_building_netw_total,
                                                                  mdot_cool_netw_all, gv.cp, "DC")

    Q_DH_losses_supply = np.vectorize(calc_piping_thermal_losses)(T_sst_heat_supply_netw_total,
                                                                  mdot_heat_netw_all, mdot_heat_netw_min,
                                                                  ntwk_length, gv.ground_temperature, gv.K_DH, gv.cp)

    Q_DH_losses_return = np.vectorize(calc_piping_thermal_losses)(T_sst_heat_return_netw_total,
                                                                  mdot_heat_netw_all, mdot_heat_netw_min,
                                                                  ntwk_length, gv.ground_temperature, gv.K_DH, gv.cp)
    Q_DH_losses = Q_DH_losses_supply + Q_DH_losses_return
    Q_DH_building_netw_total_inclLosses = Q_DH_building_netw_total + Q_DH_losses

    Q_DC_losses_supply = np.vectorize(calc_piping_thermal_losses)(T_sst_cool_supply_netw_total,
                                                                  mdot_cool_netw_all, mdot_cool_netw_min,
                                                                  ntwk_length, gv.ground_temperature, gv.K_DH, gv.cp)

    Q_DC_losses_return = np.vectorize(calc_piping_thermal_losses)(T_sst_heat_return_netw_total,
                                                                  mdot_cool_netw_all, mdot_cool_netw_min,
                                                                  ntwk_length, gv.ground_temperature, gv.K_DH, gv.cp)
    Q_DC_losses = Q_DC_losses_supply + Q_DC_losses_return
    Q_DC_building_netw_total_inclLosses = Q_DC_building_netw_total + Q_DC_losses

    T_sst_heat_return_netw_total_inclLosses = np.vectorize(calc_temp_withlosses)(T_sst_heat_return_netw_total,
                                                                                 Q_DH_losses_return, mdot_heat_netw_all,
                                                                                 gv.cp, "negative")

    T_sst_heat_supply_netw_total_inclLosses = np.vectorize(calc_temp_withlosses)(T_sst_heat_supply_netw_total,
                                                                                 Q_DH_losses_supply, mdot_heat_netw_all,
                                                                                 gv.cp, "positive")

    T_sst_cool_return_netw_total_inclLosses = np.vectorize(calc_temp_withlosses)(T_sst_cool_return_netw_total,
                                                                                 Q_DC_losses_return, mdot_cool_netw_all,
                                                                                 gv.cp, "positive")

    T_sst_cool_supply_netw_total_inclLosses = np.vectorize(calc_temp_withlosses)(T_sst_cool_supply_netw_total,
                                                                                 Q_DC_losses_supply, mdot_cool_netw_all,
                                                                                 gv.cp, "negative")

    day_of_max_heatmassflow_fin = np.zeros(8760)
    day_of_max_heatmassflow = find_index_of_max(mdot_heat_netw_all)
    day_of_max_heatmassflow_fin[:] = day_of_max_heatmassflow

    results = pd.DataFrame({"mdot_DH_netw_total": mdot_heat_netw_all,
                            "mdot_cool_netw_total": mdot_cool_netw_all,
                            "Q_DH_building_netw_total": Q_DH_building_netw_total_inclLosses,
                            "Q_DC_building_netw_total": Q_DC_building_netw_total_inclLosses,
                            "T_sst_heat_return_netw_total": T_sst_heat_return_netw_total_inclLosses,
                            "T_sst_cool_return_netw_total": T_sst_cool_return_netw_total_inclLosses,
                            "T_sst_heat_supply_netw_total": T_sst_heat_supply_netw_total_inclLosses,
                            "T_sst_cool_supply_netw_total": T_sst_cool_supply_netw_total_inclLosses,
                            "Qcdata_netw_total": Qcdata_netw_total,
                            "Ecaf_netw_total": Ecaf_netw_total,
                            "day_of_max_heatmassflow": day_of_max_heatmassflow,
                            "mdotdata_netw_total": mdotdata_netw_total,
                            "Electr_netw_total": Electr_netw_total,
                            "Q_DH_losses": Q_DH_losses,
                            "Q_DC_losses": Q_DC_losses})

    # the key depicts whether this is the distribution of all customers or a distribution of a group of them.
    fName_result = "Network_summary_result_" + key + ".csv"
    '''
    edge_node_df.to_csv(locator.pathNtwLayout + '//' + 'EdgeNode_DH.csv')


    print time.clock() - t0, "seconds process time for Network summary\n"

#============================
# Supply and return temperatures
# ============================

def calc_temp_withlosses(t0, Q, m, cp, case):
    """
    This function calculates the new temperature of the distribution including losses

    :param t0: current distribution temperature
    :param Q: load including thermal losses
    :param m: mass flow rate
    :param cp: specific heat capacity
    :param case: "positive": if there is an addition to the losses, :negative" otherwise
    :return:
        t1: new temperature of the distribution accounting for thermal losses in the grid
    """
    if m > 0:
        if case == "positive":
            t1 = t0 + Q / (m * cp)
        else:
            t1 = t0 - Q / (m * cp)
    else:
        t1 = 0
    return t1

def calc_return_temp(sum_t_m, sum_m):
    """
    This function calculates the return temperature of the distribution for a time step

    :param sum_t_m: sum of temperature times mass flow rate
    :param sum_m: sum of mass flow rate
    :return:
        tr: vector return temperature
    """
    if sum_m > 0:
        tr = sum_t_m / sum_m
    else:
        tr = 0
    return tr


def calc_supply_temp(tr, Q, m, cp, case):
    """
    This function calculates the supply temperature of the distribution for a time step.

    :param tr: current return temperature
    :param Q: load including thermal losses
    :param m: mass flow rate
    :param cp: specific heat capacity
    :param case:
    :return:
        ts: new temperature of the distribution accounting for thermal losses in the grid
    """
    if m > 0:
        if case == "DH":
            ts = tr + Q / (m * cp)
        else:
            ts = tr - Q / (m * cp)
    else:
        ts = 0
    return ts

#============================
# Thermal losses
#============================

def calc_piping_thermal_losses(Tnet, mmax, mmin, L, Tg, K, cp):
    """
    This function estimates the average thermal losses of a distribution for an hour of the year

    :param Tnet: current temperature of the pipe
    :param mmax: maximum mass flow rate in the pipe
    :param mmin: minimum mass flow rate in the pipe
    :param L: length of the pipe
    :param Tg: ground temperature
    :param K: linear transmittance coefficient (it accounts for insulation and pipe diameter)
    :param cp: specific heat capacity
    :return:
        Qloss: thermal lossess in the pipe.
    """
    if mmin != 1E6:  # control variable see function fn.calc_min_flow
        mavg = (mmax + mmin) / 2
        Tx = Tg + (Tnet - Tg) * math.exp(-K * L / (mavg * cp))
        Qloss = (Tnet - Tx) * mavg * cp
    else:
        Qloss = 0
    return Qloss

#============================
# Mass flow rates
#============================

def calc_min_flow(m0, m1):
    """
    This fucntion calculates the minimum flow of a distribution by comparison of two vectors.
    this is useful when lookig up at multiple buildings in a for loop.

    :param m0: last minimum mass flow rate
    :param m1: current minimum mass flow rate
    :return:
        mmin: new minimum mass flow rate
    """
    if m0 == 0:
        m0 = 1E6
    if m1 > 0:
        mmin = min(m0, m1)
    else:
        mmin = m0
    return mmin

def find_index_of_max(array):
    """
    Returns the index of an array on which the maximum value is at.

    Parameters
    ----------
    array : ndarray
        Array of observations. Each row represents a day and each column the hourly data of that day


    Returns
    -------

    max_index_hour : integer
        max_index_hour : tells on what hour it happens (hour of the year)

    to use: e.g. data_array[max_index_hour] will give the maximum data of the year

    """

    max_value = -abs(np.amax(array))

    max_index_hour = 0

    for k in range(len(array)):
        if array[k] > max_value:
            max_value = array[k]
            max_index_hour = k

    return max_index_hour

#============================
#test
#============================


def run_as_script(scenario_path=None):
    """
    run the whole network summary routine
    """
    import cea.globalvar
    import cea.inputlocator as inputlocator
    from geopandas import GeoDataFrame as gpdf
    from cea.utilities import epwreader
    from cea.resources import geothermal

    gv = cea.globalvar.GlobalVariables()

    if scenario_path is None:
        scenario_path = gv.scenario_reference

    locator = inputlocator.InputLocator(scenario_path=scenario_path)
    total_demand = pd.read_csv(locator.get_total_demand())
    building_names = pd.read_csv(locator.get_total_demand())['Name']
    weather_file = locator.get_default_weather()
    # add geothermal part of preprocessing
    T_ambient = epwreader.epw_reader(weather_file)['drybulb_C']
    gv.ground_temperature = geothermal.calc_ground_temperature(T_ambient.values, gv)

    key = 'all'
    network_matrix_main(locator)

    print 'test_network_matrix_main() succeeded'

if __name__ == '__main__':
    run_as_script()
