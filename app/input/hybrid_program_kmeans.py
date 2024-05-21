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

import json
import os
from urllib.request import urlopen
from qiskit import IBMQ, transpile, QuantumCircuit
import threading
import base64
import numpy as np
import requests
from math import acos, sqrt
from typing import Any


def main(backend, **kwargs) -> Any:
    currentIteration = 1
    iterations = kwargs["iterations"]
    centroids = kwargs["centroids"]
    data = kwargs["data"]
    backend4 = backend
    ibmq_backend = kwargs["ibmq_backend"]
    ibmq_token = kwargs["ibmq_token"]
    circuits_string = kwargs["circuits_string"]

    while currentIteration <= 50:
        currentIteration = currentIteration + 1
        # SPLIT: Circuit Execution
        cluster_mapping = Task_0qfiqux_execute(circuits_string, ibmq_token, ibmq_backend, backend4)
        # SPLIT: Result Evaluation
        clusteringConverged, new_centroids, iterations = Task_0lg77kd_execute(cluster_mapping, data, centroids,
                                                                              iterations)
        if not clusteringConverged == 'false':
            break
        pass

        # SPLIT: Parameter Optimization
        circuits_string = Task_11jwstv_execute(centroids, data)

    pass
    # SPLIT
    serialized_result = {"cluster_mapping": cluster_mapping,
                         "clusteringConverged": clusteringConverged,
                         "new_centroids": new_centroids,
                         "iterations": iterations,
                         "circuits_string": circuits_string,
                         }


def Task_0qfiqux_create_backend(backend_name, token):
    if IBMQ.active_account():
        IBMQ.disable_account()
    provider = IBMQ.enable_account(token, url=ibmq_url, hub=ibmq_hub, group=ibmq_group, project=ibmq_project)
    return provider.get_backend(backend_name.lower())


def Task_0qfiqux_map_histogram_to_qubit_hits(histogram):
    # create array and store the hits per qubit, i.e. [#|0>, #|1>]
    length = int(len(list(histogram.keys())[0]))
    qubit_hits = np.zeros((length, 2))

    for basis_state in histogram:
        for i in range(0, length):
            if basis_state[length - i - 1] == '0':
                qubit_hits[i][0] = qubit_hits[i][0] + histogram[basis_state]
            else:
                qubit_hits[i][1] = qubit_hits[i][1] + histogram[basis_state]

    return qubit_hits


def Task_0qfiqux_calculate_qubits_0_hits(histogram):
    # the length can be read out from the
    # string of any arbitrary (e.g. the 0th) bitstring
    length = int(len(list(histogram.keys())[0]))
    hits = np.zeros(length)

    qubit_hits_map = Task_0qfiqux_map_histogram_to_qubit_hits(histogram)
    for i in range(0, int(qubit_hits_map.shape[0])):
        hits[i] = int(qubit_hits_map[i][0])

    return hits


def Task_0qfiqux_calculate_cluster_mapping(amount_of_data, k, distances):
    cluster_mapping = np.zeros(amount_of_data)
    for i in range(0, amount_of_data):
        lowest_distance = distances[i * k + 0]
        lowest_distance_centroid_index = 0
        for j in range(1, k):
            if distances[i * k + j] < lowest_distance:
                lowest_distance_centroid_index = j
        cluster_mapping[i] = lowest_distance_centroid_index

    return cluster_mapping


