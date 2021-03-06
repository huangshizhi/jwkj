# -*- coding: utf-8 -*-
"""
Created on Thu Apr 20 10:04:41 2017

@author: huangshizhi

物联网流量分配方案

早期的方法，存在的问题较多，不再使用
"""

import pandas as pd
import pulp as pl

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.types import String,Integer,Numeric


'''
根据当月物联网数据，判断是否有iccid重复
'''
def is_duplicate(pdata):
    #判断iccid是否重复
    iccid_duplicated_df = pdata[pdata.duplicated(['iccid'], keep='first')] 
    iccid_duplicated_list = iccid_duplicated_df['iccid'].tolist()
    if len(iccid_duplicated_list)>0:
        print("该月份物联网数据有重复,重复个数为%-6.0f" % int(len(iccid_duplicated_list)))
        print(iccid_duplicated_list)
    else:
        print("该月物联网卡数据无重复!")
        
''' 
根据流量资费数据，得到套餐list,套餐资费和套餐类型字典
'''       
def get_package_dict(ptest):
    ptest.index = ptest['packages'].tolist()
    plist = ptest.index.tolist()
    df = ptest.to_dict(orient='dict')
    
    costs_dict = df['package_cost']
    package_type_dict = df['package_type']
    
    return plist,costs_dict,package_type_dict
    


'''
根据流量总和和物联网卡个数，求出最优解；
参数flow_sum为流量总和，flow_length为物联网数量个数，
plist为套餐类型,形如:['12MB', '30MB', '500MB', '1G', '2G']
costs_dict为各自套餐对应的资费，形如 {'2G': 90.0, '1G': 60.0, '500MB': 30.0, '30MB': 5.0, '12MB': 2.5}
package_type_dict为套餐类型对应流量数值，单位为MB
返回最优资费minum_value

'''
def min_amount(flow_sum,flow_length,plist,costs_dict,package_type_dict):
    prob=pl.LpProblem('jwkj',pl.LpMinimize)  
    #定义套餐变量
    pack_vars = pl.LpVariable.dicts("套餐",plist,0,cat='Integer')       
    #目标函数   
    prob += pl.lpSum([costs_dict[i]*pack_vars[i] for i in plist])    
    #约束条件
    prob += pl.lpSum([pack_vars[i] for i in plist]) == flow_length #个数约束    
    prob += pl.lpSum([package_type_dict[i]* pack_vars[i] for i in plist])>=flow_sum #套餐约束
    #问题求解
    prob.solve()
    
    '''
    # 显示结果
    for v in prob.variables():
        print((v.name,v.varValue))
    '''
    var_list = prob.variables()
    var_item={}

    #各个套餐类型及其所需个数
    for v in var_list:
        print((v.name,v.varValue))
        var_item[v.name]=int(v.varValue)
                                 
    if var_item["套餐_"+plist[-1]]>0:
        print("使用最小套餐流量不能满足条件！")    
        
    minum_value = pl.value(prob.objective)
    print("理论最优资费为:%6.2f" %minum_value)
    return minum_value
    

'''
套餐够用，多余流量为0；套餐不够用，多出的流量取绝对值。
'''

def sign(a):
    if a>=0:
        return 0
    else:
        return abs(a)

'''
给定一个list类型数据，进行累加运算
流量汇总
'''

def sum_list(liuliang_list):
    if(len(liuliang_list)>=0):
        liuliang_sum_list=[]
        liuliang_sum = 0
        for j in range(len(liuliang_list)) :        
            liuliang_sum = liuliang_sum + liuliang_list[j]
            liuliang_sum_list.append(liuliang_sum)
        return liuliang_sum_list
    else:
        return -1

'''
得到套餐分组信息的统计信息
'''
def get_stats(group):
    return {'min':group.min(),'sum':group.sum(),
            'count':group.count(),'max':group.max(),
            'avg':group.mean()}


'''
list类型的倍数
'''    
def product_list(list_test,p):
    if(len(list_test)>=0):
        temp_list=[]
        for i in list_test:
            temp_list.append(p*i)
        return p,temp_list
    
   
