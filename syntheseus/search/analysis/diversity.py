from __future__ import annotations

import logging
import random
from collections.abc import Collection
from typing import Callable, Optional

from syntheseus.search.chem import BackwardReaction, Molecule
from syntheseus.search.graph.route import SynthesisGraph

ROUTE_DISTANCE_METRIC = Callable[[SynthesisGraph, SynthesisGraph], float]

logger = logging.getLogger(__name__)


def estimate_packing_number(
    routes: Collection[SynthesisGraph],
    radius: float,
    distance_metric: ROUTE_DISTANCE_METRIC,
    max_packing_number: Optional[int] = None,
    num_tries: int = 100,
    random_state: Optional[random.Random] = None,
) -> list[SynthesisGraph]:
    """
    Estimate packing number of a set of routes,
    defined as the size of the largest subset
    where d(x, y) > radius for all distinct x, y in the subset.
    This function estimates the packing number by trying to construct
    a subset of routes that satisfy the definition above.
    Because this is an NP-hard problem, we use a greedy heuristic algorithm.
    This algorithm is run several times and the best result is returned.

    Because this algorithm is constructive, we return the set of routes
    rather than simply the packing number. The size of the returned set
    is a lower bound to the true packing number.

    Args:
        routes: set of routes to estimate the packing number of.
        radius: distance threshold for the definition of packing number.
        distance_metric: distance between two routes.
        max_packing_number: to avoid expensive computations,
            the algorithm is stopped if a packing number
            larger than this value is found.
            If None, the algorithm will run until completion.
        num_tries: the number of random restarts to perform.
        random_state: random state to use for shuffling routes.

    Returns:
        A set of routes with the largest packing number found.
    """

    # Cleanly handle edge case of no routes
    if len(routes) == 0:
        return list()

    # Check argument type (leads to cryptic error message if not checked)
    assert all(
        isinstance(route, SynthesisGraph) for route in routes
    ), "Routes must be of type SynthesisGraph."

    # Initialize random state
    random_state = random_state or random.Random()

    # Try to get best packing set
    best_packing_set: list[SynthesisGraph] = list()
    route_list = list(routes)
    for try_idx in range(num_tries):
        if max_packing_number is not None and len(best_packing_set) >= max_packing_number:
            logger.debug("Stopping early because max packing number has been reached.")
            break  # no point trying further since the max packing number has been reached

        # Shuffle routes (gives a random restart to greedy algorithm)
        random_state.shuffle(route_list)

        # Construct a packing set and check whether it is better than the previous one
        packing_set = _recursive_construct_packing_set(
            route_list,
            radius,
            distance_metric,
            max_packing_number,
        )
        logger.debug(
            f"Run #{try_idx+1}/{num_tries}:"
            f" Found packing set of size {len(packing_set)}."
            f" (previous best size={len(best_packing_set)})."
        )
        if len(packing_set) > len(best_packing_set):
            logger.debug("This is the new best.")
            best_packing_set = packing_set

    return best_packing_set


def _recursive_construct_packing_set(
    routes: list[SynthesisGraph],
    radius: float,
    distance_metric: ROUTE_DISTANCE_METRIC,
    max_packing_number: Optional[int] = None,
) -> list[SynthesisGraph]:
    """
    Recursive helper function for estimate_packing_number which finds a packing set.

    If <= 1 route is provided, the packing set is just the set of routes.
    If >= 2 routes are provided, then the list is divided into two subsets
    and the second subset is merged into the first,
    which requires at most (N/2)^2 distance computations.
    """

    assert (
        max_packing_number is None or max_packing_number > 0
    ), "Max packing number must be positive."

    # Base cases:
    if len(routes) <= 1:
        return list(routes)

    # Recursive case:
    # first calculate packing set for both halves
    cutoff_idx = len(routes) // 2
    route_set1 = _recursive_construct_packing_set(
        routes[:cutoff_idx],
        radius,
        distance_metric,
        max_packing_number,
    )
    route_set2 = _recursive_construct_packing_set(
        routes[cutoff_idx:],
        radius,
        distance_metric,
        max_packing_number,
    )
    assert (
        max_packing_number is None or len(route_set1) <= max_packing_number
    ), "Max packing number exceeded in recursive call."

    # If route set 1 is smaller than route set 2, switch them.
    # This is done because we will merge route set 2 into route set 1 below,
    # and this guarantees that the packing set is at least as large as the
    # largest packing set for the two halves here
    if len(route_set1) < len(route_set2):
        route_set1, route_set2 = route_set2, route_set1

    # Which routes from set 2 can be merged into set 1?
    routes_to_merge: list[SynthesisGraph] = list()
    for route2 in route_set2:
        # Optionally break early if there are too many routes
        if (
            max_packing_number is not None
            and len(route_set1) + len(routes_to_merge) >= max_packing_number
        ):
            break

        for route1 in route_set1:
            if distance_metric(route1, route2) <= radius:
                # If route2 is too close to ANY route in route_set1,
                # then it cannot be merged
                break
        else:
            routes_to_merge.append(route2)

    return route_set1 + routes_to_merge


def _jaccard_distance(
    set1: set,
    set2: set,
) -> float:
    intersection = set1 & set2
    union = set1 | set2
    if len(union) == 0:
        return 0.0  # both sets are empty so distance is 0
    else:
        return 1.0 - len(intersection) / len(union)


def _get_reactions(route: SynthesisGraph) -> set[BackwardReaction]:
    return set(route._graph.nodes)


def _get_molecules(route: SynthesisGraph) -> set[Molecule]:
    all_mols: set[Molecule] = set()
    for rxn in route._graph.nodes:
        all_mols.add(rxn.product)
        all_mols.update(rxn.reactants)
    return all_mols


def reaction_jaccard_distance(
    route1: SynthesisGraph,
    route2: SynthesisGraph,
) -> float:
    """
    Calculate the Jaccard distance between the sets of reactions in 2 routes.
    """

    # Get sets of reactions
    reactions1 = _get_reactions(route1)
    reactions2 = _get_reactions(route2)
    return _jaccard_distance(reactions1, reactions2)


def molecule_jaccard_distance(
    route1: SynthesisGraph,
    route2: SynthesisGraph,
) -> float:
    """
    Calculate the Jaccard distance between the sets of molecules in 2 routes.
    """

    # Get sets of molecules
    molecules1 = _get_molecules(route1)
    molecules2 = _get_molecules(route2)
    return _jaccard_distance(molecules1, molecules2)


def reaction_symmetric_difference_distance(
    route1: SynthesisGraph,
    route2: SynthesisGraph,
) -> float:
    """
    Calculate the symmetric difference distance between the sets of reactions in 2 routes.
    """

    # Get sets of reactions
    reactions1 = _get_reactions(route1)
    reactions2 = _get_reactions(route2)
    return len(reactions1 ^ reactions2)


def molecule_symmetric_difference_distance(
    route1: SynthesisGraph,
    route2: SynthesisGraph,
) -> float:
    """
    Calculate the symmetric difference distance between the sets of reactions in 2 routes.
    """

    # Get sets of reactions
    molecules1 = _get_molecules(route1)
    molecules2 = _get_molecules(route2)
    return len(molecules1 ^ molecules2)
