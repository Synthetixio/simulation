"""modelstats.py: Functions for extracting aggregate information from the Havven model."""

from statistics import mean, stdev


def mean_profit_fraction(havven) -> float:
    return mean(a.profit_fraction() for a in havven.schedule.agents)

def wealth_sd(havven) -> float:
    """Return the standard deviation of wealth in the economy."""
    return stdev(a.wealth() for a in havven.schedule.agents)

def gini(havven) -> float:
    """Return the gini coefficient in the economy."""
    n, s_wealth = len(havven.schedule.agents), sorted([a.wealth() for a in havven.schedule.agents])
    return 1 + (1/n) - 2*(sum(x*(n-i) for i, x in enumerate(s_wealth)) / (n*sum(s_wealth)))

def max_wealth(havven) -> float:
    """Return the wealth of the richest person in the economy."""
    w = [a.wealth() for a in havven.schedule.agents]
    return max(w)

def min_wealth(havven) -> float:
    """Return the wealth of the poorest person in the economy."""
    w = [a.wealth() for a in havven.schedule.agents]
    return min(w)

def fiat_demand(havven) -> float:
    cur = sum([ask.quantity * ask.price for ask in havven.fiat_cur_market.sell_orders])
    nom = sum([ask.quantity * ask.price for ask in havven.fiat_nom_market.sell_orders])
    return cur + nom

def fiat_supply(havven) -> float:
    cur = sum([bid.quantity * bid.price for bid in havven.fiat_cur_market.buy_orders])
    nom = sum([bid.quantity * bid.price for bid in havven.fiat_nom_market.buy_orders])
    return cur + nom

def curit_demand(havven) -> float:
    nom = sum([bid.quantity for bid in havven.nom_cur_market.buy_orders])
    fiat = sum([bid.quantity for bid in havven.fiat_cur_market.buy_orders])
    return nom + fiat

def curit_supply(havven) -> float:
    nom = sum([ask.quantity for ask in havven.fiat_cur_market.sell_orders])
    fiat = sum([ask.quantity for ask in havven.nom_cur_market.sell_orders])
    return nom + fiat

def nomin_demand(havven) -> float:
    cur = sum([ask.quantity * ask.price for ask in havven.nom_cur_market.sell_orders])
    fiat = sum([bid.quantity for bid in havven.fiat_nom_market.buy_orders])
    return cur + fiat

def nomin_supply(havven) -> float:
    cur = sum([bid.quantity * bid.price for bid in havven.nom_cur_market.buy_orders])
    fiat = sum([ask.quantity for ask in havven.fiat_nom_market.sell_orders])
    return cur + fiat
