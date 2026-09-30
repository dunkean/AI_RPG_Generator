import ast
import json
import re


def parse_table(raw_data):
    try:
        lines = raw_data.split("\n")
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line != ""]
        lines = [line for line in lines if "|" in line]

        headers = lines[0].split("|")
        values = [line.split("|") for line in lines[2:]]
        # print(values)
        
        for i, header in enumerate(headers):
            headers[i] = header.strip()
        headers = headers[1:-1]
        for i, value in enumerate(values):
            for j, v in enumerate(value):
                values[i][j] = v.strip()
        values = [value[1:-1] for value in values]
        new_content = []
        finished_early = False
        for k, value in enumerate(values):
            item = {}
            for j, v in enumerate(headers):
                # if len(value) <= j and k >= len(values) - 1:
                #     print("Table finished early - repairing")
                #     finished_early = True
                #     break
                val = value[j]
                if val[0] == "[" or val[0] == "{":
                    val = parse_json(val)
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass

                item[v.lower()] = val
            if not finished_early:
                new_content.append(item)
    except Exception as e:
        print("****", e)
        return None

    return new_content


def strip_json_comments(json_text):
    # Use regular expressions to remove comments from the JSON text
    pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
    stripped_text = re.sub(pattern, lambda m: m.group(1) if m.group(1) else '', json_text, flags=re.MULTILINE)

    return stripped_text


def parse_json(raw_data):
    raw_data = strip_json_comments(raw_data)
    raw_data = raw_data[raw_data.find("{"):]
    raw_data = raw_data[:raw_data.rfind("}") + 1]

    try:
        json_obj = json.loads(raw_data)
    except Exception as e:
        # log error
        # print(f"Cannot parse directly as JSON: {e}")
        pass

        try:
            json_dict = ast.literal_eval(raw_data)
            json_str = json.dumps(json_dict, indent=2)
            json_obj = json.loads(json_str)
        except Exception as e:
            # log error
            # print(f"Cannot eval as dict: {e}")
            return None

    return json_obj
