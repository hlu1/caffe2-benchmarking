#!/usr/bin/env python3

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import os
import shutil
from frameworks.framework_base import FrameworkBase
from utils.custom_logger import getLogger


class OculusFramework(FrameworkBase):
    def __init__(self, tempdir):
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777, True)

    def getName(self):
        return "oculus"

    def runBenchmark(self, info, benchmark, platform):
        tests = benchmark["tests"]
        assert len(tests) == 1, "At this point, only one test should " + \
            "exist in one benchmark. However, benchmark " + \
            "{} doesn't.".format(benchmark["name"])

        model = benchmark["model"]
        test = tests[0]
        assert set({"input_files", "output_files"}).issubset(test.keys())

        input_files = [f["location"] for f in test["input_files"]]
        inputs = \
            platform.copyFilesToPlatform(input_files)
        outputs = [platform.getOutputDir() + "/" + t["filename"]
                   for t in test["output_files"]]
        # Always copy binary to /system/bin/ directory
        program = platform.copyFilesToPlatform(info["program"], "/system/bin/")
        commands = self._composeRunCommand(program, platform, model, test,
                                           inputs, outputs)
        platform.runBenchmark(commands, True)

        target_dir = self.tempdir + "/output/"
        shutil.rmtree(target_dir, True)
        os.makedirs(target_dir)

        platform.delFilesFromPlatform(inputs)
        # output files are removed after being copied back
        output_files = platform.moveFilesFromPlatform(outputs,
                                                      target_dir)

        json_file = platform.moveFilesFromPlatform(
            platform.getOutputDir() + "report.json",
            self.tempdir)
        with open(json_file, 'r') as f:
            json_content = json.load(f)

        result = {}
        for one_test in json_content:
            for one_entry in one_test:
                type = one_entry["type"]
                value = one_entry["value"]
                unit = one_entry["unit"]
                metric = one_entry["metric"]
                if type in result:
                    entry = result[type]
                    if entry["unit"] is not None and entry["unit"] != unit:
                        getLogger().error("The unit do not match in different"
                                          " test runs {} and {}".
                                          format(entry["unit"], unit))
                        entry["unit"] = None
                    if entry["metric"] is not None and \
                            entry["metric"] != metric:
                        getLogger().error("The metric do not match in "
                                          " different test runs {} and {}".
                                          format(entry["metric"], metric))
                        entry["metric"] = None
                    entry["values"].append(value)
                else:
                    result[type] = {
                        "type": type,
                        "values": [value],
                        "unit": unit,
                        "metric": metric,
                    }
        # cleanup
        # platform.delFilesFromPlatform(program)
        # for input in test["input"]:
        #     platform.delFilesFromPlatform(input)
        return result, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        assert "model" in benchmark, \
            "Model must exist in the benchmark {}".format(filename)
        assert "name" in benchmark["model"], \
            "field name must exist in model in benchmark {}".format(filename)
        assert "format" in benchmark["model"], \
            "field format must exist in model in benchmark {}".format(filename)
        assert "tests" in benchmark, \
            "Tests field is missing in benchmark {}".format(filename)

        for test in benchmark["tests"]:
            assert "input_files" in test, \
                "inputs must exist in test in benchmark {}".format(filename)
            assert "output_files" in test, \
                "outputs must exist in test in benchmark {}".format(filename)
            assert "metric" in test, \
                "metric must exist in test in benchmark {}".format(filename)
            assert "batch" in test, \
                "batch must exist in test in benchmark {}".format(filename)

    def _composeRunCommand(self, program, platform, model, test,
                           inputs, outputs):
        cmd = [program,
               "--json", platform.getOutputDir() + "report.json",
               "--model", model["name"],
               "--input", ' ' .join(inputs),
               "--output", ' '.join(outputs)]
        if "batch" in test:
            cmd.append("--batch")
            cmd.append(str(test["batch"]))
        if "debug" in test:
            cmd.append("--debug")
            cmd.append(str(test["debug"]))
        if "benchmark" in test:
            cmd.append("--benchmark")
            cmd.append(str(test["benchmark"]))
        return ' '.join(cmd)
