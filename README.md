# jwkj

jwkj 物联网优化脚本

iot_optium.py 为准确的脚本，采用pl.GLPK()优化器，参数设置为
prob.solve(pl.GLPK(r"D:\ad_portrait\software\glpk-4.62\glpk-4.62\w64\glpsol.exe",options=['--mipgap', '0.001']))
效率不如
prob.solve(pl.GUROBI())
prob.solve(pl.CPLEX())
这两个商用软件，这两个软件都有限制变量个数，如CPLEX限制变量不能超过1000个！
