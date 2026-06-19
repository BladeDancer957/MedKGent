from neo4j import GraphDatabase
from template import *

class Neo4jProcessor:
    def __init__(self, uri, username, password, database_name, update_agent, model):
        # 连接到 Neo4j 数据库，数据库名称默认为 "neo4j"
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database_name = database_name
        self.update_agent = update_agent
        self.model = model

    def close(self):
        # 关闭数据库连接
        self.driver.close()

    def get_entity_by_identifier(self, tx, identifier):
        # 根据 identifier 获取实体
        result = tx.run("MATCH (e:Entity {identifier: $identifier}) RETURN e", identifier=identifier)
        return result.single()

    def create_entity(self, tx, entity):
        # 创建实体节点
        tx.run("""
            CREATE (e:Entity {identifier: $identifier, text: $text, name: $name, type: $type, database: $database, database_url: $database_url})
            """, 
            identifier=entity['identifier'],
            text=entity['text'],
            name=entity['name'],
            type=entity['type'],
            database=entity['database'],
            database_url=entity['database_url']
        )

    def create_relation(self, tx, head_id, tail_id, relation_type, score):
        # 判断关系类型是否是有向关系
        if relation_type in ["Cause", "Inhibit", "Prevent", "Stimulate", "Treat"]:
            # 有向关系：从头实体到尾实体
            tx.run("""
                MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                CREATE (h)-[r:%s {score: $score}]->(t)
                """ % relation_type, head_id=head_id, tail_id=tail_id, score=score)
                    
        else:
            # 无向关系：双向关系
            tx.run("""
                MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                CREATE (h)-[r1:%s {score: $score}]->(t)
                """ % relation_type, head_id=head_id, tail_id=tail_id, score=score)

            tx.run("""
                MATCH (h:Entity {identifier: $tail_id}), (t:Entity {identifier: $head_id})
                CREATE (h)-[r2:%s {score: $score}]->(t)
                """ % relation_type, head_id=head_id, tail_id=tail_id, score=score)


    def new_create_relation(self, tx, head, tail, relation_type, score):
        # 判断关系类型是否是有向关系
        if relation_type in ["Cause", "Inhibit", "Prevent", "Stimulate", "Treat"]:
            reverse_relations = self.get_reverse_relations(tx, head['identifier'], tail['identifier']) # 头尾实体之间的关系对象
            reverse_relations = [relation['r'][1] for relation in reverse_relations]


            if relation_type not in reverse_relations:
                tx.run("""
                    MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                    CREATE (h)-[r:%s {score: $score}]->(t)
                    """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'], score=score)
            else: # 判断两个关系是否可以兼容
                system_message = "You are a builder of biomedical knowledge graphs." 
                user_message = update_template1.format(relation_type, head["text"], tail["text"])

                while True:
                    response = self.update_agent.get_response(system_message, user_message, self.model, temperature=0.2)[0]

                    if response.strip()=="Y" or response.strip()=="N1" or response.strip()=="N2":
                        break

                if response.strip() == "Y":
                    tx.run("""
                        MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                        CREATE (h)-[r:%s {score: $score}]->(t)
                        """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'], score=score)
                elif response.strip() == "N1":  
                    # 有向关系：删除尾实体到头实体的有向关系
                    # 删除尾实体到头实体的有向关系
                    tx.run("""
                        MATCH (h:Entity {identifier: $tail_id})-[r:%s]->(t:Entity {identifier: $head_id})
                        DELETE r
                        """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'])

                    # 创建头实体到尾实体的有向关系
                    tx.run("""
                        MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                        CREATE (h)-[r:%s {score: $score}]->(t)
                        """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'], score=score)
                else:
                    pass

        else:
            # 无向关系：双向关系
            tx.run("""
                MATCH (h:Entity {identifier: $head_id}), (t:Entity {identifier: $tail_id})
                CREATE (h)-[r1:%s {score: $score}]->(t)
                """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'], score=score)

            tx.run("""
                MATCH (h:Entity {identifier: $tail_id}), (t:Entity {identifier: $head_id})
                CREATE (h)-[r2:%s {score: $score}]->(t)
                """ % relation_type, head_id=head['identifier'], tail_id=tail['identifier'], score=score)


    def update_relation(self, tx, head_id, tail_id, relation_type, score):
        # 更新关系的置信度，包括有向和无向关系
        tx.run("""
            MATCH (h:Entity {identifier: $head_id})-[r:%s]-(t:Entity {identifier: $tail_id})
            SET r.score = 1 - (1 - r.score) * (1 - $score)
            """ % relation_type, head_id=head_id, tail_id=tail_id, score=score)

    def get_existing_relations(self, tx, head_id, tail_id):
        # 获取头实体和尾实体之间的所有关系，包括有向和无向（但无法获得尾实体到头实体之间的有向关系）
        result = tx.run("""
            MATCH (h:Entity {identifier: $head_id})-[r]-(t:Entity {identifier: $tail_id})
            RETURN r
            """, head_id=head_id, tail_id=tail_id)
        
        return result.data()

    def get_reverse_relations(self, tx, head_id, tail_id):
        
        # 获取尾实体到头实体的有向关系
        result_reverse = tx.run("""
            MATCH (t:Entity {identifier: $tail_id})-[r]->(h:Entity {identifier: $head_id})
            RETURN r
            """, head_id=head_id, tail_id=tail_id)

        return result_reverse.data()


    def resolve_relation_conflict(self, tx, head, tail, conflict_relation, relation_type, score):
        # 这个函数负责根据冲突关系来解决冲突，比如删除现有关系或其他操作

        # 如果冲突关系是有向的，删除有向关系
        if conflict_relation in ["Cause", "Inhibit", "Prevent", "Stimulate", "Treat"]:
            # 有向关系：删除头实体到尾实体的有向关系
            tx.run("""
                MATCH (h:Entity {identifier: $head_id})-[r:%s]->(t:Entity {identifier: $tail_id})
                DELETE r
                """ % conflict_relation, head_id=head['identifier'], tail_id=tail['identifier'])

        else:
            # 无向关系：删除头实体到尾实体的无向关系
            tx.run("""
                MATCH (h:Entity {identifier: $head_id})-[r:%s]-(t:Entity {identifier: $tail_id})
                DELETE r
                """ % conflict_relation, head_id=head['identifier'], tail_id=tail['identifier'])

        # 删除冲突关系后，可以重新添加新的关系
        self.new_create_relation(tx, head, tail, relation_type, score)



    def process_triplet(self, tx, triplet):
        head = triplet['head']
        tail = triplet['tail']
        relation_type = triplet['type']
        score = float(triplet['score'])

        # 查找头实体和尾实体
        head_entity = self.get_entity_by_identifier(tx, head['identifier'])
        
        
        tail_entity = self.get_entity_by_identifier(tx, tail['identifier'])

        # 情况 1: 如果头实体和尾实体都没有找到，直接插入
        if not head_entity and not tail_entity:
            self.create_entity(tx, head)
            self.create_entity(tx, tail)
            self.create_relation(tx, head['identifier'], tail['identifier'], relation_type, score)

        # 情况 2: 如果头实体和尾实体都存在
        elif head_entity and tail_entity:
            existing_relations = self.get_existing_relations(tx, head['identifier'], tail['identifier']) # 头尾实体之间的关系对象
            # 2.1 如果在数据库中该对实体之间原本不存在关系，则为这对实体添加当前三元组中的关系并赋予当前三元组中的置信度
            if not existing_relations: 
                self.create_relation(tx, head['identifier'], tail['identifier'], relation_type, score)


            # 2.2 如果在数据库中该对实体之间存在关系，
            else: 
                match_relation = False 
                #2.2.1 且已经包含当前三元组中的关系，则更新数据库中该对实体在此关系（当前三元组中的关系）下的置信度，更新为1-(1-数据库中该三元组的置信度)*(1-当前三元组的置信度), 即当重复的三元组出现时，置信度增加
                for relation in existing_relations:
    
                    if relation['r'][1] == relation_type: # 
                        # The same relation type exists, update confidence score
                        match_relation = True
                        self.update_relation(tx, head['identifier'], tail['identifier'], relation_type, score)
                        break
                #2.2.2 但不包含当前三元组中的关系，则把数据库中该对实体之间的所有三元组都弹出来，和当前三元组让llm来评估对比，判断当前三元组中的关系是否可以直接加进去（加的时候注意关系是否是有向的），还是和现有的某个关系有冲突，此时，有冲突的三元组只保留一个。
                if not match_relation:
                    # 获取所有现有关系
                    # 如果 可能是元组，确保正确提取关系对象并访问其类型
                    all_relations = [relation['r'][1] for relation in existing_relations]

                    system_message = "You are a builder of biomedical knowledge graphs." 
                    user_message = update_template.format(all_relations, head["text"], tail["text"], relation_type)
                    
                    while True:
                        response = self.update_agent.get_response(system_message, user_message, self.model, temperature=0.2)[0]

                        if response.strip()=="Y" or response.strip() in all_relations or response.strip()=="N":
                            break

                    if response.strip() == "Y":
                        self.new_create_relation(tx, head, tail, relation_type, score)
                    elif response.strip() in all_relations:
                        self.resolve_relation_conflict(tx, head, tail, response.strip(), relation_type, score)
                    else:
                        pass

        # 情况 3: 如果只有头实体或尾实体在 Neo4j 中存在
        else:
            if not head_entity:
                self.create_entity(tx, head)
            if not tail_entity:
                self.create_entity(tx, tail)

            self.create_relation(tx, head['identifier'], tail['identifier'], relation_type, score)

    def process_triplets(self, triplets):
        # 遍历三元组并处理
        with self.driver.session(database=self.database_name) as session:  # 在指定的数据库上执行操作
            for triplet in triplets:
                session.execute_write(self.process_triplet, triplet)  # 替换 write_transaction 为 execute_write
