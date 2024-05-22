from redbaron import RedBaron

def is_empty(block):
    if len(block["lines"]) == 0:
        return True
    else:
        for line in block["lines"]:
            if line.type != "endl":
                return False
        return True


def get_wf_type(part_name):
    if "circuit" in part_name.lower() and "exec" in part_name.lower():
        return "quantme:QuantumCircuitExecutionTask"
    elif "result" in part_name.lower() and "eval" in part_name.lower():
        return "quantme:ResultEvaluationTask"
    elif "parameter" in part_name.lower() and "optimiz" in part_name.lower():
        return "quantme:ParameterOptimizationTask"
    print("Unknown QuantME type: " + part_name)
    return part_name


id_counter = 1


def add_ids(codeblock):
    if codeblock['type'] == "wrapper":
        for block in codeblock["blocks"]:
            add_ids(block)
    elif codeblock['type'] == "block":
        global id_counter
        codeblock['id'] = str(id_counter) + '_' + codeblock['name']
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
        params = get_vars(condition[0])
        block['parameters'] = params


class ScriptAnalyzer:

    result = []

    def __init__(self, codeblock):
        self.result = self.get_blocks(codeblock, "root")
        add_ids(self.result)
        main_arguments = []
        for argument in codeblock.arguments.find_all('name'):
            print(argument.value)
            if argument.value != "kwargs":
            #and argument.value != "user_messenger":
                print("add argument")
                main_arguments.append(argument.value)
        self.result['parameters'] = main_arguments
        print(main_arguments)
        compute_variables(self.result)

    def get_result(self):
        return self.result

    def get_blocks(self, codeblock, name):
        result_wrapper = {"name": name, "type": "wrapper", "blocks": []}
        current_block = {"name": "init", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
        for line in codeblock:
            print(codeblock)
            print("linie")
            print(line)
            if line.type == 'comment' and "# SPLIT" in line.value:
                if not is_empty(current_block):
                    result_wrapper["blocks"].append(current_block.copy())
                if line.value[9:]:
                    part_name = line.value[9:].replace(" ", "_")
                    wf_type = get_wf_type(line.value[9:])
                    current_block = {"name": part_name, "type": "block", "wf_type": wf_type, "lines": []}
                else:
                    current_block = {"name": "next", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
            elif line.type == 'while':
                if not is_empty(current_block):
                    result_wrapper["blocks"].append(current_block.copy())
                current_block = {"name": "next", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
                while_block = self.get_blocks(line, 'while_wrapper')
                while_block["condition"] = line.test.dumps()
                result_wrapper["blocks"].append(while_block)
            elif line.type == 'pass':
                pass
            elif line.type == 'ifelseblock':
                if len(line.value) == 1 and line.value[0].value[0].type == 'break':
                    if not is_empty(current_block):
                        result_wrapper["blocks"].append(current_block.copy())
                    break_block = {"name": "break", "type": "break", "condition": line.value[0].test.dumps()}
                    result_wrapper["blocks"].append(break_block)
                    current_block = {"name": "next", "type": "block", "wf_type": "bpmn:ServiceTask", "lines": []}
            else:
                current_block["lines"].append(line)
        if not is_empty(current_block):
            result_wrapper["blocks"].append(current_block)
        return result_wrapper