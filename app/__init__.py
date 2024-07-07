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

from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from redis import Redis
import rq
from app import Config
import logging


app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, result_model, errors
from app.controller import register_blueprints
from flask_smorest import Api

app.redis = Redis.from_url(app.config['REDIS_URL'], port=5010)
app.queue = rq.Queue('qc-script-splitter', connection=app.redis, default_timeout=10000)
app.logger.setLevel(logging.INFO)


api = Api(app)
register_blueprints(api)
