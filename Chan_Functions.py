# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys   
reload(sys) # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入   
sys.setdefaultencoding('utf-8')

import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime,timedelta
import matplotlib
import numpy as np
import pylab as pl
from matplotlib import collections  as mc
import matplotlib.dates as mdates
from vtConstant import *
from ctaBase import *
from copy import deepcopy
import time


def to_transed_eve(df):
    #df2 = pd.read_csv('/Users/xuegeng/Desktop/jh.csv')#实验用
    """
    因为bar数据存储的时候会把今天晚上的bar存成明天的日期，
    所以这个函数可以把df的晚上的bar的日期改成前一天的
     ====================
    Input:
        close              float64
        date                 int64
        datetime    datetime64[ns]
        exchange            object
        high               float64
        low                float64
        open               float64
        symbol              object
        time                object
        volume               int64
        vtSymbol            object
    """
    def trans_eve(former):
        
        if former.hour > 19:
            later = former - timedelta(days=1)
        else: 
            later = former
        
        return later
    
    datetime_sr = df.datetime.copy()
    datetime_sr = datetime_sr.apply(pd.to_datetime)
    datetime_sr = datetime_sr.apply(trans_eve)
    df.datetime = datetime_sr
    
    return df

def update_object(obj1, obj2):
    """只更新obj1中有的属性"""      
    d1 = obj1.__dict__
    d2 = obj2.__dict__    
    for k in d1.iterkeys():
        try:
           d1[k] = d2[k]
        except KeyError:
           pass
    obj1.__dict__ = d1
    return obj1

def bi_to_baohanbi(bi):
    """将一笔转化为包含笔"""
    bhb = CtaBaohanbiData()
    bhb = update_object(bhb , bi)
    if bhb.btype == BI_UP:
        bhb.high_price = bi.end_price
        bhb.low_price = bi.start_price
    else:
        bhb.high_price = bi.start_price
        bhb.low_price = bi.end_price
    bhb.extreme_bi_index = bi.bi_index
    return bhb
    
def process_bi_baohan(to_examine_bis):
    """将这些笔的包含关系处理好"""
    tezhengbi = []#未包含的特征笔
    after_tezhengbi = []#包含的特征笔
    for i in range(1,len(to_examine_bis),2):#取出特征笔
        bhb = bi_to_baohanbi(to_examine_bis[i])
        tezhengbi.append(bhb)
    
    
    for i in range(1,len(tezhengbi)):
        pb = deepcopy(tezhengbi[i-1])
        cb = deepcopy(tezhengbi[i])
        
        
        #检查是否包含
        if ((pb.high_price >= cb.high_price) and (pb.low_price <= cb.low_price))\
                or ((pb.high_price <= cb.high_price) and (pb.low_price >= cb.low_price)):
                    #构造现笔
            #前一个包含后一个
            if pb.high_price >= cb.high_price:
                pb.extreme_bi_index = pb.bi_index
            else:
                pb.extreme_bi_index = cb.bi_index
                
            if to_examine_bis[0].btype == BI_UP:
                pb.high_price = max(cb.high_price , pb.high_price)
                pb.low_price = max(cb.low_price , pb.low_price)
            else:
                pb.high_price = min(cb.high_price , pb.high_price)
                pb.low_price = min(cb.low_price , pb.low_price)
                
            pb.end_fenxing_index =  cb.end_fenxing_index     
            pb.end_datetime = cb.end_datetime
            #替换包含的几笔               
            after_tezhengbi.append(deepcopy(pb))
        
        else:
            if len(after_tezhengbi) == 0:
                after_tezhengbi.append(deepcopy(pb))
                after_tezhengbi.append(deepcopy(cb))
            else:
                after_tezhengbi.append(deepcopy(cb))
            
    return after_tezhengbi #接下来要干分型

   
