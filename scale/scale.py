#!/usr/bin/python3

"""Primary scale logic"""
from workload import schedule_goal, get_critical_node_names, get_pods_number_on_node
from utils import get_nodes, get_cluster_name
from update_nodes import updateUnschedulable
from gcloud_update import increase_new_gcloud_node, shutdown_specified_node
from settings import settings

import logging
import argparse

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s')

scale_logger = logging.getLogger("scale")

SERVICE_PROVIDER = "gcloud"


def shutdown_empty_nodes(nodes, options):
    """
    Search through all nodes and shut down those that are unschedulable
    and devoid of non-critical pods

    CRITICAL NODES SHOULD NEVER BE INCLUDED IN THE INPUT LIST
    """
    for node in nodes:
        if get_pods_number_on_node(node, options) == 0 and node.spec.unschedulable:
            scale_logger.info(
                "Shutting down empty node: %s" % node.metadata.name)
            shutdown_specified_node(node.metadata.name)


def resize_for_new_nodes(newTotalNodes):
    """create new nodes to match newTotalNodes required
    only for scaling up, no action taken if newTotalNodes
    is smaller than number of current nodes"""
    if newTotalNodes <= len(get_nodes()):
        return
    scale_logger.info("Using service provider: %s" % SERVICE_PROVIDER)
    if SERVICE_PROVIDER == "gcloud":
        increase_new_gcloud_node(
            newTotalNodes, get_cluster_name())


def scale(options):
    """Update the nodes property based on scaling policy
    and create new nodes if necessary"""
    allNodes = get_nodes()
    scale_logger.info("Scaling on cluster %s" % get_cluster_name(allNodes[0]))
    nodes = []  # a list of nodes that are NOT critical
    criticalNodeNames = get_critical_node_names(options)
    for node in allNodes:
        if node.metadata.name not in criticalNodeNames:
            nodes.append(node)
    goal = schedule_goal(options)
    scale_logger.info("Total nodes in the cluster: %i" % len(allNodes))
    scale_logger.info("Found %i critical nodes; recommending additional %i nodes for service" % (
        (len(allNodes) - len(nodes),
         goal)
    ))

    updateUnschedulable(len(nodes) - goal, nodes, options)

    if len(criticalNodeNames) + goal > len(allNodes):
        scale_logger.info("Resize the cluster to %i nodes to satisfy the demand" % (
            len(criticalNodeNames) + goal))
        resize_for_new_nodes(len(criticalNodeNames) + goal)

    # CRITICAL NODES SHOULD NOT BE SHUTDOWN
    shutdown_empty_nodes(nodes, options)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="Show verbose output (debug)", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        scale_logger.setLevel(logging.DEBUG)
    else:
        scale_logger.setLevel(logging.INFO)

    options = settings()
    scale(options)