def Task_0qfiqux_execute_negative_rotation_clustering(circuits, k, backend, shots_per_circuit):
    # this is the amount of qubits that are needed in total
    # and also the amount of distances, i.e. every data point
    # to every centroid
    global_work_amount = 0
    for quantum_circuit in circuits:
        global_work_amount += quantum_circuit.num_qubits

    # store some general information about the data
    amount_of_data = int(global_work_amount / k)

    # we store the distances as [(t1,c1), (t1,c2), ..., (t1,cn), (t2,c1), ..., (tm,cn)]
    # while each (ti,cj) stands for one distance, i.e. (ti,cj) = distance data point i
    # to centroid j
    distances = np.zeros(global_work_amount)

    # this is the index to iterate over all parameter pairs in the queue (parameters list)
    index = 0

    for quantum_circuit in circuits:
        # track the parameter pairs we will check within each circuit
        index += quantum_circuit.num_qubits

        # execute on IBMQ backend
        transpiled_circuit = transpile(quantum_circuit, backend)
        job = backend.run(transpiled_circuit)

        # store the result for this sub circuit run
        histogram = job.result().get_counts()
        hits = Task_0qfiqux_calculate_qubits_0_hits(histogram)

        # We will assign the data point to the centroid
        # with more 0 hits. E.g. if k = 2 we have hits
        # for the comparison with the first and second
        # centroid. The higher the hits, the closer we
        # are, i.e. the lower the distance. I.e. the
        # hit amount is anti proportional to the distance.
        # Hence, we add a small amount to each hit (to avoid
        # zero division) and take the inverse of it and
        # let the super class calculate the mapping, which
        # will assign to the centroid with minimal distance.
        safe_delta = 50
        for i in range(0, hits.shape[0]):
            distances[index - quantum_circuit.num_qubits + i] = 1.0 / (hits[i] + safe_delta)

    # calculate the new cluster mapping
    cluster_mapping = Task_0qfiqux_calculate_cluster_mapping(amount_of_data, k, distances)

    return cluster_mapping


def Task_0qfiqux_execute(circuits_string, ibmq_token, ibmq_backend, backend4):
    print('Executing K-Means circuits...')

    # retrieve IBMQ backend object
    backend = backend4

    # retrieve circuits from the string representation
    circuits_strings = circuits_string.split('##########')
    circuits = []
    for circuit_string in circuits_strings:
        circuits.append(QuantumCircuit.from_qasm_str(circuit_string))

    # execute the circuits and retrieve the cluster mappings
    print('Executing circuits: ', len(circuits))
    cluster_mapping = Task_0qfiqux_execute_negative_rotation_clustering(circuits, 2, backend, 1024)

    return str(json.dumps(cluster_mapping.tolist()))


def Task_0lg77kd_text_to_array(text):
    text_lines = list(filter(None, text.split("\n")))
    data_array = np.zeros(shape=(len(text_lines), 2))
    for idx, data_line in enumerate(text_lines):
        for idy, val2 in enumerate(data_line.split(" ")):
            data_array[idx][idy] = float(val2)
    return data_array


def Task_0lg77kd_standardize(data_to_standardize):
    data_x = np.zeros(data_to_standardize.shape[0])
    data_y = np.zeros(data_to_standardize.shape[0])
    preprocessed_data = np.zeros_like(data_to_standardize)

    # create x and y coordinate arrays
    for i in range(0, len(data_to_standardize)):
        data_x[i] = data_to_standardize[i][0]
        data_y[i] = data_to_standardize[i][1]

    # make zero mean and unit variance, i.e. standardize
    temp_data_x = (data_x - np.mean(data_x)) / np.std(data_x)
    temp_data_y = (data_y - np.mean(data_y)) / np.std(data_y)

    # create tuples to return
    for i in range(0, data_to_standardize.shape[0]):
        preprocessed_data[i][0] = temp_data_x[i]
        preprocessed_data[i][1] = temp_data_y[i]

    return preprocessed_data


def Task_0lg77kd_normalize(data_to_normalize):
    normalized_data = np.zeros_like(data_to_normalize)

    # create tuples and normalize
    for i in range(0, data_to_normalize.shape[0]):
        norm = sqrt(pow(data_to_normalize[i][0], 2) + pow(data_to_normalize[i][1], 2))
        normalized_data[i][0] = data_to_normalize[i][0] / norm
        normalized_data[i][1] = data_to_normalize[i][1] / norm

    return normalized_data


def Task_0lg77kd_centroids_to_array(centroids):
    centroids_list = centroids.replace("\n", "").split("] [")
    centroids_array = np.zeros(shape=(len(centroids_list), 2))
    for idx, centroid in enumerate(centroids_list):
        data_points = list(filter(None, centroid.replace("]", "").replace("[", "").split(" ")))
        for idy, data_point in enumerate(data_points):
            centroids_array[idx][idy] = float(data_point)
    return centroids_array


