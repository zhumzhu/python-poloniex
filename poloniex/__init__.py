# Poloniex API wrapper tested on Python 2.7.6 & 3.4.3
# https://github.com/s4w3d0ff/python-poloniex
# BTC: 15D8VaZco22GTLVrFMAehXyif6EGf8GMYV
# TODO:
#   [x] PEP8
#   [ ] Add better logger access
#   [ ] Find out if request module has the equivalent to urlencode
#   [ ] Add Push Api application wrapper
#   [ ] Convert docstrings to sphinx
#
#    Copyright (C) 2016  https://github.com/s4w3d0ff
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# python 2
try:
    from urllib import urlencode as _urlencode
    str = unicode
# python 3
except:
    from urllib.parse import urlencode as _urlencode

from json import loads as _loads
from hmac import new as _new
from hashlib import sha512 as _sha512
from time import time
import logging
# 3rd party
from requests.exceptions import RequestException
from requests import post as _post
from requests import get as _get
# local
from .coach import Coach
from .retry import retry
# logger
logger = logging.getLogger(__name__)

retryDelays = (0, 2, 5, 30)

# Possible Commands
PUBLIC_COMMANDS = [
    'returnTicker',
    'return24hVolume',
    'returnOrderBook',
    'returnTradeHistory',
    'returnChartData',
    'returnCurrencies',
    'returnLoanOrders']

PRIVATE_COMMANDS = [
    'returnBalances',
    'returnCompleteBalances',
    'returnDepositAddresses',
    'generateNewAddress',
    'returnDepositsWithdrawals',
    'returnOpenOrders',
    'returnTradeHistory',
    'returnAvailableAccountBalances',
    'returnTradableBalances',
    'returnOpenLoanOffers',
    'returnOrderTrades',
    'returnActiveLoans',
    'returnLendingHistory',
    'createLoanOffer',
    'cancelLoanOffer',
    'toggleAutoRenew',
    'buy',
    'sell',
    'cancelOrder',
    'moveOrder',
    'withdraw',
    'returnFeeInfo',
    'transferBalance',
    'returnMarginAccountSummary',
    'marginBuy',
    'marginSell',
    'getMarginPosition',
    'closeMarginPosition']


class PoloniexError(Exception):
    pass