'''
数据比较，给定数据a,与某个list类型比较，取绝对值，求出最小值及对应值        
'''  
def compare_number(a,list1):
    minum = float("inf")
    temp = []
    for i in range(len(list1)):
        if abs(a-list1[i])<minum:
            temp.append(abs(a-list1[i]))
    idx = temp.index(min(temp))
    return a,list1[idx],idx


'''
目的：根据分配套餐值及数量，交换临近的流量顺序
数据比较，给定数据a,与某个list的数值进行比较，
返回比较值与接近值      
'''

def neighbor_number(a,l1):
    minum = float("inf")
    t1 = []
    for i in range(len(l1)):
        if (a-l1[i])<minum:
            t1.append(a-l1[i])
    t2 = [t for t in t1 if t>0]
    if len(t2)>0:
        idx = t1.index(min(t2))
        return a,l1[idx]
    else:
        t3 = [abs(t) for t in t1 ]
        idx = t3.index(min(t3))
        return a,l1[idx]
'''
截取套餐最大的流量值
返回大套餐类型的dataframe和剩余的dataframe
'''
def get_max_data(df,ptype):
    '''
    df = pdata_sort_descending    
    ptype = max_package_type
    '''    
    flist = df['flow'].tolist()
    temp_list = []
    flow_sum_list = sum_list(flist)
    avg_list = []    
    for i in range(len(flow_sum_list)):
        if i == 0:
            avg_list.append(flow_sum_list[i])
        else:
            avg_list.append(flow_sum_list[i]/(i+1))
    k1,k2,k3 = compare_number(ptype,avg_list)
    print("最大套餐值:",k1)
    #判断是否需要进行交换
    if (abs(ptype*(k3+1) - flow_sum_list[k3])>flist[k3+1]):
        print("不需要交换顺序！")
        temp_list = flist[:k3+2]
    else:
        print("交换临近顺序！")
        temp_list = flist[:k3]
        delta = ptype*(k3+1) - flow_sum_list[k3-1]
        neighbor_value = neighbor_number(delta,flist)[1]
        temp_list.append(neighbor_value)
       
    ptemp = pd.DataFrame(temp_list,columns=['flow'])
    df_max_1 = pd.merge(left = df,right = ptemp,how='inner',on = 'flow')
    is_duplicate(df_max_1)
    df_max = df_max_1.drop_duplicates(['iccid']) #只计算考虑iccid没有重复的情况  

    df_max['package_type'] = ptype
    df_iccid_list = "|".join(df_max['iccid'].tolist())
    reminder_df = df[~df['iccid'].str.contains(df_iccid_list)]   
   
    return df_max,reminder_df
   
   

'''
得到最大套餐
'''

def get_max_package(iot_data):
    #按套餐类型分组
    grouped = iot_data['flow'].groupby(iot_data['package_type'])    
    count_data = grouped.apply(get_stats).unstack()
    #重置索引
    decribe_data = count_data.reset_index()
    
    #判断流量从小到大进行排序，是否可行
    if len(decribe_data)>1:
        max_avg = decribe_data.at[len(decribe_data)-1,'avg']
        max_count  = decribe_data.at[len(decribe_data)-1,'count']
        max_package_type = decribe_data.at[len(decribe_data)-1,'package_type']
        second_max_package_type= decribe_data.at[len(decribe_data)-2,'package_type']
        #if (max_avg > second_max_package_type):
        if ((decribe_data.at[len(decribe_data)-1,'sum'] - max_package_type * max_count) > second_max_package_type):
            print("使用从小到大对流量进行排序，不是一个可行解，需要将流量从大到小进行排序！")
            
        elif(max_avg < max_package_type): 
            max_package_type = 0 
    else:
        return 0
    return max_package_type   
'''
计算物联网套餐资费总价
'''

def compute_total(iot_data):  
    #按套餐类型分组
    grouped = iot_data['flow'].groupby(iot_data['package_type'])    
    count_data = grouped.apply(get_stats).unstack()
    #重置索引
    decribe_data = count_data.reset_index()
    #合并数据
    cdata = pd.merge(left = decribe_data,right = package_price,how='left',on = 'package_type')
    #判断是否超出套餐流量，超出按每M0.2048元计费，不超出则为0
    cdata['flow_delta'] = cdata['sum'] - cdata['package_type']*cdata['count']
    cdata['sign_liliang'] = cdata['flow_delta'].apply(lambda x :sign(-x)*0.2048)           
    #计算各个套餐总价
    cdata['flow_total'] = cdata['count']*cdata['package_cost']+cdata['sign_liliang']
    compute_total =  round(cdata['flow_total'].sum(),2)
    
    return compute_total



