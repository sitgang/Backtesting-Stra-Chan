# encoding: UTF-8

'''
本文件中包含了CTA模块中用到的一些基础设置、类和常量等。
'''

from __future__ import division


# 把vn.trader根目录添加到python环境变量中
import sys
sys.path.append('..')


# 常量定义
# CTA引擎中涉及到的交易方向类型
CTAORDER_BUY = u'买开'
CTAORDER_SELL = u'卖平'
CTAORDER_SHORT = u'卖开'
CTAORDER_COVER = u'买平'

# 本地停止单状态
STOPORDER_WAITING = u'等待中'
STOPORDER_CANCELLED = u'已撤销'
STOPORDER_TRIGGERED = u'已触发'

# 本地停止单前缀
STOPORDERPREFIX = 'CtaStopOrder.'

# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# CTA引擎中涉及的数据类定义
from vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

########################################################################
class StopOrder(object):
    """本地停止单"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT
        
        self.strategy = None             # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号 
        self.status = EMPTY_STRING       # 停止单状态


########################################################################
class CtaBarData(object):
    """K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.open = EMPTY_FLOAT             # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT
        
        self.date = EMPTY_STRING            # bar开始的时间，日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        self.volume = EMPTY_INT             # 成交量
        self.openInterest = EMPTY_INT       # 持仓量
        
########################################################################

class CtaBaohanBarData(object):
    """包含后的K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.open = EMPTY_FLOAT             # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT
        
        self.direction = EMPTY_STRING       #相比于上一根是向上还是向下
        #方向有这么几个
        #DIRECTION_NONE = u'无方向'
        #DIRECTION_LONG = u'多'
        #DIRECTION_SHORT = u'空'
        
        self.date = EMPTY_STRING            # bar开始的时间，日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        self.volume = EMPTY_INT             # 成交量
        self.openInterest = EMPTY_INT       # 持仓量

########################################################################

class CtaFenxingData(object):
    """分型"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.ftype = EMPTY_STRING            #分型类型
        #类型有这么几个
        #FENXING_DING = u"顶分型"
        #FENXING_DI = u"底分型"
        self.bar_index =  EMPTY_INT       #形成分型的bar排在list里的第几，形成新分型的时候并不会找多
        self.price = EMPTY_FLOAT            #分型形成的高点
        
        self.date = EMPTY_STRING            # bar开始的时间，日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        

########################################################################

class CtaBiData(object):
    """笔"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.btype = EMPTY_STRING            #BI类型
        #类型有这么几个
        #BI_UP = u"UP"
        #BI_DOWN = u"DOWN"
        
        self.start_fenxing_index =  EMPTY_INT     #形成笔的前分型排在list里的第几
        self.end_fenxing_index =  EMPTY_INT       #形成笔的后分型排在list里的第几

        self.start_price = EMPTY_FLOAT            #分型形成的端点
        self.end_price = EMPTY_FLOAT              #分型形成的端点
        
        self.start_datetime = None                # python的datetime时间对象
        self.end_datetime = None                  # python的datetime时间对象
        
        self.bi_index = EMPTY_INT                 #形成的笔在bi_list里的第几
        
########################################################################

class CtaBaohanbiData(object):
    """包含笔"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.btype = EMPTY_STRING            #BI类型
        #类型有这么几个
        #BI_UP = u"UP"
        #BI_DOWN = u"DOWN"
        
        self.start_fenxing_index =  EMPTY_INT     #形成笔的前分型排在list里的第几
        self.end_fenxing_index =  EMPTY_INT       #形成笔的后分型排在list里的第几

        self.high_price = EMPTY_FLOAT            #包含过后的高价
        self.low_price = EMPTY_FLOAT              #包含过后的低价
        
        self.start_datetime = None                # python的datetime时间对象
        self.end_datetime = None                  # python的datetime时间对象
        
        self.bi_index = EMPTY_INT                 #这个index是指两个形成包含的特征笔的前一笔
        self.extreme_bi_index = EMPTY_INT         #这个index是指两个形成包含的特征笔的最高（低）一笔
        
########################################################################

class CtaXianduanData(object):
    """线段"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.xtype = EMPTY_STRING            #线段类型
        #类型有这么几个
        # 线段常量
        #XIANDUAN_UP = u"XIANDUAN_UP"
        #XIANDUAN_DOWN = u"XIANDUAN_DOWN"
        
        self.start_bi_index =  EMPTY_INT     #形成线段的笔分型排在list里的第几
        self.end_bi_index =  EMPTY_INT       #形成线段的笔分型排在list里的第几

        self.start_price = EMPTY_FLOAT            #线段形成的高点
        self.end_price = EMPTY_FLOAT              #线段形成的高点
        
        self.start_datetime = None                # python的datetime时间对象
        self.end_datetime = None                  # python的datetime时间对象
        
########################################################################

class CtaZhongshuData(object):
    """中枢"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        
        self.start_xianduan_index =  EMPTY_INT     #形成线段的笔分型排在list里的第几
        self.end_xianduan_index =  EMPTY_INT       #形成线段的笔分型排在list里的第几

        self.high_price = EMPTY_FLOAT            #中枢的上界
        self.low_price = EMPTY_FLOAT              #中枢的下界
        
        self.start_datetime = None                # python的datetime时间对象
        self.end_datetime = None                  # python的datetime时间对象
        
        self.start_plot_datetime = None                # python的datetime时间对象
        self.end_plot_datetime = None                  # python的datetime时间对象
        
        self.xd_list = []                       #用于装构成中枢的线段
        self.count = EMPTY_INT                  #由几个线段构成了这个中枢
        
########################################################################
class CtaTickData(object):
    """Tick数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""       
        self.vtSymbol = EMPTY_STRING            # vt系统代码
        self.symbol = EMPTY_STRING              # 合约代码
        self.exchange = EMPTY_STRING            # 交易所代码

        # 成交数据
        self.lastPrice = EMPTY_FLOAT            # 最新成交价
        self.volume = EMPTY_INT                 # 最新成交量
        self.openInterest = EMPTY_INT           # 持仓量
        
        self.upperLimit = EMPTY_FLOAT           # 涨停价
        self.lowerLimit = EMPTY_FLOAT           # 跌停价
        
        # tick的时间
        self.date = EMPTY_STRING            # 日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        # 五档行情
        self.bidPrice1 = EMPTY_FLOAT
        self.bidPrice2 = EMPTY_FLOAT
        self.bidPrice3 = EMPTY_FLOAT
        self.bidPrice4 = EMPTY_FLOAT
        self.bidPrice5 = EMPTY_FLOAT
        
        self.askPrice1 = EMPTY_FLOAT
        self.askPrice2 = EMPTY_FLOAT
        self.askPrice3 = EMPTY_FLOAT
        self.askPrice4 = EMPTY_FLOAT
        self.askPrice5 = EMPTY_FLOAT        
        
        self.bidVolume1 = EMPTY_INT
        self.bidVolume2 = EMPTY_INT
        self.bidVolume3 = EMPTY_INT
        self.bidVolume4 = EMPTY_INT
        self.bidVolume5 = EMPTY_INT
        
        self.askVolume1 = EMPTY_INT
        self.askVolume2 = EMPTY_INT
        self.askVolume3 = EMPTY_INT
        self.askVolume4 = EMPTY_INT
        self.askVolume5 = EMPTY_INT    