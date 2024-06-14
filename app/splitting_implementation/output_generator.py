import os
from app.splitting_implementation.polling_agent_generator import generate_polling_agent
from subprocess import PIPE, run
import zipfile
import tempfile
import shutil
from app import app

def create_output(block):
    if 'parameters' in block:
        parameters = block["parameters"]
    else:
        parameters = []
        app.logger.info("check and return")

    if 'return_variables' in block:
        return_variables = block["return_variables"]
    else:
        return_variables = []

    res = f'def main({", ".join(parameters)}):\n'

    # Keep track of return variables to be excluded
    excluded_return_variables = []

    for line in block["lines"]:
        if line.type == "endl":
            continue
        line_content = line.dumps()
        # Skip lines containing "kwargs" or "user_messenger" and note the variables to exclude
        if "kwargs" in line_content or "user_messenger" in line_content:
            # Check if this line sets a return variable
            for var in return_variables:
                if var in line_content:
                    excluded_return_variables.append(var)
            continue
        res += f"    {line_content}\n"

    # Filter out excluded return variables
    filtered_return_variables = [var for var in return_variables if var not in excluded_return_variables]

    if len(filtered_return_variables) > 0:
        res += f'    return {", ".join(filtered_return_variables)}\n'
    if len(filtered_return_variables) == 0 and len(parameters) == 0:
        return None

    return res

def write_blocks(pythonfile, requirementsfile, block, all_functions, imports, result):
    if block["type"] == "block":
        if create_output(block) == None:
            app.logger.info(f"Skipping block as it has no body")
            app.logger.info(block["id"])
            return

    if block["type"] == "block":
        directory = f'output/{block["id"]}/service'
        if not os.path.exists(directory):
            os.makedirs(directory)

        fw = open(f'{directory}/app.py', 'w')
        pa_writer = open(f'{directory}/polling_agent.py', 'w')
        polling_agent = generate_polling_agent(block, block['parameters'], block['return_variables'])
        pa_writer.write(polling_agent)
        templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                          'templates')
        startingPointTemp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        print("Working on block")
        print(block["id"])
        try:
            with open(startingPointTemp.name, "w") as starting_point2:
                for imp in imports:
                    print("imp")
                    print(imp)
                    starting_point2.write(imp.dumps())
                    starting_point2.write('\n')
                starting_point2.write(create_output(block))
                starting_point2.write('\n')
                starting_point2.write(all_functions.dumps())
                
            # Ensure the file is properly closed
            starting_point2.close()

            # Print the content of the startingPointTemp file
            with open(startingPointTemp.name, "r") as sp_file:
                print("Content of startingPointTemp:")
                print(sp_file.read())

            path = os.path.join(templatesDirectory, startingPointTemp.name)
            command = ["deadcode", path, "--ignore-names", "main", "--fix"]
            for i in range(10):
                cli_output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
                if "Well done!" in cli_output.stdout:
                    break
            print("generated app.py for ")
            print(startingPointTemp.name)

            result.program = zip_polling_agent(requirementsfile, polling_agent, startingPointTemp, block["id"])
        finally:
            # Ensure the temporary file is deleted after use
            os.remove(startingPointTemp.name)
        
        dockerfile_reader = open(os.path.join(templatesDirectory, 'Dockerfile'), "r")
        dockerfile_writer = open(f'output/{block["id"]}/Dockerfile', 'w')
        dockerfile_writer.write(dockerfile_reader.read())

    elif block["type"] == "wrapper":
        for sub_block in block["blocks"]:
            write_blocks(pythonfile, requirementsfile, sub_block, all_functions, imports, result)

def zip_folder(folder_path, starting_point, zipObj, script_folder_name):
    # Create a temporary directory to store the files inside the folder
    temp_dir = tempfile.TemporaryDirectory()
    temp_folder_path = temp_dir.name

    # Copy all files and directories from the original folder to the temporary directory
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            print(file_path)
            relative_path = os.path.relpath(file_path, folder_path)
            target_path = os.path.join(temp_folder_path, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy(file_path, target_path)

    # Write the app.py file to the temporary directory
    # shutil.copy(starting_point.name, os.path.join(temp_folder_path, 'app.py'))

    # Zip the temporary directory
    service_zip_path = os.path.join(temp_folder_path, 'service.zip')
    shutil.make_archive(service_zip_path[:-4], 'zip', temp_folder_path)

    # Add the resulting zip file to the main zip archive
    zipObj.write(service_zip_path, f"{script_folder_name}service.zip")

    # Clean up the temporary directory
    temp_dir.cleanup()

def zip_polling_agent(requirements, polling_agent, starting_point, script_id):
    templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'templates')
    polling_agent_wrapper_path = f'../polling_agent_wrapper.zip'
    if os.path.exists(polling_agent_wrapper_path):
        mode = 'a'  # Append mode
    else:
        mode = 'w'  # Write mode

    script_folder_name = f"{script_id}/"
    
    # Log the starting point file
    print("STARTING POINT:", starting_point.name)

    service_zip_path = '../service.zip'
    try:
        with zipfile.ZipFile(service_zip_path, 'w') as zipObj1:
            # Write polling agent code to a temporary file and add it to the zip
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as polling_temp:
                polling_temp.write(polling_agent.encode())
                zipObj1.write(polling_temp.name, 'polling_agent.py')

            # Add the starting_point file as 'app.py'
            if os.path.exists(starting_point.name):
                zipObj1.write(starting_point.name, 'app.py')
            else:
                raise FileNotFoundError(f"Starting point file {starting_point.name} not found")

            # Add the requirements file
            with open(os.path.join(templatesDirectory, 'requirements.txt'), 'rb') as requirements_file:
                zipObj1.writestr('requirements.txt', requirements_file.read())
    except Exception as e:
        print(f"Error creating service.zip: {e}")
        raise

    second_service_zip_path = '../second_service.zip'
    try:
        with zipfile.ZipFile(second_service_zip_path, 'w') as zipObj2:
            # Add the first service.zip
            zipObj2.write(service_zip_path, 'service.zip')

            # Add the Dockerfile
            zipObj2.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
    except Exception as e:
        print(f"Error creating second_service.zip: {e}")
        raise

    try:
        with zipfile.ZipFile(polling_agent_wrapper_path, mode) as zipObj:
            # Add the second service.zip to the main zip file
            zipObj.write(second_service_zip_path, f"{script_folder_name}service.zip")
    except Exception as e:
        print(f"Error creating polling_agent_wrapper.zip: {e}")
        raise

    try:
        with open(polling_agent_wrapper_path, "rb") as zipFile:
            zip_content = zipFile.read()
    except Exception as e:
        print(f"Error reading polling_agent_wrapper.zip: {e}")
        raise

    print("Zip polling agent")
    return zip_content


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
    #zipObj.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
    zipObj = open('../polling_agent_wrapper.zip', "rb")
    return zipObj.read() 