def find_end_node_bi(after_tezhengbi):
    """找到构成线段的两端的笔"""
    #after_tezhengbi必须大等于于三
    if not len(after_tezhengbi) >= 3 :
        return None
        
    for i in range(2,len(after_tezhengbi)):#取出特征笔
        ppb = after_tezhengbi[i-2]
        pb = after_tezhengbi[i-1]
        cb = after_tezhengbi[i]
        if ppb.btype == BI_UP:#特征向量是向上的，那线段就是向下的,那就是底分型
            if ppb.high_price > pb.high_price and pb.high_price < cb.high_price:#出现底分型
                return deepcopy(pb)#返回终止笔
        elif ppb.btype == BI_DOWN:
            if ppb.high_price < pb.high_price and pb.high_price > cb.high_price:#出现顶分型
                return deepcopy(pb)#返回终止笔
    
    return None
    

    
def generate_new_xianduan(start_bi,end_bi):
    """这里进入的两个笔是“笔”对象和“包含笔”对象"""
    """生成新的线段"""
    new_xianduan0 = CtaXianduanData()
    new_xianduan  = update_object(new_xianduan0,start_bi)
    if start_bi.btype == BI_UP:
        new_xianduan.xtype = XIANDUAN_UP            #线段类型
        new_xianduan.end_price = end_bi.high_price                      #线段形成的端点
    else:
        new_xianduan.xtype = XIANDUAN_DOWN
        new_xianduan.end_price = end_bi.low_price                      #线段形成的端点
          
    new_xianduan.end_datetime = end_bi.start_datetime   #线段的结束时间是顶分型特征笔的开始时间
    
    return new_xianduan

#==============================中枢函数====================================
def is_overlap(range1, range2):
    """求得线段是否在中枢内"""
    #如果和等于区间的边界，那么算不在中枢内
    overlap = max(0, min(range1[1], range2[1]) - max(range1[0], range2[0]))
    if overlap > 0:
        return True
    else:
        return False      

def return_xianduan_lowhigh(xd):
    """根据线段对象返回高低值"""
    return min(xd.start_price,xd.end_price),max(xd.start_price,xd.end_price)
    
def return_zhongshu_lowhigh(zs):
    """根据中枢对象返回高低值"""
    return zs.low_price,zs.high_price
    
         
def return_interval(range1,range2):
    """
    输入两个list表示区间，得到交集的边界值
    return_interval([3,22],[20,80])
    """
    
    import interval
    x=interval.interval[range1[0], range1[1]]
    z=interval.interval[range2[0], range2[1]]
    a  = x & z
    return a[0]

def is_xd_in_zs(xd, zs):
    """线段是否在中枢内"""
    xd_low,xd_high = return_xianduan_lowhigh(xd)
    zs_low,zs_high = return_zhongshu_lowhigh(zs)
    return is_overlap([xd_low,xd_high],[zs_low,zs_high])

def update_zhongshu(last_zhongshu,new_xianduan):
    """根据最新线段的一些值修改它所在中枢的一些值"""
    x_low, x_high = return_xianduan_lowhigh(new_xianduan)
    z_low, z_high = last_zhongshu.low_price,last_zhongshu.high_price
    lowp, highp = return_interval([x_low, x_high], [z_low, z_high])

    last_zhongshu.high_price = highp
    last_zhongshu.low_price = lowp              
    
    last_zhongshu.end_plot_datetime = last_zhongshu.end_datetime
    last_zhongshu.end_datetime = new_xianduan.end_datetime              
        
    last_zhongshu.xd_list.append(deepcopy(new_xianduan))
    last_zhongshu.count += 1
    
    return last_zhongshu 
    
    
