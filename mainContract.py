# -*- coding: utf-8 -*-
import tushare as ts
token = '1d2474f7708835bf813552f4c5d41dea83664ac30165efbf07d7e5c768ca579f'
import tushare as ts
#getFutureBarRTIntraDay --获取当日期货分钟线
#ts.set_token('1d2474f7708835bf813552f4c5d41dea83664ac30165efbf07d7e5c768ca579f')

mkt = ts.Market()
#开盘时间
df = mkt.FutureBarRTIntraDay('pb1612')

#df2[df2.index.time < t]


awesome = {
#"EG":{"main":"EG1701",'name':u'玻璃1701'},
#"SM":{"main":"SM1702",'name':u'锰硅1702'},
#"RO":{"main":"RO1701",'name':u'菜籽油1701'},
#"WS":{"main":"WS1701",'name':u'强麦1701'},
#"SF":{"main":"SF1704",'name':u'硅铁1704'},
#"LR":{"main":"LR1611",'name':u'晚籼稻1611'},
#"PM":{"main":"PM1701",'name':u'普麦1701'},
#"ER":{"main":"ER1705",'name':u'早籼稻1705'},
#"JR":{"main":"JR1705",'name':u'粳稻1705'},
#"V":{"main":"V1702",'name':u'聚氯乙烯1702'},
#"FB":{"main":"FB1703",'name':u'胶合板1703'},
#"L":{"main":"L1702",'name':u'聚乙烯1702'},
#"CS":{"main":"CS1707",'name':u'玉米淀粉1707'},
#"PP":{"main":"PP1706",'name':u'聚丙烯1706'},
#"JD":{"main":"JD1706",'name':u'鸡蛋1706'},
#"BB":{"main":"BB1706",'name':u'纤维板1706'},
#"FU":{"main":"FU1703",'name':u'燃油1703'},
#"RU":{"main":"RU1706",'name':u'橡胶1706'},
#"WR":{"main":"WR1706",'name':u'线材1706'},
"HC":{"main":"HC1611",'name':u'热轧卷板1611'},
"RB":{"main":"RB1612",'name':u'螺纹钢1612'},
}

for it in awesome.values():
    code = it['main']
    df = mkt.FutureBarRTIntraDay(code)
    print code
    print df.ix[0]