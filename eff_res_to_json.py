from ROOT import TFile
import argparse
import yaml
import os
import re
import math
import json


parser = argparse.ArgumentParser()
parser.add_argument("config", help="Path to the YAML configuration file")
args = parser.parse_args()

with open(os.path.expandvars(args.config), 'r') as stream:
    try:
        params = yaml.full_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

CHIPS = params['CHIPS']
FILE_PATHS = params['FILE_PATHS']
NOISE_PATHS = params['NOISE_PATHS']
NSIGMANOISE = params['NSIGMANOISE']

for file_path_list, noise_path, chip in zip(FILE_PATHS, NOISE_PATHS, CHIPS):
    eff_list = []
    err_eff_up = []
    err_eff_low = []
    charge = []
    clustersize_list = []
    err_clustersize_list = []
    err_res = []
    res_x = []
    res_y = []

    #get apts Id
    root_file = TFile(file_path_list[0], "READ")
    subdir = root_file.Get("AnalysisDUT")
    key_list = subdir.GetListOfKeys()
    dir_list = []
    for key in key_list:
        if key.GetClassName() == "TDirectoryFile":
            dir_list.append(key.GetName())
    apts = dir_list[0]
    root_file.Close()

    noise_file = TFile(noise_path, "read")
    noise_values = noise_file.Get(
        "EventLoaderEUDAQ2/"+apts+"/hPixelRawValues")
    noise_rms = noise_values.GetStdDev()
    noise_file.Close()

    for file_path in file_path_list:
        input_file = TFile(file_path, "read")

        residualsX = input_file.Get(
            "AnalysisDUT/"+apts+"/local_residuals/residualsX")
        residualsY = input_file.Get(
            "AnalysisDUT/"+apts+"/local_residuals/residualsY")
        clusterSize = input_file.Get(
            "AnalysisDUT/"+apts+"/clusterSizeAssociated")
        efficiency = input_file.Get(
            "AnalysisEfficiency/"+apts+"/eTotalEfficiency")

        thr = int(re.findall(r'\d+', file_path)[-1])
        if thr < NSIGMANOISE*noise_rms:
            continue
        eff_list.append(100*efficiency.GetEfficiency(1))
        err_eff_up.append(100*efficiency.GetEfficiencyErrorUp(1))
        err_eff_low.append(100*efficiency.GetEfficiencyErrorLow(1))
        charge.append(thr)

        err_res.append(math.sqrt(residualsX.GetStdDevError()**2+residualsY.GetStdDevError()**2)/2.)
        res_x.append(residualsX.GetStdDev())
        res_y.append(residualsY.GetStdDev())

        clustersize_list.append(clusterSize.GetMean())
        err_clustersize_list.append(clusterSize.GetMeanError())

    info_dict = {
        "chip": chip,
        "noise_rms": noise_rms,
        "residuals_x_rms": res_x,
        "residuals_y_rms": res_y,
        "err_residuals": err_res,
        "err_clustersize": err_clustersize_list,
        "clustersize": clustersize_list,
        "efficiency": eff_list,
        "err_eff_low": err_eff_low,
        "err_eff_up": err_eff_up,
        "threshold": charge
    }

    with open("data/"+chip+".json", "w") as fp:
        json.dump(info_dict,fp) 