def Task_0lg77kd_calculate_centroids(cluster_mapping, old_centroids, data):
    # create empty arrays
    centroids = np.zeros_like(old_centroids)
    cluster_k = centroids.shape[0]

    for i in range(0, cluster_k):
        sum_x = 0
        sum_y = 0
        amount = 0
        for j in range(0, cluster_mapping.shape[0]):
            if cluster_mapping[j] == i:
                sum_x += data[j][0]
                sum_y += data[j][1]
                amount += 1

        # if no points assigned to centroid, take old coordinates
        if amount == 0:
            averaged_x = old_centroids[i][0]
            averaged_y = old_centroids[i][1]
        else:
            averaged_x = sum_x / amount
            averaged_y = sum_y / amount

        norm = sqrt(pow(averaged_x, 2) + pow(averaged_y, 2))
        centroids[i][0] = averaged_x / norm
        centroids[i][1] = averaged_y / norm

    return centroids


def Task_0lg77kd_calculate_euclidean_distance(first, second):
    norm = 0.0
    for i in range(0, first.shape[0]):
        norm += pow(first[i] - second[i], 2)
    return sqrt(norm)


def Task_0lg77kd_calculate_averaged_euclidean_distance(old_centroids, new_centroids):
    result = 0.0
    for i in range(0, old_centroids.shape[0]):
        result += Task_0lg77kd_calculate_euclidean_distance(old_centroids[i], new_centroids[i])
    return result / old_centroids.shape[0]


def Task_0lg77kd_execute(cluster_mapping, data, centroids, iterations):
    print('Calculating new centroids...')

    # calculate new centroids based on the circuit execution results
    cluster_mapping_list = np.array(json.loads(cluster_mapping))
    data_array = Task_0lg77kd_text_to_array(data)
    standardized_data = Task_0lg77kd_standardize(data_array)
    normalized_data = Task_0lg77kd_normalize(standardized_data)
    old_centroids_array = Task_0lg77kd_centroids_to_array(centroids)
    old_centroids_standardized = Task_0lg77kd_standardize(old_centroids_array)
    old_centroids = Task_0lg77kd_normalize(old_centroids_standardized)
    new_centroids = Task_0lg77kd_calculate_centroids(cluster_mapping_list, old_centroids, normalized_data)

    # calculate distance between new and old centroids
    distance = Task_0lg77kd_calculate_averaged_euclidean_distance(old_centroids, new_centroids)

    # check convergence
    iterations = int(iterations) + 1
    clusteringConverged = (distance < 0.1) | (iterations > 10)
    clusteringConverged = str(clusteringConverged).lower()

    return str(clusteringConverged), str(new_centroids), str(iterations)

def Task_11jwstv_text_to_array(text):
    text_lines = list(filter(None, text.split("\n")))
    data_array = np.zeros(shape=(len(text_lines), 2))
    for idx, data_line in enumerate(text_lines):
        for idy, val2 in enumerate(data_line.split(" ")):
            data_array[idx][idy] = float(val2)
    return data_array


def Task_11jwstv_standardize(data_to_standardize):
    data_x = np.zeros(data_to_standardize.shape[0])
    data_y = np.zeros(data_to_standardize.shape[0])
    preprocessed_data = np.zeros_like(data_to_standardize)

    # create x and y coordinate arrays
    for i in range(0, len(data_to_standardize)):
        data_x[i] = data_to_standardize[i][0]
        data_y[i] = data_to_standardize[i][1]

    # make zero mean and unit variance, i.e. standardize
    temp_data_x = (data_x - np.mean(data_x)) / np.std(data_x)
    temp_data_y = (data_y - np.mean(data_y)) / np.std(data_y)

    # create tuples to return
    for i in range(0, data_to_standardize.shape[0]):
        preprocessed_data[i][0] = temp_data_x[i]
        preprocessed_data[i][1] = temp_data_y[i]

    return preprocessed_data