def return_node_index_if_intersect(cut_list):
    """
    输入是一堆线段，输出有交集的线段的两个端点线段在这个list里的index
    如果没有则去掉最先的一个再算，如果没有交集则返回空list
    """
    #print "cut_list: " + str(len(cut_list))
    lowhigh_list = map(lambda x:return_xianduan_lowhigh(x),cut_list)
    for i in range(len(cut_list)):
        lh_sub = lowhigh_list[i:]
        if len(lh_sub) >= 3:
            end_node_index = return_end_node_index_if_intersect(lh_sub)
            if end_node_index >= 2:
                return [i, end_node_index + i]
    return  [] #没有找到端点则返回空list
    
def return_end_node_index_if_intersect(lowhigh_list):
    """
    输入是一堆lowhigh price，返回结束线段在这个list中的index
    """
    #print "lowhigh_list: " + str(lowhigh_list)
    c = lowhigh_list[0]
    b = lowhigh_list[1]
    for i in lowhigh_list[1:]:
        if is_overlap(c,i):
            b = i
            c = return_interval(c,i)
        else:
            break
    return lowhigh_list.index(b)#结束线段的index
    

def create_zhongshu(xd0,xd1,xd2):
    """这里用三根线段来创造一个中枢"""
    zs = CtaZhongshuData()
    zs = update_object(zs,xd0)
    
    x_low, x_high = return_xianduan_lowhigh(xd0)
    x1_low, x1_high = return_xianduan_lowhigh(xd1)
    lowp, highp = return_interval([x_low, x_high], [x1_low, x1_high])
    x2_low, x2_high = return_xianduan_lowhigh(xd2)
    lowp, highp = return_interval([lowp, highp], [x2_low, x2_high])
    zs.high_price = highp
    zs.low_price = lowp       
    
    zs.start_datetime = xd0.start_datetime               
    zs.end_datetime = xd2.end_datetime                 
        
    zs.start_plot_datetime = xd1.start_datetime              
    zs.end_plot_datetime = xd1.end_datetime     
        
    zs.xd_list = [xd0,xd1,xd2]                    
    zs.count = 3
    
    return deepcopy(zs)           

def merge_zs(zs0,zs1):
    """
    用于取两个中枢range的交集作为新中枢的范围
    范围一个新的中枢
    """
    new_zs = CtaZhongshuData()
    new_zs = update_object(new_zs, zs0)
    
    z0_low = min(map(lambda x:min(x.start_price,x.end_price), zs0.xd_list))
    z0_high = max(map(lambda x:max(x.start_price,x.end_price), zs0.xd_list))
    
    
    z1_low = min(map(lambda x:min(x.start_price,x.end_price), zs1.xd_list))
    z1_high = max(map(lambda x:max(x.start_price,x.end_price), zs1.xd_list))
    
    new_zs.high_price,new_zs.low_price = return_interval([z0_low, z0_high], [z1_low, z1_high])
   
    new_zs.end_xianduan_index =  zs1.end_xianduan_index
    new_zs.end_datetime = zs1.end_datetime
        
    new_zs.end_plot_datetime = zs1.end_plot_datetime
    new_zs.xd_list += zs1.xd_list[1:]#因为他们共享一条线段                  
    new_zs.count = 3
    
    return new_zs
    
def create_zhongshu_with_xds(xd_list):
    """用多根线段创建中枢，其中最后一根和最先一根是开始线段和终止线段"""
    xd0, xd1, xd2 = xd_list[0],xd_list[1],xd_list[2]
    zs = create_zhongshu(xd0,xd1,xd2)
    if len(xd_list) > 3:
        for i in range(3,len(xd_list)):
            zs = update_zhongshu(zs,xd_list[i])
    return zs


def is_lowhigh_descending(lhs):
    """用于判断一组高低价是否连续下降"""
    plh = lhs[0]
    for i in range(1,len(lhs)):
        clh = lhs[i]
        if clh[0] < plh[0] and clh[1] < plh[1]:
            plh = lhs[i]
        else:
            return False
    
    return True

