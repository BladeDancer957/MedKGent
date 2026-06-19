from agent import LLMAgent
from kg import Neo4jProcessor
from utils import *
from template import *

import argparse
import concurrent.futures
import itertools
import os
import time

from dotenv import load_dotenv


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build biomedical knowledge graphs from JSON abstracts."
    )

    parser.add_argument(
        "--model",
        type=str,
        default="qwen-plus",
        help="LLM model name, e.g. qwen-plus, qwen-max, deepseek-v3.",
    )

    parser.add_argument(
        "--base_dir",
        type=str,
        default="./data_samples",
        help="Directory containing input JSON files.",
    )

    parser.add_argument(
        "--N",
        type=int,
        default=50,
        help="Number of LLM sampling runs per abstract. Default: 50.",
    )

    parser.add_argument(
        "--confidence_threshold",
        type=float,
        default=0.6,
        help="Confidence threshold used when filtering voted triples. Default: 0.6.",
    )

    parser.add_argument(
        "--env_file",
        type=str,
        default=".env",
        help="Path to .env file. Default: .env.",
    )

    return parser.parse_args()


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def main():
    args = parse_args()

    # Load environment variables from .env
    load_dotenv(args.env_file)

    # Set up the agents
    api_key = get_required_env("API_KEY")
    base_url = os.getenv(
        "BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = args.model

    extractor_agent = LLMAgent(api_key, base_url)
    update_agent = LLMAgent(api_key, base_url)

    # Setup Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = get_required_env("NEO4J_PASSWORD")
    database_name = os.getenv("NEO4J_DATABASE", "neo4j")

    processor = Neo4jProcessor(
        uri,
        user,
        password,
        database_name,
        update_agent,
        model,
    )

    # Define system message
    system_message = "You are a builder of biomedical knowledge graphs."

    # Runtime parameters
    base_dir = args.base_dir
    N = args.N
    confidence_threshold = args.confidence_threshold

    for i, file_path in enumerate(traverse_json_files(base_dir)):
        # 读取并返回 JSON 文件内容
        json_data = read_json(file_path)

        time1 = time.time()

        # 这里可以对每个 JSON 数据进行处理
        assert has_multiple_identifiers(json_data)

        if "llm_relations" in json_data:
            print("该摘要已经用llm处理过了。")
            continue

        abstract = json_data.get("abstract", [])
        entities_dict = deduplicate_entities(json_data.get("entities", []))
        entities_type, entities = generate_entity_string(entities_dict)
        relations_defination = " ; ".join(initial_relations)
        user_message = extract_template.format(
            abstract,
            entities_type,
            relations_defination,
        )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    fetch_response,
                    extractor_agent,
                    system_message,
                    user_message,
                    model,
                    0.7,
                )
                for _ in range(N)
            ]
            results = [future.result() for future in futures]

        time.sleep(3)

        none_response = [
            response for response in results if response.strip() == "None"
        ]
        none_count = len(none_response)

        valid_response = [
            response
            for response in results
            if is_valid_response(response, entities, relations)
        ]
        valid_count = len(valid_response)

        if none_count / N > 0.5 or valid_count / N < 0.5:
            print(
                "当前摘要难以抽取三元组none_count:{}, 或合理输出次数太少valid_count: {}, 换下个摘要.".format(
                    none_count / N,
                    valid_count / N,
                )
            )

            if "llm_relations" not in json_data:
                json_data["llm_relations"] = []
                write_json(json_data, file_path)

            time2 = time.time()
            print(time2 - time1)
            continue

        candidate_triples = [
            response.split(" $ ") for response in valid_response
        ]
        candidate_triples = list(itertools.chain(*candidate_triples))

        print("统计三元组置信度")
        print("合理输出: ", valid_count / N)

        vote_dict = vote(candidate_triples, valid_count)
        vote_dict = process_vote(vote_dict, confidence_threshold)

        llm_relations = transform2llm_realtions(vote_dict, entities_dict)

        # 插入neo4j数据库，更新，扩充并解决冲突
        processor.process_triplets(llm_relations)

        if "llm_relations" not in json_data:
            json_data["llm_relations"] = llm_relations
            write_json(json_data, file_path)

        time2 = time.time()
        print(time2 - time1)

    # 关闭连接
    processor.close()


if __name__ == "__main__":
    main()