# encoding: UTF-8

'''
本文件中包含的是CTA模块的回测引擎，回测引擎的API和CTA引擎一致，
可以使用和实盘相同的代码进行回测。
'''
from __future__ import division
#import sys 
#reload(sys) 
#sys.setdefaultencoding('utf-8') 
from datetime import datetime, timedelta
from collections import OrderedDict,defaultdict
from itertools import product
import matplotlib.pyplot as plt
import pandas as pd
pd.options.display.max_rows = 8
pd.options.mode.chained_assignment = None # default='warn' # 因为我并不在意dataframe是否被赋值
import numpy as np
import pymongo, os, json, time
from colorama import init,Fore
init(autoreset = True)


from ctaBase import *
from ctaSetting import *

from vtConstant import *
from vtGateway import VtOrderData, VtTradeData,VtAccountData
from vtFunction import loadMongoSetting
from Chan_Functions import *

#字体颜色
#REDPREFIX = u'\x1b[31m'
#GREENPREFIX = u'\x1b[32m'
#YELLOWPREFIX = u'\x1b[33m'
#BLUEPREFIX = u'\x1b[34m'

########################################################################
class BacktestingEngine(object):
    """
    CTA回测引擎
    函数接口和策略引擎保持一样，
    从而实现同一套代码从回测到实盘。
    """
    
    TICK_MODE = 'tick'
    BAR_MODE = 'bar'
    settingFileName = 'CTA_setting.json'
    contractSettingFileName = 'Contact_setting.json'
    settingFileName = '/Users/xuegeng/Desktop/Algo 2/' + settingFileName
    contractSettingFileName = '/Users/xuegeng/Desktop/Algo 2/' + contractSettingFileName

    #----------------------------------------------------------------------
    def __init__(self):
        
        self.contractInfo = {}  #合约配置，key为合约名称，value为字典
                                #keys为size, slippage,commission，margin                
        self.strategyDict = {}  #key为合约名称，value为策略实例
    
        self.dataStartDate = None       # 回测数据开始日期，datetime对象
        self.dataEndDate = None         # 回测数据结束日期，datetime对象
        self.strategyStartDate = None   # 策略启动日期（即前面的数据用于初始化），datetime对象
    
        self.dbName = ''            # 回测数据库名
        self.symbols = []           # contractInfo的keys
    
        self.mode = self.BAR_MODE   # 回测模式，默认为K线
    
        self.dbClient = None        # 数据库客户端
    
        self.initData = {}          #key为合约策略名称,value是包含初始化数据的列表
                                    #表里面是data数据
        self.dataframe = pd.DataFrame()       #总的回测数据
        
        self.logList = []               # 日志记录
        self.account = VtAccountData()  # 账户信息
        self.account.available = 1000000
        self.initCapital = 1000000
        
        self.workingLimitOrderDict = {}
        self.limitOrderDict = {}
        self.workingStopOrderDict = {}
        self.stopOrderDict = {}
        self.limitOrderCount = 0
        self.stopOrderCount = 0

        self.tradeDict = {}
        self.tradeCount = 0
        
        self.resultList = []  #交易结果
    
    #----------------------------------------------------------------------
    def setStartDate(self, startDate='20100416'):
        """设置回测的启动日期"""
        self.dataStartDate = datetime.strptime(startDate, '%Y%m%d')
        
