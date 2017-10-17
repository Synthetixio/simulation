"""stats.py: Functions for extracting aggregate information from the Havven model."""

from statistics import mean, stdev

import model
import agents


def mean_profit_fraction(havven: "model.Havven") -> float:
    """Return the average fraction of profit being made by market participants."""
    return mean(float(a.profit_fraction()) for a in havven.schedule.agents)


def mean_banker_profit_fraction(havven: "model.Havven") -> float:
    """Return the average fraction of profit being made by Bankers in the market."""
    return mean(float(a.profit_fraction()) for a in havven.schedule.agents
                if isinstance(a, agents.Banker))


def mean_arb_profit_fraction(havven: "model.Havven") -> float:
    """Return the average fraction of profit being made by Arbitrageurs in the market."""
    return mean(float(a.profit_fraction()) for a in havven.schedule.agents
                if isinstance(a, agents.Arbitrageur))


def mean_rand_profit_fraction(havven: "model.Havven") -> float:
    """Return the average fraction of profit being made by Randomizers in the market."""
    return mean(float(a.profit_fraction()) for a in havven.schedule.agents
                if isinstance(a, agents.Randomizer))


def wealth_sd(havven: "model.Havven") -> float:
    """Return the standard deviation of wealth in the market."""
    return stdev(float(a.wealth()) for a in havven.schedule.agents)


def gini(havven: "model.Havven") -> float:
    """Return the gini coefficient in the market."""
    n, s_wealth = len(havven.schedule.agents), sorted([float(a.wealth()) for a in havven.schedule.agents])
    return float(1 + (1 / n) - 2 * (sum(x * (n - i) for i, x in enumerate(s_wealth)) / (n * sum(s_wealth))))


def max_wealth(havven: "model.Havven") -> float:
    """Return the wealth of the richest person in the market."""
    w = [float(a.wealth()) for a in havven.schedule.agents]
    return max(w)


def min_wealth(havven: "model.Havven") -> float:
    """Return the wealth of the poorest person in the market."""
    w = [float(a.wealth()) for a in havven.schedule.agents]
    return min(w)


def fiat_demand(havven: "model.Havven") -> float:
    """Return the total quantity of fiat presently being bought in the marketplace."""
    curits = sum([float(ask.quantity * ask.price) for ask in havven.market_manager.curit_fiat_market.asks])
    nomins = sum([float(ask.quantity * ask.price) for ask in havven.market_manager.nomin_fiat_market.asks])
    return curits + nomins


def fiat_supply(havven: "model.Havven") -> float:
    """Return the total quantity of fiat presently being sold in the marketplace."""
    curits = sum([float(bid.quantity * bid.price) for bid in havven.market_manager.curit_fiat_market.bids])
    nomins = sum([float(bid.quantity * bid.price) for bid in havven.market_manager.nomin_fiat_market.bids])
    return curits + nomins


def curit_demand(havven: "model.Havven") -> float:
    """Return the total quantity of curits presently being bought in the marketplace."""
    nomins = sum([float(bid.quantity) for bid in havven.market_manager.curit_nomin_market.bids])
    fiat = sum([float(bid.quantity) for bid in havven.market_manager.curit_fiat_market.bids])
    return nomins + fiat


def curit_supply(havven: "model.Havven") -> float:
    """Return the total quantity of curits presently being sold in the marketplace."""
    nomins = sum([float(ask.quantity) for ask in havven.market_manager.curit_fiat_market.asks])
    fiat = sum([float(ask.quantity) for ask in havven.market_manager.curit_nomin_market.asks])
    return nomins + fiat


def nomin_demand(havven: "model.Havven") -> float:
    """Return the total quantity of nomins presently being bought in the marketplace."""
    curits = sum([float(ask.quantity * ask.price) for ask in havven.market_manager.curit_nomin_market.asks])
    fiat = sum([float(bid.quantity) for bid in havven.market_manager.nomin_fiat_market.bids])
    return curits + fiat


def nomin_supply(havven: "model.Havven") -> float:
    """Return the total quantity of nomins presently being sold in the marketplace."""
    curits = sum([float(bid.quantity * bid.price) for bid in havven.market_manager.curit_nomin_market.bids])
    fiat = sum([float(ask.quantity) for ask in havven.market_manager.nomin_fiat_market.asks])
    return curits + fiat
