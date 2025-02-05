from redbaron import RedBaron
from app import app

def is_empty(block):
    app.logger.info("block is not empty")
    app.logger.info(block)
    # Define the lines to skip
    # Define the lines to skip
    linesToSkip = ["user_messenger"]
    
    # Filter out lines that contain any content from linesToSkip
    def should_skip(line):
        app.logger.info(line)
        for skip_content in linesToSkip:
            app.logger.info(skip_content)
            app.logger.info(line.dumps())
            if skip_content in line.dumps():
                return True
        return False

    filtered_lines = [line for line in block["lines"] if not should_skip(line)]
    
    if len(filtered_lines) == 0:
        return True
    else:
        for line in filtered_lines:
            app.logger.info("line in block")
            app.logger.info(line)
            if line.type != "endl":
                return False
        return True


def get_wf_type(part_name):
    app.logger.info("part name")
    app.logger.info(part_name)
    app.logger.info(part_name.lower())
    if "classical" in part_name.lower():
        app.logger.info("write part name")
        return "bpmn:ServiceTask", "Update Variables"
    elif "circuit" in part_name.lower() and "generation" in part_name.lower():
        return "quantme:QuantumCircuitLoadingTask", "Generate Circuit"
    elif "circuit" in part_name.lower() and "exec" in part_name.lower():
        return "quantme:QuantumCircuitExecutionTask", "Execute Circuit"
    elif "result" in part_name.lower() and "eval" in part_name.lower():
        return "quantme:ResultEvaluationTask", "Evaluate Results"
    elif "parameter" in part_name.lower() and "optimiz" in part_name.lower():
        return "quantme:ParameterOptimizationTask", "Optimize Parameters"
    print("Unknown QuantME type: " + part_name)
    return part_name, ""


id_counter = 1


def add_ids(codeblock):
    if codeblock['type'] == "wrapper":
        for block in codeblock["blocks"]:
            add_ids(block)
    elif codeblock['type'] == "block":
        global id_counter
        codeblock['id'] = codeblock['name'] + '_' + str(id_counter)
        id_counter += 1

def get_vars(node):
    variables = []
    if node.type == "name":
        if node.value not in variables:
            variables.append(node.value)
    elif node.type == "atomtrailers":
        if node.value[1].type == 'call':
            for x in node.value[1].value:
                variables.extend(get_vars(x))
        elif node.value[1].type == "getitem":
            for x in node.value:
                variables.extend(get_vars(x))
    elif node.type == "call_argument":
        variables.extend(get_vars(node.value))
    elif node.type == "getitem":
        variables.extend(get_vars(node.value))
    elif node.type == "dict":
        for x in node.value:
            variables.extend(get_vars(x.value))
    elif node.type == "comparison" or node.type == "binary_operator":
        variables.extend(get_vars(node.first))
        variables.extend(get_vars(node.second))
    elif node.type == "unitary_operator":
        variables.extend(get_vars(node.target.first))
        variables.extend(get_vars(node.target.second))
    return variables


def get_params(lines):
    return_variables = []
    unknown_variables = []
    for line in lines:
        # e.g., iterations = kwargs["iterations"]
        # e.g., currentIteration = currentIteration + 1
        if line.type == "assignment":
            right_hand_side = line.value
            variables = get_vars(right_hand_side)
            unknown_variables.extend(
                x for x in variables if x not in unknown_variables and x not in return_variables and x != "kwargs" and x != "user_messenger"
            )
            left_hand_side = line.target
            print(left_hand_side)
            if left_hand_side.type == "name":
                print("name")
                print(left_hand_side)
                if left_hand_side.value not in return_variables:
                    return_variables.append(left_hand_side.value)
            elif left_hand_side.type == "tuple":
                print("tuple")
                print(left_hand_side.value)
                for var in left_hand_side.value:
                    if var.value not in return_variables:
                        return_variables.append(var.value)
        # e.g., user_messenger.publish(serialized_result, final=True)
        elif line.type == "atomtrailers":
            print("todo: compute parameters for the following:   ", line.dumps())
    return return_variables, unknown_variables


def compute_variables(block):
    if 'type' not in block:
        return
    if block['type'] == "wrapper":
        for b in block['blocks']:
            compute_variables(b)
    elif block['type'] == "block":
        return_variables, params = get_params(block['lines'])
        block['return_variables'] = return_variables
        block['parameters'] = params
    elif block['type'] in ["start_while", "break"]:
        condition = RedBaron(block['condition'])
        print("compute variables")
        app.logger.info("compute variables")
        app.logger.info(condition[0])
        print(condition[0])
        params = get_vars(condition[0])
        block['parameters'] = params

class ScriptAnalyzer:

    result = []

    def __init__(self, codeblock):
        # Find the assignment to `serialized_result`
        app.logger.info("init script analyzer")
        for node in codeblock.find_all('AssignmentNode'):

            print("assignment node")
            print(node)
            if node.target.value == 'serialized_result':
                node.parent.remove(node)
                break
        self.result = self.get_blocks(codeblock, "root")
        add_ids(self.result)
        main_arguments = []
        
        for argument in codeblock.arguments.find_all('name'):
            print(argument.value)
            if argument.value != "kwargs":
                print("add argument")
                main_arguments.append(argument.value)
        self.result['parameters'] = main_arguments
        print(main_arguments)

        compute_variables(self.result)

    def get_result(self):
        return self.result

    def get_blocks(self, codeblock, name):
        result_wrapper = {"name": name, "type": "wrapper", "blocks": []}
        current_block = {"name": "init", "label": "Current", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
        for line in codeblock:
            print("processing line")
            print(line)
            if line.type == 'comment' and "# SPLIT" in line.value:
                if not is_empty(current_block):
                    print("create block split")
                    result_wrapper["blocks"].append(current_block.copy())
                if line.value[9:]:
                    part_name = line.value[9:].replace(" ", "")
                    wf_type, label = get_wf_type(line.value[9:])
                    print("create block quantme")
                    current_block = {"name": part_name, "label": label, "type": "block", "wf_type": wf_type, "lines": []}
                else:
                    print("create block empty")
                    # current_block = {"name": "next", "label": "Update Variables", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
            elif line.type == 'while':
                if not is_empty(current_block):
                    result_wrapper["blocks"].append(current_block.copy())
                current_block = {"name": "next", "label": "Update Variables", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
                while_block = self.get_blocks(line, 'while_wrapper')
                while_block["condition"] = line.test.dumps()
                print("condition")
                print(line.test.dumps())
                result_wrapper["blocks"].append(while_block)
            elif line.type == 'for':
                if not is_empty(current_block):
                    result_wrapper["blocks"].append(current_block.copy())
                current_block = {"name": "next", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
                for_block = self.get_blocks(line, 'for_wrapper')
                for_block["condition"] = line.target.dumps()
                result_wrapper["blocks"].append(for_block)
            elif line.type == 'pass':
                pass
            elif line.type == 'ifelseblock':
                if len(line.value) == 1 and line.value[0].value[0].type == 'break':
                    if not is_empty(current_block):
                        result_wrapper["blocks"].append(current_block.copy())
                    #break_block = {"name": "break", "label": "BREAk", "type": "break", "condition": line.value[0].test.dumps()}
                    #result_wrapper["blocks"].append(break_block)
                    #current_block = {"name": "next", "label": "Update Variables", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
            else:
                print("add lines to block")
                print(current_block)
                current_block["lines"].append(line)
        if not is_empty(current_block):
            result_wrapper["blocks"].append(current_block)
        return result_wrapper