from agent import LLMAgent
from kg import Neo4jProcessor
from utils import *
from template import *
import concurrent.futures
import time
import itertools


def main():
    # Set up the agents
    api_key = "xxx"
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = "qwen-plus"  # deepseek-v3  qwen-plus qwen-max

    extractor_agent = LLMAgent(api_key, base_url)
    
    update_agent = LLMAgent(api_key, base_url)

    # Setup Neo4j
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "xxx"
    database_name = "neo4j"  # 这里指定你要使用的数据库名
    processor = Neo4jProcessor(uri, user, password, database_name, update_agent, model)

    # Define system message 
    system_message = "You are a builder of biomedical knowledge graphs." 
    
    # 1. First agent extracts triples
    base_dir = "./data_samples"

    for i, file_path in enumerate(traverse_json_files(base_dir)):
         # 读取并返回 JSON 文件内容
        json_data = read_json(file_path)

        time1 = time.time()
        # 这里可以对每个 JSON 数据进行处理
        assert has_multiple_identifiers(json_data) 

        if 'llm_relations' in json_data:
            print("该摘要已经用llm处理过了。")
            continue
        
        if i == 5:
            break

        abstract = json_data.get("abstract", [])
        entities_dict = deduplicate_entities(json_data.get("entities", []))
        entities_type, entities = generate_entity_string(entities_dict)
        relations_defination = " ; ".join(initial_relations)
        user_message = extract_template.format(abstract, entities_type, relations_defination)

       
        N = 30
        confidence_threshold = 0.6

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_response, extractor_agent, system_message, user_message, model, 0.7) for _ in range(N)]
            results = [future.result() for future in futures]

        time.sleep(3)
        
        none_response = [response for response in results if response.strip()=="None"]
        none_count = len(none_response)
        valid_response = [response for response in results if is_valid_response(response, entities, relations)]
        valid_count = len(valid_response)

        if none_count/N >0.5 or valid_count/N <0.5:
            print("当前摘要难以抽取三元组none_count:{}, 或合理输出次数太少valid_count: {}, 换下个摘要.".format(none_count/N,valid_count/N))
            if 'llm_relations' not in json_data:
                json_data['llm_relations'] = []
                write_json(json_data, file_path)
            time2 = time.time()
            print(time2-time1)
            continue
        
        candidate_triples = [response.split(" $ ") for response in valid_response]
        candidate_triples = list(itertools.chain(*candidate_triples))
        
        print("统计三元组置信度")
        print("合理输出: ", valid_count/N)
        vote_dict = vote(candidate_triples, valid_count)
        
        vote_dict = process_vote(vote_dict, confidence_threshold)

        llm_relations = transform2llm_realtions(vote_dict, entities_dict)

        # 插入neo4j数据库，更新，扩充并解决冲突
        processor.process_triplets(llm_relations)

        if 'llm_relations' not in json_data:
            json_data['llm_relations'] = llm_relations
            write_json(json_data, file_path)
        # break
        time2 = time.time()
        print(time2-time1)

    #  关闭连接
    processor.close()

if __name__ == "__main__":
    main()
