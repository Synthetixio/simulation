from agents import MarketPlayer


class HavvenFoundation(MarketPlayer):
    """
    Currently this is just used a dummy agent to set up some variables to allow for
      issuance to work

    In the future this can be extended to be a buyer of last resort, as well as to
      work as a "banker" issuing and burning as needed for stabilisation.
    """
    def setup(self, *args):
        pass
