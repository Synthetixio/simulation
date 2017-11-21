"""stats.py: Functions for extracting aggregate information from the Havven model."""

from statistics import mean, stdev

from mesa.datacollection import DataCollector

import model


def mean_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """Return the average fraction of profit being made by market participants."""
    return mean(float(a.profit_fraction()) for a in havven_model.schedule.agents)


def mean_banker_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """Return the average fraction of profit being made by Bankers in the market."""
    if len(havven_model.agent_manager.agents['Banker']) == 0:
        return 0
    return mean(float(a.profit_fraction()) for a in havven_model.agent_manager.agents['Banker'])


def mean_arb_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """Return the average fraction of profit being made by Arbitrageurs in the market."""
    if len(havven_model.agent_manager.agents['Arbitrageur']) == 0:
        return 0
    return mean(float(a.profit_fraction()) for a in havven_model.agent_manager.agents['Arbitrageur'])


def mean_rand_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """Return the average fraction of profit being made by Randomizers in the market."""
    if len(havven_model.agent_manager.agents['Randomizer']) == 0:
        return 0
    return mean(float(a.profit_fraction()) for a in havven_model.agent_manager.agents['Randomizer'])


def mean_nomshort_profit_fraction(havven_model: "model.HavvenModel") -> float:
    """Return the average fraction of profit being made by NominShorters in the market."""
    if len(havven_model.agent_manager.agents['NominShorter']) == 0:
        return 0
    return mean(float(a.profit_fraction()) for a in havven_model.agent_manager.agents['NominShorter'])


def mean_escrownomshort_profit_fraction(havven_model: "model.HavvenModel") -> float:
    if len(havven_model.agent_manager.agents['HavvenEscrowNominShorter']) == 0:
        return 0
    return mean(float(a.profit_fraction()) for a in havven_model.agent_manager.agents['HavvenEscrowNominShorter'])


def wealth_sd(havven_model: "model.HavvenModel") -> float:
    """Return the standard deviation of wealth in the market."""
    return stdev(float(a.wealth()) for a in havven_model.schedule.agents)


def gini(havven_model: "model.HavvenModel") -> float:
    """Return the gini coefficient in the market."""
    n, s_wealth = len(havven_model.schedule.agents), sorted([float(a.wealth()) for a in havven_model.schedule.agents])
    return float(1 + (1 / n) - 2 * (sum(x * (n - i) for i, x in enumerate(s_wealth)) / (n * sum(s_wealth))))


def max_wealth(havven_model: "model.HavvenModel") -> float:
    """Return the wealth of the richest person in the market."""
    w = [float(a.wealth()) for a in havven_model.schedule.agents]
    return max(w)


def min_wealth(havven_model: "model.HavvenModel") -> float:
    """Return the wealth of the poorest person in the market."""
    w = [float(a.wealth()) for a in havven_model.schedule.agents]
    return min(w)


def fiat_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of fiat presently being bought in the marketplace."""
    havvens = sum([float(ask.quantity * ask.price) for ask in havven_model.market_manager.havven_fiat_market.asks])
    nomins = sum([float(ask.quantity * ask.price) for ask in havven_model.market_manager.nomin_fiat_market.asks])
    return havvens + nomins


def fiat_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of fiat presently being sold in the marketplace."""
    havvens = sum([float(bid.quantity * bid.price) for bid in havven_model.market_manager.havven_fiat_market.bids])
    nomins = sum([float(bid.quantity * bid.price) for bid in havven_model.market_manager.nomin_fiat_market.bids])
    return havvens + nomins


def havven_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of havvens presently being bought in the marketplace."""
    nomins = sum([float(bid.quantity) for bid in havven_model.market_manager.havven_nomin_market.bids])
    fiat = sum([float(bid.quantity) for bid in havven_model.market_manager.havven_fiat_market.bids])
    return nomins + fiat


def havven_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of havvens presently being sold in the marketplace."""
    nomins = sum([float(ask.quantity) for ask in havven_model.market_manager.havven_fiat_market.asks])
    fiat = sum([float(ask.quantity) for ask in havven_model.market_manager.havven_nomin_market.asks])
    return nomins + fiat


def nomin_demand(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of nomins presently being bought in the marketplace."""
    havvens = sum([float(ask.quantity * ask.price) for ask in havven_model.market_manager.havven_nomin_market.asks])
    fiat = sum([float(bid.quantity) for bid in havven_model.market_manager.nomin_fiat_market.bids])
    return havvens + fiat


def nomin_supply(havven_model: "model.HavvenModel") -> float:
    """Return the total quantity of nomins presently being sold in the marketplace."""
    havvens = sum([float(bid.quantity * bid.price) for bid in havven_model.market_manager.havven_nomin_market.bids])
    fiat = sum([float(ask.quantity) for ask in havven_model.market_manager.nomin_fiat_market.asks])
    return havvens + fiat


def create_datacollector() -> DataCollector:
    return DataCollector(
                model_reporters={
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
                    "Bank Profit %": lambda h: round(100 * mean_banker_profit_fraction(h), 3),
                    "Arb Profit %": lambda h: round(100 * mean_arb_profit_fraction(h), 3),
                    "Rand Profit %": lambda h: round(100 * mean_rand_profit_fraction(h), 3),
                    "NomShort Profit %": lambda h: round(100 * mean_nomshort_profit_fraction(h), 3),
                    "EscrowNomShort Profit %": lambda h: round(100 * mean_escrownomshort_profit_fraction(h), 3),
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
                }, agent_reporters={
                    "Agents": lambda a: a,
                })
