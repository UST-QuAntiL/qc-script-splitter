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

@app.route('/qc-script-splitter/api/v1.0/split-implementation', methods=['POST'])
def split_implementation():
    if not request.json or not 'implementation-url' in request.json:
        abort(400)

    in_path = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'input/hybrid_program_kmeans.py')
    f = open(in_path, "r")
    
    job = app.queue.enqueue('app.tasks.do_the_split', request.json["implementation-url"])

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