import json
import ast


def table_parser(raw_data):
    try:
        lines = raw_data.split("\n")
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line != ""]
        lines = [line for line in lines if "|" in line]

        headers = lines[0].split("|")
        values = [line.split("|") for line in lines[2:]]
        
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
                item[v.lower()] = value[j]
            if not finished_early:
                new_content.append(item)
    except Exception as e:
        print("****", e)
        return None

    return new_content


def json_parser(raw_data):
    raw_data = raw_data[raw_data.find("{"):]
    raw_data = raw_data[:raw_data.rfind("}")+1]

    try:
        json_obj = json.loads(raw_data)
    except Exception as e:
        print(f"Cannot parse directly as JSON: {e}")

        try:
            json_dict = ast.literal_eval(raw_data)
            json_str = json.dumps(json_dict, indent=2)
            json_obj = json.loads(json_str)
        except Exception as e:
            print(f"Cannot eval as dict: {e}")
            return None

    return json_obj
