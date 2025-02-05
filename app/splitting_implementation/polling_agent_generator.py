# ******************************************************************************
#  Copyright (c) 2021 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************
import os
import random
import string
import tempfile
from os.path import basename


def generate_polling_agent(block, parameters, return_values, global_assignments):
    # Read from polling agent template

     # directory containing all templates required for generation
    templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'templates')
    
    with open(os.path.join(templatesDirectory, 'polling_agent_template.py'), "r") as template:
        content = template.read()

    # generate random name for the polling agent and replace placeholder
    pollingAgentName = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    content = content.replace("$ServiceNamePlaceholder", pollingAgentName)

    # handle variable retrieval for input data
    load_data_str = ''
    filtered_results = []
    for left_side, assignment in global_assignments:
        parameters = [param for param in parameters if param not in [left_side]]


    #print('Number of input parameters: %d' % len(parameters))
    for inputParameter in parameters:
        load_data_str += '\n'
        load_data_str += '                    if variables.get("' + inputParameter + '").get("type").casefold() in ["integer", "double", "boolean"]:\n'
        load_data_str += '                        print("Input Parameter ' + inputParameter + ' (basic type)")\n'
        load_data_str += '                        ' + inputParameter + ' = variables.get("' + inputParameter + '").get("value")\n'
        load_data_str += '                        print("...value: %s" % ' + inputParameter + ')\n'
        load_data_str += '                    else:\n'
        load_data_str += '                        try:\n'
        load_data_str += '                            ' + inputParameter + ' = variables.get("' + inputParameter + '").get("value")\n'
        load_data_str += '                            if ' + inputParameter + ' is None:\n'
        load_data_str += '                                ' + inputParameter + ' = download_data(camundaEndpoint + "/process-instance/" + externalTask.get("processInstanceId") + "/variables/' + inputParameter + '/data")\n'
        load_data_str += '                        except Exception as err:\n'
        load_data_str += '                            ' + inputParameter + ' = download_data(camundaEndpoint + "/process-instance/" + externalTask.get("processInstanceId") + "/variables/' + inputParameter + '/data")\n'
        load_data_str += '                            print("...downloaded value: %s" % ' + inputParameter + ')\n'

    content = content.replace("### LOAD INPUT DATA ###", load_data_str)

    # Keep track of return variables to be excluded
    excluded_return_variables = []
    for line in block["lines"]:
            if line.type == "endl":
                continue
            line_content = line.dumps()
            # Skip lines containing "kwargs" and note the variables to exclude
            if "kwargs" in line_content or "user_messenger" in line_content:
                # Check if this line sets a return variable
                for var in return_values:
                    if var in line_content:
                        excluded_return_variables.append(var)
                continue

        # Filter out excluded return variables
    filtered_return_variables = [var for var in return_values if var not in excluded_return_variables]
    r_variables =[]
    call_str = ", ".join(filtered_return_variables)

    if len(filtered_return_variables) > 0:
        call_str += " = "
    call_str += "app.main(" + ", ".join(parameters) + ")"
    content = content.replace("### CALL SCRIPT PART ###", call_str)

    # handle output
    '''
    Required return value by Camunda:
    {
        "workerId": pollingAgentName, 
        "variables": {
            "variable_name": {
                "value": 'base64_content',
                "type": "File",
                "valueInfo": {
                    "filename": "file_name",
                    "encoding": ""
                }
            }
        }
    }
    '''
    outputHandler = '\n'
    outputHandler += '                    body = {"workerId": "' + pollingAgentName + '"}\n'
    outputHandler += '                    body["variables"] = {}\n'
    for outputParameter in filtered_return_variables:
        # encode output parameter as file to circumvent the Camunda size restrictions on strings
        outputHandler += '\n'
        outputHandler += '                    if isinstance(' + outputParameter + ', int):\n'
        outputHandler += '                        print("OutputParameter (int) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "integer"}\n'
        outputHandler += '                    elif isinstance(' + outputParameter + ', float):\n'
        outputHandler += '                        print("OutputParameter (float) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "double"}\n'
        outputHandler += '                    elif isinstance(' + outputParameter + ', bool):\n'
        outputHandler += '                        print("OutputParameter (bool) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "boolean"}\n'
        outputHandler += '                    else:\n'
        outputHandler += '                        try:\n'
        outputHandler += '                            print("Encode OutputParameter %s" % ' + outputParameter + ')\n'
        outputHandler += '                            '+outputParameter + ' = base64.b64encode(str.encode(' + outputParameter+ ')).decode("utf-8")\n'
        outputHandler += '                            body["variables"]["' + outputParameter + '"] = {"value":' + outputParameter + ', "type": "File", "valueInfo": {"filename": "' + outputParameter + '.txt", "encoding": ""}}\n'
        outputHandler += '                        except Exception as err:\n'
        outputHandler += '                            print("Could not pickle %s" % err)\n'
        outputHandler += '                    print("body: %s" % body)'

    # remove the placeholder
    return content.replace("### STORE OUTPUT DATA SECTION ###", outputHandler)
