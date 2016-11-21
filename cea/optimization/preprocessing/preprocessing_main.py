"""
============================
pre-processing algorithm
============================

"""

from __future__ import division

import pandas as pd

import cea.optimization.preprocessing.other_services.processheat as process_heat
from cea.optimization.conversion_storage.master import summarize_network
from cea.optimization.preprocessing.decentralized_buildings import decentralized_buildings
from cea.optimization.preprocessing.other_services import electricity
from cea.resources import geothermal
from cea.technologies import substation
from cea.utilities import  epwreader

__author__ = "Jimeno A. Fonseca"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca", "Thuy-An Nguyen", "Tim Vollrath"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "thomas@arch.ethz.ch"
__status__ = "Production"


def preproccessing(locator, total_demand, building_names, weather_file, gv):
    '''
    This function aims at preprocessing all data for the optimization.

    :param locator: path to locator function
    :param total_demand: dataframe with total demand and names of all building in the area
    :param building_names: dataframe with names of all buildings in the area
    :param weather_file: path to wather file
    :param gv: path to global variables class
    :return:

    extraCosts: extra pareto optimal costs due to electricity and process heat (
    these are treated separately and not considered inside the optimization)
    extraCO2: extra pareto optimal emissions due to electricity and process heat (
    these are treated separately and not considered inside the optimization)
    extraPrim: extra pareto optimal primary energy due to electricity and process heat (
    these are treated separately and not considered inside the optimization)
    solar_features: extraction of solar features form the results of the solar technologies calculation.
    '''

    # GET ENERGY POTENTIALS
    # geothermal
    T_ambient = epwreader.epw_reader(weather_file)['drybulb_C']
    gv.ground_temperature = geothermal.calc_ground_temperature(T_ambient.values, gv)

    # solar
    print "Solar features extraction"
    solar_features = SolarFeatures(locator)

    # GET LOADS IN SUBSTATIONS
    # prepocess space heating, domestic hot water and space cooling to substation.
    print "Run substation model for each building separately"
    substation.substation_main(locator, total_demand, building_names, gv, Flag = True) # True if disconected buildings are calculated

    # GET COMPETITIVE ALTERNATIVES TO A NETWORK
    # estimate what would be the operation of single buildings only for heating.
    # For cooling all buildings are assumed to be connected to the cooling distribution on site.
    print "Heating operation pattern for single buildings"
    decentralized_buildings.decentralized_main(locator, building_names, gv)

    # GET DH NETWORK
    # at first estimate a distribution with all the buildings connected at it.
    print "Create distribution file with all buildings connected"
    summarize_network.network_main(locator, total_demand, building_names, gv, "all") #"_all" key for all buildings

    # GET EXTRAS
    # estimate the extra costs, emissions and primary energy of electricity.
    print "electricity"
    elecCosts, elecCO2, elecPrim = electricity.calc_pareto_electricity(locator, gv)

    # estimate the extra costs, emissions and primary energy for process heat
    print "Process-heat"
    hpCosts, hpCO2, hpPrim = process_heat.calc_pareto_Qhp(locator, total_demand, gv)

    extraCosts = elecCosts + hpCosts
    extraCO2 = elecCO2 + hpCO2
    extraPrim = elecPrim + hpPrim

    return extraCosts, extraCO2, extraPrim, solar_features


class SolarFeatures(object):
    def __init__(self, locator):
        self.PV_Peak = pd.read_csv(locator.pathSolarRaw + "/Pv.csv", usecols=["PV_kWh"]).values.max()
        self.SolarAreaPV = pd.read_csv(locator.pathSolarRaw + "/Pv.csv", usecols=["Area"]).values.max()
        self.PVT_Peak = pd.read_csv(locator.pathSolarRaw + "/PVT_35.csv", usecols=["PV_kWh"]).values.max()
        self.PVT_Qnom = pd.read_csv(locator.pathSolarRaw + "/PVT_35.csv", usecols=["Qsc_KWh"]).values.max()*1000
        self.SolarAreaPVT = pd.read_csv(locator.pathSolarRaw + "/PVT_35.csv", usecols=["Area"]).values.max()
        self.SC_Qnom = pd.read_csv(locator.pathSolarRaw + "/SC_75.csv", usecols=["Qsc_Kw"]).values.max()* 1000
        self.SolarAreaSC = pd.read_csv(locator.pathSolarRaw + "/SC_75.csv", usecols=["Area"]).values.max()
