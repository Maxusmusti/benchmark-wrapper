#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the uperf benchmark. See http://uperf.org/ for more information."""
from typing import Dict, List, Tuple, Union
import re
from snafu.wrapper import Benchmark


class Uperf(Benchmark):
    """
    Wrapper for the uperf benchmark.
    """

    tool_name = "uperf"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arg_group.add_argument(
            "-w", "--workload", dest="workload", env_var="WORKLOAD", help="Provide XML workload location"
        )
        self.arg_group.add_argument(
            "-s",
            "--sample",
            dest="sample",
            env_var="SAMPLE",
            default=1,
            type=int,
            help="Number of times to run the benchmark",
        )
        self.arg_group.add_argument(
            "--resourcetype",
            dest="resourcetype",
            env_var="RESOURCETYPE",
            help="Provide the resource type for uperf run - pod/vm/baremetal",
        )
        # TODO: need help text for these and add some standardization
        self.arg_group.add_argument("--ips", dest="ips", env_var="ips", default="")
        self.arg_group.add_argument("-h", "--remoteip", dest="remoteip", env_var="h", default="")
        self.arg_group.add_argument("--hostnet", dest="hostnetwork", env_var="hostnet", default="False")
        self.arg_group.add_argument("--serviceip", dest="serviceip", env_var="serviceip", default="False")
        self.arg_group.add_argument("--server-node", dest="server_node", env_var="server_node", default="")
        self.arg_group.add_argument("--client-node", dest="client_node", env_var="client_node", default="")
        self.arg_group.add_argument("--cluster-name", dest="cluster_name", env_var="clustername", default="")
        self.arg_group.add_argument("--num-pairs", dest="num_pairs", env_var="num_pairs", default="")
        self.arg_group.add_argument(
            "--multus-client", dest="multus_client", env_var="multus_client", default=""
        )
        self.arg_group.add_argument(
            "--network-policy", dest="networkpolicy", env_var="networkpolicy", default=""
        )
        self.arg_group.add_argument("--nodes-count", dest="nodes_in_iter", env_var="node_count", default="")
        self.arg_group.add_argument("--pod-density", dest="pod_density", env_var="pod_count", default="")
        self.arg_group.add_argument("--colocate", dest="colocate", env_var="colocate", default="")
        self.arg_group.add_argument("--step-size", dest="step_size", env_var="stepsize", default="")
        # density_range and node_range are defined and exported in the cr file
        # it will appear in ES as startvalue-endvalue, for example
        # 5-10, for a run that began with 5 nodes involved and ended with 10
        self.arg_group.add_argument(
            "--density-range", dest="density_range", env_var="density_range", default=""
        )
        self.arg_group.add_argument("--node-range", dest="node_range", env_var="node_range", default="")
        # each node will run with density number of pods, this is the 0 based
        # number of that pod, useful for displaying throughput of each density
        self.arg_group.add_argument("--pod-id", dest="pod-id", env_var="my_pod_idx", default="")
        # TODO: Are these two common metadata?
        self.arg_group.add_argument("-u", "--uuid", dest="uuid", env_var="UUID", help="Provide UUID of run")
        self.arg_group.add_argument("--user", dest="user", env_var="USER", help="Provide user")

        self.required_args.update({"workload", "uuid", "user"})

    def preflight_checks(self) -> bool:
        checks = [self.check_required_args(), self.check_file(self.config.workload)]

        return False not in checks

    def setup(self):
        """Setup uperf."""

    def cleanup(self):
        """Cleanup uperf."""

    def run(self) -> Tuple[bool, List[str]]:
        """
        Run uperf benchmark ``self.config.sample`` number of times.

        Returns immediately if a sample fails. Will attempt to Uperf run three times for each sample.

        Returns
        -------
        tuple :
            First value in tuple is bool representing if we were able to run uperf successfully. Second
            value in tuple is a list of stdouts returned by successful uperf samples.
        """

        cmd = f"uperf -v -a -R -i 1 -m {self.config.workload}"
        results: List[str] = list()
        for sample_num in range(1, self.config.sample + 1):
            self.logger.info(f"Starting Uperf sample number {sample_num}")
            sample = self.run_process(cmd, retries=2, expected_rc=0)
            if not sample["success"]:
                self.logger.critical(f"Uperf failed to run! Got results: {sample}")
                return False, results
            else:
                self.logger.info(f"Finished collecting sample {sample_num}")
                self.logger.debug(f"Got results: {sample}")
                results.append(sample["stdout"])

        self.logger.info(f"Successfully collected {self.config.sample} samples.")
        return True, results

    def emit_metrics(self):
        """Emit uperf metrics."""

    @staticmethod
    def parse_stdout(stdout: str) -> Tuple[List[Tuple[str, str, str]], Dict[str, Union[str, int]]]:
        """Return parsed stdout of Uperf sample."""

        # This will effectivly give us:
        # <profile name="{{test}}-{{proto}}-{{wsize}}-{{rsize}}-{{nthr}}">
        config = re.findall(r"running profile:(.*) \.\.\.", stdout)[0]
        test_type, protocol, wsize, rsize, nthr = config.split("-")
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)", stdout)
        # We assume message_size=write_message_size to prevent breaking dependant implementations
        return (
            results,
            {
                "test_type": test_type,
                "protocol": protocol,
                "message_size": int(wsize),
                "read_message_size": int(rsize),
                "num_threads": int(nthr),
                "duration": len(results),
            },
        )