'''
给定使用流量情况，输出对应的套餐
返回选定的套餐及套餐个数,f流量，t套餐
'''
def flow_package(f,t):
    item_list=[]
    
    for i in range(len(f)): 
        p,l = product_list(t,i+1)
        k1,k2,k3 = compare_number(f[i],l)       
        item={}
        item['liuliang'],item['taocan_sum'],item['package_type'],item['geshu'],  \
            item['liuliang_delta'] ,item['liuliang_delta_per'] = (k1,k2,k2/p,p,(k2-k1),(k2-k1)/p)
        item_list.append(item)
    tdata_delta = pd.DataFrame(item_list)
    tdata = pd.merge(left = tdata_delta,right = package_price,how='left', on='package_type')
    tdata['sign_liliang'] = tdata['liuliang_delta'].apply(lambda x :sign(x)*0.2048)           
    tdata['account_per_flow'] =  tdata['package_cost']+tdata['sign_liliang']/tdata_delta['geshu']
    #tdata['account_per_flow_floor'] = tdata['account_per_flow'].apply(lambda x :math.floor(x))
    #tdata['account_per_flow_sum'] = tdata['account_per_flow'] +tdata['liuliang_delta_per']
    #单位浪费的流量可控，即流量尽量够用
    
    hdata = tdata[tdata['liuliang_delta_per']>=-20] 
    
    if len(hdata)>0:
        #使得每张卡所需平均费用最小，取平均费用最小值的最大索引,套餐均值尽可能少
        minum = min(hdata['account_per_flow']) #套餐均值最小
        idx = hdata[hdata['account_per_flow']==minum]['geshu'].idxmax() #得到minum对应的最大索引值
    else:    
        minum = min(tdata['account_per_flow']) #套餐均值最小
        idx = tdata[tdata['account_per_flow']==minum]['geshu'].idxmax() #得到minum对应的最大索引值
 
    #返回使用套餐及使用套餐个数  
    return (tdata.at[idx,'geshu'],tdata.at[idx,'package_type'])

'''
重置套餐流量顺序
'''

def package_list_redefine(pdata_sort,package_list):
    liuliang_list = pdata_sort['flow'].tolist()
    start_time = datetime.now()
    print("开始时间:"+str(start_time))
    tidx = 0  #所选套餐索引位置
    temp_list = []
    compare_list = liuliang_list
    while(0<len(compare_list)):     
        s = sum_list(compare_list) #流量累计
        t = package_list[tidx:]  #套餐类型
        h = flow_package(s,t)    #得到数据形如(套餐个数，套餐)
        delta = h[0]*h[1] - sum(compare_list[:h[0]-1])
        flow_value = neighbor_number(delta,compare_list)[1]
        for i in range(h[0]-1):
            temp_list.append(compare_list[i])  
            
        temp_list.append(flow_value)
        compare_list  = list(set(compare_list)-set(temp_list))
        compare_list.sort()
    end_time = datetime.now()
    print("重置套餐顺序耗时:"+str(end_time-start_time))
    return temp_list

'''
本函数实现给定流量使用情况，输出该流量所使用的套餐类型
pdata为输入数据,liuliang_list类型数据，taocan_list为所有套餐类型
'''

def package_type(pdata,package_list):
    liuliang_list = pdata['flow'].tolist()
    start_time = datetime.now()
    print("开始时间:"+str(start_time))
    count = 0 #统计流量套餐个数
    tidx = 0  #所选套餐索引位置
    while(count<len(liuliang_list)):
        s = sum_list(liuliang_list[count:]) #流量累计
        t = package_list[tidx:]  #套餐类型
        h = flow_package(s,t) #得到数据形如(套餐个数，套餐)
        idx = h[0] #数据框索引位置
        pdata.ix[count:count+idx-1,'package_type'] = h[1] #数据框相应位置赋值套餐值
        tidx = package_list.index(h[1]) #套餐所在索引位置
        count = count + idx
    end_time = datetime.now()
    print("计算流量所对应的套餐耗时:"+str(end_time-start_time))
    return pdata

