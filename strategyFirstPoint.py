 # encoding: UTF-8

from ctaBase import *
from ctaTemplate import CtaTemplate
from vtGateway import VtOrderData, VtTradeData,VtAccountData
from vtConstant import *
from ctaSetting import *
from vtFunction import mailhelper

import datetime
import pandas as pd
import talib,math
import numpy as np

#BERTREND
UP  = "UP"
DOWN = "DOWN"
DING = "DING"
DI = "DI"
FENXINGDISTANCE = 4#两分型（counter）之间距离大于等于4


########################################################################
class FirstPointStrategy(CtaTemplate):
    """关于利用macd的时间力度辅助判断第一买卖点的交易策略"""
    className = u'FirstPointStrategy'
    author = u'薛耕'

    # 策略参数
    initDays = 40           # 初始化数据所用的天数

    # 策略变量
    tickPrice = None
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟
    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数

    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
         
        """===========================申明变量=============================="""
        super(FirstPointStrategy, self).__init__(ctaEngine, setting)
       
        ###测试变量
        self.start_time = datetime.datetime(2016,11,24)
        self.end_time = None
        self.vAvailable = 1000000.0#虚拟可用资金
        self.vRate = 0.6#保证金比例
        
        
        
        ###指标变量
        self.closes = []
        self.macd_len = 34
        self.macd_area_buffer = []#分型出现就清空，添加入backup，macd数据加入areas
        self.macd_area_backup = []#替换不清空
        self.macd_areas = []#第一个分型不去比较红蓝柱子面积
        self.macd_duration = []#此次分型对应的macd除以此次分型形成时间的值
        self.bolling_len = 5
        self.bolling_fenxing = []#布尔值数列，表示分型是否处在超强区域
        self.powerful_area = False#是否在超强区域
        
        self.last_fenxing_datetime = None
        self.last_fenxing_type = None
        
        ###交易变量
        self.last_fenxing_datetime2 = None
        self.volume = 1#新增分型购买手数，每替代一次手数加一
        self.real_volume = 1#根据基数来确定买入量
        self.max_replace_counts = 4
        self.ding_signal = False
        self.di_signal = False
        self.risk_rate = 0.8
        self.account = VtAccountData()
        self.mh = mailhelper()
       
        ###分型变量
        self.fenxing = None
        self.lastFenxing = None
        self.fenxingCounter = 0
        self.lastFenxingCounter = 0
        
        ###k线变量
        self.newBar = None
        self.firstBar = None
        self.middleBar = None
        self.lastBar = None
        self.barCounter = 0
        self.barTrend = None#改变为常量
        self.bars = []
        
        ###包含变量
        self.hasBaohan = False
        
        ###统计变量
        self.fenxingTuples = []
      
        
                

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    
    def onAccount(self, account):
        """获取账户信息"""
        self.account = account  #VtAccountData
    
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:    
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice
            self.tickPrice = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间

            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        """这个好，撤销之前的单"""
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

       
        
        self.newBar = bar.__dict__
        self.process_baohan()
        self.process_fenxing()
        self.process_indextools()
        self.process_tradesignal()
