"""stats.py: Functions for extracting aggregate information from the Havven model."""

from statistics import stdev
from typing import List, Any

from mesa.datacollection import DataCollector

import agents


def mean(values: List[Any]):
    if len(values) > 0:
        return sum(values)/len(values)
    return 0


def _profit_excluded(name: str) -> bool:
    """
    True iff the agent's profit should be is excluded
    from the average profit computation.
    """
    return name in agents.players_to_exclude


def mean_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """
    Return the average fraction of profit being made by market participants,
    excluding Merchants and Buyers.
    """
    if len(havven_model.schedule.agents) == 0:
        return 0
    return float(mean([a.profit_fraction() for a in havven_model.schedule.agents
                 if not _profit_excluded(a)]))


def mean_agent_profit_fraction(name: str, havven_model: "model.HavvenModel"):
    if len(havven_model.agent_manager.agents[name]) == 0:
        return 0
    return float(mean([a.profit_fraction() for a in havven_model.agent_manager.agents[name]]))


def wealth_sd(havven_model: "model.HavvenModel") -> float:
    """Return the standard deviation of wealth in the market."""
    return float(stdev([a.wealth() for a in havven_model.schedule.agents]))


def gini(havven_model: "model.HavvenModel") -> float:
    """Return the gini coefficient in the market."""
    n = len(havven_model.schedule.agents)
    s_wealth = sorted([a.wealth() for a in havven_model.schedule.agents])
    total_wealth = float(sum(s_wealth))
    if total_wealth == 0 or n == 0:
        return 0
    scaled_wealth = float(sum([(i+1)*w for i, w in enumerate(s_wealth)]))
    return (2.0*scaled_wealth)/(n*total_wealth) - (n+1.0)/n


def max_wealth(havven_model: "model.HavvenModel") -> float:
    """Return the wealth of the richest person in the market."""
    if len(havven_model.schedule.agents) == 0:
        return 0

    return float(max([a.wealth() for a in havven_model.schedule.agents]))


def min_wealth(havven_model: "model.HavvenModel") -> float:
    """Return the wealth of the poorest person in the market."""
    if len(havven_model.schedule.agents) == 0:
        return 0

    return float(min([a.wealth() for a in havven_model.schedule.agents]))


def fiat_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of fiat presently being bought in the marketplace."""
    havvens = float(sum([ask.quantity * ask.price for ask in havven_model.market_manager.havven_fiat_market.asks]))
    nomins = float(sum([ask.quantity * ask.price for ask in havven_model.market_manager.nomin_fiat_market.asks]))
    return havvens + nomins


def fiat_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of fiat presently being sold in the marketplace."""
    havvens = float(sum([bid.quantity * bid.price for bid in havven_model.market_manager.havven_fiat_market.bids]))
    nomins = float(sum([bid.quantity * bid.price for bid in havven_model.market_manager.nomin_fiat_market.bids]))
    return havvens + nomins


def havven_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of havvens presently being bought in the marketplace."""
    nomins = float(sum([bid.quantity for bid in havven_model.market_manager.havven_nomin_market.bids]))
    fiat = float(sum([bid.quantity for bid in havven_model.market_manager.havven_fiat_market.bids]))
    return nomins + fiat


def havven_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of havvens presently being sold in the marketplace."""
    nomins = float(sum([ask.quantity for ask in havven_model.market_manager.havven_fiat_market.asks]))
    fiat = float(sum([ask.quantity for ask in havven_model.market_manager.havven_nomin_market.asks]))
    return nomins + fiat


def nomin_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of nomins presently being bought in the marketplace."""
    havvens = float(sum([ask.quantity * ask.price for ask in havven_model.market_manager.havven_nomin_market.asks]))
    fiat = float(sum([bid.quantity for bid in havven_model.market_manager.nomin_fiat_market.bids]))
    return havvens + fiat


def nomin_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of nomins presently being sold in the marketplace."""
    havvens = float(sum([bid.quantity * bid.price for bid in havven_model.market_manager.havven_nomin_market.bids]))
    fiat = float(sum([ask.quantity for ask in havven_model.market_manager.nomin_fiat_market.asks]))
    return havvens + fiat


def create_datacollector() -> DataCollector:
    base_reporters = {
        "0": lambda x: 0,  # Note: workaround for showing labels (more info server.py)
        "1": lambda x: 1,
        "Nomin Price": lambda h: float(h.market_manager.nomin_fiat_market.price),
        "Nomin Ask": lambda h: float(h.market_manager.nomin_fiat_market.lowest_ask_price()),
        "Nomin Bid": lambda h: float(h.market_manager.nomin_fiat_market.highest_bid_price()),
        "Havven Price": lambda h: float(h.market_manager.havven_fiat_market.price),
        "Havven Ask": lambda h: float(h.market_manager.havven_fiat_market.lowest_ask_price()),
        "Havven Bid": lambda h: float(h.market_manager.havven_fiat_market.highest_bid_price()),
        "Havven/Nomin Price": lambda h: float(h.market_manager.havven_nomin_market.price),
        "Havven/Nomin Ask": lambda h: float(h.market_manager.havven_nomin_market.lowest_ask_price()),
        "Havven/Nomin Bid": lambda h: float(h.market_manager.havven_nomin_market.highest_bid_price()),
        "Havven Nomins": lambda h: float(h.manager.nomins),
        "Havven Havvens": lambda h: float(h.manager.havvens),
        "Havven Fiat": lambda h: float(h.manager.fiat),
        "Gini": gini,
        "Nomins": lambda h: float(h.manager.nomin_supply),
        "Escrowed Havvens": lambda h: float(h.manager.escrowed_havvens),
        #"Wealth SD": stats.wealth_sd,
        "Max Wealth": max_wealth,
        "Min Wealth": min_wealth,
        "Avg Profit %": lambda h: round(100 * mean_profit_fraction(h), 3),
        "Havven Demand": havven_demand,
        "Havven Supply": havven_supply,
        "Nomin Demand": nomin_demand,
        "Nomin Supply": nomin_supply,
        "Fiat Demand": fiat_demand,
        "Fiat Supply": fiat_supply,
        "Fee Pool": lambda h: float(h.manager.nomins),
        "Fees Distributed": lambda h: float(h.fee_manager.fees_distributed),
        "NominFiatOrderBook": lambda h: h.market_manager.nomin_fiat_market,
        "HavvenFiatOrderBook": lambda h: h.market_manager.havven_fiat_market,
        "HavvenNominOrderBook": lambda h: h.market_manager.havven_nomin_market
    }

    agent_reporters = {}
    for name in agents.player_names:
        if name not in agents.players_to_exclude:
            agent_reporters[name] = lambda h, y=name: round(mean_agent_profit_fraction(y, h)*100, 3)

    base_reporters.update(agent_reporters)

    return DataCollector(
        model_reporters=base_reporters,
        agent_reporters={
            "Agents": lambda a: a,
        }
    )