'''
对流量数值从小到大进行排序，优先使用小流量套餐 
'''   
def iot_ascending_data(pdata,package_price):       
    #套餐列表
    package_list = package_price['package_type'].tolist()       
    #对流量数据flow进行排序，从小到大
    pdata_sort = pdata.sort_values(by=['flow'])
    package_list_data = package_list_redefine(pdata_sort,package_list)

    p1 = pd.DataFrame(package_list_data,columns=['flow'])    
    p2 = pd.merge(left = p1,right = pdata_sort,how='inner',on = 'flow')
    p3 = p2.drop_duplicates()
    p3.index = range(len(p3))
    #调用流量-套餐函数  
    package_data = package_type(p3,package_list)
    #合并，生成对应套餐价格
    iot_data = pd.merge(left = package_data,right = package_price,how='left',on = 'package_type')
    return iot_data

     
if __name__=='__main__': 
    engine = create_engine('mysql+pymysql://root:root@localhost:3306/test?charset=utf8', echo=False) 
    #pdata_init = pd.read_sql("select * from  jwkj_iot_0616",engine)

    #pdata_init = pd.read_excel(r'D:\ad_portrait\物联网卡资费\code\测试数据.xlsx',sheetname='month_201611_zj')
    pdata_init = pd.read_excel(r"D:\ad_portrait\物联网卡资费\数据\测试数据\random_test.xlsx") 
    '''    
    将['iccid']字段变换为'str'类型，以便  get_max_data使用下列语句    
    df_iccid_list = "|".join(df_max['iccid'].tolist())
    
    '''
    pdata_init['iccid'] = pdata_init['iccid'].astype('str')
    
    is_duplicate(pdata_init) #判断物联网数据是否有重复   
    pdata = pdata_init.drop_duplicates(['iccid']) #只计算考虑iccid没有重复的情况  
    package_price = pd.read_excel(r'D:\ad_portrait\物联网卡资费\package_price.xlsx',sheetname="浙江联通")
    
    
    plist,costs_dict,package_type_dict  = get_package_dict(package_price)
    #重置索引
    package_price.index = range(len(package_price))  

    flow_sum = pdata['flow'].sum() #流量总量
    flow_length = len(pdata)  #总的卡个数    
    #计算得到理论最优值，以便进行比较
    opt_minum = min_amount(flow_sum,flow_length,plist,costs_dict,package_type_dict)
    
    #从小到大进行排序，返回结果
    iot_data  = iot_ascending_data(pdata,package_price)
    #返回最大套餐类型，以便判断是否需要从大到小控制流量
    max_package_type = get_max_package(iot_data) 
        
    if max_package_type >0:
        #从大到小进行排序
        pdata_sort_descending = pdata.sort_values(by=['flow'],ascending=False)
        df_max,reminder_df  = get_max_data(pdata_sort_descending,max_package_type)
        df_max_price = pd.merge(left = df_max,right = package_price,how='left',on = 'package_type')
        reminder_iot = iot_ascending_data(reminder_df,package_price)
        reminder_iot_3 = reminder_iot[['iccid','flow','package_type']]
        #reminder_iot_3 = reminder_iot[['iot_id','iccid','flow','package_type']]
        iot_data = pd.concat([df_max,reminder_iot_3],ignore_index=True)
        #iot_data = pd.concat([df_max_price,reminder_iot],ignore_index=True)
    else:
        pass
    
    package_sum = compute_total(iot_data)        
    amount_ratio = package_sum/opt_minum #最优解的倍数    
    print("流量套餐总价为%-10.2f,最优资费总价为%-10.2f" %(package_sum,opt_minum))
    print("求得的解与最优解的比值:%-10.4f" %amount_ratio)    
    
    #保存输出
    #iot_data.to_excel(r"D:\ad_portrait\物联网卡资费\数据\测试数据\random_test_package.xlsx",index=False)

    #保存到数据库
    
    iot_data.to_sql('jwkj_iot_0616',engine,if_exists = 'replace',
                    index=False,chunksize = 500000,
                    dtype={'iccid':String(50),'iot_id':Integer,'flow':Numeric(20,4),
                           'package_type':Integer,'iot_id':Integer})
    