#        self.process_sendmail()
        self.process_ordertrigger()
        self.newBar = None
        
        # 计算指标数值
      
        
        # 发出状态更新事件
        self.putEvent()
    
    def process_baohan(self):
        """===========================包含函数=================================="""
        """
        存在包含条件的k线进行包含处理
        """
        if self.lastFenxing and\
            self.newBar['low'] >= self.lastBar['low'] and\
            self.newBar['high'] <= self.lastBar['high']:#存在包含关系;分型之后才需要判断包含
                
            self.hasBaohan = True
        
        else:
            self.hasBaohan = False
            self.firstBar = self.middleBar
            self.middleBar = self.lastBar
            self.lastBar = self.newBar
            self.barCounter += 1
            self.bars.append(self.newBar)        
    
    def process_fenxing(self):
        """===========================分型函数=============================="""
        """
        用于确定顶分型和底分型
        """
        if self.firstBar == None:return
        #顶分型
        if (self.middleBar['high'] > self.firstBar['high'] and self.middleBar['high'] > self.lastBar['high']
            and self.middleBar['low'] > self.firstBar['low'] and self.middleBar['low'] > self.firstBar['low']):
            self.fenxing = (self.middleBar['datetime'],self.middleBar['high'],DING)
            self.fenxingCounter = self.barCounter
            
            try:#如果上个分型不存在，直接加入分型队列
                assert self.lastFenxing
            except AssertionError:
                self.fenxingTuples.append(self.fenxing)
                self.lastFenxing = self.fenxing
                self.lastFenxingCounter = self.fenxingCounter
            
            if self.lastFenxing[2] == DING:#如果上一个分型也是顶分型的话，保留高的那个
                if self.fenxing[1] >= self.lastFenxing[1]:#如果后来居上
                    self.fenxingTuples[-1] = self.fenxing
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
                else:#后者顶分型力度不够
                    pass
                    
            else:#上一个分型是底分型,无共用K线，就加入列表，确认分型
                if self.fenxingCounter - self.lastFenxingCounter >= FENXINGDISTANCE :#无共用k线
                    self.fenxingTuples.append(self.fenxing)
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
            
        #底分型
        elif (self.middleBar['high'] < self.firstBar['high'] and self.middleBar['high'] < self.lastBar['high']
            and self.middleBar['low'] < self.firstBar['low'] and self.middleBar['low'] < self.firstBar['low']):
            
            self.fenxing = (self.middleBar['datetime'],self.middleBar['low'],DI)
            self.fenxingCounter = self.barCounter
            
            try:#如果上个分型不存在，直接加入分型队列
                assert self.lastFenxing
            except AssertionError:
                self.fenxingTuples.append(self.fenxing)
                self.lastFenxing = self.fenxing
                self.lastFenxingCounter = self.fenxingCounter
            
            
            if self.lastFenxing[2] == DI:#如果上一个分型也是底分型的话，保留低的那个
                
                if self.fenxing[1] <= self.lastFenxing[1]:#如果后来居下
                    self.fenxingTuples[-1] = self.fenxing
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
                
                else:#后者底分型力度不够
                    pass
            else:#上一个分型是顶分型,无共用K线，就加入列表，确认分型
                if self.fenxingCounter - self.lastFenxingCounter >= FENXINGDISTANCE :#无共用k线
                    self.fenxingTuples.append(self.fenxing)
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
        #无分型
        else:
            pass
        
    
    def process_indextools(self):
        
        """======================更新辅助指标=================="""
        
        ###更新closes
        close = self.newBar['close']
        self.closes.append(close)
        if len(self.closes) < self.macd_len:return#如果收盘价列表不够用于计算，则继续添加
        if len(self.fenxingTuples)<=1:return#如果两个分型都没有，则继续等待分型
        now_fenxing = self.fenxingTuples[-1]
        ###判断分型是否更新
        ###未更新
        if self.last_fenxing_datetime == now_fenxing[0]:
            
            self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
            
            
        ###更新了
        else:
            ###替代前分型
            if self.last_fenxing_type == now_fenxing[2]:
                
                #macd处理
                self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
                self.macd_area_backup.extend(self.macd_area_buffer)#backup加入buffer
                macd_area = sum(self.macd_area_backup)#计算
                self.macd_areas[-1] = (now_fenxing[0],macd_area)#替换最后一个红蓝柱面积
                self.macd_duration[-1] = (now_fenxing[0],macd_area/(self.fenxingTuples[-1][0]-self.fenxingTuples[-2][0]).total_seconds())
                self.macd_area_buffer = []#清空buffer
                
                #bolling处理
                ceil = talib.BBANDS(np.array(self.closes))[0][-2]
                floor = talib.BBANDS(np.array(self.closes))[-1][-2]
                self.powerful_area = ((now_fenxing[1] > ceil) | (now_fenxing[1] < floor))
                self.bolling_fenxing[-1] = (now_fenxing[0],self.powerful_area)
                
                #判断变量
                self.last_fenxing_datetime = now_fenxing[0]
                
            ###增加新的分型    
            else:
                
                #macd处理
                self.macd_area_backup = []#清空backup
                self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
                self.macd_area_backup.extend(self.macd_area_buffer)#backup加入buffer
                macd_area = sum(self.macd_area_backup)
                self.macd_areas.append((now_fenxing[0],macd_area))#增加一个红蓝柱面积
                self.macd_duration.append((now_fenxing[0],macd_area/(self.fenxingTuples[-1][0]-self.fenxingTuples[-2][0]).total_seconds()))
                self.macd_area_buffer = []#清空buffer
                
                #bolling处理
                ceil = talib.BBANDS(np.array(self.closes))[0][-2]
                floor = talib.BBANDS(np.array(self.closes))[-1][-2]
                self.powerful_area = ((now_fenxing[1] > ceil) | (now_fenxing[1] < floor))
                self.bolling_fenxing.append((now_fenxing[0],self.powerful_area))
                
                #判断变量
                self.last_fenxing_datetime = now_fenxing[0]
                self.last_fenxing_type = now_fenxing[2]
    
    def process_tradesignal(self):
        
        """======================发出交易信号=================="""
        
        #有三个分型即可判断指标，因为这是第一买卖点策略
        if len(self.fenxingTuples) <= 4:return #如果三个分型都没有，则继续等待分型
        now_fenxing = self.fenxingTuples[-1]
        
        ###判断分型是否更新
        ###未更新
        if self.last_fenxing_datetime2 == now_fenxing[0]:
            return
            
        ###更新了
        else:
            ###不管替代前分型还是新增分型,满足条件的话，变一次买一次
            now_duration = self.macd_duration[-1][-1]
            last_duration = self.macd_duration[-3][-1]
            macd_beichi = abs(now_duration) < abs(last_duration)
            
            #对于这个分型是否是第一卖点的判断
            if now_fenxing[-1] == DING:
                qianding = self.fenxingTuples[-3]
                new_high = now_fenxing[1] > qianding[1]#创出新高
                if macd_beichi and new_high:
                    self.ding_signal = True
                    
            #对于这个分型是否是第二买点的判断
            elif now_fenxing[-1] == DI:
                qiandi = self.fenxingTuples[-3]
                new_low = now_fenxing[1] < qiandi[1]#创出新低
                if macd_beichi and new_low:
                    self.di_signal = True
                        
                            
            self.last_fenxing_datetime2 = now_fenxing[0]     
    def process_sendmail(self):
        
        """======================发出交易信息给邮箱=================="""
        if not (self.di_signal | self.ding_signal):
            return
        now_fenxing = self.fenxingTuples[-1]
        qian_fenxing = self.fenxingTuples[-3]
        now_duration = self.macd_duration[-1]
        last_duration = self.macd_duration[-3]
        s1 = '\t'.join(["现在分型："+now_fenxing[0].strftime('%Y-%m-%d %H:%M:%S'),"价格："+str(now_fenxing[1])])
        s2 = '\t'.join(["上个分型："+qian_fenxing[0].strftime('%Y-%m-%d %H:%M:%S'),"价格："+str(qian_fenxing[1])])
        s3 = "macd力度："+str(now_duration[-1]*100)
        s4 = "上次macd力度：" + str(last_duration[-1]*100)
        s5 = "力度倍数："+str(now_duration[-1]/last_duration[-1])
        if self.di_signal:
         
            #if self.trading:
            self.mh.send_mail(['2478405586@qq.com'],"出现底——做多信号",'\n'.join([s1,s2,s3,s4,s5]))
            
        elif self.ding_signal:
            
            #if self.trading:#2478405586
            self.mh.send_mail(['2478405586@qq.com'],"出现顶——做空信号",'\n'.join([s1,s2,s3,s4,s5]))
    def process_ordertrigger(self):
        
        """======================发出交易Order=================="""
        
        if self.di_signal:
            
            if self.pos < 0:
                
                orderID = self.cover(self.newBar['close'] + 1, abs(self.pos), stop=True)#平仓所有空头
                self.orderList.append(orderID)
                self.volume = 1
                
            if self.volume > self.max_replace_counts:#最多买4+3+2+1手
                
                self.di_signal = False
                return
                
            self.buy(self.newBar['close']+1, self.real_volume)
            self.volume += 1
            
        elif self.ding_signal:
            
            if self.pos > 0:
                
                orderID = self.sell(self.newBar['close'] - 1, abs(self.pos), stop=True)#平仓所有多头
                self.orderList.append(orderID)
                self.volume = 1
            
            if self.volume > self.max_replace_counts:#最多做空4+3+2+1手
                
                self.ding_signal = False
                return
                
            self.short(self.newBar['close']-1, self.real_volume)
            self.volume += 1
            
        self.ding_signal = False
        self.di_signal = False
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        
        #price = self.closes[-1]
        #if self.volume == self.max_replace_counts+1:
        #    self.volume = 1
        #fenmu = sum(range(self.volume,self.max_replace_counts+1))
        #part = self.volume/float(fenmu)
        #self.real_volume = int(math.ceil(part*((self.account.available*self.risk_rate)/(price*self.vRate))))
        
        
        
        
        #开多
        if trade.direction == DIRECTION_LONG and trade.offset == OFFSET_OPEN:
            self.vAvailable -= trade.price * trade.volume * self.vRate
        #平多
        elif trade.direction == DIRECTION_SHORT and trade.offset == OFFSET_CLOSE:
            self.vAvailable += trade.price * trade.volume * self.vRate
        #开空
        elif trade.direction == DIRECTION_SHORT and trade.offset == OFFSET_OPEN:
            self.vAvailable += trade.price * trade.volume * self.vRate
        #平空
        elif trade.direction == DIRECTION_LONG and trade.offset == OFFSET_CLOSE:
            self.vAvailable -= trade.price * trade.volume * self.vRate
        
        #print self.vAvailable
        
        price = self.closes[-1]
        if self.volume == self.max_replace_counts+1:self.volume = 1
        fenmu = sum(range(self.volume,self.max_replace_counts+1))
        part = self.volume/float(fenmu)
        self.real_volume = math.ceil(part*((self.vAvailable*self.risk_rate)/(price*self.vRate)))
        
        #print trade.offset,trade.direction,trade.volume,trade.price
      


















