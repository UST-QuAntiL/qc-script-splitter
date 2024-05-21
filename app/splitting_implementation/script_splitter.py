import sys

from redbaron import RedBaron
import json
from workflow_generator import WorkflowJson
from script_analyzer import ScriptAnalyzer
from output_generator import write_blocks


def do_the_split(red):
    all_but_main = red.findAll("DefNode", name=lambda n: n != "main")
    main_function = red.findAll("DefNode", name=lambda n: n == "main")[0]
    all_imports = red.findAll("import")

    scripts_analyzer = ScriptAnalyzer(main_function)
    result = scripts_analyzer.get_result()

    write_blocks(result, all_but_main, all_imports)

    foobar = WorkflowJson(result)
    wf_result = foobar.get_result()
    wf_json_writer = open("output/workflow.json", "w")
    wf_json_writer.write(json.dumps(wf_result, indent=4))
    print(json.dumps(wf_result))
    return wf_result


if __name__ == "__main__":
    in_path = "input/hybrid_program_kmeans.py"
    f = open(in_path, "r")
    result = do_the_split(RedBaron(f.read()))
    print(json.dumps(result))
