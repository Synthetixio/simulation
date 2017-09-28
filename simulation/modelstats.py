"""modelstats.py: Functions for extracting aggregate information from the Havven model."""

def wealth_sd(model:"HavvenModel") -> float:
    """Return the standard deviation of wealth in the economy."""
    num_agents = len(model.schedule.agents)
    wealths = [a.wealth() for a in model.schedule.agents]
    mean_wealth = sum(wealths)/num_agents
    sum_squared_diffs = sum([(w - mean_wealth)**2 for w in wealths])
    return (sum_squared_diffs/(num_agents - 1))**0.5

def gini(model:"HavvenModel") -> float:
    """Return the gini coefficient in the economy."""
    n, s_wealth = len(model.schedule.agents), sorted([a.wealth() for a in model.schedule.agents])
    return 1 + (1/n) - 2*(sum(x*(n-i) for i, x in enumerate(s_wealth)) / (n*sum(s_wealth)))

def max_wealth(model:"HavvenModel") -> float:
    """Return the wealth of the richest person in the economy."""
    w = [a.wealth() for a in model.schedule.agents]
    return max(w)

def min_wealth(model:"HavvenModel") -> float:
    """Return the wealth of the poorest person in the economy."""
    w = [a.wealth() for a in model.schedule.agents]
    return min(w)

def fiat_demand(model:"HavvenModel") -> float:
    cur = sum([ask.quantity * ask.price for ask in model.fiat_cur_market.sell_orders])
    nom = sum([ask.quantity * ask.price for ask in model.fiat_nom_market.sell_orders])
    return cur + nom

def fiat_supply(model:"HavvenModel") -> float:
    cur = sum([bid.quantity * bid.price for bid in model.fiat_cur_market.buy_orders])
    nom = sum([bid.quantity * bid.price for bid in model.fiat_nom_market.buy_orders])
    return cur + nom

def curit_demand(model:"HavvenModel") -> float:
    nom = sum([bid.quantity for bid in model.nom_cur_market.buy_orders])
    fiat = sum([bid.quantity for bid in model.fiat_cur_market.buy_orders])
    return nom + fiat

def curit_supply(model:"HavvenModel") -> float:
    nom = sum([ask.quantity for ask in model.fiat_cur_market.sell_orders])
    fiat = sum([ask.quantity for ask in model.nom_cur_market.sell_orders])
    return nom + fiat

def nomin_demand(model:"HavvenModel") -> float:
    cur = sum([ask.quantity * ask.price for ask in model.nom_cur_market.sell_orders])
    fiat = sum([bid.quantity for bid in model.fiat_nom_market.buy_orders])
    return cur + fiat

def nomin_supply(model:"HavvenModel") -> float:
    cur = sum([bid.quantity * bid.price for ask in model.nom_cur_market.buy_orders])
    fiat = sum([ask.quantity for ask in model.fiat_nom_market.sell_orders])
    return cur + fiat
