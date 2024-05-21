import os
from app.splitting_implementation.polling_agent_generator import generate_polling_agent
from subprocess import PIPE, run
import zipfile
import tempfile
import shutil


def create_output(block):
    if 'parameters' in block:
        parameters = block["parameters"]
    else:
        parameters = []
    if 'return_variables' in block:
        return_variables = block["return_variables"]
    else:
        return_variables = []
    res = f'def main({", ".join(parameters)}):\n'
    for line in block["lines"]:
        if line.type == "endl":
            continue
        res += f"    {line.dumps()}\n"
    if len(block['return_variables']) > 0:
        res += f'    return {", ".join(return_variables)}\n'
    return res


def write_blocks(block, all_functions, imports, result):
    if block["type"] == "block":
        directory = f'output/{block["id"]}/service'
        if not os.path.exists(directory):
            os.makedirs(directory)

        fw = open(f'{directory}/app.py', 'w')
        #for imp in imports:
         #   fw.write(imp.dumps())
          #  fw.write('\n')

        #fw.write(create_output(block))
        #fw.write('\n')
        #fw.write(all_functions.dumps())
        #fw.close()

        pa_writer = open(f'{directory}/polling_agent.py', 'w')
        polling_agent = generate_polling_agent(block['parameters'], block['return_variables'])
        pa_writer.write(polling_agent)
        templatesDirectory = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))),
                                      'templates')
        startingPointTemp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        print("Working on block")
        print(block["id"])
        with open(startingPointTemp.name, "w") as starting_point2:
            
            for imp in imports:
                starting_point2.write(imp.dumps())
                starting_point2.write('\n')
            starting_point2.write(create_output(block))
            starting_point2.write('\n')
            starting_point2.write(all_functions.dumps())
            path = os.path.join(templatesDirectory, startingPointTemp.name)
            command = ["deadcode", path, "--ignore-names", "main", "--fix"]
            for i in range(10):
                cli_output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
                if "Well done!" in cli_output.stdout:
                    break
            print("generated app.py for ")
            print(startingPointTemp.name)

        result.program = zip_polling_agent("", polling_agent, startingPointTemp, block["id"])
        dockerfile_reader = open(os.path.join(templatesDirectory, 'Dockerfile'), "r")
        dockerfile_writer = open(f'output/{block["id"]}/Dockerfile', 'w')
        dockerfile_writer.write(dockerfile_reader.read())

    elif block["type"] == "wrapper":
        for block in block["blocks"]:
            write_blocks(block, all_functions, imports, result)


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
    #shutil.copy(starting_point.name, os.path.join(temp_folder_path, 'app.py'))

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
    # Get the path to the existing zip file or create a new one if it doesn't exist
    polling_agent_wrapper_path = f'../polling_agent_wrapper.zip'
    if os.path.exists(polling_agent_wrapper_path):
        mode = 'a'  # Append mode
    else:
        mode = 'w'  # Write mode

    # Create a folder with the script_id name
    script_folder_name = f"{script_id}/"

    # Open the zip file in the appropriate mode
    with zipfile.ZipFile(polling_agent_wrapper_path, mode) as zipObj:
        # Add Dockerfile and requirements.txt from templates directory if they don't exist
        if 'Dockerfile' not in zipObj.namelist():
            zipObj.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
        if 'requirements.txt' not in zipObj.namelist():
            zipObj.write(os.path.join(templatesDirectory, 'requirements.txt'), 'requirements.txt')
        
        zipObj.write(starting_point.name, f"{script_folder_name}app.py")
        
        # Create a new ZipFile object to hold the hybrid program
        with zipfile.ZipFile('../hybrid_program.zip', 'w') as zipObj2:
            # Add the starting_point file as 'hybrid_program.py'
            zipObj2.write(starting_point.name, 'hybrid_program.py')
            # Write polling agent code to a temporary file and add it to the zip
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as polling_temp:
                polling_temp.write(polling_agent.encode())
                zipObj2.write(polling_temp.name, f"{script_folder_name}polling_agent.py")
        
        # Add the hybrid program zip file to the main zip file
        zipObj.write('../hybrid_program.zip', f"{script_folder_name}hybrid_program.zip")

    # Read the updated zip file and return its content
    with open(polling_agent_wrapper_path, "rb") as zipFile:
        zip_content = zipFile.read()

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
    zipObj.write(os.path.join(templatesDirectory, 'Dockerfile'), 'Dockerfile')
    zipObj = open('../polling_agent_wrapper.zip', "rb")
    return zipObj.read()