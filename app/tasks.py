# ******************************************************************************
#  Copyright (c) 2020-2021 University of Stuttgart
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
import datetime

from app import app, db

from app.result_model import Result
import json
import base64
import sys

from redbaron import RedBaron
import json
from app.splitting_implementation.workflow_generator import WorkflowJson
from app.splitting_implementation.script_analyzer import ScriptAnalyzer
from app.splitting_implementation.output_generator import write_blocks
from redbaron import RedBaron
import os
import tempfile
from os.path import basename
import zipfile
from rq import get_current_job
import tempfile
from os import listdir
from tempfile import mkdtemp
import urllib.request


def execute(provider, impl_url, impl_data, impl_language, transpiled_qasm, input_params, token, access_key_aws,
            secret_access_key_aws, qpu_name,
            optimization_level, noise_model, only_measurement_errors, shots, bearer_token, qasm_string, **kwargs):
    """Create database entry for result. Get implementation code, prepare it, and execute it. Save result in db"""
    app.logger.info("Starting execute task...")
    

def do_the_split(implementations_url):

    # directory containing all templates required for generation
    directory = mkdtemp()
    job = get_current_job()
    script_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + implementations_url
    app.logger.info("Retrieve implementation from url")
    app.logger.info(script_url)

    
    # insert results into job object
    result = Result.query.get(job.get_id())

    downloadPath, response = urllib.request.urlretrieve(script_url, "service.zip")
    with zipfile.ZipFile(downloadPath, "r") as zip_ref:
        directory = mkdtemp()
        app.logger.info('Extracting to directory: ' + str(directory))
        zip_ref.extractall(directory)

        # zip contains one folder per task within the candidate
        zipContents = [f for f in listdir(directory)]
        app.logger.info(zipContents)
        pythonfile = None
        requirementsfile = None
    
        for zipContent in zipContents:
            app.logger.info("analyze the content of the zip file")

            if search_python_file(os.path.join(directory, zipContent)) != None:
                pythonfile = search_python_file(os.path.join(directory, zipContent))

            if search_requirements_file(os.path.join(directory, zipContent)) != None:
                requirementsfile = search_requirements_file(os.path.join(directory, zipContent))
                continue
            #requirementsfile = search_requirements_file(os.path.join(directory, zipContents[0]))
    
        if pythonfile != None:
            app.logger.info(pythonfile)
            # RedBaron object containing all information about the hybrid program to generate
            with open(os.path.join(pythonfile), "r") as source_code:
                    splitterBaron = RedBaron(source_code.read())
                    all_but_main = splitterBaron.findAll("DefNode", name=lambda n: n != "main")
                    main_function = splitterBaron.findAll("DefNode", name=lambda n: n == "main")[0]
                    # Find all 'import ...' statements
                    import_statements = splitterBaron.find_all('ImportNode')

                    # Find all 'from ... import ...' statements
                    from_import_statements = splitterBaron.find_all('FromImportNode')

                    # Combine both import statements
                    all_imports = import_statements + from_import_statements

                    scripts_analyzer = ScriptAnalyzer(main_function)
                    analyzer_result = scripts_analyzer.get_result()

                    write_blocks(pythonfile, requirementsfile, analyzer_result, all_but_main, all_imports, result)

                    foobar = WorkflowJson(analyzer_result)
                    wf_result = foobar.get_result()
                    #wf_json_writer = open("output/workflow.json", "w")
                    #wf_json_writer.write(json.dumps(wf_result, indent=4))
                    result.agent = zip_workflow_result(wf_result)
                    print(json.dumps(wf_result))

    app.logger.info("generated ")
    
    app.logger.info('Program generation successful!')


    # update database
    result.complete = True
    db.session.commit()


def zip_polling_agent(requirements, polling_agent, starting_point):
    templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'splitting_implementation/templates')
    # zip generated polling agent, afterwards zip resulting file with required Dockerfile
    if os.path.exists('../polling_agent.zip'):
        os.remove('../polling_agent.zip')
    if os.path.exists('../polling_agent_wrapper.zip'):
        os.remove('../polling_agent_wrapper.zip')
    zipObj = zipfile.ZipFile('../polling_agent_wrapper.zip', 'w')
    zipObj.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
    zipObj.write(os.path.join(templatesDirectory, 'requirements'), 'requirements')

    pollingTemp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    with open(pollingTemp.name, "w") as source_code:
        source_code.write(polling_agent)
    zipObj = open('../polling_agent_wrapper.zip', "rb")
    return zipObj.read()

def zip_workflow_result(workflowResult):
    templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'splitting_implementation/templates')
    # zip generated polling agent, afterwards zip resulting file with required Dockerfile
    if os.path.exists('../polling_agent.zip'):
        os.remove('../polling_agent.zip')
    if os.path.exists('../polling_agent_wrapper.zip'):
        os.remove('../polling_agent_wrapper.zip')
    workflowTemp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    with open(workflowTemp.name, "w") as source_code:
        source_code.write(json.dumps(workflowResult, indent=4))
    zipObj = zipfile.ZipFile('../polling_agent_wrapper.zip', 'w')
    zipObj.write(workflowTemp.name, 'workflow.json')
    zipObj.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
    zipObj = open('../polling_agent_wrapper.zip', "rb")
    return zipObj.read()

def search_python_file(directory):
    app.logger.info("find python file inside zip")
    app.logger.info(directory)
    # only .py are supported, also nested in zip files
    if directory.endswith('.py'):
        app.logger.info('Found Python file with name: ' + str(directory))

        # we only support one file, in case there are multiple files, try the first one
        return os.path.join(directory)

def search_requirements_file(directory):
    app.logger.info("find requirements file inside zip")
    app.logger.info(directory)
    # only .py are supported, also nested in zip files
    if directory.endswith('.txt'):
        app.logger.info('Found requirements file with name: ' + str(directory))

        # we only support one file, in case there are multiple files, try the first one
        return os.path.join(directory)