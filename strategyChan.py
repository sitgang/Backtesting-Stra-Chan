#coding=UTF-8
'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''


from ctaBacktesting import BacktestingEngine
from copy import deepcopy
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
pd.options.display.max_rows = 8
import numpy as np
import talib

from ctaTemplate import CtaTemplate
from ctaBase import *
from ctaSetting import *
from vtConstant import *
from Chan_Functions import *
# encoding: UTF-8
########################################################################
class ChanStrategy(CtaTemplate):
    """缠论策略"""
    
    # 策略类的名称和作者
    className = u'缠论'
    author = u"薛耕"
    
    # 策略的基本参数
    name = EMPTY_UNICODE           # 策略实例名称
    vtSymbol = EMPTY_STRING        # 交易的合约vt系统代码    
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）
    
    # 策略的基本变量，由引擎管理
    inited = False                 # 是否进行了初始化
    trading = False                # 是否启动交易，由引擎管理
    pos = 0                        # 持仓情况
    
    #全局变量
    #orderList = []                      # 保存委托代码的列表
    
    #包含bar的数列
    baohanbar_list =[]
    current_bar = CtaBaohanBarData()
    
    #分型相关
    fenxing_list = []
    
    #笔相关
    last_fenxing = CtaFenxingData()
    bi_list = []
    
    #包含笔
    baohanbi_list = []
    
    #线段相关
    xianduan_list = []
    
    #中枢相关
    last_xianduan = CtaXianduanData()
    last_zhongshu = CtaZhongshuData()
    zhongshu_list = []
    
    #MACD相关
    close_list = []
    macd_list = []
    macd_datetimelist = []
    
    #画图相关
    plot_engine = plot_engine()
    fig, ax = plt.subplots(figsize = (20,8))
        
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
        """Constructor"""
        self.ctaEngine = ctaEngine

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
    #----------------------------------------------------------------------
    def __str__(self):
        return name
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        
        #initData = self.loadBar(self.initDays)
        #for bar in initData:
        #    self.onBar(bar)

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
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onAccount(self, account):
        """收到成交推送（必须由用户继承实现）"""
        self.account = account  #VtAccountData
        self.writeCtaLog(u'%s成交推送' %self.name)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        """这个好，撤销之前的单"""
        #for orderID in self.orderList:
        #    self.cancelOrder(orderID)
        #self.orderList = []
        
        #需要用数据清洗来删除出格的值
        
        self.current_bar.__dict__.update(bar.__dict__)
        self.process_baohan()
        self.process_fenxing()
        self.process_bi()
        self.process_xianduan()
        self.process_zhongshu()
        self.process_macd()
        #self.process_first_point()
        #self.process_second_point()
        #self.process_third_point()
        
    
    #----------------------------------------------------------------------
    def buy(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume, stop)
    
    #----------------------------------------------------------------------
    def sell(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, stop)       

    #----------------------------------------------------------------------
    def short(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, stop)          
 
    #----------------------------------------------------------------------
    def cover(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(self.vtSymbol, orderType, price, volume, self) 
            return vtOrderID
        else:
            # 交易停止时发单返回空字符串
            return ''        
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return
        
        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)
    
    #----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType
    
    #----------------------------------------------------------------------
    def replotInit(self):
        
        self.fig, self.ax = plt.subplots(figsize = (20,8))
    #----------------------------------------------------------------------
    def plotCandlestick(self,df):
        
        self.plot_engine.draw_candlestick(df,self.ax)
    #----------------------------------------------------------------------
    def plotCandlestick2(self,df):
        
        self.plot_engine.draw_candlestick2(df,self.ax)
    #----------------------------------------------------------------------
    def plotFenxing(self):
        
        self.plot_engine.draw_fenxing(self.fenxing_list,self.ax)        
    #----------------------------------------------------------------------
    def plotFenxing2(self):
        
        self.plot_engine.draw_fenxing2(self.fenxing_list,self.ax,dd)
    #----------------------------------------------------------------------
    def plotBi(self):
        
        self.plot_engine.draw_bi(self.bi_list,self.ax)
    #----------------------------------------------------------------------
    def plotBi2(self,dd):
        
        self.plot_engine.draw_bi2(self.bi_list,self.ax,dd)
    #----------------------------------------------------------------------
    def plotXianduan(self):
        
        self.plot_engine.draw_xianduan(self.xianduan_list,self.ax)
    #----------------------------------------------------------------------
    def plotXianduan2(self,dd):
        
        self.plot_engine.draw_xianduan2(self.xianduan_list,self.ax,dd)
    #----------------------------------------------------------------------
    def plotZhongshu(self):
        
        self.plot_engine.draw_zhongshu(self.zhongshu_list,self.ax)
    #----------------------------------------------------------------------
    def plotZhongshu2(self,dd):
        
        self.plot_engine.draw_zhongshu2(self.zhongshu_list,self.ax,dd)
    
    #----------------------------------------------------------------------
    def process_baohan(self):
        """===========================包含函数=================================="""
        """
        存在包含条件的k线进行包含处理
        """
        #确定都进入了
        #如果当前bar是第一根
        if len(self.baohanbar_list) == 0:
            #构造包含bar
            cb = deepcopy(self.current_bar)
            cb.direction = DIRECTION_NONE
            self.baohanbar_list.append(cb)
            
        #如果当前bar不是第一根
        else:
            
            #如果当前bar和上一根有包含关系
            cb = deepcopy(self.current_bar)
            preb = self.baohanbar_list[-1]
            #newbar = CtaBaohanBarData()
            if ((cb.high >= preb.high) and (cb.low <= preb.low))\
                or ((cb.high <= preb.high) and (cb.low >= preb.low)):
                 
                #处理包含关系
                #newbar.__dict__.update(cb.__dict__)
                if preb.direction == DIRECTION_LONG:
                    cb.high = max(cb.high , preb.high)
                    cb.low = max(cb.low , preb.low)
                    
                elif preb.direction == DIRECTION_SHORT:
                    cb.high = min(cb.high , preb.high)
                    cb.low = min(cb.low , preb.low)
                else:
                    pass
                #开盘价和方向继承上一bar
                cb.open = preb.open
                cb.direction = preb.direction

                #替换最后的bar进入包含bar的队列
                #print "tihuan\n"
                self.baohanbar_list[-1] = cb
                
            #如果当前bar和上一根没有包含关系
            else:
                #判断方向
                #如果是向上的
                if cb.high > preb.high:
                    cb.direction = DIRECTION_LONG
                    #print "bubaohan long\n"
                #如果是向下的
                else:
                    cb.direction = DIRECTION_SHORT
                    #print "bubaohan short\n"
                #添加进入包含bar的队列
                #print "tianjia\n"
                self.baohanbar_list.append(cb)
        
    #----------------------------------------------------------------------
    def process_fenxing(self):
        """===========================分型函数=============================="""
        """
        用经过包含的bar来确定分型
        """
        FENXING_LIMIT = 4
        #如果分型list里面还没有分型存在
        if len(self.fenxing_list) == 0:
            #如果包含barlist大于等于三
            if len(self.baohanbar_list) >= 3:
                #那么遍历包含barlist，找到分型，加入分型list
                baohanbar_count = len(self.baohanbar_list)
                for i in range(2,baohanbar_count):
                    pre_bar = self.baohanbar_list[i-1]
                    now_bar = self.baohanbar_list[i]
                    pre_direction = pre_bar.direction
                    now_direction = now_bar.direction
                    #如果bar的方向出现变化（还要确定不是相对与无变化的变化），那么就出现了分型
                    if pre_direction != now_direction and pre_direction != DIRECTION_NONE:
                        now_fenxing = CtaFenxingData()
                        now_fenxing = update_object(now_fenxing, pre_bar)
                        #now_fenxing.__dict__.update(pre_bar.__dict__)
                        now_fenxing.bar_index = self.baohanbar_list.index(pre_bar)
                        if pre_direction == DIRECTION_LONG:
                            now_fenxing.ftype = FENXING_DING
                            now_fenxing.price = pre_bar.high
                        else:
                            now_fenxing.ftype = FENXING_DI
                            now_fenxing.price = pre_bar.low
                        self.fenxing_list.append(now_fenxing)
                    
                        
            #如果包含barlist小于三
            else:
                #过掉
                pass
                
        #如果已经有分型存在
        else:
            #从index开始遍历bar，寻找转折方向
            pre_direction = DIRECTION_NONE
            now_direction = DIRECTION_NONE
            baohanbar_count = len(self.baohanbar_list)
            last_fenxing = self.fenxing_list[-1]#取出用来定位的分型
            findex = last_fenxing.bar_index#上一分型在barlist里的位置
            for i in range(findex+2,baohanbar_count):
                pre_bar = self.baohanbar_list[i-1]
                now_bar = self.baohanbar_list[i]
                pre_direction = pre_bar.direction
                now_direction = now_bar.direction
                #如果bar的方向出现变化（还要确定不是相对于无变化的变化），那么就出现了分型
                if pre_direction != now_direction and pre_direction != DIRECTION_NONE:
                    now_fenxing = CtaFenxingData()
                    now_fenxing = update_object(now_fenxing, pre_bar)
                    #now_fenxing.__dict__.update(pre_bar.__dict__)
                    #如果找到了转折（分型），那么得到现在的遍历当下的bar的index
                    now_fenxing.bar_index = self.baohanbar_list.index(pre_bar)
                    interval = now_fenxing.bar_index - last_fenxing.bar_index
                    #比较index，如果大于等于FENXING_LIMIT
                    if interval >= FENXING_LIMIT:
                        #检查方向
                        #如果方向相同
                        if (pre_bar.direction == DIRECTION_LONG and last_fenxing.ftype == FENXING_DING)\
                            or (pre_bar.direction == DIRECTION_SHORT and last_fenxing.ftype == FENXING_DI):
                            #新分型方向为同向
                            now_fenxing.ftype = last_fenxing.ftype
                            if pre_bar.direction == DIRECTION_LONG:
                                #如果创新低和新高才替代
                                if pre_bar.high < last_fenxing.price:
                                    pass
                                else:
                                    now_fenxing.price = pre_bar.high
                                    #替换最后一个分型
                                    self.fenxing_list[-1] = now_fenxing
                                
                            else:
                                #如果创新低和新高才替代
                                if pre_bar.low > last_fenxing.price:
                                    pass
                                else:
                                    now_fenxing.price = pre_bar.low
                                    #替换最后一个分型
                                    self.fenxing_list[-1] = now_fenxing
                        #如果方向不同
                        else:
                            #构造新分型
                            if last_fenxing.ftype == FENXING_DING:
                                now_fenxing.ftype = FENXING_DI
                                now_fenxing.price = pre_bar.low
                            else:
                                now_fenxing.ftype = FENXING_DING
                                now_fenxing.price = pre_bar.high
                            #添加进入分型list
                            self.fenxing_list.append(now_fenxing)
                            
                    #如果小于FENXING_LIMIT
                    else:
                        #修改上个分型到现在这个假分型中间所有bar的方向
                        to_change_direction = self.baohanbar_list[findex].direction
                        for j in range(findex+1,i):
                            to_change_bar = self.baohanbar_list[j]
                            to_change_bar.direction = to_change_direction
                            self.baohanbar_list[j] = to_change_bar
        
    #----------------------------------------------------------------------
    def process_bi(self):
        """===========================笔函数=============================="""
        """
        用分型来确定笔
        """
        #如果fenxing_list里的分型小于2
        if len(self.fenxing_list) < 2:
            #跳过
            pass
        #如果fenxing_list里的分型大于等于2
        else:
            #检查是否出现了新的分型，检查last_findex和fenxing_list的最后一个的findex是否还一样
            is_new_fenxing = self.last_fenxing.bar_index != self.fenxing_list[-1].bar_index
            #如果没有
            if not is_new_fenxing:
                #不处理
                pass
            #如果有新分型
            else:                
                #构造出笔对象
                new_bi = CtaBiData()
                new_bi = update_object(new_bi, self.last_fenxing)
                #new_bi.__dict__.update(self.last_fenxing.__dict__)
                start_fenxing = self.fenxing_list[-2]
                end_fenxing = self.fenxing_list[-1]
                if end_fenxing.ftype == FENXING_DING:
                    new_bi.btype = BI_UP
                    new_bi.start_price = start_fenxing.price        
                    new_bi.end_price = end_fenxing.price      
                                     
                else:
                    new_bi.btype = BI_DOWN
                    new_bi.start_price = start_fenxing.price        
                    new_bi.end_price = end_fenxing.price  
                                 
                new_bi.start_fenxing_index =  self.fenxing_list.index(start_fenxing)     
                new_bi.end_fenxing_index =  self.fenxing_list.index(end_fenxing)
                new_bi.start_datetime = start_fenxing.datetime  
                new_bi.end_datetime =end_fenxing.datetime 
        
                #检查是分型的延长还是新添加的分型
                is_prolong_fenxing = self.last_fenxing.ftype == end_fenxing.ftype
                if is_prolong_fenxing:
                    new_bi.bi_index = len(self.bi_list )-1
                    self.bi_list[-1] =  new_bi
                else:
                    
                    new_bi.bi_index = len(self.bi_list)
                    self.bi_list.append(new_bi)
                #修改last_fenxing作为下次判断分型的依据
                self.last_fenxing = deepcopy(self.fenxing_list[-1])
    
    
  
        
    #----------------------------------------------------------------------
    def process_xianduan(self):
        """===========================线段函数=============================="""
        """
        用笔来确定线段
        """
        
        #至少有六笔才开始考虑线段
        #如果bi_list还不及六笔
        if len(self.bi_list) < 6:
            #并不进行操作
            pass
        #如果已经大于等于六笔
        else:
            #如果xianduan_list已经有了线段
            if len(self.xianduan_list) > 0:
                #看现在的bi_list长度减一减去上一线段的findex是不是大于等于6
                #如果不大于等于
                last_xianduan = self.xianduan_list[-1]
                if len(self.bi_list) - 1 - last_xianduan.end_bi_index < 6:
                    #不操作
                    pass
                #如果大于等于
                else:
                    #在上一线段的bindex之后遍历，处理包含（用一个函数处理），找到分型（用一个函数找）
                    to_examine_bis0 = deepcopy(self.bi_list[last_xianduan.end_bi_index +1:])#这里面都是CtaBiData
                    #包含必须在当下处理
                    after_tezhengbi = process_bi_baohan(to_examine_bis0)#这里面都是CtaBaohanbiData
                    
                    if len(after_tezhengbi) >= 3:
                        
                        end_bi = find_end_node_bi(after_tezhengbi)
                        if not end_bi == None:
                            start_bi = to_examine_bis0[0]
                            
                            new_xianduan = generate_new_xianduan(start_bi,end_bi)
                            new_xianduan.start_bi_index =  start_bi.bi_index
                            #因为即使特征向量有包含，它也包含不了那结束的一笔，因为特征笔是相反的
                            new_xianduan.end_bi_index = end_bi.extreme_bi_index -1 
                            self.xianduan_list.append(new_xianduan)
                            
                        else:
                            pass
                    else:
                        pass
                    
            #如果还没有线段
            else:
                #遍历，处理包含（用一个函数处理），找到分型（用一个函数找）
                to_examine_bis0 = deepcopy(self.bi_list)
                after_tezhengbi = process_bi_baohan(to_examine_bis0)
                if len(after_tezhengbi) >= 3:
                    
                    end_bi = find_end_node_bi(after_tezhengbi)
                    if not end_bi == None:
                        start_bi = to_examine_bis0[0]  
                        
                        new_xianduan = generate_new_xianduan(start_bi,end_bi)
                        new_xianduan.start_bi_index =  0    
                        #因为即使特征向量有包含，它也包含不了那结束的一笔，因为特征笔是相反的
                        new_xianduan.end_bi_index = end_bi.extreme_bi_index -1 
                        self.xianduan_list.append(new_xianduan)
                            
                    else:
                        pass
                else:
                    pass
        
    #----------------------------------------------------------------------
    def process_zhongshu(self):
        """===========================中枢函数=============================="""
        """
        用线段来确定中枢
        """
        
        #只要有三个线段就可以形成一个中枢
        #中枢是取线段的交集
        #如果线段回不到中枢，那说明中枢已经结束
        #中枢对象中需要包含他所包含的线段，以方便中枢的扩大
        #当中枢里的线段多余等于9时，分割为三个中枢并扩大
        #当两个中枢有交集时，扩大中枢
        
        
        
        #是否有线段
        is_xianduan_list_empty = len(self.xianduan_list) == 0
        #是否有中枢
        is_zhongshu_list_empty = len(self.zhongshu_list) == 0
        #线段相比于上次执行此函数是否是新的
        if is_xianduan_list_empty:
            is_xianduan_new  = False
        else:
            is_xianduan_new = self.last_xianduan.end_bi_index != \
                                self.xianduan_list[-1].end_bi_index
            
        #中枢是否是新的
        is_zhongshu_new = False
        
        
        
        
        #根据新线段改上一中枢
        #基本条件：有中枢，有新线段，新线段在上个中枢内，新线段接着中枢的endnode
        if (not is_zhongshu_list_empty) and is_xianduan_new:
            #必须是紧接着的线段才能更新上一个中枢
            is_xianduan_adjunct = len(self.xianduan_list) -2 == \
                                self.zhongshu_list[-1].end_xianduan_index
            #print "is_xianduan_adjunct : " + str(is_xianduan_adjunct)
            #print "len(self.xianduan_list) -2 : " + str(len(self.xianduan_list) -2)
            #print "self.zhongshu_list[-1].end_xianduan_index : " + str(self.zhongshu_list[-1].end_xianduan_index)
            if is_xianduan_adjunct:
                new_xianduan = self.xianduan_list[-1]
                last_zhongshu = self.zhongshu_list[-1]
                if is_xd_in_zs(new_xianduan,last_zhongshu):
                    #修改上一中枢
                    changed_zhongshu = update_zhongshu(last_zhongshu,new_xianduan)
                    changed_zhongshu.end_xianduan_index = len(self.xianduan_list) - 1
                    #替换最后一个中枢
                    self.zhongshu_list[-1] = deepcopy(changed_zhongshu)
                    #修改中枢是否是新的
                    is_zhongshu_new = True
        
        
        
        #根据新线段形成新中枢 # 要么新建中枢，要么扩大中枢，不存在又改又建
        #基本条件：分类来看
        #如果已经有中枢了
        if not is_zhongshu_list_empty:
            new_xianduan = self.xianduan_list[-1]
            last_zhongshu = self.zhongshu_list[-1]
            #基本条件：从上个中枢的end_xd_index来切分xd_list能剩余至少三个线段
            cut_index = last_zhongshu.end_xianduan_index
            cut_list = self.xianduan_list[cut_index:]
            if len(cut_list) >= 3:
                #寻找交集,返回端点线段的在cut_list中的index，但可能没有
                nis = return_node_index_if_intersect(cut_list)
                #有的话，返回开始和结束的xd_index
                if nis:
                    nis = map(lambda x:x+cut_index,nis)
                    #根据线段生成中枢
                    xd_list = deepcopy(self.xianduan_list[nis[0]:nis[1]+1])
                    new_zhongshu = create_zhongshu_with_xds(xd_list)
                    new_zhongshu.start_xianduan_index =  nis[0]
                    new_zhongshu.end_xianduan_index =  nis[1]
                    #添加入中枢list
                    self.zhongshu_list.append(deepcopy(new_zhongshu))
                    #修改中枢是否是新的
                    is_zhongshu_new = True
                    
        #如果还没有中枢
        else:
            #基本条件：self.xd_list至少有三个线段
            if len(self.xianduan_list) >= 3:
                #寻找交集，但可能没有
                xd_list = deepcopy(self.xianduan_list)
                nis = return_node_index_if_intersect(xd_list)
                #有的话，返回开始和结束的xd_index
                if nis:
                    #nis = map(lambda x:x+cut_index-1,nis)
                    #根据线段生成中枢
                    xd_list = deepcopy(self.xianduan_list[nis[0]:nis[1]+1])
                    new_zhongshu = create_zhongshu_with_xds(xd_list)
                    
                    new_zhongshu.start_xianduan_index =  nis[0]
                    new_zhongshu.end_xianduan_index =  nis[1]
                    #添加入中枢list
                    self.zhongshu_list.append(deepcopy(new_zhongshu))
                    #修改中枢是否是新的
                    is_zhongshu_new = True
                    
        
        """这个的测试先要找可以有合并的区间，弄个大的时间区间，用程序找"""
        
        
        ## 新老中枢合并 # 我不确定它是否必要 # 可能是必要的，最后看哪个效果好
        ## 基本条件：最后一个中枢更新了，至少有两个中枢
        #len_zhongshu_gte2 = len(self.zhongshu_list) >= 2
        #if is_zhongnshu_new and len_zhongshu_gte2:
        #    last_zs, pre_last_zs = self.zhongshu_list[-1], self.zhongshu_list[-2]              
        #    z0_low, z0_high = last_zs.low_price,last_zs.high_price
        #    z1_low, z1_high = pre_last_zs.low_price,pre_last_zs.high_price
        #    if is_overlap([z0_low, z0_high], [z1_low, z1_high]):
        #        zs_merged = merge_zs(last_zs, pre_last_zs)
        #        #用新的替换这两个胶合的中枢
        #        self.zhongshu_list[-2:] = [zs_merged]
        #   
        #/用于测试中枢合并
        #for zs in zs_list:
        #lh = map(lambda x:(min(x.start_price,x.end_price),max(x.start_price,x.end_price)),zs.xd_list)
        #zs.min = min(map(lambda x:x[0],lh))
        #zs.max = max(map(lambda x:x[1],lh))
        
        #九线段扩大
        #基本条件：最后一个中枢更新了，至少有一个中枢
        len_zhongshu_gte1 = len(self.zhongshu_list) >= 1
        if is_zhongshu_new and len_zhongshu_gte1:
            now_zhongshu = self.zhongshu_list[-1]
            if now_zhongshu.count == 9:
                xds = deepcopy(now_zhongshu.xd_list)
                zs0 = create_zhongshu(xds[0],xds[1],xds[2])
                zs1 = create_zhongshu(xds[3],xds[4],xds[5])
                zs2 = create_zhongshu(xds[6],xds[7],xds[8])
                zs_merged0 = merge_zs(zs0,zs1)
                zs_merged1 = merge_zs(zs_merged0,zs2)
                self.zhongshu_list[-1] = zs_merged1
        
        
        
        
        if not is_xianduan_list_empty:
            self.last_xianduan = deepcopy(self.xianduan_list[-1])
        
        is_zhongshu_new  = False
        
    #----------------------------------------------------------------------
    #---判断买卖点不可以修改买卖点，因为线段是不可以修改的，某个特定时间的线段是固定的--
    #笔可以更新，但是线段不可以，而我们不判断笔背驰，所以买卖点都不可以更改，避免未来函数
    #----------------------------------------------------------------------
    def process_macd(self):
        """===========================MACD函数=============================="""
        self.close_list.append(bar.close)
        if len(self.close_list) >= 34:
            #它们两个同时添加，这样就可以用index来查找日期对应的指标切段
            self.macd_list.append(talib.MACD(np.array(self.close_list[:34]))[2][-1])
            self.macd_datetime_list.append(str(bar.datetime))
            
    #----------------------------------------------------------------------
    def process_first_point(self):
        """===========================第一点函数=============================="""
        """
        用构筑好的结构来判断第一点
        笔背驰就不判断了，太随机了
        """
        #不用执行这个函数的情况
        #线段不到三个
        is_xd_list_three = len(self.xianduan_list) >= 3
        if not is_xd_list_three: return 
        #线段不是新的
        is_xianduan_new = self.last_xianduan_p1.end_bi_index !=\
                            self.xianduan_list[-1].end_bi_index
        if not is_xianduan_new: return
        #如果是新的，更新self.last_xianduan_p1
        if is_xianduan_new: self.last_xianduan_p1 =\
                            deepcopy(self.xianduan_list[-1])
        
        #拷贝新线段，以备后用
        current_xianduan =deepcopy(self.last_xianduan_list[-1])
                            
       
        #线段背驰
        #当一个新的线段形成的时候
        #判断相比于上上一个线段，是否创了新低或新高
        ppx = deepcopy(self.xianduan_list[-3])
        cx = deepcopy(self.xianduan_list[-1])
        #start-end price # 是否同向
        ppsep = (ppx.start_price,ppx.end_price)
        csep = (cx.start_price,cx.end_price)
        is_tongxiang = is_tonghao(ppsep[0]-ppsep[1],csep[0]-csep[1])
        
        if is_tongxiang:
            if ppsep[0] < ppsep[1]:
                direction  = XIANDUAN_UP
                is_new_hl = ppsep[1] < csep[1]
            elif ppsep[0] > ppsep[1]:
                direction  = XIANDUAN_DOWN
                is_new_hl = ppsep[1] > csep[1]
            else:
                direction  = DIRECTION_NONE
                is_new_hl = False
        else:
            direction  = DIRECTION_NONE
            is_new_hl = False
        
        #判断两个时间段内的均线面积（MACD面积（需要34 个数据））是否没有创新低或新高
        if direction == DIRECTION_NONE or is_new_hl:
            pass
        else:
            start_datetime_pp, end_datetime_pp = str(ppx.start_datetime), str(ppx.end_datetime)
            start_datetime_c, end_datetime_c = str(cx.start_datetime), str(cx.end_datetime)
            #这里我们用MACD的加和来作为背驰的依据
            start_pp_index, end_pp_index, start_c_index, end_c_index = \
                            map(self.macd_datetime_list.index,\
                            [start_datetime_pp, end_datetime_pp,start_datetime_c, end_datetime_c])
            macd_pp = sum(self.macd_list[start_pp_index:end_pp_index + 1])
            macd_c = sum(self.macd_list[start_c_index:end_c_index + 1])
            
            is_same_direction = is_tonghao(macd_pp, macd_c)
            is_weaker = abs(macd_c) < abs(macd_pp)
            if is_same_direction and is_weaker:
                is_xianduan_beichi = True
            else:
                is_xianduan_beichi = False
            if is_xianduan_beichi:
                #根据方向，构造、添加第一买卖点
        
    
    
        #趋势背驰
        #不用执行趋势笔背驰的情况
        #中枢不到三个
        is_zs_list_three = len(self.zhongshu_list) >= 3
        if not is_zs_list_three: return 
        #拷贝新中枢，以备后用
        current_zhongshu =deepcopy(self.zhongshu_list[-1])
        #判断中枢是否是新的（中枢的线段只有三个，且形成它的最后一个线段就是current_xianduan）
        end_with_current_xianduan = current_xianduan.end_bi_index == current_zhongshu.xd_list[-1].end_bi_index
        is_new_born = len(current_zhongshu.xd_list) == 3
        if not(end_with_current_xianduan and is_new_born): return
        
        #判断最后三个中枢
        ppz = deepcopy(self.zhongshu_list[-3])
        pz = deepcopy(self.zhongshu_list[-2])
        cz = deepcopy(self.zhongshu_list[-1])
        #依次下降或上升
        lhs = map(return_zhongshu_lowhigh,[ppz,pz,cz])
        is_zhognshu_descending = is_lowhigh_descending(lhs)
        is_zhognshu_ascending = is_lowhigh_ascending(lhs)
        if not(is_zhognshu_descending or is_zhognshu_ascending): return
        #然后比较这两个中枢的时间段内的均线的面积（或者MACD的面积/或面积除以时间）
        #获取切割的时间
        start_datetime_pp, end_datetime_pp = str(ppz.end_plot_datetime), str(pz.start_plot_datetime)
        start_datetime_p, end_datetime_p = str(pz.end_plot_datetime), str(cz.start_plot_datetime)
        #这里我们用MACD的加和来作为背驰的依据
        start_pp_index, end_pp_index, start_p_index, end_p_index = \
                        map(self.macd_datetime_list.index,\
                        [start_datetime_pp, end_datetime_pp,start_datetime_p, end_datetime_p])
        macd_pp = sum(self.macd_list[start_pp_index:end_pp_index + 1])
        macd_p = sum(self.macd_list[start_p_index:end_p_index + 1])
        
        is_same_direction = is_tonghao(macd_pp, macd_p)
        is_weaker = abs(macd_p) < abs(macd_pp)
        if is_same_direction and is_weaker:
            is_trend_beichi = True
        else:
            is_trend_beichi = False
        #添加第一点
        
                
    #----------------------------------------------------------------------
    def process_second_point(self):
        """===========================第二点函数=============================="""
        """
        用第一点诞生的那根线段的后面第二根线段来判断第二点
        第二点不考虑第一点是趋势背驰还是线段背驰，
        """
        #我们不用考虑第一点是根据什么背驰规则形成的
        #我们也不用笔形成第一点，所以不用笔形成第二点
        
        #判断第二点
        #如果刚刚形成了新的线段，那我们检查上一个同向的第一点是不是以新线段的上上线段为依据的
        #如果是，那么看这个线段是否突破上上线段的最值点
        #如果都是，判断为第二点
        
    #----------------------------------------------------------------------
    def process_third_point(self):
        """===========================第三点函数=============================="""
        """
        用离开中枢的线段来判断第三点
        """
        #线段不可修改的定义直接使得未来函数不可能
        #当出现一个新的线段的时候，开始判断
        #如果他的上一个线段在中枢里面，而本线段不在中枢里面
        #如果它和它上一个线段不是同向
        #那么标记为第三点
        
        
        
        
        
        
        
        
                                        
                                                
                                                                
#从对象里取出来的东西，除非你要修改对象，不然千万不要动它的属性，要动就要copy

        
        
        
        
        
        
        
        
