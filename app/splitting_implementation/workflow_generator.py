class WorkflowJson:
    last_element_id = None
    gateway_counter = 1
    break_id = None
    wf_result = []
    sequence_flows = []

    def add_start(self, parameters):
        self.wf_result.append({"id": "StartEvent_1", "type": "bpmn:StartEvent", "parameters": parameters})
        self.last_element_id = "StartEvent_1"

    def append_sequence_flow(self, target_ref):
        self.add_sequence_flow(self.last_element_id, target_ref)

    def add_sequence_flow(self, source_ref, target_ref, condition=None):
        sequence_flow = {
            "type": "bpmn:SequenceFlow",
            "sourceRef": source_ref,
            "targetRef": target_ref,
            "label": ""
        }
        if condition is not None:
            sequence_flow["condition"] = condition.replace("and", "&&")
            sequence_flow["label"] = "Yes"
        self.sequence_flows.append(sequence_flow)

    def add_end(self):
        self.wf_result.append({"id": "EndEvent_1", "type": "bpmn:EndEvent"})
        self.append_sequence_flow(target_ref="EndEvent_1")

    def append_with_sequence_flow(self, block):
        print("APPEND")
        print(block["id"])
        print(block["return_variables"])
        if(block["return_variables"] != []):
            self.wf_result.append({
                "type": block["wf_type"],
                "id": block["id"],
                "label": block.get("label", ""),
                "file": f"{block['id']}",
                "return_variables": block['return_variables'],
                "parameters": block['parameters']
            })
            self.append_sequence_flow(target_ref=block['id'])
            self.last_element_id = block["id"]

    def add_while(self, inner_block):
        first = f"ExclusiveGateway_{self.gateway_counter}"
        second = f"Gateway_{self.gateway_counter+1}"
        third = f"Gateway_{self.gateway_counter + 2}"
        self.gateway_counter += 2

        self.wf_result.append({"id": first, "label": "", "type": "bpmn:ExclusiveGateway"})
        self.append_sequence_flow(first)

        self.last_element_id = first
        self.break_id = third

        for x in inner_block["blocks"]:
            self.generate_wf(x)

        
        conditionExpression = inner_block['condition'].replace("and", "&&")
        self.wf_result.append({"id": second, "type": "bpmn:ExclusiveGateway", "label": "", "condition": "${" + conditionExpression + "}"})
        self.append_sequence_flow(second)
        #self.wf_result.append({"id": third, "type": "bpmn:ExclusiveGateway"})
        self.add_sequence_flow(second, first, "${" + inner_block['condition'] + "}")
        # negation of the loop condition
        #self.add_sequence_flow(second, third, "${!(" + inner_block['condition'] + ")}")

        self.last_element_id = second
        self.break_id = None

    def add_break(self, block):
        self.wf_result.append({
            "id": "ExclusiveGateway_break",
            "condition": block['condition'],
            "type": "bpmn:ExclusiveGateway"}
        )
        self.append_sequence_flow("ExclusiveGateway_break")
        self.add_sequence_flow("ExclusiveGateway_break", self.break_id, "True")
        self.last_element_id = "ExclusiveGateway_break"

    def generate_wf(self, block):
        print(block)
        if block["name"] == "root":
            self.add_start(block['parameters'])
            for x in block["blocks"]:
                self.generate_wf(x)
            self.add_end()
        elif block["type"] == "wrapper":
            self.add_while(block)
        elif block["type"] == "block":
            print(block["lines"])
            self.append_with_sequence_flow(block)
        elif block["type"] == "break":
            self.add_break(block)
        else:
            print("xxxxxx not handled")
        return

    def get_result(self):
        result = self.wf_result
        result.extend(self.sequence_flows)
        return result

    def __init__(self, block):
        self.generate_wf(block)