def Task_11jwstv_normalize(data_to_normalize):
    normalized_data = np.zeros_like(data_to_normalize)

    # create tuples and normalize
    for i in range(0, data_to_normalize.shape[0]):
        norm = sqrt(pow(data_to_normalize[i][0], 2) + pow(data_to_normalize[i][1], 2))
        normalized_data[i][0] = data_to_normalize[i][0] / norm
        normalized_data[i][1] = data_to_normalize[i][1] / norm

    return normalized_data


def Task_11jwstv_centroids_to_array(centroids):
    centroids_list = centroids.replace("\n", "").split("] [")
    centroids_array = np.zeros(shape=(len(centroids_list), 2))
    for idx, centroid in enumerate(centroids_list):
        data_points = list(filter(None, centroid.replace("]", "").replace("[", "").split(" ")))
        for idy, data_point in enumerate(data_points):
            centroids_array[idx][idy] = float(data_point)
    return centroids_array


def Task_11jwstv_calculate_angles(cartesian_points, base_vector):
    angles = np.zeros(cartesian_points.shape[0])
    for i in range(0, angles.shape[0]):
        angles[i] = acos(base_vector[0] * cartesian_points[i][0] + base_vector[1] * cartesian_points[i][1])

    return angles


def Task_11jwstv_generate_negative_rotation_clustering(max_qubits, data_angles, centroid_angles):
    # store a list of quantum circuits
    circuits = []

    # this is also the amount of qubits that are needed in total
    global_work_amount = centroid_angles.shape[0] * data_angles.shape[0]

    # create tuples of parameters corresponding for each qubit,
    # i.e. create [[t1,c1], [t1,c2], ..., [t1,cn], [t2,c1], ..., [tm,cn]]
    # now with ti = data_angle_i and cj = centroid_angle_j
    parameters = []
    for i in range(0, data_angles.shape[0]):
        for j in range(0, centroid_angles.shape[0]):
            parameters.append((data_angles[i], centroid_angles[j]))

    # this is the index to iterate over all parameter pairs in the queue (parameters list)
    index = 0
    queue_not_empty = True

    # create the circuit(s)
    while queue_not_empty:
        max_qubits_for_circuit = global_work_amount - index

        if max_qubits < max_qubits_for_circuit:
            qubits_for_circuit = max_qubits
        else:
            qubits_for_circuit = max_qubits_for_circuit

        qc = QuantumCircuit(qubits_for_circuit, qubits_for_circuit)

        for i in range(0, qubits_for_circuit):
            # test_angle rotation
            qc.ry(parameters[index][0], i)

            # negative centroid_angle rotation
            qc.ry(-parameters[index][1], i)

            # measure
            qc.measure(i, i)

            index += 1
            if index == global_work_amount:
                queue_not_empty = False
                break

        circuits.append(qc)

    return circuits


def Task_11jwstv_execute(centroids, data):
    print('Adapting K-Means circuits...')

    # calculate angles of base data points and centroids
    print('Calculating angles...')
    base_vector = np.array([0.7071, 0.7071])
    data_array = Task_11jwstv_text_to_array(data)
    standardized_data = Task_11jwstv_standardize(data_array)
    normalized_data = Task_11jwstv_normalize(standardized_data)
    old_centroids_array = Task_11jwstv_centroids_to_array(centroids)
    old_centroids_standardized = Task_11jwstv_standardize(old_centroids_array)
    old_centroids = Task_11jwstv_normalize(old_centroids_standardized)
    data_angles = Task_11jwstv_calculate_angles(normalized_data, base_vector)
    centroid_angles = Task_11jwstv_calculate_angles(old_centroids, base_vector)

    # generate the quantum circuits for a QPU with 5 qubits
    print('Generating circuits...')
    circuits = Task_11jwstv_generate_negative_rotation_clustering(5, data_angles, centroid_angles)
    circuits_string = '##########\n'.join([circuit.qasm() for circuit in circuits])

    return str(circuits_string)