def is_lowhigh_ascending(lhs):
    """用于判断一组高低价是否连续上升"""
    plh = lhs[0]
    for i in range(1,len(lhs)):
        clh = lhs[i]
        if clh[0] > plh[0] and clh[1] > plh[1]:
            plh = lhs[i]
        else:
            return False
    
    return True

def is_tonghao(num1, num2):
    """用于判断两个数是否同号"""
    is_both_positive = num1 > 0 and num2 > 0
    is_both_negative = num1 < 0 and num2 < 0
    return is_both_positive or is_both_negative
    
def is_tongxiang(tuple1,tuple2):
    """判断两个开始结束值，以判断两个线段的方式是否同向"""
    return is_tonghao(tuple1[0]-tuple1[1],tuple2[0]-tuple2[1])
#==============================绘图函数====================================


#fig, ax = plt.subplots(figsize = (20,8))


class plot_engine():
    
    @staticmethod
    def draw_candlestick(df,ax):
        """
        这个函数是用于华蜡烛图的
        ====================
        Input:
            close              float64
            date                 int64
            datetime    datetime64[ns]
            exchange            object
            high               float64
            low                float64
            open               float64
            symbol              object
            time                object
            volume               int64
            vtSymbol            object
        """
        
        quotes=df[['datetime','open','high','low','close']].values
        tuples = [tuple(x) for x in quotes]
        qw=[]
            
        for things in tuples:
            date=matplotlib.dates.date2num(things[0])
            tuple1=(date,things[1],things[2],things[3],things[4])
            qw.append(tuple1)
        ax.xaxis_date()
        ax.grid(linestyle='-', linewidth=0.1)
        matplotlib.finance.candlestick_ohlc(ax, qw, colorup='r',colordown='g', alpha =.4, width=0.0005)
        plt.show()
    
    
    
    
    @staticmethod
    def draw_fenxing(fenxing_list,ax):

        difenxingTimes = []
        difenxingPrices = []
        dingfenxingTimes = []
        dingfenxingPrices = []
        for fenxing in fenxing_list:
            if fenxing.ftype == u'DI':
                difenxingTimes.append(fenxing.datetime)
                difenxingPrices.append(fenxing.price)
            else:
                dingfenxingTimes.append(fenxing.datetime)
                dingfenxingPrices.append(fenxing.price)
        
        plt.scatter(difenxingTimes,difenxingPrices,marker='^',c='r',s=60)
        plt.scatter(dingfenxingTimes,dingfenxingPrices,marker='v',c='g',s=60)
    
    
    @staticmethod
    def draw_bi(bi_list,ax):

        from pylab import Line2D
        line2d_list =[] 
    
        for bi in bi_list:
            if bi.btype == BI_UP:
                line2d_list.append(Line2D([bi.start_datetime, bi.end_datetime], \
                    [bi.start_price,bi.end_price], linewidth=10, alpha = 0.7,color = "orangered"))
            else:
                line2d_list.append(Line2D([bi.start_datetime, bi.end_datetime], \
                    [bi.start_price,bi.end_price], linewidth=10, alpha = 0.7,color = "aquamarine"))
        
        
        
        for line in line2d_list:
            ax.add_line(line)
        plt.show()
        
    
    @staticmethod
    def draw_xianduan(xianduan_list,ax):

        from pylab import Line2D
        line2d_list =[] 
    
        for xd in xianduan_list:
            if xd.xtype == XIANDUAN_UP:
                line2d_list.append(Line2D([xd.start_datetime, xd.end_datetime], \
                    [xd.start_price,xd.end_price], linewidth=20, alpha = 0.4,color = "violet"))
            else:
                line2d_list.append(Line2D([xd.start_datetime, xd.end_datetime], \
                    [xd.start_price,xd.end_price], linewidth=20, alpha = 0.4,color = "skyblue"))
        
        
        
        for line in line2d_list:
            ax.add_line(line)
        plt.show()
    
    @staticmethod
    def draw_zhongshu(zhongshu_list,ax):
        import matplotlib.patches as patches

        rec_list =[] 
    
        for zs in zhongshu_list:
            x = time.mktime(zs.start_plot_datetime.timetuple())
            y = zs.low_price
            width = time.mktime(zs.end_plot_datetime.timetuple()) - x
            height = zs.high_price - y
            rec_list.append(patches.Rectangle((x,y),width,height,linewidth=1,edgecolor='none',facecolor='crimson'))
        
        
        for rec in rec_list:
            ax.add_patch(rec)
    
        
        plt.show()
        
    @staticmethod
    def draw_candlestick2(df,ax):
    
        
        quotes=df[['datetime','open','high','low','close']].values
        tuples = [tuple(x) for x in quotes]
        qw=[]
            
        for index,things in enumerate(tuples):
            tuple1=(index,things[1],things[2],things[3],things[4])
            qw.append(tuple1)
        ax.grid(linestyle='-', linewidth=0.1)
        matplotlib.finance.candlestick_ohlc(ax, qw, colorup='r',colordown='g', alpha =.4, width=0.0005)
        plt.show()
    
    @staticmethod
    def draw_fenxing2(fenxing_list,ax,dd):

        difenxingTimes = []
        difenxingPrices = []
        dingfenxingTimes = []
        dingfenxingPrices = []
        for fenxing in fenxing_list:
            if fenxing.ftype == u'DI':
                difenxingTimes.append(dd[fenxing.datetime])
                difenxingPrices.append(fenxing.price)
            else:
                dingfenxingTimes.append(dd[fenxing.datetime])
                dingfenxingPrices.append(fenxing.price)
        
        plt.scatter(difenxingTimes,difenxingPrices,marker='^',c='r',s=60)
        plt.scatter(dingfenxingTimes,dingfenxingPrices,marker='v',c='g',s=60)
        
    @staticmethod
    def draw_bi2(bi_list,ax,dd):

        from pylab import Line2D
        line2d_list =[] 
    
        for bi in bi_list:
            if bi.btype == BI_UP:
                line2d_list.append(Line2D([dd[bi.start_datetime], dd[bi.end_datetime]], \
                    [bi.start_price,bi.end_price], linewidth=10, alpha = 0.7,color = "orangered"))
            else:
                line2d_list.append(Line2D([dd[bi.start_datetime], dd[bi.end_datetime]], \
                    [bi.start_price,bi.end_price], linewidth=10, alpha = 0.7,color = "aquamarine"))
    
    
    
        for line in line2d_list:
            ax.add_line(line)
        plt.show()
    
    @staticmethod
    def draw_xianduan2(xianduan_list,ax,dd):

        from pylab import Line2D
        line2d_list =[] 
    
        for xd in xianduan_list:
            if xd.xtype == XIANDUAN_UP:
                line2d_list.append(Line2D([dd[xd.start_datetime], dd[xd.end_datetime]], \
                    [xd.start_price,xd.end_price], linewidth=20, alpha = 0.4,color = "violet"))
            else:
                line2d_list.append(Line2D([dd[xd.start_datetime], dd[xd.end_datetime]], \
                    [xd.start_price,xd.end_price], linewidth=20, alpha = 0.4,color = "skyblue"))
        
        
        
        for line in line2d_list:
            ax.add_line(line)
        plt.show()
    
    @staticmethod
    def draw_zhongshu2(zhongshu_list,ax,dd):
        import matplotlib.patches as patches

        rec_list =[] 
    
        for zs in zhongshu_list:
            x = dd[zs.start_plot_datetime]
            y = zs.low_price
            width = dd[zs.end_plot_datetime] - x
            height = zs.high_price - y
            rec_list.append(patches.Rectangle((x,y),width,height,linewidth=1,edgecolor='none',facecolor='crimson'))
        
        
        for rec in rec_list:
            ax.add_patch(rec)
    
        
        plt.show()