#        initTimeDelta = timedelta(initDays)
        self.strategyStartDate = self.dataStartDate

    #----------------------------------------------------------------------
    def setEndDate(self, endDate=''):
        """设置回测的结束日期"""
        if endDate:
            self.dataEndDate= datetime.strptime(endDate, '%Y%m%d')

     #----------------------------------------------------------------------
    def setBacktestingMode(self, mode):
        """设置回测模式"""
        self.mode = mode
    
    #----------------------------------------------------------------------
    def setDatabase(self, dbName, symbol):
        """设置历史数据所用的数据库"""
        self.dbName = dbName
    
    #----------------------------------------------------------------------
    def loadContractSetting(self):
        """读取合约配置"""
        with open(self.contractSettingFileName) as f:
            self.contractInfo = json.load(f)
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingFileName) as f:
            l = json.load(f)
            
            for setting in l:
                self.loadStrategy(setting)
    
            self.symbols = self.strategyDict.keys()
            for symbol in self.symbols:
                self.workingLimitOrderDict[symbol] = {}
                self.limitOrderDict[symbol] = {}
                self.workingStopOrderDict[symbol] = {}
                self.stopOrderDict[symbol] = {}
                self.tradeDict[symbol] = {}
                
        self.loadContractSetting()  
     #----------------------------------------------------------------------
    def loadStrategy(self, setting):
        """载入策略"""
        try:
            name = setting['name']
            className = setting['className']
            vtSymbol = setting['vtSymbol']
            self.output( u"载入策略： " + name)
        except Exception, e:
            self.writeCtaLog(u'载入策略出错：%s' %e)
            return
        
        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        
        if not strategyClass:
            self.writeCtaLog(u'找不到策略类：%s' %className)
            return
      
        # 创建策略实例
        strategy = strategyClass(self, setting)  
        self.strategyDict[vtSymbol] = strategy
        
        #不保存tick映射
        #不订阅合约
        
    #----------------------------------------------------------------------
    def loadHistoryData(self):
        """载入历史数据"""
        host, port = loadMongoSetting()
        
        self.dbClient = pymongo.MongoClient(host, port)
        self.output(u'开始载入数据')
                
        for symbol in self.symbols:
            
            self.output(u"载入历史数据" + str(symbol))
            
            collection = self.dbClient[self.dbName][symbol]
    
            # 载入回测数据
            if not self.dataEndDate:
                flt = {'datetime':{'$gte':self.strategyStartDate}}   # 数据过滤条件
            else:
                flt = {'datetime':{'$gte':self.strategyStartDate,
                    '$lte':self.dataEndDate}}
            dbCursor = collection.find(flt)
            initData =[]
            for d in dbCursor:
                initData.append(d)

            if self.dataframe.empty:
                self.dataframe = pd.DataFrame(initData)
            else:
                self.dataframe = pd.concat([self.dataframe,pd.DataFrame(initData)])
                    
            #这里只管喂就好了，初始化的逻辑交给策略
        df = self.dataframe.drop_duplicates()
        del df['_id']
        df = to_transed_eve(df)
        df = df.sort_values('datetime')
        index = pd.Index(np.arange(df.count()[0]))
        df.index = index
        df[['open','close','low','high']] = df[['open','close','low','high']].applymap(float)
        df[['volume']] = df[['volume']].applymap(int)
        
        
        self.dataframe = df
        
        
        
        self.output(u'载入完成，数据量：%s' %(self.dataframe.count()[0]))


    #----------------------------------------------------------------------
    def runBacktesting(self):
        """运行回测"""
        # 载入历史数据
        self.loadHistoryData()
        
        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = CtaBarData
            func = self.newBar
        else:
            dataClass = CtaTickData
            func = self.newTick
        
        self.output(u'开始回测')
        
       
        for strategy in self.strategyDict.values():
            strategy.inited = True
            strategy.onInit()
        self.output(u'策略初始化完成')
        
        for strategy in self.strategyDict.values():
            strategy.trading = True
            strategy.onStart()
        self.output(u'策略启动完成')
        
        self.output(u'开始回放数据')
        
        

        
        for i in range(self.dataframe.count()[0]):
            dict_ = self.dataframe.ix[i].to_dict()
            data = dataClass()
            data.__dict__ = dict_
            #time.sleep(0.1)
            func(data)
        
        
