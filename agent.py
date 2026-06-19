from openai import OpenAI

class LLMAgent:
    def __init__(self, api_key: str, base_url: str):
        """
        Initializes the agent with the given API key and base URL.
        :param api_key: The API key for accessing API.
        :param base_url: The base URL for API.
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def get_response(self, system_message: str, user_message: str, model: str, temperature: float = 1.0) -> list:
        """
        Fetches responses from the model for the given query.
        :param system_message: System-level instruction to the model.
        :param user_message: The user's message for generating a response.
        :param model: The model name (default is "deepseek-chat").
        :param n: Number of completions (default: 1).
        :param temperature: Controls randomness.
        :return: A list of generated responses.
        """
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature
        )
        return [choice.message.content for choice in response.choices]
