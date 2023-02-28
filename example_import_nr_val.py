from nornir import InitNornir
from nornir_rich.functions import print_result
from nr_val import task_engine

nr = InitNornir(config_file="config.yml")

# ----------------------------------------------------------------------------
# FILE: An example using a file as an input
# ----------------------------------------------------------------------------
result = nr.run(task=task_engine, input_data="input_data.yml")
print_result(result, vars=["result", "report_text"])

# ----------------------------------------------------------------------------
# VARIABLE: An example using a variable as an input
# ----------------------------------------------------------------------------
# my_input_data = {
#     "groups": {
#         "ios": {
#             "intf_bonded": {
#                 "port_channel": {
#                     "Po1": {"protocol": "LACP", "members": ["Gi0/2", "Gi0/3"]}
#                 }
#             },
#         }
#     }
# }

# result = nr.run(task=task_engine, input_data=my_input_data)
# print_result(result, vars=["result", "report_text"])

# ----------------------------------------------------------------------------
# REPORT: An example using a file as an input adn saving the report to file
# ----------------------------------------------------------------------------
# result = nr.run(
#     task=task_engine,
#     input_data="input_data.yml",
#     directory="/Users/user1/reports",
# )
# print_result(result, vars=["result", "report_text"])
