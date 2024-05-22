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

from app import app, db
from app.result_model import Result
from flask import jsonify, abort, request, url_for, send_from_directory
import json
import os
import tempfile
from os.path import basename
import string
import random
from io import BytesIO
import requests

def fetch_file_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

@app.route('/qc-script-splitter/api/v1.0/split-implementation', methods=['POST'])
def split_implementation():
    # Extract required input data
    if not request.files.get('script'):
        if not request.json or not 'implementation-url' in request.json:
            print('Not all required parameters available in request: ')
            abort(400)
    
    if 'script' in request.files:
        script_file = request.files["script"]
    elif 'implementation-url' in request.json:
        script_url = request.json['implementation-url']
        script_file = fetch_file_from_url(script_url)
    else:
        abort(400)

    # Store file with required programs in local file and forward path to the workers
    directory = app.config["UPLOAD_FOLDER"]
    app.logger.info('Storing file comprising required programs at folder: ' + str(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    script_file_name = 'script' + random_string + '.zip'

    # Save the script file appropriately
    script_file_path = os.path.join(directory, script_file_name)
    if isinstance(script_file, BytesIO):
        with open(script_file_path, 'wb') as f:
            f.write(script_file.getvalue())
    else:
        script_file.save(script_file_path)

    script_url = url_for('download_uploaded_file', name=os.path.basename(script_file_name))
    app.logger.info('File available via URL: ' + str(script_url))
    #script_file.save(os.path.join(directory, fileName))

    # Assuming you have set up RQ and defined app.queue and app.tasks.do_the_split correctly
    job = app.queue.enqueue('app.tasks.do_the_split', script_url)

    result = Result(id=job.get_id())
    db.session.add(result)
    db.session.commit()

    app.logger.info('Returning HTTP response to client...')
    content_location = '/qc-script-splitter/api/v1.0/results/' + result.id
    response = jsonify({'Location': content_location})
    response.status_code = 202
    response.headers['Location'] = content_location
    response.autocorrect_location_header = True
    return response

@app.route('/qc-script-splitter/api/v1.0/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Return result when it is available."""
    result = Result.query.get(result_id)
    app.logger.info(result)
    if result.complete:
        if result.error:
            return jsonify({'id': result.id, 'complete': result.complete, 'error': result.error}), 200
        else:
            # create result directory if not existing
            directory = app.config["RESULT_FOLDER"]
            if not os.path.exists(directory):
                os.makedirs(directory)

            # create files and serve as URL
            programName = os.path.join(directory, result.id + '-program.zip')
            with open(programName, 'wb') as file:
                file.write(result.program)
            agentName = os.path.join(directory, result.id + '-agent.zip')
            with open(agentName, 'wb') as file:
                file.write(result.agent)

            return jsonify({'id': result.id, 'complete': result.complete,
                            'programsUrl': url_for('download_generated_file', name=result.id + '-program.zip'),
                            'workflowUrl': url_for('download_generated_file', name=result.id + '-agent.zip')}), 200
    else:
        return jsonify({'id': result.id, 'complete': result.complete}), 200


@app.route('/qc-script-splitter/api/v1.0/version', methods=['GET'])
def version():
    return jsonify({'version': '1.0'})

@app.route("/")
def heartbeat():
    return '<h1>script splitter is running</h1> <h3>View the API Docs <a href="/api/swagger-ui">here</a></h3>'

@app.route('/qc-script-splitter/api/v1.0/hybrid-programs/<name>')
def download_generated_file(name):
    return send_from_directory(app.config["RESULT_FOLDER"], name)

@app.route('/qc-script-splitter/api/v1.0/uploads/<name>')
def download_uploaded_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