#        print BLUEPREFIX + str(self.tradeDict['PP1702'].values())
#        print "\n\n"
#        for trade in self.tradeDict['PP1702'].values():
#            print REDPREFIX + str(trade.price) + " " +trade.direction + " " + trade.offset + " " + str(trade.volume)
        self.output(u'数据回放结束')
    
     #----------------------------------------------------------------------
    def newBar(self, bar):
        """新的K线"""
        self.bar = bar
        self.dt = bar.datetime
        self.crossLimitOrder()      # 先撮合限价单
        self.crossStopOrder()       # 再撮合停止单
        stra = self.strategyDict[bar.symbol]
        #print bar.datetime
        stra.onBar(bar)    # 推送K线到策略中
    #----------------------------------------------------------------------
    def newTick(self, tick):
        """新的Tick"""
        self.tick = tick
        self.dt = tick.datetime
        self.crossLimitOrder()
        self.crossStopOrder()
        
        stra = self.strategyDict[tick.symbol]
        stra.onTick(tick)
    #----------------------------------------------------------------------
    def initStrategy(self, strategyClass, setting=None):
        """
        初始化策略
        setting是策略的参数设置，如果使用类中写好的默认设置则可以不传该参数
        """
    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)
        
        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = price
        order.totalVolume = volume
        order.status = STATUS_NOTTRADED     # 刚提交尚未成交
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = str(self.dt)
        
        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE
        
        # 保存到限价单字典中
        try:
            self.workingLimitOrderDict[vtSymbol][orderID] = order
            self.limitOrderDict[vtSymbol][orderID] = order
        except KeyError:
            self.workingLimitOrderDict[vtSymbol] = {}
            self.workingLimitOrderDict[vtSymbol][orderID] = order
            self.limitOrderDict[vtSymbol] = {}
            self.limitOrderDict[vtSymbol][orderID] = order

        return orderID#会返回orderID的

     #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        if vtOrderID in self.workingLimitOrderDict[self.bar.symbol]:
            order = self.workingLimitOrderDict[self.bar.symbol][vtOrderID]
            order.status = STATUS_CANCELLED
            order.cancelTime = str(self.dt)
            del self.workingLimitOrderDict[self.bar.symbol][vtOrderID]
    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        
        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE
        
        # 保存stopOrder对象到字典中
        self.stopOrderDict[vtSymbol][stopOrderID] = so
        self.workingStopOrderDict[vtSymbol][stopOrderID] = so
        
        return stopOrderID
     #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        if stopOrderID in self.workingStopOrderDict[self.bar.symbol]:
            so = self.workingStopOrderDict[self.bar.symbol][stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[self.bar.symbol][stopOrderID]
     #----------------------------------------------------------------------
    def crossLimitOrder(self):
        """基于最新数据撮合限价单"""
        # 先确定会撮合成交的价格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low        # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = self.bar.high      # 若卖出方向限价单价格低于该价格，则会成交
            buyBestCrossPrice = self.bar.open   # 在当前时间点前发出的买入委托可能的最优成交价
            sellBestCrossPrice = self.bar.open  # 在当前时间点前发出的卖出委托可能的最优成交价
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1
        
        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict[self.bar.symbol].items():
            # 判断是否会成交
            buyCross = order.direction==DIRECTION_LONG and order.price>=buyCrossPrice
            sellCross = order.direction==DIRECTION_SHORT and order.price<=sellCrossPrice
            
            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset
                
                # 以买入为例：
                # 1. 假设当根K线的OHLC分别为：100, 125, 90, 110
                # 2. 假设在上一根K线结束(也是当前K线开始)的时刻，策略发出的委托为限价105
                # 3. 则在实际中的成交价会是100而不是105，因为委托发出时市场的最优价格是100
                if buyCross:
                    trade.price = min(order.price, buyBestCrossPrice)
                    stra = self.strategyDict[self.bar.symbol]
                    stra.pos += order.totalVolume
                    #print "a"
                
                else:
                    trade.price = max(order.price, sellBestCrossPrice)
                    stra = self.strategyDict[self.bar.symbol]
                    stra.pos -= order.totalVolume
                
                trade.volume = order.totalVolume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                trade.symbol  = self.bar.symbol
                stra = self.strategyDict[self.bar.symbol]
                stra.onTrade(trade)
                #print trade.direction
                
                self.tradeDict[trade.vtSymbol][tradeID] = trade
 
                '''#在此处更新回测账户'''
                #print REDPREFIX +str(trade.symbol) + "\t"+  "%.1f"%trade.price + "\t" +\
                #        trade.direction + "\t" + trade.offset + "\t" + str(trade.volume)
                self.updateAccount(trade)
                
                # 推送委托数据
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
        
                stra = self.strategyDict[self.bar.symbol]
                stra.onOrder(order)
                
                # 从字典中删除该限价单
                del self.workingLimitOrderDict[self.bar.symbol][orderID]
    #----------------------------------------------------------------------
    def crossStopOrder(self):
        """基于最新数据撮合停止单"""
        # 先确定会撮合成交的价格，这里和限价单规则相反
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.high    # 若买入方向停止单价格低于该价格，则会成交
            sellCrossPrice = self.bar.low    # 若卖出方向限价单价格高于该价格，则会成交
            bestCrossPrice = self.bar.open   # 最优成交价，买入停止单不能低于，卖出停止单不能高于
        else:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            bestCrossPrice = self.tick.lastPrice
        
        # 遍历停止单字典中的所有停止单
        for stopOrderID, so in self.workingStopOrderDict[self.bar.symbol].items():
            # 判断是否会成交
            buyCross = so.direction==DIRECTION_LONG and so.price<=buyCrossPrice
            sellCross = so.direction==DIRECTION_SHORT and so.price>=sellCrossPrice
            
            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = so.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                
                if buyCross:
                    self.strategyDict[self.bar.symbol].pos += so.volume
                    trade.price = max(bestCrossPrice, so.price)
                else:
                    self.strategyDict[self.bar.symbol].pos -= so.volume
                    trade.price = min(bestCrossPrice, so.price)
                
                self.limitOrderCount += 1
                orderID = str(self.limitOrderCount)
                trade.orderID = orderID
                trade.vtOrderID = orderID
                
                trade.direction = so.direction
                trade.offset = so.offset
                trade.volume = so.volume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                trade.symbol  = self.bar.symbol
                stra = self.strategyDict[self.bar.symbol]
                stra.onTrade(trade)
                
                self.tradeDict[trade.vtSymbol][tradeID] = trade
                
                '''#在此处更新回测账户'''
                #print REDPREFIX + str(trade.symbol) + "\t"+  "%.1f"%trade.price + "\t" +\
                #        trade.direction + "\t" + trade.offset + "\t" + str(trade.volume)
                self.updateAccount(trade)
                
                # 推送委托数据
                so.status = STOPORDER_TRIGGERED
                
                order = VtOrderData()
                order.vtSymbol = so.vtSymbol
                order.symbol = so.vtSymbol
                order.orderID = orderID
                order.vtOrderID = orderID
                order.direction = so.direction
                order.offset = so.offset
                order.price = so.price
                order.totalVolume = so.volume
                order.tradedVolume = so.volume
                order.status = STATUS_ALLTRADED
                order.orderTime = trade.tradeTime
                
                
                stra = self.strategyDict[self.bar.symbol]
                stra.onOrder(order)
                
                self.limitOrderDict[order.symbol][orderID] = order
                
                # 从字典中删除该限价单
                del self.workingStopOrderDict[order.symbol][stopOrderID]
    #----------------------------------------------------------------------
    def updateAccount(self,trade):
        '''根据成交数据更新账户信息'''
        price = trade.price
        volume = trade.volume
        direction = trade.direction
        symbol = trade.vtSymbol
        margin = self.contractInfo[symbol]['margin']
        size = self.contractInfo[symbol]['size']
        
        if direction == u"空":
            volume = -volume
        
        self.account.available += size * price * margin * volume
        
        #将账户信息推送到
        for stra in self.strategyDict.values():
            try:
                stra.onAccount(self.account)
            except NotImplementedError:
                pass

    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """考虑到回测中不允许向数据库插入数据，防止实盘交易中的一些代码出错"""
        pass
    
    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Bar"""
        return self.initData
    
    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Tick"""
        return self.initData

    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录日志"""
        log = str(datetime.now()) + ' ' + content 
        self.logList.append(log)
        
    #----------------------------------------------------------------------
    def output(self, content):
        """输出内容"""
        print unicode(datetime.now()) + u"\t" + content 
    #----------------------------------------------------------------------
    def calculateBacktestingResult(self):
        """
        计算回测结果
        """
        #将交易结果化为dataframe
        tradeResult = []
        def todict(t):return t.__dict__
        for symbol in self.tradeDict.keys():
            tradeResult.extend(self.tradeDict[symbol].values())
            
        tradeResult = map(todict,tradeResult)
        d = pd.DataFrame(tradeResult)
        d= d.sort_values('dt')
        index = pd.Index(np.arange(d.count()[0]))
        d.index = index
        
        self.output(u'计算回测结果')
        
        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        self.resultList = []             # 交易结果列表
        longTrade = {}              # 未平仓的多头交易
        shortTrade = {}             # 未平仓的空头交易
        symbolNow = ''              # 当前的交易标的
        for symbol in self.symbols:
            longTrade[symbol] = []
            shortTrade[symbol] = []
        for i in range(d.count()[0]):
            dict_ = d.ix[i].to_dict()
            trade = VtTradeData()
            trade.__dict__ = dict_
            
            # 这些变量会被较多地引用，故先赋值
#            if not symbolNow :
#                symbolNow = trade.vtSymbol
            if symbolNow != trade.vtSymbol:
                symbolNow = trade.vtSymbol
                commission = self.contractInfo[trade.vtSymbol]['commission']
                slippage = self.contractInfo[trade.vtSymbol]['slippage']
                size = self.contractInfo[trade.vtSymbol]['size']
                margin = self.contractInfo[trade.vtSymbol]['margin']
            elif symbolNow == trade.vtSymbol:
                pass
    
            # 多头交易
            if trade.direction == DIRECTION_LONG:
                # 如果尚无空头交易
                if not shortTrade[symbolNow]:
                    longTrade[symbolNow].append(trade)
                # 当前多头交易为平空
                else:
                    while True:
                        entryTrade = shortTrade[symbolNow][0]
                        exitTrade = trade
                        
                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(symbolNow,entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,-closedVolume,
                                               commission,slippage,size,margin)
                        #print BLUEPREFIX + str(result.pnl)
                        #print result.volume
                        self.resultList.append(result)
                        
                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume
                        
                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            shortTrade[symbolNow].pop(0)
                        
                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break
                        
                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not shortTrade[symbolNow]:
                                longTrade[symbolNow].append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass
                        
            # 空头交易        
            else:
                # 如果尚无多头交易
                if not longTrade[symbolNow]:
                    shortTrade[symbolNow].append(trade)
                # 当前空头交易为平多
                else:                    
                    while True:
                        entryTrade = longTrade[symbolNow][0]
                        exitTrade = trade
                        
                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(symbolNow,entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,closedVolume,
                                               commission,slippage,size,margin)
                        #print BLUEPREFIX + str(result.pnl)
                        #print result.volume
                        self.resultList.append(result)
                        
                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume
                        
                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            longTrade[symbolNow].pop(0)
                        
                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break
                        
                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not longTrade[symbolNow]:
                                shortTrade[symbolNow].append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass                    
                    
        # 检查是否有交易
        if not self.resultList:
            self.output(u'无交易结果')
            return {}
        
        #将各标的交易的持仓区间用Series来表示持仓浮盈
        floatProfit = defaultdict(list)   #key为symbol，value是包含sr的list
        df = self.dataframe.set_index('datetime').sort_index().drop_duplicates()
        pnlList = []
        for result in self.resultList:
            symbolDf = df[df.symbol == result.symbol]
            symbolDf = symbolDf[result.entryDt:result.exitDt]#+ delta]
            symbolDf = symbolDf.drop_duplicates().sort_index()
            sr = (symbolDf['close'] - symbolDf.ix[0]['close']) * result.size *self.contractInfo[result.symbol]['margin']* result.volume #- result.commission #- result.slippage
            floatProfit[result.symbol].append(sr)       #每笔交易区间的资金变化
            pnlList.append(result.pnl)                  #每笔交易的利润
#===========================================================================
            #print str(result.entryDt) + " =====> " + str(result.exitDt) + " ==========>>>  " + str(result.pnl)

        index = np.unique(df.index)
        capitalSr = pd.Series(0,index = index)
        for lsSymbol in floatProfit.values():
            for floatSr in lsSymbol:
                #print GREENPREFIX + str(floatSr) + "\n\n"
                floatSr = pd.Series(floatSr,index = index)
                floatSr = floatSr.fillna(method='ffill').fillna(0)
                capitalSr += floatSr
                
        capitalSr = capitalSr.drop_duplicates()
        capitalSr = capitalSr +self.initCapital    #可以看到回测期间的资金变化
        
        pnlStat = pd.Series(pnlList) # 盈利序列
        drawdownSr = capitalSr.cummax() - capitalSr  # 回测序列
#===========================================================================

        # 计算盈亏相关数据
        winningRate = pnlStat[pnlStat>0].count()/pnlStat.count()    #胜率
        averageWinning = pnlStat[pnlStat>0].mean()             # 平均每笔盈利
        averageLosing = pnlStat[pnlStat<0].mean()                # 平均每笔亏损
        profitLossRatio = -averageWinning/averageLosing         # 盈亏比
        
        #稳健指标计算    
        #回归年度回报率
        lenSr = len(capitalSr)
        m,b = np.polyfit(np.arange(lenSr), capitalSr.tolist(), 1)# 对资金曲线进行简单回归
        expectedMonthlyReturn = lenSr * m / b                   # 回测收益率
        testInterval = ((capitalSr.index[-1] - capitalSr.index[0]).days /30.0) # 测试区间对应的时间长度（月）
        monthlyReturnRatio = expectedMonthlyReturn / testInterval #月化收益率
        RAR = (1 + monthlyReturnRatio )**12 - 1 # 回归年度回报率
        
        #稳健风险回报比率
        temp = 0;maxDrawdownLs = []
        for i in range(1,len(drawdownSr)):
            if drawdownSr[i] == 0:
                tempDrawdown = drawdownSr[temp:i].max()
                if tempDrawdown != 0:
                    maxDrawdownLs.append(tempDrawdown)
                    temp = i
        
        if len(maxDrawdownLs) >= 5:
            aveDrawdown = np.mean(maxDrawdownLs[-5:]) # 五次最大回测的平均值
        else:
            aveDrawdown = np.mean(maxDrawdownLs) # 五次最大回测的平均值
        RCube = RAR / aveDrawdown        #稳健风险回报比率

        
        # 返回回测结果
        d = {}
        d['capital'] = capitalSr[-1] / self.initCapital
        d['maxCapital'] = capitalSr.max()
        d['maxdrawdown'] = (pnlStat.cummax() - pnlStat).max()
        d['maxdrawdownDay'] = drawdownSr.argmax().isoformat()
        d['totalResult'] = pnlStat.count()
        d['pnlList'] = pnlList
        d['capitalSr'] = capitalSr
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['floatProfit'] = floatProfit
        
        
        d['RAR'] = RAR
        d['RCube'] = RCube
        
        return d
        
    #----------------------------------------------------------------------
    def showBacktestingResult(self,d):
        """
        显示回测结果
        """
        capitalSr = d['capitalSr']
        floatProfit = d['floatProfit']
        pnlList = d['pnlList']
        
        # 输出
        self.output('-' * 30)
        self.output(u'第一笔交易：  \t%s' % capitalSr.index[0])
        self.output(u'最后一笔交易：\t%s' % capitalSr.index[-1])
        
        self.output(u'总交易次数：  \t%s' % formatNumber(d['totalResult']))        
        self.output(u'总盈亏：      \t%s' % formatNumber(d['capital']))
        self.output(u'最大回撤:     \t%s' % formatNumber(d['maxdrawdown']))                
        self.output(u'最大回撤时间: \t%s' % d['maxdrawdownDay'])                

        
        self.output(u'胜率          \t%s%%' %formatNumber(d['winningRate']*100))
        self.output(u'平均每笔盈利  \t%s' %formatNumber(d['averageWinning']))
        self.output(u'平均每笔亏损  \t%s' %formatNumber(d['averageLosing']))
        self.output(u'盈亏比：      \t%s' %formatNumber(d['profitLossRatio']))
        
        self.output(u'回归年度回报率(RAR)    \t%s'%formatNumber(d['RAR']))
        self.output(u'稳健风险回报比率(R立方)\t%s'%formatNumber(d['RCube']))
    
        #绘图
        x = np.array(capitalSr.index.tolist())  # 时间列表
        y1 = np.array(capitalSr)                # 资金列表
        y2 =np.array(capitalSr.cummax())        # 最大资金列表
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1,figsize = (20,12))
        
        ax1.grid(color='black', linestyle='-', linewidth=0.6,alpha = 0.5)
        ax1.plot(x,y1,axes = ax1,c='c',lw=1.6)
        ax1.set_ylabel('Capital')
        ax1.legend(['Capital'])#资金曲线图
        
        ax2.grid(color='black', linestyle='-', linewidth=0.6,alpha = 0.5)
        ax2.fill_between(x,y1,y2,alpha = 0.6,facecolor='r')
        ax2.fill_between(x,y1,ax2.get_ylim()[0],facecolor='c')
        ax2.set_ylabel('Withdraw')
        
        ax3.grid(color='black', linestyle='-', linewidth=0.6,alpha = 0.5)
        ax3.hist(pnlList,color = 'c',alpha = 0.8)
        ax3.set_ylabel('pnl Counts')
        
        plt.show()
        
        
     #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """发送策略更新事件，回测中忽略"""
        pass

    #----------------------------------------------------------------------
    def setSlippage(self, slippage):
        """设置滑点点数"""
        self.slippage = slippage
        
    #----------------------------------------------------------------------
    def setSize(self, size):
        """设置合约大小"""
        self.size = size
        
    #----------------------------------------------------------------------
    def setRate(self, rate):
        """设置佣金比例"""
        self.rate = rate
#----------------------------------------------------------------------
def formatNumber(n):
    """格式化数字到字符串"""
    n = round(n, 2)         # 保留两位小数
    return format(n, ',')   # 加上千分符        
########################################################################
class TradingResult(object):
    """每笔交易的结果"""

    #----------------------------------------------------------------------
    def __init__(self, symbol, entryPrice, entryDt, exitPrice, 
                 exitDt, volume, rate, slippage, size ,margin):
        """Constructor"""
        self.entryPrice = entryPrice    # 开仓价格
        self.exitPrice = exitPrice      # 平仓价格
        
        self.entryDt = entryDt          # 开仓时间datetime    
        self.exitDt = exitDt            # 平仓时间
        
        self.volume = volume    # 交易数量（+/-代表方向）
        self.symbol = symbol
        self.size = size
        
        self.turnover = (self.entryPrice+self.exitPrice)*size*abs(volume)   # 成交金额
        self.commission = self.turnover*rate                                # 手续费成本
        self.slippage = slippage*2*size*abs(volume)                         # 滑点成本
        self.pnl = (self.exitPrice - self.entryPrice) * volume * size * margin
                    #- self.commission - self.slippage)                      # 净盈亏


if __name__ == '__main__':

    engine = BacktestingEngine()
    
    engine.setDatabase("VnTrader_1Min_Db",None)
    engine.setStartDate('20170101')
    #engine.setEndDate('20160404')
    engine.loadSetting()
    engine.runBacktesting()

    df = engine.dataframe
    st = engine.strategyDict['rb0000']
    df3 = pd.DataFrame(map(lambda x:{"datetime":x.datetime,"close":x.close,"open":x.open,"high":x.high,"low":x.low},st.baohanbar_list))
    #因为我不在意开盘价和收盘价，所以强行改变开收盘价好看
    df3['close'][df3.close > df3.open] =  df3.high
    df3['open'][df3.close > df3.open] =  df3.low
    df3['close'][df3.close <= df3.open] =  df3.low
    df3['open'][df3.close <= df3.open] =  df3.high
    
    
    dd = dict(map(lambda x:(x[1],x[0]),df3.datetime.to_dict().items()))
    #st.plotCandlestick(df3)
    #st.plotFenxing()
    #st.plotBi()
    #st.plotXianduan()
    #st.plotZhongshu()
    
    #st.plotCandlestick2(df3)
    #st.plotBi2(dd)
    #st.plotXianduan2(dd)
    #st.plotZhongshu2(dd)
       
    