class Poloniex(object):
    """The Poloniex Object!"""

    def __init__(
            self, Key=False, Secret=False,
            timeout=1, coach=True, jsonNums=False):
        """
        Key = str api key supplied by Poloniex
        Secret = str secret hash supplied by Poloniex
        timeout = int time in sec to wait for an api response
            (otherwise 'requests.exceptions.Timeout' is raised)
        coach = bool to indicate if the api coach should be used
        jsonNums = datatype to use when parsing json ints and floats

        # Time Placeholders # (MONTH == 30*DAYS)

        self.MINUTE, self.HOUR, self.DAY, self.WEEK, self.MONTH, self.YEAR
        """
        # Call coach, set nonce
        if coach is True:
            coach = Coach()
        self.logger = logger
        self.coach = coach
        self._nonce = int("{:.6f}".format(time()).replace('.', ''))
        # json number datatypes
        self.jsonNums = jsonNums
        # Grab keys, set timeout, ditch coach?
        self.Key, self.Secret, self.timeout = Key, Secret, timeout
        # Set time labels
        self.MINUTE, self.HOUR, self.DAY, self.WEEK, self.MONTH, self.YEAR = \
            60, 60 * 60, 60 * 60 * 24, 60 * 60 * 24 * \
            7, 60 * 60 * 24 * 30, 60 * 60 * 24 * 365

    @property
    def nonce(self):
        self._nonce += 42
        return self._nonce

    # -----------------Meat and Potatos---------------------------------------
    @retry(delays=retryDelays, exception=RequestException)
    def __call__(self, command, args={}):
        """
        Main Api Function
        - encodes and sends <command> with optional [args] to Poloniex api
        - raises 'poloniex.PoloniexError' if an api key or secret is missing
            (and the command is 'private'), if the <command> is not valid, or
            if an error is returned from poloniex.com
        - returns decoded json api message
        """
        global PUBLIC_COMMANDS, PRIVATE_COMMANDS

        # check in with the coach
        if self.coach:
            self.coach.wait()

        # pass the command
        args['command'] = command

        # private?
        if command in PRIVATE_COMMANDS:
            # check for keys
            if not self.Key or not self.Secret:
                raise PoloniexError("A Key and Secret needed!")
            # set nonce
            args['nonce'] = self.nonce
            # encode arguments for url
            postData = _urlencode(args)
            # sign postData with our Secret
            sign = _new(
                self.Secret.encode('utf-8'),
                postData.encode('utf-8'),
                _sha512)
            # post request
            ret = _post(
                'https://poloniex.com/tradingApi',
                data=args,
                headers={'Sign': sign.hexdigest(), 'Key': self.Key},
                timeout=self.timeout)
            # decode json
            if not self.jsonNums:
                jsonout = _loads(ret.text, parse_float=str)
            else:
                jsonout = _loads(ret.text,
                                 parse_float=self.jsonNums,
                                 parse_int=self.jsonNums)
            # check if poloniex returned an error
            if 'error' in jsonout:
                raise PoloniexError(jsonout['error'])
            return jsonout

        # public?
        elif command in PUBLIC_COMMANDS:
            ret = _get(
                'https://poloniex.com/public?' + _urlencode(args),
                timeout=self.timeout)
            # decode json
            if not self.jsonNums:
                jsonout = _loads(ret.text, parse_float=str)
            else:
                jsonout = _loads(ret.text,
                                 parse_float=self.jsonNums,
                                 parse_int=self.jsonNums)
            # check if poloniex returned an error
            if 'error' in jsonout:
                raise PoloniexError(jsonout['error'])
            return jsonout
        else:
            raise PoloniexError("Invalid Command!: %s" % command)

    # --PUBLIC COMMANDS-------------------------------------------------------
    def returnTicker(self):
        """ Returns the ticker for all markets """
        return self.__call__('returnTicker')

    def return24hVolume(self):
        """ Returns the volume data for all markets """
        return self.__call__('return24hVolume')

    def returnCurrencies(self):
        """ Returns additional market info for all markets """
        return self.__call__('returnCurrencies')

    def returnLoanOrders(self, coin):
        """ Returns loan order book for <coin> """
        return self.__call__('returnLoanOrders', {
                             'currency': str(coin).upper()})

    def returnOrderBook(self, pair='all', depth=20):
        """
        Returns orderbook for [pair='all']
        at a depth of [depth=20] orders
        """
        return self.__call__('returnOrderBook', {
            'currencyPair': str(pair).upper(),
            'depth': str(depth)
        })

    def returnChartData(self, pair, period=False, start=False, end=False):
        """
        Returns chart data for <pair> with a candle period of
        [period=self.DAY] starting from [start=time()-self.YEAR]
        and ending at [end=time()]
        """
        if period not in [300, 900, 1800, 7200, 14400, 86400]:
            period = self.DAY
        if not start:
            start = time() - self.MONTH
        if not end:
            end = time()
        return self.__call__('returnChartData', {
            'currencyPair': str(pair).upper(),
            'period': str(period),
            'start': str(start),
            'end': str(end)
        })

    @retry(delays=retryDelays, exception=RequestException)
    def marketTradeHist(self, pair, start=False, end=False):
        """
        Returns public trade history for <pair>
        starting at <start> and ending at [end=time()]
        """
        if self.coach:
            self.coach.wait()
        args = {'command': 'returnTradeHistory',
                'currencyPair': str(pair).upper()}
        if start:
            args['start'] = start
        if end:
            args['end'] = end
        ret = _get(
            'https://poloniex.com/public?' + _urlencode(args),
            timeout=self.timeout)
        # decode json
        if not self.jsonNums:
            jsonout = _loads(ret.text, parse_float=str)
        else:
            jsonout = _loads(ret.text,
                             parse_float=self.jsonNums,
                             parse_int=self.jsonNums)
        # check if poloniex returned an error
        if 'error' in jsonout:
            raise PoloniexError(jsonout['error'])
        return jsonout

    # --PRIVATE COMMANDS------------------------------------------------------
    def generateNewAddress(self, coin):
        """ Creates a new deposit address for <coin> """
        return self.__call__('generateNewAddress', {
                             'currency': coin})

    def returnTradeHistory(self, pair='all', start=False, end=False):
        """ Returns private trade history for <pair> """
        args = {'currencyPair': str(pair).upper()}
        if start:
            args['start'] = start
        if end:
            args['end'] = end
        return self.__call__('returnTradeHistory', args)

    def returnBalances(self):
        """ Returns coin balances """
        return self.__call__('returnBalances')

    def returnAvailableAccountBalances(self, account=False):
        """ Returns available account balances """
        if account:
            return self.__call__('returnAvailableAccountBalances',
                                 {'account': account})
        return self.__call__('returnAvailableAccountBalances')

    def returnMarginAccountSummary(self):
        """ Returns margin account summary """
        return self.__call__('returnMarginAccountSummary')

    def getMarginPosition(self, pair='all'):
        """ Returns margin position for [pair='all'] """
        return self.__call__('getMarginPosition', {
                             'currencyPair': str(pair).upper()})

    def returnCompleteBalances(self, account='all'):
        """ Returns complete balances """
        return self.__call__('returnCompleteBalances',
                             {'account': str(account)})

    def returnDepositAddresses(self):
        """ Returns deposit addresses """
        return self.__call__('returnDepositAddresses')

    def returnOpenOrders(self, pair='all'):
        """ Returns your open orders for [pair='all'] """
        return self.__call__('returnOpenOrders', {
                             'currencyPair': str(pair).upper()})

    def returnDepositsWithdrawals(self, start=False, end=False):
        """ Returns deposit/withdraw history """
        if not start:
            start = time() - self.MONTH
        if not end:
            end = time()
        args = {'start': str(start), 'end': str(end)}
        return self.__call__('returnDepositsWithdrawals', args)

    def returnTradableBalances(self):
        """ Returns tradable balances """
        return self.__call__('returnTradableBalances')

    def returnActiveLoans(self):
        """ Returns active loans """
        return self.__call__('returnActiveLoans')

    def returnOpenLoanOffers(self):
        """ Returns open loan offers """
        return self.__call__('returnOpenLoanOffers')

    def returnFeeInfo(self):
        """ Returns current trading fees and trailing 30-day volume in BTC """
        return self.__call__('returnFeeInfo')

    def returnLendingHistory(self, start=False, end=False, limit=False):
        if not start:
            start = time() - self.MONTH
        if not end:
            end = time()
        args = {'start': str(start), 'end': str(end)}
        if limit:
            args['limit'] = str(limit)
        return self.__call__('returnLendingHistory', args)

    def returnOrderTrades(self, orderId):
        """ Returns any trades made from <orderId> """
        return self.__call__('returnOrderTrades', {
                             'orderNumber': str(orderId)})

    def createLoanOffer(self, coin, amount, rate, autoRenew=0, duration=2):
        """ Creates a loan offer for <coin> for <amount> at <rate> """
        return self.__call__('createLoanOffer', {
            'currency': str(coin).upper(),
            'amount': str(amount),
            'duration': str(duration),
            'autoRenew': str(autoRenew),
            'lendingRate': str(rate)
        })

    def cancelLoanOffer(self, orderId):
        """ Cancels the loan offer with <orderId> """
        return self.__call__('cancelLoanOffer', {'orderNumber': str(orderId)})

    def toggleAutoRenew(self, orderId):
        """ Toggles the 'autorenew' feature on loan <orderId> """
        return self.__call__('toggleAutoRenew', {'orderNumber': str(orderId)})

    def closeMarginPosition(self, pair):
        """ Closes the margin position on <pair> """
        return self.__call__('closeMarginPosition', {
                             'currencyPair': str(pair).upper()})

    def marginBuy(self, pair, rate, amount, lendingRate=2):
        """ Creates <pair> margin buy order at <rate> for <amount> """
        return self.__call__('marginBuy', {
            'currencyPair': str(pair).upper(),
            'rate': str(rate),
            'amount': str(amount),
            'lendingRate': str(lendingRate)
        })

    def marginSell(self, pair, rate, amount, lendingRate=2):
        """ Creates <pair> margin sell order at <rate> for <amount> """
        return self.__call__('marginSell', {
            'currencyPair': str(pair).upper(),
            'rate': str(rate),
            'amount': str(amount),
            'lendingRate': str(lendingRate)
        })

    def buy(self, pair, rate, amount, orderType=False):
        """ Creates buy order for <pair> at <rate> for
            <amount> with optional orderType """

        req = {
            'currencyPair': str(pair).upper(),
            'rate': str(rate),
            'amount': str(amount),
        }

        # order type specified?
        if orderType:
            possTypes = ['fillOrKill', 'immediateOrCancel', 'postOnly']
            # check type
            if not orderType in possTypes:
                raise ValueError('Invalid orderType')
            req[orderType] = 1

        return self.__call__('buy', req)

    def sell(self, pair, rate, amount, orderType=False):
        """ Creates sell order for <pair> at <rate> for
            <amount> with optional orderType """

        req = {
            'currencyPair': str(pair).upper(),
            'rate': str(rate),
            'amount': str(amount),
        }

        # order type specified?
        if orderType:
            possTypes = ['fillOrKill', 'immediateOrCancel', 'postOnly']
            # check type
            if not orderType in possTypes:
                raise ValueError('Invalid orderType')
            req[orderType] = 1

        return self.__call__('sell', req)

    def cancelOrder(self, orderId):
        """ Cancels order <orderId> """
        return self.__call__('cancelOrder', {'orderNumber': str(orderId)})

    def moveOrder(self, orderId, rate, amount=False, orderType=False):
        """ Moves an order by <orderId> to <rate> for <amount> """

        req = {
            'orderNumber': str(orderId),
            'rate': str(rate)
        }
        if amount:
            req['amount'] = str(amount)
        # order type specified?
        if orderType:
            possTypes = ['immediateOrCancel', 'postOnly']
            # check type
            if not orderType in possTypes:
                raise ValueError('Invalid orderType')
            req[orderType] = 1

        return self.__call__('moveOrder', req)

    def withdraw(self, coin, amount, address, paymentId=False):
        """ Withdraws <coin> <amount> to <address> """
        req = {
            'currency': str(coin).upper(),
            'amount': str(amount),
            'address': str(address)
        }
        if paymentId:
            req['paymentId'] = str(paymentId)
        return self.__call__('withdraw', req)

    def transferBalance(self, coin, amount, fromac, toac):
        """
        Transfers coins between accounts (exchange, margin, lending)
        - moves <coin> <amount> from <fromac> to <toac>
        """
        return self.__call__('transferBalance', {
            'currency': str(coin).upper(),
            'amount': str(amount),
            'fromAccount': str(fromac),
            'toAccount': str(toac)
        })
