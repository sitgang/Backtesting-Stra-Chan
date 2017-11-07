# encoding: UTF-8

"""
包含一些开放中常用的函数
"""

import decimal
import json
from datetime import datetime
import smtplib  
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText  
from email.mime.application import MIMEApplication  

MAX_NUMBER = 10000000000000
MAX_DECIMAL = 4

#----------------------------------------------------------------------
def safeUnicode(value):
    """检查接口数据潜在的错误，保证转化为的字符串正确"""
    # 检查是数字接近0时会出现的浮点数上限
    if type(value) is int or type(value) is float:
        if value > MAX_NUMBER:
            value = 0
    
    # 检查防止小数点位过多
    if type(value) is float:
        d = decimal.Decimal(str(value))
        if abs(d.as_tuple().exponent) > MAX_DECIMAL:
            value = round(value, ndigits=MAX_DECIMAL)
    
    return unicode(value)

#----------------------------------------------------------------------
def loadMongoSetting():
    """载入MongoDB数据库的配置"""
    try:
        f = file("VT_setting.json")
        setting = json.load(f)
        host = setting['mongoHost']
        port = setting['mongoPort']
    except:
        host = 'localhost'
        port = 27017
        
    return host, port

#----------------------------------------------------------------------
def todayDate():
    """获取当前本机电脑时间的日期"""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)    

#----------------------------------------------------------------------
class mailhelper(object):
    '''
    这个类实现发送邮件的功能
    '''
    def __init__(self):

        #self.mail_host="mail.bit.edu.cn"  #设置服务器
        #self.mail_user="1120142875"    #用户名
        #self.mail_pass="francium0426"   #密码
        #self.mail_postfix="bit.edu.cn"  #发件箱的后缀
        self.mail_host="smtp.qq.com"  #设置服务器
        self.mail_user="621181828"    #用户名
        self.mail_pass="pcupmzvzeovybefa"   #密码
        self.mail_postfix="qq.com"  #发件箱的后缀

    def send_mail(self,to_list,sub,content='!',pic_path=None):
        me=u"Shingen Quant System"+"<"+self.mail_user+"@"+self.mail_postfix+">"
        
        msg = MIMEMultipart(_subtype='plain',_charset='utf-8')
        
        part = MIMEText(content)  
        msg.attach(part) 
        
        if pic_path:
            
            part = MIMEApplication(open(pic_path,'rb').read())  
            part.add_header('Content-Disposition', 'attachment', filename="FloatValue.jpg")  
            msg.attach(part)
        
        #msg = MIMEText(content,_subtype='plain',_charset='utf-8')
        msg['Subject'] = sub
        msg['From'] = me
        msg['To'] = ";".join(to_list)
        
         
        try:
            server = smtplib.SMTP_SSL(self.mail_host,465)
            #server = smtplib.SMTP()
            #server.connect(self.mail_host)
            server.login(self.mail_user,self.mail_pass)
            server.sendmail(me, to_list, msg.as_string())
            server.close()
            return True
        except Exception, e:
            print str(e)
            return False 
