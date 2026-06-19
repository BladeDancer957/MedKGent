from collections import Counter
import os
import json

def transform2llm_realtions(vote_dict, entities_dict):

    # 转换字典1的每一项为所需格式
    output = []
    for key, confidence in vote_dict.items():
        # 分割三元组的key
        head_text, relation, tail_text = key.split(" | ")
        
        # 根据实体字典获取head和tail的详细信息
        head = next((value for key, value in entities_dict.items() if value['text'] == head_text), None)
        tail = next((value for key, value in entities_dict.items() if value['text'] == tail_text), None)
        
        # 添加到输出列表
        output.append({
            "head": head,
            "score": str(confidence),
            "type": relation,
            "tail": tail
        })

    return output


def process_vote(vote_dict, confidence_threshold):

    filtered_data = {key: value for key, value in vote_dict.items() if value > confidence_threshold}

    final_data = {}

    # Iterate through the original data
    for key, value in filtered_data.items():
        # Split the key into subject, relation, and object
        e1, r1, e2 = key.split(" | ")
        
        # Check if the reverse key exists
        reverse_key = f"{e2} | {r1} | {e1}"
        
        # If reverse_key exists, keep the one with the higher confidence
        if reverse_key in filtered_data:
            if filtered_data[reverse_key] <= value:
                final_data[key] = value
            else:
                final_data[reverse_key] =filtered_data[reverse_key]
        else:
            final_data[key] = value

    return final_data

def write_json(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def fetch_response(extractor_agent, system_message, user_message, model, temperature=0.7):
    # 调用get_response函数并获取第一个响应
    return extractor_agent.get_response(system_message, user_message, model, temperature)[0]

def vote(lst, n):
    vote_dict = {}
    for item in lst:
        if item in vote_dict:
            vote_dict[item] += 1
        else:
            vote_dict[item] = 1
    
    # 将计数除以n
    for key in vote_dict:
        vote_dict[key] /= n
        if vote_dict[key] == 1.0:
            vote_dict[key] = 0.95
    
    return vote_dict

def is_valid_response(response, entities, relations):
    # 去除多余的空格
    response = response.strip()

    # 判断条件1: response 为 "None"
    if response == "None":
        return False

    # 判断条件2: response 为 "A | B | C"
    if " | " in response:
        parts = response.split(" | ")
        if len(parts) == 3:
            A, B, C = parts
            if A !=  C and A in entities and C in entities and B in relations:
                return True

    # 判断条件3: response 为多个 "A | B | C" 三元组，用 $ 分隔
    triples = response.split(" $ ")
    seen = set()  # 用来检查重复的三元组
    for triple in triples:
        parts = triple.split(" | ")
        if len(parts) == 3:
            A, B, C = parts
            if A !=  C and A in entities and C in entities and B in relations:
                # 检查三元组是否重复
                if (A, B, C) in seen:
                    return False
                seen.add((A, B, C))
            else:
                return False  # 如果A、B、C不在对应列表中，返回False
        else:
            return False  # 如果不满足"A | B | C"格式，返回False

    # 如果通过所有条件
    return True

def generate_entity_string(entity_dict):
    # 用列表存储每个实体的字符串
    entity_strings1 = []
    entity_strings2 = []
    
    # 遍历字典中的每一项
    for entity in entity_dict.values():
        # 提取text, identifier 和 type，连接为一个字符串
        entity_string1 = f"{entity['text']} ｜ {entity['type']}"
        # 将这个字符串加入到列表
        entity_strings1.append(entity_string1)
        entity_strings2.append(entity['text'])
    
    # 用 ' ; ' 连接每一项
    result = ' ; '.join(entity_strings1)
    return result, entity_strings2


def deduplicate_entities(entities):
    # 创建一个字典，用于按 identifier 聚合实体
    result = {}

    for entity in entities:
        identifier = entity.get("identifier")
        entity_type = entity.get("type")
        
        # 如果该 identifier 不为空
        if identifier is not None and identifier != "-" and entity_type.lower() in ["disease", "chemical", "gene", "species", "variant", "cellline"]:
            # 如果这个 identifier 已经在字典中，合并 text 字段
            if identifier in result:
                # 获取当前的实体字典
                existing_entity = result[identifier]
                
                # 如果当前的 text 不在现有的 text 中，添加到括号内，并用逗号分隔
                if entity["text"] not in existing_entity["text"]:
                    existing_entity["text"] += f",{entity['text']}"  # 合并时确保用逗号分隔
            else:
                # 如果 identifier 不在字典中，直接加入
                result[identifier] = { 
                    "text": entity["text"],
                    "name": entity["name"],
                    "type": entity["type"],
                    "identifier": identifier,
                    "normalized_id": entity.get("normalized_id"),
                    "database": entity.get("database"),
                    "database_url": entity.get("database_url")
                }
    
    # 进一步整理 text 格式，确保只保留第一次出现的 text，然后其他的 text 放到括号中
    for identifier, entity in result.items():
        entity["text"] = entity["text"].split(',')[0] + f" ({', '.join(entity['text'].split(',')[1:])})" if ',' in entity['text'] else entity["text"]

    return result

def has_multiple_identifiers(json_data):
    # 获取所有非 null 的 identifier
    identifiers = set()
    
    for entity in json_data.get("entities", []):
        identifier = entity.get("identifier")
        entity_type = entity.get("type")
        if identifier is not None and identifier != "-" and entity_type.lower() in ["disease", "chemical", "gene", "species", "variant", "cellline"]:
            identifiers.add(identifier)
    
    # 判断是否至少有两个不同的有效 identifier [2,30]
    return len(identifiers) >= 2 and len(identifiers) <= 30

def traverse_json_files(base_dir): # 按时间顺序 从1975-01-01 到2024-12-31依次遍历json文件
    # 遍历每一年的文件夹
    for year in sorted(os.listdir(base_dir)):
        year_dir = os.path.join(base_dir, year)
        if os.path.isdir(year_dir):
            # 遍历每一月的文件夹
            for month in sorted(os.listdir(year_dir)):
                month_dir = os.path.join(year_dir, month)
                if os.path.isdir(month_dir):
                    # 遍历每一日的文件夹
                    for day in sorted(os.listdir(month_dir)):
                        day_dir = os.path.join(month_dir, day)
                        if os.path.isdir(day_dir):
                            # 获取当前日文件夹中所有 JSON 文件，并按文件名中的数字进行排序
                            json_files = [f for f in os.listdir(day_dir) if f.endswith('.json')]
                            json_files.sort(key=lambda x: int(x.split('.')[0]))  # 按文件名中的数字部分排序
                            # 遍历并处理每个 JSON 文件
                            for filename in json_files:
                                file_path = os.path.join(day_dir, filename)
                                yield file_path
                               


def vote_on_triples(responses: list, threshold: int) -> list:
    """
    Votes on the triples generated by the extractor agent.
    :param responses: List of response strings (each containing triples).
    :param threshold: Minimum frequency for a triple to be retained.
    :return: List of triples that passed the frequency threshold.
    """
    triples = []
    for response in responses:
        # Assuming the response is in a readable triple format, such as:
        # 'Entity1-Relationship-Entity2'
        # We need to extract all the triples from the response here
        # This is a simplified placeholder; use actual extraction logic
        triples.extend(response.split('\n'))  # Replace this with actual extraction logic
    
    triple_counts = Counter(triples)
    return [triple for triple, count in triple_counts.items() if count >= threshold]
