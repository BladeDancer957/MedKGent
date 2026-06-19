relations =["Associate", "Cause", "Compare", "Cotreat", "Drug_Interact", "Inhibit", "Interact", "Negative_Correlate", "Positive_Correlate", "Prevent", "Stimulate", "Treat"]

initial_relations = [
        "Associate | Undirected | The Associate relationship typically occurs between two Genes, Gene and Disease, Disease and Gene, Gene and Chemical, Chemical and Gene, Disease and Chemical, Chemical and Disease, Disease and Variant, Variant and Disease, two Chemicals, Chemical and Variant, Variant and Chemical, two Variants.", 

        "Cause | Directed | A positive correlation exists when the status of one entity tends to increase (or decrease) as the other increase (or decreases). The Cause relationship typically occurs between Chemical and Disease, Variant and Disease, Disease and Variant.", 

        "Compare | Undirected | The effect comparison of two chemicals/drugs. The Compare relationship typically occurs between two Chemicals.", 

        "Cotreat | Undirected | It is defined as the use of two or more chemical/drugs administered separately or in a fixed-dose combination. The Cotreat relationship typically occurs between two Chemicals.", 

        "Drug_Interact | Undirected | A pharmacodynamic interaction between two chemicals that results in an array of side effects. The Drug_Interact relationship typically occurs between two Chemicals.", 

        "Inhibit | Directed | A negative correlation exists when the status of the two entities tends to be opposite. The Inhibit relationship typically occurs between Disease and Gene, Chemical and Variant.", 

        "Interact | Undirected | Physical interaction, like protein-binding. The Interact relationship typically occurs between two Genes, Gene and Chemical, Chemical and Gene, two Chemicals, Chemical and Variant, Variant and Chemical.", 

        "Negative_Correlate | Undirected | A negative correlation exists when the status of the two entities tends to be opposite. The Negative_Correlate relationship typically occurs between two Genes, Gene and Chemical, Chemical and Gene, two Chemicals.",

        "Positive_Correlate | Undirected | A positive correlation exists when the status of one entity tends to increase (or decrease) as the other increase (or decreases). The Positive_Correlate relationship typically occurs between two Genes, Gene and Chemical, Chemical and Gene, two Chemicals.",

        "Prevent | Directed | A negative correlation exists when the status of the two entities tends to be opposite. The Prevent relationship typically occurs between Disease and Variant, Variant and Disease.",

        "Stimulate | Directed | A positive correlation exists when the status of one entity tends to increase (or decrease) as the other increase (or decreases). The Stimulate relationship typically occurs between Disease and Gene, Chemical and Variant.",

        "Treat | Directed | A chemical/drug treats a disease. The Treat relationship typically occurs between Chemical and Disease.",
    ]




extract_template = '''You are a domain expert in biomedicine and now you are building a knowledge graph in this domain. 
            Read the following abstract (### Abstract) of the medical paper, along with the medical entities (### Entities) mentioned in the abstract, separated by ' ; '. 
            Each entity consists of two parts, separated by ' | ': 'Entity Name (Alias1, Alias2) | Entity Type (one of: Disease, Chemical, Gene, Species, Variant, CellLine)'. Note that some entities may have no aliases or multiple aliases, separated by ', ' within the '()'. 
            Extract the relationships between entities (### Entities). 
            You can select a relationship from the predefined set (### Relationships), separated by ' ; '.  
            Each relationship follows this format, separated by ' | ': 'Relationship Name | Directionality (Directed or Undirected) | Relationship definition and the entity type pairs it should occur between'.
            Note that: 
            (1) When extracting triples, consider the types of the two entities and whether the relationship can exist between these entity types. 
            (2) Some relationships are strictly directional, including Cause, Inhibit, Prevent, Stimulate, and Treat (i.e., in most cases, it can only describe the relationship from the head entity to the tail entity, but not the reverse. e.g., Chemical;Treat;Disease, not Disease;Treat;Chemical).
            (3) The output should not include both "entity1 | relation1 | entity2" and "entity2 | relation1 | entity1" at the same time, e.g., "ammonia | Association | metabolic acidosis" and "metabolic acidosis | Association | ammonia".
            Your output should not include any explanations or descriptions, only contain the extracted triples, each strictly formatted as "Head Entity Name (Alias1, Alias2) | Relationship Name | Tail Entity Name (Alias1, Alias2)", e.g., "Donepezil | Treat | Alzheimer's disease (Alzheimer, AD)", with triples separated by ' $ '.
            If no triples can be extracted based on the current context, output "None".
            
            ### Abstract: {}
            ### Entities: {}
            ### Relationships: {}
            Output: Let's think step by step: '''



update_template = '''
        You are a domain expert in biomedicine working on building a knowledge graph in this field. There is an existing relationship list R: {} between medical head entity e1: {} and tail entity e2: {}, where the list can contain one or more compatible and non-conflicting relationships. 
        Each relationship in R can be used as a predicate to describe the relationship between entities e1 and e2.
        Note that some relationships are strictly directional, including Cause, Inhibit, Prevent, Stimulate, and Treat (i.e., in most cases, it can only describe the relationship from the head entity to the tail entity, but not the reverse. e.g., Chemical;Treat;Disease, not Disease;Treat;Chemical).
        Now, a new relationship r: {} has been extracted between e1 and e2, and your task is to determine whether this new relationship r conflicts with any of the relationships in list R.
            (1) If new relationship r is compatible with all relationships in R, output "Y".
            (2) If there is a conflict, analyze which relationship is more appropriate to describe the relationship between e1 and e2: new relationship r or one of the relationships in R. 
                (2-1) If new relationship r is more suitable, output the name of the conflicting relationship in R.
                (2-2) If new relationship r is less suitable, output "N". 
        Your output should not include any explanations or descriptions, only three possible outcomes: "Y", relationship name, or "N".
        
        Output: Let's think step by step: '''


update_template1 = '''
        You are a domain expert in biomedicine working on building a knowledge graph in this field. 
        Given that the relationship r: {} is a directed relationship, in most cases it can only be described from the head entity to the tail entity, and not the reverse, though there may be exceptions. 
        Now, there are two triplets between two medical entities e1: {} and e2: {}, i.e., (e1, r, e2) and (e2, r, e1). 
        Please determine whether these two triplets are compatible. If they are compatible, output "Y". If not, output "N1" if only (e1, r, e2) can exist, or output "N2" if only (e2, r, e1) can exist.
        Your output should not include any explanations or descriptions, only three possible outcomes: "Y", "N1", or "N2".
        
        Output: Let's think step by step: '''